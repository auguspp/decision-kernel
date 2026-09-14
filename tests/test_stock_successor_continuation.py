"""Regression tests for the exact pre-Research production successor failure.

Synthetic only: no live GitHub, CNINFO or model calls. The real failed run/work/
reading/artifact identities are immutable request configuration, not test fetches.
"""
from datetime import date, timedelta
from pathlib import Path

import pytest

from decision_kernel.adapters import cninfo as adapter_cninfo
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_source_successor as successor
from test_stock_research_host import setup_host


def test_timezone_regression_uses_adapter_contract_before_any_inventory_fetch(tmp_path, monkeypatch):
    # Production 34797952444 failed because runtime.cninfo_http never exported this.
    assert not hasattr(successor.cninfo, "SHANGHAI_TZ")
    assert successor.SHANGHAI_TZ is adapter_cninfo.SHANGHAI_TZ
    code = "603353.SH"; ticker = "603353"
    class Session:
        code = "a" * 40
        binding = {"source_preparation": {"artifact_id": 10320565453}}
        request = {"source_preparation_run_id": 34765190284}
        def for_code(self, thscode):
            assert thscode == code
            return {"thscode": code, "material": {"selected_ids": []}, "required_reviews": []}
    seen = {}
    def fetch(**kwargs):
        seen.update(kwargs)
        raise once.TrialError("synthetic stop after timezone calculation")
    monkeypatch.setattr(successor.cninfo, "fetch_cninfo_disclosures", fetch)
    stamp = "2026-09-14T02:04:36+00:00"
    with pytest.raises(once.TrialError, match="synthetic stop"):
        successor.capture(session=Session(), ticker=ticker,
            observation={"row": {"thscode": code}}, api=object(), code_commit="a"*40,
            output=tmp_path/"sources", clock=lambda: stamp)
    assert seen["stock_code"] == ticker
    assert seen["end_date"] == date(2026, 9, 14)
    assert seen["start_date"] == date(2026, 9, 14) - timedelta(days=400)


def test_continuation_identity_is_fixed_sibling_not_revival_or_new_question():
    for code in ("603353.SH", "300711.SZ"):
        root_id, root_prefix = intake.execution(code)
        old_id, old_prefix = successor.execution(code)
        eid, prefix = successor.continuation_execution(code)
        assert old_id == root_id + "-source-successor-v1"
        assert old_prefix == root_prefix + "source-successor-v1/"
        assert eid == root_id + "-source-successor-continuation-v1"
        assert prefix == root_prefix + "source-successor-continuation-v1/"
        assert (eid, prefix) != (old_id, old_prefix)
    with pytest.raises(once.TrialError):
        successor.continuation_execution("600184.SH")


def test_continuation_request_pins_exact_failed_production_state():
    root = Path(__file__).parents[1]
    request = once.identity._json((root / successor.CONTINUATION_REQUEST).read_bytes())
    assert request["mode"] == successor.CONTINUATION_MODE
    assert request["permission"] == {"comment_id": 5652950925,
        "body_sha256": "1770b224701663c95614830b6eabadc0465eafd12164e2ddbc5052cb8bb9a33e",
        "created_at": "2026-09-13T11:22:23Z"}
    assert request["source_stock_run_id"] == 34673882756
    assert request["source_preparation_run_id"] == 34765190284
    assert request["failed_successor_run_id"] == 34797952444
    assert request["failed_successor_work_commit"] == "f53fdd6c0f1bb6088a8eae9a1363d35a975dbbb9"
    assert request["failed_successor_reading_commit"] == "eb17ca1694057fe24dad51c99c9cec9aaf431ff6"
    assert request["failed_successor_artifact"] == {
        "id": 10330128020,
        "name": "stock-business-research-34797952444-1",
        "size_in_bytes": 15816299,
        "digest": "sha256:9b9bab464bceee731e3090fe799a4defffacf7208bd9fa8e17034a3750ef4b9c",
        "head_sha": "23670560b79bb4b21f5f32fb60959b4044dd2910"}
    expected = {
        "603353.SH": ("1d3fe1b752a18a2759618e464f733bfe34b962e6", "ed9c55c958e0ebb0a8e1b35fa3a2212b13520b71"),
        "300711.SZ": ("86a5679a7bc9211ddc283554ecc8f6040e73028c", "302559a71f342b3bfcab0faa658961cc1063d16a"),
    }
    assert {i["thscode"] for i in request["items"]} == successor.TARGETS
    for item in request["items"]:
        assert (item["predecessor_selection"]["git_blob"], item["predecessor_failure"]["git_blob"]) == expected[item["thscode"]]
        assert item["predecessor_selection"]["ref"] == item["predecessor_failure"]["ref"] == request["failed_successor_work_commit"]


def test_source_refs_for_continuation_keeps_old_and_failed_successor_predecessors():
    def spec(purpose): return {"purpose": purpose}
    binding = {k: spec(k) for k in (
        "parent_selection", "parent_failure", "recovery_selection", "recovery_failure",
        "predecessor_successor_selection", "predecessor_successor_failure",
        "predecessor_successor_request", "predecessor_successor_reading")}
    assert [s["purpose"] for s in successor.source_refs(binding)] == list(binding)


def test_original_host_accepts_continuation_session_identity_without_reopening_old_child(tmp_path, monkeypatch):
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch, mode="STOP")
    code = "300711.SZ"; eid, prefix = successor.continuation_execution(code)
    args["item"].update(thscode=code, security_id=intake.security(code), execution_id=eid,
        prefix=prefix, observation={"thscode": code, "eligible_for_shadow_reading": True})
    continuation_request = {"schema_version": 1, "enabled": True, "mode": successor.CONTINUATION_MODE,
        "permission": args["request"]["permission"]}
    api.files[args["code"]][successor.CONTINUATION_REQUEST] = once.raw(continuation_request)
    binding = {"thscode": code, "execution_id": eid, "prefix": prefix,
        "material": {"selected_ids": ["synthetic"]}}
    class Session:
        request = continuation_request
        request_path = successor.CONTINUATION_REQUEST
        mode = successor.CONTINUATION_MODE
        binding = {"source_preparation": {"artifact_digest": "sha256:" + "1"*64}}
        def for_code(self, thscode):
            assert thscode == code
            return binding
    reached = []
    def capture(**kw):
        reached.append(kw["ticker"])
        raise once.TrialError("synthetic continuation capture stop")
    args.update(capture=capture, full_input=True, successor_session=Session())
    result = host.run_item(**args)
    assert reached == ["300711"] and calls == []
    assert result["execution_id"] == eid
    assert result["status"] == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE"
    old_prefix = successor.execution(code)[1]
    assert not any(path.startswith(old_prefix) for path in writes)
