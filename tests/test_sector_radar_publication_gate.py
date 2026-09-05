from __future__ import annotations

import json
import runpy
import shutil
from datetime import datetime, time, timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime import sector_radar_context as surface
from decision_kernel.runtime import hithink_http
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar_producer import SectorRadarProducerContext, SECTOR_RADAR_WORKFLOW_PATH
from test_sector_radar_audit import (
    FRIDAY, MONDAY, REPOSITORY, TZ, SyntheticProvider, execute, hints_json,
    prohibit_network, resolution,
)

SCRIPT = Path(".github/scripts/verify-sector-radar-publication.py").resolve()
WORKFLOW = Path(".github/workflows/sector-radar-shadow.yml")


def script():
    return runpy.run_path(str(SCRIPT), run_name="publication_gate_test")


def identity():
    return {"repository": REPOSITORY, "workflow_path": SECTOR_RADAR_WORKFLOW_PATH,
            "run_id": 101, "run_attempt": 1, "commit_sha": "a" * 40}


def inventory(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def make_case(tmp_path, monkeypatch, mode="candidates", failure=None):
    """Exercise the LIVE code branch with MOCKED transport entirely in tmp_path.

    These are synthetic integration tests, not genuine LIVE_HITHINK acquisition
    evidence. No artifacts from this fixture are promoted to the real state chain.
    """
    restored = resolution()
    session = FRIDAY if mode == "same-session" else MONDAY
    observed = datetime.combine(session, time(16, 10), tzinfo=TZ)
    context = SectorRadarProducerContext(**identity(), observed_at=observed)
    provider = SyntheticProvider(restored, session=session, jump=mode == "candidates", failure=failure)
    prohibit_network(monkeypatch)
    monkeypatch.setattr(hithink_http, "_request_hithink_json",
                        lambda **kwargs: provider(kwargs["path"], kwargs["params"]))
    raw_hints = hints_json()
    run_dir, state_dir = tmp_path / "sector-radar-run", tmp_path / "decision-state/sector-radar"
    try:
        outcome = audit.run_audited_sector_radar_producer(
            resolution=restored, parent_hints=parse_sector_parent_hints(raw_hints),
            parent_hints_json=raw_hints, context=context,
            state_directory=state_dir, output_directory=run_dir,
            api_key="fixture-credential", now=lambda: observed + timedelta(minutes=5),
            capture_now=lambda: observed,
        )
    finally:
        prohibit_network(monkeypatch)
    return run_dir, state_dir, outcome, observed


def workflow_environment(monkeypatch):
    for key, value in {
        "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ID": "101", "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_SHA": "a" * 40,
        "HITHINK_FINANCE_API_KEY": "",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize("mode", ["same-session", "quiet", "candidates"])
def test_existing_replay_matches_actual_uploads_then_context_without_new_events(tmp_path, monkeypatch, mode):
    run_dir, state_dir, outcome, observed = make_case(tmp_path, monkeypatch, mode)
    before_state, before_run = inventory(state_dir), inventory(run_dir)
    workflow_environment(monkeypatch)
    monkeypatch.chdir(tmp_path)
    gate = script()
    gate["main"]()
    receipt = json.loads((run_dir / gate["RECEIPT_NAME"]).read_text())
    assert receipt["status"] == "REPLAY_AND_UPLOAD_FILES_MATCHED"
    assert receipt["offline_replay"]["status"] == "MATCHED_SUCCEEDED"
    assert receipt["offline_replay"]["network_calls"] == 0
    assert receipt["offline_replay"]["production_state_writes"] == 0
    assert receipt["market_state_hash"] == outcome.persistent_bundle.market_state.state_hash
    assert receipt["event_ledger_hash"] == outcome.persistent_bundle.event_ledger.ledger_hash
    assert receipt["verification_hash"] == canonical_hash({k: v for k, v in receipt.items() if k != "verification_hash"})
    assert receipt["workflow_identity"] == identity()
    assert inventory(state_dir) == before_state
    after = inventory(run_dir)
    assert {k: v for k, v in after.items() if k != gate["RECEIPT_NAME"]} == before_run

    class Clock:
        @staticmethod
        def now(tz=None):
            return observed + timedelta(minutes=6)

    monkeypatch.setattr(surface, "datetime", Clock)
    assert surface.main([
        "--bundle", str(state_dir), "--parent-hints", str(run_dir / "input-audit/inputs/parent-hints.json"),
        "--output", str(run_dir / "context"),
    ]) == 0
    displayed = json.loads((run_dir / "context/context.json").read_text())
    assert displayed["market_state_hash"] == receipt["market_state_hash"]
    assert displayed["event_ledger_hash"] == receipt["event_ledger_hash"]
    assert displayed["recorded_events_latest_session"] == (2 if mode == "candidates" else 0)
    assert displayed["new_alerts_created"] == 0
    assert inventory(state_dir) == before_state


@pytest.mark.parametrize("target", [
    "state/market-state.json", "state/candidate-events.json", "state/manifest.json",
    "output/operations.json", "output/operations.md", "output/result.json", "output/summary.md",
])
def test_even_parse_equivalent_upload_byte_changes_cannot_pass(tmp_path, monkeypatch, target):
    run_dir, state_dir, _, _ = make_case(tmp_path, monkeypatch)
    category, name = target.split("/")
    path = (state_dir if category == "state" else run_dir) / name
    path.write_bytes(path.read_bytes() + b"\n")
    before = inventory(tmp_path)
    with pytest.raises(ValueError, match="upload file differs"):
        script()["verify_publication"](run_dir, state_dir, identity())
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("field", ["repository", "workflow_path", "run_id", "run_attempt", "commit_sha"])
def test_other_run_identity_is_rejected(tmp_path, monkeypatch, field):
    run_dir, state_dir, _, _ = make_case(tmp_path, monkeypatch, "same-session")
    expected = identity()
    expected[field] = 2 if field in {"run_id", "run_attempt"} else "other"
    with pytest.raises(ValueError, match="identity differs"):
        script()["verify_publication"](run_dir, state_dir, expected)


def test_a_valid_synthetic_audit_is_not_a_live_publication_proof(tmp_path, monkeypatch):
    _, _, root = execute(tmp_path)
    state_dir = tmp_path / "copied-test-state"
    shutil.copytree(root / "expected/state", state_dir)
    prohibit_network(monkeypatch)
    with pytest.raises(ValueError, match="successful live"):
        script()["verify_publication"](root.parent, state_dir, identity())


def test_a_matched_rejection_is_not_a_successful_publication(tmp_path, monkeypatch):
    with pytest.raises(audit.SectorRadarAuditError):
        make_case(tmp_path, monkeypatch, failure="continuity")
    root = tmp_path / "sector-radar-run/input-audit"
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_REJECTED"
    state_dir = tmp_path / "decision-state/sector-radar"
    state_dir.mkdir(parents=True)
    with pytest.raises(ValueError, match="successful live"):
        script()["verify_publication"](root.parent, state_dir, identity())


@pytest.mark.parametrize("change", ["missing", "extra-state", "extra-run", "symlink", "receipt", "response"])
def test_missing_stale_or_unsealed_files_fail_without_writes(tmp_path, monkeypatch, change):
    run_dir, state_dir, _, _ = make_case(tmp_path, monkeypatch, "same-session")
    gate = script()
    if change == "missing": (state_dir / "candidate-events.json").unlink()
    if change == "extra-state": (state_dir / "old.json").write_text("{}")
    if change == "extra-run": (run_dir / "summary.md").write_text("old candidate summary")
    if change == "symlink":
        path = state_dir / "market-state.json"
        path.unlink()
        path.symlink_to(run_dir / "input-audit/expected/state/market-state.json")
    if change == "receipt": (run_dir / gate["RECEIPT_NAME"]).write_text("previous receipt")
    if change == "response":
        path = next((run_dir / "input-audit/responses").iterdir())
        path.write_bytes(path.read_bytes() + b"\n")
    before = inventory(tmp_path)
    with pytest.raises((ValueError, RuntimeError)):
        gate["verify_publication"](run_dir, state_dir, identity())
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_EVENT_NAME", "schedule"),
    ("GITHUB_RUN_ATTEMPT", "2"), ("HITHINK_FINANCE_API_KEY", "must-not-be-passed"),
])
def test_cli_refuses_wrong_context_before_reading_any_state(tmp_path, monkeypatch, key, value):
    workflow_environment(monkeypatch)
    monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        script()["main"]()
    assert list(tmp_path.iterdir()) == []


def test_workflow_gates_remote_publication_and_retains_failed_audit():
    text = WORKFLOW.read_text()
    names = ["Run independent Sector Radar shadow producer", "Verify exact offline replay before publication",
             "Render read-only saved-state context", "Upload complete run audit",
             "Upload authoritative state bundle", "Save cache acceleration copy"]
    positions = [text.index(name) for name in names]
    assert positions == sorted(positions)
    gate = text.split("      - name: " + names[1] + "\n")[1].split("      - name: ")[0]
    assert "if: success()" in gate and 'HITHINK_FINANCE_API_KEY: ""' in gate
    assert "python .github/scripts/verify-sector-radar-publication.py" in gate
    for name in names[4:]:
        assert "if: success()" in text.split("      - name: " + name + "\n")[1].split("      - name: ")[0]
    assert "if: always()" in text.split("      - name: " + names[3] + "\n")[1].split("      - name: ")[0]
    assert "steps.replay-check.outcome" in text
    assert "publication-verification.json" in text
    assert "schedule:" not in text and "continue-on-error" not in text
