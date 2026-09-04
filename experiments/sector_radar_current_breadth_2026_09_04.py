from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    require_hithink_data,
)
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history,
    normalize_hithink_index_snapshot,
    qualify_hithink_index_snapshot,
)
from decision_kernel.runtime.hithink_http import (
    HITHINK_API_KEY_ENV,
    HITHINK_CALENDAR_PATH,
    _request_hithink_json,
)
from decision_kernel.runtime.hithink_index_http import (
    HITHINK_INDEX_CATALOG_PATH,
    HITHINK_INDEX_HISTORY_PATH,
    HITHINK_INDEX_SNAPSHOT_PATH,
)

TARGET_SESSION = date(2026, 9, 4)
BENCHMARK = ("000300.SH", "沪深300")
CONSTITUENTS_PATH = "/api/a-share-index/constituents/ths-stock-list"
STOCK_SNAPSHOT_PATH = "/api/a-share/prices/snapshot"
STOCK_PAGE_LIMIT = 500
MAX_TRANSPORT_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0
REQUEST_PACE_SECONDS = float(
    os.environ.get("SECTOR_RADAR_BREADTH_REQUEST_PACE_SECONDS", "2")
)

RESULT = Path("sector-radar-current-breadth.json")
SUMMARY = Path("sector-radar-current-breadth-summary.md")
PROGRESS = Path("sector-radar-current-breadth-progress.jsonl")
ERROR = Path("sector-radar-current-breadth-error.json")

FINALISTS: tuple[tuple[str, str, str], ...] = (
    ("881101.TI", "种植业与林业", "PRESSURE_BROAD_AGRICULTURE"),
    ("881102.TI", "养殖业", "PRESSURE_BROAD_LIVESTOCK"),
    ("881166.TI", "军工装备", "PRESSURE_BROAD_SHIPBUILDING_CONTEXT"),
    ("884183.TI", "航海装备", "PRESSURE_GRANULAR_SHIPBUILDING"),
    ("884005.TI", "海洋捕捞", "PRESSURE_GRANULAR_FISHERY"),
    ("884006.TI", "水产养殖", "PRESSURE_GRANULAR_AQUACULTURE"),
    ("884275.TI", "生猪养殖", "PRESSURE_GRANULAR_PORK"),
    ("884276.TI", "肉鸡养殖", "PRESSURE_GRANULAR_CHICKEN"),
    ("884001.TI", "种子生产", "CURRENT_GRANULAR_20D_LEADER"),
    ("884277.TI", "其他养殖", "CURRENT_GRANULAR_20D_LEADER"),
    ("881158.TI", "零售", "CURRENT_BROAD_STATE_ENTRY_CONTROL"),
    ("881174.TI", "厨卫电器", "CURRENT_BROAD_STATE_ENTRY_AND_SPIKE_CONTROL"),
    ("881132.TI", "黑色家电", "CURRENT_BROAD_STATE_ENTRY_CONTROL"),
    ("881169.TI", "贵金属", "FADING_LONG_HORIZON_CONTROL"),
    ("884182.TI", "地面兵装", "GRANULAR_SIBLING_OVERLAP_CONTROL"),
)

_A_SHARE = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")
_INDEX = re.compile(r"^\d{6}\.TI$")


def jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def digest(value: Any) -> str:
    raw = json.dumps(
        jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def locator(path: str, params: Mapping[str, str]) -> str:
    query = urlencode(sorted(params.items()))
    return f"https://fuyao.aicubes.cn{path}" + (f"?{query}" if query else "")


def progress(payload: Mapping[str, Any]) -> None:
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(jsonable(payload), ensure_ascii=False, sort_keys=True) + "\n"
        )


