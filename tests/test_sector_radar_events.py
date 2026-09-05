from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    calculate_current_sector_breadth,
    normalize_sector_membership,
)
from decision_kernel.runtime.sector_radar_events import (
    append_sector_radar_candidate_events,
    create_sector_radar_candidate_event_ledger,
    parse_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_shadow import (
    BROAD_881,
    PERSISTENT_TOP_DECILE,
    SECTOR_RADAR_SHADOW_POLICY_VERSION,
    SectorRadarShadowCandidate,
    SectorRadarShadowComposition,
    SectorRadarShadowGroup,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
SESSION = date(2026, 9, 7)
CREATED = datetime(2026, 9, 7, 15, 20, tzinfo=SHANGHAI)
RECORDED = datetime(2026, 9, 7, 16, 0, tzinfo=SHANGHAI)


def candidate(*, rating_20: int = 95) -> SectorRadarShadowCandidate:
    return SectorRadarShadowCandidate(
        thscode="881101.TI",
        name="种植业与林业",
        family=BROAD_881,
        as_of_session=SESSION,
        event_type=PERSISTENT_TOP_DECILE,
        horizon_5_rank=Decimal("8"),
        horizon_5_rating=91,
        horizon_20_rank=Decimal("5"),
        horizon_20_rating=rating_20,
        horizon_60_rating=88,
        horizon_5_excess_return=Decimal("0.03"),
        horizon_20_excess_return=Decimal("0.08"),
        horizon_60_excess_return=Decimal("0.12"),
        rank_change_5_sessions_20d=Decimal("9"),
        excess_acceleration_5_sessions_20d=Decimal("0.02"),
        positive_20d_excess_persistence_sessions=8,
        top_quartile_20d_persistence_sessions=5,
        turnover_pulse_5_vs_prior_20=Decimal("1.3"),
        persistent_gate_entered=True,
        acceleration_gate_entered=False,
    )


def breadth(*, observed_at: datetime = RECORDED):
    membership = normalize_sector_membership(
        sector_thscode="881101.TI",
        sector_name="种植业与林业",
        captured_at=CREATED,
        members=(
            SectorConstituentIdentity("600001.SH", "600001", "甲"),
            SectorConstituentIdentity("600002.SH", "600002", "乙"),
        ),
    )
    return calculate_current_sector_breadth(
        membership=membership,
        market_session=SESSION,
        observed_at=observed_at,
        sector_last_price=Decimal("103"),
        sector_prev_price=Decimal("100"),
        constituent_points=(
            ConstituentMarketPoint(
                thscode="600001.SH",
                market_session=SESSION,
                last_price=Decimal("102"),
                prev_price=Decimal("100"),
                turnover=Decimal("1000"),
            ),
            ConstituentMarketPoint(
                thscode="600002.SH",
                market_session=SESSION,
                last_price=Decimal("104"),
                prev_price=Decimal("100"),
                turnover=Decimal("500"),
            ),
        ),
    )


def composition(
    *,
    signal: SectorRadarShadowCandidate | None = None,
    observed_at: datetime = RECORDED,
) -> SectorRadarShadowComposition:
    signal = signal or candidate()
    current_breadth = breadth(observed_at=observed_at)
    group = SectorRadarShadowGroup(
        group_key=signal.thscode,
        primary_candidate=signal,
        primary_breadth=current_breadth,
        parent_context_thscode=signal.thscode,
        parent_context_name=signal.name,
        granular_drivers=(),
        granular_driver_breadth=(),
        all_candidates=(signal,),
        grouping_reason="QUALIFIED_881_PARENT_ONLY",
    )
    return SectorRadarShadowComposition(
        policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
        as_of_session=SESSION,
        all_candidates=(signal,),
        all_groups=(group,),
        surfaced_groups=(group,),
        omitted_groups=(),
        truncated_group_count=0,
        quiet_reason=None,
    )


def append(ledger, current_composition, *, recorded_at=RECORDED):
    return append_sector_radar_candidate_events(
        ledger=ledger,
        composition=current_composition,
        source_market_state_hash="a" * 64,
        catalog_hash="b" * 64,
        parent_hint_mapping_hash="c" * 64,
        benchmark_thscode="000300.SH",
        formula_version="sector-rs-5-20-60-persistence126-v0",
        recorded_at=recorded_at,
    )


def test_event_ledger_round_trips_and_has_no_signal_authority() -> None:
    empty = create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="pure daily composition test",
    )
    update = append(empty, composition())

    assert len(update.added_event_ids) == 1
    assert update.reused_event_ids == ()
    assert len(update.ledger.events) == 1
    assert update.ledger.signal_transition_authority == "NONE"
    assert update.ledger.human_attention_authority == "NONE"
    assert update.ledger.investment_authority == "NONE"

    serialized = serialize_sector_radar_candidate_event_ledger(update.ledger)
    parsed = parse_sector_radar_candidate_event_ledger(serialized)
    assert parsed == update.ledger
    assert serialize_sector_radar_candidate_event_ledger(parsed) == serialized


def test_same_signal_event_is_reused_without_overwriting_first_enrichment() -> None:
    empty = create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="pure daily composition test",
    )
    first = append(empty, composition())
    first_event = first.ledger.events[0]

    repeated_at = RECORDED + timedelta(minutes=10)
    repeated = append(
        first.ledger,
        composition(observed_at=repeated_at),
        recorded_at=repeated_at,
    )

    assert repeated.added_event_ids == ()
    assert repeated.reused_event_ids == (first_event.event_id,)
    assert repeated.ledger is first.ledger
    assert repeated.ledger.ledger_hash == first.ledger.ledger_hash
    assert repeated.ledger.events[0].first_breadth_hash == (
        first_event.first_breadth_hash
    )
    assert repeated.ledger.events[0].first_recorded_at == RECORDED


def test_existing_event_rejects_changed_signal_payload_for_same_identity() -> None:
    empty = create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="pure daily composition test",
    )
    first = append(empty, composition())

    with pytest.raises(ValueError, match="recomputed signal identity"):
        append(
            first.ledger,
            composition(signal=candidate(rating_20=94)),
            recorded_at=RECORDED + timedelta(minutes=5),
        )


def test_ledger_hash_detects_serialized_signal_tampering() -> None:
    empty = create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="pure daily composition test",
    )
    current = append(empty, composition()).ledger
    payload = json.loads(serialize_sector_radar_candidate_event_ledger(current))
    payload["events"][0]["candidate"]["horizon_20_rating"] = 94

    with pytest.raises(ValueError, match="candidate hash mismatch"):
        parse_sector_radar_candidate_event_ledger(
            json.dumps(payload, ensure_ascii=False)
        )


def test_empty_composition_keeps_ledger_exactly_unchanged() -> None:
    empty = create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="pure daily composition test",
    )
    quiet = SectorRadarShadowComposition(
        policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
        as_of_session=SESSION,
        all_candidates=(),
        all_groups=(),
        surfaced_groups=(),
        omitted_groups=(),
        truncated_group_count=0,
        quiet_reason="NO_NEW_HIERARCHICAL_STATE_ENTRY_GROUP",
    )

    update = append(empty, quiet)
    assert update.ledger is empty
    assert update.added_event_ids == ()
    assert update.reused_event_ids == ()
