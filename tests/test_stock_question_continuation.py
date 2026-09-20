"""Offline composition tests for reviewed-question technical continuation.

The predecessor is generated through the real question host with synthetic Git/model
boundaries. No network or company material is used.
"""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_continuation as cont
from decision_kernel.runtime import stock_question_host as question
from decision_kernel.runtime import stock_research_intake as intake
from test_saved_research_once import pre, quick
from test_stock_question_host import setup_question


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("continuation tests must not access networking")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


class PermissionDeniedError(RuntimeError):
    pass


def setup_continuation(tmp_path, monkeypatch, *, route="WAIT_FOR_TRIGGER"):
    qargs, api, base_request, q, context, pf, _, writes, parent_prefix = setup_question(
        tmp_path, monkeypatch)
    run_id = 77
    monkeypatch.setenv("GITHUB_RUN_ID", str(run_id))

    # Generate the exact retained technical gap through the original question host.
    def failed_pre(stage, prompt, model, output, usage):
        assert stage == "pre"
        usage.append({
            "stage": "pre", "status": "FAILED", "phase": "RESPONSE",
            "error_type": "PermissionDeniedError", "requested_model": "gpt-6-astra",
            "response_received": False, "output_text_retained": False,
        })
        raise PermissionDeniedError("synthetic provider denial")

    qargs["call"] = failed_pre
    first = question.run_question(**qargs)
    assert first["status"] == "EXECUTION_GAP", first
    pred_work = api.heads[intake.WORK_REF]
    saved = api.files[pred_work]
    assert parent_prefix + "pre.json" not in saved
    assert parent_prefix + "funnel.json" not in saved

    artifact = {
        "id": 78,
        "name": "stock-business-research-77-1",
        "size_in_bytes": 12345,
        "digest": "sha256:" + "8" * 64,
        "head_sha": qargs["code"],
    }
    original_get = api.get

    def get(path):
        if path == f"actions/runs/{run_id}":
            return {
                "id": run_id,
                "path": ".github/workflows/stock-business-research.yml",
                "event": "workflow_dispatch",
                "run_attempt": 1,
                "head_branch": "main",
                "head_sha": qargs["code"],
                "status": "completed",
                "conclusion": "failure",
            }
        if path == f"actions/runs/{run_id}/jobs?per_page=100":
            jobs = [
                {"name": "research-stock-business", "conclusion": "failure"},
                {"name": "prepare-stock-sources", "conclusion": "skipped"},
            ]
            return {"total_count": len(jobs), "jobs": jobs}
        if path == f"actions/runs/{run_id}/artifacts?per_page=100":
            a = {**artifact, "expired": False,
                 "workflow_run": {"head_sha": qargs["code"]}}
            return {"total_count": 1, "artifacts": [a]}
        return original_get(path)

    api.get = get
    predecessor_sources = {}
    for key, (filename, purpose) in cont.PREDECESSOR_FILES.items():
        raw = saved[parent_prefix + filename]
        predecessor_sources[key] = once.source_ref(
            parent_prefix + filename, pred_work, raw, purpose)

    request = {
        "schema_version": 1,
        "enabled": True,
        "mode": cont.MODE,
        "permission": base_request["permission"],
        "question_source": base_request["question_source"],
        "context_source": base_request["context_source"],
        "preflight_source": base_request["preflight_source"],
        "approved_egress_hash": None,
        "predecessor": {
            "run_id": run_id,
            "artifact": artifact,
            "work_commit": pred_work,
            "execution_id": question.question_execution(
                q["security_id"], q["question_id"])[0],
            "root": parent_prefix,
            "sources": predecessor_sources,
        },
    }
    _, packet, discovery, ctx, _, predecessor = cont._inputs(
        api=api, code=qargs["code"], request=request, clock=qargs["clock"])
    request["approved_egress_hash"] = cont.egress_hash(
        packet, discovery, ctx)
    api.files[qargs["code"]][cont.REQUEST] = once.raw(request)

    calls = []

    def model_call(stage, prompt, model, output, usage):
        calls.append(stage)
        assert "TECHNICAL_CONTINUATION_OF:" + predecessor["parent_execution_id"] in prompt["known_unknowns"]
        if stage == "pre":
            return pre(prompt, route)
        return quick(prompt)

    args = {
        "api": api,
        "code": qargs["code"],
        "output": tmp_path / "continuation",
        "clock": qargs["clock"],
        "call": model_call,
    }
    return args, api, request, q, context, pf, calls, writes, parent_prefix, predecessor


