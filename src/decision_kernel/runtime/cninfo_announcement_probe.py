from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter

from decision_kernel.adapters.cninfo import CninfoAdapterError, resolve_cninfo_org_id
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.cninfo_http import (
    CNINFO_ANNOUNCEMENT_HTTPS_URL,
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNINFO_STOCK_MAP_URL,
    CninfoRuntimeError,
    _announcement_disclosure_referer,
    _announcement_query_form,
    _request_json,
)
from decision_kernel.runtime.stock_field_source_study import notice_query

STOCK_CODE = "600036"
START_DATE = date(2026, 9, 14)
END_DATE = date(2026, 9, 15)
MAX_REQUESTS = 7
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
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.2 Safari/605.1.15"
)
_HTTP_BROWSER_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "User-Agent": _USER_AGENT,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}
_HTTPS_BROWSER_HEADERS = {
    **_HTTP_BROWSER_HEADERS,
    "Referer": "https://www.cninfo.com.cn/new/disclosure",
    "Origin": "https://www.cninfo.com.cn",
}
_PAGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": _USER_AGENT,
    "Referer": "http://www.cninfo.com.cn/",
}


def _fresh_session() -> requests.Session:
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=0))
    session.mount("https://", HTTPAdapter(max_retries=0))
    return session


def _status_from_runtime_error(exc: CninfoRuntimeError) -> int | None:
    match = re.search(r"status ([1-5][0-9]{2})", str(exc))
    return None if match is None else int(match.group(1))


