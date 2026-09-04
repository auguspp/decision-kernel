from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .hithink import (
    A_SHARE_CLOSE,
    SHANGHAI_TZ,
    latest_completed_a_share_session,
    require_hithink_data,
)


HITHINK_INDEX_MARKET_SOURCE = "HiThink Financial-API index daily market data"
HITHINK_INDEX_PRICE_CONVENTION = "UNADJUSTED_COMPLETED_A_SHARE_INDEX_CLOSE"
HITHINK_INDEX_SNAPSHOT_QUALIFICATION = (
    "PROVIDER_DATE_AND_BENCHMARK_LATEST_PREVIOUS_CLOSE_MATCH"
)

_INDEX_THSCODE = re.compile(r"^\d{6}\.(?:TI|SH|SZ)$")
_INDUSTRY_THSCODE = re.compile(r"^\d{6}\.TI$")
_BROAD_INDUSTRY_THSCODE = re.compile(r"^881\d{3}\.TI$")
_GRANULAR_INDUSTRY_THSCODE = re.compile(r"^884\d{3}\.TI$")
_PROVIDER_INDEX_TICKER = re.compile(r"^[0-9A-Z]{6}$")


class HithinkIndexAdapterError(ValueError):
    """HiThink index data cannot satisfy the explicit Harness contract."""


@dataclass(frozen=True)
class HithinkIndexIdentity:
    thscode: str
    name: str


@dataclass(frozen=True)
class HithinkIndustryCatalog:
    provider_timestamp_ms: int
    catalog_hash: str
    identities: tuple[HithinkIndexIdentity, ...]
    broad_industries: tuple[HithinkIndexIdentity, ...]
    granular_industries: tuple[HithinkIndexIdentity, ...]
    unexpected_industries: tuple[HithinkIndexIdentity, ...]


@dataclass(frozen=True)
class HithinkIndexSnapshotPoint:
    thscode: str
    ticker: str
    last_price: Decimal
    prev_price: Decimal
    price_change: Decimal
    price_change_ratio_pct: Decimal
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    volume: Decimal
    turnover: Decimal


@dataclass(frozen=True)
class HithinkIndexSnapshotBatch:
    provider_timestamp_ms: int
    requested_thscodes: tuple[str, ...]
    points: tuple[HithinkIndexSnapshotPoint, ...]


@dataclass(frozen=True)
class HithinkCompletedIndexPricePoint:
    close: Decimal
    volume: Decimal
    turnover: Decimal
    as_of: datetime


@dataclass(frozen=True)
class HithinkCompletedIndexHistory:
    thscode: str
    points: tuple[HithinkCompletedIndexPricePoint, ...]
    response_session: date
    expected_latest_session: date


@dataclass(frozen=True)
class HithinkQualifiedIndexSnapshotBatch:
    market_session: date
    benchmark_thscode: str
    provider_timestamp_ms: int
    qualification_method: str
    points: tuple[HithinkIndexSnapshotPoint, ...]


def _provider_timestamp_ms(data: Mapping[str, Any], *, endpoint: str) -> int:
    raw = data.get("timestamp")
    if isinstance(raw, bool):
        raise HithinkIndexAdapterError(f"{endpoint} has an invalid timestamp")
    try:
        timestamp = int(raw)
    except (TypeError, ValueError) as exc:
        raise HithinkIndexAdapterError(
            f"{endpoint} has an invalid timestamp"
        ) from exc
    if timestamp <= 0:
        raise HithinkIndexAdapterError(f"{endpoint} has an invalid timestamp")
    return timestamp


