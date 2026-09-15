from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime import hithink_index_http
from decision_kernel.runtime.hithink_http import HITHINK_CALENDAR_PATH, HithinkRuntimeError


SHANGHAI = ZoneInfo("Asia/Shanghai")
SESSIONS = (
    date(2026, 9, 1),
    date(2026, 9, 2),
    date(2026, 9, 3),
    date(2026, 9, 4),
)
OBSERVED_AFTER_CLOSE = datetime(2026, 9, 4, 16, tzinfo=SHANGHAI)


def _date_ms(value: date, *, hour: int = 0) -> int:
    return int(
        datetime.combine(value, time(hour), tzinfo=SHANGHAI).timestamp() * 1000
    )


def _calendar_envelope(sessions=SESSIONS) -> dict:
    return {
        "code": 0,
        "data": {
            "item": [
                {"date": session.strftime("%Y%m%d")}
                for session in sessions
            ]
        },
    }


def _catalog_envelope() -> dict:
    return {
        "code": 0,
        "data": {
            "timestamp": _date_ms(SESSIONS[-1], hour=18),
            "item": [
                {"thscode": "881101.TI", "name": "种植业与林业"},
                {"thscode": "881102.TI", "name": "养殖业"},
                {"thscode": "884006.TI", "name": "水产养殖"},
            ],
        },
    }


def _snapshot_row(thscode: str, last: str, previous: str) -> dict:
    last_value = Decimal(last)
    previous_value = Decimal(previous)
    return {
        "thscode": thscode,
        "ticker": thscode[:6],
        "last_price": str(last_value),
        "prev_price": str(previous_value),
        "price_change": str(last_value - previous_value),
        "price_change_ratio_pct": str(
            (last_value - previous_value) / previous_value * Decimal(100)
        ),
        "open_price": str(previous_value),
        "high_price": str(max(last_value, previous_value) + Decimal("1")),
        "low_price": str(min(last_value, previous_value) - Decimal("1")),
        "volume": "100",
        "turnover": "1000",
    }


def _snapshot_envelope() -> dict:
    rows = [
        _snapshot_row("000300.SH", "4548.05", "4530"),
        _snapshot_row("881102.TI", "3043.893", "3000"),
    ]
    return {
        "code": 0,
        "data": {
            "timestamp": _date_ms(SESSIONS[-1], hour=18),
            "total": len(rows),
            "item": rows,
        },
    }


def _history_envelope(
    *,
    thscode: str = "000300.SH",
    sessions=SESSIONS,
    closes=("4500", "4520", "4530", "4548.05"),
) -> dict:
    return {
        "code": 0,
        "data": {
            "thscode": thscode,
            "interval": "1d",
            "adjust": None,
            "timestamp": _date_ms(sessions[-1]),
            "item": [
                {
                    "date_ms": _date_ms(session),
                    "close_price": close,
                    "volume": str(100 + index),
                    "turnover": str(1000 + index * 10),
                }
                for index, (session, close) in enumerate(
                    zip(sessions, closes, strict=True)
                )
            ],
        },
    }


