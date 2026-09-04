from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkIndexSnapshotPoint,
    HithinkQualifiedIndexSnapshotBatch,
    normalize_hithink_industry_catalog,
)
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_state import (
    STATE_UPDATE_ALREADY_CURRENT,
    STATE_UPDATE_APPENDED,
    SectorRadarStateSourceLineage,
    append_qualified_sector_snapshot,
    calculate_sector_radar_state_snapshot_pair,
    create_sector_radar_market_state,
    parse_sector_radar_market_state,
    serialize_sector_radar_market_state,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
START = date(2026, 1, 1)
SESSIONS = tuple(START + timedelta(days=index) for index in range(130))
CREATED = datetime(2026, 5, 10, 16, 0, tzinfo=SHANGHAI)


def catalog(items=None):
    return normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": 1780000000000,
                "item": items
                or [
                    {"thscode": "881101.TI", "name": "种植业与林业"},
                    {"thscode": "881102.TI", "name": "养殖业"},
                    {"thscode": "884001.TI", "name": "种子生产"},
                    {"thscode": "884275.TI", "name": "生猪养殖"},
                ],
            },
        }
    )


def series(code: str, name: str, step: str) -> SectorPriceSeries:
    increment = Decimal(step)
    return SectorPriceSeries(
        thscode=code,
        name=name,
        points=tuple(
            SectorPricePoint(
                session=session,
                close=Decimal("100") + increment * index,
                turnover=Decimal("1000") + Decimal(index),
            )
            for index, session in enumerate(SESSIONS)
        ),
    )


def state():
    return create_sector_radar_market_state(
        catalog=catalog(),
        benchmark=series("000300.SH", "沪深300", "0.2"),
        broad_series=(
            series("881102.TI", "养殖业", "0.4"),
            series("881101.TI", "种植业与林业", "0.3"),
        ),
        granular_series=(
            series("884275.TI", "生猪养殖", "0.6"),
            series("884001.TI", "种子生产", "0.5"),
        ),
        created_at=CREATED,
        source="qualified synthetic history",
        source_lineage=(
            SectorRadarStateSourceLineage(
                role="TEST_HISTORY",
                workflow_run_id=1,
                artifact_id=2,
                artifact_digest="sha256:" + "a" * 64,
                result_hash="b" * 64,
            ),
        ),
    )


def snapshot_for(current_state, *, session: date, price_offset: str = "1"):
    offset = Decimal(price_offset)
    points = []
    for item in current_state.series:
        previous = item.closes[-1]
        last = previous + offset
        points.append(
            HithinkIndexSnapshotPoint(
                thscode=item.thscode,
                ticker=("1B0300" if item.thscode == "000300.SH" else item.thscode[:6]),
                last_price=last,
                prev_price=previous,
                price_change=offset,
                price_change_ratio_pct=offset / previous * Decimal("100"),
                open_price=previous,
                high_price=last,
                low_price=previous,
                volume=Decimal("100"),
                turnover=item.turnovers[-1] + Decimal("10"),
            )
        )
    return HithinkQualifiedIndexSnapshotBatch(
        market_session=session,
        benchmark_thscode="000300.SH",
        provider_timestamp_ms=1780000001000,
        qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
        points=tuple(reversed(points)),
    )


def test_state_creation_trims_to_pair_safe_window_and_round_trips() -> None:
    current = state()

    assert len(current.sessions) == 127
    assert current.sessions[0] == SESSIONS[-127]
    assert current.sessions[-1] == SESSIONS[-1]
    assert len(current.series) == 5
    assert [item.thscode for item in current.series] == [
        "000300.SH",
        "881101.TI",
        "881102.TI",
        "884001.TI",
        "884275.TI",
    ]
    assert len(current.state_hash) == 64

    serialized = serialize_sector_radar_market_state(current)
    parsed = parse_sector_radar_market_state(serialized)
    assert parsed == current


def test_state_hash_detects_any_serialized_market_change() -> None:
    payload = json.loads(serialize_sector_radar_market_state(state()))
    payload["series"][0]["closes"][-1] = "999999"

    with pytest.raises(ValueError, match="state hash mismatch"):
        parse_sector_radar_market_state(json.dumps(payload, ensure_ascii=False))


