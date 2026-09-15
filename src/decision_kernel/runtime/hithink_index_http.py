from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

from ..adapters.hithink import (
    SHANGHAI_TZ,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
)
from ..adapters.hithink_index import (
    HithinkCompletedIndexHistory,
    HithinkIndustryCatalog,
    HithinkIndexSnapshotBatch,
    HithinkQualifiedIndexSnapshotBatch,
    normalize_hithink_completed_index_history,
    normalize_hithink_industry_catalog,
    normalize_hithink_index_snapshot,
    normalize_hithink_index_thscode,
    qualify_hithink_index_snapshot,
)
from .hithink_http import (
    HITHINK_CALENDAR_PATH,
    HithinkRuntimeError,
    _request_hithink_calendar,
    _request_hithink_json,
)


HITHINK_INDEX_CATALOG_PATH = "/api/a-share-index/catalog/ths-index-list"
HITHINK_INDEX_SNAPSHOT_PATH = "/api/a-share-index/prices/snapshot"
HITHINK_INDEX_HISTORY_PATH = "/api/a-share-index/prices/historical"
HITHINK_INDEX_HISTORY_LOOKBACK_DAYS = 240

_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


def _require_runtime_inputs(
    *,
    api_key: str | None,
    observed_at: datetime | None = None,
) -> str:
    if not api_key:
        raise HithinkRuntimeError(
            "HiThink credentials are required for live index market data"
        )
    if observed_at is not None and (
        observed_at.tzinfo is None or observed_at.utcoffset() is None
    ):
        raise HithinkRuntimeError("live index observed_at must be timezone-aware")
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


def _validate_runtime_calendar(
    sessions: Sequence[date],
) -> tuple[date, ...]:
    normalized = tuple(sessions)
    if not normalized or normalized != tuple(sorted(set(normalized))):
        raise HithinkRuntimeError(
            "HiThink trading calendar must be non-empty, unique and ascending"
        )
    return normalized


def _resolve_runtime_calendar(
    *,
    trading_sessions: Sequence[date] | None,
    observed_at: datetime,
    api_key: str,
    request_json: _RequestJSON | None,
    effective_request: _RequestJSON,
    timeout_seconds: float,
) -> tuple[date, ...]:
    if trading_sessions is not None:
        return _validate_runtime_calendar(trading_sessions)
    if request_json is None:
        envelope = _request_hithink_calendar(
            api_key=api_key,
            shanghai_date=observed_at.astimezone(SHANGHAI_TZ).date(),
            timeout_seconds=timeout_seconds,
        )
    else:
        envelope = effective_request(HITHINK_CALENDAR_PATH, {})
    return _validate_runtime_calendar(normalize_hithink_calendar(envelope))


def fetch_hithink_industry_catalog(
    *,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> HithinkIndustryCatalog:
    """Fetch one exact HiThink formal-industry catalog.

    This is Harness acquisition only. It does not select candidates, rank sectors,
    allocate Research attention, or carry investment authority.
    """

    normalized_key = _require_runtime_inputs(api_key=api_key)
    request_json = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )
    envelope = request_json(
        HITHINK_INDEX_CATALOG_PATH,
        {"tag": "industry"},
    )
    return normalize_hithink_industry_catalog(envelope)


def fetch_hithink_index_snapshot_batch(
    *,
    thscodes: Sequence[str],
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> HithinkIndexSnapshotBatch:
    """Fetch an explicit index snapshot batch without inferring session freshness."""

    normalized_key = _require_runtime_inputs(api_key=api_key)
    requested = tuple(
        normalize_hithink_index_thscode(thscode)
        for thscode in thscodes
    )
    request_json = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )
    envelope = request_json(
        HITHINK_INDEX_SNAPSHOT_PATH,
        {"thscodes": ",".join(requested)},
    )
    return normalize_hithink_index_snapshot(
        envelope,
        requested_thscodes=requested,
    )


