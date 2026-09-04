from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..adapters.hithink import (
    SHANGHAI_TZ,
    HithinkCompletedPriceHistory,
    HithinkCompletedSessionPrice,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    normalize_hithink_completed_price_history,
    observed_market_from_completed_price,
)
from ..market import ObservedMarket


HITHINK_API_KEY_ENV = "HITHINK_FINANCE_API_KEY"
HITHINK_BASE_URL = "https://fuyao.aicubes.cn"
HITHINK_CALENDAR_PATH = "/api/a-share/calendar/trading-days"
HITHINK_HISTORY_PATH = "/api/a-share/prices/historical"
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class HithinkRuntimeError(RuntimeError):
    """The outer HiThink runtime could not produce the required qualified market input."""


@lru_cache(maxsize=8)
def _request_hithink_calendar(
    *,
    api_key: str,
    shanghai_date: date,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    """Reuse one exact calendar response per credential/date in this process only.

    `shanghai_date` deliberately participates in the cache key even though the
    provider endpoint has no date parameter. A long-lived Harness process therefore
    cannot carry yesterday's calendar into a new Shanghai date. History responses
    are never cached. Exceptions are not cached by ``lru_cache``.
    """

    del shanghai_date
    return _request_hithink_json(
        api_key=api_key,
        path=HITHINK_CALENDAR_PATH,
        params={},
        timeout_seconds=timeout_seconds,
    )


def fetch_hithink_completed_price_history(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> HithinkCompletedPriceHistory:
    """Fetch the existing 45-day raw-close window for Harness consumers.

    This is commodity acquisition only. It does not classify anomalies, allocate
    Research attention, change fundamental state, or carry investment authority.
    The live runtime still requires the provider response to reach the latest
    completed A-share session.
    """

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkRuntimeError("live observed_at must be timezone-aware")
    if not api_key:
        raise HithinkRuntimeError("HiThink credentials are required for live market data")

    if request_json is None:
        calendar_envelope = _request_hithink_calendar(
            api_key=api_key,
            shanghai_date=observed_at.astimezone(SHANGHAI_TZ).date(),
            timeout_seconds=timeout_seconds,
        )
        request_json = lambda path, params: _request_hithink_json(
            api_key=api_key,
            path=path,
            params=params,
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
    start_at = end_at - timedelta(days=45)
    envelope = request_json(
        HITHINK_HISTORY_PATH,
        {
            "thscode": thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
            "adjust": "none",
        },
    )
    history = normalize_hithink_completed_price_history(
        envelope,
        thscode=thscode,
        sessions=calendar,
        observed_at=observed_at,
    )
    if history.response_session != history.expected_latest_session:
        raise HithinkRuntimeError(
            "HiThink raw history does not reach the latest completed A-share session"
        )
    return history


def fetch_latest_hithink_observed_market(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> ObservedMarket:
    """Fetch the latest qualified completed close for live Odds."""

    history = fetch_hithink_completed_price_history(
        thscode=thscode,
        observed_at=observed_at,
        api_key=api_key,
        request_json=request_json,
        timeout_seconds=timeout_seconds,
    )
    latest = history.points[-1]
    return observed_market_from_completed_price(
        HithinkCompletedSessionPrice(
            thscode=history.thscode,
            close=latest.close,
            as_of=latest.as_of,
            expected_latest_session=history.expected_latest_session,
        )
    )


def _request_hithink_json(
    *,
    api_key: str,
    path: str,
    params: Mapping[str, str],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    query = urlencode(params)
    url = f"{HITHINK_BASE_URL}{path}{'?' if query else ''}{query}"
    request = Request(
        url,
        headers={"Accept": "application/json", "X-api-key": api_key},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = f"HiThink HTTP request failed for {path} with status {exc.code}"
        retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
        if retry_after:
            safe_retry_after = " ".join(retry_after.split())[:64]
            message += f"; Retry-After={safe_retry_after}"
        raise HithinkRuntimeError(message) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HithinkRuntimeError(
            f"HiThink request or response decoding failed for {path}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HithinkRuntimeError("HiThink response is not a JSON object")
    return payload
