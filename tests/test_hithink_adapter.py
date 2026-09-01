from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

import decision_kernel.adapters.hithink as hithink
from decision_kernel.adapters.hithink import (
    HITHINK_MARKET_SOURCE,
    HITHINK_PRICE_CONVENTION,
    HithinkAdapterError,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    normalize_hithink_latest_completed_price,
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


def test_adapter_exposes_no_transport_or_credential_api() -> None:
    assert not hasattr(hithink, "fetch_hithink_observed_market")
    assert not hasattr(hithink, "HITHINK_BASE_URL")
    assert not hasattr(hithink, "HITHINK_API_KEY_ENV")


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
        thscode="002384.sz",
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
    assert market.market_data_source == f"{HITHINK_MARKET_SOURCE} | 002384.SZ"


def test_older_provider_history_preserves_its_actual_price_clock() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)
    older = sessions[:-1]

    qualified = normalize_hithink_latest_completed_price(
        _history_envelope(older),
        thscode="002384.SZ",
        sessions=sessions,
        observed_at=observed_at,
    )
    market = observed_market_from_hithink_response(
        _history_envelope(older),
        thscode="002384.SZ",
        sessions=sessions,
        observed_at=observed_at,
    )

    assert qualified.expected_latest_session == sessions[-1]
    assert qualified.as_of.date() == sessions[-2]
    assert market.market_timestamp.date() == sessions[-2]
    assert market.market_price == Decimal("13")


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
    with pytest.raises(HithinkAdapterError, match="raw-close contract"):
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


def test_raw_history_rejects_future_off_calendar_and_duplicate_rows() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    off_calendar = _history_envelope(sessions)
    weekend = sessions[-1] + timedelta(days=1)
    while weekend.weekday() < 5:
        weekend += timedelta(days=1)
    off_calendar["data"]["item"][-1]["date_ms"] = _date_ms(weekend)
    off_calendar["data"]["timestamp"] = _date_ms(weekend)
    with pytest.raises(HithinkAdapterError, match="future-dated|off-calendar"):
        observed_market_from_hithink_response(
            off_calendar,
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )

    duplicate = _history_envelope(sessions)
    duplicate["data"]["item"][-1]["date_ms"] = duplicate["data"]["item"][-2]["date_ms"]
    duplicate["data"]["timestamp"] = duplicate["data"]["item"][-2]["date_ms"]
    with pytest.raises(HithinkAdapterError, match="duplicate dates"):
        observed_market_from_hithink_response(
            duplicate,
            thscode="002384.SZ",
            sessions=sessions,
            observed_at=observed_at,
        )
