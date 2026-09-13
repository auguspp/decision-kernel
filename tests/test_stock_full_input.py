"""Pure byte-contract tests. No repository, network, model or execution authority."""
import base64
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
import zlib

import pytest

from decision_kernel.runtime import stock_full_input as full


def context(ticker="300711", text="完整正文和反证。" * 100):
    return {"issuer_inventory": {"stock_code": ticker, "selected_ids": ["a", "b"],
                "checked_at": "2026-09-13T15:18:00Z"},
        "issuer_documents": [{"announcement_id": name, "page_count": 1,
            "retrieved_at": "2026-09-13T15:18:01Z", "pages": [{"page_number": 1, "text": text}]}
            for name in ["a", "b"]],
        "stock_observation": {"row": {"thscode": ticker + (".SH" if ticker[0] == "6" else ".SZ")}},
        "source_limitations": "SYNTHETIC BYTE FIXTURE, NOT RESEARCH OR SOURCE ACCEPTANCE"}


def parameters(raw, stage="PRE"):
    prompt = {"stage": stage, "public_context": json.loads(raw), "evidence_ids": ["fixture-not-admitted"]}
    return {"model": "synthetic-model", "instructions": "Synthetic instruction, not a live model call.",
        "input": [{"role": "user", "content": full._raw(prompt).decode()}],
        "text": {"format": {"type": "json_schema", "strict": True, "name": "Synthetic", "schema": {}}},
        "tools": [], "store": False, "max_output_tokens": 100, "stream": True}


@pytest.mark.parametrize("ticker", sorted(full.TICKERS))
def test_every_source_byte_round_trips_without_retiming(ticker):
    original = full._raw(context(ticker, "完整正文和反证。" * 15000))
    assert len(original) > full.STORED_BYTES
    stored = full.pack(original, ticker=ticker)
    assert len(stored) < full.STORED_BYTES
    assert full.unpack(stored, ticker=ticker) == original
    assert json.loads(full.unpack(stored, ticker=ticker)) == json.loads(original)


@pytest.mark.parametrize("defect", ["ticker", "version", "extra", "count-bool", "count-too-big",
    "count-small", "decoded-hash", "compressed-hash", "base64", "truncated", "trailing", "second-stream"])
def test_envelope_corruption_or_rehashed_bad_stream_rejected(defect):
    raw = full._raw(context())
    value = json.loads(full.pack(raw, ticker="300711"))
    if defect == "ticker": value["ticker"] = "603353"
    elif defect == "version": value["schema_version"] = True
    elif defect == "extra": value["permission"] = "invented"
    elif defect == "count-bool": value["decoded_bytes"] = True
    elif defect == "count-too-big": value["decoded_bytes"] = full.DECODED_BYTES + 1
    elif defect == "count-small": value["decoded_bytes"] -= 1
    elif defect == "decoded-hash": value["decoded_sha256"] = "0" * 64
    elif defect == "compressed-hash": value["compressed_sha256"] = "0" * 64
    elif defect == "base64": value["data"] += "!"
    else:
        data = base64.b64decode(value["data"])
        if defect == "truncated": data = data[:-1]
        elif defect == "trailing": data += b"trailing"
        else: data += zlib.compress(b"second stream")
        value["data"] = base64.b64encode(data).decode()
        value["compressed_sha256"] = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError): full.unpack(full._raw(value), ticker="300711")


@pytest.mark.parametrize("defect", ["missing-document", "duplicate", "page-number", "page-count-bool",
                                    "wrong-issuer", "wrong-observation"])
def test_mismatched_issuer_document_page_shape_not_packaged(defect):
    value = context()
    if defect == "missing-document": value["issuer_documents"].pop()
    elif defect == "duplicate": value["issuer_inventory"]["selected_ids"] = ["a", "a"]
    elif defect == "page-number": value["issuer_documents"][0]["pages"][0]["page_number"] = True
    elif defect == "page-count-bool": value["issuer_documents"][0]["page_count"] = True
    elif defect == "wrong-issuer": value["issuer_inventory"]["stock_code"] = "603353"
    else: value["stock_observation"]["row"]["thscode"] = "603353.SH"
    with pytest.raises(ValueError): full.pack(full._raw(value), ticker="300711")


