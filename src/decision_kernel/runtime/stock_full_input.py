"""Lossless Stock input representation and a composable pre-send check, NOT a host.

No source acquisition, model call, permission, execution identity or persistence.
The original host must still do source/admission/clock checks and conditional
Funnel routing. This module is not activated by the production workflow.
"""
from __future__ import annotations

import base64
import hashlib
import json
import zlib
from dataclasses import dataclass

POLICY = "STOCK_FULL_INPUT_ZLIB_V1"
TICKERS = frozenset({"603353", "300711"})
STORED_BYTES = 512 * 1024
DECODED_BYTES = 1536 * 1024
REQUEST_BYTES = 2 * 1024 * 1024


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _raw(value):
    # Same JSON byte contract as saved_research_once.raw for JSON-only values.
    # Kept dependency-free so byte checks do not import the Research executor.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _json(raw, limit):
    _require(type(raw) is bytes and 0 < len(raw) <= limit, "full-input byte bound")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "full-input duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("full-input nonfinite JSON value")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=constant)
    _require(type(value) is dict, "full-input requires JSON object")
    return value


def _context(raw, ticker):
    _require(ticker in TICKERS, "full-input ticker outside repair scope")
    value = _json(raw, DECODED_BYTES)
    _require(_raw(value) == raw, "full-input context serialization differs")
    inventory, docs = value["issuer_inventory"], value["issuer_documents"]
    selected = inventory["selected_ids"]
    _require(inventory["stock_code"] == ticker
        and value["stock_observation"]["row"]["thscode"] == ticker + (".SH" if ticker[0] == "6" else ".SZ")
        and type(selected) is list and 0 < len(selected) <= 32
        and len(set(selected)) == len(selected) and type(docs) is list
        and [d["announcement_id"] for d in docs] == selected,
        "full-input issuer/document inventory differs")
    for doc in docs:
        count, pages = doc["page_count"], doc["pages"]
        _require(type(count) is int and 0 < count <= 500 and type(pages) is list
            and len(pages) == count
            and all(type(p["page_number"]) is int and p["page_number"] == i
                    and type(p["text"]) is str for i, p in enumerate(pages, 1)),
            "full-input page inventory differs")
    # Shape/identity only: never financial truth, readable-body or recency certification.
    return value


def _pack(raw: bytes, *, ticker: str, policy, check_context) -> bytes:
    """Keep EVERY original JSON byte, including repeated text, metadata and clocks."""
    check_context(raw, ticker)
    compressed = zlib.compress(raw, level=9)
    envelope = {"schema_version": 1, "policy": policy, "ticker": ticker,
        "encoding": "zlib+base64", "decoded_bytes": len(raw), "decoded_sha256": _sha(raw),
        "compressed_sha256": _sha(compressed),
        "data": base64.b64encode(compressed).decode("ascii")}
    stored = _raw(envelope)
    _require(len(stored) <= STORED_BYTES, "full-input storage bound; no clipping")
    _require(_unpack(stored, ticker=ticker, policy=policy, check_context=check_context) == raw, "full-input pack round-trip differs")
    return stored


def _unpack(stored: bytes, *, ticker: str, policy, check_context) -> bytes:
    """Bound decompression BEFORE allocation; reject trailing or concatenated streams."""
    envelope = _json(stored, STORED_BYTES)
    _require(set(envelope) == {"schema_version", "policy", "ticker", "encoding",
        "decoded_bytes", "decoded_sha256", "compressed_sha256", "data"}
        and type(envelope["schema_version"]) is int and envelope["schema_version"] == 1
        and envelope["policy"] == policy and envelope["ticker"] == ticker
        and envelope["encoding"] == "zlib+base64"
        and type(envelope["decoded_bytes"]) is int and 0 < envelope["decoded_bytes"] <= DECODED_BYTES
        and type(envelope["data"]) is str and _raw(envelope) == stored,
        "full-input envelope differs")
    compressed = base64.b64decode(envelope["data"], validate=True)
    _require(base64.b64encode(compressed).decode("ascii") == envelope["data"]
        and _sha(compressed) == envelope["compressed_sha256"], "full-input compressed identity differs")
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, envelope["decoded_bytes"] + 1)
    _require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
        and len(raw) == envelope["decoded_bytes"] and _sha(raw) == envelope["decoded_sha256"],
        "full-input decoded identity differs")
    check_context(raw, ticker)
    return raw


