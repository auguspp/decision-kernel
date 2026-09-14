"""Synthetic tests for the bounded saved-artifact Stock successor.

No live source, GitHub Actions dispatch or model call occurs here. The real
artifact/request identities are asserted as immutable configuration only.
"""
from pathlib import Path

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_source_successor as successor
from test_stock_research_host import setup_host


def test_successor_identity_is_one_fixed_child_not_price_date_or_permission():
    for code in ("603353.SH", "300711.SZ"):
        root_id, root_prefix = intake.execution(code)
        eid, prefix = successor.execution(code)
        assert eid == root_id + "-source-successor-v1"
        assert prefix == root_prefix + "source-successor-v1/"
    with pytest.raises(once.TrialError):
        successor.execution("600184.SH")


def test_work_inventory_accepts_only_the_named_successor_child():
    code = "603353.SH"; _, root = intake.execution(code)
    path = root + "source-successor-v1/prepare.json"
    class API:
        def get(self, _):
            return {"truncated": False, "tree": [{"path": path, "type": "blob", "mode": "100644",
                "sha": "a"*40, "size": 2}]}
    assert path in intake.inventory(API(), "b"*40)
    bad = root + "source-successor-v2/prepare.json"
    class Bad:
        def get(self, _):
            return {"truncated": False, "tree": [{"path": bad, "type": "blob", "mode": "100644",
                "sha": "a"*40, "size": 2}]}
    with pytest.raises(once.TrialError, match="outside contract"):
        intake.inventory(Bad(), "b"*40)


def test_successor_request_binds_exact_source_only_artifact_and_old_permission():
    root = Path(__file__).parents[1]
    request = once.identity._json((root / successor.REQUEST).read_bytes())
    prep = (root / "research_runs/stock-source-preparation-request.json").read_bytes()
    assert request["permission"] == {"comment_id": 5652950925,
        "body_sha256": "1770b224701663c95614830b6eabadc0465eafd12164e2ddbc5052cb8bb9a33e",
        "created_at": "2026-09-13T11:22:23Z"}
    assert request["source_preparation_request_sha256"] == once.sha(prep)
    assert request["source_preparation_run_id"] == 34765190284
    assert request["source_research_run_id"] == 34751517820
    assert request["source_stock_run_id"] == 34673882756
    assert request["source_preparation_artifact"] == {
        "id": 10320565453,
        "name": "stock-source-preparation-34765190284-1",
        "size_in_bytes": 12563240,
        "digest": "sha256:25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c",
        "head_sha": "99ad4e9391231be86b0bff27f2776a3966215fe8"}
    assert {i["thscode"] for i in request["items"]} == successor.TARGETS
    gh = next(i for i in request["items"] if i["thscode"] == "300711.SZ")
    assert gh["material"]["prepared_context_bytes"] == 636462
    assert gh["material"]["prepared_context_sha256"] == "4cb6c5a18a18ef6ed8b011f315c7bac000a3ecaaf4b21b6cd72b476a3344cbf0"


def test_host_successor_does_not_run_a_context_recheck_before_saved_capture(tmp_path, monkeypatch):
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch, mode="STOP")
    code = "603353.SH"; eid, prefix = successor.execution(code)
    args["item"].update(thscode=code, security_id=intake.security(code), execution_id=eid,
        prefix=prefix, observation={"thscode": code, "eligible_for_shadow_reading": True})
    successor_request = {"schema_version": 1, "enabled": True, "mode": successor.MODE,
        "permission": args["request"]["permission"]}
    api.files[args["code"]][successor.REQUEST] = once.raw(successor_request)
    binding = {"thscode": code, "execution_id": eid, "prefix": prefix,
        "material": {"selected_ids": ["synthetic"]}}
    class Session:
        request = successor_request
        binding = {"source_preparation": {"artifact_digest": "sha256:" + "1"*64}}
        def for_code(self, thscode):
            assert thscode == code
            return binding
    reached = []
    def capture(**kw):
        reached.append(kw["ticker"])
        raise once.TrialError("synthetic successor capture stop")
    def no_pre_capture_recheck(**kw):
        pytest.fail("successor context recheck ran before capture produced a context")
    monkeypatch.setattr(successor, "recheck", no_pre_capture_recheck)
    args.update(capture=capture, full_input=True, successor_session=Session())
    result = host.run_item(**args)
    assert reached == ["603353"]
    assert result["status"] == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE"
    assert not result["formal_research_started"] and calls == []


def test_cli_modes_remain_mutually_exclusive_and_successor_is_explicit_native_dispatch(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        host.main(["--source-run-id", "42", "--code-commit", "a"*40, "--output", str(tmp_path/"none"),
                   "--source-successor", "--recover-sources"])
    for k,v in {"GITHUB_REPOSITORY": once.REPO, "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": "a"*40, "GITHUB_EVENT_NAME": "schedule"}.items():
        monkeypatch.setenv(k,v)
    with pytest.raises(once.TrialError, match="explicit native dispatch"):
        host.main(["--source-run-id", "42", "--code-commit", "a"*40,
                   "--output", str(tmp_path/"none2"), "--source-successor"])


def test_workflow_has_one_explicit_successor_flag_not_a_second_executor():
    root = Path(__file__).parents[1]
    text = (root / ".github/workflows/stock-business-research.yml").read_text()
    assert text.count("source-successor:") == 1
    assert "--source-successor" in text
    assert text.count("research-stock-business:") == 1
    assert 'test ! \\( "$RECOVER_SOURCES" = true -a "$SOURCE_SUCCESSOR" = true \\)' in text
