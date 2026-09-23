"""One actual pinned SDK stream over mock HTTP; all inputs/results synthetic."""
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import socket

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime import reviewed_question_input as reviewed
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from decision_kernel.research_funnel import DiscoveryInput
from test_single_quick_execution import case, assessment
from test_reviewed_full_input import simple_context


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("live networking forbidden")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def full_case(size=600_000):
    p, d, _ = case(); context = simple_context(size)
    stored = full.pack(once.raw(context), ticker=p.ticker)
    old = p.source_refs[0]
    spec = once.source_ref(old.path, old.ref, stored, "MODEL_CONTEXT")
    seed = p.seed_evidence_artifacts[0].model_copy(update={"source_locator": once.locator(spec),
        "content_hash": spec["sha256"], "raw_storage_ref": once.locator(spec)})
    p = ExternalResearchInputPacket.model_validate({**p.model_dump(mode="json"),
        "security_id": intake.security(p.case_id), "source_lane": reviewed.LANE,
        "source_refs": [spec], "seed_evidence_artifacts": [seed.model_dump(mode="json")]})
    d = DiscoveryInput.model_validate({**d.model_dump(mode="json"),
        "security_id": p.security_id, "source_lane": p.source_lane,
        "source_lineage": [{"evidence_artifact_id": str(seed.id), "source_locator": seed.source_locator,
                            "available_at": seed.available_at.isoformat()}]})
    return p, d, context, full.ReviewedFullContext.load(spec, lambda _: stored, ticker=p.ticker)


