"""Synthetic safety tests for the consumed Stock successor continuation.

No live GitHub, CNINFO or model calls occur here. Exact one-shot production
receipts stay frozen in the request/docs/Git history; blocking tests protect the
reusable continuation identity, binding and fail-closed contracts.
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
    assert cninfo_http.SHANGHAI_TZ is adapter_cninfo.SHANGHAI_TZ
    assert successor.cninfo.SHANGHAI_TZ is adapter_cninfo.SHANGHAI_TZ
    code = "603353.SH"; ticker = "603353"
    class Session:
        code = "a" * 40
        binding = {"source_preparation": {"artifact_id": 1}}
        request = {"source_preparation_run_id": 2}
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


def test_continuation_request_stays_structurally_bound_to_consumed_predecessor():
    root = Path(__file__).parents[1]
    request = once.identity._json((root / continuation.REQUEST).read_bytes())
    assert set(request) == {"schema_version", "enabled", "mode", "permission",
        "source_stock_run_id", "source_preparation_run_id", "failed_successor_run_id",
        "failed_successor_artifact", "failed_successor_reading_commit",
        "failed_successor_work_commit", "items"}
    assert request["schema_version"] == 1 and request["enabled"] is True
    assert request["mode"] == continuation.MODE
    assert set(request["permission"]) == {"comment_id", "body_sha256", "created_at"}
    assert type(request["permission"]["comment_id"]) is int and request["permission"]["comment_id"] > 0
    assert len(request["permission"]["body_sha256"]) == 64
    assert all(type(request[k]) is int and request[k] > 0 for k in
        ("source_stock_run_id", "source_preparation_run_id", "failed_successor_run_id"))

    def lowercase_hex(value, length):
        return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)

    assert lowercase_hex(request["failed_successor_work_commit"], 40)
    assert lowercase_hex(request["failed_successor_reading_commit"], 40)
    artifact = request["failed_successor_artifact"]
    assert set(artifact) == {"id", "name", "size_in_bytes", "digest", "head_sha"}
    assert type(artifact["id"]) is int and artifact["id"] > 0
    assert type(artifact["size_in_bytes"]) is int and artifact["size_in_bytes"] > 0
    assert isinstance(artifact["name"], str) and artifact["name"]
    assert artifact["digest"].startswith("sha256:") and lowercase_hex(artifact["digest"][7:], 64)
    assert lowercase_hex(artifact["head_sha"], 40)

    items = request["items"]
    assert isinstance(items, list) and len(items) == len(continuation.TARGETS)
    assert {i["thscode"] for i in items} == continuation.TARGETS
    for item in items:
        assert set(item) == {"thscode", "predecessor_selection", "predecessor_failure"}
        for key, suffix, purpose in (
            ("predecessor_selection", "/source-successor-v1/prepare.json",
             "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_SELECTION_REQUEST"),
            ("predecessor_failure", "/source-successor-v1/failure.json",
             "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_FAILURE_REQUEST")):
            spec = item[key]
            assert set(spec) == {"repository", "path", "ref", "git_blob", "sha256", "purpose"}
            assert spec["repository"] == once.REPO
            assert spec["ref"] == request["failed_successor_work_commit"]
            assert spec["path"].endswith(suffix) and spec["purpose"] == purpose
            assert lowercase_hex(spec["git_blob"], 40) and lowercase_hex(spec["sha256"], 64)


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


def test_reader_preserves_accepted_bounds_and_failed_work_ref():
    root = Path(__file__).parents[1]
    text = (root / "src/decision_kernel/runtime/stock_research_reading.py").read_text()
    assert "EXTRA_API_CALLS = 72" in text and "MAX_STOCK_SOURCE_FILES = 32" in text
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
