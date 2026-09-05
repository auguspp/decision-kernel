from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HITHINK_INDEX_SNAPSHOT_TIMESTAMP_SEMANTICS,
    HithinkIndexAdapterError,
    normalize_hithink_completed_index_history,
    normalize_hithink_index_snapshot,
    qualify_hithink_index_snapshot,
)
from decision_kernel.runtime import hithink_index_http
from decision_kernel.runtime.hithink_http import HITHINK_CALENDAR_PATH


SHANGHAI = ZoneInfo("Asia/Shanghai")
THURSDAY = date(2026, 9, 3)
FRIDAY = date(2026, 9, 4)
SATURDAY = date(2026, 9, 5)
MONDAY = date(2026, 9, 7)
COMPLETED_SESSIONS = (THURSDAY, FRIDAY)


def _ms(day: date, hour: int, minute: int = 0) -> int:
    return int(
        datetime.combine(day, time(hour, minute), tzinfo=SHANGHAI).timestamp()
        * 1000
    )


def _snapshot_row(
    thscode: str,
    *,
    last: str,
    previous: str,
) -> dict[str, str]:
    last_value = Decimal(last)
    previous_value = Decimal(previous)
    change = last_value - previous_value
    return {
        "thscode": thscode,
        "ticker": "1B0300" if thscode == "000300.SH" else thscode[:6],
        "last_price": str(last_value),
        "prev_price": str(previous_value),
        "price_change": str(change),
        "price_change_ratio_pct": str(
            change / previous_value * Decimal(100)
        ),
        "open_price": str(previous_value),
        "high_price": str(max(last_value, previous_value) + Decimal("1")),
        "low_price": str(min(last_value, previous_value) - Decimal("1")),
        "volume": "100",
        "turnover": "1000",
    }


def _snapshot_envelope(*, ready_at_ms: int) -> dict:
    rows = [
        _snapshot_row("000300.SH", last="4548.05", previous="4530"),
        _snapshot_row("881102.TI", last="3043.893", previous="3000"),
    ]
    return {
        "code": 0,
        "data": {
            "timestamp": ready_at_ms,
            "total": len(rows),
            "item": rows,
        },
    }


def _history_envelope() -> dict:
    return {
        "code": 0,
        "data": {
            "thscode": "000300.SH",
            "interval": "1d",
            "adjust": None,
            "timestamp": _ms(FRIDAY, 0),
            "item": [
                {
                    "date_ms": _ms(THURSDAY, 0),
                    "close_price": "4530",
                    "volume": "100",
                    "turnover": "1000",
                },
                {
                    "date_ms": _ms(FRIDAY, 0),
                    "close_price": "4548.05",
                    "volume": "101",
                    "turnover": "1010",
                },
            ],
        },
    }


def _calendar_envelope(sessions) -> dict:
    return {
        "code": 0,
        "data": {
            "item": [
                {"date": session.strftime("%Y%m%d")}
                for session in sessions
            ]
        },
    }


def _history(*, sessions, observed_at):
    return normalize_hithink_completed_index_history(
        _history_envelope(),
        thscode="000300.SH",
        sessions=sessions,
        observed_at=observed_at,
    )


def test_weekend_data_ready_time_is_not_misread_as_market_session() -> None:
    observed_at = datetime(2026, 9, 5, 10, 1, tzinfo=SHANGHAI)
    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(ready_at_ms=_ms(SATURDAY, 10)),
        requested_thscodes=("000300.SH", "881102.TI"),
    )
    history = _history(
        sessions=COMPLETED_SESSIONS,
        observed_at=observed_at,
    )

    qualified = qualify_hithink_index_snapshot(
        snapshot,
        benchmark_history=history,
        trading_sessions=COMPLETED_SESSIONS,
        observed_at=observed_at,
    )

    assert qualified.market_session == FRIDAY
    assert qualified.provider_timestamp_ms == _ms(SATURDAY, 10)
    assert qualified.provider_timestamp_semantics == (
        HITHINK_INDEX_SNAPSHOT_TIMESTAMP_SEMANTICS
    )
    assert qualified.qualification_method == HITHINK_INDEX_SNAPSHOT_QUALIFICATION


def test_data_ready_time_before_completed_close_still_fails_closed() -> None:
    observed_at = datetime(2026, 9, 4, 16, 0, tzinfo=SHANGHAI)
    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(ready_at_ms=_ms(FRIDAY, 14, 59)),
        requested_thscodes=("000300.SH", "881102.TI"),
    )
    history = _history(
        sessions=COMPLETED_SESSIONS,
        observed_at=observed_at,
    )

    with pytest.raises(HithinkIndexAdapterError, match="precedes the completed"):
        qualify_hithink_index_snapshot(
            snapshot,
            benchmark_history=history,
            trading_sessions=COMPLETED_SESSIONS,
            observed_at=observed_at,
        )


def test_data_ready_time_on_unfinished_later_trading_session_fails_closed() -> None:
    observed_at = datetime(2026, 9, 7, 10, 0, tzinfo=SHANGHAI)
    calendar = (*COMPLETED_SESSIONS, MONDAY)
    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(ready_at_ms=_ms(MONDAY, 10)),
        requested_thscodes=("000300.SH", "881102.TI"),
    )
    history = _history(sessions=calendar, observed_at=observed_at)

    with pytest.raises(HithinkIndexAdapterError, match="later trading session"):
        qualify_hithink_index_snapshot(
            snapshot,
            benchmark_history=history,
            trading_sessions=calendar,
            observed_at=observed_at,
        )


def test_runtime_qualifies_weekend_snapshot_with_one_calendar_request() -> None:
    observed_at = datetime(2026, 9, 5, 10, 1, tzinfo=SHANGHAI)
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH:
            return _snapshot_envelope(ready_at_ms=_ms(SATURDAY, 10))
        if path == HITHINK_CALENDAR_PATH:
            return _calendar_envelope(COMPLETED_SESSIONS)
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope()
        raise AssertionError(path)

    qualified = hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
        thscodes=("000300.SH", "881102.TI"),
        benchmark_thscode="000300.SH",
        observed_at=observed_at,
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert [path for path, _ in calls] == [
        hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH,
        HITHINK_CALENDAR_PATH,
        hithink_index_http.HITHINK_INDEX_HISTORY_PATH,
    ]
    assert qualified.market_session == FRIDAY


def test_runtime_can_reuse_an_exact_supplied_calendar() -> None:
    observed_at = datetime(2026, 9, 5, 10, 1, tzinfo=SHANGHAI)
    calls: list[str] = []

    def request_json(path: str, params):
        calls.append(path)
        if path == hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH:
            return _snapshot_envelope(ready_at_ms=_ms(SATURDAY, 10))
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope()
        raise AssertionError(path)

    qualified = hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
        thscodes=("000300.SH", "881102.TI"),
        benchmark_thscode="000300.SH",
        observed_at=observed_at,
        api_key="fixture-secret",
        request_json=request_json,
        trading_sessions=COMPLETED_SESSIONS,
    )

    assert calls == [
        hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH,
        hithink_index_http.HITHINK_INDEX_HISTORY_PATH,
    ]
    assert qualified.market_session == FRIDAY
