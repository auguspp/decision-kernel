"""Three fixed FTShare company inputs for original source preparation, not Evidence.

Reuse retained JSON/decimal/clock primitives. Contracts, holder counts and named
holder changes have DIFFERENT pagination, identity and economic meanings.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo

from . import ftshare_discovery as discovery
from .ftshare_financial import decode, raw_json

VERSION = "ftshare-company-events-v1"
BASE = "https://market.ft.tech/gateway/api/v1/market/data/"
ROUTES = {"contracts": "corporate/contract/by-symbol", "holder_counts": "holder/stock-holder-nums",
          "holder_changes": "holder/stock-share-chg"}
PAGE_SIZE, MAX_PAGES, MAX_BYTES = 200, 4, 2 * 1024 * 1024
require, DataError = discovery._require, discovery.DiscoveryError
STOPS = {"AUTHENTICATION_UNAVAILABLE", "AUTHENTICATION_FAILED", "ENTITLEMENT_DENIED", "RATE_LIMITED",
         "CREDENTIAL_REFLECTION_REJECTED", "REDIRECT_REJECTED"}


def valid_ticker(ticker):
    return isinstance(ticker, str) and re.fullmatch(r"(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)", ticker)


def parameters(family, ticker, page):
    require(family in ROUTES and valid_ticker(ticker) and type(page) is int
            and 1 <= page <= MAX_PAGES, "REQUEST_IDENTITY")
    if family == "holder_counts":
        require(page == 1, "REQUEST_IDENTITY")
        return {"stock_code": ticker}  # Documented single-issuer ALL-history mode.
    return {"symbol" if family == "contracts" else "stock_code": ticker[:6] if family == "contracts" else ticker,
            "page": page, "page_size": PAGE_SIZE}


def request_page(family, params):
    """The stored key goes only to these three fixed official routes, never logs."""
    require(family in ROUTES and isinstance(params, dict), "REQUEST_IDENTITY")
    ticker = params.get("stock_code")
    if family == "contracts":
        symbol = params.get("symbol")
        require(isinstance(symbol, str) and re.fullmatch(r"[036][0-9]{5}", symbol), "REQUEST_IDENTITY")
        ticker = symbol + (".SH" if symbol.startswith("6") else ".SZ")
    require(params == parameters(family, ticker, params.get("page", 1)), "REQUEST_IDENTITY")
    key = os.environ.get("FTSHARE_API_KEY")
    require(isinstance(key, str) and bool(key) and key.isascii()
            and all(32 < ord(c) < 127 for c in key), "AUTHENTICATION_UNAVAILABLE")
    req = Request(BASE + ROUTES[family] + "?" + urlencode(params), headers={
        "FTSHARE_API_KEY": key, "Accept": "application/json", "Accept-Encoding": "identity",
        "User-Agent": "decision-kernel/" + VERSION})
    try:
        response = build_opener(discovery._NoRedirect()).open(req, timeout=20)
    except HTTPError as exc:
        response = exc
    with response:
        require(response.geturl() == req.full_url, "REDIRECT_REJECTED")
        require(response.headers.get("Content-Encoding", "identity") == "identity", "ENCODING_REJECTED")
        raw = response.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
        require(key.encode() not in raw, "CREDENTIAL_REFLECTION_REJECTED")
        length = response.headers.get("Content-Length")
        require(length is None or length.isdigit() and int(length) == len(raw), "RESPONSE_LENGTH_MISMATCH")
        return response.status, raw


def page_rows(value, family, page):
    require(isinstance(value, dict) and type(value.get("code")) is int, "PARSE_FAILURE")
    # Official company contract examples use 0; retained gateway probes use 200.
    require(value["code"] in {0, 200}, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
        404: "PROVIDER_NOT_FOUND", 429: "RATE_LIMITED"}.get(value["code"], "PROVIDER_REJECTED"))
    body = value.get("data")
    require(isinstance(body, dict), "PARSE_FAILURE")
    if family == "contracts":
        rows, total, pages = (body.get(k) for k in ("records", "total", "pages"))
        require(body.get("pageNum") == page and body.get("pageSize") == PAGE_SIZE,
                "PAGINATION_MISMATCH")
    else:
        rows, total, pages = (body.get(k) for k in ("items", "total_items", "total_pages"))
    require(type(total) is int and type(pages) is int and total >= 0 and pages >= 0,
            "PAGINATION_MISMATCH")
    if family == "holder_counts":
        require(page == 1 and pages in {0, 1} and (total == 0 or pages == 1), "PAGINATION_MISMATCH")
        require(total <= PAGE_SIZE * MAX_PAGES, "PAGINATION_LIMIT")
        expected = total
    else:
        require(pages == (total + PAGE_SIZE - 1) // PAGE_SIZE if total else pages in {0, 1},
                "PAGINATION_MISMATCH")
        require(pages <= MAX_PAGES, "PAGINATION_LIMIT")
        expected = min(PAGE_SIZE, max(0, total - (page - 1) * PAGE_SIZE))
    require(isinstance(rows, list) and len(rows) == expected, "PAGINATION_MISMATCH")
    return rows, total, pages


def capture_family(*, family, ticker, output, fetch=request_page, clock=discovery.now):
    parameters(family, ticker, 1)
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    started = clock()
    last = discovery._clock(started)
    result = {"provider": "FTSHARE", "family": family, "ticker": ticker,
        "endpoint": BASE + ROUTES[family], "adapter_version": VERSION, "started_at": started,
        "status": "INCOMPLETE", "requests": [], "rows": [], "automatic_retry": False,
        "coverage": "BOUNDED_SINGLE_ISSUER_PROVIDER_RETURN_NOT_ALL_ISSUER_DISCLOSURES"}
    rows, expected, seen = [], None, set()
    try:
        for number in range(1, (1 if family == "holder_counts" else MAX_PAGES) + 1):
            event = {"parameters": parameters(family, ticker, number), "started_at": clock(),
                     "http_status": None, "provider_status": None, "status": "TRANSPORT_FAILURE"}
            result["requests"].append(event)
            require(discovery._clock(event["started_at"]) >= last, "CLOCK_MISMATCH")
            status, raw = fetch(family, event["parameters"])
            received = clock()
            last = discovery._clock(received)
            require(last >= discovery._clock(event["started_at"]), "CLOCK_MISMATCH")
            require(type(status) is int and 100 <= status <= 599 and isinstance(raw, bytes), "TRANSPORT_FAILURE")
            require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
            name = f"page-{number}.json"
            (output / name).write_bytes(raw)
            event.update(http_status=status, retrieved_at=received, path=name, bytes=len(raw),
                         sha256=hashlib.sha256(raw).hexdigest(), status="RAW_RESPONSE_RETAINED")
            value = None
            try:
                value = decode(raw)
                if isinstance(value, dict) and type(value.get("code")) is int:
                    event["provider_status"] = value["code"]
            except (ValueError, TypeError, UnicodeError):
                if status == 200:
                    raise
            require(status == 200, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
                404: "HTTP_NOT_FOUND", 429: "RATE_LIMITED"}.get(status, "HTTP_REJECTED"))
            page, total, pages = page_rows(value, family, number)
            require(expected is None or expected == (total, pages), "PAGINATION_MISMATCH")
            expected = total, pages
            field = {"contracts": "security_code", "holder_counts": "stock_code", "holder_changes": "trade_code"}[family]
            for index, row in enumerate(page):
                require(isinstance(row, dict) and row.get(field) == (ticker if family == "holder_counts" else ticker[:6]),
                        "IDENTITY_MISMATCH")
                digest = hashlib.sha256(raw_json(row)).hexdigest()
                require(digest not in seen, "DUPLICATE_RECORD")
                seen.add(digest)
                rows.append({"provider_fields": row, "raw_page": name, "row_index": index,
                             "raw_sha256": event["sha256"], "retrieved_at": received})
            event["status"] = "PROVIDER_DATA_PARSED_NOT_EVIDENCE"
            if number >= pages:
                require(len(rows) == total, "PAGINATION_MISMATCH")
                result.update(status="COMPLETE" if rows else "EMPTY", rows=rows, total=total)
                break
    except DataError as exc:
        result["status"] = str(exc)
    except (URLError, OSError, TimeoutError):
        result["status"] = "TRANSPORT_FAILURE"
    except (ValueError, TypeError, KeyError, OverflowError):
        result["status"] = "PARSE_FAILURE"
    finally:
        result["finished_at"] = clock()
        require(discovery._clock(result["finished_at"]) >= last, "CLOCK_MISMATCH")
        (output / "capture.json").write_bytes(raw_json(result))
    return result


def day(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "EVENT_DATE_UNKNOWN")
    return date.fromisoformat(value)


def window_context(capture, *, start_date, end_date):
    """Select by publication date, NOT signing/holding date or historical PIT."""
    family = capture["family"]
    result = {"family": family, "capture_status": capture["status"], "status": "SOURCE_UNAVAILABLE",
              "records": [], "excluded_outside_window": 0}
    if capture["status"] not in {"COMPLETE", "EMPTY"}:
        return result
    try:
        selected = []
        for record in capture["rows"]:
            row = record["provider_fields"]
            published = day(row.get({"contracts": "dim_rdate", "holder_counts": "publish_date",
                                     "holder_changes": "announcement_date"}[family]))
            require(published <= discovery._clock(record["retrieved_at"]).astimezone(ZoneInfo("Asia/Shanghai")).date(),
                    "FUTURE_PUBLICATION")
            if not start_date <= published <= end_date:
                result["excluded_outside_window"] += 1
                continue
            details = {"publish_date": published.isoformat(), "publish_time_precision": "DAY",
                "publish_timezone": "UNKNOWN", "available_at": record["retrieved_at"],
                "historical_available_at": "NOT_ESTABLISHED", "economic_acceptance": "NOT_ESTABLISHED"}
            if family == "contracts":
                signed = row.get("sign_date")
                require(signed is None or day(signed) <= published, "SIGNING_AFTER_PUBLICATION_REVIEW_REQUIRED")
                value = row.get("amounts")
                require(value is None or type(value) in {int, str, Decimal}, "AMOUNT_INVALID")
                require(value is None or len(str(value)) <= 128 and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", str(value)), "AMOUNT_INVALID")
                details.update(sign_date=signed, contract_amount={"value": None if value is None else str(value),
                    "unit": "PROVIDER_YUAN_CURRENCY_UNVERIFIED", "status": "UNKNOWN" if value is None else "PROVIDER_REPORTED"},
                    meaning="CONTRACT_NOT_REVENUE_PROFIT_OR_CASH")
            elif family == "holder_counts":
                report = day(row.get("report_date"))
                require(report <= published, "HOLDING_DATE_AFTER_PUBLICATION")
                count = row.get("holder_num")
                require(type(count) is int and count >= 0, "HOLDER_COUNT_INVALID")
                details.update(report_date=report.isoformat(), holder_count=count, unit="HOLDERS",
                               meaning="COUNT_NOT_NAMED_HOLDER_TRADES_OR_FUND_FLOW")
            else:
                direction = row.get("shareholding_change_info")
                require(direction in {"增持", "减持"} and isinstance(row.get("holder_name"), str)
                        and bool(row["holder_name"].strip()), "HOLDER_CHANGE_IDENTITY")
                begin, end = day(row.get("change_start_date")), day(row.get("change_end_date"))
                require(begin <= end, "CHANGE_DATE_ORDER")
                details.update(holder_name=row["holder_name"], direction=direction,
                    change_start_date=begin.isoformat(), change_end_date=end.isoformat(),
                    completion="NOT_ESTABLISHED", quantity_unit="UNKNOWN_NOT_USED_IN_ARITHMETIC",
                    meaning="PROVIDER_CHANGE_DESCRIPTION_NOT_VERIFIED_COMPLETION_OR_INVESTMENT_SIGNAL")
            selected.append({**decode(raw_json(record)), **details})
        result.update(records=selected, status="SECONDARY_CONTEXT_READY" if selected else "NO_RECORDS_IN_PUBLICATION_WINDOW")
    except (DataError, ValueError, TypeError, KeyError) as exc:
        result.update(status=str(exc) if isinstance(exc, DataError) else "PARSE_FAILURE", records=[])
    return result


def prepare(*, ticker, start_date, end_date, output, fetch=request_page, clock=discovery.now):
    require(valid_ticker(ticker) and type(start_date) is date and type(end_date) is date
            and start_date <= end_date and (end_date - start_date).days <= 366, "REQUEST_IDENTITY_OR_WINDOW")
    started = clock()
    require(end_date <= discovery._clock(started).astimezone(ZoneInfo("Asia/Shanghai")).date(), "FUTURE_REQUEST_DATE")
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    result = {"kind": "FTSHARE_COMPANY_EVENT_SECONDARY_CONTEXT", "adapter_version": VERSION,
        "ticker": ticker, "publication_window": [start_date.isoformat(), end_date.isoformat()],
        "started_at": started, "families": {}, "model_calls": 0, "pdf_calls": 0,
        "automatic_retry": False, "source_custody": "NOT_ESTABLISHED", "research_execution_allowed": False,
        "investment_authority": "NONE", "usage": "EXISTING_QUESTION_FORMATION_AND_SECONDARY_CONTEXT_ONLY"}
    stopped = False
    for family in ROUTES:
        if stopped:
            result["families"][family] = {"family": family, "status": "NOT_ATTEMPTED_AFTER_PROVIDER_STOP", "records": []}
            continue
        captured = capture_family(family=family, ticker=ticker, output=output/family, fetch=fetch, clock=clock)
        result["families"][family] = window_context(captured, start_date=start_date, end_date=end_date)
        stopped = captured["status"] in STOPS
    result["status"] = "COMPANY_CONTEXT_PREPARED_NOT_ADMITTED" if all(
        item["status"] in {"SECONDARY_CONTEXT_READY", "NO_RECORDS_IN_PUBLICATION_WINDOW"}
        for item in result["families"].values()) else "PARTIAL_COMPANY_CONTEXT"
    result["finished_at"] = clock()
    (output / "company-event-context.json").write_bytes(raw_json(result))
    return result
