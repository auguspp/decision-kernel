from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from decision_kernel.adapters.hithink import SHANGHAI_TZ, require_hithink_data

from .hithink_http import HithinkRuntimeError, _request_hithink_json
from .sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    SectorMembershipSnapshot,
    normalize_sector_membership,
)


HITHINK_SECTOR_CONSTITUENTS_PATH = (
    "/api/a-share-index/constituents/ths-stock-list"
)
HITHINK_A_SHARE_SNAPSHOT_PATH = "/api/a-share/prices/snapshot"
HITHINK_A_SHARE_SNAPSHOT_PAGE_SIZE = 500
HITHINK_SECTOR_MEMBERSHIP_SEMANTICS = "CURRENT_CONSTITUENTS_AT_CAPTURE_ONLY"
HITHINK_ALL_MARKET_SNAPSHOT_SEMANTICS = (
    "CURRENT_COMPLETED_SESSION_ALL_A_SHARE_SNAPSHOT"
)
HITHINK_SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY = "NONE"
HITHINK_SECTOR_BREADTH_INVESTMENT_AUTHORITY = "NONE"

_A_SHARE_THSCODE = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


@dataclass(frozen=True)
class HithinkAllMarketSnapshotBatch:
    """One exact paginated A-share snapshot for a qualified market session."""

    market_session: date
    page_size: int
    page_count: int
    declared_total: int
    returned_unique_rows: int
    priced_rows: int
    unpriced_rows: int
    provider_timestamp_min_ms: int
    provider_timestamp_max_ms: int
    points: tuple[ConstituentMarketPoint, ...]
    snapshot_semantics: str = HITHINK_ALL_MARKET_SNAPSHOT_SEMANTICS
    human_attention_authority: str = (
        HITHINK_SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = HITHINK_SECTOR_BREADTH_INVESTMENT_AUTHORITY


def _require_runtime_inputs(
    *,
    api_key: str | None,
    timeout_seconds: float,
) -> str:
    if not api_key:
        raise HithinkRuntimeError(
            "HiThink credentials are required for sector breadth acquisition"
        )
    if timeout_seconds <= 0:
        raise HithinkRuntimeError(
            "HiThink sector breadth timeout must be positive"
        )
    return api_key


def _default_request_json(
    *,
    api_key: str,
    timeout_seconds: float,
) -> _RequestJSON:
    return lambda path, params: _request_hithink_json(
        api_key=api_key,
        path=path,
        params=params,
        timeout_seconds=timeout_seconds,
    )


def _provider_timestamp_ms(
    data: Mapping[str, Any],
    *,
    endpoint: str,
) -> int:
    raw = data.get("timestamp")
    if isinstance(raw, bool):
        raise HithinkRuntimeError(f"{endpoint} has an invalid timestamp")
    try:
        timestamp_ms = int(raw)
    except (TypeError, ValueError) as exc:
        raise HithinkRuntimeError(
            f"{endpoint} has an invalid timestamp"
        ) from exc
    if timestamp_ms <= 0:
        raise HithinkRuntimeError(f"{endpoint} has an invalid timestamp")
    return timestamp_ms


def _non_negative_int(
    value: Any,
    *,
    field: str,
) -> int:
    if isinstance(value, bool):
        raise HithinkRuntimeError(f"{field} must be a non-negative integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HithinkRuntimeError(
            f"{field} must be a non-negative integer"
        ) from exc
    if parsed < 0:
        raise HithinkRuntimeError(f"{field} must be a non-negative integer")
    return parsed


def _optional_decimal(
    value: Any,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise HithinkRuntimeError(f"{field} must be numeric or null")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HithinkRuntimeError(f"{field} must be numeric or null") from exc
    if not parsed.is_finite():
        raise HithinkRuntimeError(f"{field} must be finite")
    if positive and parsed <= 0:
        raise HithinkRuntimeError(f"{field} must be positive when present")
    if non_negative and parsed < 0:
        raise HithinkRuntimeError(
            f"{field} must be non-negative when present"
        )
    return parsed


def normalize_hithink_sector_membership(
    envelope: Mapping[str, Any],
    *,
    sector_thscode: str,
    sector_name: str,
) -> SectorMembershipSnapshot:
    """Normalize one current HiThink constituent response into the pure contract."""

    data = require_hithink_data(
        envelope,
        endpoint=HITHINK_SECTOR_CONSTITUENTS_PATH,
    )
    timestamp_ms = _provider_timestamp_ms(
        data,
        endpoint=HITHINK_SECTOR_CONSTITUENTS_PATH,
    )
    raw_items = data.get("item")
    if not isinstance(raw_items, list) or not raw_items:
        raise HithinkRuntimeError(
            f"HiThink current membership is empty for {sector_thscode}"
        )

    members: list[SectorConstituentIdentity] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, Mapping):
            raise HithinkRuntimeError(
                "HiThink current membership contains a malformed row at "
                f"index {index}"
            )
        members.append(
            SectorConstituentIdentity(
                thscode=str(raw.get("thscode", "")),
                ticker=str(raw.get("ticker", "")),
                name=str(raw.get("name", "")),
            )
        )

    try:
        return normalize_sector_membership(
            sector_thscode=sector_thscode,
            sector_name=sector_name,
            captured_at=datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=SHANGHAI_TZ,
            ),
            members=members,
        )
    except ValueError as exc:
        raise HithinkRuntimeError(
            f"HiThink current membership is invalid for {sector_thscode}: {exc}"
        ) from exc


