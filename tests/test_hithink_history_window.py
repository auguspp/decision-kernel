from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink import (
    HithinkAdapterError,
    normalize_hithink_completed_price_history,
)
from decision_kernel.runtime import hithink_http
from decision_kernel.runtime.hithink_http import HithinkRuntimeError


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _sessions() -> tuple[date, ...]:
    return (
        date(2026, 8, 24),
        date(2026, 8, 25),
        date(2026, 8, 26),
        date(2026, 8, 27),
        date(2026, 8, 28),
    )


def _date_ms(value: date) -> int:
    return int(datetime.combine(value, time(), tzinfo=SHANGHAI).timestamp() * 1000)


def _calendar_envelope(sessions: tuple[date, ...]) -> dict:
    return {
        "code": 0,
        "data": {
            "item": [{"date": session.strftime("%Y%m%d")} for session in sessions]
        },
    }


def _history_envelope(sessions: tuple[date, ...]) -> dict:
    return {
        "code": 0,
        "data": {
            "adjust": "none",
            "interval": "1d",
            "thscode": "600000.SH",
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


def test_adapter_preserves_entire_qualified_completed_close_window() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    history = normalize_hithink_completed_price_history(
        _history_envelope(sessions),
        thscode="600000.sh",
        sessions=sessions,
        observed_at=observed_at,
    )

    assert history.thscode == "600000.SH"
    assert history.response_session == sessions[-1]
    assert history.expected_latest_session == sessions[-1]
    assert tuple(point.close for point in history.points) == (
        Decimal("10"),
        Decimal("11"),
        Decimal("12"),
        Decimal("13"),
        Decimal("14"),
    )
    assert tuple(point.as_of.date() for point in history.points) == sessions
    assert all(point.as_of.time() == time(15) for point in history.points)
    assert all(point.as_of.tzinfo == SHANGHAI for point in history.points)


def test_adapter_history_exposes_staleness_instead_of_fabricating_freshness() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    history = normalize_hithink_completed_price_history(
        _history_envelope(sessions[:-1]),
        thscode="600000.SH",
        sessions=sessions,
        observed_at=observed_at,
    )

    assert history.response_session == sessions[-2]
    assert history.expected_latest_session == sessions[-1]
    assert history.points[-1].close == Decimal("13")
    assert history.points[-1].as_of.date() == sessions[-2]


def test_adapter_history_rejects_unfinished_live_session() -> None:
    sessions = _sessions()
    before_close = datetime.combine(sessions[-1], time(14, 59), tzinfo=SHANGHAI)

    with pytest.raises(
        HithinkAdapterError,
        match="extends beyond the latest completed session",
    ):
        normalize_hithink_completed_price_history(
            _history_envelope(sessions),
            thscode="600000.SH",
            sessions=sessions,
            observed_at=before_close,
        )


def test_runtime_exposes_same_fresh_window_without_adding_radar_semantics() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == "/api/a-share/calendar/trading-days":
            return _calendar_envelope(sessions)
        if path == "/api/a-share/prices/historical":
            return _history_envelope(sessions)
        raise AssertionError(path)

    history = hithink_http.fetch_hithink_completed_price_history(
        thscode="600000.SH",
        observed_at=observed_at,
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert history.points[-1].close == Decimal("14")
    assert history.response_session == history.expected_latest_session == sessions[-1]
    assert [path for path, _ in calls] == [
        "/api/a-share/calendar/trading-days",
        "/api/a-share/prices/historical",
    ]
    assert calls[1][1]["adjust"] == "none"
    assert int(calls[1][1]["end"]) - int(calls[1][1]["start"]) == int(
        timedelta(days=45).total_seconds() * 1000
    )


def test_runtime_history_fails_visibly_when_provider_window_is_stale() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    def request_json(path: str, params):
        if path == "/api/a-share/calendar/trading-days":
            return _calendar_envelope(sessions)
        if path == "/api/a-share/prices/historical":
            return _history_envelope(sessions[:-1])
        raise AssertionError(path)

    with pytest.raises(HithinkRuntimeError, match="latest completed"):
        hithink_http.fetch_hithink_completed_price_history(
            thscode="600000.SH",
            observed_at=observed_at,
            api_key="fixture-secret",
            request_json=request_json,
        )
