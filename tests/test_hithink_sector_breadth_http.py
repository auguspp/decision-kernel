from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.runtime.hithink_sector_breadth_http import (
    HITHINK_A_SHARE_SNAPSHOT_PATH,
    HITHINK_SECTOR_CONSTITUENTS_PATH,
    fetch_hithink_all_market_snapshot,
    fetch_hithink_sector_membership,
    normalize_hithink_sector_membership,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
SESSION = date(2026, 9, 4)


def timestamp_ms(value: date = SESSION, *, hour: int = 18) -> int:
    return int(
        datetime(
            value.year,
            value.month,
            value.day,
            hour,
            tzinfo=SHANGHAI,
        ).timestamp()
        * 1000
    )


def membership_envelope(items=None, *, timestamp: int | None = None):
    return {
        "code": 0,
        "data": {
            "timestamp": timestamp or timestamp_ms(),
            "item": items
            or [
                {"thscode": "600002.SH", "ticker": "600002", "name": "乙"},
                {"thscode": "000001.SZ", "ticker": "000001", "name": "甲"},
            ],
        },
    }


def stock_row(
    code: str,
    *,
    last: str | None = "11",
    previous: str | None = "10",
    turnover: str | None = "1000",
):
    return {
        "thscode": code,
        "ticker": code[:6],
        "last_price": last,
        "prev_price": previous,
        "price_change": None,
        "price_change_ratio_pct": None,
        "open_price": None,
        "high_price": None,
        "low_price": None,
        "volume": None,
        "turnover": turnover,
    }


def snapshot_envelope(items, *, total: int, session: date = SESSION):
    return {
        "code": 0,
        "data": {
            "timestamp": timestamp_ms(session),
            "total": total,
            "item": items,
        },
    }


def test_membership_fetch_uses_exact_endpoint_and_canonicalizes_identity() -> None:
    calls = []

    def request(path, params):
        calls.append((path, params))
        return membership_envelope()

    result = fetch_hithink_sector_membership(
        sector_thscode="881102.ti",
        sector_name=" 养殖业 ",
        api_key="secret",
        request_json=request,
    )

    assert calls == [
        (HITHINK_SECTOR_CONSTITUENTS_PATH, {"thscode": "881102.TI"})
    ]
    assert result.sector_thscode == "881102.TI"
    assert result.sector_name == "养殖业"
    assert [item.thscode for item in result.members] == [
        "000001.SZ",
        "600002.SH",
    ]
    assert result.captured_at == datetime(
        2026,
        9,
        4,
        18,
        tzinfo=SHANGHAI,
    )
    assert len(result.constituent_set_hash) == 64


def test_membership_fails_closed_on_duplicate_or_invalid_rows() -> None:
    duplicate = membership_envelope(
        [
            {"thscode": "600001.SH", "ticker": "600001", "name": "甲"},
            {"thscode": "600001.SH", "ticker": "600001", "name": "甲"},
        ]
    )
    with pytest.raises(HithinkRuntimeError, match="duplicate"):
        normalize_hithink_sector_membership(
            duplicate,
            sector_thscode="881101.TI",
            sector_name="种植业与林业",
        )

    malformed = membership_envelope(
        [{"thscode": "600001.SH", "ticker": "999999", "name": "甲"}]
    )
    with pytest.raises(HithinkRuntimeError, match="ticker disagrees"):
        normalize_hithink_sector_membership(
            malformed,
            sector_thscode="881101.TI",
            sector_name="种植业与林业",
        )


def test_all_market_snapshot_paginates_exact_total_and_sorts_points() -> None:
    calls = []
    pages = {
        0: snapshot_envelope(
            [stock_row("600002.SH"), stock_row("000001.SZ")],
            total=3,
        ),
        2: snapshot_envelope([stock_row("430001.BJ")], total=3),
    }

    def request(path, params):
        calls.append((path, params))
        return pages[int(params["offset"])]

    result = fetch_hithink_all_market_snapshot(
        market_session=SESSION,
        api_key="secret",
        request_json=request,
        page_size=2,
    )

    assert calls == [
        (HITHINK_A_SHARE_SNAPSHOT_PATH, {"limit": "2", "offset": "0"}),
        (HITHINK_A_SHARE_SNAPSHOT_PATH, {"limit": "2", "offset": "2"}),
    ]
    assert result.page_count == 2
    assert result.declared_total == 3
    assert result.returned_unique_rows == 3
    assert result.priced_rows == 3
    assert result.unpriced_rows == 0
    assert [point.thscode for point in result.points] == [
        "000001.SZ",
        "430001.BJ",
        "600002.SH",
    ]
    assert result.points[0].last_price == Decimal("11")
    assert result.snapshot_semantics == (
        "CURRENT_COMPLETED_SESSION_ALL_A_SHARE_SNAPSHOT"
    )
    assert result.human_attention_authority == "NONE"
    assert result.investment_authority == "NONE"


def test_all_market_snapshot_preserves_missing_market_values_as_unpriced() -> None:
    def request(path, params):
        del path, params
        return snapshot_envelope(
            [
                stock_row("600001.SH"),
                stock_row(
                    "600002.SH",
                    last=None,
                    previous=None,
                    turnover=None,
                ),
            ],
            total=2,
        )

    result = fetch_hithink_all_market_snapshot(
        market_session=SESSION,
        api_key="secret",
        request_json=request,
        page_size=2,
    )

    assert result.priced_rows == 1
    assert result.unpriced_rows == 1
    unpriced = next(point for point in result.points if point.thscode == "600002.SH")
    assert unpriced.last_price is None
    assert unpriced.prev_price is None
    assert unpriced.turnover is None


def test_all_market_snapshot_fails_on_date_total_or_pagination_drift() -> None:
    with pytest.raises(HithinkRuntimeError, match="provider date disagrees"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: snapshot_envelope(
                [stock_row("600001.SH")],
                total=1,
                session=date(2026, 9, 3),
            ),
        )

    pages = {
        0: snapshot_envelope(
            [stock_row("600001.SH"), stock_row("600002.SH")],
            total=3,
        ),
        2: snapshot_envelope([stock_row("600003.SH")], total=4),
    }
    with pytest.raises(HithinkRuntimeError, match="total changed"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: pages[int(params["offset"])],
            page_size=2,
        )

    with pytest.raises(HithinkRuntimeError, match="short page"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: snapshot_envelope(
                [stock_row("600001.SH")],
                total=3,
            ),
            page_size=2,
        )


def test_all_market_snapshot_rejects_duplicates_invalid_values_and_missing_key() -> None:
    duplicate = snapshot_envelope(
        [stock_row("600001.SH"), stock_row("600001.SH")],
        total=2,
    )
    with pytest.raises(HithinkRuntimeError, match="duplicate identity"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: duplicate,
            page_size=2,
        )

    invalid = snapshot_envelope(
        [stock_row("600001.SH", last="NaN")],
        total=1,
    )
    with pytest.raises(HithinkRuntimeError, match="must be finite"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key="secret",
            request_json=lambda path, params: invalid,
        )

    with pytest.raises(HithinkRuntimeError, match="credentials"):
        fetch_hithink_all_market_snapshot(
            market_session=SESSION,
            api_key=None,
            request_json=lambda path, params: snapshot_envelope([], total=0),
        )


def test_serialized_snapshot_contract_has_no_recommendation_or_action_authority() -> None:
    result = fetch_hithink_all_market_snapshot(
        market_session=SESSION,
        api_key="secret",
        request_json=lambda path, params: snapshot_envelope(
            [stock_row("600001.SH")],
            total=1,
        ),
    )
    serialized = repr(asdict(result)).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "portfolio" not in serialized
