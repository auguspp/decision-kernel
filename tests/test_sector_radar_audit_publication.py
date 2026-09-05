from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime import hithink_http, sector_radar_producer
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_producer import SectorRadarProducerContext, SECTOR_RADAR_WORKFLOW_PATH

from test_sector_radar_audit import (
    OBSERVED, PRODUCED, REPOSITORY, SyntheticProvider,
    execute, hints_json, prohibit_network, resolution,
)


class StubTransportBoundary:
    """Exercise default CLI wiring with synthetic inputs entirely inside pytest.

    This is not a real HiThink run: the lowest transport is replaced before the
    producer starts, a dummy credential is used, and every file is under tmp_path.
    No workflow or artifact upload is performed by these tests.
    """
    def __init__(self, monkeypatch, tmp_path, *, jump=False, failure=None):
        self.root = tmp_path
        self.restored = resolution()
        self.provider = SyntheticProvider(self.restored, jump=jump, failure=failure)
        self.raw_hints = hints_json()
        self.hints = parse_sector_parent_hints(self.raw_hints)
        self.calls = []

        def transport(*, api_key, path, params, timeout_seconds):
            assert api_key == "pytest-not-a-provider-secret"
            self.calls.append(path)
            return self.provider(path, params)

        monkeypatch.setattr(hithink_http, "_request_hithink_json", transport)
        monkeypatch.setattr(hithink_http, "_request_hithink_calendar", lambda **kwargs: pytest.fail("unrecorded calendar access"))

    def run(self):
        return audit.run_audited_sector_radar_producer(
            resolution=self.restored, parent_hints=self.hints,
            parent_hints_json=self.raw_hints,
            context=SectorRadarProducerContext(REPOSITORY, SECTOR_RADAR_WORKFLOW_PATH, 201, 1, "a" * 40, OBSERVED),
            state_directory=self.root / "state-target",
            output_directory=self.root / "run",
            api_key="pytest-not-a-provider-secret",
            now=lambda: PRODUCED, capture_now=lambda: OBSERVED,
        )


def sentinel_state(root):
    target = root / "state-target"
    target.mkdir()
    for name, content in (("market-state.json", b"previous market"), ("candidate-events.json", b"previous ledger"), ("manifest.json", b"previous manifest")):
        (target / name).write_bytes(content)
    return {path.name: path.read_bytes() for path in target.iterdir()}


def test_default_wiring_seals_complete_audit_before_publishing(tmp_path, monkeypatch):
    boundary = StubTransportBoundary(monkeypatch, tmp_path)
    publish = audit._publish_bundle
    publications = []

    def checked_publish(bundle, directory):
        root = tmp_path / "run/input-audit"
        manifest = audit.validate_sector_radar_input_audit(root)
        assert manifest["status"] == "SUCCEEDED"
        for name in ("market-state.json", "candidate-events.json", "manifest.json"):
            assert (root / "expected/state" / name).is_file()
        assert not directory.exists()
        publications.append(directory)
        publish(bundle, directory)

    monkeypatch.setattr(audit, "_publish_bundle", checked_publish)
    outcome = boundary.run()
    assert publications == [tmp_path / "state-target"]
    persisted = load_sector_radar_persistent_bundle(
        tmp_path / "state-target", expected_repository=REPOSITORY,
        expected_workflow=SECTOR_RADAR_WORKFLOW_PATH,
        expected_parent_hint_mapping_hash=boundary.hints.mapping_hash,
    )
    assert persisted.market_state == outcome.persistent_bundle.market_state
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(tmp_path / "run/input-audit")["status"] == "MATCHED_SUCCEEDED"


