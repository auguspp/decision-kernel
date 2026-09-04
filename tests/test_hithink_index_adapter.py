from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkIndexAdapterError,
    normalize_hithink_completed_index_history,
    normalize_hithink_industry_catalog,
    normalize_hithink_index_snapshot,
    qualify_hithink_index_snapshot,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
SESSIONS = (
    date(2026, 9, 1),
    date(2026, 9, 2),
    date(2026, 9, 3),
    date(2026, 9, 4),
)
OBSERVED_AFTER_CLOSE = datetime(2026, 9, 4, 16, 0, tzinfo=SHANGHAI)


def _date_ms(value: date, *, hour: int = 0) -> int:
    return int(
        datetime.combine(value, time(hour), tzinfo=SHANGHAI).timestamp() * 1000
    )


def _calendar_sessions() -> tuple[date, ...]:
    return SESSIONS


def _catalog_envelope(items: list[dict] | None = None) -> dict:
    return {
        "code": 0,
        "data": {
            "timestamp": _date_ms(SESSIONS[-1], hour=18),
            "item": items
            or [
                {"thscode": "884006.TI", "name": "水产养殖"},
                {"thscode": "881102.TI", "name": "养殖业"},
                {"thscode": "882001.TI", "name": "意外层级"},
                {"thscode": "881101.TI", "name": "种植业与林业"},
            ],
        },
    }


def _snapshot_row(
    thscode: str,
    *,
    last: str,
    previous: str,
    turnover: str = "1000",
) -> dict:
    last_value = Decimal(last)
    previous_value = Decimal(previous)
    change = last_value - previous_value
    ratio = change / previous_value * Decimal(100)
    return {
        "thscode": thscode,
        "ticker": thscode[:6],
        "last_price": str(last_value),
        "prev_price": str(previous_value),
        "price_change": str(change),
        "price_change_ratio_pct": str(ratio),
        "open_price": str(min(last_value, previous_value)),
        "high_price": str(max(last_value, previous_value) + Decimal("1")),
        "low_price": str(min(last_value, previous_value) - Decimal("1")),
        "volume": "100",
        "turnover": turnover,
    }


def _snapshot_envelope(
    rows: list[dict],
    *,
    session: date = SESSIONS[-1],
    total: int | None = None,
) -> dict:
    return {
        "code": 0,
        "data": {
            "timestamp": _date_ms(session, hour=18),
            "total": len(rows) if total is None else total,
            "item": rows,
        },
    }