def sse(text):
    part = {"type": "output_text", "text": text, "annotations": []}
    item = {"id": "msg_single", "type": "message", "role": "assistant", "status": "completed", "content": [part]}
    final = {"id": "resp_single", "object": "response", "created_at": 1789056000, "status": "completed",
        "model": once.DEEPSEEK_MODEL, "output": [item], "parallel_tool_calls": False,
        "tool_choice": "auto", "tools": [], "error": None, "incomplete_details": None,
        "usage": {"input_tokens": 10, "input_tokens_details": {"cached_tokens": 0}, "output_tokens": 2,
                  "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 12}}
    events = [
        {"type": "response.created", "response": {**final, "status": "in_progress", "output": []}},
        {"type": "response.output_item.added", "output_index": 0, "item": {**item, "status": "in_progress", "content": []}},
        {"type": "response.content_part.added", "output_index": 0, "content_index": 0, "item_id": "msg_single", "part": {**part, "text": ""}},
        {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "item_id": "msg_single", "delta": text},
        {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "item_id": "msg_single", "text": text},
        {"type": "response.content_part.done", "output_index": 0, "content_index": 0, "item_id": "msg_single", "part": part},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": final}]
    return "".join("data: " + json.dumps({**e, "sequence_number": i}) + "\n\n" for i, e in enumerate(events)).encode()


@pytest.mark.parametrize("route", ["STOP", "WAIT_FOR_TRIGGER", "FULL_CANDIDATE", "INVALID"])
def test_complete_input_single_sdk_call_raw_retention_and_reading(tmp_path, monkeypatch, route):
    import openai
    import httpx2 as httpx
    p, d, context, bound = full_case()
    old_hash = bound.egress_hash(p, d, context)
    bound = bound.preview(p, d, context)  # actual SDK construction, forbidden transport
    assert bound.single_quick_prompt_sha256 and bound.single_quick_request_sha256
    assert bound.pre_prompt_sha256 is None and bound.pre_request_sha256 is None
    assert bound.egress_hash(p, d, context) == old_hash
    prompt = once.initial_prompt(p, d, context, bound_context=bound)
    text = '{"route":' if route == "INVALID" else assessment(prompt, route).model_dump_json()
    seen = []
    def transport(request):
        body = json.loads(request.content); seen.append(body)
        assert str(request.url) == once.DEEPSEEK_BASE_URL + "/responses"
        assert once.sha(request.content) == bound.single_quick_request_sha256
        sent = json.loads(body["input"][0]["content"])
        assert sent["public_context"] == context
        assert sent["public_context"]["issuer_documents"][0]["pages"][-1]["text"].endswith("counterevidence")
        assert not {"pre_research", "pre_research_hash"} & set(sent)
        assert body["model"] == once.DEEPSEEK_MODEL and body["reasoning"] == {"effort": "none"}
        assert body["max_output_tokens"] == 6000 and body["tools"] == [] and body["store"] is False
        assert "strict" not in body["text"]["format"]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse(text))
    monkeypatch.setattr(openai, "DefaultHttpxClient", lambda **kw: httpx.Client(transport=httpx.MockTransport(transport), **kw))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-credential-never-live")
    call = partial(once.model_call, bound_context=bound, base_url=once.DEEPSEEK_BASE_URL,
        model=once.DEEPSEEK_MODEL, provider="DEEPSEEK_OFFICIAL", api_key_env="DEEPSEEK_API_KEY",
        extra_parameters={"reasoning": {"effort": "none"}})
    candidate, checked, usage = once.research(p, d, context, tmp_path, call=call,
        bound_context=bound, provider_event_prefix="DEEPSEEK_RESPONSES",
        model_or_executor="synthetic mock HTTP + original SDK")
    assert len(seen) == len(usage) == 1 and usage[0]["stage"] == "quick"
    assert usage[0]["pre_send"]["request_sha256"] == bound.single_quick_request_sha256
    assert usage[0]["usage"]["total_tokens"] == 12 and usage[0]["output_text_retained"]
    assert (tmp_path / "quick-model-output.txt").read_text() == text
    view = single.reading_view(once.raw(p), once.raw(candidate))
    assert view["pre_state"] == "NOT_APPLICABLE" and view["human_attention_authority"] == "NONE"
    assert view["status"] == ("EXECUTION_GAP" if route == "INVALID" else "VALIDATED_QUICK_RESULT")
    assert not list(tmp_path.glob("pre*")) and candidate.receipt.technical_retries_used == 0
    assert "synthetic-credential-never-live" not in "\n".join(x.read_text() for x in tmp_path.iterdir())


def test_old_egress_and_pre_preview_cannot_authorize_single_quick():
    p, d, context, bound = full_case(100)
    legacy = p.model_copy(update={"method_version": "research-funnel-v1", "prompt_version": "test"})
    old = bound.preview(legacy, d, context)
    assert old.pre_request_sha256 and old.single_quick_request_sha256 is None
    assert old.egress_hash(legacy, d, context) != old.egress_hash(p, d, context)
    prompt = once.initial_prompt(p, d, context)
    with pytest.raises(ValueError, match="SINGLE_PREVIEW_REQUIRED"):
        old.send_hook("quick", prompt, single.QuickAssessment, full._parameters(prompt, single.QuickAssessment), {})
    new = bound.preview(p, d, context)
    pre_prompt = once.pre_prompt(legacy, d, context)
    with pytest.raises(ValueError, match="LEGACY_PREVIEW_REQUIRED"):
        new.send_hook("pre", pre_prompt, once.PreResearchResult, full._parameters(pre_prompt, once.PreResearchResult), {})


@pytest.mark.parametrize("damage", ["prompt", "preview-digest", "model", "destination", "repeat"])
def test_single_actual_send_check_fails_closed(damage):
    import httpx2 as httpx
    p, d, context, bound = full_case(100); bound = bound.preview(p, d, context)
    prompt = once.initial_prompt(p, d, context)
    parameters = full._parameters(prompt, single.QuickAssessment)
    if damage == "prompt": prompt["question"] += " changed"
    if damage == "preview-digest": bound = replace(bound, single_quick_request_sha256="0" * 64)
    if damage == "model": parameters["model"] = "unapproved"
    if damage in {"prompt", "model"}:
        with pytest.raises(ValueError): bound.send_hook("quick", prompt, single.QuickAssessment, parameters, {})
        return
    hook = bound.send_hook("quick", prompt, single.QuickAssessment, parameters, {})
    url = "https://invalid.example/responses" if damage == "destination" else once.DEEPSEEK_BASE_URL + "/responses"
    request = httpx.Request("POST", url, json={**parameters, "stream": True})
    if damage == "repeat":
        hook(request)
    with pytest.raises(ValueError): hook(request)
