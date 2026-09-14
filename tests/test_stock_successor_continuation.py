"""Regression tests for the exact pre-Research production successor failure.

Synthetic only: no live GitHub, CNINFO or model calls. The real failed run/work/
reading/artifact identities are immutable request configuration, not test fetches.
"""
from datetime import date, timedelta
from pathlib import Path

import pytest

from decision_kernel.adapters import cninfo as adapter_cninfo
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_source_successor as successor
from decision_kernel.runtime import stock_source_successor_continuation as continuation
from test_stock_research_host import setup_host


def test_timezone_regression_uses_runtime_contract_before_any_inventory_fetch(tmp_path, monkeypatch):
    # Production 34797952444 failed before network because runtime.cninfo_http lacked this export.
    assert cninfo_http.SHANGHAI_TZ is adapter_cninfo.SHANGHAI_TZ
    assert successor.cninfo.SHANGHAI_TZ is adapter_cninfo.SHANGHAI_TZ
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
        eid, prefix = continuation.execution(code)
        assert old_id == root_id + "-source-successor-v1"
        assert old_prefix == root_prefix + "source-successor-v1/"
        assert eid == root_id + "-source-successor-continuation-v1"
        assert prefix == root_prefix + "source-successor-continuation-v1/"
        assert (eid, prefix) != (old_id, old_prefix)
    with pytest.raises(once.TrialError):
        continuation.execution("600184.SH")


def test_continuation_request_pins_exact_failed_production_state():
    root = Path(__file__).parents[1]
    request = once.identity._json((root / continuation.REQUEST).read_bytes())
    assert request["mode"] == continuation.MODE
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
    assert {i["thscode"] for i in request["items"]} == continuation.TARGETS
    for item in request["items"]:
        assert (item["predecessor_selection"]["git_blob"], item["predecessor_failure"]["git_blob"]) == expected[item["thscode"]]
        assert item["predecessor_selection"]["ref"] == item["predecessor_failure"]["ref"] == request["failed_successor_work_commit"]


def test_source_refs_for_continuation_keeps_old_and_failed_successor_predecessors():
    def spec(purpose): return {"purpose": purpose}
    binding = {k: spec(k) for k in (
        "parent_selection", "parent_failure", "recovery_selection", "recovery_failure",
        "predecessor_successor_selection", "predecessor_successor_failure",
        "predecessor_successor_request", "predecessor_successor_reading")}
    assert [s["purpose"] for s in continuation.source_refs(binding)] == list(binding)


def test_original_host_accepts_continuation_session_identity_without_reopening_old_child(tmp_path, monkeypatch):
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch, mode="STOP")
    code = "300711.SZ"; eid, prefix = continuation.execution(code)
    args["item"].update(thscode=code, security_id=intake.security(code), execution_id=eid,
        prefix=prefix, observation={"thscode": code, "eligible_for_shadow_reading": True})
    continuation_request = {"schema_version": 1, "enabled": True, "mode": continuation.MODE,
        "permission": args["request"]["permission"]}
    api.files[args["code"]][continuation.REQUEST] = once.raw(continuation_request)
    binding = {"thscode": code, "execution_id": eid, "prefix": prefix,
        "material": {"selected_ids": ["synthetic"]}}
    class Session:
        request = continuation_request
        request_path = continuation.REQUEST
        mode = continuation.MODE
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
    assert all(old_prefix not in endpoint for _, endpoint, _ in writes)


def test_reader_keeps_failed_work_ref_distinct_and_does_not_raise_accepted_bounds():
    root = Path(__file__).parents[1]
    text = (root / "src/decision_kernel/runtime/stock_research_reading.py").read_text()
    assert "EXTRA_API_CALLS = 64" in text and "MAX_STOCK_SOURCE_FILES = 24" in text
    assert "failed_work_ref = binding['predecessor_successor_selection']['ref']" in text
    assert "continuation_request['failed_successor_work_commit'] == failed_work_ref" in text
    assert "continuation_reading['research']['stock_business_work']['work_commit'] == failed_work_ref" in text
    assert "predecessor_reading['research']['stock_business_work']['work_commit'] == failed_work_ref" in text
    assert "continuation_request['failed_successor_work_commit'] == commit" not in text


def test_recheck_allows_new_child_work_commit_but_requires_predecessor_blobs():
    root = Path(__file__).parents[1]
    text = (root / "src/decision_kernel/runtime/stock_source_successor_continuation.py").read_text()
    recheck = text.split("def recheck", 1)[1]
    assert 'work_head == session.request["failed_successor_work_commit"]' not in recheck
    assert 'rows.get(spec["path"], {}).get("sha") == spec["git_blob"]' in recheck
