"""Finite client for the Human-authorized third-party Tushare Relay.

This is a compatibility/relay source, not official Tushare identity and not a
generic provider router. Only explicitly reviewed endpoints are allowed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import time
from typing import Any, Callable

import requests

BASE = "https://pcd.mobcvb.cn"
PRO = BASE + "/tushare/pro"
CAPABILITIES = BASE + "/tushare/capabilities"
SECRET_ENV = "TUSHARE_PROXY_API_KEY"
MAX_BODY = 4 * 1024 * 1024
RETRY_WAIT_SECONDS = 30
ALLOWED = frozenset({
    "hm_list", "hm_detail", "report_rc", "top_list", "top_inst",
    "stk_surv", "research_report",
    "daily", "daily_basic", "adj_factor", "trade_cal",
    "income", "balancesheet", "cashflow", "fina_indicator", "disclosure_date",
    "shibor", "index_classify", "index_member_all", "ths_index", "ths_daily",
    "index_global", "hk_daily", "us_daily", "fut_wsr",
})
HEADER_ALLOWLIST = ("X-Request-ID", "X-Cache", "X-RateLimit-Remaining",
                    "X-RateLimit-IP-Remaining", "Retry-After")

class RelayError(ValueError):
    pass

def require(ok: bool, code: str) -> None:
    if not ok:
        raise RelayError(code)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_JSON_KEY")
        out[key] = value
    return out

def decode(raw: bytes) -> dict[str, Any]:
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, "BODY_SIZE")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(RelayError("NONFINITE_JSON")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RelayError("JSON_INVALID") from exc
    require(isinstance(value, dict), "ENVELOPE")
    return value

def _params(api: str, params: dict[str, Any]) -> dict[str, str]:
    require(api in ALLOWED and isinstance(params, dict), "API_SCOPE")
    out = {}
    for key, value in params.items():
        require(isinstance(key, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is not None,
                "PARAM_NAME")
        require(value is not None and isinstance(value, (str, int)) and not isinstance(value, bool),
                "PARAM_VALUE")
        text = str(value)
        require(len(text) <= 256 and "\x00" not in text, "PARAM_VALUE")
        out[key] = text
    require(out.get("__probe") != "1", "PROBE_NOT_PRODUCTION")
    return out

def classify(http_status: int, body: dict[str, Any]) -> str:
    error = body.get("error")
    code = body.get("code")
    msg = body.get("msg")
    if http_status == 200 and body.get("ok") is not False and code in (0, None):
        return "SUCCESS"
    if http_status == 429 or error in {"rate_limited", "ip_rate_limited"}:
        return "RATE_LIMIT"
    if http_status in {401, 403} or error in {"unauthorized", "forbidden"}:
        return "AUTH_OR_ENTITLEMENT"
    if error == "data_source_unavailable":
        return "SOURCE_UNAVAILABLE"
    if http_status == 400 or error == "invalid_params":
        return "INVALID_PARAMS"
    if (http_status in {502, 503, 504}
            or error in {"upstream_pool_exhausted", "upstream_timeout", "minute_data_pending"}
            or (http_status == 200 and code == 1 and msg == "timeout")):
        return "TEMPORARY_QUEUE"
    return "SOURCE_ERROR"

def _http_get(api: str, params: dict[str, str], key: str, *, clock: Callable[[], str] = now) -> dict[str, Any]:
    url = PRO + "/" + api
    headers = {"X-API-Key": key, "Accept": "application/json",
               "Accept-Encoding": "identity", "User-Agent": "DecisionKernel-TushareRelay/1"}
    client = requests.Session()
    client.trust_env = False
    requested_at = clock()
    try:
        with client.get(url, params=params, headers=headers, timeout=(10, 35),
                        allow_redirects=False, stream=True) as response:
            prepared = requests.Request("GET", url, params=params).prepare().url
            require(response.url == prepared, "DESTINATION_CHANGED")
            require(response.headers.get("Content-Encoding", "identity").lower() in {"", "identity"},
                    "ENCODING_CHANGED")
            length = response.headers.get("Content-Length")
            require(length is None or length.isdigit() and int(length) <= MAX_BODY, "BODY_SIZE")
            chunks = []
            size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                require(size <= MAX_BODY, "BODY_SIZE")
                chunks.append(chunk)
            raw = b"".join(chunks)
            require(length is None or len(raw) == int(length), "BODY_LENGTH")
            require(key.encode() not in raw, "CREDENTIAL_REFLECTION")
            received_at = clock()
            safe_headers = {name: response.headers[name] for name in HEADER_ALLOWLIST
                            if response.headers.get(name) is not None}
            return {"http_status": response.status_code, "raw": raw,
                    "requested_at": requested_at, "received_at": received_at,
                    "headers": safe_headers}
    finally:
        client.close()

def request(api: str, params: dict[str, Any], *, key: str | None = None,
            transport: Callable[..., dict[str, Any]] = _http_get,
            sleep: Callable[[float], None] = time.sleep, clock: Callable[[], str] = now) -> dict[str, Any]:
    """At most two attempts. Temporary queue waits exactly 30 seconds once."""
    p = _params(api, params)
    credential = key if key is not None else os.environ.get(SECRET_ENV, "")
    require(isinstance(credential, str) and len(credential) >= 8
            and credential.isascii() and all(32 < ord(c) < 127 for c in credential),
            "CREDENTIAL_UNAVAILABLE")
    attempts = []
    for attempt_no in (1, 2):
        if attempt_no == 2:
            sleep(RETRY_WAIT_SECONDS)
        try:
            result = transport(api, p, credential, clock=clock)
            require(set(result) == {"http_status", "raw", "requested_at", "received_at", "headers"},
                    "TRANSPORT_CONTRACT")
            body = decode(result["raw"])
            classification = classify(result["http_status"], body)
            attempts.append({**result, "attempt": attempt_no, "classification": classification,
                             "business_code": body.get("code"), "business_error": body.get("error"),
                             "business_msg": body.get("msg") or body.get("message")})
        except requests.Timeout:
            attempts.append({"attempt": attempt_no, "http_status": None, "raw": None,
                             "requested_at": clock(), "received_at": clock(), "headers": {},
                             "classification": "TEMPORARY_QUEUE", "business_code": None,
                             "business_error": "TRANSPORT_TIMEOUT", "business_msg": None})
        except requests.ConnectionError:
            attempts.append({"attempt": attempt_no, "http_status": None, "raw": None,
                             "requested_at": clock(), "received_at": clock(), "headers": {},
                             "classification": "TRANSPORT_CONNECTION", "business_code": None,
                             "business_error": "TRANSPORT_CONNECTION", "business_msg": None})
        result = attempts[-1]
        if result["classification"] != "TEMPORARY_QUEUE" or attempt_no == 2:
            break
    return {"api": api, "params": p, "attempts": attempts,
            "status": attempts[-1]["classification"]}

def successful_body(result: dict[str, Any]) -> dict[str, Any] | None:
    require(isinstance(result, dict) and result.get("api") in ALLOWED, "RESULT_SCOPE")
    attempts = result.get("attempts")
    require(isinstance(attempts, list) and 1 <= len(attempts) <= 2, "RESULT_ATTEMPTS")
    last = attempts[-1]
    if last.get("classification") != "SUCCESS":
        return None
    return decode(last["raw"])

def rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    require(isinstance(body, dict) and body.get("code") in (0, None), "BUSINESS_STATUS")
    data = body.get("data")
    require(isinstance(data, dict), "DATA_ENVELOPE")
    fields, items = data.get("fields"), data.get("items")
    require(isinstance(fields, list) and len(fields) <= 512
            and all(isinstance(x, str) and 0 < len(x) <= 128 for x in fields), "DATA_FIELDS")
    require(isinstance(items, list) and len(items) <= 10000, "DATA_ROWS")
    out = []
    for item in items:
        require(isinstance(item, list) and len(item) == len(fields), "DATA_ROW_SHAPE")
        out.append(dict(zip(fields, item, strict=True)))
    count = body.get("count")
    require(count is None or type(count) is int and count >= len(out), "DATA_COUNT")
    return out
