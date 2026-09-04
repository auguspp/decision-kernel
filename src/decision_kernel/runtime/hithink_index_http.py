from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
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
    requested = tuple(thscodes)
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
) -> HithinkCompletedIndexHistory:
    """Fetch one qualified completed-session index history window."""

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        observed_at=observed_at,
    )
    if lookback_calendar_days <= 0:
        raise HithinkRuntimeError(
            "HiThink index history lookback must be positive"
        )

    if request_json is None:
        calendar_envelope = _request_hithink_calendar(
            api_key=normalized_key,
            shanghai_date=observed_at.astimezone(SHANGHAI_TZ).date(),
            timeout_seconds=timeout_seconds,
        )
        request_json = _default_request_json(
            api_key=normalized_key,
            timeout_seconds=timeout_seconds,
        )
    else:
        calendar_envelope = request_json(HITHINK_CALENDAR_PATH, {})

    calendar = normalize_hithink_calendar(calendar_envelope)
    expected_latest = latest_completed_a_share_session(
        calendar,
        observed_at=observed_at,
    )
    end_at = datetime.combine(
        expected_latest + timedelta(days=1),
        datetime.min.time(),
        tzinfo=SHANGHAI_TZ,
    )
    start_at = end_at - timedelta(days=lookback_calendar_days)
    envelope = request_json(
        HITHINK_INDEX_HISTORY_PATH,
        {
            "thscode": thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
        },
    )
    history = normalize_hithink_completed_index_history(
        envelope,
        thscode=thscode,
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
) -> HithinkQualifiedIndexSnapshotBatch:
    """Fetch and qualify one explicit sector snapshot against completed benchmark history.

    The snapshot timestamp is not trusted by itself. Qualification requires the
    provider date, latest benchmark close and previous benchmark close to agree with
    the independently normalized completed-session history.
    """

    normalized_key = _require_runtime_inputs(
        api_key=api_key,
        observed_at=observed_at,
    )
    requested = tuple(thscodes)
    if benchmark_thscode.strip().upper() not in {
        value.strip().upper() for value in requested
    }:
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
    benchmark_history = fetch_hithink_completed_index_history(
        thscode=benchmark_thscode,
        observed_at=observed_at,
        api_key=normalized_key,
        request_json=effective_request,
        timeout_seconds=timeout_seconds,
    )
    return qualify_hithink_index_snapshot(
        snapshot,
        benchmark_history=benchmark_history,
    )
