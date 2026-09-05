from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ,
    latest_completed_a_share_session,
    require_hithink_data,
)
from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkQualifiedIndexSnapshotBatch,
)
from decision_kernel.identity import canonical_hash

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
HITHINK_STOCK_REFERENCE_SEMANTICS = (
    "OBSERVED_STOCK_QUOTES_FOR_OFFLINE_RECONCILIATION_NOT_PER_SECURITY_SESSION_PROOF"
)
HITHINK_STOCK_TIMESTAMP_SEMANTICS = "PROVIDER_DATA_READY_TIME_NOT_MARKET_SESSION"
# Capture after the fixed-price trading window too; this is an acquisition guard,
# not a guarantee of provider finality or a change to the index close convention.
STOCK_REFERENCE_NOT_BEFORE = time(15, 30)
HITHINK_SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY = "NONE"
HITHINK_SECTOR_BREADTH_INVESTMENT_AUTHORITY = "NONE"

_A_SHARE_THSCODE = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


@dataclass(frozen=True)
class HithinkStockSnapshotReference:
    """Explicit opt-in for the isolated dump study, not a new production default.

    A benchmark/calendar anchors the comparison session, not each stock quote's
    last-trade date. The provider does not expose per-row timestamps here. Exact
    date-keyed dump reconciliation is still required and can reject the result.
    Weekday gaps, including holidays not independently established here, fail.
    """

    trading_sessions: tuple[date, ...]
    benchmark: HithinkQualifiedIndexSnapshotBatch
    observed_at: datetime

    @property
    def market_session(self) -> date:
        return self.benchmark.market_session

    def validate(self) -> None:
        _aware_reference_clock(self.observed_at)
        sessions = self.trading_sessions
        if (
            not isinstance(sessions, tuple)
            or not sessions
            or any(type(day) is not date or day.weekday() >= 5 for day in sessions)
            or sessions != tuple(sorted(set(sessions)))
        ):
            raise HithinkRuntimeError("stock reference calendar must be exact ascending weekday sessions")
        if (
            not isinstance(self.benchmark, HithinkQualifiedIndexSnapshotBatch)
            or self.benchmark.benchmark_thscode != "000300.SH"
            or self.benchmark.qualification_method != HITHINK_INDEX_SNAPSHOT_QUALIFICATION
            or sum(p.thscode == "000300.SH" for p in self.benchmark.points) != 1
        ):
            raise HithinkRuntimeError("stock reference requires the qualified CSI300 price anchor")
        session = self.market_session
        if type(session) is not date or session not in sessions:
            raise HithinkRuntimeError("stock reference benchmark session is absent from calendar")
        if latest_completed_a_share_session(sessions, observed_at=self.observed_at) != session:
            raise HithinkRuntimeError("stock reference benchmark/calendar session disagreement")
        local = self.observed_at.astimezone(SHANGHAI_TZ)
        if local.date() == session:
            if local.time() < STOCK_REFERENCE_NOT_BEFORE:
                raise HithinkRuntimeError("stock reference capture is before 15:30 completed-session boundary")
        elif not (
            session.weekday() == 4
            and local.weekday() in (5, 6)
            and 1 <= (local.date() - session).days <= 2
        ):
            raise HithinkRuntimeError(
                "stock reference weekday gap or unfinished session; calendar absence is not holiday evidence"
            )

    def validate_received_at(self, received_at: datetime) -> None:
        self.validate()
        _aware_reference_clock(received_at)
        if received_at < self.observed_at:
            raise HithinkRuntimeError("stock reference receive clock precedes observation")
        if received_at.astimezone(SHANGHAI_TZ).date() != self.observed_at.astimezone(SHANGHAI_TZ).date():
            raise HithinkRuntimeError("stock reference capture crossed an observation-date boundary")

    def validate_ready_time(self, timestamp_ms: Any, *, received_at: datetime) -> None:
        self.validate_received_at(received_at)
        if type(timestamp_ms) is not int or timestamp_ms <= 0:
            raise HithinkRuntimeError("stock reference data-ready timestamp must be positive integer milliseconds")
        try:
            ready = datetime.fromtimestamp(timestamp_ms / 1000, tz=SHANGHAI_TZ)
        except (OSError, OverflowError, ValueError) as exc:
            raise HithinkRuntimeError("stock reference data-ready timestamp is invalid") from exc
        lower = datetime.combine(self.market_session, STOCK_REFERENCE_NOT_BEFORE, tzinfo=SHANGHAI_TZ)
        if ready < lower:
            raise HithinkRuntimeError("stock reference data-ready time precedes the completed capture boundary")
        if ready > received_at:
            raise HithinkRuntimeError("stock reference data-ready time follows response receipt")

    def evidence(self) -> dict[str, Any]:
        self.validate()
        return {
            "semantics": HITHINK_STOCK_REFERENCE_SEMANTICS,
            "provider_timestamp_semantics": HITHINK_STOCK_TIMESTAMP_SEMANTICS,
            "comparison_session": self.market_session.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "calendar_hash": canonical_hash(self.trading_sessions),
            "qualified_benchmark_hash": canonical_hash(asdict(self.benchmark)),
            "closed_interval_basis": (
                "SAME_SESSION_AFTER_1530"
                if self.observed_at.astimezone(SHANGHAI_TZ).date() == self.market_session
                else "FRIDAY_TO_SATURDAY_OR_SUNDAY_ONLY"
            ),
            "per_security_market_session": "NOT_PROVEN_BY_PAGE_TIMESTAMP",
            "production_qualification": "NOT_ESTABLISHED",
        }


def _aware_reference_clock(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise HithinkRuntimeError("stock reference clocks must be timezone-aware")


@dataclass(frozen=True)
class HithinkAllMarketSnapshotBatch:
    """Exact paginated quotes under the explicitly recorded snapshot semantics."""

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
    reference_context: HithinkStockSnapshotReference | None = None,
    received_at: Callable[[], datetime] | None = None,
) -> HithinkAllMarketSnapshotBatch:
    """Fetch exact paginated quotes, with an explicit isolated-study opt-in.

    With no reference_context the existing Sector producer date-equality contract
    is unchanged. With a context, page timestamps are data-ready clocks bounded by
    the completed capture window and response receipt; they do not prove each stock
    traded in the anchor session. Missing values remain explicit in both modes.
    """

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    if isinstance(page_size, bool) or page_size <= 0:
        raise HithinkRuntimeError(
            "HiThink all-market snapshot page_size must be positive"
        )
    if reference_context is not None:
        reference_context.validate()
        if reference_context.market_session != market_session:
            raise HithinkRuntimeError("stock reference context disagrees with requested market session")
    elif received_at is not None:
        raise HithinkRuntimeError("stock reference receive clock requires an explicit reference context")
    receive_clock = received_at or (lambda: datetime.now(timezone.utc))
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
        if reference_context is not None:
            reference_context.validate_ready_time(data.get("timestamp"), received_at=receive_clock())
        timestamp_ms = _provider_timestamp_ms(
            data,
            endpoint=HITHINK_A_SHARE_SNAPSHOT_PATH,
        )
        provider_session = datetime.fromtimestamp(
            timestamp_ms / 1000,
            tz=SHANGHAI_TZ,
        ).date()
        if reference_context is None and provider_session != market_session:
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
        snapshot_semantics=(HITHINK_ALL_MARKET_SNAPSHOT_SEMANTICS if reference_context is None else HITHINK_STOCK_REFERENCE_SEMANTICS),
    )