def _decimal(
    value: Any,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> Decimal:
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HithinkIndexAdapterError(
            f"HiThink index field {field} is not numeric"
        ) from exc
    if not normalized.is_finite():
        raise HithinkIndexAdapterError(
            f"HiThink index field {field} is not finite"
        )
    if positive and normalized <= 0:
        raise HithinkIndexAdapterError(
            f"HiThink index field {field} must be positive"
        )
    if non_negative and normalized < 0:
        raise HithinkIndexAdapterError(
            f"HiThink index field {field} must be non-negative"
        )
    return normalized


def normalize_hithink_index_thscode(thscode: str) -> str:
    normalized = thscode.strip().upper()
    if not _INDEX_THSCODE.fullmatch(normalized):
        raise HithinkIndexAdapterError(
            "HiThink index identity must be a six-digit .TI, .SH, or .SZ thscode"
        )
    return normalized


def normalize_hithink_index_provider_ticker(
    *,
    ticker: Any,
    thscode: str,
) -> str:
    """Preserve provider ticker metadata without replacing exact index identity.

    Exact requested and returned ``thscode`` remains canonical. HiThink may
    return six-character aliases such as ``1B0300`` for Shanghai standard
    indices, while formal ``.TI`` industry rows retain their six-digit code.
    """

    normalized_thscode = normalize_hithink_index_thscode(thscode)
    normalized_ticker = str(ticker).strip().upper()
    if not _PROVIDER_INDEX_TICKER.fullmatch(normalized_ticker):
        raise HithinkIndexAdapterError(
            "HiThink index snapshot ticker metadata is invalid for "
            f"{normalized_thscode}"
        )
    if (
        normalized_thscode.endswith(".TI")
        and normalized_ticker != normalized_thscode[:6]
    ):
        raise HithinkIndexAdapterError(
            "HiThink industry snapshot ticker disagrees with "
            f"{normalized_thscode}"
        )
    return normalized_ticker


def normalize_hithink_industry_catalog(
    envelope: Mapping[str, Any],
) -> HithinkIndustryCatalog:
    endpoint = "/api/a-share-index/catalog/ths-index-list"
    data = require_hithink_data(envelope, endpoint=endpoint)
    timestamp = _provider_timestamp_ms(data, endpoint=endpoint)
    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise HithinkIndexAdapterError("HiThink industry catalog is empty")

    by_thscode: dict[str, HithinkIndexIdentity] = {}
    for raw in items:
        if not isinstance(raw, Mapping):
            raise HithinkIndexAdapterError(
                "HiThink industry catalog contains a malformed row"
            )
        thscode = str(raw.get("thscode", "")).strip().upper()
        name = str(raw.get("name", "")).strip()
        if not _INDUSTRY_THSCODE.fullmatch(thscode) or not name:
            raise HithinkIndexAdapterError(
                "HiThink industry catalog contains an invalid identity"
            )
        if thscode in by_thscode:
            raise HithinkIndexAdapterError(
                f"HiThink industry catalog contains duplicate identity {thscode}"
            )
        by_thscode[thscode] = HithinkIndexIdentity(
            thscode=thscode,
            name=name,
        )

    identities = tuple(by_thscode[key] for key in sorted(by_thscode))
    canonical = json.dumps(
        [
            {
                "name": identity.name,
                "thscode": identity.thscode,
            }
            for identity in identities
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return HithinkIndustryCatalog(
        provider_timestamp_ms=timestamp,
        catalog_hash=hashlib.sha256(canonical).hexdigest(),
        identities=identities,
        broad_industries=tuple(
            identity
            for identity in identities
            if _BROAD_INDUSTRY_THSCODE.fullmatch(identity.thscode)
        ),
        granular_industries=tuple(
            identity
            for identity in identities
            if _GRANULAR_INDUSTRY_THSCODE.fullmatch(identity.thscode)
        ),
        unexpected_industries=tuple(
            identity
            for identity in identities
            if not _BROAD_INDUSTRY_THSCODE.fullmatch(identity.thscode)
            and not _GRANULAR_INDUSTRY_THSCODE.fullmatch(identity.thscode)
        ),
    )


def normalize_hithink_index_snapshot(
    envelope: Mapping[str, Any],
    *,
    requested_thscodes: Sequence[str],
) -> HithinkIndexSnapshotBatch:
    endpoint = "/api/a-share-index/prices/snapshot"
    normalized_requested = tuple(
        normalize_hithink_index_thscode(thscode)
        for thscode in requested_thscodes
    )
    if not normalized_requested:
        raise HithinkIndexAdapterError(
            "HiThink index snapshot requires at least one explicit identity"
        )
    if len(normalized_requested) != len(set(normalized_requested)):
        raise HithinkIndexAdapterError(
            "HiThink index snapshot request contains duplicate identities"
        )

    data = require_hithink_data(envelope, endpoint=endpoint)
    timestamp = _provider_timestamp_ms(data, endpoint=endpoint)
    items = data.get("item")
    if not isinstance(items, list):
        raise HithinkIndexAdapterError("HiThink index snapshot has no item list")

    total = data.get("total")
    if isinstance(total, bool):
        raise HithinkIndexAdapterError("HiThink index snapshot total is invalid")
    try:
        normalized_total = int(total)
    except (TypeError, ValueError) as exc:
        raise HithinkIndexAdapterError(
            "HiThink index snapshot total is invalid"
        ) from exc
    if normalized_total != len(items):
        raise HithinkIndexAdapterError(
            "HiThink index snapshot total disagrees with returned rows"
        )

    by_thscode: dict[str, HithinkIndexSnapshotPoint] = {}
    for raw in items:
        if not isinstance(raw, Mapping):
            raise HithinkIndexAdapterError(
                "HiThink index snapshot contains a malformed row"
            )
        thscode = normalize_hithink_index_thscode(
            str(raw.get("thscode", ""))
        )
        if thscode in by_thscode:
            raise HithinkIndexAdapterError(
                f"HiThink index snapshot contains duplicate identity {thscode}"
            )
        ticker = normalize_hithink_index_provider_ticker(
            ticker=raw.get("ticker"),
            thscode=thscode,
        )

        point = HithinkIndexSnapshotPoint(
            thscode=thscode,
            ticker=ticker,
            last_price=_decimal(
                raw.get("last_price"),
                field="last_price",
                positive=True,
            ),
            prev_price=_decimal(
                raw.get("prev_price"),
                field="prev_price",
                positive=True,
            ),
            price_change=_decimal(
                raw.get("price_change"),
                field="price_change",
            ),
            price_change_ratio_pct=_decimal(
                raw.get("price_change_ratio_pct"),
                field="price_change_ratio_pct",
            ),
            open_price=_decimal(
                raw.get("open_price"),
                field="open_price",
                positive=True,
            ),
            high_price=_decimal(
                raw.get("high_price"),
                field="high_price",
                positive=True,
            ),
            low_price=_decimal(
                raw.get("low_price"),
                field="low_price",
                positive=True,
            ),
            volume=_decimal(
                raw.get("volume"),
                field="volume",
                non_negative=True,
            ),
            turnover=_decimal(
                raw.get("turnover"),
                field="turnover",
                non_negative=True,
            ),
        )
        if point.low_price > point.high_price:
            raise HithinkIndexAdapterError(
                f"HiThink index snapshot low exceeds high for {thscode}"
            )
        if not point.low_price <= point.last_price <= point.high_price:
            raise HithinkIndexAdapterError(
                f"HiThink index snapshot last price is outside daily range for {thscode}"
            )
        by_thscode[thscode] = point

    requested_set = set(normalized_requested)
    returned_set = set(by_thscode)
    if requested_set != returned_set:
        missing = sorted(requested_set - returned_set)
        extra = sorted(returned_set - requested_set)
        raise HithinkIndexAdapterError(
            "HiThink index snapshot identities disagree with the explicit request; "
            f"missing={missing}; extra={extra}"
        )

    return HithinkIndexSnapshotBatch(
        provider_timestamp_ms=timestamp,
        requested_thscodes=normalized_requested,
        points=tuple(by_thscode[thscode] for thscode in normalized_requested),
    )


def normalize_hithink_completed_index_history(
    envelope: Mapping[str, Any],
    *,
    thscode: str,
    sessions: Sequence[date],
    observed_at: datetime,
) -> HithinkCompletedIndexHistory:
    endpoint = "/api/a-share-index/prices/historical"
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkIndexAdapterError("observed_at must be timezone-aware")
    normalized_thscode = normalize_hithink_index_thscode(thscode)
    normalized_sessions = tuple(sessions)
    if not normalized_sessions or normalized_sessions != tuple(
        sorted(set(normalized_sessions))
    ):
        raise HithinkIndexAdapterError(
            "trading calendar must be unique and ascending"
        )

    data = require_hithink_data(envelope, endpoint=endpoint)
    if str(data.get("thscode", "")).strip().upper() != normalized_thscode:
        raise HithinkIndexAdapterError(
            "HiThink index history thscode disagrees with the request"
        )
    if data.get("interval") != "1d":
        raise HithinkIndexAdapterError("HiThink index history is not daily")
    if data.get("adjust") is not None:
        raise HithinkIndexAdapterError(
            "HiThink index history unexpectedly contains adjustment semantics"
        )

    expected_latest = latest_completed_a_share_session(
        normalized_sessions,
        observed_at=observed_at,
    )
    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise HithinkIndexAdapterError("HiThink index history is empty")

    session_set = set(normalized_sessions)
    observed_local_date = observed_at.astimezone(SHANGHAI_TZ).date()
    bars: dict[date, tuple[Decimal, Decimal, Decimal]] = {}
    for raw in items:
        if not isinstance(raw, Mapping):
            raise HithinkIndexAdapterError(
                "HiThink index history contains a malformed row"
            )
        if any(
            raw.get(field) is None
            for field in ("date_ms", "close_price", "volume", "turnover")
        ):
            raise HithinkIndexAdapterError(
                "HiThink index history row is missing required fields"
            )
        try:
            session = datetime.fromtimestamp(
                int(raw["date_ms"]) / 1000,
                tz=SHANGHAI_TZ,
            ).date()
        except (TypeError, ValueError, OverflowError) as exc:
            raise HithinkIndexAdapterError(
                "HiThink index history row has an invalid date"
            ) from exc
        if session in bars:
            raise HithinkIndexAdapterError(
                "HiThink index history contains duplicate dates"
            )
        if session > observed_local_date:
            raise HithinkIndexAdapterError(
                "HiThink index history contains a future-dated bar"
            )
        if session not in session_set:
            raise HithinkIndexAdapterError(
                "HiThink index history contains an off-calendar bar"
            )
        bars[session] = (
            _decimal(
                raw.get("close_price"),
                field="close_price",
                positive=True,
            ),
            _decimal(
                raw.get("volume"),
                field="volume",
                non_negative=True,
            ),
            _decimal(
                raw.get("turnover"),
                field="turnover",
                non_negative=True,
            ),
        )

    response_timestamp = _provider_timestamp_ms(data, endpoint=endpoint)
    response_session = datetime.fromtimestamp(
        response_timestamp / 1000,
        tz=SHANGHAI_TZ,
    ).date()
    if response_session != max(bars):
        raise HithinkIndexAdapterError(
            "HiThink index history timestamp disagrees with its latest bar"
        )
    if response_session > expected_latest:
        raise HithinkIndexAdapterError(
            "HiThink index history extends beyond the latest completed session"
        )

    points = tuple(
        HithinkCompletedIndexPricePoint(
            close=bars[session][0],
            volume=bars[session][1],
            turnover=bars[session][2],
            as_of=datetime.combine(
                session,
                A_SHARE_CLOSE,
                tzinfo=SHANGHAI_TZ,
            ),
        )
        for session in sorted(bars)
    )
    return HithinkCompletedIndexHistory(
        thscode=normalized_thscode,
        points=points,
        response_session=response_session,
        expected_latest_session=expected_latest,
    )


def qualify_hithink_index_snapshot(
    snapshot: HithinkIndexSnapshotBatch,
    *,
    benchmark_history: HithinkCompletedIndexHistory,
) -> HithinkQualifiedIndexSnapshotBatch:
    if benchmark_history.response_session != benchmark_history.expected_latest_session:
        raise HithinkIndexAdapterError(
            "benchmark history is stale and cannot qualify an index snapshot"
        )
    if len(benchmark_history.points) < 2:
        raise HithinkIndexAdapterError(
            "benchmark history requires latest and previous completed closes"
        )

    benchmark_thscode = benchmark_history.thscode
    by_thscode = {point.thscode: point for point in snapshot.points}
    benchmark_snapshot = by_thscode.get(benchmark_thscode)
    if benchmark_snapshot is None:
        raise HithinkIndexAdapterError(
            "index snapshot does not contain its benchmark qualification identity"
        )

    latest = benchmark_history.points[-1]
    previous = benchmark_history.points[-2]
    if benchmark_snapshot.last_price != latest.close:
        raise HithinkIndexAdapterError(
            "index snapshot benchmark last price disagrees with completed history"
        )
    if benchmark_snapshot.prev_price != previous.close:
        raise HithinkIndexAdapterError(
            "index snapshot benchmark previous price disagrees with completed history"
        )

    provider_session = datetime.fromtimestamp(
        snapshot.provider_timestamp_ms / 1000,
        tz=SHANGHAI_TZ,
    ).date()
    if provider_session != benchmark_history.response_session:
        raise HithinkIndexAdapterError(
            "index snapshot provider date disagrees with the completed benchmark session"
        )

    return HithinkQualifiedIndexSnapshotBatch(
        market_session=benchmark_history.response_session,
        benchmark_thscode=benchmark_thscode,
        provider_timestamp_ms=snapshot.provider_timestamp_ms,
        qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
        points=snapshot.points,
    )
