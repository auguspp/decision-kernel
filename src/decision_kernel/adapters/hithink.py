from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from ..market import ObservedMarket


HITHINK_API_KEY_ENV = "HITHINK_FINANCE_API_KEY"
HITHINK_BASE_URL = "https://fuyao.aicubes.cn"
HITHINK_MARKET_SOURCE = "HiThink Financial-API raw daily close"
HITHINK_PRICE_CONVENTION = "RAW_UNADJUSTED_LATEST_COMPLETED_A_SHARE_CLOSE"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
A_SHARE_CLOSE = time(15, 0)
_A_SHARE_TICKER = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class HithinkAdapterError(ValueError):
    """HiThink data cannot satisfy the qualified completed-session contract."""


@dataclass(frozen=True)
class HithinkCompletedSessionPrice:
    thscode: str
    close: Decimal
    as_of: datetime
    expected_latest_session: date


def require_hithink_data(
    envelope: Mapping[str, Any],
    *,
    endpoint: str,
) -> Mapping[str, Any]:
    code = envelope.get("code")
    if code != 0:
        request_id = envelope.get("request_id")
        raise HithinkAdapterError(
            f"{endpoint} returned business code {code}; request_id={request_id}"
        )
    data = envelope.get("data")
    if not isinstance(data, Mapping):
        raise HithinkAdapterError(f"{endpoint} returned no data object")
    return data


def normalize_hithink_calendar(
    envelope: Mapping[str, Any],
) -> tuple[date, ...]:
    data = require_hithink_data(
        envelope,
        endpoint="/api/a-share/calendar/trading-days",
    )
    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise HithinkAdapterError("A-share trading calendar is empty")

    sessions: list[date] = []
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("date"), str):
            raise HithinkAdapterError(
                "A-share trading calendar contains a malformed row"
            )
        try:
            session = datetime.strptime(item["date"], "%Y%m%d").date()
        except ValueError as exc:
            raise HithinkAdapterError(
                "A-share trading calendar has an invalid date"
            ) from exc
        sessions.append(session)

    if sessions != sorted(set(sessions)):
        raise HithinkAdapterError(
            "A-share trading calendar is not unique and ascending"
        )
    return tuple(sessions)


def latest_completed_a_share_session(
    sessions: Sequence[date],
    *,
    observed_at: datetime,
) -> date:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkAdapterError("observed_at must be timezone-aware")

    local = observed_at.astimezone(SHANGHAI_TZ)
    completed = tuple(
        session
        for session in sessions
        if session < local.date()
        or (session == local.date() and local.time() >= A_SHARE_CLOSE)
    )
    if not completed:
        raise HithinkAdapterError(
            "trading calendar contains no completed A-share session"
        )
    return max(completed)


