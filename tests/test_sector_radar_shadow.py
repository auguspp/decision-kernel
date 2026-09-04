from __future__ import annotations

from dataclasses import asdict, replace
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    calculate_current_sector_breadth,
    normalize_sector_membership,
)
from decision_kernel.runtime.sector_radar import (
    SectorHorizonObservation,
    SectorRadarObservation,
    SectorRadarSnapshot,
)
from decision_kernel.runtime.sector_radar_shadow import (
    ACCELERATING,
    BROAD_881,
    GRANULAR_884,
    PERSISTENT_TOP_DECILE,
    SectorRadarShadowCandidate,
    SectorRadarShadowStateEntries,
    build_current_parent_link,
    compose_sector_radar_shadow,
    select_sector_radar_state_entries,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
PREVIOUS = date(2026, 9, 3)
SESSION = date(2026, 9, 4)
CAPTURED = datetime(2026, 9, 4, 15, 30, tzinfo=SHANGHAI)
OBSERVED = datetime(2026, 9, 4, 16, 0, tzinfo=SHANGHAI)
FORMULA = "sector-rs-5-20-60-persistence126-v0"


def horizon(
    sessions: int,
    *,
    rank: str,
    rating: int,
    excess: str,
) -> SectorHorizonObservation:
    return SectorHorizonObservation(
        sessions=sessions,
        sector_return=Decimal(excess),
        benchmark_return=Decimal(0),
        excess_return=Decimal(excess),
        cross_sectional_rank=Decimal(rank),
        cross_sectional_rating=rating,
    )


def observation(
    code: str,
    name: str,
    session: date,
    *,
    rating_5: int = 50,
    rating_20: int = 50,
    rank_5: str = "50",
    rank_20: str = "50",
    excess_20: str = "0.01",
    rank_change: str = "0",
    acceleration: str = "0",
    positive_run: int = 0,
    turnover: str | None = "1",
) -> SectorRadarObservation:
    return SectorRadarObservation(
        thscode=code,
        name=name,
        as_of_session=session,
        history_session_count=126,
        horizon_5=horizon(5, rank=rank_5, rating=rating_5, excess="0.01"),
        horizon_20=horizon(
            20,
            rank=rank_20,
            rating=rating_20,
            excess=excess_20,
        ),
        horizon_60=horizon(60, rank="50", rating=50, excess="0.02"),
        rank_change_5_sessions_20d=Decimal(rank_change),
        excess_acceleration_5_sessions_20d=Decimal(acceleration),
        positive_20d_excess_persistence_sessions=positive_run,
        positive_20d_excess_run_started=session if positive_run else None,
        positive_20d_excess_persistence_left_censored=False,
        top_quartile_20d_persistence_sessions=positive_run,
        top_quartile_20d_run_started=session if positive_run else None,
        top_quartile_20d_persistence_left_censored=False,
        turnover_pulse_5_vs_prior_20=(
            None if turnover is None else Decimal(turnover)
        ),
    )


def snapshot(session: date, observations) -> SectorRadarSnapshot:
    return SectorRadarSnapshot(
        formula_version=FORMULA,
        as_of_session=session,
        benchmark_thscode="000300.SH",
        benchmark_name="沪深300",
        history_window_start=date(2026, 1, 5),
        history_window_end=session,
        observations=tuple(observations),
        exclusions=(),
    )


def candidate(
    code: str,
    name: str,
    family: str,
    *,
    acceleration: bool = False,
    rank_5: str = "10",
    rank_20: str = "10",
) -> SectorRadarShadowCandidate:
    return SectorRadarShadowCandidate(
        thscode=code,
        name=name,
        family=family,
        as_of_session=SESSION,
        event_type=ACCELERATING if acceleration else PERSISTENT_TOP_DECILE,
        horizon_5_rank=Decimal(rank_5),
        horizon_5_rating=95 if acceleration else 70,
        horizon_20_rank=Decimal(rank_20),
        horizon_20_rating=95,
        horizon_60_rating=80,
        horizon_5_excess_return=Decimal("0.03"),
        horizon_20_excess_return=Decimal("0.08"),
        horizon_60_excess_return=Decimal("0.12"),
        rank_change_5_sessions_20d=Decimal("25") if acceleration else Decimal(0),
        excess_acceleration_5_sessions_20d=(
            Decimal("0.02") if acceleration else Decimal(0)
        ),
        positive_20d_excess_persistence_sessions=8,
        top_quartile_20d_persistence_sessions=5,
        turnover_pulse_5_vs_prior_20=Decimal("1.3"),
        persistent_gate_entered=not acceleration,
        acceleration_gate_entered=acceleration,
    )


def entries(family: str, candidates=()) -> SectorRadarShadowStateEntries:
    return SectorRadarShadowStateEntries(
        policy_version="sector-shadow-state-entry-hierarchy-v0",
        family=family,
        as_of_session=SESSION,
        previous_session=PREVIOUS,
        benchmark_thscode="000300.SH",
        formula_version=FORMULA,
        candidates=tuple(candidates),
        quiet_reason=None if candidates else "NO_NEW_QUALIFIED_STATE_ENTRY",
    )


def membership(code: str, name: str, member_codes: tuple[str, ...]):
    return normalize_sector_membership(
        sector_thscode=code,
        sector_name=name,
        captured_at=CAPTURED,
        members=tuple(
            SectorConstituentIdentity(item, item[:6], item) for item in member_codes
        ),
    )


def breadth(code: str, name: str, member_codes: tuple[str, ...]):
    current_membership = membership(code, name, member_codes)
    return calculate_current_sector_breadth(
        membership=current_membership,
        market_session=SESSION,
        observed_at=OBSERVED,
        sector_last_price=Decimal("102"),
        sector_prev_price=Decimal("100"),
        constituent_points=tuple(
            ConstituentMarketPoint(
                thscode=item,
                market_session=SESSION,
                last_price=Decimal("102"),
                prev_price=Decimal("100"),
                turnover=Decimal(index + 1) * Decimal("100"),
            )
            for index, item in enumerate(member_codes)
        ),
    )


def test_state_entry_emits_once_and_unchanged_state_stays_quiet() -> None:
    previous = snapshot(
        PREVIOUS,
        (
            observation(
                "881101.TI",
                "种植业与林业",
                PREVIOUS,
                rating_20=89,
                positive_run=4,
            ),
        ),
    )
    current_observation = observation(
        "881101.TI",
        "种植业与林业",
        SESSION,
        rating_20=95,
        rank_20="5",
        positive_run=5,
    )
    current = snapshot(SESSION, (current_observation,))

    first = select_sector_radar_state_entries(current=current, previous=previous)
    assert first.family == BROAD_881
    assert [item.event_type for item in first.candidates] == [
        PERSISTENT_TOP_DECILE
    ]

    next_session = date(2026, 9, 7)
    repeated = snapshot(
        next_session,
        (replace(current_observation, as_of_session=next_session),),
    )
    deduplicated = select_sector_radar_state_entries(
        current=repeated,
        previous=current,
    )
    assert deduplicated.candidates == ()
    assert deduplicated.quiet_reason == "NO_NEW_QUALIFIED_STATE_ENTRY"


def test_acceleration_lane_can_surface_before_20d_top_decile() -> None:
    previous = snapshot(
        PREVIOUS,
        (
            observation(
                "881166.TI",
                "军工装备",
                PREVIOUS,
                rating_5=70,
                rating_20=58,
                positive_run=8,
                rank_change="10",
                acceleration="0.01",
                turnover="1.1",
            ),
        ),
    )
    current = snapshot(
        SESSION,
        (
            observation(
                "881166.TI",
                "军工装备",
                SESSION,
                rating_5=93,
                rating_20=60,
                rank_5="6",
                rank_20="36",
                positive_run=9,
                rank_change="33",
                acceleration="0.031",
                turnover="1.32",
            ),
        ),
    )

    selected = select_sector_radar_state_entries(current=current, previous=previous)
    assert selected.candidates[0].event_type == ACCELERATING
    assert selected.candidates[0].horizon_20_rating == 60


def test_state_entry_rejects_mixed_or_changed_universe() -> None:
    mixed = snapshot(
        SESSION,
        (
            observation("881101.TI", "广义", SESSION),
            observation("884001.TI", "细分", SESSION),
        ),
    )
    with pytest.raises(ValueError, match="homogeneous"):
        select_sector_radar_state_entries(current=mixed, previous=None)

    previous = snapshot(
        PREVIOUS,
        (observation("881101.TI", "甲", PREVIOUS),),
    )
    current = snapshot(
        SESSION,
        (observation("881102.TI", "乙", SESSION),),
    )
    with pytest.raises(ValueError, match="universe changed"):
        select_sector_radar_state_entries(current=current, previous=previous)


def test_broad_parent_and_contained_child_use_one_group() -> None:
    broad_candidate = candidate("881166.TI", "军工装备", BROAD_881)
    child_candidate = candidate(
        "884183.TI",
        "航海装备",
        GRANULAR_884,
        acceleration=True,
        rank_5="2",
    )
    parent_membership = membership(
        "881166.TI",
        "军工装备",
        ("600001.SH", "600002.SH", "600003.SH"),
    )
    child_membership = membership(
        "884183.TI",
        "航海装备",
        ("600001.SH", "600002.SH"),
    )
    link = build_current_parent_link(
        parent=parent_membership,
        child=child_membership,
    )

    composed = compose_sector_radar_shadow(
        broad_entries=entries(BROAD_881, (broad_candidate,)),
        granular_entries=entries(GRANULAR_884, (child_candidate,)),
        breadth_observations=(
            breadth(
                "881166.TI",
                "军工装备",
                ("600001.SH", "600002.SH", "600003.SH"),
            ),
            breadth(
                "884183.TI",
                "航海装备",
                ("600001.SH", "600002.SH"),
            ),
        ),
        parent_links=(link,),
    )

    assert len(composed.all_candidates) == 2
    assert len(composed.all_groups) == 1
    group = composed.surfaced_groups[0]
    assert group.primary_candidate.thscode == "881166.TI"
    assert [item.thscode for item in group.granular_drivers] == ["884183.TI"]
    assert group.grouping_reason == (
        "QUALIFIED_881_PARENT_WITH_FULLY_CONTAINED_884_DRIVERS"
    )


def test_granular_siblings_group_under_non_candidate_parent() -> None:
    pork = candidate(
        "884275.TI",
        "生猪养殖",
        GRANULAR_884,
        acceleration=True,
        rank_5="3",
    )
    chicken = candidate(
        "884276.TI",
        "肉鸡养殖",
        GRANULAR_884,
        rank_20="8",
    )
    parent_membership = membership(
        "881102.TI",
        "养殖业",
        ("600001.SH", "600002.SH", "600003.SH"),
    )
    pork_membership = membership(
        "884275.TI",
        "生猪养殖",
        ("600001.SH", "600002.SH"),
    )
    chicken_membership = membership(
        "884276.TI",
        "肉鸡养殖",
        ("600003.SH",),
    )

    composed = compose_sector_radar_shadow(
        broad_entries=entries(BROAD_881),
        granular_entries=entries(GRANULAR_884, (pork, chicken)),
        breadth_observations=(
            breadth(
                "884275.TI",
                "生猪养殖",
                ("600001.SH", "600002.SH"),
            ),
            breadth("884276.TI", "肉鸡养殖", ("600003.SH",)),
        ),
        parent_links=(
            build_current_parent_link(
                parent=parent_membership,
                child=pork_membership,
            ),
            build_current_parent_link(
                parent=parent_membership,
                child=chicken_membership,
            ),
        ),
    )

    assert len(composed.all_groups) == 1
    group = composed.all_groups[0]
    assert group.primary_candidate.thscode == "884275.TI"
    assert group.parent_context_thscode == "881102.TI"
    assert [item.thscode for item in group.granular_drivers] == ["884276.TI"]
    assert group.grouping_reason == (
        "GRANULAR_SIBLINGS_GROUPED_UNDER_NON_CANDIDATE_881_CONTEXT"
    )


def test_three_group_cap_preserves_complete_omitted_set() -> None:
    broad_candidates = tuple(
        candidate(
            f"88110{index}.TI",
            f"行业{index}",
            BROAD_881,
            acceleration=index < 2,
            rank_5=str(index + 1),
            rank_20=str(index + 1),
        )
        for index in range(1, 5)
    )
    breadth_rows = tuple(
        breadth(item.thscode, item.name, (f"60000{index}.SH",))
        for index, item in enumerate(broad_candidates, start=1)
    )

    composed = compose_sector_radar_shadow(
        broad_entries=entries(BROAD_881, broad_candidates),
        granular_entries=entries(GRANULAR_884),
        breadth_observations=breadth_rows,
        parent_links=(),
        max_surfaced_groups=3,
    )

    assert len(composed.all_groups) == 4
    assert len(composed.surfaced_groups) == 3
    assert len(composed.omitted_groups) == 1
    assert composed.truncated_group_count == 1
    assert {group.group_key for group in composed.all_groups} == {
        item.thscode for item in broad_candidates
    }


def test_composition_requires_same_session_breadth_and_retains_no_authority() -> None:
    broad_candidate = candidate("881101.TI", "种植业与林业", BROAD_881)
    wrong_session_breadth = replace(
        breadth("881101.TI", "种植业与林业", ("600001.SH",)),
        market_session=PREVIOUS,
    )
    with pytest.raises(ValueError, match="breadth session mismatch"):
        compose_sector_radar_shadow(
            broad_entries=entries(BROAD_881, (broad_candidate,)),
            granular_entries=entries(GRANULAR_884),
            breadth_observations=(wrong_session_breadth,),
            parent_links=(),
        )

    composed = compose_sector_radar_shadow(
        broad_entries=entries(BROAD_881, (broad_candidate,)),
        granular_entries=entries(GRANULAR_884),
        breadth_observations=(
            breadth("881101.TI", "种植业与林业", ("600001.SH",)),
        ),
        parent_links=(),
    )
    serialized = repr(asdict(composed)).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "portfolio" not in serialized
    assert composed.human_attention_authority == "NONE"
    assert composed.investment_authority == "NONE"