def fetch_hithink_completed_index_history(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
    lookback_calendar_days: int = HITHINK_INDEX_HISTORY_LOOKBACK_DAYS,
    trading_sessions: Sequence[date] | None = None,
) -> HithinkCompletedIndexHistory:
    """Fetch one qualified completed-session index history window."""

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        observed_at=observed_at,
    )
    normalized_thscode = normalize_hithink_index_thscode(thscode)
    if lookback_calendar_days <= 0:
        raise HithinkRuntimeError(
            "HiThink index history lookback must be positive"
        )

    effective_request = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )
    calendar = _resolve_runtime_calendar(
        trading_sessions=trading_sessions,
        observed_at=observed_at,
        api_key=normalized_key,
        request_json=request_json,
        effective_request=effective_request,
        timeout_seconds=timeout_seconds,
    )
    expected_latest = latest_completed_a_share_session(
        calendar,
        observed_at=observed_at,
    )
    exclusive_end_at = datetime.combine(
        expected_latest + timedelta(days=1),
        datetime.min.time(),
        tzinfo=SHANGHAI_TZ,
    )
    # HiThink daily history can include a bar keyed exactly at `end`. Keep the
    # request inside the latest completed session; strict adapter qualification
    # still rejects any unfinished/future bar that crosses this bound.
    end_at = exclusive_end_at - timedelta(milliseconds=1)
    start_at = exclusive_end_at - timedelta(days=lookback_calendar_days)
    envelope = effective_request(
        HITHINK_INDEX_HISTORY_PATH,
        {
            "thscode": normalized_thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
        },
    )
    history = normalize_hithink_completed_index_history(
        envelope,
        thscode=normalized_thscode,
        sessions=calendar,
        observed_at=observed_at,
    )
    if history.response_session != history.expected_latest_session:
        raise HithinkRuntimeError(
            "HiThink index history does not reach the latest completed A-share session"
        )
    return history


def fetch_hithink_qualified_index_snapshot_batch(
    *,
    thscodes: Sequence[str],
    benchmark_thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
    trading_sessions: Sequence[date] | None = None,
) -> HithinkQualifiedIndexSnapshotBatch:
    """Fetch and qualify one explicit snapshot against completed benchmark history.

    HiThink defines the snapshot timestamp as data-ready time, not the represented
    market session. The completed session is anchored by exact latest/previous
    benchmark closes and an independently normalized trading calendar. A timestamp
    on a weekend or holiday may therefore follow the completed market date, while a
    timestamp on a later trading session remains disallowed.
    """

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        observed_at=observed_at,
    )
    requested = tuple(
        normalize_hithink_index_thscode(thscode)
        for thscode in thscodes
    )
    normalized_benchmark = normalize_hithink_index_thscode(benchmark_thscode)
    if normalized_benchmark not in set(requested):
        raise HithinkRuntimeError(
            "qualified index snapshot request must include its benchmark identity"
        )

    effective_request = request_json or _default_request_json(
        api_key=normalized_key,
        timeout_seconds=timeout_seconds,
    )
    snapshot = fetch_hithink_index_snapshot_batch(
        thscodes=requested,
        api_key=normalized_key,
        request_json=effective_request,
        timeout_seconds=timeout_seconds,
    )
    calendar = _resolve_runtime_calendar(
        trading_sessions=trading_sessions,
        observed_at=observed_at,
        api_key=normalized_key,
        request_json=request_json,
        effective_request=effective_request,
        timeout_seconds=timeout_seconds,
    )
    benchmark_history = fetch_hithink_completed_index_history(
        thscode=normalized_benchmark,
        observed_at=observed_at,
        api_key=normalized_key,
        request_json=effective_request,
        timeout_seconds=timeout_seconds,
        trading_sessions=calendar,
    )
    return qualify_hithink_index_snapshot(
        snapshot,
        benchmark_history=benchmark_history,
        trading_sessions=calendar,
        observed_at=observed_at,
    )
