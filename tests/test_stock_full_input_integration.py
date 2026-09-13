"""Original checked-source and pinned SDK composition; synthetic, NO live transport.

These tests must run in full repository CI, not be skipped for a missing SDK.
The SDK builds real request bytes, but the fake transport never sends them.
"""
import json
import socket

import pytest

from decision_kernel.research_funnel import PreResearchResult, QuickResearchResult
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_full_input as full
from test_stock_full_input import context


def test_original_checked_source_is_used_without_raising_shared_limits():
    raw = once.raw(context(text="完整正文和反证。" * 15000))
    assert full._raw(json.loads(raw)) == raw and len(raw) > identity.MAX_BYTES
    stored = full.pack(raw, ticker="300711")
    spec = once.source_ref("research_runs/byte-fixture/source.json", "a" * 40, stored, "MODEL_CONTEXT")
    calls = []
    def load(s): calls.append(s); return stored
    assert full.checked_unpack(spec, load, ticker="300711") == raw
    assert calls == [spec] and identity.MAX_BYTES == 512 * 1024
    assert len(stored) <= identity.MAX_BYTES
    with pytest.raises(ValueError): full.checked_unpack({**spec, "sha256": "0" * 64}, load, ticker="300711")
    with pytest.raises(ValueError): full.checked_unpack({**spec, "ref": "main"}, load, ticker="300711")
    with pytest.raises(ValueError): full.checked_unpack({**spec, "purpose": "PERMISSION"}, load, ticker="300711")
    with pytest.raises(ValueError): identity._checked_source(
        once.source_ref(spec["path"], "a" * 40, raw, "MODEL_CONTEXT"), lambda _: raw)


def test_original_model_call_limit_is_not_relaxed(tmp_path):
    usage = []
    with pytest.raises(once.TrialError, match="unsupported model request byte bound"):
        once.model_call("pre", {}, PreResearchResult, tmp_path, usage, max_prompt_bytes=full.REQUEST_BYTES)
    assert once.MAX_PROMPT_BYTES == 128 * 1024 and usage == [] and not list(tmp_path.iterdir())


@pytest.mark.parametrize("stage,output_type", [("PRE", PreResearchResult), ("QUICK", QuickResearchResult)])
def test_pinned_original_sdk_final_wire_is_checked_without_any_network(monkeypatch, capsys, stage, output_type):
    from openai import OpenAI, DefaultHttpxClient, APIConnectionError
    from openai.lib._parsing._responses import type_to_text_format_param
    def deny(*args, **kwargs): pytest.fail("test attempted real network")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    raw = once.raw(context(text="完整正文和反证。" * 15000))
    source = full.pack(raw, ticker="300711")
    spec = once.source_ref("research_runs/byte-fixture/source.json", "a" * 40, source, "MODEL_CONTEXT")
    decoded = full.checked_unpack(spec, lambda _: source, ticker="300711")
    ids = ["11111111-1111-4111-8111-111111111111"]
    # This is an SDK byte fixture, not a fabricated Funnel result or a live Pre/Quick.
    prompt = {"stage": stage, "public_context": json.loads(decoded), "evidence_ids": ids,
              "known_unknowns": ["SYNTHETIC BYTE TEST, NO RESEARCH EXECUTION"]}
    strict = type_to_text_format_param(once.admitted_output_type(output_type, ids))
    params = dict(model=once.MODEL, instructions=once.SYSTEM,
        input=[{"role": "user", "content": once.raw(prompt).decode()}],
        text={"format": strict}, tools=[], store=False, max_output_tokens=once.MAX_OUTPUT_TOKENS)
    gate = full.FinalRequestCheck.build(decoded, ticker="300711",
        expected_url=once.BASE_URL + "/responses", parameters={**params, "stream": True})
    receipt, delivered_to_fake = {}, []
    class NoNetwork:
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
        def close(self): pass
        def handle_request(self, request):
            assert receipt["request_bytes"] == len(request.content)
            delivered_to_fake.append(request.content)
            raise OSError("intentional fake transport stop; no request sent")
    with OpenAI(api_key="synthetic-not-a-secret", base_url=once.BASE_URL, max_retries=0,
        http_client=DefaultHttpxClient(transport=NoNetwork(), follow_redirects=False,
            trust_env=False, event_hooks={"request": [gate.hook(receipt)]})) as client:
        with pytest.raises(APIConnectionError):
            with client.responses.stream(**params) as stream:
                stream.get_final_response()
    assert len(delivered_to_fake) == 1
    assert 512 * 1024 < receipt["request_bytes"] <= full.REQUEST_BYTES
    actual = json.loads(delivered_to_fake[0])
    assert actual == {**params, "stream": True}
    assert once.raw(json.loads(actual["input"][0]["content"])["public_context"]) == raw
    with capsys.disabled():
        print("SYNTHETIC_SDK_FULL_INPUT_" + stage + "=" + json.dumps(receipt, sort_keys=True))
