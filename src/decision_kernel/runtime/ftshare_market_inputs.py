"""Bounded FTShare market/board/industry inputs; existing gates keep authority.

Provider-specific routes, not a provider registry or a second Radar executor.
Raw responses are retained before interpretation. No retries or default changes.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import os

from . import ftshare_discovery as d
from .ftshare_financial import decode, raw_json
from .external_radar_observations import AUTHORITY, _seal

VERSION = "ftshare-market-board-industry-v1"
BASE = "https://market.ft.tech/gateway/api/v1/market/data/"
ROUTES = {"stock_bars": "stock-candlesticks", "stock_flow": "eastmoney-stock-flow",
          "sector_members": "ths-industry-constituents", "sector_bars": "ths-board-kline",
          "concept_members": "eastmoney-board-constituents", "concept_bars": "eastmoney-board-daily-ohlc",
          "futures_bars": "futures/kline", "warehouse": "futures/fut-wsr"}
MAX_BYTES, PAGE_SIZE, MAX_PAGES = 2 * 1024 * 1024, 200, 4
TZ = timezone(timedelta(hours=8))
require = d._require


def day(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "DATE_INVALID")
    return date.fromisoformat(value)


def security(value):
    require(isinstance(value, str) and re.fullmatch(r"(?:6\d{5}\.SH|[03]\d{5}\.SZ)", value), "SECURITY_INVALID")
    return value


def ms(value, *, end=False):
    at = datetime.combine(value + timedelta(days=1) if end else value, time(), TZ)
    return int(at.timestamp()) * 1000 - (1 if end else 0)


def parameters(kind, identity, start, end, page=1):
    require(kind in ROUTES and type(page) is int and 1 <= page <= MAX_PAGES, "REQUEST_INVALID")
    a, b = day(start), day(end)
    require(a <= b and (b - a).days <= 92, "WINDOW_TOO_WIDE")
    paging = {"page": page, "page_size": PAGE_SIZE}
    if kind.startswith("stock_"):
        security(identity)
        if kind == "stock_bars":
            require(page == 1, "REQUEST_INVALID")
            return {"symbol": identity, "interval_unit": "Day", "adjust_kind": "None",
                    "since_ts_millis": ms(a), "until_ts_millis": ms(b, end=True), "limit": 100}
        return {"symbol": identity, "trade_date": b.isoformat(), **paging}
    if kind.startswith("sector_"):
        require(isinstance(identity, str) and re.fullmatch(r"88\d{4}", identity), "SECTOR_INVALID")
        return ({"industry_code": identity, **paging} if kind == "sector_members"
                else {"board_code": identity, **paging})
    if kind.startswith("concept_"):
        require(isinstance(identity, str) and re.fullmatch(r"BK\d{4}", identity), "CONCEPT_INVALID")
        if kind == "concept_members":
            require(page == 1, "REQUEST_INVALID")
            return {"board_code": identity}
        return {"board_code": identity, "start_date": start, "end_date": end, **paging}
    if kind == "warehouse":
        require(identity in {"LC", "CU", "RB"}, "VARIETY_INVALID")
        return {"symbol": identity, "trade_date": int(b.strftime("%Y%m%d")), **paging}
    require(isinstance(identity, str) and re.fullmatch(r"(?:LC\d{4}\.GFE|(?:CU|RB)\d{4}\.SHF)", identity), "CONTRACT_INVALID")
    require(page == 1, "REQUEST_INVALID")
    return {"symbol": identity, "interval": "daily", "start": ms(a), "end": ms(b, end=True), "limit": 100}


def request(kind, params):
    """Only reviewed fixed official paths; caller-generated parameters, no URL input."""
    require(kind in ROUTES, "ROUTE_INVALID")
    key = os.environ.get("FTSHARE_API_KEY")
    require(isinstance(key, str) and key and key.isascii()
            and all(32 < ord(c) < 127 for c in key), "AUTHENTICATION_UNAVAILABLE")
    req = Request(BASE + ROUTES[kind] + "?" + urlencode(params), headers={
        "FTSHARE_API_KEY": key, "X-Client-Name": "ft-claw", "Accept": "application/json",
        "Accept-Encoding": "identity", "User-Agent": "decision-kernel/" + VERSION})
    try:
        response = build_opener(d._NoRedirect()).open(req, timeout=20)
    except HTTPError as exc:
        response = exc
    with response:
        require(response.geturl() == req.full_url, "REDIRECT_REJECTED")
        require(response.headers.get("Content-Encoding", "identity") == "identity", "ENCODING_REJECTED")
        raw = response.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
        require(key.encode() not in raw, "CREDENTIAL_REFLECTION_REJECTED")
        return response.status, raw


def body(value):
    if isinstance(value, dict) and "code" in value:
        require(type(value["code"]) is int, "ENVELOPE_INVALID")
        require(value["code"] in {0, 200}, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED",
                429: "RATE_LIMITED", 404: "PROVIDER_NOT_FOUND"}.get(value["code"], "PROVIDER_REJECTED"))
        return value.get("data")
    return value


def page_rows(value, kind, number):
    value = body(value)
    if kind == "concept_members":
        require(number == 1 and isinstance(value, dict) and isinstance(value.get("constituents"), list), "SHAPE_INVALID")
        return value["constituents"], 1, value
    if isinstance(value, list):
        require(number == 1 and kind in {"stock_bars", "stock_flow", "futures_bars"}, "PAGINATION_MISSING")
        require(len(value) < 100 if kind.endswith("bars") else len(value) <= 1, "POSSIBLY_TRUNCATED")
        return value, 1, {}
    require(isinstance(value, dict), "SHAPE_INVALID")
    if kind == "futures_bars":
        rows = value.get("items")
        require(isinstance(rows, list) and type(value.get("total")) is int
                and len(rows) == value["total"] and len(rows) < 100, "POSSIBLY_TRUNCATED")
        return rows, 1, value
    rows = value.get("records", value.get("items"))
    total, pages = value.get("total_items", value.get("total")), value.get("total_pages", value.get("pages"))
    require(isinstance(rows, list) and type(total) is int and type(pages) is int
            and total >= 0 and pages >= 0, "PAGINATION_MISSING")
    require(pages == (total + PAGE_SIZE - 1) // PAGE_SIZE if total else pages in {0, 1}, "PAGINATION_MISMATCH")
    require(pages <= MAX_PAGES, "PAGINATION_LIMIT")
    require(len(rows) == min(PAGE_SIZE, max(0, total - (number-1)*PAGE_SIZE)), "PAGINATION_MISMATCH")
    if "pageNum" in value:
        require(value["pageNum"] == number and value.get("pageSize") == PAGE_SIZE, "PAGINATION_MISMATCH")
    return rows, max(1, pages), value


def capture(*, kind, identity, start, end, output: Path, fetch=request, clock=d.now):
    parameters(kind, identity, start, end)
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    started = clock()
    require(day(end) < d._clock(started).astimezone(TZ).date(), "COMPLETED_SESSION_REQUIRED")
    out = {"version": VERSION, "provider": "FTSHARE", "kind": kind, "identity": identity,
           "start": start, "end": end, "started_at": started, "endpoint": BASE + ROUTES[kind],
           "status": "INCOMPLETE", "requests": [], "rows": [], "automatic_retry": False}
    expected, seen, rows = None, set(), []
    last = d._clock(started)
    try:
        for number in range(1, MAX_PAGES + 1):
            params = parameters(kind, identity, start, end, number)
            event = {"parameters": params, "requested_at": clock(), "http_status": None, "provider_status": None}
            out["requests"].append(event)
            require(d._clock(event["requested_at"]) >= last, "CLOCK_ORDER")
            status, raw = fetch(kind, params)
            received = clock(); last = d._clock(received)
            require(last >= d._clock(event["requested_at"]), "CLOCK_ORDER")
            require(type(status) is int and isinstance(raw, bytes) and len(raw) <= MAX_BYTES, "RESPONSE_INVALID")
            name = f"page-{number}.json"; (output / name).write_bytes(raw)
            event.update(http_status=status, received_at=received, path=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
            require(status == 200, {401: "AUTHENTICATION_FAILED", 403: "ENTITLEMENT_DENIED", 429: "RATE_LIMITED",
                    404: "HTTP_NOT_FOUND"}.get(status, "HTTP_REJECTED"))
            value = decode(raw)
            if isinstance(value, dict): event["provider_status"] = value.get("code")
            page, pages, meta = page_rows(value, kind, number)
            counts = (pages, meta.get("total_items", meta.get("total")))
            require(expected is None or counts == expected, "PAGINATION_CHANGED")
            expected = counts
            for index, row in enumerate(page):
                require(isinstance(row, dict), "ROW_INVALID")
                key = sha256(raw_json(row)).hexdigest(); require(key not in seen, "DUPLICATE_ROW"); seen.add(key)
                rows.append({"fields": row, "raw_page": name, "raw_sha256": event["sha256"],
                             "row_index": index, "received_at": received})
            if number >= pages:
                out.update(status="COMPLETE" if rows else "EMPTY", rows=rows)
                if kind == "concept_members":
                    require(meta.get("board_code") == identity, "IDENTITY_MISMATCH")
                    out["board_name"] = meta.get("board_name")
                break
    except d.DiscoveryError as exc:
        out.update(status=str(exc), rows=[])
    except (URLError, OSError, TimeoutError):
        out.update(status="TRANSPORT_FAILURE", rows=[])
    except (ValueError, TypeError, KeyError, OverflowError):
        out.update(status="PARSE_FAILURE", rows=[])
    finally:
        out["finished_at"] = clock()
        require(d._clock(out["finished_at"]) >= last, "CLOCK_ORDER")
        (output / "capture.json").write_bytes(raw_json(out))
    return out


def number(value, *, nonnegative=False):
    require(type(value) in {str, int, Decimal} and len(str(value)) <= 100, "NUMBER_INVALID")
    result = Decimal(str(value))
    require(result.is_finite() and abs(result.adjusted()) <= 24 and (not nonnegative or result >= 0), "NUMBER_INVALID")
    return result


def bar(row, date_key):
    values = {k: number(row.get(k), nonnegative=True) for k in ("open", "high", "low", "close")}
    require(values["low"] > 0 and values["low"] <= min(values["open"], values["close"])
            <= max(values["open"], values["close"]) <= values["high"], "OHLC_INVALID")
    return {"date": date_key, **{k: str(v) for k, v in values.items()}}


def normalize(saved):
    """Pure interpretation of retained input. Never promotes provider identity/authority."""
    kind, ident = saved["kind"], saved["identity"]
    out = {"version": VERSION, "kind": {"stock_bars": "MARKET_EXPRESSION_CONTEXT", "stock_flow": "MARKET_EXPRESSION_CONTEXT",
           "sector_members": "SECTOR_CURRENT_MEMBERSHIP", "sector_bars": "SECTOR_MARKET_CONTEXT",
           "concept_members": "CONCEPT_CURRENT_MEMBER", "concept_bars": "CONCEPT_MARKET_CONTEXT",
           "futures_bars": "INDUSTRY_VARIABLE_OBSERVATION", "warehouse": "INDUSTRY_VARIABLE_OBSERVATION"}[kind],
           "provider": "FTSHARE", "input_kind": kind, "identity": ident, "status": "SOURCE_UNAVAILABLE",
           "capture_status": saved["status"], "observations": [], "qualification": "CONTEXT_ONLY",
           "historical_pit_availability": "NOT_ESTABLISHED", "default_provider_changed": False, **AUTHORITY}
    if saved["status"] not in {"COMPLETE", "EMPTY"}: return _seal(out)
    try:
        rows, excluded, dates = [], 0, set()
        for retained in saved["rows"]:
            r = retained["fields"]
            p = {"received_at": retained["received_at"], "raw_page": retained["raw_page"],
                 "raw_sha256": retained["raw_sha256"], "row_index": retained["row_index"]}
            if kind == "stock_bars":
                require(r.get("symbol", ident) in {ident, ident.replace(".SH", ".XSHG").replace(".SZ", ".XSHE")}, "IDENTITY_MISMATCH")
                ts = r.get("ts_millis"); require(type(ts) is int and ts > 0, "BAR_TIME_INVALID")
                at = datetime.fromtimestamp(ts / 1000, TZ); ds = at.date().isoformat()
                require(saved["start"] <= ds <= saved["end"] and at <= d._clock(retained["received_at"]), "BAR_TIME_OUTSIDE_REQUEST")
                require(ds not in dates, "DUPLICATE_SESSION"); dates.add(ds)
                item = bar(r, ds)
                vol = number(r.get("volume"), nonnegative=True)
                require(vol == vol.to_integral_value(), "VOLUME_NOT_SHARES")
                item.update(ticker=ident, volume=str(vol), turnover=str(number(r.get("turnover"), nonnegative=True)),
                            price_unit="CNY", volume_unit="SHARES", turnover_unit="CNY", adjustment="none", **p)
            elif kind in {"sector_members", "concept_members"}:
                if kind == "sector_members": require(r.get("industry_code") == ident, "IDENTITY_MISMATCH")
                code = r.get("stock_code")
                require(isinstance(code, str) and re.fullmatch(r"[036]\d{5}", code), "MEMBER_IDENTITY_UNSUPPORTED")
                ticker = code + (".SH" if code[0] == "6" else ".SZ")
                name = r.get("stock_name"); require(isinstance(name, str) and name.strip(), "MEMBER_NAME_INVALID")
                require(ticker not in dates, "DUPLICATE_MEMBER"); dates.add(ticker)
                item = {"ticker": ticker, "name": name, "board_code": ident,
                        "board_name": r.get("industry_name", saved.get("board_name")),
                        "membership_as_of": retained["received_at"], "historical_membership": False, **p}
            elif kind in {"sector_bars", "concept_bars"}:
                require(r.get("board_code") == ident, "IDENTITY_MISMATCH")
                ds = r.get("date", r.get("trade_date")); day(ds)
                if not saved["start"] <= ds <= saved["end"]: excluded += 1; continue
                require(ds not in dates, "DUPLICATE_SESSION"); dates.add(ds)
                item = {**bar(r, ds), "board_code": ident, "price_unit": "INDEX_POINTS", **p}
            elif kind == "stock_flow":
                require(r.get("symbol") == ident, "IDENTITY_MISMATCH")
                ds = r.get("trade_date", r.get("date")); day(ds)
                require(ds == saved["end"], "FLOW_DATE_DIFFERS")
                item = {"ticker": ident, "date": ds, "provider_fields": r,
                        "units": "SOURCE_FIELD_SPECIFIC_NOT_ASSUMED", "flow_is_earnings": False, **p}
            elif kind == "futures_bars":
                require(r.get("symbol") == ident, "IDENTITY_MISMATCH")
                td = str(r.get("trade_date")); require(re.fullmatch(r"\d{8}", td), "TRADE_DATE_INVALID")
                ds = date(int(td[:4]), int(td[4:6]), int(td[6:])).isoformat()
                require(saved["start"] <= ds <= saved["end"], "FUTURES_DATE_DIFFERS")
                require(ds not in dates, "DUPLICATE_SESSION"); dates.add(ds)
                require(r.get("dominant_contract") is None and r.get("forward_factor") is None
                        and r.get("backward_factor") is None, "CONTRACT_SERIES_KIND_DIFFERS")
                item = {**bar(r, ds), "contract": ident, "variety": re.match(r"[A-Z]+", ident)[0],
                        "series_kind": "FIXED_EXPIRY_NOT_CONTINUOUS", "roll": "NOT_APPLICABLE",
                        "price_unit": "PROVIDER_QUOTE_UNIT_NOT_VERIFIED", "volume_unit": "CONTRACTS_NOT_VERIFIED",
                        "provider_fields": r, "industry_inflection_established": False, **p}
            else:
                # Warehouse schemas and units vary by exchange. Never invent ton/lot conversion.
                item = {"variety": ident, "requested_date": saved["end"], "provider_fields": r,
                        "date_identity": "UNVERIFIED", "warehouse_unit": "UNKNOWN",
                        "qualification": "RAW_CONTEXT_ONLY", "industry_inflection_established": False, **p}
            rows.append(item)
        out.update(observations=rows, status="OBSERVATIONS_NORMALIZED" if rows else "EMPTY_REQUESTED_WINDOW",
                   excluded_outside_window=excluded)
        if kind == "sector_members" and rows:
            from .sector_breadth import SectorConstituentIdentity, normalize_sector_membership
            require(len({x["board_name"] for x in rows}) == 1, "SECTOR_NAME_CONFLICT")
            snapshot = normalize_sector_membership(sector_thscode=ident + ".TI", sector_name=rows[0]["board_name"],
                captured_at=d._clock(saved["finished_at"]),
                members=[SectorConstituentIdentity(x["ticker"], x["ticker"][:6], x["name"]) for x in rows])
            out["existing_sector_membership"] = asdict(snapshot)
    except (ValueError, TypeError, KeyError, ArithmeticError, OverflowError) as exc:
        out.update(status=str(exc) if isinstance(exc, d.DiscoveryError) else "NORMALIZATION_FAILED", observations=[])
    return _seal(out)


def compare_stock(projection, reference):
    """Compare against retained raw HiThink bars using ORIGINAL field tolerances.

    Caller verifies the saved source receipt; this is not full Stock admission.
    """
    from .hithink_stock_reading import reconcile_volume, reconcile_turnover, _number
    require(projection["projection"]["input_kind"] == "stock_bars", "COMPARISON_INPUT_KIND")
    p = projection["projection"]
    require(reference["ticker"] == p["identity"] and reference["adjustment"] == "none", "COMPARISON_IDENTITY")
    old = {r["date"]: r for r in reference["bars"]}
    require(len(old) == len(reference["bars"]), "REFERENCE_DUPLICATE_SESSION")
    result = []
    for row in p["observations"]:
        prior = old.get(row["date"])
        if prior is None: result.append({"date": row["date"], "status": "REFERENCE_SESSION_MISSING"}); continue
        checks = {}
        for k in ("open", "high", "low", "close"):
            checks[k] = "EXACT" if _number(prior, k, p["identity"], positive=True) == Decimal(row[k]) else "DIFFERENT"
        for key, fn in (("volume", reconcile_volume), ("turnover", reconcile_turnover)):
            try: checks[key] = fn(prior[key], row[key], code=p["identity"])["status"]
            except ValueError: checks[key] = "DIFFERENT"
        result.append({"date": row["date"], "fields": checks,
                       "status": "MATCH" if all(v in {"EXACT", "WITHIN_EXPLICIT_TOLERANCE"} for v in checks.values()) else "DIFFERENT"})
    return {"ticker": p["identity"], "status": "COMPARED" if result else "NOT_COMPARED", "rows": result,
            "reference_source": reference.get("source"), "reference_sha256": reference.get("raw_sha256"),
            "qualification": "COMPARISON_ONLY_NOT_STOCK_GATE", "default_provider_changed": False}
