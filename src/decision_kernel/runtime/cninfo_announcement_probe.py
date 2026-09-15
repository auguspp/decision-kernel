from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping

import requests
from requests.adapters import HTTPAdapter

from decision_kernel.adapters.cninfo import resolve_cninfo_org_id
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.cninfo_http import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNINFO_STOCK_MAP_URL,
    CninfoRuntimeError,
    _announcement_query_form,
    _request_json,
)

STOCK_CODE = "600036"
START_DATE = date(2026, 9, 14)
END_DATE = date(2026, 9, 15)
DISCLOSURE_PAGE_URL = "https://www.cninfo.com.cn/new/disclosure"
MAX_REQUESTS = 6
MAX_JSON_BYTES = 256 * 1024

AUTHORITY = {
    "production_qualification": "NOT_ESTABLISHED",
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
    "market_state_writes": 0,
    "events_created": 0,
}

_PRIOR_STUDY_HEADERS = {
    "Accept-Encoding": "identity",
    "Accept": "application/json",
}
_BROWSER_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Safari/605.1.15"
    ),
    "Referer": DISCLOSURE_PAGE_URL,
    "Origin": "https://www.cninfo.com.cn",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}
_PAGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": _BROWSER_HEADERS["User-Agent"],
    "Referer": "https://www.cninfo.com.cn/",
}


def _fresh_session() -> requests.Session:
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=0))
    session.mount("https://", HTTPAdapter(max_retries=0))
    return session


def _status_from_runtime_error(exc: CninfoRuntimeError) -> int | None:
    match = re.search(r"status ([1-5][0-9]{2})", str(exc))
    return None if match is None else int(match.group(1))


def _json_shape_from_response(response: Any) -> dict[str, Any]:
    length = response.headers.get("Content-Length") if hasattr(response, "headers") else None
    if isinstance(length, str) and length.isdigit() and int(length) > MAX_JSON_BYTES:
        return {"json_shape": "REJECTED_OVERSIZE"}
    chunks: list[bytes] = []
    count = 0
    for chunk in response.iter_content(chunk_size=65536):
        count += len(chunk)
        if count > MAX_JSON_BYTES:
            return {"json_shape": "REJECTED_OVERSIZE"}
        chunks.append(chunk)
    try:
        payload = json.loads(b"".join(chunks).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"json_shape": "NOT_JSON"}
    if not isinstance(payload, Mapping):
        return {"json_shape": type(payload).__name__.upper()}
    rows = payload.get("announcements")
    return {
        "json_shape": "OBJECT",
        "top_level_keys": sorted(str(key) for key in payload),
        "total_announcement": payload.get("totalAnnouncement"),
        "announcement_count": len(rows) if isinstance(rows, list) else None,
        "has_more": payload.get("hasMore"),
    }


def _requests_post(
    *,
    session: Any,
    variant: str,
    form: Mapping[str, str],
    headers: Mapping[str, str],
) -> dict[str, Any]:
    try:
        response = session.request(
            "POST",
            CNINFO_ANNOUNCEMENT_QUERY_URL,
            data=dict(form),
            headers=dict(headers),
            timeout=(5, 10),
            stream=True,
            allow_redirects=False,
        )
        with response:
            status = response.status_code
            result: dict[str, Any] = {"variant": variant, "method": "POST", "status": status}
            if status == 200:
                result.update(_json_shape_from_response(response))
            return result
    except requests.RequestException as exc:
        return {
            "variant": variant,
            "method": "POST",
            "status": None,
            "transport_error_type": type(exc).__name__,
        }


def _warm_disclosure_session(session: Any) -> dict[str, Any]:
    try:
        response = session.request(
            "GET",
            DISCLOSURE_PAGE_URL,
            headers=dict(_PAGE_HEADERS),
            timeout=(5, 10),
            stream=True,
            allow_redirects=False,
        )
        with response:
            return {
                "variant": "requests_session_warm_get",
                "method": "GET",
                "status": response.status_code,
                "cookie_count_after": len(session.cookies),
            }
    except requests.RequestException as exc:
        return {
            "variant": "requests_session_warm_get",
            "method": "GET",
            "status": None,
            "cookie_count_after": len(session.cookies),
            "transport_error_type": type(exc).__name__,
        }