def request(
    api_key: str,
    path: str,
    params: Mapping[str, str],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        started = datetime.now(timezone.utc)
        try:
            envelope = _request_hithink_json(
                api_key=api_key,
                path=path,
                params=params,
                timeout_seconds=30.0,
            )
        except ConnectionError as exc:
            completed = datetime.now(timezone.utc)
            attempt = {
                "attempt_number": attempt_number,
                "status": "TRANSIENT_CONNECTION_FAILURE",
                "request_started_at": started,
                "response_completed_at": completed,
                "duration_seconds": (completed - started).total_seconds(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            attempts.append(attempt)
            progress(
                {
                    "stage": "transport_retry",
                    "path": path,
                    "params": dict(sorted(params.items())),
                    **attempt,
                }
            )
            if attempt_number == MAX_TRANSPORT_ATTEMPTS:
                raise
            time.sleep(RETRY_BASE_SECONDS * (2 ** (attempt_number - 1)))
            continue

        completed = datetime.now(timezone.utc)
        attempts.append(
            {
                "attempt_number": attempt_number,
                "status": "SUCCESS",
                "request_started_at": started,
                "response_completed_at": completed,
                "duration_seconds": (completed - started).total_seconds(),
            }
        )
        return envelope, {
            "path": path,
            "params": dict(sorted(params.items())),
            "source_locator": locator(path, params),
            "request_started_at": started,
            "response_completed_at": completed,
            "duration_seconds": (completed - started).total_seconds(),
            "request_id": envelope.get("request_id"),
            "business_code": envelope.get("code"),
            "envelope_sha256": digest(envelope),
            "transport_attempt_count": attempt_number,
            "transport_retry_count": attempt_number - 1,
            "transport_attempts": attempts,
            "retry_scope": "TRANSIENT_CONNECTION_FAILURE_ONLY",
        }
    raise RuntimeError("unreachable request loop")


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def normalize_membership(
    envelope: Mapping[str, Any],
    *,
    sector_thscode: str,
) -> dict[str, Any]:
    if not _INDEX.fullmatch(sector_thscode):
        raise ValueError(f"invalid sector identity: {sector_thscode}")
    data = require_hithink_data(envelope, endpoint=CONSTITUENTS_PATH)
    timestamp_raw = data.get("timestamp")
    if isinstance(timestamp_raw, bool):
        raise ValueError(f"membership timestamp is invalid for {sector_thscode}")
    try:
        timestamp_ms = int(timestamp_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"membership timestamp is invalid for {sector_thscode}"
        ) from exc
    if timestamp_ms <= 0:
        raise ValueError(f"membership timestamp is invalid for {sector_thscode}")

    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise ValueError(f"membership is empty for {sector_thscode}")

    by_code: dict[str, dict[str, str]] = {}
    for raw in items:
        if not isinstance(raw, Mapping):
            raise ValueError(f"membership contains malformed row for {sector_thscode}")
        thscode = str(raw.get("thscode", "")).strip().upper()
        ticker = str(raw.get("ticker", "")).strip()
        name = str(raw.get("name", "")).strip()
        if not _A_SHARE.fullmatch(thscode) or ticker != thscode[:6] or not name:
            raise ValueError(f"membership contains invalid identity for {sector_thscode}")
        if thscode in by_code:
            raise ValueError(
                f"membership contains duplicate identity {thscode} for {sector_thscode}"
            )
        by_code[thscode] = {"thscode": thscode, "ticker": ticker, "name": name}

    members = tuple(by_code[key] for key in sorted(by_code))
    return {
        "sector_thscode": sector_thscode,
        "provider_timestamp_ms": timestamp_ms,
        "provider_timestamp": datetime.fromtimestamp(
            timestamp_ms / 1000, tz=SHANGHAI_TZ
        ),
        "members": members,
        "member_count": len(members),
        "constituent_set_hash": digest(members),
        "membership_semantics": "CURRENT_CONSTITUENTS_AT_CAPTURE_ONLY",
    }


def normalize_stock_snapshot_item(raw: Mapping[str, Any]) -> dict[str, Any]:
    thscode = str(raw.get("thscode", "")).strip().upper()
    ticker = str(raw.get("ticker", "")).strip()
    if not _A_SHARE.fullmatch(thscode) or ticker != thscode[:6]:
        raise ValueError("stock snapshot contains invalid identity")

    last_price = decimal_or_none(raw.get("last_price"))
    prev_price = decimal_or_none(raw.get("prev_price"))
    volume = decimal_or_none(raw.get("volume"))
    turnover = decimal_or_none(raw.get("turnover"))
    provider_change_pct = decimal_or_none(raw.get("price_change_ratio_pct"))

    valid_price = (
        last_price is not None
        and prev_price is not None
        and last_price > 0
        and prev_price > 0
        and volume is not None
        and volume >= 0
        and turnover is not None
        and turnover >= 0
    )
    daily_return = last_price / prev_price - Decimal(1) if valid_price else None

    return {
        "thscode": thscode,
        "ticker": ticker,
        "last_price": last_price,
        "prev_price": prev_price,
        "volume": volume,
        "turnover": turnover,
        "provider_change_pct": provider_change_pct,
        "daily_return": daily_return,
        "price_status": "PRICED" if valid_price else "UNPRICED_OR_INVALID",
    }


def fetch_all_market_snapshot(
    api_key: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    request_meta: list[dict[str, Any]] = []
    provider_timestamps: list[int] = []
    reported_total: int | None = None
    offset = 0

    while True:
        if request_meta and REQUEST_PACE_SECONDS:
            time.sleep(REQUEST_PACE_SECONDS)
        params = {"limit": str(STOCK_PAGE_LIMIT), "offset": str(offset)}
        envelope, meta = request(api_key, STOCK_SNAPSHOT_PATH, params)
        data = require_hithink_data(envelope, endpoint=STOCK_SNAPSHOT_PATH)

        timestamp_raw = data.get("timestamp")
        if isinstance(timestamp_raw, bool):
            raise ValueError("all-market stock snapshot timestamp is invalid")
        try:
            timestamp_ms = int(timestamp_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("all-market stock snapshot timestamp is invalid") from exc
        if timestamp_ms <= 0:
            raise ValueError("all-market stock snapshot timestamp is invalid")
        provider_timestamps.append(timestamp_ms)

        total_raw = data.get("total")
        if isinstance(total_raw, bool):
            raise ValueError("all-market stock snapshot total is invalid")
        try:
            current_total = int(total_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("all-market stock snapshot total is invalid") from exc
        if current_total <= 0:
            raise ValueError("all-market stock snapshot total is invalid")
        if reported_total is None:
            reported_total = current_total
        elif reported_total != current_total:
            raise ValueError("all-market stock snapshot total changed during pagination")

        items = data.get("item")
        if not isinstance(items, list):
            raise ValueError("all-market stock snapshot page has no item list")
        if not items and offset < reported_total:
            raise ValueError("all-market stock snapshot pagination ended unexpectedly")

        priced = 0
        unpriced = 0
        for raw in items:
            if not isinstance(raw, Mapping):
                raise ValueError("all-market stock snapshot contains malformed row")
            item = normalize_stock_snapshot_item(raw)
            code = item["thscode"]
            if code in by_code:
                raise ValueError(f"all-market stock snapshot duplicated {code}")
            by_code[code] = item
            if item["price_status"] == "PRICED":
                priced += 1
            else:
                unpriced += 1

        meta.update(
            {
                "offset": offset,
                "returned_rows": len(items),
                "priced_rows": priced,
                "unpriced_rows": unpriced,
                "provider_timestamp_ms": timestamp_ms,
            }
        )
        request_meta.append(meta)
        progress({"stage": "stock_snapshot_page", **meta})

        if len(items) < STOCK_PAGE_LIMIT:
            termination = "SHORT_PAGE"
            break
        offset += STOCK_PAGE_LIMIT
        if offset >= reported_total:
            termination = "REPORTED_TOTAL_REACHED"
            break

    provider_dates = {
        datetime.fromtimestamp(value / 1000, tz=SHANGHAI_TZ).date()
        for value in provider_timestamps
    }
    if provider_dates != {TARGET_SESSION}:
        raise ValueError(
            "all-market stock snapshot pages do not all map to the target session"
        )

    return by_code, {
        "page_limit": STOCK_PAGE_LIMIT,
        "page_count": len(request_meta),
        "reported_total": reported_total,
        "returned_unique_rows": len(by_code),
        "priced_rows": sum(
            1 for item in by_code.values() if item["price_status"] == "PRICED"
        ),
        "unpriced_rows": sum(
            1
            for item in by_code.values()
            if item["price_status"] != "PRICED"
        ),
        "provider_timestamp_min_ms": min(provider_timestamps),
        "provider_timestamp_max_ms": max(provider_timestamps),
        "provider_session": TARGET_SESSION,
        "termination": termination,
        "requests": request_meta,
        "snapshot_semantics": "CURRENT_ALL_MARKET_PAGE_SNAPSHOT",
    }


def mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("cannot calculate mean of empty sequence")
    return sum(values, Decimal(0)) / Decimal(len(values))


def breadth_observation(
    *,
    sector_thscode: str,
    sector_name: str,
    rationale: str,
    membership: Mapping[str, Any],
    stock_snapshot_by_code: Mapping[str, Mapping[str, Any]],
    index_daily_return: Decimal,
) -> dict[str, Any]:
    members = tuple(membership["members"])
    priced: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for member in members:
        snapshot = stock_snapshot_by_code.get(member["thscode"])
        if snapshot is None or snapshot["price_status"] != "PRICED":
            missing.append(member)
            continue
        priced.append({**member, **snapshot})

    returns = [item["daily_return"] for item in priced]
    if not returns:
        raise ValueError(f"no priced constituents for {sector_thscode}")
    turnovers = [item["turnover"] for item in priced]
    total_turnover = sum(turnovers, Decimal(0))

    advancers = sum(1 for value in returns if value > 0)
    decliners = sum(1 for value in returns if value < 0)
    unchanged = len(returns) - advancers - decliners
    positive_returns = sorted((value for value in returns if value > 0), reverse=True)
    positive_mass = sum(positive_returns, Decimal(0))
    top3_positive_mass = sum(positive_returns[:3], Decimal(0))
    top3_turnover = sum(sorted(turnovers, reverse=True)[:3], Decimal(0))

    leaders = sorted(
        priced,
        key=lambda item: (item["daily_return"], item["thscode"]),
        reverse=True,
    )[:5]
    laggards = sorted(
        priced,
        key=lambda item: (item["daily_return"], item["thscode"]),
    )[:5]

    member_count = int(membership["member_count"])
    priced_count = len(priced)
    equal_weight_mean = mean(returns)
    return {
        "sector_thscode": sector_thscode,
        "sector_name": sector_name,
        "selection_rationale": rationale,
        "index_daily_return": index_daily_return,
        "member_count": member_count,
        "priced_member_count": priced_count,
        "missing_or_unpriced_member_count": len(missing),
        "coverage_ratio": Decimal(priced_count) / Decimal(member_count),
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "advancer_share": Decimal(advancers) / Decimal(priced_count),
        "decliner_share": Decimal(decliners) / Decimal(priced_count),
        "equal_weight_mean_daily_return": equal_weight_mean,
        "equal_weight_median_daily_return": statistics.median(returns),
        "index_minus_equal_weight_mean": index_daily_return - equal_weight_mean,
        "total_constituent_turnover": total_turnover,
        "top3_turnover_share": (
            None if total_turnover == 0 else top3_turnover / total_turnover
        ),
        "top3_positive_return_mass_share": (
            None if positive_mass == 0 else top3_positive_mass / positive_mass
        ),
        "leaders": tuple(
            {
                "thscode": item["thscode"],
                "name": item["name"],
                "daily_return": item["daily_return"],
                "turnover": item["turnover"],
            }
            for item in leaders
        ),
        "laggards": tuple(
            {
                "thscode": item["thscode"],
                "name": item["name"],
                "daily_return": item["daily_return"],
                "turnover": item["turnover"],
            }
            for item in laggards
        ),
        "missing_or_unpriced_members": tuple(missing),
        "constituent_set_hash": membership["constituent_set_hash"],
        "membership_provider_timestamp": membership["provider_timestamp"],
        "breadth_semantics": "CURRENT_CONSTITUENT_EQUAL_WEIGHT_PROXY_ONLY",
        "historical_breadth_authority": "NONE",
        "index_contribution_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }


def pairwise_overlaps(
    memberships: Mapping[str, Mapping[str, Any]],
    names: Mapping[str, str],
) -> tuple[dict[str, Any], ...]:
    codes = sorted(memberships)
    result: list[dict[str, Any]] = []
    sets = {
        code: {member["thscode"] for member in memberships[code]["members"]}
        for code in codes
    }
    for left_index, left in enumerate(codes):
        for right in codes[left_index + 1 :]:
            intersection = sets[left] & sets[right]
            union = sets[left] | sets[right]
            smaller = min(len(sets[left]), len(sets[right]))
            result.append(
                {
                    "left_thscode": left,
                    "left_name": names[left],
                    "right_thscode": right,
                    "right_name": names[right],
                    "intersection_count": len(intersection),
                    "jaccard": (
                        Decimal(len(intersection)) / Decimal(len(union))
                        if union
                        else Decimal(0)
                    ),
                    "smaller_set_containment": (
                        Decimal(len(intersection)) / Decimal(smaller)
                        if smaller
                        else Decimal(0)
                    ),
                    "intersection_sample": tuple(sorted(intersection)[:10]),
                    "overlap_semantics": "CURRENT_CONSTITUENT_SET_OVERLAP_ONLY",
                }
            )
    result.sort(
        key=lambda item: (
            item["jaccard"],
            item["smaller_set_containment"],
            item["intersection_count"],
            item["left_thscode"],
            item["right_thscode"],
        ),
        reverse=True,
    )
    return tuple(result)


def pct(value: Any) -> str:
    return "NA" if value is None else f"{Decimal(str(value)):+.1%}"


def summary_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# Sector Discovery Radar — current constituent breadth proof",
        "",
        f"- Captured: `{result['captured_at']}`",
        f"- Qualified market session: `{result['market_session']}`",
        f"- Finalists / controls: `{len(result['sectors'])}`",
        f"- Full-market stock snapshot rows: `{result['stock_snapshot']['returned_unique_rows']}` / provider total `{result['stock_snapshot']['reported_total']}`",
        "- Current constituent breadth only; no historical membership backfill.",
        "- Human attention authority: `NONE`",
        "- Investment authority: `NONE`",
        "",
        "## Breadth observations",
        "",
        "| Sector | Index | Coverage | Advancers | EW mean | EW median | Top-3 turnover | Top-3 positive mass |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["sectors"]:
        lines.append(
            f"| {row['sector_name']} `{row['sector_thscode']}` | "
            f"{pct(row['index_daily_return'])} | "
            f"{pct(row['coverage_ratio'])} | "
            f"{pct(row['advancer_share'])} | "
            f"{pct(row['equal_weight_mean_daily_return'])} | "
            f"{pct(row['equal_weight_median_daily_return'])} | "
            f"{pct(row['top3_turnover_share'])} | "
            f"{pct(row['top3_positive_return_mass_share'])} |"
        )

    lines.extend(
        [
            "",
            "## Highest current membership overlap",
            "",
            "| Left | Right | Intersection | Jaccard | Smaller-set containment |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in result["pairwise_overlap"][:15]:
        lines.append(
            f"| {row['left_name']} `{row['left_thscode']}` | "
            f"{row['right_name']} `{row['right_thscode']}` | "
            f"{row['intersection_count']} | {pct(row['jaccard'])} | "
            f"{pct(row['smaller_set_containment'])} |"
        )

    lines.extend(
        [
            "",
            "Current breadth is an equal-weight cross-sectional proxy. It is not index contribution, historical breadth, Fundamental Evidence, a Research route, recommendation, action, or investment authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    if REQUEST_PACE_SECONDS < 0:
        raise ValueError("request pace must be non-negative")
    api_key = os.environ.get(HITHINK_API_KEY_ENV)
    if not api_key:
        raise ValueError(f"{HITHINK_API_KEY_ENV} is required")
    if len(FINALISTS) != len({item[0] for item in FINALISTS}):
        raise ValueError("finalist identities must be unique")

    captured_at = datetime.now(timezone.utc)
    calendar_envelope, calendar_meta = request(api_key, HITHINK_CALENDAR_PATH, {})
    calendar = normalize_hithink_calendar(calendar_envelope)
    latest = latest_completed_a_share_session(calendar, observed_at=captured_at)
    if latest != TARGET_SESSION:
        raise ValueError(f"expected target session {TARGET_SESSION}, got {latest}")
    progress({"stage": "calendar", "latest_session": latest, **calendar_meta})

    if REQUEST_PACE_SECONDS:
        time.sleep(REQUEST_PACE_SECONDS)
    catalog_envelope, catalog_meta = request(
        api_key,
        HITHINK_INDEX_CATALOG_PATH,
        {"tag": "industry"},
    )
    catalog_data = require_hithink_data(
        catalog_envelope,
        endpoint=HITHINK_INDEX_CATALOG_PATH,
    )
    catalog_items = catalog_data.get("item")
    if not isinstance(catalog_items, list):
        raise ValueError("industry catalog has no item list")
    catalog_names = {
        str(item.get("thscode", "")).strip().upper(): str(item.get("name", "")).strip()
        for item in catalog_items
        if isinstance(item, Mapping)
    }
    for code, expected_name, _ in FINALISTS:
        if catalog_names.get(code) != expected_name:
            raise ValueError(
                f"catalog identity changed for {code}: {catalog_names.get(code)!r}"
            )
    progress({"stage": "catalog", "finalist_count": len(FINALISTS), **catalog_meta})

    index_codes = (BENCHMARK[0],) + tuple(item[0] for item in FINALISTS)
    if REQUEST_PACE_SECONDS:
        time.sleep(REQUEST_PACE_SECONDS)
    index_snapshot_envelope, index_snapshot_meta = request(
        api_key,
        HITHINK_INDEX_SNAPSHOT_PATH,
        {"thscodes": ",".join(index_codes)},
    )
    index_snapshot = normalize_hithink_index_snapshot(
        index_snapshot_envelope,
        requested_thscodes=index_codes,
    )

    end_at = datetime.combine(
        TARGET_SESSION + timedelta(days=1),
        datetime.min.time(),
        tzinfo=SHANGHAI_TZ,
    )
    start_at = end_at - timedelta(days=45)
    if REQUEST_PACE_SECONDS:
        time.sleep(REQUEST_PACE_SECONDS)
    benchmark_history_envelope, benchmark_history_meta = request(
        api_key,
        HITHINK_INDEX_HISTORY_PATH,
        {
            "thscode": BENCHMARK[0],
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
        },
    )
    benchmark_history = normalize_hithink_completed_index_history(
        benchmark_history_envelope,
        thscode=BENCHMARK[0],
        sessions=calendar,
        observed_at=captured_at,
    )
    qualified_index_snapshot = qualify_hithink_index_snapshot(
        index_snapshot,
        benchmark_history=benchmark_history,
    )
    if qualified_index_snapshot.market_session != TARGET_SESSION:
        raise ValueError("qualified index snapshot does not match the target session")
    index_by_code = {
        point.thscode: point for point in qualified_index_snapshot.points
    }
    progress(
        {
            "stage": "qualified_index_snapshot",
            "market_session": qualified_index_snapshot.market_session,
            "qualification_method": qualified_index_snapshot.qualification_method,
            "index_snapshot": index_snapshot_meta,
            "benchmark_history": benchmark_history_meta,
        }
    )

    memberships: dict[str, dict[str, Any]] = {}
    names = {code: name for code, name, _ in FINALISTS}
    for index, (code, name, rationale) in enumerate(FINALISTS):
        if REQUEST_PACE_SECONDS:
            time.sleep(REQUEST_PACE_SECONDS)
        envelope, meta = request(api_key, CONSTITUENTS_PATH, {"thscode": code})
        membership = normalize_membership(envelope, sector_thscode=code)
        memberships[code] = membership
        progress(
            {
                "stage": "membership",
                "index": index + 1,
                "total": len(FINALISTS),
                "sector_thscode": code,
                "sector_name": name,
                "selection_rationale": rationale,
                "member_count": membership["member_count"],
                "constituent_set_hash": membership["constituent_set_hash"],
                **meta,
            }
        )
        print(
            f"MEMBERSHIP {index + 1}/{len(FINALISTS)} {code} {name} "
            f"members={membership['member_count']}",
            flush=True,
        )

    stock_snapshot_by_code, stock_snapshot_meta = fetch_all_market_snapshot(api_key)

    sector_rows = []
    for code, name, rationale in FINALISTS:
        point = index_by_code[code]
        index_daily_return = point.last_price / point.prev_price - Decimal(1)
        sector_rows.append(
            breadth_observation(
                sector_thscode=code,
                sector_name=name,
                rationale=rationale,
                membership=memberships[code],
                stock_snapshot_by_code=stock_snapshot_by_code,
                index_daily_return=index_daily_return,
            )
        )

    result: dict[str, Any] = {
        "schema_version": 1,
        "captured_at": captured_at,
        "market_session": TARGET_SESSION,
        "source": "HiThink Financial-API current industry constituents and A-share snapshots",
        "finalist_policy": "EXACT_BOUNDED_PRESSURE_CASES_CURRENT_ENTRIES_AND_CONTROLS",
        "finalists": tuple(
            {
                "thscode": code,
                "name": name,
                "selection_rationale": rationale,
            }
            for code, name, rationale in FINALISTS
        ),
        "calendar_request": calendar_meta,
        "catalog_request": catalog_meta,
        "index_snapshot_qualification": {
            "benchmark_thscode": BENCHMARK[0],
            "benchmark_name": BENCHMARK[1],
            "qualification_method": qualified_index_snapshot.qualification_method,
            "index_snapshot_request": index_snapshot_meta,
            "benchmark_history_request": benchmark_history_meta,
        },
        "stock_snapshot": stock_snapshot_meta,
        "memberships": tuple(memberships[code] for code, _, _ in FINALISTS),
        "sectors": tuple(sector_rows),
        "pairwise_overlap": pairwise_overlaps(memberships, names),
        "breadth_semantics": "CURRENT_CONSTITUENT_EQUAL_WEIGHT_PROXY_ONLY",
        "historical_membership_backfill": "PROHIBITED",
        "historical_breadth_authority": "NONE",
        "index_contribution_authority": "NONE",
        "research_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
        "explicit_non_authorities": (
            "NO_DETECTOR",
            "NO_RESEARCH_ROUTE",
            "NO_RECOMMENDATION",
            "NO_ACTION",
        ),
    }
    result["result_hash"] = digest(result)
    RESULT.write_text(
        json.dumps(jsonable(result), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    normalized = json.loads(RESULT.read_text(encoding="utf-8"))
    SUMMARY.write_text(summary_markdown(normalized), encoding="utf-8")

    print(f"RESULT={RESULT}")
    print(f"SUMMARY={SUMMARY}")
    print(f"MARKET_SESSION={TARGET_SESSION}")
    print(f"FINALISTS={len(FINALISTS)}")
    print("HISTORICAL_BREADTH_AUTHORITY=NONE")
    print("HUMAN_ATTENTION_AUTHORITY=NONE")
    print("INVESTMENT_AUTHORITY=NONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        ERROR.write_text(
            json.dumps(
                {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "progress_path": str(PROGRESS),
                    "historical_breadth_authority": "NONE",
                    "human_attention_authority": "NONE",
                    "investment_authority": "NONE",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