def test_new_completed_session_appends_once_and_same_session_is_idempotent() -> None:
    current = state()
    next_session = current.sessions[-1] + timedelta(days=1)
    qualified = snapshot_for(current, session=next_session)

    update = append_qualified_sector_snapshot(
        state=current,
        catalog=catalog(),
        snapshot=qualified,
        observed_at=CREATED + timedelta(days=1),
    )

    assert update.status == STATE_UPDATE_APPENDED
    assert update.appended_session == next_session
    assert update.previous_state_hash == current.state_hash
    assert len(update.state.sessions) == 127
    assert update.state.sessions[-1] == next_session
    assert update.state.sessions[0] == current.sessions[1]
    assert update.state.state_hash != current.state_hash

    same_session = snapshot_for(
        update.state,
        session=next_session,
        price_offset="0",
    )
    same_session = HithinkQualifiedIndexSnapshotBatch(
        market_session=same_session.market_session,
        benchmark_thscode=same_session.benchmark_thscode,
        provider_timestamp_ms=same_session.provider_timestamp_ms,
        qualification_method=same_session.qualification_method,
        points=tuple(
            HithinkIndexSnapshotPoint(
                thscode=point.thscode,
                ticker=point.ticker,
                last_price=point.prev_price,
                prev_price=point.prev_price,
                price_change=Decimal(0),
                price_change_ratio_pct=Decimal(0),
                open_price=point.prev_price,
                high_price=point.prev_price,
                low_price=point.prev_price,
                volume=point.volume,
                turnover=next(
                    item.turnovers[-1]
                    for item in update.state.series
                    if item.thscode == point.thscode
                ),
            )
            for point in same_session.points
        ),
    )
    repeated = append_qualified_sector_snapshot(
        state=update.state,
        catalog=catalog(),
        snapshot=same_session,
        observed_at=CREATED + timedelta(days=1, minutes=5),
    )
    assert repeated.status == STATE_UPDATE_ALREADY_CURRENT
    assert repeated.appended_session is None
    assert repeated.state == update.state


def test_state_continuity_and_same_session_revision_fail_closed() -> None:
    current = state()
    next_session = current.sessions[-1] + timedelta(days=1)
    qualified = snapshot_for(current, session=next_session)
    bad_first = qualified.points[0]
    broken = HithinkQualifiedIndexSnapshotBatch(
        market_session=qualified.market_session,
        benchmark_thscode=qualified.benchmark_thscode,
        provider_timestamp_ms=qualified.provider_timestamp_ms,
        qualification_method=qualified.qualification_method,
        points=(
            HithinkIndexSnapshotPoint(
                thscode=bad_first.thscode,
                ticker=bad_first.ticker,
                last_price=bad_first.last_price,
                prev_price=bad_first.prev_price + Decimal("1"),
                price_change=bad_first.price_change,
                price_change_ratio_pct=bad_first.price_change_ratio_pct,
                open_price=bad_first.open_price,
                high_price=bad_first.high_price,
                low_price=bad_first.low_price,
                volume=bad_first.volume,
                turnover=bad_first.turnover,
            ),
            *qualified.points[1:],
        ),
    )
    with pytest.raises(ValueError, match="continuity failed"):
        append_qualified_sector_snapshot(
            state=current,
            catalog=catalog(),
            snapshot=broken,
            observed_at=CREATED + timedelta(days=1),
        )

    same_session = snapshot_for(
        current,
        session=current.sessions[-1],
    )
    with pytest.raises(ValueError, match="same-session Sector Radar close changed"):
        append_qualified_sector_snapshot(
            state=current,
            catalog=catalog(),
            snapshot=same_session,
            observed_at=CREATED + timedelta(minutes=5),
        )


def test_catalog_drift_prevents_state_update() -> None:
    current = state()
    changed = catalog(
        [
            {"thscode": "881101.TI", "name": "种植业与林业"},
            {"thscode": "881102.TI", "name": "养殖业（变更）"},
            {"thscode": "884001.TI", "name": "种子生产"},
            {"thscode": "884275.TI", "name": "生猪养殖"},
        ]
    )
    with pytest.raises(ValueError, match="catalog hash disagrees"):
        append_qualified_sector_snapshot(
            state=current,
            catalog=changed,
            snapshot=snapshot_for(
                current,
                session=current.sessions[-1] + timedelta(days=1),
            ),
            observed_at=CREATED + timedelta(days=1),
        )


def test_state_calculates_exact_previous_current_universe_pairs() -> None:
    pair = calculate_sector_radar_state_snapshot_pair(state())

    assert pair.previous_session == SESSIONS[-2]
    assert pair.current_session == SESSIONS[-1]
    assert len(pair.broad_previous.observations) == 2
    assert len(pair.broad_current.observations) == 2
    assert len(pair.granular_previous.observations) == 2
    assert len(pair.granular_current.observations) == 2
    assert pair.broad_current.benchmark_thscode == "000300.SH"
    assert pair.human_attention_authority == "NONE"
    assert pair.investment_authority == "NONE"

    serialized = repr(asdict(pair)).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "portfolio" not in serialized