@pytest.mark.parametrize("stage", ["calculation", "audit_write", "audit_validation", "final_publish"])
def test_default_wiring_failures_preserve_old_target_bytes(tmp_path, monkeypatch, stage):
    boundary = StubTransportBoundary(monkeypatch, tmp_path, failure="continuity" if stage == "calculation" else None)
    before = sentinel_state(tmp_path)
    publications = []
    publish = audit._publish_bundle

    def checked_publish(bundle, directory):
        publications.append(directory)
        publish(bundle, directory)

    monkeypatch.setattr(audit, "_publish_bundle", checked_publish)
    if stage == "audit_write":
        add = audit._Recorder.add
        def failed_add(self, name, data):
            if name == "expected/state/market-state.json":
                raise OSError("synthetic disk-full audit failure")
            return add(self, name, data)
        monkeypatch.setattr(audit._Recorder, "add", failed_add)
    elif stage == "audit_validation":
        monkeypatch.setattr(audit, "validate_sector_radar_input_audit", lambda root: (_ for _ in ()).throw(audit.SectorRadarAuditError("synthetic sealed-audit validation failure")))
    elif stage == "final_publish":
        replace_directory = Path.replace
        target = tmp_path / "state-target"
        def failed_replace(self, destination):
            # Fail precisely after the old target was moved to backup. The
            # production bundle writer must restore that backup on error.
            if self == target.with_name(f".{target.name}.tmp") and Path(destination) == target:
                raise OSError("synthetic final directory-swap failure")
            return replace_directory(self, destination)
        monkeypatch.setattr(Path, "replace", failed_replace)
    with pytest.raises((OSError, audit.SectorRadarAuditError)):
        boundary.run()
    assert {path.name: path.read_bytes() for path in (tmp_path / "state-target").iterdir()} == before
    assert len(publications) == (1 if stage == "final_publish" else 0)
    assert not (tmp_path / ".state-target.tmp").exists()
    assert not (tmp_path / ".state-target.backup").exists()


def test_context_clock_offset_is_preserved_for_existing_state_hash_contract(tmp_path, monkeypatch):
    _, _, root = execute(tmp_path, jump=False)
    context = json.loads((root / "inputs/context.json").read_text())
    assert context["observed_at"].endswith("+08:00")
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


def test_cli_dispatches_through_audit_wrapper_without_any_real_network(tmp_path, monkeypatch):
    restored = resolution()
    hints = parse_sector_parent_hints(hints_json())
    raw_path = tmp_path / "hints.json"
    raw_path.write_text(hints_json())
    calls = []
    monkeypatch.setattr(sector_radar_producer, "load_sector_parent_hints", lambda path: hints)
    monkeypatch.setattr(sector_radar_producer, "resolve_sector_radar_persistence", lambda **kwargs: restored)
    def wrapper(**kwargs):
        calls.append(kwargs)
        raise audit.SectorRadarAuditError("synthetic stop before transport")
    monkeypatch.setattr(sector_radar_producer, "run_audited_sector_radar_producer", wrapper)
    prohibit_network(monkeypatch)
    result = sector_radar_producer.main([
        "run", "--repository", REPOSITORY, "--run-id", "201", "--run-attempt", "1",
        "--commit-sha", "a" * 40, "--prior-success-found", "false", "--artifact-available", "false",
        "--state-directory", str(tmp_path / "state-target"),
        "--output-directory", str(tmp_path / "run"), "--parent-hints", str(raw_path),
    ])
    assert result == 2
    assert len(calls) == 1
    assert calls[0]["parent_hints_json"] == raw_path.read_text()
    assert not (tmp_path / "state-target").exists()


def test_replay_checks_source_manifest_against_actual_input_files(tmp_path, monkeypatch):
    first, _, _ = execute(tmp_path / "first")
    bundle = first.persistent_bundle
    from decision_kernel.runtime.sector_radar_persistence import SectorRadarPersistenceResolution, SOURCE_LATEST_SUCCESS_ARTIFACT
    restored = SectorRadarPersistenceResolution(
        source_kind=SOURCE_LATEST_SUCCESS_ARTIFACT, market_state=bundle.market_state,
        event_ledger=bundle.event_ledger, source_bundle_manifest=bundle.manifest,
        bootstrap_manifest_hash=None,
    )
    _, _, root = execute(tmp_path / "restored", restored=restored, run_id=102)
    source_path = root / "inputs/resolution.json"
    source = json.loads(source_path.read_text())
    manifest = source["source_bundle_manifest"]
    manifest["market_state_file_sha256"] = "f" * 64
    manifest.pop("manifest_hash")
    manifest["manifest_hash"] = canonical_hash(manifest)
    data = json.dumps(source).encode()
    source_path.write_bytes(data)
    audit_path = root / "manifest.json"
    audit_manifest = json.loads(audit_path.read_text())
    audit_manifest["files"]["inputs/resolution.json"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    audit_manifest.pop("audit_hash")
    audit_manifest["audit_hash"] = canonical_hash(audit_manifest)
    audit_path.write_text(json.dumps(audit_manifest))
    prohibit_network(monkeypatch)
    with pytest.raises(audit.SectorRadarAuditError, match="source manifest"):
        audit.replay_sector_radar_input_audit(root)
