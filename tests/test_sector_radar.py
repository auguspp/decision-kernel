from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal

import pytest

from decision_kernel.runtime.sector_radar import (
    SECTOR_RADAR_FORMULA_VERSION,
    SectorPricePoint,
    SectorPriceSeries,
    calculate_sector_radar_snapshot,
)


START = date(2026, 1, 5)
SESSIONS = tuple(START + timedelta(days=index) for index in range(70))
AS_OF = SESSIONS[-1]


def _series(
    thscode: str,
    name: str,
    closes: list[Decimal],
    *,
    turnovers: list[Decimal] | None = None,
    sessions: tuple[date, ...] = SESSIONS,
) -> SectorPriceSeries:
    if turnovers is None:
        turnovers = [Decimal("100") for _ in closes]
    return SectorPriceSeries(
        thscode=thscode,
        name=name,
        points=tuple(
            SectorPricePoint(
                session=session,
                close=close,
                turnover=turnover,
            )
            for session, close, turnover in zip(
                sessions,
                closes,
                turnovers,
                strict=True,
            )
        ),
    )


def _constant(value: str = "100") -> list[Decimal]:
    return [Decimal(value) for _ in SESSIONS]


def _linear(step: str) -> list[Decimal]:
    increment = Decimal(step)
    return [Decimal("100") + increment * index for index in range(len(SESSIONS))]


def test_sector_radar_calculates_visible_horizons_ranks_persistence_and_turnover() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())
    strong_turnover = [Decimal("100") for _ in SESSIONS]
    strong_turnover[-5:] = [Decimal("200") for _ in range(5)]

    snapshot = calculate_sector_radar_snapshot(
        sectors=(
            _series(
                "881001.TI",
                "强势行业",
                _linear("2"),
                turnovers=strong_turnover,
            ),
            _series("881002.TI", "中性行业", _linear("1")),
            _series("881003.TI", "较弱行业", _linear("0.2")),
        ),
        benchmark=benchmark,
        as_of_session=AS_OF,
    )

    assert snapshot.formula_version == SECTOR_RADAR_FORMULA_VERSION
    assert snapshot.as_of_session == AS_OF
    assert snapshot.history_window_start == SESSIONS[0]
    assert snapshot.history_window_end == AS_OF
    assert snapshot.exclusions == ()
    assert snapshot.radar_semantics == "PRICE_PATH_DISCOVERY_OBSERVATION_ONLY"
    assert snapshot.human_attention_authority == "NONE"
    assert snapshot.investment_authority == "NONE"

    strong, neutral, weak = snapshot.observations
    assert [item.thscode for item in snapshot.observations] == [
        "881001.TI",
        "881002.TI",
        "881003.TI",
    ]

    assert strong.horizon_20.sector_return == Decimal("238") / Decimal("198") - 1
    assert strong.horizon_20.benchmark_return == 0
    assert strong.horizon_20.excess_return == strong.horizon_20.sector_return
    assert strong.horizon_20.cross_sectional_rank == Decimal("1")
    assert strong.horizon_20.cross_sectional_rating == 99
    assert neutral.horizon_20.cross_sectional_rank == Decimal("2")
    assert neutral.horizon_20.cross_sectional_rating == 50
    assert weak.horizon_20.cross_sectional_rank == Decimal("3")
    assert weak.horizon_20.cross_sectional_rating == 1

    assert strong.rank_change_5_sessions_20d == 0
    assert strong.positive_20d_excess_persistence_sessions == 50
    assert strong.positive_20d_excess_run_started == SESSIONS[20]
    assert strong.positive_20d_excess_persistence_left_censored is True
    assert strong.top_quartile_20d_persistence_sessions == 50
    assert strong.top_quartile_20d_run_started == SESSIONS[20]
    assert strong.top_quartile_20d_persistence_left_censored is True
    assert strong.turnover_pulse_5_vs_prior_20 == Decimal("2")


def test_sector_radar_uses_average_tie_ranks_and_bounded_ratings() -> None:
    snapshot = calculate_sector_radar_snapshot(
        sectors=(
            _series("881011.TI", "并列甲", _linear("1")),
            _series("881012.TI", "并列乙", _linear("1")),
            _series("881013.TI", "较弱", _linear("0.1")),
        ),
        benchmark=_series("000300.SH", "沪深300", _constant()),
        as_of_session=AS_OF,
    )

    first, second, third = snapshot.observations
    assert first.horizon_20.cross_sectional_rank == Decimal("1.5")
    assert second.horizon_20.cross_sectional_rank == Decimal("1.5")
    assert first.horizon_20.cross_sectional_rating == 75
    assert second.horizon_20.cross_sectional_rating == 75
    assert third.horizon_20.cross_sectional_rank == Decimal("3")
    assert third.horizon_20.cross_sectional_rating == 1


