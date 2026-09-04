from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.runtime.hithink_sector_breadth_http import (
    fetch_hithink_all_market_snapshot,
)


SESSION = date(2026, 9, 4)
SHANGHAI = ZoneInfo("Asia/Shanghai")


# This regression must remain in the ordinary full suite after the one-time repair
# workflow removes itself.
def test_all_market_snapshot_rejects_non_a_share_identity_even_when_ticker_matches() -> None:
    timestamp_ms = int(
        datetime(2026, 9, 4, 18, tzinfo=SHANGHAI).timestamp() * 1000
    )
    envelope = {
        "code": 0,
        "data": {
            "timestamp": timestamp_ms,
            "total": 1,
            "item": [
                {
                    "thscode": "ABCDEF.XY",
                    "ticker": "ABCDEF",
                    "last_price": "10",
                    "prev_price": "9",
                    "turnover": "1000",
                }
            ],
        },
    }

    with pytest.raises(HithinkRuntimeError, match="invalid A-share identity"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: envelope,
        )
