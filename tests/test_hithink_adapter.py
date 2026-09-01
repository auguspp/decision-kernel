from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink import (
    HITHINK_MARKET_SOURCE,
    HITHINK_PRICE_CONVENTION,
    HithinkAdapterError,
    fetch_hithink_observed_market,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    observed_market_from_hithink_response,
    require_hithink_data,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _sessions(count: int = 5) -> tuple[date, ...]:
    result: list[date] = []
    current = date(2026, 8, 24)
    while len(result) < count:
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return tuple(result)


def _date_ms(value: date) -> int:
    return int(datetime.combine(value, time(), tzinfo=SHANGHAI).timestamp() * 1000)


def _calendar_envelope(sessions: tuple[date, ...]) -> dict:
    return {
        "code": 0,
        "request_id": "calendar-request",
        "data": {
            "timestamp": _date_ms(sessions[-1]),
            "item": [
                {"date_ms": _date_ms(session), "date": session.strftime("%Y%m%d")}
                for session in sessions
            ],
        },
    }


def _history_envelope(
    sessions: tuple[date, ...],
    *,
    thscode: str = "002384.SZ",
) -> dict:
    return {
        "code": 0,
        "request_id": "history-request",
        "data": {
            "adjust": "none",
            "interval": "1d",
            "thscode": thscode,
            "timestamp": _date_ms(sessions[-1]),
            "item": [
                {
                    "date_ms": _date_ms(session),
                    "close_price": str(Decimal("10") + Decimal(index)),
                    "volume": str(Decimal("100") + Decimal(index)),
                    "turnover": str(Decimal("1000") + Decimal(index * 10)),
                }
                for index, session in enumerate(sessions)
            ],
        },
    }


def test_completed_session_gate_never_uses_an_unfinished_live_day() -> None:
    sessions = _sessions()
    live_session = sessions[-1]
    before_close = datetime.combine(live_session, time(14, 59), tzinfo=SHANGHAI)

    assert latest_completed_a_share_session(
        sessions,
        observed_at=before_close,
    ) == sessions[-2]
    assert latest_completed_a_share_session(
        sessions,
        observed_at=before_close.replace(hour=15, minute=0),
    ) == live_session


def test_calendar_requires_unique_ascending_sessions() -> None:
    sessions = _sessions(3)
    envelope = _calendar_envelope(sessions)
    assert normalize_hithink_calendar(envelope) == sessions

    envelope["data"]["item"].reverse()
    with pytest.raises(HithinkAdapterError, match="unique and ascending"):
        normalize_hithink_calendar(envelope)


def test_provider_business_error_is_visible_even_when_http_would_be_successful() -> None:
    with pytest.raises(HithinkAdapterError, match="business code 2003"):
        require_hithink_data(
            {"code": 2003, "request_id": "denied", "data": None},
            endpoint="/api/a-share/prices/historical",
        )


def test_latest_completed_raw_close_maps_to_kernel_observed_market() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    market = observed_market_from_hithink_response(
        _history_envelope(sessions),
        thscode="002384.SZ",
        sessions=sessions,
        observed_at=observed_at,
    )

    assert market.market_price == Decimal("14")
    assert market.market_timestamp == datetime.combine(
        sessions[-1], time(15), tzinfo=SHANGHAI
    )
    assert market.market_utc_offset_minutes == 480
    assert market.currency == "CNY"
    assert market.price_convention == HITHINK_PRICE_CONVENTION
    assert HITHINK_MARKET_SOURCE in market.market_data_source
    assert "002384.SZ" in market.market_data_source
    assert f"session={sessions[-1].isoformat()}" in market.market_data_source


def test_stale_completed_history_is_not_fed_to_odds_as_current_market() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    with pytest.raises(HithinkAdapterError, match="not the latest completed"):
        observed_market_from_hithink_response(
            _history_envelope(sessions[:-1]),
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )


def test_before_close_response_cannot_leak_the_unfinished_session() -> None:
    sessions = _sessions()
    before_close = datetime.combine(sessions[-1], time(14, 59), tzinfo=SHANGHAI)

    with pytest.raises(HithinkAdapterError, match="beyond the latest completed session"):
        observed_market_from_hithink_response(
            _history_envelope(sessions),
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=before_close,
        )


def test_raw_history_metadata_and_values_fail_closed() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    adjusted = _history_envelope(sessions)
    adjusted["data"]["adjust"] = "forward"
    with pytest.raises(HithinkAdapterError, match="raw-close request"):
        observed_market_from_hithink_response(
            adjusted,
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )

    wrong_security = _history_envelope(sessions)
    wrong_security["data"]["thscode"] = "600519.SH"
    with pytest.raises(HithinkAdapterError, match="thscode disagrees"):
        observed_market_from_hithink_response(
            wrong_security,
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )

    non_finite = _history_envelope(sessions)
    non_finite["data"]["item"][-1]["close_price"] = "NaN"
    with pytest.raises(HithinkAdapterError, match="invalid market values"):
        observed_market_from_hithink_response(
            non_finite,
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )


def test_fetch_adapter_uses_only_calendar_and_raw_daily_history() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params: dict[str, str]):
        calls.append((path, dict(params)))
        if path == "/api/a-share/calendar/trading-days":
            return _calendar_envelope(sessions)
        if path == "/api/a-share/prices/historical":
            return _history_envelope(sessions)
        raise AssertionError(f"unexpected path: {path}")

    market = fetch_hithink_observed_market(
        thscode="002384.sz",
        observed_at=observed_at,
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert market.market_price == Decimal("14")
    assert [path for path, _ in calls] == [
        "/api/a-share/calendar/trading-days",
        "/api/a-share/prices/historical",
    ]
    history_params = calls[1][1]
    assert history_params["thscode"] == "002384.SZ"
    assert history_params["interval"] == "1d"
    assert history_params["adjust"] == "none"
    assert int(history_params["start"]) < int(history_params["end"])


def test_fetch_adapter_requires_explicit_credentials_and_a_share_identity() -> None:
    observed_at = datetime(2026, 9, 1, 16, tzinfo=SHANGHAI)

    with pytest.raises(HithinkAdapterError, match="credentials"):
        fetch_hithink_observed_market(
            thscode="002384.SZ",
            observed_at=observed_at,
            api_key=None,
            request_json=lambda path, params: {},
        )

    with pytest.raises(HithinkAdapterError, match="A-share thscode"):
        fetch_hithink_observed_market(
            thscode="AAPL",
            observed_at=observed_at,
            api_key="fixture-secret",
            request_json=lambda path, params: {},
        )
