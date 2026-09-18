"""Lossless Stock discovery from a saved Sector result; no acquisition or gate.

This is a projection of retained breadth leaders, not a whole-market scanner,
Research result, Stock qualification, persistent queue, or execution authority.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation

from decision_kernel.adapters.hithink import to_hithink_thscode
from decision_kernel.identity import canonical_hash
from .sector_radar_discovery import _candidate_breadths, _stock_candidate_rows, _stock_pool_lines, _validate_projection

VERSION = "sector-stock-discovery-pool-v1"
SEMANTICS = "ALL_QUALIFIED_GROUP_RETAINED_LEADERS_NOT_ALL_MEMBERS_OR_STOCK_QUALIFICATION"
AUTHORITY = {
    "human_attention_authority": "NONE", "research_authority": "NONE",
    "investment_authority": "NONE", "automatic_research_routing": False,
    "market_requests": 0, "events_created": 0, "market_state_writes": 0,
}


def _checked_leader(row: dict) -> tuple[str, str]:
    if not isinstance(row, dict) or not {"thscode", "ticker", "name", "daily_return", "turnover"} <= row.keys():
        raise ValueError("discovery leader identity or observation is missing")
    code, ticker, name = row["thscode"], row["ticker"], row["name"]
    if not all(isinstance(v, str) and v and v == v.strip() for v in (code, ticker, name)):
        raise ValueError("discovery leader identity is invalid")
    exchange = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}.get(code[-2:])
    if exchange is None or len(ticker) != 6 or to_hithink_thscode(ticker=ticker, exchange=exchange) != code:
        raise ValueError("discovery leader ticker/exchange identity differs")
    for key in ("daily_return", "turnover"):
        value = row[key]
        if isinstance(value, (bool, float)) or not isinstance(value, (str, int, Decimal)):
            raise ValueError("discovery leader numeric representation is invalid")
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError("discovery leader number is invalid") from exc
        if not number.is_finite() or (key == "turnover" and number < 0) or (key == "daily_return" and number < -1):
            raise ValueError("discovery leader number is invalid")
    return code, name


def build_stock_discovery_pool(result: dict) -> dict:
    """Retain all original group/driver leaders, merging only exact securities.

The producer/original-code reader still owns market qualification. These checks
bind the supplied saved result and its lossless partition; they do not rerun the
Sector detector or turn source consistency into economic truth.
    """
    if not isinstance(result, dict) or result.get("result_hash") != canonical_hash(
        {key: value for key, value in result.items() if key != "result_hash"}
    ):
        raise ValueError("discovery source result hash differs")
    _validate_projection(result)
    composition = result["composition"]
    shown = {group["group_key"] for group in composition["surfaced_groups"]}
    candidates = deepcopy(_stock_candidate_rows(result))
    for row in candidates:
        for origin in row["origins"]:
            _checked_leader(origin["retained_leader"])
        row.update(stock_qualification="NOT_CHECKED_BY_THIS_POOL",
                   business_link="NOT_ESTABLISHED_BY_THIS_POOL",
                   research_status="NOT_CHECKED_BY_THIS_POOL")
    direction_count = sum(len(_candidate_breadths(g)) for g in composition["all_groups"])
    origin_count = sum(len(row["origins"]) for row in candidates)
    body = {
        "version": VERSION, "semantics": SEMANTICS,
        "market_session": result["market_session"], "source_produced_at": result["produced_at"],
        "source_result_hash": result["result_hash"],
        "market_state_hash": result["output_market_state_hash"],
        "event_ledger_hash": result["event_ledger_update"]["event_ledger_hash"],
        "ordering": "DIRECTION_ROUND_ROBIN_RETAINED_POSITION_NOT_INVESTMENT_RANKING",
        "coverage": {
            "qualified_groups": len(composition["all_groups"]),
            "qualified_directions": direction_count,
            "homepage_groups": len(shown), "distinct_stocks": len(candidates),
            "retained_origin_records": origin_count,
            "stocks_only_outside_homepage": sum(
                not any(origin["group_on_homepage"] for origin in row["origins"]) for row in candidates),
            "all_members_covered": False, "ongoing_without_event_covered": False,
            "concept_universe_covered": False, "smart_money_covered": False,
        },
        "candidates": candidates, **AUTHORITY,
    }
    body["pool_hash"] = canonical_hash(body)
    return body


def plan_stock_discovery_batch(result: dict, *, pool_hash: str, offset: int = 0) -> dict:
    """Plan one bounded prefix of THIS pool; never claim it has been executed.

The caller must supply the original pool hash on every page. An offset is not a
cross-day cursor, progress receipt, retry permission, or automatic next dispatch.
    """
    from .stock_radar_reading import MAX_ISSUERS, MAX_MEMBERSHIPS, MAX_REQUESTS

    pool = build_stock_discovery_pool(result)
    rows = pool["candidates"]
    if pool_hash != pool["pool_hash"]:
        raise ValueError("discovery batch belongs to another pool")
    if type(offset) is not int or not 0 <= offset <= len(rows):
        raise ValueError("discovery batch offset is invalid")
    selected: list[str] = []
    directions: set[str] = set()
    for row in rows[offset:]:
        prospective = directions | {origin["sector_thscode"] for origin in row["origins"]}
        cost = 4 + len(prospective) + 3 * (len(selected) + 1)
        if (len(selected) + 1 > MAX_ISSUERS or len(prospective) > MAX_MEMBERSHIPS or cost > MAX_REQUESTS):
            if not selected:
                raise ValueError("one discovery candidate cannot fit the existing Stock budget")
            break
        selected.append(row["thscode"])
        directions = prospective
    end = offset + len(selected)
    body = {
        "version": "stock-discovery-batch-plan-v1", "pool_hash": pool_hash,
        "market_session": pool["market_session"], "offset": offset,
        "selected_codes": selected, "direction_codes": sorted(directions),
        "prior_page_codes": [row["thscode"] for row in rows[:offset]],
        "deferred_codes": [row["thscode"] for row in rows[end:]],
        "next_offset": end if end < len(rows) else None,
        "maximum_request_count": 4 + len(directions) + 3 * len(selected) if selected else 0,
        "limits": {"issuers": MAX_ISSUERS, "memberships": MAX_MEMBERSHIPS, "requests": MAX_REQUESTS},
        "execution": "NOT_EXECUTED", "prior_pages_execution": "NOT_ASSERTED",
        "routing_integration": "NOT_CONNECTED_TO_LIVE_STOCK_EXECUTOR",
        **AUTHORITY,
    }
    body["plan_hash"] = canonical_hash(body)
    return body


def render_stock_discovery_pool(result: dict) -> list[str]:
    """Strict saved-result consumer reusing the original pure display helper."""
    build_stock_discovery_pool(result)
    return _stock_pool_lines(result)
