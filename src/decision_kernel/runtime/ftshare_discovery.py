"""Bounded FTShare report-index input; never issuer custody or Research authority.

Reuse the official report-announcement-list HTTP/pagination contract (MIT Skill
handler). This public route does not send credentials. No alternate host, retry,
provider framework, PDF request, or automatic research is implemented here.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

ENDPOINT = "https://market.ft.tech/gateway/api/v1/market/data/report-announcements/list"
VERSION = "ftshare-report-discovery-v1"
PAGE_SIZE, MAX_PAGES, MAX_BYTES = 200, 4, 2 * 1024 * 1024


class DiscoveryError(ValueError):
    """Only a finite local reason, never provider text or credentials."""


def _require(condition, code):
    if not condition:
        raise DiscoveryError(code)


def _clock(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.utcoffset() is not None, "CLOCK_MISMATCH")
    return parsed


def now():
    return datetime.now(timezone.utc).isoformat()


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            _require(key not in out, "PARSE_FAILURE")
            out[key] = value
        return out
    def reject(value):
        raise DiscoveryError("PARSE_FAILURE")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiscoveryError("REDIRECT_REJECTED")


def request_page(parameters):
    """One fixed-destination, finite GET. Environment keys/base URLs are unused."""
    req = Request(ENDPOINT + "?" + urlencode(parameters), headers={
        "Accept": "application/json", "Accept-Encoding": "identity",
        "User-Agent": "decision-kernel/ftshare-report-discovery-v1"})
    try:
        response = build_opener(_NoRedirect()).open(req, timeout=20)
    except HTTPError as exc:
        response = exc  # Preserve its bounded body and status, without a retry.
    with response:
        _require(response.geturl() == req.full_url, "REDIRECT_REJECTED")
        _require(response.headers.get("Content-Encoding", "identity") == "identity",
                 "ENCODING_REJECTED")
        raw = response.read(MAX_BYTES + 1)
        _require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
        length = response.headers.get("Content-Length")
        _require(length is None or length.isdigit() and int(length) == len(raw),
                 "RESPONSE_LENGTH_MISMATCH")
        return response.status, raw


def _page(value, *, ticker, day, number):
    _require(isinstance(value, dict) and type(value.get("code")) is int, "PARSE_FAILURE")
    _require(value["code"] == 200, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
        404: "PROVIDER_NOT_FOUND", 429: "RATE_LIMITED"}.get(value["code"], "PROVIDER_REJECTED"))
    body = value["data"]
    _require(isinstance(body, dict) and all(type(body.get(k)) is int for k in
        ("pageNum", "pageSize", "total", "pages")), "PAGINATION_MISMATCH")
    total, pages = body["total"], body["pages"]
    _require(body["pageNum"] == number and body["pageSize"] == PAGE_SIZE and total >= 0
        and pages == ((total + PAGE_SIZE - 1) // PAGE_SIZE if total else pages)
        and (total > 0 or pages in {0, 1}), "PAGINATION_MISMATCH")
    _require(pages <= MAX_PAGES, "PAGINATION_LIMIT")
    rows = body["records"]
    _require(isinstance(rows, list) and len(rows) == min(PAGE_SIZE, max(0, total - (number - 1) * PAGE_SIZE)),
             "PAGINATION_MISMATCH")
    normalized = []
    for row in rows:
        _require(isinstance(row, dict) and row.get("sec_code") == ticker, "IDENTITY_MISMATCH")
        aid, digest, title, published = (row.get(k) for k in
            ("announcement_id", "url_hash", "announcement_title", "announcement_time"))
        _require(isinstance(aid, str) and re.fullmatch(r"[0-9]{1,20}", aid)
            and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
            and isinstance(title, str) and 0 < len(title.strip()) <= 1024,
            "IDENTITY_MISMATCH")
        _require(isinstance(published, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", published),
                 "PROVIDER_TIME_INVALID")
        _require(datetime.strptime(published, "%Y-%m-%d %H:%M:%S").date() == day, "PROVIDER_DATE_MISMATCH")
        normalized.append({"announcement_id": aid, "ticker": ticker, "title": title,
            "provider_time_raw": published, "provider_timezone": "UNKNOWN",
            "url_hash": digest})
    return normalized, total, pages


def discover(*, ticker: str, announcement_date: date, output: Path,
             fetch=request_page, clock=now):
    """Retain each complete response; incomplete discovery cannot qualify a lead."""
    _require(isinstance(ticker, str) and re.fullmatch(r"[036][0-9]{5}", ticker), "REQUEST_IDENTITY")
    _require(type(announcement_date) is date, "REQUEST_DATE")
    started = clock()
    _require(announcement_date <= _clock(started).astimezone(ZoneInfo("Asia/Shanghai")).date(), "FUTURE_REQUEST_DATE")
    _require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    result = {"provider": "FTSHARE", "endpoint": ENDPOINT, "adapter_version": VERSION,
        "ticker": ticker, "announcement_date": announcement_date.isoformat(),
        "started_at": started, "retrieved_at": None, "status": "INCOMPLETE",
        "requests": [], "announcements": [], "coverage": "ONE_ISSUER_ONE_DATE_ONLY",
        "source_custody": "NOT_ESTABLISHED", "evidence_authority": "NONE",
        "research_execution_allowed": False, "investment_authority": "NONE",
        "automatic_retry": False, "auth_header_used": False}
    rows, expected, seen = [], None, set()
    last_clock = _clock(started)
    try:
        for number in range(1, MAX_PAGES + 1):
            params = {"date": announcement_date.strftime("%Y%m%d"), "sec_code": ticker,
                      "page": number, "page_size": PAGE_SIZE}
            event = {"parameters": params, "started_at": clock(), "http_status": None,
                     "provider_status": None, "status": "TRANSPORT_FAILURE"}
            result["requests"].append(event)
            _require(_clock(event["started_at"]) >= last_clock, "CLOCK_MISMATCH")
            status, raw = fetch(params)
            received = clock()
            _require(_clock(received) >= _clock(event["started_at"]), "CLOCK_MISMATCH")
            last_clock = _clock(received)
            _require(type(status) is int and 100 <= status <= 599 and isinstance(raw, bytes), "TRANSPORT_FAILURE")
            _require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
            name = f"page-{number}.json"
            (output / name).write_bytes(raw)
            event.update(http_status=status, retrieved_at=received, raw_path=name, bytes=len(raw),
                         raw_sha256=hashlib.sha256(raw).hexdigest(), status="RESPONSE_RETAINED")
            if status != 200:
                raise DiscoveryError({401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
                    404: "HTTP_NOT_FOUND", 429: "RATE_LIMITED"}.get(status, "HTTP_REJECTED"))
            value = _json(raw)
            if isinstance(value, dict) and type(value.get("code")) is int:
                event["provider_status"] = value["code"]
            page, total, pages = _page(value, ticker=ticker, day=announcement_date, number=number)
            _require(expected is None or expected == (total, pages), "PAGINATION_MISMATCH")
            expected = total, pages
            for row in page:
                _require(row["announcement_id"] not in seen, "DUPLICATE_ANNOUNCEMENT")
                seen.add(row["announcement_id"])
            rows.extend(page)
            event["status"] = "INDEX_PARSED_NOT_PRIMARY_EVIDENCE"
            if number >= pages:
                _require(len(rows) == total, "PAGINATION_MISMATCH")
                result.update(status="COMPLETE" if rows else "EMPTY", announcements=rows,
                              retrieved_at=received, total=total)
                break
    except DiscoveryError as exc:
        result["status"] = str(exc)
    except (URLError, TimeoutError, OSError):
        result["status"] = "TRANSPORT_FAILURE"
    except (ValueError, KeyError, TypeError, OverflowError, RecursionError):
        result["status"] = "PARSE_FAILURE"
    finally:
        result["finished_at"] = clock()
        if _clock(result["finished_at"]) < last_clock:
            result.update(status="CLOCK_MISMATCH", announcements=[])
        with (output / "discovery.json").open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return result