@pytest.mark.parametrize("route,stages", [
    ("WAIT_FOR_TRIGGER", ["pre"]),
    ("STOP", ["pre"]),
    ("CONTINUE_TO_QUICK", ["pre", "quick"]),
])
def test_exact_technical_gap_continues_once_through_original_funnel(
        tmp_path, monkeypatch, route, stages):
    args, api, _, _, _, _, calls, _, parent_prefix, pred = setup_continuation(
        tmp_path, monkeypatch, route=route)
    result = cont.run_continuation(**args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert calls == stages
    child = pred["child_prefix"]
    saved = api.files[api.heads[intake.WORK_REF]]
    for name in ("prepare.json", "source.json", "input.json", "launch.json",
                 "admission.json", "candidate.json", "receipt.json",
                 "validation.json", "funnel.json", "host-receipt.json", "README.md"):
        assert child + name in saved
    # Parent is preserved byte-for-byte and never reopened.
    assert saved[parent_prefix + "host-receipt.json"] == api.files[
        request_ref(args, api, pred)][parent_prefix + "host-receipt.json"]
    receipt = json.loads(saved[child + "receipt.json"])
    assert receipt["model_or_executor"] == cont.MODEL_OR_EXECUTOR
    targets = [e["target"] for e in receipt["tool_events"]]
    assert cont.PROVIDER_EVENT_PREFIX + ":PRE" in targets
    if route == "CONTINUE_TO_QUICK":
        assert cont.PROVIDER_EVENT_PREFIX + ":QUICK" in targets
    launch = json.loads(saved[child + "launch.json"])
    assert launch["provider"]["name"] == cont.PROVIDER
    assert launch["provider"]["model"] == once.DEEPSEEK_MODEL
    assert launch["predecessor"]["run_id"] == 77
    assert result["investment_authority"] == "NONE"
    assert result["semantic_acceptance"] == "NOT_ESTABLISHED"


def request_ref(args, api, pred):
    # All predecessor sources are pinned to one immutable work commit.
    return args["api"].files and next(
        spec["ref"] for spec in pred["source_refs"]
        if spec["path"].endswith("host-receipt.json"))


def test_second_invocation_reuses_child_without_model_or_write(
        tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, writes, _, pred = setup_continuation(
        tmp_path, monkeypatch, route="STOP")
    first = cont.run_continuation(**args)
    assert first["status"] == "VALIDATED_FUNNEL_RESULT"
    before_calls, before_writes = len(calls), len(writes)
    before = deepcopy(api.files[api.heads[intake.WORK_REF]])
    args["output"] = tmp_path / "second"
    second = cont.run_continuation(**args)
    assert second["status"] == "EXISTING_QUESTION_CONTINUATION_REUSED_NO_EXECUTION"
    assert second["existing_paths"]
    assert all(p.startswith(pred["child_prefix"]) for p in second["existing_paths"])
    assert len(calls) == before_calls and len(writes) == before_writes
    assert api.files[api.heads[intake.WORK_REF]] == before


@pytest.mark.parametrize("damage", [
    "permission", "egress", "main", "stale-preflight",
    "predecessor-host", "run", "artifact",
])
def test_changed_authority_source_or_predecessor_never_calls_model(
        tmp_path, monkeypatch, damage):
    args, api, request, _, _, pf, calls, writes, parent_prefix, pred = setup_continuation(
        tmp_path, monkeypatch, route="STOP")
    if damage == "permission":
        api.comment["body"] = "revoked"
    elif damage == "egress":
        request["approved_egress_hash"] = "0" * 64
        api.files[args["code"]][cont.REQUEST] = once.raw(request)
    elif damage == "main":
        api.heads["main"] = "0" * 40
    elif damage == "stale-preflight":
        # Advance beyond the synthetic preflight validity window.
        old_clock = args["clock"]
        args["clock"] = lambda: (
            reading.clock(old_clock()) + timedelta(hours=2)).isoformat()
    elif damage == "predecessor-host":
        ref = request["predecessor"]["work_commit"]
        path = parent_prefix + "host-receipt.json"
        api.files[ref][path] += b" "
    elif damage == "run":
        old_get = api.get
        def wrong_run(path):
            value = old_get(path)
            if path == "actions/runs/77":
                value = {**value, "conclusion": "success"}
            return value
        api.get = wrong_run
    else:
        old_get = api.get
        def wrong_artifact(path):
            value = old_get(path)
            if path == "actions/runs/77/artifacts?per_page=100":
                value = deepcopy(value)
                value["artifacts"][0]["digest"] = "sha256:" + "9" * 64
            return value
        api.get = wrong_artifact
    before = len(writes)
    result = cont.run_continuation(**args)
    assert result["status"] == "NOT_EXECUTED", result
    assert not result["formal_research_started"]
    assert not calls and len(writes) == before


def test_continuation_identity_is_fixed_child_of_same_question_root():
    parent_id, parent = question.question_execution("SZSE:300711", "funding")
    eid, prefix = cont.execution("SZSE:300711", "funding")
    assert eid == parent_id + "-technical-continuation-v1"
    assert prefix == parent + cont.CHILD
    assert prefix.startswith(parent)


def test_deepseek_egress_contract_uses_accepted_wire_shape(
        tmp_path, monkeypatch):
    args, api, request, _, _, _, _, _, _, _ = setup_continuation(
        tmp_path, monkeypatch)
    _, packet, discovery, context, _, _ = cont._inputs(
        api=api, code=args["code"], request=request, clock=args["clock"])
    prompt = once.pre_prompt(packet, discovery, context)
    _, _, fmt, params = cont._deepseek_request(prompt, once.PreResearchResult)
    assert set(fmt) == {"type", "name", "schema"}
    assert "strict" not in fmt
    assert params["model"] == "deepseek-flash"
    assert params["reasoning"] == {"effort": "none"}
    assert params["tools"] == [] and params["store"] is False
    assert cont.egress_hash(packet, discovery, context) == request["approved_egress_hash"]


def test_default_request_disabled_and_workflow_manual_only():
    root = Path(__file__).parents[1]
    request = json.loads((root / cont.REQUEST).read_text())
    assert request == {
        "approved_egress_hash": None,
        "context_source": None,
        "enabled": False,
        "mode": cont.MODE,
        "permission": None,
        "predecessor": None,
        "preflight_source": None,
        "question_source": None,
        "schema_version": 1,
    }
    workflow = (root / ".github/workflows/stock-business-research.yml").read_text()
    assert "reviewed-question-continuation:" in workflow
    assert "decision_kernel.runtime.stock_question_continuation" in workflow
    assert "secrets.DEEPSEEK_API_KEY" in workflow
    assert "inputs.reviewed-question-continuation && !inputs.reviewed-question" in workflow
    assert "!inputs.reviewed-question-continuation && !inputs.prepare-sources" in workflow


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_run"])
def test_cli_rejects_nonmanual_event_before_api(
        tmp_path, monkeypatch, event):
    monkeypatch.setenv("GITHUB_REPOSITORY", once.REPO)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic")
    with pytest.raises(once.TrialError):
        cont.main(["--code-commit", "a" * 40,
                   "--output", str(tmp_path / "out")])
    assert not (tmp_path / "out").exists()


def test_research_provider_labels_default_and_deepseek_are_distinct(
        tmp_path):
    from test_saved_research_once import fixture
    packet, discovery, context = fixture()

    def stop(stage, prompt, model, out, usage):
        return pre(prompt, "STOP")

    (tmp_path / "old").mkdir()
    _, _, _ = once.research(
        packet, discovery, context, tmp_path / "old", call=stop)
    old = json.loads((tmp_path / "old" / "candidate-before-validation.json").read_text())
    assert old["receipt"]["model_or_executor"] == (
        "trusted Python + Sub2API Responses / gpt-6-astra")
    assert any(e["target"] == "SUB2API_RESPONSES:PRE"
               for e in old["receipt"]["tool_events"])

    (tmp_path / "new").mkdir()
    _, _, _ = once.research(
        packet, discovery, context, tmp_path / "new", call=stop,
        provider_event_prefix=cont.PROVIDER_EVENT_PREFIX,
        model_or_executor=cont.MODEL_OR_EXECUTOR)
    new = json.loads((tmp_path / "new" / "candidate-before-validation.json").read_text())
    assert new["receipt"]["model_or_executor"] == cont.MODEL_OR_EXECUTOR
    assert any(e["target"] == cont.PROVIDER_EVENT_PREFIX + ":PRE"
               for e in new["receipt"]["tool_events"])
