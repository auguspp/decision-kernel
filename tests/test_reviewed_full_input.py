"""Full Industry input through the original host; synthetic Git/model edges only."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import socket
from uuid import NAMESPACE_URL, uuid5
import zlib

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_full_input as legacy
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import industry_daily_question as industry
from decision_kernel.runtime import stock_research_intake as intake
from test_industry_daily_question import setup_industry
from test_stock_daily_question import _put


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Full-input tests cannot use live networking")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def simple_context(size=500_000):
    return {"issuer_documents": [{"announcement_id": "123", "page_count": 2,
        "pages": [{"page_number": 1, "text": "Synthetic original full first page"},
                  {"page_number": 2, "text": "Synthetic final page, including counterevidence"}]}],
        "source_limitations": "SYNTHETIC NOT RESEARCH. " + "x" * size}


def seal_full(case):
    """Reseal synthetic bytes and every dependent reference, without inventing a run."""
    raw = once.raw(case.context)
    stored = full.pack(raw, ticker=case.q["ticker"])
    old = case.request["context_source"]
    source = once.source_ref(old["path"], old["ref"], stored, "MODEL_CONTEXT")
    case.api.files[source["ref"]][source["path"]] = stored
    case.request["context_source"] = source
    eid = host.question_execution(case.q["security_id"], case.q["question_id"])[0]
    case.pf["seed_publications"] = [{"evidence_id": str(uuid5(NAMESPACE_URL, eid + ":" + source["sha256"])),
                                   "kind": "GIT_COMMIT", "source": source}]
    qs = _put(case, "question_source", case.q)
    _put(case, "preflight_source", case.pf)
    case.review.update(reading_source=case.q["reading_source"], question_source=qs)
    case.review["economic_exposure"]["context_source"] = source
    _put(case, "batch_review_source", case.review)
    case.custody["context"] = source
    _put(case, "source_custody_source", case.custody)
    case.api.files[case.args["code"]][daily.REQUEST] = once.raw(case.request)
    return stored


@pytest.mark.parametrize("size", [1, 500_000, 1_000_000])
def test_shared_codec_preserves_every_original_byte(size):
    raw = once.raw(simple_context(size))
    saved = full.pack(raw, ticker="600362")
    assert len(saved) <= legacy.STORED_BYTES
    assert full.unpack(saved, ticker="600362") == raw
    assert json.loads(saved)["policy"] == full.POLICY
    assert legacy.TICKERS == frozenset({"603353", "300711"})
    with pytest.raises(ValueError): legacy.unpack(saved, ticker="600362")
    with pytest.raises(ValueError): legacy.pack(raw, ticker="600362")


@pytest.mark.parametrize("damage", ["ticker", "policy", "bytes", "hash", "compressed-hash", "tail", "concat", "truncated", "bomb"])
def test_damaged_or_wrong_scope_envelope_is_rejected(damage):
    saved = json.loads(full.pack(once.raw(simple_context(100)), ticker="600362"))
    if damage == "ticker": saved["ticker"] = "300711"
    elif damage == "policy": saved["policy"] = legacy.POLICY
    elif damage == "bytes": saved["decoded_bytes"] += 1
    elif damage == "hash": saved["decoded_sha256"] = "0" * 64
    elif damage == "compressed-hash": saved["compressed_sha256"] = "0" * 64
    else:
        data = base64.b64decode(saved["data"])
        if damage == "tail": data += b"tail"
        elif damage == "concat": data += zlib.compress(b"{}")
        elif damage == "truncated": data = data[:-2]
        else: data = zlib.compress(b"x" * (legacy.DECODED_BYTES + 1))
        saved.update(data=base64.b64encode(data).decode(), compressed_sha256=once.sha(data))
    with pytest.raises((ValueError, zlib.error)):
        full.unpack(once.raw(saved), ticker="600362")


@pytest.mark.parametrize("damage", ["missing-page", "wrong-order", "empty-page", "too-many-pages", "oversized"])
def test_complete_input_never_means_partial_or_unbounded_input(damage):
    context = simple_context(100)
    doc = context["issuer_documents"][0]
    if damage == "missing-page": doc["pages"].pop()
    elif damage == "wrong-order": doc["pages"].reverse()
    elif damage == "empty-page": doc["pages"][-1]["text"] = ""
    elif damage == "too-many-pages": doc["page_count"] = 501
    else: context["source_limitations"] = "x" * legacy.DECODED_BYTES
    with pytest.raises(ValueError): full.pack(once.raw(context), ticker="600362")


@pytest.mark.parametrize("route,stages", [("WAIT_FOR_TRIGGER", ["pre"]), ("STOP", ["pre"]),
                                         ("CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_large_input_crosses_original_industry_host_and_retains_compressed_source(tmp_path, monkeypatch, route, stages):
    c = setup_industry(tmp_path, monkeypatch, route)
    c.context["source_limitations"] += " SYNTHETIC full scope including counterevidence." * 13000
    stored = seal_full(c)
    original, prompts = c.args["call"], []
    def call(stage, prompt, *args):
        prompts.append(deepcopy(prompt))
        return original(stage, prompt, *args)
    c.args["call"] = call
    result = host.run_question(**c.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert c.calls == stages and len(once.raw(c.context)) > 512 * 1024
    assert all(p["public_context"] == c.context for p in prompts)
    assert result["full_input"]["policy"] == full.POLICY
    assert result["full_input"]["pre_request_sha256"]
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    assert saved[c.prefix + "source.json"] == stored
    assert full.unpack(saved[c.prefix + "source.json"], ticker=c.q["ticker"]) == once.raw(c.context)
    assert json.loads(saved[daily.PREFIX + "slots/01/prepare.json"])["policy"] == daily.POLICY
    before = len(c.writes)
    repeated = host.run_question(**{**c.args, "output": tmp_path / "second"})
    assert repeated["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", repeated
    assert len(c.writes) == before and c.calls == stages


@pytest.mark.parametrize("damage", ["old-permission", "wrong-envelope-ticker", "changed-source", "unreadable-pdf"])
def test_invalid_large_input_has_no_reservation_or_model_call(tmp_path, monkeypatch, damage):
    c = setup_industry(tmp_path, monkeypatch)
    c.context["source_limitations"] += "x" * 550_000
    seal_full(c)
    cs = c.request["context_source"]
    if damage == "old-permission":
        c.request["permission"] = daily.PERMISSION
        c.api.files[c.args["code"]][daily.REQUEST] = once.raw(c.request)
    elif damage == "wrong-envelope-ticker":
        value = json.loads(c.api.files[cs["ref"]][cs["path"]]); value["ticker"] = "600362"
        raw = once.raw(value); c.api.files[cs["ref"]][cs["path"]] = raw
        c.request["context_source"] = once.source_ref(cs["path"], cs["ref"], raw, "MODEL_CONTEXT")
        c.api.files[c.args["code"]][daily.REQUEST] = once.raw(c.request)
    elif damage == "changed-source": c.api.files[cs["ref"]][cs["path"]] += b"changed"
    else:
        pdf = c.custody["documents"][0]["pdf_source"]
        c.api.files[pdf["ref"]][pdf["path"]] = b"not a PDF"
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert c.calls == [] and c.writes == [] and not result["formal_research_started"]


@pytest.mark.parametrize("success", [True, False])
def test_latest_inventory_is_still_required_not_downgraded_to_static(tmp_path, monkeypatch, success):
    c = setup_industry(tmp_path, monkeypatch)
    c.context["source_limitations"] += "x" * 550_000
    cid, query = "LATEST_UPDATE_CHECK", "synthetic exact issuer update query"
    declaration = deepcopy(c.q["required_classes"][0])
    declaration.update(id=cid, mode="LATEST_INVENTORY", planned_queries=[query])
    c.q["required_classes"].append(declaration)
    c.pf["required_classes"].append({"id": cid, "mode": "LATEST_INVENTORY", "body_ids": [], "inventory_id": "updates"})
    c.pf["inventories"] = [{"id": "updates", "class_id": cid, "started_at": c.pf["started_at"],
        "finished_at": c.pf["finished_at"], "planned_queries": [query], "query_events": [{"query": query,
            "status": "SUCCEEDED" if success else "FAILED", "tool_reference": "SYNTHETIC OFFLINE QUERY",
            "checked_at": c.pf["finished_at"]}], "leads": []}]
    c.pf["limits"]["max_queries"] = 1
    seal_full(c)
    result = host.run_question(**c.args)
    assert result["status"] == ("VALIDATED_FUNNEL_RESULT" if success else "NOT_EXECUTED"), result
    if not success: assert c.calls == [] and c.writes == []


@pytest.mark.parametrize("stage,output_type", [("PRE", once.PreResearchResult), ("QUICK", once.QuickResearchResult)])
def test_actual_deepseek_sdk_wire_is_plain_and_checked_before_fake_transport(stage, output_type):
    from openai import OpenAI, DefaultHttpxClient, APIConnectionError
    context = simple_context(600_000)
    stored = full.pack(once.raw(context), ticker="600362")
    spec = once.source_ref("research_runs/synthetic-full/source.json", "a" * 40, stored, "MODEL_CONTEXT")
    bound = full.ReviewedFullContext.load(spec, lambda _: stored, ticker="600362")
    prompt = {"stage": stage, "public_context": context, "evidence_ids": ["11111111-1111-4111-8111-111111111111"]}
    parameters = full._parameters(prompt, output_type)
    receipt, seen = {}, []
    gate = bound.request_check(stage.lower(), prompt, output_type, parameters).hook(receipt)
    class NoNetwork:
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
        def close(self): pass
        def handle_request(self, request):
            assert receipt["request_sha256"] == once.sha(request.content)
            seen.append(request.content)
            raise OSError("Intentional synthetic transport stop")
    with OpenAI(api_key="synthetic-not-a-secret", base_url=once.DEEPSEEK_BASE_URL, max_retries=0,
        http_client=DefaultHttpxClient(transport=NoNetwork(), follow_redirects=False, trust_env=False,
                                       event_hooks={"request": [gate]})) as client:
        with pytest.raises(APIConnectionError):
            with client.responses.stream(**parameters) as stream: stream.get_final_response()
    assert len(seen) == 1 and 512 * 1024 < receipt["request_bytes"] <= legacy.REQUEST_BYTES
    assert receipt["policy"] == full.POLICY
    actual = json.loads(seen[0])
    assert actual == {**parameters, "stream": True}
    assert json.loads(actual["input"][0]["content"])["public_context"] == context
    assert actual["reasoning"] == {"effort": "none"} and "strict" not in actual["text"]["format"]


@pytest.mark.parametrize("damage", ["destination", "model", "body", "second-send"])
def test_original_final_request_hook_rejects_mutation(damage):
    import httpx
    context = simple_context(100)
    stored = full.pack(once.raw(context), ticker="600362")
    spec = once.source_ref("research_runs/synthetic-full/source.json", "a" * 40, stored, "MODEL_CONTEXT")
    bound = full.ReviewedFullContext.load(spec, lambda _: stored, ticker="600362")
    prompt = {"stage": "PRE", "public_context": context, "evidence_ids": ["11111111-1111-4111-8111-111111111111"]}
    params = full._parameters(prompt, once.PreResearchResult)
    hook = bound.request_check("pre", prompt, once.PreResearchResult, params).hook({})
    wire, url = {**params, "stream": True}, once.DEEPSEEK_BASE_URL + "/responses"
    if damage == "destination": url = "https://invalid.example/responses"
    elif damage == "model": wire["model"] = "other-model"
    elif damage == "body": wire["input"] = []
    request = httpx.Request("POST", url, content=once.raw(wire))
    if damage == "second-send": hook(request)
    with pytest.raises(ValueError): hook(request)