def fetch_hithink_sector_membership(
    *,
    sector_thscode: str,
    sector_name: str,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> SectorMembershipSnapshot:
    """Fetch one exact current `.TI` constituent set with no fallback."""

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    request_json = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )
    envelope = request_json(
        HITHINK_SECTOR_CONSTITUENTS_PATH,
        {"thscode": sector_thscode.strip().upper()},
    )
    return normalize_hithink_sector_membership(
        envelope,
        sector_thscode=sector_thscode,
        sector_name=sector_name,
    )


def _normalize_stock_snapshot_point(
    raw: Mapping[str, Any],
    *,
    market_session: date,
    row_label: str,
) -> ConstituentMarketPoint:
    thscode = str(raw.get("thscode", "")).strip().upper()
    ticker = str(raw.get("ticker", "")).strip()
    if not _A_SHARE_THSCODE.fullmatch(thscode):
        raise HithinkRuntimeError(
            f"{row_label} has an invalid A-share identity {thscode!r}"
        )
    if ticker != thscode[:6]:
        raise HithinkRuntimeError(
            f"{row_label} ticker disagrees with A-share identity {thscode}"
        )

    return ConstituentMarketPoint(
        thscode=thscode,
        market_session=market_session,
        last_price=_optional_decimal(
            raw.get("last_price"),
            field=f"{row_label} last_price",
            positive=True,
        ),
        prev_price=_optional_decimal(
            raw.get("prev_price"),
            field=f"{row_label} prev_price",
            positive=True,
        ),
        turnover=_optional_decimal(
            raw.get("turnover"),
            field=f"{row_label} turnover",
            non_negative=True,
        ),
    )


def fetch_hithink_all_market_snapshot(
    *,
    market_session: date,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
    page_size: int = HITHINK_A_SHARE_SNAPSHOT_PAGE_SIZE,
) -> HithinkAllMarketSnapshotBatch:
    """Fetch one exact paginated current A-share snapshot.

    The caller must supply the independently qualified completed market session.
    Every provider page must map to that same Shanghai date. Missing market values
    remain explicit and are not converted into zero returns.
    """

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    if isinstance(page_size, bool) or page_size <= 0:
        raise HithinkRuntimeError(
            "HiThink all-market snapshot page_size must be positive"
        )
    request_json = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )

    by_code: dict[str, ConstituentMarketPoint] = {}
    provider_timestamps: list[int] = []
    declared_total: int | None = None
    page_count = 0
    offset = 0

    while True:
        envelope = request_json(
            HITHINK_A_SHARE_SNAPSHOT_PATH,
            {"limit": str(page_size), "offset": str(offset)},
        )
        data = require_hithink_data(
            envelope,
            endpoint=HITHINK_A_SHARE_SNAPSHOT_PATH,
        )
        timestamp_ms = _provider_timestamp_ms(
            data,
            endpoint=HITHINK_A_SHARE_SNAPSHOT_PATH,
        )
        provider_session = datetime.fromtimestamp(
            timestamp_ms / 1000,
            tz=SHANGHAI_TZ,
        ).date()
        if provider_session != market_session:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot provider date disagrees with the "
                f"qualified market session: {provider_session} != {market_session}"
            )
        provider_timestamps.append(timestamp_ms)

        page_total = _non_negative_int(
            data.get("total"),
            field="HiThink all-market snapshot total",
        )
        if page_total <= 0:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot declared total must be positive"
            )
        if declared_total is None:
            declared_total = page_total
        elif page_total != declared_total:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot total changed during pagination"
            )

        raw_items = data.get("item")
        if not isinstance(raw_items, list):
            raise HithinkRuntimeError(
                "HiThink all-market snapshot page has no item list"
            )
        if len(raw_items) > page_size:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot page exceeds the requested limit"
            )
        if not raw_items and len(by_code) < declared_total:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot pagination ended before total"
            )

        for index, raw in enumerate(raw_items):
            if not isinstance(raw, Mapping):
                raise HithinkRuntimeError(
                    "HiThink all-market snapshot contains a malformed row at "
                    f"offset {offset + index}"
                )
            point = _normalize_stock_snapshot_point(
                raw,
                market_session=market_session,
                row_label=f"HiThink stock snapshot row {offset + index}",
            )
            if point.thscode in by_code:
                raise HithinkRuntimeError(
                    "HiThink all-market snapshot contains duplicate identity "
                    f"{point.thscode}"
                )
            by_code[point.thscode] = point

        page_count += 1
        if len(by_code) > declared_total:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot returned more rows than declared"
            )
        if len(by_code) == declared_total:
            break
        if len(raw_items) < page_size:
            raise HithinkRuntimeError(
                "HiThink all-market snapshot short page ended before declared total"
            )
        offset += page_size

    ordered_points = tuple(by_code[code] for code in sorted(by_code))
    priced_rows = sum(
        point.last_price is not None
        and point.prev_price is not None
        and point.turnover is not None
        for point in ordered_points
    )
    return HithinkAllMarketSnapshotBatch(
        market_session=market_session,
        page_size=page_size,
        page_count=page_count,
        declared_total=declared_total,
        returned_unique_rows=len(ordered_points),
        priced_rows=priced_rows,
        unpriced_rows=len(ordered_points) - priced_rows,
        provider_timestamp_min_ms=min(provider_timestamps),
        provider_timestamp_max_ms=max(provider_timestamps),
        points=ordered_points,
    )