def normalize_hithink_latest_completed_price(
    envelope: Mapping[str, Any],
    *,
    thscode: str,
    sessions: Sequence[date],
    observed_at: datetime,
) -> HithinkCompletedSessionPrice:
    """Normalize one raw daily close without fabricating request-time market freshness."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkAdapterError("observed_at must be timezone-aware")
    normalized_thscode = _normalize_thscode(thscode)
    normalized_sessions = tuple(sessions)
    if not normalized_sessions or normalized_sessions != tuple(
        sorted(set(normalized_sessions))
    ):
        raise HithinkAdapterError(
            "trading calendar is not unique and ascending"
        )

    expected_latest = latest_completed_a_share_session(
        normalized_sessions,
        observed_at=observed_at,
    )
    bars, response_session = _normalize_raw_history_bars(
        envelope,
        thscode=normalized_thscode,
        sessions=normalized_sessions,
        observed_local_date=observed_at.astimezone(SHANGHAI_TZ).date(),
    )
    if response_session > expected_latest:
        raise HithinkAdapterError(
            "raw A-share history extends beyond the latest completed session"
        )

    return HithinkCompletedSessionPrice(
        thscode=normalized_thscode,
        close=bars[response_session],
        as_of=datetime.combine(
            response_session,
            A_SHARE_CLOSE,
            tzinfo=SHANGHAI_TZ,
        ),
        expected_latest_session=expected_latest,
    )


def observed_market_from_hithink_response(
    envelope: Mapping[str, Any],
    *,
    thscode: str,
    sessions: Sequence[date],
    observed_at: datetime,
) -> ObservedMarket:
    """Map the exact latest completed raw A-share close into the kernel market contract."""

    price = normalize_hithink_latest_completed_price(
        envelope,
        thscode=thscode,
        sessions=sessions,
        observed_at=observed_at,
    )
    if price.as_of.date() != price.expected_latest_session:
        raise HithinkAdapterError(
            "Odds ObservedMarket is not the latest completed A-share session"
        )

    return ObservedMarket(
        market_price=price.close,
        market_timestamp=price.as_of,
        market_utc_offset_minutes=480,
        market_data_source=(
            f"{HITHINK_MARKET_SOURCE} | {price.thscode} | "
            f"session={price.expected_latest_session.isoformat()}"
        ),
        price_convention=HITHINK_PRICE_CONVENTION,
        currency="CNY",
    )


def fetch_hithink_observed_market(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> ObservedMarket:
    """Fetch only the calendar and raw daily history needed for one Odds price input."""

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkAdapterError("observed_at must be timezone-aware")
    normalized_thscode = _normalize_thscode(thscode)
    if not api_key:
        raise HithinkAdapterError(
            "HiThink credentials are required for ObservedMarket"
        )

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
            "thscode": normalized_thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
            "adjust": "none",
        },
    )
    return observed_market_from_hithink_response(
        envelope,
        thscode=normalized_thscode,
        sessions=calendar,
        observed_at=observed_at,
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
        raise HithinkAdapterError(
            f"HiThink HTTP request failed with status {exc.code}"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HithinkAdapterError(
            "HiThink request or response decoding failed"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HithinkAdapterError("HiThink response is not a JSON object")
    return payload


def _normalize_thscode(thscode: str) -> str:
    normalized = thscode.strip().upper()
    if not _A_SHARE_TICKER.fullmatch(normalized):
        raise HithinkAdapterError(
            "ObservedMarket requires one qualified A-share thscode"
        )
    return normalized


def _normalize_raw_history_bars(
    envelope: Mapping[str, Any],
    *,
    thscode: str,
    sessions: Sequence[date],
    observed_local_date: date,
) -> tuple[dict[date, Decimal], date]:
    data = require_hithink_data(
        envelope,
        endpoint="/api/a-share/prices/historical",
    )
    if data.get("thscode") != thscode:
        raise HithinkAdapterError(
            "A-share history thscode disagrees with the request"
        )
    if data.get("interval") != "1d":
        raise HithinkAdapterError("A-share history is not daily")
    if data.get("adjust") != "none":
        raise HithinkAdapterError(
            "A-share history adjustment disagrees with the raw-close request"
        )

    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise HithinkAdapterError("A-share history response is empty")

    session_set = set(sessions)
    bars: dict[date, Decimal] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise HithinkAdapterError(
                "A-share history contains a malformed row"
            )
        required = ("date_ms", "close_price", "volume", "turnover")
        if any(item.get(field) is None for field in required):
            raise HithinkAdapterError(
                "A-share history row is missing required fields"
            )
        try:
            session = datetime.fromtimestamp(
                int(item["date_ms"]) / 1000,
                tz=SHANGHAI_TZ,
            ).date()
            close = Decimal(str(item["close_price"]))
            volume = Decimal(str(item["volume"]))
            turnover = Decimal(str(item["turnover"]))
        except (InvalidOperation, TypeError, ValueError, OverflowError) as exc:
            raise HithinkAdapterError(
                "A-share history row has invalid values"
            ) from exc

        if session in bars:
            raise HithinkAdapterError(
                "A-share history contains duplicate dates"
            )
        if session > observed_local_date:
            raise HithinkAdapterError(
                "A-share history contains a future-dated bar"
            )
        if session not in session_set:
            raise HithinkAdapterError(
                "A-share history contains an off-calendar bar"
            )
        if (
            not close.is_finite()
            or not volume.is_finite()
            or not turnover.is_finite()
            or close <= 0
            or volume < 0
            or turnover < 0
        ):
            raise HithinkAdapterError(
                "A-share history row has invalid market values"
            )
        bars[session] = close

    try:
        response_session = datetime.fromtimestamp(
            int(data["timestamp"]) / 1000,
            tz=SHANGHAI_TZ,
        ).date()
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise HithinkAdapterError(
            "A-share history has an invalid timestamp"
        ) from exc
    if response_session != max(bars):
        raise HithinkAdapterError(
            "A-share history timestamp disagrees with its latest bar"
        )
    return bars, response_session