def _history_envelope(
    thscode: str,
    *,
    sessions: tuple[date, ...] = SESSIONS,
    closes: tuple[str, ...] = ("4500", "4520", "4530", "4548.05"),
    adjust=None,
) -> dict:
    return {
        "code": 0,
        "data": {
            "thscode": thscode,
            "interval": "1d",
            "adjust": adjust,
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


def test_industry_catalog_is_canonical_hashed_and_partitioned() -> None:
    catalog = normalize_hithink_industry_catalog(_catalog_envelope())

    assert [identity.thscode for identity in catalog.identities] == [
        "881101.TI",
        "881102.TI",
        "882001.TI",
        "884006.TI",
    ]
    assert [identity.thscode for identity in catalog.broad_industries] == [
        "881101.TI",
        "881102.TI",
    ]
    assert [identity.thscode for identity in catalog.granular_industries] == [
        "884006.TI"
    ]
    assert [identity.thscode for identity in catalog.unexpected_industries] == [
        "882001.TI"
    ]

    canonical = json.dumps(
        [
            {"name": identity.name, "thscode": identity.thscode}
            for identity in catalog.identities
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert catalog.catalog_hash == hashlib.sha256(canonical).hexdigest()

    reordered = _catalog_envelope(
        list(reversed(_catalog_envelope()["data"]["item"]))
    )
    assert normalize_hithink_industry_catalog(reordered).catalog_hash == catalog.catalog_hash


def test_industry_catalog_rejects_duplicates_and_malformed_identity() -> None:
    with pytest.raises(HithinkIndexAdapterError, match="duplicate identity"):
        normalize_hithink_industry_catalog(
            _catalog_envelope(
                [
                    {"thscode": "881101.TI", "name": "甲"},
                    {"thscode": "881101.TI", "name": "乙"},
                ]
            )
        )

    with pytest.raises(HithinkIndexAdapterError, match="invalid identity"):
        normalize_hithink_industry_catalog(
            _catalog_envelope(
                [{"thscode": "881101.SH", "name": "错误后缀"}]
            )
        )


def test_snapshot_requires_exact_identity_set_and_preserves_request_order() -> None:
    rows = [
        _snapshot_row("881102.TI", last="3043.893", previous="3000"),
        _snapshot_row("000300.SH", last="4548.05", previous="4530"),
    ]
    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(rows),
        requested_thscodes=("000300.sh", "881102.ti"),
    )

    assert snapshot.requested_thscodes == ("000300.SH", "881102.TI")
    assert [point.thscode for point in snapshot.points] == [
        "000300.SH",
        "881102.TI",
    ]
    assert snapshot.points[0].last_price == Decimal("4548.05")
    assert snapshot.points[1].turnover == Decimal("1000")


def test_snapshot_preserves_standard_index_provider_ticker_aliases() -> None:
    shanghai_alias = _snapshot_row(
        "000300.SH",
        last="4548.05",
        previous="4530",
    )
    shanghai_alias["ticker"] = "1b0300"
    shenzhen_index = _snapshot_row(
        "399006.SZ",
        last="3286.55",
        previous="3312",
    )
    industry = _snapshot_row(
        "881101.TI",
        last="1847.32",
        previous="1800",
    )

    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope([industry, shanghai_alias, shenzhen_index]),
        requested_thscodes=("000300.SH", "399006.SZ", "881101.TI"),
    )

    assert [point.ticker for point in snapshot.points] == [
        "1B0300",
        "399006",
        "881101",
    ]


def test_snapshot_fails_closed_on_missing_extra_duplicate_and_bad_total() -> None:
    benchmark = _snapshot_row("000300.SH", last="4548.05", previous="4530")
    industry = _snapshot_row("881102.TI", last="3043.893", previous="3000")

    with pytest.raises(HithinkIndexAdapterError, match="missing=.*881102"):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([benchmark]),
            requested_thscodes=("000300.SH", "881102.TI"),
        )

    with pytest.raises(HithinkIndexAdapterError, match="extra=.*881102"):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([benchmark, industry]),
            requested_thscodes=("000300.SH",),
        )

    with pytest.raises(HithinkIndexAdapterError, match="duplicate identity"):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([benchmark, benchmark]),
            requested_thscodes=("000300.SH", "881102.TI"),
        )

    with pytest.raises(HithinkIndexAdapterError, match="total disagrees"):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([benchmark], total=2),
            requested_thscodes=("000300.SH",),
        )


def test_snapshot_rejects_invalid_market_values_and_ticker_mismatch() -> None:
    bad_range = _snapshot_row("000300.SH", last="4548.05", previous="4530")
    bad_range["high_price"] = "4540"
    with pytest.raises(HithinkIndexAdapterError, match="outside daily range"):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([bad_range]),
            requested_thscodes=("000300.SH",),
        )

    bad_industry_ticker = _snapshot_row(
        "881101.TI",
        last="1847.32",
        previous="1800",
    )
    bad_industry_ticker["ticker"] = "999999"
    with pytest.raises(
        HithinkIndexAdapterError,
        match="industry snapshot ticker disagrees",
    ):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([bad_industry_ticker]),
            requested_thscodes=("881101.TI",),
        )

    malformed_standard_ticker = _snapshot_row(
        "000300.SH",
        last="4548.05",
        previous="4530",
    )
    malformed_standard_ticker["ticker"] = "bad alias"
    with pytest.raises(
        HithinkIndexAdapterError,
        match="ticker metadata is invalid",
    ):
        normalize_hithink_index_snapshot(
            _snapshot_envelope([malformed_standard_ticker]),
            requested_thscodes=("000300.SH",),
        )


def test_index_history_preserves_completed_points_and_exposes_staleness() -> None:
    fresh = normalize_hithink_completed_index_history(
        _history_envelope("000300.SH"),
        thscode="000300.sh",
        sessions=_calendar_sessions(),
        observed_at=OBSERVED_AFTER_CLOSE,
    )
    assert fresh.thscode == "000300.SH"
    assert fresh.response_session == fresh.expected_latest_session == SESSIONS[-1]
    assert fresh.points[-1].close == Decimal("4548.05")
    assert fresh.points[-1].turnover == Decimal("1030")
    assert fresh.points[-1].as_of.time() == time(15)

    stale = normalize_hithink_completed_index_history(
        _history_envelope(
            "000300.SH",
            sessions=SESSIONS[:-1],
            closes=("4500", "4520", "4530"),
        ),
        thscode="000300.SH",
        sessions=_calendar_sessions(),
        observed_at=OBSERVED_AFTER_CLOSE,
    )
    assert stale.response_session == SESSIONS[-2]
    assert stale.expected_latest_session == SESSIONS[-1]


