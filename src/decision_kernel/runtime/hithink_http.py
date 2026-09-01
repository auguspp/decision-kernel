from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..adapters.hithink import (
    SHANGHAI_TZ,
    HithinkAdapterError,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    normalize_hithink_latest_completed_price,
    observed_market_from_completed_price,
)
from ..market import ObservedMarket


HITHINK_API_KEY_ENV = "HITHINK_FINANCE_API_KEY"
HITHINK_BASE_URL = "https://fuyao.aicubes.cn"
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class HithinkRuntimeError(RuntimeError):
    """The outer HiThink runtime could not produce the required live market input."""


def fetch_latest_hithink_observed_market(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> ObservedMarket:
    """Fetch exactly the calendar and raw history required for one live Odds price."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkRuntimeError("live observed_at must be timezone-aware")
    if not api_key:
        raise HithinkRuntimeError("HiThink credentials are required for live market data")

    if request_json is None:
        request_json = lambda path, params: _request_hithink_json(
            api_key=api_key,
            path=path,
            params=params,
            timeout_seconds=timeout_seconds,
        )

    calendar = normalize_hithink_calendar(
        request_json("/api/a-share/calendar/trading-days", {})
    )
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
        "/api/a-share/prices/historical",
        {
            "thscode": thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
            "adjust": "none",
        },
    )
    try:
        price = normalize_hithink_latest_completed_price(
            envelope,
            thscode=thscode,
            sessions=calendar,
            observed_at=observed_at,
        )
    except HithinkAdapterError:
        raise

    if price.as_of.date() != price.expected_latest_session:
        raise HithinkRuntimeError(
            "HiThink raw history does not reach the latest completed A-share session"
        )
    return observed_market_from_completed_price(price)


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
        raise HithinkRuntimeError(
            f"HiThink HTTP request failed with status {exc.code}"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HithinkRuntimeError(
            "HiThink request or response decoding failed"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HithinkRuntimeError("HiThink response is not a JSON object")
    return payload