def run_probe(
    *,
    request_json: Callable[..., Any] = _request_json,
    session_factory: Callable[[], Any] = _fresh_session,
) -> dict[str, Any]:
    request_count = 0
    try:
        org_rows = request_json(
            url=CNINFO_STOCK_MAP_URL,
            method="POST",
            form={"keyWord": STOCK_CODE, "maxNum": "10"},
            timeout_seconds=10.0,
        )
        request_count += 1
        if not isinstance(org_rows, list):
            raise ValueError("CNINFO_ORG_SEARCH_ARRAY_REQUIRED")
        org_id = resolve_cninfo_org_id({"stockList": org_rows}, stock_code=STOCK_CODE)
    except Exception as exc:
        result = {
            "schema_version": 1,
            "semantics": "CASE_BOUNDED_CNINFO_REQUEST_CONTRACT_PROBE_NOT_EVIDENCE",
            "stock_code": STOCK_CODE,
            "query_window": [START_DATE.isoformat(), END_DATE.isoformat()],
            "org_lookup": {"status": "FAILED", "error_type": type(exc).__name__},
            "announcement_attempts": [],
            "request_count": max(request_count, 1),
            "max_requests": MAX_REQUESTS,
            "disposition": "ORG_LOOKUP_FAILED",
            "cause": "UNKNOWN",
            **AUTHORITY,
        }
        result["probe_hash"] = canonical_hash(result)
        return result

    form = _announcement_query_form(
        stock_code=STOCK_CODE,
        org_id=org_id,
        start_date=START_DATE,
        end_date=END_DATE,
        page_size=1,
        page_number=1,
    )
    attempts: list[dict[str, Any]] = []

    request_count += 1
    try:
        payload = request_json(
            url=CNINFO_ANNOUNCEMENT_QUERY_URL,
            method="POST",
            form=form,
            timeout_seconds=10.0,
        )
        if isinstance(payload, Mapping):
            rows = payload.get("announcements")
            attempts.append({
                "variant": "urllib_current_production",
                "method": "POST",
                "status": 200,
                "json_shape": "OBJECT",
                "top_level_keys": sorted(str(key) for key in payload),
                "total_announcement": payload.get("totalAnnouncement"),
                "announcement_count": len(rows) if isinstance(rows, list) else None,
                "has_more": payload.get("hasMore"),
            })
        else:
            attempts.append({
                "variant": "urllib_current_production",
                "method": "POST",
                "status": 200,
                "json_shape": type(payload).__name__.upper(),
            })
    except CninfoRuntimeError as exc:
        attempts.append({
            "variant": "urllib_current_production",
            "method": "POST",
            "status": _status_from_runtime_error(exc),
            "transport_error_type": type(exc).__name__,
        })

    with session_factory() as session:
        attempts.append(_requests_post(
            session=session,
            variant="requests_prior_source_study",
            form=form,
            headers=_PRIOR_STUDY_HEADERS,
        ))
        request_count += 1

    with session_factory() as session:
        attempts.append(_requests_post(
            session=session,
            variant="requests_browser_headers",
            form=form,
            headers=_BROWSER_HEADERS,
        ))
        request_count += 1

    with session_factory() as session:
        warm = _warm_disclosure_session(session)
        attempts.append(warm)
        request_count += 1
        if warm.get("status") == 200:
            attempts.append(_requests_post(
                session=session,
                variant="requests_warmed_browser_session",
                form=form,
                headers=_BROWSER_HEADERS,
            ))
            request_count += 1

    if request_count > MAX_REQUESTS:
        raise RuntimeError("CNINFO_PROBE_REQUEST_BUDGET_EXCEEDED")

    announcement_posts = [item for item in attempts if item["method"] == "POST"]
    working = [
        item["variant"]
        for item in announcement_posts
        if item.get("status") == 200 and item.get("json_shape") == "OBJECT"
    ]
    statuses = [item.get("status") for item in announcement_posts]
    if working:
        disposition = "HTTPS_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED"
    elif statuses and all(status == 403 for status in statuses):
        disposition = "ALL_TESTED_HTTPS_ANNOUNCEMENT_CONTRACTS_403"
    else:
        disposition = "NO_WORKING_HTTPS_ANNOUNCEMENT_CONTRACT_OBSERVED"

    result = {
        "schema_version": 1,
        "semantics": "CASE_BOUNDED_CNINFO_REQUEST_CONTRACT_PROBE_NOT_EVIDENCE",
        "stock_code": STOCK_CODE,
        "query_window": [START_DATE.isoformat(), END_DATE.isoformat()],
        "org_lookup": {"status": "OK", "org_id": org_id},
        "announcement_attempts": attempts,
        "working_variants": working,
        "request_count": request_count,
        "max_requests": MAX_REQUESTS,
        "disposition": disposition,
        "cause": "UNKNOWN",
        **AUTHORITY,
    }
    result["probe_hash"] = canonical_hash(result)
    return result


def render_summary(result: Mapping[str, Any]) -> str:
    lines = [
        "# CNINFO announcement source probe",
        "",
        f"Disposition: `{result['disposition']}`",
        f"Requests used: `{result['request_count']}/{result['max_requests']}`",
        f"Cause: `{result['cause']}`",
        "",
        "This is a transport/request-contract probe only. It is not Evidence, Research, a market observation, or production acceptance.",
        "",
        "## Attempts",
        "",
    ]
    for item in result.get("announcement_attempts", []):
        lines.append(f"- `{item['variant']}` {item['method']}: status `{item.get('status')}`")
    lines.extend([
        "",
        "No retry, provider fallback, redirect following, 403-body retention, cookie-value retention, PDF acquisition, Research, Odds or Action is performed.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    result = run_probe()
    (args.output / "probe.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    (args.output / "summary.md").write_text(render_summary(result), encoding="utf-8")
    print(result["disposition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