def test_index_history_rejects_unfinished_adjusted_and_off_calendar_rows() -> None:
    before_close = datetime(2026, 9, 4, 14, 59, tzinfo=SHANGHAI)
    with pytest.raises(HithinkIndexAdapterError, match="beyond the latest completed"):
        normalize_hithink_completed_index_history(
            _history_envelope("000300.SH"),
            thscode="000300.SH",
            sessions=_calendar_sessions(),
            observed_at=before_close,
        )

    with pytest.raises(HithinkIndexAdapterError, match="adjustment semantics"):
        normalize_hithink_completed_index_history(
            _history_envelope("000300.SH", adjust="none"),
            thscode="000300.SH",
            sessions=_calendar_sessions(),
            observed_at=OBSERVED_AFTER_CLOSE,
        )

    off_calendar_session = date(2026, 9, 5)
    envelope = _history_envelope("000300.SH")
    envelope["data"]["item"][0]["date_ms"] = _date_ms(off_calendar_session)
    with pytest.raises(HithinkIndexAdapterError, match="off-calendar"):
        normalize_hithink_completed_index_history(
            envelope,
            thscode="000300.SH",
            sessions=_calendar_sessions(),
            observed_at=datetime(2026, 9, 6, 16, tzinfo=SHANGHAI),
        )


def test_snapshot_qualification_requires_provider_date_and_two_benchmark_closes() -> None:
    snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(
            [
                _snapshot_row(
                    "000300.SH",
                    last="4548.05",
                    previous="4530",
                ),
                _snapshot_row(
                    "881102.TI",
                    last="3043.893",
                    previous="3000",
                ),
            ]
        ),
        requested_thscodes=("000300.SH", "881102.TI"),
    )
    history = normalize_hithink_completed_index_history(
        _history_envelope("000300.SH"),
        thscode="000300.SH",
        sessions=_calendar_sessions(),
        observed_at=OBSERVED_AFTER_CLOSE,
    )

    qualified = qualify_hithink_index_snapshot(
        snapshot,
        benchmark_history=history,
    )
    assert qualified.market_session == SESSIONS[-1]
    assert qualified.benchmark_thscode == "000300.SH"
    assert qualified.qualification_method == HITHINK_INDEX_SNAPSHOT_QUALIFICATION
    assert [point.thscode for point in qualified.points] == [
        "000300.SH",
        "881102.TI",
    ]

    wrong_date = normalize_hithink_index_snapshot(
        _snapshot_envelope(
            [
                _snapshot_row(
                    "000300.SH",
                    last="4548.05",
                    previous="4530",
                )
            ],
            session=SESSIONS[-2],
        ),
        requested_thscodes=("000300.SH",),
    )
    with pytest.raises(HithinkIndexAdapterError, match="provider date disagrees"):
        qualify_hithink_index_snapshot(
            wrong_date,
            benchmark_history=history,
        )


def test_snapshot_qualification_rejects_price_mismatch_stale_or_missing_benchmark() -> None:
    history = normalize_hithink_completed_index_history(
        _history_envelope("000300.SH"),
        thscode="000300.SH",
        sessions=_calendar_sessions(),
        observed_at=OBSERVED_AFTER_CLOSE,
    )
    wrong_price = normalize_hithink_index_snapshot(
        _snapshot_envelope(
            [_snapshot_row("000300.SH", last="4549", previous="4530")]
        ),
        requested_thscodes=("000300.SH",),
    )
    with pytest.raises(HithinkIndexAdapterError, match="last price disagrees"):
        qualify_hithink_index_snapshot(
            wrong_price,
            benchmark_history=history,
        )

    missing_benchmark = normalize_hithink_index_snapshot(
        _snapshot_envelope(
            [_snapshot_row("881102.TI", last="3043.893", previous="3000")]
        ),
        requested_thscodes=("881102.TI",),
    )
    with pytest.raises(HithinkIndexAdapterError, match="does not contain"):
        qualify_hithink_index_snapshot(
            missing_benchmark,
            benchmark_history=history,
        )

    stale_history = normalize_hithink_completed_index_history(
        _history_envelope(
            "000300.SH",
            sessions=SESSIONS[:-1],
            closes=("4500", "4520", "4530"),
        ),
        thscode="000300.SH",
        sessions=_calendar_sessions(),
        observed_at=OBSERVED_AFTER_CLOSE,
    )
    current_snapshot = normalize_hithink_index_snapshot(
        _snapshot_envelope(
            [_snapshot_row("000300.SH", last="4548.05", previous="4530")]
        ),
        requested_thscodes=("000300.SH",),
    )
    with pytest.raises(HithinkIndexAdapterError, match="history is stale"):
        qualify_hithink_index_snapshot(
            current_snapshot,
            benchmark_history=stale_history,
        )