def _mapping_shape(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = payload.get("announcements")
    total = payload.get("totalAnnouncement")
    contract_shape = (
        type(total) is int
        and total >= 0
        and (rows is None or isinstance(rows, list))
    )
    return {
        "json_shape": "OBJECT",
        "contract_shape": (
            "CNINFO_ANNOUNCEMENT_PAGE" if contract_shape else "OTHER_JSON_OBJECT"
        ),
        "top_level_keys": sorted(str(key) for key in payload),
        "total_announcement": total,
        "announcement_count": len(rows) if isinstance(rows, list) else None,
        "has_more": payload.get("hasMore"),
    }


def _json_shape_from_response(response: Any) -> dict[str, Any]:
    length = response.headers.get("Content-Length") if hasattr(response, "headers") else None
    if isinstance(length, str) and length.isdigit() and int(length) > MAX_JSON_BYTES:
        return {"json_shape": "REJECTED_OVERSIZE", "contract_shape": "NOT_ESTABLISHED"}
    chunks: list[bytes] = []
    count = 0
    for chunk in response.iter_content(chunk_size=65536):
        count += len(chunk)
        if count > MAX_JSON_BYTES:
            return {"json_shape": "REJECTED_OVERSIZE", "contract_shape": "NOT_ESTABLISHED"}
        chunks.append(chunk)
    try:
        payload = json.loads(b"".join(chunks).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"json_shape": "NOT_JSON", "contract_shape": "NOT_ESTABLISHED"}
    if not isinstance(payload, Mapping):
        return {
            "json_shape": type(payload).__name__.upper(),
            "contract_shape": "NOT_ESTABLISHED",
        }
    return _mapping_shape(payload)


def _requests_post(
    *,
    session: Any,
    variant: str,
    url: str,
    form: Mapping[str, str],
    headers: Mapping[str, str],
) -> dict[str, Any]:
    try:
        response = session.request(
            "POST",
            url,
            data=dict(form),
            headers=dict(headers),
            timeout=(5, 10),
            stream=True,
            allow_redirects=False,
        )
        with response:
            status = response.status_code
            result: dict[str, Any] = {
                "variant": variant,
                "method": "POST",
                "url_scheme": urlsplit(url).scheme,
                "status": status,
            }
            if status == 200:
                result.update(_json_shape_from_response(response))
            return result
    except requests.RequestException as exc:
        return {
            "variant": variant,
            "method": "POST",
            "url_scheme": urlsplit(url).scheme,
            "status": None,
            "transport_error_type": type(exc).__name__,
        }


def _warm_disclosure_session(session: Any, disclosure_url: str) -> dict[str, Any]:
    try:
        response = session.request(
            "GET",
            disclosure_url,
            headers=dict(_PAGE_HEADERS),
            timeout=(5, 10),
            stream=True,
            allow_redirects=False,
        )
        with response:
            return {
                "variant": "requests_http_issuer_page_warm_get",
                "method": "GET",
                "url_scheme": urlsplit(disclosure_url).scheme,
                "status": response.status_code,
                "cookie_count_after": len(session.cookies),
            }
    except requests.RequestException as exc:
        return {
            "variant": "requests_http_issuer_page_warm_get",
            "method": "GET",
            "url_scheme": urlsplit(disclosure_url).scheme,
            "status": None,
            "cookie_count_after": len(session.cookies),
            "transport_error_type": type(exc).__name__,
        }


def run_probe(
    *,
    request_json: Callable[..., Any] = _request_json,
    session_factory: Callable[[], Any] = _fresh_session,
) -> dict[str, Any]:
    request_count = 1
    try:
        org_rows = request_json(
            url=CNINFO_STOCK_MAP_URL,
            method="POST",
            form={"keyWord": STOCK_CODE, "maxNum": "10"},
            timeout_seconds=10.0,
        )
        if not isinstance(org_rows, list):
            raise ValueError("CNINFO_ORG_SEARCH_ARRAY_REQUIRED")
        org_id = resolve_cninfo_org_id({"stockList": org_rows}, stock_code=STOCK_CODE)
    except (CninfoRuntimeError, CninfoAdapterError, ValueError) as exc:
        result = {
            "schema_version": 2,
            "semantics": "CASE_BOUNDED_CNINFO_REQUEST_CONTRACT_PROBE_NOT_EVIDENCE",
            "stock_code": STOCK_CODE,
            "query_window": [START_DATE.isoformat(), END_DATE.isoformat()],
            "org_lookup": {"status": "FAILED", "error_type": type(exc).__name__},
            "announcement_attempts": [],
            "working_variants": [],
            "production_contract_observed": False,
            "request_count": request_count,
            "max_requests": MAX_REQUESTS,
            "disposition": "ORG_LOOKUP_FAILED",
            "cause": "UNKNOWN",
            **AUTHORITY,
        }
        result["probe_hash"] = canonical_hash(result)
        return result

    current_form = _announcement_query_form(
        stock_code=STOCK_CODE,
        org_id=org_id,
        start_date=START_DATE,
        end_date=END_DATE,
        page_size=1,
        page_number=1,
    )
    prior_form = notice_query(
        STOCK_CODE,
        {"stockList": [{"code": STOCK_CODE, "orgId": org_id}]},
        END_DATE,
    )["params"]
    issuer_page = _announcement_disclosure_referer(current_form)
    attempts: list[dict[str, Any]] = []

    request_count += 1
    try:
        payload = request_json(
            url=CNINFO_ANNOUNCEMENT_QUERY_URL,
            method="POST",
            form=current_form,
            timeout_seconds=10.0,
        )
        attempts.append({
            "variant": "urllib_current_production",
            "method": "POST",
            "url_scheme": urlsplit(CNINFO_ANNOUNCEMENT_QUERY_URL).scheme,
            "status": 200,
            **(
                _mapping_shape(payload)
                if isinstance(payload, Mapping)
                else {
                    "json_shape": type(payload).__name__.upper(),
                    "contract_shape": "NOT_ESTABLISHED",
                }
            ),
        })
    except CninfoRuntimeError as exc:
        attempts.append({
            "variant": "urllib_current_production",
            "method": "POST",
            "url_scheme": urlsplit(CNINFO_ANNOUNCEMENT_QUERY_URL).scheme,
            "status": _status_from_runtime_error(exc),
            "transport_error_type": type(exc).__name__,
        })

    with session_factory() as session:
        attempts.append(_requests_post(
            session=session,
            variant="requests_http_current_form_prior_headers",
            url=CNINFO_ANNOUNCEMENT_QUERY_URL,
            form=current_form,
            headers=_PRIOR_STUDY_HEADERS,
        ))
        request_count += 1

    with session_factory() as session:
        attempts.append(_requests_post(
            session=session,
            variant="requests_http_prior_source_study",
            url=CNINFO_ANNOUNCEMENT_QUERY_URL,
            form=prior_form,
            headers=_PRIOR_STUDY_HEADERS,
        ))
        request_count += 1

    with session_factory() as session:
        attempts.append(_requests_post(
            session=session,
            variant="requests_https_legacy_browser_headers",
            url=CNINFO_ANNOUNCEMENT_HTTPS_URL,
            form=current_form,
            headers=_HTTPS_BROWSER_HEADERS,
        ))
        request_count += 1

    with session_factory() as session:
        warm = _warm_disclosure_session(session, issuer_page)
        attempts.append(warm)
        request_count += 1
        if warm.get("status") == 200:
            attempts.append(_requests_post(
                session=session,
                variant="requests_warmed_http_browser_session",
                url=CNINFO_ANNOUNCEMENT_QUERY_URL,
                form=current_form,
                headers={**_HTTP_BROWSER_HEADERS, "Referer": issuer_page},
            ))
            request_count += 1

    if request_count > MAX_REQUESTS:
        raise RuntimeError("CNINFO_PROBE_REQUEST_BUDGET_EXCEEDED")

    announcement_posts = [item for item in attempts if item["method"] == "POST"]
    working = [
        item["variant"]
        for item in announcement_posts
        if item.get("status") == 200
        and item.get("contract_shape") == "CNINFO_ANNOUNCEMENT_PAGE"
    ]
    production_contract_observed = "urllib_current_production" in working
    http_working = [
        item["variant"] for item in announcement_posts
        if item.get("url_scheme") == "http" and item["variant"] in working
    ]
    https_working = [
        item["variant"] for item in announcement_posts
        if item.get("url_scheme") == "https" and item["variant"] in working
    ]
    statuses = [item.get("status") for item in announcement_posts]
    if production_contract_observed:
        disposition = "PRODUCTION_HTTP_ANNOUNCEMENT_CONTRACT_OBSERVED"
    elif http_working:
        disposition = "HTTP_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED_NOT_PRODUCTION"
    elif https_working:
        disposition = "HTTPS_ONLY_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED"
    elif statuses and all(status == 403 for status in statuses):
        disposition = "ALL_TESTED_ANNOUNCEMENT_CONTRACTS_403"
    else:
        disposition = "NO_WORKING_ANNOUNCEMENT_CONTRACT_OBSERVED"

    result = {
        "schema_version": 2,
        "semantics": "CASE_BOUNDED_CNINFO_REQUEST_CONTRACT_PROBE_NOT_EVIDENCE",
        "stock_code": STOCK_CODE,
        "query_window": [START_DATE.isoformat(), END_DATE.isoformat()],
        "org_lookup": {"status": "OK", "org_id": org_id},
        "announcement_attempts": attempts,
        "working_variants": working,
        "production_contract_observed": production_contract_observed,
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
        f"Production HTTP contract observed: `{result['production_contract_observed']}`",
        f"Requests used: `{result['request_count']}/{result['max_requests']}`",
        f"Cause: `{result['cause']}`",
        "",
        "This is a transport/request-contract probe only. It is not Evidence, Research, a market observation, or production acceptance.",
        "",
        "HTTP announcement JSON is locator/discovery metadata only. Original document bytes remain qualified separately on CNINFO's official HTTPS static host.",
        "",
        "## Attempts",
        "",
        "| Variant | Method | Scheme | Status | Contract |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for attempt in result["announcement_attempts"]:
        lines.append(
            "| {variant} | {method} | {scheme} | {status} | {contract} |".format(
                variant=attempt["variant"],
                method=attempt["method"],
                scheme=attempt.get("url_scheme", "-"),
                status=attempt.get("status"),
                contract=attempt.get("contract_shape", "-"),
            )
        )
    lines.extend([
        "",
        "Working variants: " + (
            ", ".join(f"`{item}`" for item in result["working_variants"])
            if result["working_variants"] else "none"
        ),
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    result = run_probe()
    (output / "probe.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(render_summary(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
