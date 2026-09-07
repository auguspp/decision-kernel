from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.runtime.hithink_sector_breadth_http import (
    HITHINK_A_SHARE_SNAPSHOT_PATH,
    fetch_hithink_all_market_snapshot,
)


SESSION = date(2026, 9, 7)
SHANGHAI = ZoneInfo("Asia/Shanghai")


def timestamp_ms() -> int:
    return int(datetime(2026, 9, 7, 16, 30, tzinfo=SHANGHAI).timestamp() * 1000)


def live_unpriced_row(**overrides):
    row = {
        "thscode": "920201.BJ",
        "ticker": "920201",
        "last_price": None,
        "prev_price": 0,
        "price_change": None,
        "price_change_ratio_pct": None,
        "open_price": None,
        "high_price": None,
        "low_price": None,
        "volume": 0,
        "turnover": 0,
    }
    row.update(overrides)
    return row


def envelope(row):
    return {
        "code": 0,
        "data": {"timestamp": timestamp_ms(), "total": 1, "item": [row]},
    }


def fetch(row):
    calls = []

    def request(path, params):
        calls.append((path, params))
        return envelope(row)

    result = fetch_hithink_all_market_snapshot(
        market_session=SESSION,
        api_key="synthetic-secret",
        request_json=request,
    )
    assert calls == [
        (HITHINK_A_SHARE_SNAPSHOT_PATH, {"limit": "500", "offset": "0"})
    ]
    return result


def test_coherent_pretrading_zero_previous_is_retained_as_unpriced() -> None:
    result = fetch(live_unpriced_row())

    assert result.returned_unique_rows == 1
    assert result.priced_rows == 0
    assert result.unpriced_rows == 1
    point = result.points[0]
    assert point.thscode == "920201.BJ"
    assert point.last_price is None
    assert point.prev_price is None
    assert point.turnover == Decimal("0")


def test_zero_previous_with_present_last_price_still_fails_closed() -> None:
    with pytest.raises(HithinkRuntimeError, match="prev_price must be positive"):
        fetch(
            live_unpriced_row(
                last_price=16.77,
                volume=100,
                turnover=1677,
            )
        )


def test_zero_previous_with_trading_activity_still_fails_closed() -> None:
    with pytest.raises(HithinkRuntimeError, match="prev_price must be positive"):
        fetch(live_unpriced_row(volume=10, turnover=100))


def test_boolean_previous_is_not_misread_as_zero_sentinel() -> None:
    with pytest.raises(HithinkRuntimeError, match="prev_price must be numeric or null"):
        fetch(live_unpriced_row(prev_price=False))
