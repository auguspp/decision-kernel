"""Five FTShare financial inputs for existing source preparation, not Evidence.

Reuse the official fixed HTTP/stock-code contract and existing discovery I/O
primitives. No all-market query, default-provider switch, PDF or model call.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo

from . import ftshare_discovery as discovery

VERSION = "ftshare-financial-context-v1"
BASE = "https://market.ft.tech/gateway/api/v1/market/data/finance/"
ROUTES = {"balance": "balance", "income": "income", "cashflow": "cashflow",
          "forecast": "stock-performance-forecast", "express": "stock-performance-express"}
PAGE_SIZE, MAX_PAGES, MAX_BYTES = 200, 4, 2 * 1024 * 1024
REPORT_TYPES = {"q1": (3, 31), "q2": (6, 30), "q3": (9, 30), "annual": (12, 31)}
# Official financial Skill field contracts; provider labels are not issuer proof.
METRICS = {
    "balance": {"t_assets": "资产总计", "t_liability": "负债总计", "t_equity": "所有者权益合计",
        "cash_equivalents": "货币资金", "account_receivable": "应收账款", "inventory": "存货",
        "accounts_payable": "应付账款", "t_fixed_assets": "固定资产合计"},
    "income": {"t_revenue": "营业总收入", "cost": "营业成本（供应商定义）", "t_cost": "营业总支出",
        "sale_expense": "销售费用", "manag_expense": "管理费用", "financial_cost": "财务费用",
        "profit": "营业利润", "t_profit": "利润总额", "n_profit": "净利润"},
    "cashflow": {"net_oper_cash_flow": "经营活动现金流量净额", "net_invest_cash_flow": "投资活动现金流量净额",
        "net_fin_cash_flow": "筹资活动现金流量净额", "cash_equ_inc": "现金及现金等价物净增加额",
        "goods_sale_render_service_cash": "销售商品、提供劳务收到的现金",
        "fix_intan_long_pay_cash": "购建长期资产支付的现金", "invest_proceeds": "取得投资收益收到的现金"},
}
require = discovery._require
DataError = discovery.DiscoveryError


def raw_json(value):
    # Decimal JSON tokens are represented as exact decimal strings, never floats.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, default=str,
                       allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def decode(raw):
    discovery._json(raw)  # Existing duplicate-key/nonfinite/UTF-8 rejection.
    return json.loads(raw, parse_float=Decimal)


def request_page(family, parameters):
    """Use only the existing named secret, on the documented fixed FTShare host."""
    require(family in ROUTES, "FINANCIAL_ROUTE_INVALID")
    key = os.environ.get("FTSHARE_API_KEY")
    require(isinstance(key, str) and bool(key) and key.isascii()
            and all(32 < ord(c) < 127 for c in key), "AUTHENTICATION_UNAVAILABLE")
    req = Request(BASE + ROUTES[family] + "?" + urlencode(parameters), headers={
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


def page_rows(value, number):
    require(isinstance(value, dict) and type(value.get("code")) is int, "PARSE_FAILURE")
    require(value["code"] == 200, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
        404: "PROVIDER_NOT_FOUND", 429: "RATE_LIMITED"}.get(value["code"], "PROVIDER_REJECTED"))
    body = value.get("data")
    require(isinstance(body, dict), "PARSE_FAILURE")
    rows, total, pages = (body.get(k) for k in ("items", "total_items", "total_pages"))
    require(type(total) is int and type(pages) is int and total >= 0 and pages >= 0,
            "PAGINATION_MISMATCH")
    require(pages == (total + PAGE_SIZE - 1) // PAGE_SIZE if total else pages in {0, 1},
            "PAGINATION_MISMATCH")
    require(pages <= MAX_PAGES, "PAGINATION_LIMIT")
    require(isinstance(rows, list) and len(rows) == min(PAGE_SIZE, max(0, total - (number - 1) * PAGE_SIZE)),
            "PAGINATION_MISMATCH")
    return rows, total, pages


def capture_family(*, family, ticker, output, fetch=request_page, clock=discovery.now):
    """Retain a bounded complete single-issuer return, including other periods.

    stock_code selects the provider's single-issuer mode. Do not claim that
    adding year/report_type would constrain that mode. Local period selection
    is performed separately over the complete retained return.
    """
    require(family in ROUTES and isinstance(ticker, str)
            and re.fullmatch(r"(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)", ticker), "REQUEST_IDENTITY")
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    started = clock()
    last = discovery._clock(started)
    result = {"provider": "FTSHARE", "family": family, "endpoint": BASE + ROUTES[family],
        "adapter_version": VERSION, "ticker": ticker, "started_at": started,
        "status": "INCOMPLETE", "requests": [], "rows": [], "automatic_retry": False,
        "coverage": "SINGLE_ISSUER_PROVIDER_RETURN_NOT_ALL_ISSUER_DISCLOSURES",
        "evidence_authority": "NONE", "research_execution_allowed": False}
    rows, expected, seen = [], None, set()
    try:
        for number in range(1, MAX_PAGES + 1):
            params = {"stock_code": ticker, "page": number, "page_size": PAGE_SIZE}
            event = {"parameters": params, "started_at": clock(), "http_status": None,
                     "provider_status": None, "status": "TRANSPORT_FAILURE"}
            result["requests"].append(event)
            require(discovery._clock(event["started_at"]) >= last, "CLOCK_MISMATCH")
            status, raw = fetch(family, params)
            received = clock()
            last = discovery._clock(received)
            require(last >= discovery._clock(event["started_at"]), "CLOCK_MISMATCH")
            require(type(status) is int and 100 <= status <= 599 and isinstance(raw, bytes), "TRANSPORT_FAILURE")
            require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
            name = f"page-{number}.json"
            (output / name).write_bytes(raw)
            event.update(http_status=status, retrieved_at=received, path=name, bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), status="RAW_RESPONSE_RETAINED")
            if status != 200:
                raise DataError({401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
                    404: "HTTP_NOT_FOUND", 429: "RATE_LIMITED"}.get(status, "HTTP_REJECTED"))
            value = decode(raw)
            if isinstance(value, dict) and type(value.get("code")) is int:
                event["provider_status"] = value["code"]
            page, total, pages = page_rows(value, number)
            require(expected is None or expected == (total, pages), "PAGINATION_MISMATCH")
            expected = total, pages
            for index, row in enumerate(page):
                require(isinstance(row, dict) and row.get("stock_code") == ticker, "IDENTITY_MISMATCH")
                digest = hashlib.sha256(raw_json(row)).hexdigest()
                require(digest not in seen, "DUPLICATE_RECORD")
                seen.add(digest)
                rows.append({"provider_fields": row, "raw_page": name, "row_index": index,
                             "raw_sha256": event["sha256"], "retrieved_at": received})
            event["status"] = "PROVIDER_DATA_PARSED_NOT_EVIDENCE"
            if number >= pages:
                require(len(rows) == total, "PAGINATION_MISMATCH")
                result.update(status="COMPLETE" if rows else "EMPTY", total=total,
                              rows=rows, retrieved_at=received)
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


def period_context(capture, *, year, report_type, report_form="合并未调整"):
    """Pure secondary context; dates and statement variants never disappear."""
    require(type(year) is int and 1990 <= year <= 2100 and report_type in REPORT_TYPES
            and report_form in {"合并未调整", "合并调整"}, "REQUEST_PERIOD_OR_FORM")
    family = capture["family"]
    require(family in ROUTES, "FINANCIAL_ROUTE_INVALID")
    result = {"family": family, "ticker": capture["ticker"], "year": year, "report_type": report_type,
        "period_start": None if family == "balance" else date(year, 1, 1).isoformat(),
        "period_end": date(year, *REPORT_TYPES[report_type]).isoformat(),
        "period_semantics": "POINT_IN_TIME" if family == "balance" else "YEAR_TO_DATE_NOT_SINGLE_QUARTER",
        "requested_report_form": report_form if family in METRICS else "NOT_APPLICABLE",
        "capture_status": capture["status"], "status": "SOURCE_UNAVAILABLE", "records": [],
        "excluded_other_periods": 0, "excluded_other_forms": 0,
        "source_authority": "PROVIDER_SECONDARY_DATA_NOT_PRIMARY_EVIDENCE"}
    if capture["status"] not in {"COMPLETE", "EMPTY"}:
        return result
    try:
        now = discovery._clock(capture["finished_at"])
        require(date(year, *REPORT_TYPES[report_type]) <= now.astimezone(ZoneInfo("Asia/Shanghai")).date(),
                "REPORT_PERIOD_IN_FUTURE")
        selected = []
        for record in capture["rows"]:
            row = record["provider_fields"]
            require(row.get("stock_code") == capture["ticker"], "IDENTITY_MISMATCH")
            require(type(row.get("year")) is int and isinstance(row.get("report_type"), str), "REPORT_PERIOD_UNKNOWN")
            if row["year"] != year or row["report_type"] != report_type:
                result["excluded_other_periods"] += 1
                continue
            form = row.get("detail_report_type") if family == "cashflow" else row.get("report_form_type")
            if family in METRICS:
                require(form in {"合并未调整", "合并调整"}, "REPORT_FORM_UNKNOWN")
                if form != report_form:
                    result["excluded_other_forms"] += 1
                    continue
            published = row.get("publish_date")
            require(isinstance(published, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", published),
                    "PUBLISH_DATE_UNKNOWN")
            require(date.fromisoformat(published) <= discovery._clock(record["retrieved_at"]).astimezone(
                    ZoneInfo("Asia/Shanghai")).date(), "FUTURE_PUBLICATION")
            if family in METRICS:
                require(date.fromisoformat(published) >= date(year, *REPORT_TYPES[report_type]),
                        "PUBLICATION_BEFORE_PERIOD_END")
            metrics = {}
            for field, label in METRICS.get(family, {}).items():
                value = row.get(field)
                require(value is None or type(value) in {int, Decimal, str}, "METRIC_TYPE_INVALID")
                if value is not None:
                    require(re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", str(value)) is not None, "METRIC_TYPE_INVALID")
                    require(Decimal(str(value)).is_finite(), "METRIC_TYPE_INVALID")
                metrics[field] = {"label": label, "unit": "CNY", "value": None if value is None else str(value),
                                  "status": "UNKNOWN" if value is None else "PROVIDER_REPORTED_NOT_VERIFIED"}
            selected.append({**record, "publish_date": published, "publish_time_precision": "DAY",
                "publish_timezone": "UNKNOWN", "historical_available_at": "NOT_ESTABLISHED",
                "available_at": record["retrieved_at"], "report_form": form,
                "metrics": metrics,
                "unmapped_fields_meaning": "ORIGINAL_PROVIDER_FIELDS_NOT_RELABELLED_OR_USED_IN_ARITHMETIC"})
        result["records"] = selected
        result["status"] = "TARGET_PERIOD_NOT_RETURNED" if not selected else (
            "MULTIPLE_REPORT_VERSIONS_REVIEW_REQUIRED" if family in METRICS and len(selected) != 1
            else "SECONDARY_CONTEXT_READY")
    except (DataError, ValueError, TypeError, KeyError) as exc:
        result.update(status=str(exc) if isinstance(exc, DataError) else "PARSE_FAILURE", records=[])
    return result


def prepare(*, ticker, year, report_type, output, report_form="合并未调整",
            fetch=request_page, clock=discovery.now):
    """Prepare one issuer's five fixed financial families, without a model call."""
    require(type(year) is int and 1990 <= year <= 2100 and report_type in REPORT_TYPES
            and report_form in {"合并未调整", "合并调整"}, "REQUEST_PERIOD_OR_FORM")
    require(isinstance(ticker, str) and re.fullmatch(r"(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)", ticker), "REQUEST_IDENTITY")
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    started = clock()
    require(date(year, *REPORT_TYPES[report_type]) <= discovery._clock(started).astimezone(
        ZoneInfo("Asia/Shanghai")).date(), "REPORT_PERIOD_IN_FUTURE")
    result = {"kind": "FTSHARE_FINANCIAL_SECONDARY_CONTEXT", "adapter_version": VERSION,
        "ticker": ticker, "year": year, "report_type": report_type, "started_at": started,
        "status": "INCOMPLETE", "families": {}, "model_calls": 0, "pdf_calls": 0,
        "source_custody": "NOT_ESTABLISHED", "research_execution_allowed": False,
        "investment_authority": "NONE", "automatic_retry": False,
        "usage": "QUESTION_FORMATION_AND_SECONDARY_RESEARCH_CONTEXT_ONLY",
        "limitations": ["Provider data is not issuer Evidence; required primary sources stay required.",
            "Retrieval today does not establish historical availability or absence of corrections.",
            "The income field parcomp_n_profit is retained unmapped; no assumed parent/ex-item equivalence.",
            "Forecast/express units and profit attribution remain unverified; no arithmetic or implied actuals."]}
    stopped = False
    for family in ROUTES:
        if stopped:
            result["families"][family] = {"family": family, "status": "NOT_ATTEMPTED_AFTER_PROVIDER_STOP"}
            continue
        captured = capture_family(family=family, ticker=ticker, output=output / family, fetch=fetch, clock=clock)
        result["families"][family] = period_context(captured, year=year, report_type=report_type, report_form=report_form)
        stopped = captured["status"] in {"AUTHENTICATION_UNAVAILABLE", "AUTHENTICATION_FAILED",
            "ENTITLEMENT_DENIED", "RATE_LIMITED", "CREDENTIAL_REFLECTION_REJECTED", "REDIRECT_REJECTED"}
    result["status"] = "FINANCIAL_CONTEXT_PREPARED_NOT_ADMITTED" if all(
        result["families"][f]["status"] == "SECONDARY_CONTEXT_READY" for f in METRICS) else "PARTIAL_FINANCIAL_CONTEXT"
    result["finished_at"] = clock()
    (output / "financial-context.json").write_bytes(raw_json(result))
    return result
