"""One bounded source study of frozen stock discrepancies; never accept prices.

Requests supplies HTTP, the existing dump diagnostic validates the input report,
and existing identity/safe-JSON helpers bind evidence. No adjustment engine,
market download, production writer, retry or generic announcement crawler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from decision_kernel.adapters.cninfo import normalize_cninfo_announcement_page
from decision_kernel.identity import canonical_hash, canonical_json
from .hithink_dump_diagnostics import diagnose_inspection_report
from .hithink_dump_inspection import _file_hash, MAX_FILE_BYTES
from .hithink_dump_trial import _session, _check_response
from .sector_radar_audit import _check_safe_json

BASE = "https://fuyao.aicubes.cn"
EVENTS = BASE + "/api/a-share/corporate-actions/adjustment-factors"
HISTORY = BASE + "/api/a-share/prices/historical"
SYMBOLS = "https://www.cninfo.com.cn/new/data/szse_stock.json"
NOTICES = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
PDF_ORIGIN = "https://static.cninfo.com.cn/"
SOURCE_HASH = "668073931733d725abecb39a579495ebaad18a21b91f9b558be6a32fb366d5ce"
MAX_REQUESTS, MAX_BYTES, MAX_TOTAL = 24, 8 * 1024 * 1024, 32 * 1024 * 1024
TZ = ZoneInfo("Asia/Shanghai")
AUTHORITY = {"production_qualification": "NOT_ESTABLISHED", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE",
             "market_state_writes": 0, "events_created": 0}
PDF_PATH = re.compile(r"finalpage/[0-9]{4}-[0-9]{2}-[0-9]{2}/[0-9]+\.PDF", re.I)
# Reviewed search leads, not trading-status classifications. Fetch at most one
# uniquely latest matching original per sampled code; preserve the full query.
COVERAGE_KEYWORDS = {
    "000016.SZ": "停牌公告", "002731.SZ": "停牌", "002870.SZ": "停牌公告",
    "002998.SZ": "停牌公告", "301139.SZ": "停牌", "301266.SZ": "停牌",
    "600929.SH": "停牌", "688432.SH": "停牌",
    "603448.SH": "上市公告书", "920289.BJ": "上市公告书",
}
# Only the eleven still-unobtained document leads from the frozen gap review.
# Issuance documents are evidence leads, NOT an effective listing-status feed.
LISTING_KEYWORDS = {
    "301686.SZ": "初步询价及推介公告", "301689.SZ": "发行结果公告",
    "301699.SZ": "发行结果公告", "601091.SH": "初步询价及推介公告",
    "603448.SH": "上市公告书", "688801.SH": "发行公告", "688837.SH": "发行公告",
    "920201.BJ": "发行公告", "920268.BJ": "发行结果公告",
    "920269.BJ": "发行结果公告", "920298.BJ": "发行结果公告",
}
# Exact identity already present in run 33966231127/capture/response-16.json.
# A reviewed full original is selected, not a heuristic relaxation of date ties.
REVIEWED_LISTING_ORIGINAL = {
    "603448.SH": {"announcement_id": "1225547191",
                  "title": "天博智能首次公开发行股票主板上市公告书",
                  "publication_date": "2026-09-04",
                  "source_locator": PDF_ORIGIN + "finalpage/2026-09-04/1225547191.PDF"},
}
PROFILES = ("event-samples", "coverage-notices", "remaining-listings")


def _utc():
    return datetime.now(timezone.utc)


def _clock(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("AWARE_CAPTURE_CLOCK_REQUIRED")
    return value


def _notice_keywords(profile: str) -> dict[str, str]:
    if profile == "coverage-notices":
        return COVERAGE_KEYWORDS
    if profile == "remaining-listings":
        return LISTING_KEYWORDS
    raise ValueError("UNREVIEWED_STUDY_PROFILE")


def build_plan(report: dict, *, profile: str = "event-samples") -> dict:
    if profile not in PROFILES:
        raise ValueError("UNREVIEWED_STUDY_PROFILE")
    diagnostic = diagnose_inspection_report(report)
    raw_sessions = report["inspection"].get("expected_sessions")
    if not isinstance(raw_sessions, list) or len(raw_sessions) < 2:
        raise ValueError("EXPLICIT_SESSION_WINDOW_REQUIRED")
    sessions = [date.fromisoformat(day) for day in raw_sessions]
    if sessions != sorted(set(sessions)):
        raise ValueError("ORDERED_SESSION_WINDOW_REQUIRED")
    day = sessions[-1]
    if profile in {"coverage-notices", "remaining-listings"}:
        keywords = _notice_keywords(profile)
        gaps = set(diagnostic["coverage"]["missing_latest_or_unpriced_union"])
        gaps.update(row["thscode"] for row in diagnostic["bar_gaps"]["previous_bar"])
        selected = sorted(gaps.intersection(keywords))
        result = {"schema_version": 2 if profile == "coverage-notices" else 3, "profile": profile,
                  "source_report_hash": report["report_hash"],
                  "comparison_session": day.isoformat(), "provider_requests": [],
                  "notice_sample_codes": selected,
                  "notice_keywords": {code: keywords[code] for code in selected},
                  "unqueried_gap_codes": sorted(gaps.difference(selected)),
                  "selection_semantics": "BOUNDED_SOURCE_LEADS_NOT_TRADING_STATUS_OR_ELIGIBILITY",
                  "max_requests": MAX_REQUESTS,
                  "source_disposition": diagnostic["source_inspection_status"], **AUTHORITY}
        if profile == "remaining-listings":
            result["reviewed_originals"] = {code: dict(REVIEWED_LISTING_ORIGINAL[code])
                                            for code in selected if code in REVIEWED_LISTING_ORIGINAL}
        if (1 + 2 * len(selected) if selected else 0) > MAX_REQUESTS:
            raise ValueError("CASE_BUDGET_EXCEEDED_NO_TRUNCATION")
        result["plan_hash"] = canonical_hash(result)
        return result
    differences = diagnostic["field_summaries"]["raw_previous_close"]["all_differences"]
    if len(differences) > 16:
        raise ValueError("CASE_BUDGET_EXCEEDED_NO_TRUNCATION")
    requests = [{"id": "event-" + row["thscode"], "method": "GET", "url": EVENTS,
                 "params": {"thscode": row["thscode"], "from": day.isoformat(), "to": day.isoformat()}}
                for row in sorted(differences, key=lambda row: row["thscode"])]
    largest = diagnostic["field_summaries"]["turnover"]["largest_difference"]
    if largest is not None:
        millis = lambda d: str(int(datetime.combine(d, time(), tzinfo=TZ).timestamp() * 1000))
        requests.append({"id": "history-" + largest["thscode"], "method": "GET", "url": HISTORY,
                         "params": {"thscode": largest["thscode"], "interval": "1d", "adjust": "none",
                                    "start": millis(sessions[-2]), "end": millis(day + timedelta(days=1))}})
    # Two named cases cover ordinary cash and excluded treasury shares. They are
    # source-review samples, not all 15 cases or a general stock eligibility list.
    case_codes = {row["thscode"] for row in differences}
    notice_codes = [code for code in ("000408.SZ", "001316.SZ") if code in case_codes]
    result = {"schema_version": 1, "source_report_hash": report["report_hash"],
              "comparison_session": day.isoformat(), "provider_requests": requests,
              "notice_sample_codes": notice_codes, "max_requests": MAX_REQUESTS,
              "source_disposition": diagnostic["source_inspection_status"], **AUTHORITY}
    if len(requests) + (1 + 2 * len(notice_codes) if notice_codes else 0) > MAX_REQUESTS:
        raise ValueError("CASE_BUDGET_EXCEEDED_NO_TRUNCATION")
    result["plan_hash"] = canonical_hash(result)
    return result


def request_spec(spec: dict, *, api_key: str) -> tuple[int, bytes]:
    """Fixed supported origins only, fresh Requests session, no redirects/retries."""
    url, method, params = spec["url"], spec["method"], spec["params"]
    provider = url in {EVENTS, HISTORY}
    pdf = url.startswith(PDF_ORIGIN) and PDF_PATH.fullmatch(url[len(PDF_ORIGIN):]) is not None
    if not ((provider or url == SYMBOLS or pdf) and method == "GET" or url == NOTICES and method == "POST"):
        raise ValueError("UNREVIEWED_SOURCE_DESTINATION")
    if (url == SYMBOLS or pdf) and params:
        raise ValueError("UNEXPECTED_SOURCE_PARAMETERS")
    headers = {"Accept-Encoding": "identity", "Accept": "application/pdf" if pdf else "application/json"}
    if provider:
        if not api_key:
            raise ValueError("CREDENTIAL_REQUIRED")
        headers["X-api-key"] = api_key
    with _session() as session:
        with session.request(method, url, params=params if method == "GET" else None,
                             data=params if method == "POST" else None, headers=headers,
                             timeout=(10, 20), stream=True, allow_redirects=False) as response:
            status = response.status_code
            if type(status) is not int or not 100 <= status <= 599:
                raise ValueError("INVALID_HTTP_STATUS")
            if status != 200:
                return status, b""  # no error body, cookie, redirect or retry
            length = _check_response(response)
            if length is not None and length > MAX_BYTES:
                raise ValueError("SOURCE_BYTE_BUDGET_EXCEEDED")
            chunks, count = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                count += len(chunk)
                if count > MAX_BYTES:
                    raise ValueError("SOURCE_BYTE_BUDGET_EXCEEDED")
                chunks.append(chunk)
            if length is not None and count != length:
                raise ValueError("SOURCE_LENGTH_MISMATCH")
    return status, b"".join(chunks)


def notice_query(code: str, stock_list: dict, day: date) -> dict:
    records = stock_list.get("stockList")
    if not isinstance(records, list):
        raise ValueError("CNINFO_STOCK_LIST_REQUIRED")
    matches = [row for row in records if isinstance(row, dict) and row.get("code") == code[:6]]
    if len(matches) != 1 or not isinstance(matches[0].get("orgId"), str) or not re.fullmatch(r"[A-Za-z0-9]+", matches[0]["orgId"]):
        raise ValueError("CNINFO_EXACT_ORGANIZATION_UNAVAILABLE")
    return {"id": "notice-query-" + code, "url": NOTICES, "method": "POST", "params": {
        "pageNum": "1", "pageSize": "30", "column": "szse", "tabName": "fulltext", "plate": "",
        "stock": code[:6] + "," + matches[0]["orgId"], "searchkey": "权益分派实施公告", "secid": "",
        "category": "", "trade": "", "seDate": (day - timedelta(days=20)).isoformat() + "~" + day.isoformat(),
        "sortName": "", "sortType": "", "isHLtitle": "false"}}


def notice_pdf(code: str, payload: dict) -> dict:
    rows = payload.get("announcements")
    if payload.get("hasMore") is True or not isinstance(rows, list) or len(rows) > 30:
        raise ValueError("CNINFO_NOTICE_WINDOW_INCOMPLETE")
    matches = [row for row in rows if isinstance(row, dict) and row.get("secCode") == code[:6]
               and "2026" in str(row.get("announcementTitle", ""))
               and "权益分派实施公告" in str(row.get("announcementTitle", ""))]
    if len(matches) != 1:
        raise ValueError("CNINFO_NOTICE_SELECTION_AMBIGUOUS_OR_MISSING")
    relative = matches[0].get("adjunctUrl")
    if not isinstance(relative, str) or PDF_PATH.fullmatch(relative) is None:
        raise ValueError("CNINFO_ORIGINAL_PDF_PATH_REQUIRED")
    return {"id": "notice-pdf-" + code, "method": "GET", "url": PDF_ORIGIN + relative, "params": {}}


def coverage_notice_pdf(code: str, payload: dict, query: dict, *,
                        profile: str = "coverage-notices") -> dict:
    """Reuse CNINFO identity/date normalization; select a document, never a status."""
    keyword = _notice_keywords(profile).get(code)
    params = query["params"]
    if (keyword is None or params.get("searchkey") != keyword
            or not params.get("stock", "").startswith(code[:6] + ",")):
        raise ValueError("UNREVIEWED_COVERAGE_QUERY")
    if payload.get("hasMore") is not False:
        raise ValueError("CNINFO_NOTICE_WINDOW_INCOMPLETE")
    org_id = params["stock"].split(",", 1)[1]
    page = normalize_cninfo_announcement_page(payload, stock_code=code[:6], org_id=org_id)
    if page.total_announcement_count != len(page.announcements) or len(page.announcements) > 30:
        raise ValueError("CNINFO_NOTICE_WINDOW_INCOMPLETE")
    if profile == "remaining-listings" and any(
        row.get("secCode") != code[:6] or row.get("orgId") != org_id
        for row in payload.get("announcements") or []
    ):
        raise ValueError("EXPLICIT_LISTING_NOTICE_IDENTITY_REQUIRED")
    start, end = (date.fromisoformat(value) for value in params["seDate"].split("~"))
    candidates = []
    for item in page.announcements:
        if item.published_at is None or not start <= item.published_at.astimezone(TZ).date() <= end:
            raise ValueError("CNINFO_NOTICE_DATE_OUTSIDE_QUERY")
        if keyword in item.title:
            if profile == "remaining-listings" and not item.title.endswith(keyword):
                continue  # a pointer announcement is not the requested full document
            candidates.append(item)
    reviewed = REVIEWED_LISTING_ORIGINAL.get(code) if profile == "remaining-listings" else None
    if reviewed is not None:
        candidates = [item for item in candidates if item.announcement_id == reviewed["announcement_id"]
                      and item.title == reviewed["title"] and item.source_locator == reviewed["source_locator"]
                      and item.published_at.astimezone(TZ).date().isoformat() == reviewed["publication_date"]]
        if len(candidates) != 1:
            raise ValueError("REVIEWED_ORIGINAL_IDENTITY_CHANGED_OR_MISSING")
    if not candidates:
        raise ValueError("CNINFO_NOTICE_SELECTION_AMBIGUOUS_OR_MISSING")
    latest = max(item.published_at for item in candidates)
    selected = [item for item in candidates if item.published_at == latest]
    if len(selected) != 1:
        raise ValueError("CNINFO_NOTICE_SELECTION_AMBIGUOUS_OR_MISSING")
    url = selected[0].source_locator
    if not url.startswith(PDF_ORIGIN) or PDF_PATH.fullmatch(url[len(PDF_ORIGIN):]) is None:
        raise ValueError("CNINFO_ORIGINAL_PDF_PATH_REQUIRED")
    return {"id": "notice-pdf-" + code, "method": "GET", "url": url, "params": {}}


def capture_sources(plan: dict, root: Path, *, api_key: str, request=None, now=_utc,
                    provenance: str = "LIVE_SOURCE_STUDY") -> dict:
    if canonical_hash({k: v for k, v in plan.items() if k != "plan_hash"}) != plan.get("plan_hash"):
        raise ValueError("PLAN_HASH_MISMATCH")
    if provenance not in {"LIVE_SOURCE_STUDY", "SYNTHETIC_TEST_ONLY"} or (request is not None and provenance != "SYNTHETIC_TEST_ONLY"):
        raise ValueError("INJECTED_REQUEST_MUST_BE_SYNTHETIC")
    if root.exists() or "decision-state" in root.resolve().parts:
        raise ValueError("NEW_ISOLATED_OUTPUT_REQUIRED")
    profile = plan.get("profile", "event-samples")
    coverage = profile in {"coverage-notices", "remaining-listings"}
    if profile not in PROFILES:
        raise ValueError("UNREVIEWED_STUDY_PROFILE")
    if coverage:
        codes = plan["notice_sample_codes"]
        keywords = _notice_keywords(profile)
        schema = 2 if profile == "coverage-notices" else 3
        if (plan.get("schema_version") != schema or plan["provider_requests"]
                or len(codes) > len(keywords) or codes != sorted(set(codes))
                or not set(codes).issubset(keywords)
                or plan.get("notice_keywords") != {code: keywords[code] for code in codes}
                or (1 + 2 * len(codes) if codes else 0) > MAX_REQUESTS):
            raise ValueError("COVERAGE_PROFILE_MUST_REMAIN_PUBLIC_ONLY_AND_BOUNDED")
        if profile == "remaining-listings" and plan.get("reviewed_originals") != {
            code: REVIEWED_LISTING_ORIGINAL[code] for code in codes if code in REVIEWED_LISTING_ORIGINAL
        }:
            raise ValueError("REVIEWED_ORIGINAL_PLAN_CHANGED")
    elif len(plan["provider_requests"]) > 17 or len(plan["notice_sample_codes"]) > 2:
        raise ValueError("PLAN_BUDGET_INVALID")
    root.mkdir(parents=True)
    (root / "plan.json").write_text(canonical_json(plan) + "\n", encoding="utf-8")
    request = request or (lambda spec: request_spec(spec, api_key=api_key))
    records, problems, files = [], [], []
    started = _clock(now())
    last_clock, total = started, 0

    def get(spec):
        nonlocal total, last_clock
        if len(records) >= MAX_REQUESTS:
            raise ValueError("REQUEST_BUDGET_EXCEEDED")
        before = _clock(now())
        if before < last_clock:
            raise ValueError("CAPTURE_CLOCK_REGRESSED")
        record = {**spec, "requested_at": before, "http_status": None, "file": None, "error_type": None}
        records.append(record)
        try:
            status, raw = request(spec)
            record["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
            if status != 200 or record["http_status"] is None:
                raise ValueError("SOURCE_HTTP_REJECTED")
            if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES or total + len(raw) > MAX_TOTAL:
                raise ValueError("SOURCE_BODY_BUDGET_OR_TYPE")
            if api_key and api_key.encode() in raw:
                raise ValueError("CREDENTIAL_IN_SOURCE_BODY")
            is_pdf = spec["url"].startswith(PDF_ORIGIN)
            if is_pdf:
                if not raw.startswith(b"%PDF-"):
                    raise ValueError("PDF_CONTAINER_REQUIRED")
                payload = None
            else:
                payload = json.loads(raw.decode("utf-8"), parse_float=Decimal,
                                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
                if not isinstance(payload, dict):
                    raise ValueError("JSON_OBJECT_REQUIRED")
                _check_safe_json(payload, api_key)
            name = f"response-{len(records):02d}." + ("pdf" if is_pdf else "json")
            (root / name).write_bytes(raw)
            total += len(raw)
            item = {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            files.append(item)
            record["file"] = name
            if spec["url"] in {EVENTS, HISTORY}:
                if type(payload.get("code")) is not int or payload["code"] != 0:
                    raise ValueError("PROVIDER_REJECTED")
                if not isinstance(payload.get("data"), dict) or not isinstance(payload["data"].get("item"), list):
                    raise ValueError("PROVIDER_DATA_ITEMS_REQUIRED")
                if spec["url"] == EVENTS and payload["data"].get("thscode") != spec["params"]["thscode"]:
                    raise ValueError("EVENT_SOURCE_IDENTITY_DISAGREES")
            return payload
        except Exception as exc:
            # Retain failure class/status only, not request headers or arbitrary exception text.
            record["error_type"] = type(exc).__name__
            problems.append({"id": spec["id"], "error_type": type(exc).__name__})
            return None
        finally:
            last_clock = _clock(now())
            if last_clock < before:
                raise ValueError("CAPTURE_CLOCK_REGRESSED")
            record["completed_at"] = last_clock

    for spec in plan["provider_requests"]:
        get(spec)
    if plan["notice_sample_codes"]:
        symbols = get({"id": "cninfo-symbols", "url": SYMBOLS, "method": "GET", "params": {}})
        for code in plan["notice_sample_codes"]:
            try:
                query = notice_query(code, symbols or {}, date.fromisoformat(plan["comparison_session"]))
                if coverage:
                    query["params"]["searchkey"] = plan["notice_keywords"][code]
                payload = get(query)
                if payload is not None:
                    get(coverage_notice_pdf(code, payload, query, profile=profile) if coverage else notice_pdf(code, payload))
            except ValueError as exc:
                problems.append({"id": "notice-selection-" + code, "error_type": str(exc)})
    result = {"schema_version": 1, "semantics": "FROZEN_CASE_SOURCE_COLLECTION_NOT_PRICE_ACCEPTANCE",
              "provenance": provenance, "started_at": started, "completed_at": _clock(now()),
              "source_report_hash": plan["source_report_hash"], "plan_hash": plan["plan_hash"],
              "source_disposition": plan["source_disposition"], "requests": records, "files": files,
              "problems": problems, "status": "INCOMPLETE_SOURCE_STUDY" if problems else "CAPTURE_COMPLETE_REVIEW_REQUIRED",
              "event_publication_time": "NOT_PROVEN_BY_CURRENT_EVENT_API",
              "causes_automatically_accepted": 0, **AUTHORITY}
    if coverage:
        result["study_profile"] = profile
        result["coverage_status_classification"] = "REVIEW_REQUIRED_NO_AUTOMATIC_EXCLUSIONS"
    result["study_hash"] = canonical_hash(result)
    (root / "report.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
    (root / "summary.md").write_text(f"# Frozen stock-field source study\n\n{result['status']}\n\n"
        f"Requests: {len(records)}; retained bodies: {len(files)}; problems: {len(problems)}.\n\n"
        "Source data remains DIFFERENCES_REQUIRE_REVIEW. No price correction or stock-panel adoption.\n\n"
        "SHADOW OBSERVATION ONLY. Human / Research / Investment authority = NONE.\n", encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, default="event-samples")
    args = parser.parse_args(argv)
    report_path = args.frozen / "offline-inspection.json"
    _file_hash(report_path, 16 * 1024 * 1024)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("report_hash") != SOURCE_HASH:
        parser.error("this reviewed study requires the exact run-33959190974 offline report")
    plan = build_plan(report, profile=args.profile)
    for key, name in {"parquet": "daily-k-10d.parquet", "sessions": "sessions.json",
                      "universe": "universe.json", "snapshot": "snapshot.json"}.items():
        if _file_hash(args.frozen / "capture" / name, MAX_FILE_BYTES) != report["input_file_sha256"][key]:
            parser.error("frozen original input hash disagrees")
    api_key = os.environ.get("HITHINK_FINANCE_API_KEY", "") if args.profile == "event-samples" else ""
    if args.profile == "event-samples" and not api_key:
        parser.error("HiThink credential required; no substitute source")
    result = capture_sources(plan, args.output, api_key=api_key)
    print(result["status"], "production qualification = NOT_ESTABLISHED")
    return 2 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
