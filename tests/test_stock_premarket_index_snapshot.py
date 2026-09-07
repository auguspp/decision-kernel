"""Premarket carry is stock-only, receipt-bound, and expires before auction."""
from datetime import datetime, time

import pytest

from decision_kernel.adapters.hithink_index import (
    HithinkIndexAdapterError,
    normalize_hithink_index_snapshot,
    qualify_hithink_index_snapshot,
)
from decision_kernel.runtime import stock_radar_reading as stock
from test_hithink_index_snapshot_data_ready_time import (
    COMPLETED_SESSIONS,
    FRIDAY,
    MONDAY,
    _history,
    _snapshot_envelope,
)
from test_sector_radar_audit import prohibit_network
from test_stock_reading_calendar import inputs

TZ = stock.SHANGHAI_TZ
CALENDAR = (*COMPLETED_SESSIONS, MONDAY)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def _at(hour, minute, second=0, microsecond=0):
    return datetime(2026, 9, 7, hour, minute, second, microsecond, tzinfo=TZ)


def _ms(value):
    return int(value.timestamp() * 1000)


def _snapshot(ready_at):
    return normalize_hithink_index_snapshot(
        _snapshot_envelope(ready_at_ms=_ms(ready_at)),
        requested_thscodes=("000300.SH", "881102.TI"),
    )


def test_shared_index_rule_stays_strict_while_stock_reader_has_explicit_premarket_carry():
    ready = _at(8, 34, 26)
    received = _at(8, 34, 26, 800222)
    observed = _at(8, 34, 27)
    raw = _snapshot(ready)
    history = _history(sessions=CALENDAR, observed_at=observed)

    with pytest.raises(HithinkIndexAdapterError, match="later trading session"):
        qualify_hithink_index_snapshot(
            raw, benchmark_history=history,
            trading_sessions=CALENDAR, observed_at=observed)

    qualified, expires = stock._qualify_stock_index_snapshot(
        raw, history, CALENDAR, observed_at=observed, received_at=received)

    assert qualified.market_session == FRIDAY
    assert qualified.provider_timestamp_ms == _ms(ready)
    assert expires == datetime.combine(MONDAY, time(9, 15), tzinfo=TZ)


def test_premarket_carry_never_lets_provider_ready_time_wait_into_validity():
    raw = _snapshot(_at(8, 34, 27))
    observed = _at(8, 34, 28)
    history = _history(sessions=CALENDAR, observed_at=observed)

    with pytest.raises(ValueError, match="follows actual receipt"):
        stock._qualify_stock_index_snapshot(
            raw, history, CALENDAR, observed_at=observed,
            received_at=_at(8, 34, 26, 800222))


def test_premarket_carry_is_strictly_before_0915_not_before_0930():
    raw = _snapshot(_at(9, 14, 59))
    observed = _at(9, 15)
    history = _history(sessions=CALENDAR, observed_at=observed)

    with pytest.raises(ValueError, match="09:15 opening auction"):
        stock._qualify_stock_index_snapshot(
            raw, history, CALENDAR, observed_at=observed,
            received_at=observed)


def test_0834_stock_reading_reaches_own_history_after_receipt_bound_index_check():
    observed = _at(8, 34, 30)
    state, plan, base, calls = inputs(observed)
    ready = _at(8, 34, 26)

    def response(path, params):
        value = base(path, params)
        if path == stock.indices.HITHINK_INDEX_SNAPSHOT_PATH:
            value['data']['timestamp'] = _ms(ready)
        return value

    report = stock.observe_stock_reading(
        plan, state, request_json=response, observed_at=observed)

    assert report['projection']['market_session'] == FRIDAY.isoformat()
    assert report['projection']['surfaced_stocks']
    assert any(path == stock.STOCK_HISTORY for path, _ in calls)
    assert report['projection']['events_created'] == 0
    assert report['projection']['research_authority'] == 'NONE'
    assert report['projection']['investment_authority'] == 'NONE'


def test_reading_that_crosses_0915_stops_before_stock_history():
    start = _at(9, 14, 50)
    state, plan, base, calls = inputs(start)
    current = start

    def response(path, params):
        nonlocal current
        value = base(path, params)
        if path == stock.indices.HITHINK_INDEX_SNAPSHOT_PATH:
            value['data']['timestamp'] = _ms(_at(9, 14, 54))
            current = _at(9, 14, 55)
        elif path == stock.indices.HITHINK_INDEX_HISTORY_PATH:
            current = _at(9, 14, 56)
        elif path == stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            current = _at(9, 15)
        return value

    with pytest.raises(ValueError, match="09:15 opening auction"):
        stock.observe_stock_reading(
            plan, state, request_json=response, observed_at=start,
            cutoff_clock=lambda: current)

    assert any(path == stock.indices.HITHINK_INDEX_SNAPSHOT_PATH for path, _ in calls)
    assert not any(path == stock.STOCK_HISTORY for path, _ in calls)
