"""Synthetic quiet-session source contracts through the actual audited producer/reader."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_http, hithink_sector_breadth_http
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime.sector_radar_producer import PRODUCER_STATUS_APPENDED_QUIET
from test_sector_radar_audit import (
    execute as original_execute, SyntheticProvider, MONDAY, TUESDAY, FRIDAY,
    ms, prohibit_network,
)


def execute(tmp_path, *, quiet_stock_inputs=False, **kwargs):
    # Exercise the actual workflow environment seam, not a mocked capture stage.
    with patch.dict(os.environ, {audit.QUIET_STOCK_INPUTS_ENV: "1" if quiet_stock_inputs else "0"}):
        return original_execute(tmp_path, **kwargs)


@pytest.mark.parametrize("jump,session,expected_pages", [(False, MONDAY, 1), (True, MONDAY, 1), (False, FRIDAY, 0)])
def test_quiet_input_choice_preserves_sector_results_and_replays(tmp_path, monkeypatch, jump, session, expected_pages):
    baseline, _, _ = execute(tmp_path / "baseline", jump=jump, session=session)
    outcome, provider, root = execute(tmp_path / "enabled", jump=jump, session=session, quiet_stock_inputs=True)
    assert outcome.result == baseline.result and outcome.operations == baseline.operations
    assert outcome.persistent_bundle.market_state == baseline.persistent_bundle.market_state
    assert outcome.persistent_bundle.event_ledger == baseline.persistent_bundle.event_ledger
    assert sum(path == hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH for path, _ in provider.calls) == expected_pages
    sidecar = root / "expected/output/quiet-stock-inputs.json"
    assert sidecar.is_file() == (not jump and session == MONDAY)
    if sidecar.is_file():
        report = json.loads(sidecar.read_bytes())
        assert report["status"] == "COMPLETE_QUIET_SESSION_QUOTE_INPUTS"
        assert report["returned_unique_rows"] == report["priced_rows"] == 3
        assert report["requests_attempted"] == 1 and report["unpriced_rows"] == 0
        assert outcome.persistent_bundle.event_ledger.events == ()
        assert all(report[k] == "NONE" for k in audit.AUTHORITY)
        assert (root / "inputs/quiet-stock-inputs.json").is_file()
    prohibit_network(monkeypatch)
    # Replay uses the recorded choice even if the current environment disagrees.
    monkeypatch.setenv(audit.QUIET_STOCK_INPUTS_ENV, "0")
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


@pytest.mark.parametrize("failure,attempts", [("pagination", 2)])
def test_quiet_input_failure_is_not_an_empty_scan_or_sector_failure(tmp_path, monkeypatch, failure, attempts):
    outcome, provider, root = execute(tmp_path, jump=False, failure=failure, quiet_stock_inputs=True)
    assert outcome.status == PRODUCER_STATUS_APPENDED_QUIET
    report = json.loads((root / "expected/output/quiet-stock-inputs.json").read_bytes())
    assert report["status"] == "INPUT_UNAVAILABLE_NOT_EMPTY_SCAN"
    assert report["requests_attempted"] == attempts
    assert report["returned_unique_rows"] is report["priced_rows"] is None
    assert report["error_type"] == "HithinkRuntimeError" and not report["retry_performed"]
    assert sum(path == hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH for path, _ in provider.calls) == attempts
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


@pytest.mark.parametrize("failure", ["transport", "denominator", "future_ready", "nonfinite", "credential"])
def test_quiet_input_transport_and_budget_stop_without_retry(tmp_path, monkeypatch, failure):
    original = SyntheticProvider.__call__
    def source(self, path, params):
        if path != hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH:
            return original(self, path, params)
        if failure == "transport":
            self.calls.append((path, dict(params)))
            raise hithink_http.HithinkRuntimeError("synthetic connection failure")
        body = original(self, path, params)
        if failure == "denominator": body["data"]["total"] = 8001
        if failure == "future_ready": body["data"]["timestamp"] = ms(TUESDAY)
        if failure == "nonfinite": body["data"]["item"][0]["last_price"] = "NaN"
        if failure == "credential": body["message"] = "fixture-credential-do-not-retain"
        return body
    monkeypatch.setattr(SyntheticProvider, "__call__", source)
    if failure == "credential":
        with pytest.raises(audit.SectorRadarAuditError):
            execute(tmp_path, jump=False, quiet_stock_inputs=True)
        assert not (tmp_path / "live-state").exists()
        assert all(b"fixture-credential-do-not-retain" not in p.read_bytes() for p in (tmp_path / "run").rglob("*") if p.is_file())
        return
    outcome, _, root = execute(tmp_path, jump=False, quiet_stock_inputs=True)
    report = json.loads((root / "expected/output/quiet-stock-inputs.json").read_bytes())
    assert outcome.status == PRODUCER_STATUS_APPENDED_QUIET
    assert report["status"] == "INPUT_UNAVAILABLE_NOT_EMPTY_SCAN" and report["requests_attempted"] == 1
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


@pytest.mark.parametrize("target", ["inputs/quiet-stock-inputs.json", "expected/output/quiet-stock-inputs.json"])
def test_quiet_input_rehashed_policy_or_success_cannot_replace_replay(tmp_path, monkeypatch, target):
    _, _, root = execute(tmp_path, jump=False, quiet_stock_inputs=True)
    path = root / target
    value = json.loads(path.read_bytes())
    if target.startswith("inputs/"):
        value["max_pages"] += 1
    else:
        value["returned_unique_rows"] += 1
        value["report_hash"] = canonical_hash({k:v for k,v in value.items() if k != "report_hash"})
    path.write_bytes(audit._domain_bytes(value))
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][target] = {"bytes": path.stat().st_size, "sha256": audit._sha(path.read_bytes())}
    manifest["audit_hash"] = canonical_hash({k:v for k,v in manifest.items() if k != "audit_hash"})
    manifest_path.write_bytes(audit._domain_bytes(manifest))
    prohibit_network(monkeypatch)
    with pytest.raises(audit.SectorRadarAuditError, match="policy differs|output differs"):
        audit.replay_sector_radar_input_audit(root)


def test_quiet_input_retains_unpriced_members_without_filling_prices(tmp_path, monkeypatch):
    _, _, root = execute(tmp_path, jump=False, failure="breadth", quiet_stock_inputs=True)
    report = json.loads((root / "expected/output/quiet-stock-inputs.json").read_bytes())
    assert report["status"] == "COMPLETE_QUIET_SESSION_QUOTE_INPUTS"
    assert report["returned_unique_rows"] == report["unpriced_rows"] == 3
    assert report["priced_rows"] == 0 and report["error_type"] is None
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


def test_quiet_input_environment_does_not_retroactively_enable_legacy_replay(tmp_path, monkeypatch):
    _, provider, root = execute(tmp_path, jump=False)
    assert not any(path == hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH for path, _ in provider.calls)
    monkeypatch.setenv(audit.QUIET_STOCK_INPUTS_ENV, "1")
    prohibit_network(monkeypatch)
    assert audit.replay_sector_radar_input_audit(root)["status"] == "MATCHED_SUCCEEDED"


def test_only_ordinary_produce_enables_quiet_stock_input_and_has_no_new_clock():
    text = Path(".github/workflows/sector-radar-shadow.yml").read_text()
    assert "SECTOR_QUIET_STOCK_INPUTS: ${{ inputs.operation == 'produce' && '1' || '0' }}" in text
    assert "cron:" not in text


def test_quiet_quotes_reach_existing_independent_reader(tmp_path, monkeypatch):
    from decision_kernel.runtime import current_state as model
    from decision_kernel.runtime import current_state_delivery as delivery
    from decision_kernel.runtime import independent_stock_reading as reading
    from test_independent_stock_reading import archive, detail

    outcome, _, root = execute(tmp_path / "source", jump=False, quiet_stock_inputs=True)
    c = delivery.Collector(SimpleNamespace(calls=0, max_calls=1000), "a" * 40, tmp_path)
    ref = archive(c, root, "input-audit/", 1, 101)
    session = outcome.operations.latest_completed_session.isoformat()
    at = outcome.operations.completed_at.isoformat()
    baseline = model.assemble(code_commit="a" * 40, checked_at=at, check_started_at=at,
        lanes={"sector": {"last_qualified_result": {"archive": ref, "market_session": session}}, "stock": {}},
        research={"handoffs": {"active": []}}, capabilities=[], refresh_identity={})
    c.files.update({"current-state.json": model.read_package_bytes(baseline), "README.md": b"original\n"})
    prohibit_network(monkeypatch)
    published = detail(c, reading.attach(c, baseline))
    assert published["status"] == "SAVED_INPUT_SAMPLE_WITH_EXPLICIT_GAPS"
    assert published["observations"]["coverage"]["unique_identities"] == 3
    assert published["observations"]["coverage"]["selected_qualified"] == 0
    assert published["new_source_requests"] == c.api.calls == 0
    assert published["observations"]["context"]["comparison_session"] == session


def test_invalid_quiet_configuration_stops_before_any_source(tmp_path, monkeypatch):
    monkeypatch.setenv(audit.QUIET_STOCK_INPUTS_ENV, "yes")
    prohibit_network(monkeypatch)
    with pytest.raises(audit.SectorRadarAuditError, match="configuration"):
        original_execute(tmp_path, jump=False)
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("damage", [None, "unknown"])
def test_pre_quiet_institutional_receipt_keeps_strict_forward_compatibility(tmp_path, monkeypatch, damage):
    from test_institutional_radar import run_capture
    from decision_kernel.runtime import institutional_radar_capture as capture
    from decision_kernel.runtime import institutional_radar_compat as compat
    with monkeypatch.context() as m:
        m.setattr(capture, '_implementation', lambda: dict(compat.PRE_QUIET_STOCK_INPUTS))
        root, *_ = run_capture(tmp_path)
        expected = capture.verify(root)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    original = capture._implementation
    prohibit_network(monkeypatch)
    with pytest.raises(ValueError):
        capture.verify(root)
    if damage:
        monkeypatch.setattr(capture, '_implementation', lambda: {**compat.INSTALLED, 'extra': '0'*64})
        with pytest.raises(ValueError, match='UNREVIEWED_INSTITUTIONAL_COMPATIBILITY'):
            compat.verify(root)
    else:
        assert compat.verify(root) == (expected, compat.QUIET_EQUIVALENCE)
        assert capture._implementation is original
        with pytest.raises(ValueError):
            capture.verify(root)
        monkeypatch.setattr(capture, '_implementation', lambda: dict(compat.HISTORICAL))
        with pytest.raises(ValueError, match='UNREVIEWED_INSTITUTIONAL_COMPATIBILITY'):
            compat.verify(root)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


@pytest.mark.parametrize("damage", [None, "unknown"])
def test_pre_quiet_nested_concept_receipts_remain_exact_without_reverse_pairs(tmp_path, monkeypatch, damage):
    from test_concept_detail_supplement import execute
    from decision_kernel.runtime import concept_detail_capture as detail
    from decision_kernel.runtime import concept_radar_capture as primary
    from decision_kernel.runtime import concept_detail_compat as compat
    with monkeypatch.context() as m:
        m.setattr(primary, '_implementation', lambda: dict(compat.PRIMARY_AFTER_SECTOR))
        m.setattr(detail, '_implementation', lambda: dict(compat.POST_STOCK_READING_IMPLEMENTATION))
        root, *_ = execute(tmp_path)
        expected = detail.verify(root)
        expected_primary = primary.verify(tmp_path / 'original')
    roots = (root, tmp_path/'original')
    before = [{p.name: p.read_bytes() for p in r.iterdir()} for r in roots]
    functions = primary._implementation, detail._implementation, detail.load_base
    prohibit_network(monkeypatch)
    with pytest.raises(ValueError):
        detail.verify(root)
    with pytest.raises(ValueError):
        primary.verify(roots[1])
    if damage:
        monkeypatch.setattr(primary, '_implementation', lambda: {**compat.PRIMARY_AFTER_QUIET_STOCK_INPUTS, 'extra': '0'*64})
        with pytest.raises(ValueError, match='CONCEPT_HISTORICAL_IMPLEMENTATION_REJECTED'):
            compat.verify(root)
    else:
        assert compat.verify_primary(roots[1]) == (expected_primary, compat.PRIMARY_QUIET_EQUIVALENCE)
        assert compat.verify(root) == (expected, compat.PRIOR_DELIVERY)
        assert functions == (primary._implementation, detail._implementation, detail.load_base)
        with pytest.raises(ValueError):
            detail.verify(root)
        monkeypatch.setattr(detail, '_implementation', lambda: dict(compat.POST_SECTOR_BACKFILL_IMPLEMENTATION))
        with pytest.raises(ValueError, match='DETAIL_HISTORICAL_IMPLEMENTATION_REJECTED'):
            compat.verify(root)
    assert before == [{p.name: p.read_bytes() for p in r.iterdir()} for r in roots]


def test_quiet_compatibility_adds_only_exact_audit_hash_and_preserves_prior_maps():
    from decision_kernel.runtime import concept_detail_compat as concept
    from decision_kernel.runtime import institutional_radar_compat as institutional
    pairs = ((concept.POST_STOCK_READING_IMPLEMENTATION, concept.POST_QUIET_STOCK_INPUTS_IMPLEMENTATION),
             (concept.PRIMARY_AFTER_SECTOR, concept.PRIMARY_AFTER_QUIET_STOCK_INPUTS),
             (institutional.PRE_QUIET_STOCK_INPUTS, institutional.INSTALLED))
    for before, after in pairs:
        assert before.keys() == after.keys()
        assert {k for k in before if before[k] != after[k]} == {'runtime/sector_radar_audit.py'}
        assert before['runtime/sector_radar_audit.py'] == '1cdf284024b114b05d6fdfeeed99d4550d2b5d59b8b69676c1962660b5ac1e07'
        assert after['runtime/sector_radar_audit.py'] == '00813ef1d0ed817098c96d72b250c6c36b112a4df55d04bd201f6fa48890c8a6'
        with pytest.raises(TypeError):
            after['extra'] = '0'*64