def pack(raw: bytes, *, ticker: str) -> bytes:
    """Legacy Stock contract, byte-identical and still limited to its two tickers."""
    return _pack(raw, ticker=ticker, policy=POLICY, check_context=_context)


def unpack(stored: bytes, *, ticker: str) -> bytes:
    _require(ticker in TICKERS, "full-input envelope differs")
    return _unpack(stored, ticker=ticker, policy=POLICY, check_context=_context)


def checked_unpack(spec: dict, load, *, ticker: str) -> bytes:
    """Use the ORIGINAL checked-source gate; do not increase its 512KiB boundary."""
    from . import external_research_identity as identity
    _require(spec.get("purpose") == "MODEL_CONTEXT", "full-input source purpose differs")
    _require(identity.MAX_BYTES == STORED_BYTES, "full-input shared source contract changed")
    return unpack(identity._checked_source(spec, load), ticker=ticker)


@dataclass(frozen=True)
class FinalRequestCheck:
    """An SDK request hook, not a send function or an execution/permission token.

    `parameters` must be the exact trusted host's original Responses arguments,
    with stream=True. A caller still owes original admission and source rechecks.
    """
    decoded_raw: bytes
    ticker: str
    expected_url: str
    parameters_raw: bytes
    policy: str = POLICY

    @classmethod
    def build(cls, decoded_raw, *, ticker, expected_url, parameters):
        _context(decoded_raw, ticker)
        _require(type(expected_url) is str and expected_url.startswith("https://")
            and expected_url.endswith("/responses") and "?" not in expected_url and "#" not in expected_url,
            "full-input endpoint differs")
        _require(set(parameters) == {"model", "instructions", "input", "text", "tools",
            "store", "max_output_tokens", "stream"}
            and type(parameters["model"]) is str and bool(parameters["model"])
            and type(parameters["instructions"]) is str and bool(parameters["instructions"])
            and parameters["tools"] == [] and parameters["store"] is False
            and parameters["stream"] is True and type(parameters["max_output_tokens"]) is int
            and parameters["max_output_tokens"] > 0,
            "full-input original request shape differs")
        items = parameters["input"]
        _require(type(items) is list and len(items) == 1 and set(items[0]) == {"role", "content"}
            and items[0]["role"] == "user" and type(items[0]["content"]) is str,
            "full-input user input differs")
        prompt = _json(items[0]["content"].encode("utf-8"), REQUEST_BYTES)
        _require(prompt.get("stage") in {"PRE", "QUICK"}
            and _raw(prompt.get("public_context")) == decoded_raw,
            "full-input plain complete context absent or changed")
        fmt = parameters["text"]
        _require(type(fmt) is dict and set(fmt) == {"format"}
            and fmt["format"].get("type") == "json_schema" and fmt["format"].get("strict") is True,
            "full-input strict output format absent")
        encoded = _raw(parameters)
        _require(len(encoded) <= REQUEST_BYTES, "full-input prepared request bound; no clipping")
        # Retain immutable bytes, not mutable caller dictionaries.
        return cls(decoded_raw, ticker, expected_url, encoded)

    def hook(self, receipt: dict):
        """Check actual SDK HTTP bytes before transport; a second attempt is rejected."""
        _require(type(receipt) is dict and not receipt, "full-input receipt must be new")
        attempted = False
        def check(request):
            nonlocal attempted
            _require(not attempted, "full-input repeated send rejected")
            attempted = True
            _require(request.method == "POST" and str(request.url) == self.expected_url,
                     "full-input actual endpoint differs")
            wire = request.content
            actual = _json(wire, REQUEST_BYTES)
            _require(_raw(actual) == self.parameters_raw, "full-input actual SDK request differs")
            receipt.update(policy=self.policy, ticker=self.ticker,
                decoded_bytes=len(self.decoded_raw), decoded_sha256=_sha(self.decoded_raw),
                request_bytes=len(wire), request_sha256=_sha(wire),
                meaning="PRE_SEND_BYTE_CHECK_NOT_DELIVERY_RESEARCH_OR_PROVIDER_ACCEPTANCE")
        return check