def test_runtime_fetches_exact_industry_catalog_contract() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        return _catalog_envelope()

    catalog = hithink_index_http.fetch_hithink_industry_catalog(
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert calls == [
        (
            hithink_index_http.HITHINK_INDEX_CATALOG_PATH,
            {"tag": "industry"},
        )
    ]
    assert [item.thscode for item in catalog.broad_industries] == [
        "881101.TI",
        "881102.TI",
    ]
    assert [item.thscode for item in catalog.granular_industries] == [
        "884006.TI"
    ]


def test_runtime_fetches_one_explicit_snapshot_batch_without_qualifying_it() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        return _snapshot_envelope()

    snapshot = hithink_index_http.fetch_hithink_index_snapshot_batch(
        thscodes=("000300.SH", "881102.TI"),
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert calls == [
        (
            hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH,
            {"thscodes": "000300.SH,881102.TI"},
        )
    ]
    assert snapshot.requested_thscodes == ("000300.SH", "881102.TI")
    assert snapshot.points[1].last_price == Decimal("3043.893")


def test_runtime_index_history_uses_completed_session_window_without_adjust() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == HITHINK_CALENDAR_PATH:
            return _calendar_envelope()
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope()
        raise AssertionError(path)

    history = hithink_index_http.fetch_hithink_completed_index_history(
        thscode="000300.SH",
        observed_at=OBSERVED_AFTER_CLOSE,
        api_key="fixture-secret",
        request_json=request_json,
        lookback_calendar_days=120,
    )

    assert [path for path, _ in calls] == [
        HITHINK_CALENDAR_PATH,
        hithink_index_http.HITHINK_INDEX_HISTORY_PATH,
    ]
    history_params = calls[1][1]
    assert history_params["thscode"] == "000300.SH"
    assert history_params["interval"] == "1d"
    assert "adjust" not in history_params
    exclusive_end = datetime.combine(
        SESSIONS[-1] + timedelta(days=1),
        time(),
        tzinfo=SHANGHAI,
    )
    expected_end = exclusive_end - timedelta(milliseconds=1)
    assert int(history_params["end"]) == int(expected_end.timestamp() * 1000)
    assert int(history_params["end"]) - int(history_params["start"]) == int(
        timedelta(days=120).total_seconds() * 1000
    ) - 1
    assert history.response_session == history.expected_latest_session == SESSIONS[-1]


def test_runtime_index_history_fails_visibly_when_stale() -> None:
    def request_json(path: str, params):
        if path == HITHINK_CALENDAR_PATH:
            return _calendar_envelope()
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope(
                sessions=SESSIONS[:-1],
                closes=("4500", "4520", "4530"),
            )
        raise AssertionError(path)

    with pytest.raises(HithinkRuntimeError, match="latest completed"):
        hithink_index_http.fetch_hithink_completed_index_history(
            thscode="000300.SH",
            observed_at=OBSERVED_AFTER_CLOSE,
            api_key="fixture-secret",
            request_json=request_json,
        )


def test_runtime_history_request_ends_after_previous_session_before_close() -> None:
    before_close = datetime(2026, 9, 4, 14, 59, tzinfo=SHANGHAI)
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == HITHINK_CALENDAR_PATH:
            return _calendar_envelope()
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope(
                sessions=SESSIONS[:-1],
                closes=("4500", "4520", "4530"),
            )
        raise AssertionError(path)

    history = hithink_index_http.fetch_hithink_completed_index_history(
        thscode="000300.SH",
        observed_at=before_close,
        api_key="fixture-secret",
        request_json=request_json,
    )

    exclusive_end = datetime.combine(
        SESSIONS[-2] + timedelta(days=1),
        time(),
        tzinfo=SHANGHAI,
    )
    expected_end = exclusive_end - timedelta(milliseconds=1)
    assert int(calls[1][1]["end"]) == int(expected_end.timestamp() * 1000)
    assert history.response_session == SESSIONS[-2]


def test_runtime_qualified_snapshot_uses_snapshot_calendar_and_history_only() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH:
            return _snapshot_envelope()
        if path == HITHINK_CALENDAR_PATH:
            return _calendar_envelope()
        if path == hithink_index_http.HITHINK_INDEX_HISTORY_PATH:
            return _history_envelope()
        raise AssertionError(path)

    qualified = hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
        thscodes=("000300.SH", "881102.TI"),
        benchmark_thscode="000300.SH",
        observed_at=OBSERVED_AFTER_CLOSE,
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert [path for path, _ in calls] == [
        hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH,
        HITHINK_CALENDAR_PATH,
        hithink_index_http.HITHINK_INDEX_HISTORY_PATH,
    ]
    assert qualified.market_session == SESSIONS[-1]
    assert qualified.benchmark_thscode == "000300.SH"
    assert [point.thscode for point in qualified.points] == [
        "000300.SH",
        "881102.TI",
    ]


def test_runtime_rejects_missing_credentials_naive_time_and_missing_benchmark() -> None:
    with pytest.raises(HithinkRuntimeError, match="credentials"):
        hithink_index_http.fetch_hithink_industry_catalog(api_key=None)

    with pytest.raises(HithinkRuntimeError, match="timezone-aware"):
        hithink_index_http.fetch_hithink_completed_index_history(
            thscode="000300.SH",
            observed_at=datetime(2026, 9, 4, 16),
            api_key="fixture-secret",
            request_json=lambda path, params: {},
        )

    with pytest.raises(HithinkRuntimeError, match="include its benchmark"):
        hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
            thscodes=("881102.TI",),
            benchmark_thscode="000300.SH",
            observed_at=OBSERVED_AFTER_CLOSE,
            api_key="fixture-secret",
            request_json=lambda path, params: {},
        )


def test_runtime_contract_contains_no_fallback_or_attention_authority() -> None:
    source = (
        hithink_index_http.__file__
        and open(hithink_index_http.__file__, encoding="utf-8").read()
    ).lower()

    assert "fallback" not in source
    assert "recommendation" not in source
    assert "attention_eligible" not in source
    assert "investment_authority" not in source