def test_sector_radar_exposes_rank_improvement_and_excess_acceleration() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())
    steady = _linear("1")
    weak = _linear("0.1")
    accelerating = [Decimal("100") for _ in SESSIONS]
    for index in range(62, len(accelerating)):
        accelerating[index] = Decimal("100") + Decimal("4") * Decimal(index - 61)

    snapshot = calculate_sector_radar_snapshot(
        sectors=(
            _series("881021.TI", "稳定领先", steady),
            _series("881022.TI", "新近加速", accelerating),
            _series("881023.TI", "弱势参照", weak),
        ),
        benchmark=benchmark,
        as_of_session=AS_OF,
    )

    by_code = {item.thscode: item for item in snapshot.observations}
    newly_accelerating = by_code["881022.TI"]

    assert newly_accelerating.horizon_20.cross_sectional_rank == Decimal("1")
    assert newly_accelerating.rank_change_5_sessions_20d == Decimal("1")
    assert newly_accelerating.excess_acceleration_5_sessions_20d > 0
    assert newly_accelerating.positive_20d_excess_persistence_sessions == 8
    assert newly_accelerating.positive_20d_excess_run_started == SESSIONS[62]
    assert newly_accelerating.positive_20d_excess_persistence_left_censored is False


def test_sector_radar_ignores_future_points_after_frozen_pit() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())
    sectors = (
        _series("881031.TI", "甲", _linear("1")),
        _series("881032.TI", "乙", _linear("0.5")),
    )
    baseline = calculate_sector_radar_snapshot(
        sectors=sectors,
        benchmark=benchmark,
        as_of_session=AS_OF,
    )

    future_session = AS_OF + timedelta(days=1)
    with_future = SectorPriceSeries(
        thscode=sectors[0].thscode,
        name=sectors[0].name,
        points=sectors[0].points
        + (
            SectorPricePoint(
                session=future_session,
                close=Decimal("1000000"),
                turnover=Decimal("999999999"),
            ),
        ),
    )
    replay = calculate_sector_radar_snapshot(
        sectors=(with_future, sectors[1]),
        benchmark=SectorPriceSeries(
            thscode=benchmark.thscode,
            name=benchmark.name,
            points=benchmark.points
            + (
                SectorPricePoint(
                    session=future_session,
                    close=Decimal("1"),
                    turnover=Decimal("1"),
                ),
            ),
        ),
        as_of_session=AS_OF,
    )

    assert replay == baseline


def test_sector_radar_excludes_incomplete_sector_without_hiding_reason() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())
    complete_a = _series("881041.TI", "完整甲", _linear("1"))
    complete_b = _series("881042.TI", "完整乙", _linear("0.5"))

    missing_index = 30
    missing_sessions = SESSIONS[:missing_index] + SESSIONS[missing_index + 1 :]
    incomplete_closes = _linear("0.8")
    incomplete_closes.pop(missing_index)
    incomplete = _series(
        "881043.TI",
        "缺失行业",
        incomplete_closes,
        sessions=missing_sessions,
    )

    snapshot = calculate_sector_radar_snapshot(
        sectors=(complete_a, incomplete, complete_b),
        benchmark=benchmark,
        as_of_session=AS_OF,
    )

    assert {item.thscode for item in snapshot.observations} == {
        "881041.TI",
        "881042.TI",
    }
    assert len(snapshot.exclusions) == 1
    assert snapshot.exclusions[0].thscode == "881043.TI"
    assert "missing required benchmark sessions" in snapshot.exclusions[0].reason
    assert SESSIONS[missing_index].isoformat() in snapshot.exclusions[0].reason


def test_sector_radar_fails_closed_when_cross_section_is_not_viable() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())

    with pytest.raises(
        ValueError,
        match="at least two fully aligned eligible sectors",
    ):
        calculate_sector_radar_snapshot(
            sectors=(_series("881051.TI", "唯一行业", _linear("1")),),
            benchmark=benchmark,
            as_of_session=AS_OF,
        )


def test_sector_radar_rejects_duplicate_identities_and_stale_benchmark() -> None:
    benchmark = _series("000300.SH", "沪深300", _constant())
    duplicate_a = _series("881061.TI", "甲", _linear("1"))
    duplicate_b = _series("881061.TI", "乙", _linear("0.5"))

    with pytest.raises(ValueError, match="duplicate requested sector identities"):
        calculate_sector_radar_snapshot(
            sectors=(duplicate_a, duplicate_b),
            benchmark=benchmark,
            as_of_session=AS_OF,
        )

    with pytest.raises(ValueError, match="benchmark does not reach"):
        calculate_sector_radar_snapshot(
            sectors=(
                _series("881062.TI", "甲", _linear("1")),
                _series("881063.TI", "乙", _linear("0.5")),
            ),
            benchmark=SectorPriceSeries(
                thscode=benchmark.thscode,
                name=benchmark.name,
                points=benchmark.points[:-1],
            ),
            as_of_session=AS_OF,
        )


def test_sector_radar_snapshot_has_no_recommendation_or_action_authority() -> None:
    snapshot = calculate_sector_radar_snapshot(
        sectors=(
            _series("881071.TI", "甲", _linear("1")),
            _series("881072.TI", "乙", _linear("0.5")),
        ),
        benchmark=_series("000300.SH", "沪深300", _constant()),
        as_of_session=AS_OF,
    )

    serialized = repr(asdict(snapshot)).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "action" not in serialized
    assert snapshot.human_attention_authority == "NONE"
    assert snapshot.investment_authority == "NONE"
