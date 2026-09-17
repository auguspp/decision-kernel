from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import stock_radar_reading as stock


def sessions_61() -> tuple[date, ...]:
    days = []
    cursor = date(2026, 6, 25)
    while len(days) < 61:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def ms(day: date) -> int:
    return int(datetime.combine(day, time(), own.TZ).timestamp() * 1000)


def inputs(*, missing_index: int | None = None, volume_delta: int = 0):
    sessions = sessions_61()
    bars = []
    by_day = {}
    for i, day in enumerate(sessions):
        close = Decimal('10') + Decimal(i) / Decimal('100')
        row = {
            'date_ms': ms(day),
            'open_price': str(close), 'high_price': str(close),
            'low_price': str(close), 'close_price': str(close),
            'volume': str(100_000_000 + i),
            'turnover': str(1_000_000_000 + i),
        }
        by_day[day] = row
        if i != missing_index:
            bars.append(row)
    last = by_day[sessions[-1]]
    previous = by_day[sessions[-2]]
    history = {'code': 0, 'data': {'timestamp': ms(sessions[-1]), 'item': bars}}
    quote = {'code': 0, 'data': {'timestamp': None, 'item': [{
        'thscode': '002199.SZ', 'ticker': '002199',
        'last_price': last['close_price'], 'open_price': last['open_price'],
        'high_price': last['high_price'], 'low_price': last['low_price'],
        'prev_price': previous['close_price'],
        'volume': str(Decimal(last['volume']) + volume_delta),
        'turnover': last['turnover'],
    }]}}
    actions = {'code': 0, 'data': {'thscode': '002199.SZ', 'ticker': '002199', 'item': []}}
    observed = datetime.combine(sessions[-1], time(18, 30), own.TZ)
    return sessions, history, quote, actions, observed


def stock_path(*, missing_index: int | None = None, volume_delta: int = 0):
    sessions, history, quote, actions, observed = inputs(
        missing_index=missing_index, volume_delta=volume_delta)
    return stock._stock_path(
        SimpleNamespace(sessions=sessions), '002199.SZ', history, at=observed,
        quote=quote, actions=actions, quote_received_at=observed - timedelta(minutes=1),
    )


def test_noncritical_old_market_session_gap_keeps_selection_windows_but_nulls_60d_context():
    path = stock_path(missing_index=10, volume_delta=-2)
    assert path['history_session_count'] == 60
    assert path['returns']['5'] is not None
    assert path['returns']['20'] is not None
    assert path['twenty_day_return_five_sessions_ago'] is not None
    assert path['returns']['60'] is None
    assert '60' in path['unavailable_price_metrics']
    checks = path['input_checks']
    assert checks['history_market_session_gaps'] == [sessions_61()[10].isoformat()]
    assert checks['history_gap_meaning'] == 'ABSENCE_REASON_UNKNOWN_NOT_INFERRED_AS_SUSPENSION_OR_ZERO_TRADING'
    assert checks['history_window_checks']['20']['usable_for_raw_comparison'] is True
    assert checks['history_window_checks']['60']['usable_for_raw_comparison'] is False
    assert checks['volume_reconciliation']['status'] == 'WITHIN_EXPLICIT_TOLERANCE'
    assert checks['volume_reconciliation']['absolute_difference_shares'] == '2'


def test_missing_bar_inside_required_recent_26_market_sessions_still_fails_closed():
    sessions, history, quote, actions, observed = inputs(missing_index=50)
    with pytest.raises(own.StockReadingInputError) as caught:
        stock._stock_path(
            SimpleNamespace(sessions=sessions), '002199.SZ', history, at=observed,
            quote=quote, actions=actions, quote_received_at=observed - timedelta(minutes=1),
        )
    assert caught.value.category == 'DATA_INSUFFICIENT'
    assert caught.value.reason_code == 'REQUIRED_SELECTION_WINDOW_STOCK_SESSIONS_MISSING'


def test_volume_reconciliation_is_whole_share_bounded_and_preserves_raw_history_value():
    path = stock_path(volume_delta=2)
    check = path['input_checks']['volume_reconciliation']
    assert check['historical_shares'] == str(Decimal(100_000_060))
    assert check['snapshot_shares'] == str(Decimal(100_000_062))
    assert path['latest_volume'] == Decimal(100_000_060)

    sessions, history, quote, actions, observed = inputs(volume_delta=3)
    with pytest.raises(own.StockReadingInputError, match='CURRENT_QUOTE_HISTORY_MISMATCH'):
        stock._stock_path(
            SimpleNamespace(sessions=sessions), '002199.SZ', history, at=observed,
            quote=quote, actions=actions, quote_received_at=observed - timedelta(minutes=1),
        )


def test_complete_61_bar_window_keeps_60d_context_available():
    path = stock_path()
    assert path['history_session_count'] == 61
    assert path['returns']['60'] is not None
    assert path['unavailable_price_metrics'] == []
