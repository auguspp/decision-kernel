"""Private-safe IMA knowledge-base connectivity/search probe.

The purchased/shared IMA library is private input. This module intentionally
retains no knowledge-base names/ids, document titles/snippets/media ids/URLs or
raw provider bodies when used through the public-repository workflow.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re

import requests

from ..identity import canonical_hash, canonical_json

VERSION = "ima-private-probe-v1"
WORKFLOW = ".github/workflows/ima-private-probe.yml"
BASE = "https://ima.qq.com/openapi/wiki/v1/"
LIMIT = 20
MAX_BODY = 512 * 1024
MAX_QUERY = 120
MAX_PRIVATE_ROWS = 100
AUTHORITY = {
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
    "automatic_full": False,
    "pdf_downloads": 0,
}


class ProbeError(ValueError):
    def __init__(self, code: str, *, http_status: int | None = None, business_code: int | None = None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.business_code = business_code


def require(ok: bool, code: str, *, http_status: int | None = None) -> None:
    if not ok:
        raise ProbeError(code, http_status=http_status)


def query(value: str) -> str:
    require(isinstance(value, str), "QUERY_TYPE")
    require(not any(ord(c) < 32 for c in value), "QUERY_VALUE")
    value = value.strip()
    require(0 < len(value) <= MAX_QUERY, "QUERY_VALUE")
    return value


def secret(value: str, code: str) -> str:
    require(isinstance(value, str) and 8 <= len(value) <= 4096, code)
    require(value.isascii() and all(32 < ord(c) < 127 for c in value), code)
    return value


def credentials(env=os.environ) -> tuple[str, str]:
    return (
        secret(env.get("IMA_OPENAPI_CLIENTID", ""), "CLIENT_ID_UNAVAILABLE"),
        secret(env.get("IMA_OPENAPI_APIKEY", ""), "API_KEY_UNAVAILABLE"),
    )


def base_spec(base_query: str) -> dict:
    base_query = query(base_query)
    return {
        "endpoint": "search_knowledge_base",
        "url": BASE + "search_knowledge_base",
        "body": {"query": base_query, "cursor": "", "limit": LIMIT},
    }


def document_spec(knowledge_base_id: str, document_query: str) -> dict:
    require(isinstance(knowledge_base_id, str) and 1 <= len(knowledge_base_id) <= 256,
            "KNOWLEDGE_BASE_ID")
    require(not any(ord(c) < 32 for c in knowledge_base_id), "KNOWLEDGE_BASE_ID")
    document_query = query(document_query)
    return {
        "endpoint": "search_knowledge",
        "url": BASE + "search_knowledge",
        "body": {"query": document_query, "cursor": "", "knowledge_base_id": knowledge_base_id},
    }


def _session():
    session = requests.Session()
    session.trust_env = False
    return session


def request_raw(spec: dict, *, client_id: str, api_key: str) -> tuple[int, bytes]:
    require(isinstance(spec, dict) and spec.get("endpoint") in {"search_knowledge_base", "search_knowledge", "get_media_info"},
            "REQUEST_SPEC")
    expected = BASE + spec["endpoint"]
    require(spec.get("url") == expected and isinstance(spec.get("body"), dict), "REQUEST_SPEC")
    client_id, api_key = secret(client_id, "CLIENT_ID_UNAVAILABLE"), secret(api_key, "API_KEY_UNAVAILABLE")
    headers = {
        "ima-openapi-clientid": client_id,
        "ima-openapi-apikey": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "DecisionKernel-IMA-Private-Probe/1",
    }
    with _session() as session:
        with session.post(expected, json=spec["body"], headers=headers, stream=True,
                          allow_redirects=False, timeout=(10, 20)) as response:
            require(response.url == expected, "DESTINATION_CHANGED")
            require(response.headers.get("Content-Encoding", "identity").lower() in {"", "identity"},
                    "ENCODING_CHANGED")
            length = response.headers.get("Content-Length")
            require(length is None or length.isdigit() and int(length) <= MAX_BODY, "BODY_SIZE")
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                require(size <= MAX_BODY, "BODY_SIZE")
                chunks.append(chunk)
            raw = b"".join(chunks)
            require(length is None or len(raw) == int(length), "BODY_LENGTH")
            require(client_id.encode() not in raw and api_key.encode() not in raw, "CREDENTIAL_REFLECTION")
            return response.status_code, raw


def decode(raw: bytes) -> dict:
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, "BODY_SIZE")
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError("INVALID_JSON") from exc
    require(isinstance(value, dict), "ENVELOPE")
    return value


def payload(raw: bytes) -> dict:
    value = decode(raw)
    require(type(value.get("code")) is int, "BUSINESS_CODE_TYPE")
    if value["code"] != 0:
        raise ProbeError("BUSINESS_REJECTED", business_code=value["code"])
    data = value.get("data")
    require(isinstance(data, dict), "DATA_SHAPE")
    return data


def _private_string(value, code: str, *, limit: int = 4096) -> str:
    require(isinstance(value, str) and 0 < len(value) <= limit and "\x00" not in value, code)
    return value


def base_rows(data: dict) -> list[dict]:
    rows = data.get("info_list")
    require(isinstance(rows, list) and len(rows) <= MAX_PRIVATE_ROWS, "BASE_ROWS")
    out = []
    for row in rows:
        require(isinstance(row, dict), "BASE_ROW")
        base_id = row.get("id") if row.get("id") not in (None, "") else row.get("kb_id")
        name = row.get("name") if row.get("name") not in (None, "") else row.get("kb_name")
        out.append({"id": _private_string(base_id, "BASE_ID", limit=256),
                    "name": _private_string(name, "BASE_NAME")})
    require(type(data.get("is_end")) is bool, "BASE_PAGINATION")
    cursor = data.get("next_cursor", "")
    require(isinstance(cursor, str) and len(cursor) <= 4096, "BASE_PAGINATION")
    return out


def select_base(rows: list[dict], base_query: str) -> dict:
    base_query = query(base_query)
    require(bool(rows), "BASE_NOT_FOUND")
    exact = [r for r in rows if r["name"].strip().casefold() == base_query.casefold()]
    if len(exact) == 1:
        return exact[0]
    contains = [r for r in rows if base_query.casefold() in r["name"].casefold()]
    if len(contains) == 1:
        return contains[0]
    require(len(rows) == 1, "BASE_AMBIGUOUS")
    return rows[0]


def document_rows(data: dict) -> list[dict]:
    rows = data.get("info_list")
    require(isinstance(rows, list) and len(rows) <= MAX_PRIVATE_ROWS, "DOCUMENT_ROWS")
    for row in rows:
        require(isinstance(row, dict), "DOCUMENT_ROW")
        media_id = row.get("media_id")
        title = row.get("title")
        _private_string(media_id, "MEDIA_ID", limit=256)
        _private_string(title, "TITLE")
        if row.get("highlight_content") is not None:
            require(isinstance(row["highlight_content"], str) and len(row["highlight_content"]) <= 65536,
                    "HIGHLIGHT")
    document_pagination(data)
    return rows


def document_pagination(data: dict) -> dict:
    # Observed by upstream IMA clients: search_knowledge may omit BOTH fields.
    # Missing pagination is UNKNOWN, never proof that the library was exhausted.
    reported = "is_end" in data or "next_cursor" in data
    if not reported:
        return {"pagination_reported": False, "is_end": None,
                "next_cursor_present": None, "coverage": "UNKNOWN"}
    require("is_end" in data and "next_cursor" in data, "DOCUMENT_PAGINATION")
    require(type(data["is_end"]) is bool, "DOCUMENT_PAGINATION")
    cursor = data["next_cursor"]
    require(isinstance(cursor, str) and len(cursor) <= 4096, "DOCUMENT_PAGINATION")
    return {"pagination_reported": True, "is_end": data["is_end"],
            "next_cursor_present": bool(cursor), "coverage": "UNKNOWN"}


def _clock(value: str) -> str:
    require(isinstance(value, str), "CLOCK_TYPE")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProbeError("CLOCK_FORMAT") from exc
    require(dt.tzinfo is not None and dt.utcoffset() is not None, "CLOCK_ZONE")
    return dt.astimezone(timezone.utc).isoformat()


def _call(spec: dict, send, clock) -> tuple[dict, dict]:
    requested_at = _clock(clock())
    status, raw = send(spec)
    received_at = _clock(clock())
    require(type(status) is int and 100 <= status <= 599, "HTTP_STATUS")
    meta = {"endpoint": spec["endpoint"], "requested_at": requested_at, "received_at": received_at,
            "http_status": status, "bytes": len(raw) if isinstance(raw, bytes) else None,
            "sha256": sha256(raw).hexdigest() if isinstance(raw, bytes) else None}
    require(status == 200, "HTTP_REJECTED", http_status=status)
    data = payload(raw)
    return data, meta


def probe(base_query: str, document_query: str | None, *, send, clock, report_title_terms: str | None = None) -> dict:
    bq = query(base_query)
    dq = None if document_query is None or not document_query.strip() else query(document_query)
    if report_title_terms:
        query(report_title_terms)
        require(dq is not None, "DOCUMENT_QUERY_REQUIRED")
    base_data, base_meta = _call(base_spec(bq), send, clock)
    rows = base_rows(base_data)
    selected = select_base(rows, bq)
    if report_title_terms:
        require(bq.casefold() in selected["name"].casefold(), "BASE_NAME_MISMATCH")
    base_meta.update(match_count=len(rows), is_end=base_data["is_end"], next_cursor_present=bool(base_data.get("next_cursor")))
    documents = None
    calls = 1
    if dq is not None:
        doc_data, doc_meta = _call(document_spec(selected["id"], dq), send, clock)
        docs = document_rows(doc_data)
        doc_meta.update(match_count=len(docs), **document_pagination(doc_data))
        documents = doc_meta
        calls += 1
    result = {
        "version": VERSION,
        "status": "CONNECTED_SEARCHABLE" if documents is not None else "CONNECTED_BASE_VISIBLE",
        "base_query_hash": canonical_hash(bq),
        "document_query_hash": None if dq is None else canonical_hash(dq),
        "source_calls": calls,
        "base": base_meta,
        "documents": documents,
        "private_source_retention": "NO_RAW_OR_PRIVATE_METADATA_PUBLIC_REPO",
        "source_replay": "NOT_AVAILABLE_WITHOUT_PRIVATE_BYTES",
        "meaning": "PRIVATE_LIBRARY_CONNECTIVITY_AND_SEARCHABILITY_NOT_REPORT_RESEARCH_OR_SOURCE_RIGHTS",
        **AUTHORITY,
    }
    if report_title_terms:
        from .ima_document_check import check_one_document
        check = check_one_document(docs, report_title_terms, send=send, clock=clock)
        result["body_check"] = check
        result["source_calls"] += check["api_call_attempts"] + check["file_get_attempts"]
        result["source_count_basis"] = "REQUEST_ATTEMPTS_INCLUDING_BODY_CHECK"
        result["pdf_downloads"] = check["pdf_downloads"]
    result["receipt_hash"] = canonical_hash(result)
    return result


def safe_failure(exc: Exception) -> dict:
    code = exc.code if isinstance(exc, ProbeError) and re.fullmatch(r"[A-Z0-9_]+", exc.code) else type(exc).__name__
    status = exc.http_status if isinstance(exc, ProbeError) else None
    result = {"version": VERSION, "status": "PROBE_FAILED", "failure_code": code,
              "http_status": status, "private_source_retention": "NONE",
              "source_replay": "NOT_AVAILABLE", **AUTHORITY}
    if isinstance(exc, ProbeError) and exc.business_code is not None:
        result["business_code"] = exc.business_code
    result["receipt_hash"] = canonical_hash(result)
    return result


def encoded(value: dict) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def render(result: dict) -> str:
    if result["status"] == "PROBE_FAILED":
        return ("# IMA private report probe\n\n"
                f"status: {result['status']}\n\nfailure: {result['failure_code']}\n\n"
                "No private IMA names, ids, titles, snippets, URLs, bodies or credentials were retained.\n")
    docs = result.get("documents")
    body_check = result.get("body_check")
    return ("# IMA private report probe\n\n"
            f"status: {result['status']}\n\n"
            f"knowledge-base matches on first bounded response: {result['base']['match_count']}\n\n"
            + ("document matches on first bounded response: NOT_REQUESTED\n\n" if docs is None else
               f"document matches on first bounded response: {docs['match_count']}\n\n")
            + ("document pagination not returned; coverage UNKNOWN.\n\n"
               if docs is not None and docs.get("pagination_reported") is False else "")
            + ("single candidate check: " + body_check["status"] + ". Machine parsing is not semantic reading or Research delivery.\n\n"
               if body_check is not None else "")
            + "Counts are connectivity/search evidence only, not complete library coverage.\n\n"
              "No private IMA names, ids, titles, snippets, URLs, bodies or credentials were retained.\n")


def write_result(root: Path, result: dict) -> None:
    require(not root.exists() and not root.is_symlink() and not any(p.is_symlink() for p in root.parents),
            "OUTPUT_CREATE_ONLY")
    root.mkdir(parents=True)
    receipt = encoded(result)
    summary = render(result).encode("utf-8")
    # Defense-in-depth: private provider response fields cannot appear in the public receipt.
    lowered = receipt.lower()
    for marker in (b"media_id", b"highlight_content", b"knowledge_base_id", b"kb_id", b"kb_name", b"cover_url", b"url_info"):
        require(marker not in lowered, "PRIVATE_FIELD_LEAK")
    (root / "receipt.json").write_bytes(receipt)
    (root / "summary.md").write_bytes(summary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-query-env", default="IMA_BASE_QUERY")
    parser.add_argument("--document-query-env", default="IMA_DOCUMENT_QUERY")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    client_id = api_key = ""
    try:
        client_id, api_key = credentials()
        bq = os.environ.get(args.base_query_env, "")
        dq = os.environ.get(args.document_query_env, "")
        def send(spec):
            return request_raw(spec, client_id=client_id, api_key=api_key)
        terms = os.environ.get("IMA_REPORT_TITLE_TERMS", "")
        result = probe(bq, dq, send=send, clock=lambda: datetime.now(timezone.utc).isoformat(),
                       report_title_terms=terms or None)
    except (ProbeError, requests.RequestException, OSError, TypeError, KeyError, OverflowError) as exc:
        result = safe_failure(exc)
    write_result(args.output, result)
    print("IMA_PRIVATE_PROBE_STATUS=" + result["status"])
    print("IMA_PRIVATE_PROBE_HASH=" + result["receipt_hash"])
    check_status = result.get("body_check", {}).get("status")
    return 0 if result["status"].startswith("CONNECTED_") and check_status not in {
        "CHECK_FAILED", "PDF_PARSE_FAILED", "PDF_PARSE_TIMEOUT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