def test_duplicate_nonfinite_noncanonical_and_scope_inputs_fail_closed():
    for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'[]']:
        with pytest.raises(ValueError): full._json(raw, full.DECODED_BYTES)
    raw = full._raw(context())
    with pytest.raises(ValueError): full.pack(raw + b" ", ticker="300711")
    with pytest.raises(ValueError): full.pack(raw, ticker="600184")
    with pytest.raises(ValueError): full.pack(raw, ticker="300183")
    with pytest.raises(ValueError): full.pack(b"x" * (full.DECODED_BYTES + 1), ticker="300711")
    with pytest.raises(ValueError): full.unpack(b"x" * (full.STORED_BYTES + 1), ticker="300711")


def test_decompression_is_bounded_before_output_allocation(monkeypatch):
    value = json.loads(full.pack(full._raw(context()), ticker="300711"))
    compressed = zlib.compress(b"x" * (full.DECODED_BYTES + 100))
    value.update(data=base64.b64encode(compressed).decode(), decoded_bytes=16,
                 compressed_sha256=hashlib.sha256(compressed).hexdigest())
    original = zlib.decompressobj
    observed = []
    class Decoder:
        def __init__(self): self.inner = original()
        def decompress(self, data, max_length):
            observed.append(max_length)
            return self.inner.decompress(data, max_length)
        def __getattr__(self, key): return getattr(self.inner, key)
    monkeypatch.setattr(zlib, "decompressobj", Decoder)
    with pytest.raises(ValueError): full.unpack(full._raw(value), ticker="300711")
    assert observed == [17]


@pytest.mark.parametrize("stage", ["PRE", "QUICK"])
def test_hook_checks_final_compact_wire_and_rejects_repeated_send(stage):
    raw = full._raw(context())
    params = parameters(raw, stage)
    original = deepcopy(params)
    check = full.FinalRequestCheck.build(raw, ticker="300711",
        expected_url="https://example.invalid/v1/responses", parameters=params)
    params["instructions"] = "mutated caller dictionary"
    wire = json.dumps(original, ensure_ascii=False, separators=(",", ":")).encode()
    req = SimpleNamespace(method="POST", url="https://example.invalid/v1/responses", content=wire)
    receipt = {}; hook = check.hook(receipt); hook(req)
    assert receipt["decoded_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["request_bytes"] == len(wire)
    assert receipt["request_sha256"] == hashlib.sha256(wire).hexdigest()
    assert "NOT_DELIVERY" in receipt["meaning"]
    with pytest.raises(ValueError, match="repeated send"): hook(req)


@pytest.mark.parametrize("defect", ["compressed-context", "clipped-context", "store", "tools", "strict", "bool-tokens"])
def test_bad_prepared_request_never_gets_a_hook(defect):
    raw = full._raw(context()); params = parameters(raw)
    if defect in {"compressed-context", "clipped-context"}:
        p = json.loads(params["input"][0]["content"])
        if defect == "compressed-context": p["public_context"] = json.loads(full.pack(raw, ticker="300711"))
        else: p["public_context"]["issuer_documents"][0]["pages"][0]["text"] = "summary"
        params["input"][0]["content"] = full._raw(p).decode()
    elif defect == "store": params["store"] = True
    elif defect == "tools": params["tools"] = [{"type": "web_search"}]
    elif defect == "strict": params["text"]["format"]["strict"] = False
    else: params["max_output_tokens"] = True
    with pytest.raises(ValueError):
        full.FinalRequestCheck.build(raw, ticker="300711",
            expected_url="https://example.invalid/v1/responses", parameters=params)


@pytest.mark.parametrize("defect", ["endpoint", "method", "body", "extra", "wire-too-large"])
def test_actual_transport_differences_block_before_delivery(defect):
    raw = full._raw(context()); params = parameters(raw)
    gate = full.FinalRequestCheck.build(raw, ticker="300711",
        expected_url="https://example.invalid/v1/responses", parameters=params)
    req = SimpleNamespace(method="POST", url=gate.expected_url, content=full._raw(params))
    if defect == "endpoint": req.url += "?redirect=elsewhere"
    elif defect == "method": req.method = "GET"
    elif defect == "body":
        params["instructions"] = "wrong system"
        req.content = full._raw(params)
    elif defect == "extra":
        params["unknown"] = True
        req.content = full._raw(params)
    else: req.content += b" " * full.REQUEST_BYTES
    receipt = {}
    with pytest.raises(ValueError): gate.hook(receipt)(req)
    assert not receipt
