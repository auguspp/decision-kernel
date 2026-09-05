from __future__ import annotations

import json
from dataclasses import replace
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
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_daily as daily
from decision_kernel.runtime.sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    normalize_sector_membership,
)
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar import (
    SectorHorizonObservation,
    SectorPricePoint,
    SectorPriceSeries,
    SectorRadarObservation,
    SectorRadarSnapshot,
)
from decision_kernel.runtime.sector_radar_daily import (
    PREPARATION_BUDGET_EXCEEDED,
    PREPARATION_QUIET,
    PREPARATION_READY,
    finalize_sector_radar_daily_run,
    prepare_sector_radar_daily_run,
    render_sector_radar_daily_preparation_markdown,
    render_sector_radar_daily_summary,
    serialize_sector_radar_daily_preparation,
    serialize_sector_radar_daily_result,
)
from decision_kernel.runtime.sector_radar_events import (
    create_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_shadow import (
    ACCELERATING,
    BROAD_881,
    GRANULAR_884,
    PERSISTENT_TOP_DECILE,
    SECTOR_RADAR_SHADOW_POLICY_VERSION,
    SectorRadarShadowCandidate,
    SectorRadarShadowStateEntries,
)
from decision_kernel.runtime.sector_radar_state import (
    STATE_UPDATE_ALREADY_CURRENT,
    STATE_UPDATE_APPENDED,
    SectorRadarStateSnapshotPair,
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
START = date(2026, 1, 1)
SESSIONS = tuple(START + timedelta(days=index) for index in range(130))
CREATED = datetime(2026, 5, 10, 15, 0, tzinfo=SHANGHAI)
PREPARED = datetime(2026, 5, 11, 15, 20, tzinfo=SHANGHAI)
CAPTURED = datetime(2026, 5, 11, 15, 35, tzinfo=SHANGHAI)
PRODUCED = datetime(2026, 5, 11, 16, 0, tzinfo=SHANGHAI)
FORMULA = "sector-rs-5-20-60-persistence126-v0"


def catalog():
    return normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": 1778457600000,
                "item": [
                    {"thscode": "881101.TI", "name": "种植业与林业"},
                    {"thscode": "881102.TI", "name": "养殖业"},
                    {"thscode": "884001.TI", "name": "种子生产"},
                    {"thscode": "884275.TI", "name": "生猪养殖"},
                ],
            },
        }
    )


def parent_hints():
    current_catalog = catalog()
    payload = {
        "schema_version": 1,
        "captured_at": "2026-05-10T15:50:00+08:00",
        "membership_capture_window": {
            "start": "2026-05-10T15:30:00+08:00",
            "end": "2026-05-10T16:00:00+08:00",
        },
        "source": "synthetic current memberships",
        "source_workflow_run_id": 1,
        "source_artifact_id": 2,
        "source_artifact_digest": "sha256:" + "a" * 64,
        "source_result_hash": "b" * 64,
        "catalog_hash": current_catalog.catalog_hash,
        "catalog_shape": {"broad_881": 2, "granular_884": 2},
        "mapping_result": {
            "unique_full_containment": 2,
            "ambiguous": 0,
            "unmapped": 0,
            "exact_duplicate_granular_member_sets": 0,
            "overlapping_broad_member_sets": 0,
            "parents_with_granular_children": 2,
            "broad_parents_without_granular_children": 0,
        },
        "parent_hints": [
            {
                "child_thscode": "884001.TI",
                "child_name": "种子生产",
                "child_member_count_at_capture": 1,
                "child_constituent_set_hash_at_capture": "c" * 64,
                "child_membership_captured_at": "2026-05-10T15:40:00+08:00",
                "parent_thscode": "881101.TI",
                "parent_name": "种植业与林业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "d" * 64,
                "parent_membership_captured_at": "2026-05-10T15:35:00+08:00",
                "intersection_count_at_capture": 1,
                "child_fully_contained_at_capture": True,
            },
            {
                "child_thscode": "884275.TI",
                "child_name": "生猪养殖",
                "child_member_count_at_capture": 1,
                "child_constituent_set_hash_at_capture": "e" * 64,
                "child_membership_captured_at": "2026-05-10T15:50:00+08:00",
                "parent_thscode": "881102.TI",
                "parent_name": "养殖业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "f" * 64,
                "parent_membership_captured_at": "2026-05-10T15:45:00+08:00",
                "intersection_count_at_capture": 1,
                "child_fully_contained_at_capture": True,
            },
        ],
        "use_semantics": {
            "purpose": "CURRENT_PARENT_HINT_FOR_CANDIDATE_TIME_REVALIDATION",
            "catalog_rule": (
                "CURRENT_CATALOG_IDENTITY_AND_HASH_MUST_BE_CHECKED_EXPLICITLY"
            ),
            "membership_rule": (
                "FETCH_CANDIDATE_CHILD_AND_HINTED_PARENT_CURRENT_MEMBERSHIPS_"
                "AND_REVALIDATE_FULL_CONTAINMENT_BEFORE_GROUPING"
            ),
            "failure_rule": (
                "CATALOG_OR_CONTAINMENT_DRIFT_REMAINS_VISIBLE_AND_PREVENTS_"
                "AUTOMATIC_GROUPING"
            ),
            "historical_taxonomy_authority": "NONE",
            "research_authority": "NONE",
            "human_attention_authority": "NONE",
            "investment_authority": "NONE",
        },
    }
    payload["mapping_hash"] = canonical_hash(payload)
    return parse_sector_parent_hints(json.dumps(payload, ensure_ascii=False))


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


def market_state():
    return create_sector_radar_market_state(
        catalog=catalog(),
        benchmark=series("000300.SH", "沪深300", "0.2"),
        broad_series=(
            series("881101.TI", "种植业与林业", "0.3"),
            series("881102.TI", "养殖业", "0.4"),
        ),
        granular_series=(
            series("884001.TI", "种子生产", "0.5"),
            series("884275.TI", "生猪养殖", "0.6"),
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


def qualified_snapshot(current_state, *, session: date, same_session: bool = False):
    points = []
    for item in current_state.series:
        if same_session:
            last = item.closes[-1]
            previous = item.closes[-2]
            turnover = item.turnovers[-1]
        else:
            previous = item.closes[-1]
            last = previous + Decimal("1")
            turnover = item.turnovers[-1] + Decimal("10")
        change = last - previous
        points.append(
            HithinkIndexSnapshotPoint(
                thscode=item.thscode,
                ticker=(
                    "1B0300"
                    if item.thscode == "000300.SH"
                    else item.thscode[:6]
                ),
                last_price=last,
                prev_price=previous,
                price_change=change,
                price_change_ratio_pct=change / previous * Decimal("100"),
                open_price=previous,
                high_price=max(previous, last),
                low_price=min(previous, last),
                volume=Decimal("100"),
                turnover=turnover,
            )
        )
    return HithinkQualifiedIndexSnapshotBatch(
        market_session=session,
        benchmark_thscode="000300.SH",
        provider_timestamp_ms=1778500000000,
        qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
        points=tuple(reversed(points)),
    )


def horizon(sessions: int) -> SectorHorizonObservation:
    return SectorHorizonObservation(
        sessions=sessions,
        sector_return=Decimal("0.01"),
        benchmark_return=Decimal(0),
        excess_return=Decimal("0.01"),
        cross_sectional_rank=Decimal("1"),
        cross_sectional_rating=99,
    )


def observation(code: str, name: str, session: date) -> SectorRadarObservation:
    return SectorRadarObservation(
        thscode=code,
        name=name,
        as_of_session=session,
        history_session_count=126,
        horizon_5=horizon(5),
        horizon_20=horizon(20),
        horizon_60=horizon(60),
        rank_change_5_sessions_20d=Decimal("0"),
        excess_acceleration_5_sessions_20d=Decimal("0"),
        positive_20d_excess_persistence_sessions=5,
        positive_20d_excess_run_started=session,
        positive_20d_excess_persistence_left_censored=False,
        top_quartile_20d_persistence_sessions=5,
        top_quartile_20d_run_started=session,
        top_quartile_20d_persistence_left_censored=False,
        turnover_pulse_5_vs_prior_20=Decimal("1.2"),
    )


def snapshot(session: date, identities) -> SectorRadarSnapshot:
    return SectorRadarSnapshot(
        formula_version=FORMULA,
        as_of_session=session,
        benchmark_thscode="000300.SH",
        benchmark_name="沪深300",
        history_window_start=session - timedelta(days=126),
        history_window_end=session,
        observations=tuple(
            observation(code, name, session) for code, name in identities
        ),
        exclusions=(),
    )


def candidate(
    code: str,
    name: str,
    family: str,
    *,
    accelerating: bool = False,
) -> SectorRadarShadowCandidate:
    return SectorRadarShadowCandidate(
        thscode=code,
        name=name,
        family=family,
        as_of_session=SESSIONS[-1] + timedelta(days=1),
        event_type=ACCELERATING if accelerating else PERSISTENT_TOP_DECILE,
        horizon_5_rank=Decimal("2"),
        horizon_5_rating=95,
        horizon_20_rank=Decimal("5"),
        horizon_20_rating=95,
        horizon_60_rating=85,
        horizon_5_excess_return=Decimal("0.03"),
        horizon_20_excess_return=Decimal("0.08"),
        horizon_60_excess_return=Decimal("0.12"),
        rank_change_5_sessions_20d=Decimal("25") if accelerating else Decimal("5"),
        excess_acceleration_5_sessions_20d=(
            Decimal("0.03") if accelerating else Decimal("0.01")
        ),
        positive_20d_excess_persistence_sessions=8,
        top_quartile_20d_persistence_sessions=5,
        turnover_pulse_5_vs_prior_20=Decimal("1.3"),
        persistent_gate_entered=not accelerating,
        acceleration_gate_entered=accelerating,
    )


def install_projected_entries(
    monkeypatch,
    *,
    broad_candidates=(),
    granular_candidates=(),
    seen_families=None,
):
    seen_families = seen_families if seen_families is not None else []

    def pair(current_state):
        previous_session = current_state.sessions[-2]
        current_session = current_state.sessions[-1]
        return SectorRadarStateSnapshotPair(
            state_hash=current_state.state_hash,
            previous_session=previous_session,
            current_session=current_session,
            broad_previous=snapshot(
                previous_session,
                current_state.broad_identities,
            ),
            broad_current=snapshot(
                current_session,
                current_state.broad_identities,
            ),
            granular_previous=snapshot(
                previous_session,
                current_state.granular_identities,
            ),
            granular_current=snapshot(
                current_session,
                current_state.granular_identities,
            ),
        )

    def select(*, current, previous):
        first_code = current.observations[0].thscode
        family = BROAD_881 if first_code.startswith("881") else GRANULAR_884
        seen_families.append(family)
        projected = broad_candidates if family == BROAD_881 else granular_candidates
        projected = tuple(
            replace(item, as_of_session=current.as_of_session)
            for item in projected
        )
        return SectorRadarShadowStateEntries(
            policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
            family=family,
            as_of_session=current.as_of_session,
            previous_session=previous.as_of_session,
            benchmark_thscode=current.benchmark_thscode,
            formula_version=current.formula_version,
            candidates=projected,
            quiet_reason=None if projected else "NO_NEW_QUALIFIED_STATE_ENTRY",
        )

    monkeypatch.setattr(
        daily,
        "calculate_sector_radar_state_snapshot_pair",
        pair,
    )
    monkeypatch.setattr(daily, "select_sector_radar_state_entries", select)


def membership(code: str, *, valid_containment: bool = True):
    definitions = {
        "881101.TI": (
            "种植业与林业",
            ("600001.SH", "600002.SH")
            if valid_containment
            else ("600002.SH",),
        ),
        "881102.TI": ("养殖业", ("600003.SH", "600004.SH")),
        "884001.TI": ("种子生产", ("600001.SH",)),
        "884275.TI": ("生猪养殖", ("600003.SH",)),
    }
    name, members = definitions[code]
    return normalize_sector_membership(
        sector_thscode=code,
        sector_name=name,
        captured_at=CAPTURED,
        members=tuple(
            SectorConstituentIdentity(
                thscode=member,
                ticker=member[:6],
                name=member,
            )
            for member in members
        ),
    )


def memberships_for_plan(plan, *, valid_containment: bool = True):
    return tuple(
        membership(
            request.thscode,
            valid_containment=valid_containment,
        )
        for request in plan.membership_requests
    )


def market_points(session: date):
    return tuple(
        ConstituentMarketPoint(
            thscode=f"60000{index}.SH",
            market_session=session,
            last_price=Decimal("101") + Decimal(index),
            prev_price=Decimal("100"),
            turnover=Decimal("1000") * Decimal(index),
        )
        for index in range(1, 5)
    )


def empty_ledger():
    return create_sector_radar_candidate_event_ledger(
        created_at=PREPARED,
        source="pure daily composition test",
    )


def prepared_run(
    monkeypatch,
    *,
    broad_candidates=(),
    granular_candidates=(),
    max_membership_requests=32,
):
    current = market_state()
    next_session = current.sessions[-1] + timedelta(days=1)
    install_projected_entries(
        monkeypatch,
        broad_candidates=broad_candidates,
        granular_candidates=granular_candidates,
    )
    prepared = prepare_sector_radar_daily_run(
        market_state=current,
        catalog=catalog(),
        qualified_snapshot=qualified_snapshot(current, session=next_session),
        parent_hints=parent_hints(),
        prepared_at=PREPARED,
        next_completed_session_after_state=next_session,
        max_membership_requests=max_membership_requests,
    )
    return current, prepared


def test_daily_root_appends_state_and_composes_separate_881_884_entries(
    monkeypatch,
) -> None:
    seen = []
    broad = candidate("881101.TI", "种植业与林业", BROAD_881)
    granular = candidate(
        "884001.TI",
        "种子生产",
        GRANULAR_884,
        accelerating=True,
    )
    current = market_state()
    next_session = current.sessions[-1] + timedelta(days=1)
    install_projected_entries(
        monkeypatch,
        broad_candidates=(broad,),
        granular_candidates=(granular,),
        seen_families=seen,
    )

    prepared = prepare_sector_radar_daily_run(
        market_state=current,
        catalog=catalog(),
        qualified_snapshot=qualified_snapshot(current, session=next_session),
        parent_hints=parent_hints(),
        prepared_at=PREPARED,
        next_completed_session_after_state=next_session,
    )

    assert seen == [BROAD_881, GRANULAR_884]
    assert prepared.state_update_status == STATE_UPDATE_APPENDED
    assert prepared.acquisition_plan.status == PREPARATION_READY
    assert prepared.acquisition_plan.candidate_thscodes == (
        "881101.TI",
        "884001.TI",
    )
    assert [
        request.thscode
        for request in prepared.acquisition_plan.membership_requests
    ] == ["881101.TI", "884001.TI"]

    result = finalize_sector_radar_daily_run(
        preparation=prepared,
        parent_hints=parent_hints(),
        memberships=memberships_for_plan(prepared.acquisition_plan),
        constituent_points=market_points(prepared.market_session),
        event_ledger=empty_ledger(),
        produced_at=PRODUCED,
    )

    assert len(result.parent_revalidations) == 1
    assert result.parent_revalidations[0].current_parent_link.child_fully_contained
    assert len(result.composition.all_candidates) == 2
    assert len(result.composition.all_groups) == 1
    assert result.composition.surfaced_groups[0].primary_candidate.thscode == (
        "881101.TI"
    )
    assert len(result.added_event_ids) == 2
    assert result.reused_event_ids == ()
    assert result.event_count == 2
    assert result.human_attention_authority == "NONE"
    assert result.investment_authority == "NONE"

    serialized = serialize_sector_radar_daily_result(result)
    assert serialize_sector_radar_daily_result(result) == serialized
    summary = render_sector_radar_daily_summary(result)
    assert "SHADOW OBSERVATION ONLY" in summary
    assert "HUMAN ATTENTION AUTHORITY = NONE" in summary
    assert "INVESTMENT AUTHORITY = NONE" in summary
    assert "NOT A RECOMMENDATION" in summary


def test_same_session_rerun_reuses_market_state_and_candidate_events(
    monkeypatch,
) -> None:
    broad = candidate("881101.TI", "种植业与林业", BROAD_881)
    granular = candidate("884001.TI", "种子生产", GRANULAR_884)
    _, first_preparation = prepared_run(
        monkeypatch,
        broad_candidates=(broad,),
        granular_candidates=(granular,),
    )
    first = finalize_sector_radar_daily_run(
        preparation=first_preparation,
        parent_hints=parent_hints(),
        memberships=memberships_for_plan(first_preparation.acquisition_plan),
        constituent_points=market_points(first_preparation.market_session),
        event_ledger=empty_ledger(),
        produced_at=PRODUCED,
    )

    install_projected_entries(
        monkeypatch,
        broad_candidates=(broad,),
        granular_candidates=(granular,),
    )
    repeated_at = PRODUCED + timedelta(minutes=10)
    repeated_preparation = prepare_sector_radar_daily_run(
        market_state=first.market_state,
        catalog=catalog(),
        qualified_snapshot=qualified_snapshot(
            first.market_state,
            session=first.market_session,
            same_session=True,
        ),
        parent_hints=parent_hints(),
        prepared_at=repeated_at,
        next_completed_session_after_state=(
            first.market_session + timedelta(days=1)
        ),
    )
    repeated = finalize_sector_radar_daily_run(
        preparation=repeated_preparation,
        parent_hints=parent_hints(),
        memberships=memberships_for_plan(
            repeated_preparation.acquisition_plan
        ),
        constituent_points=market_points(repeated_preparation.market_session),
        event_ledger=first.event_ledger,
        produced_at=repeated_at + timedelta(minutes=5),
    )

    assert repeated.state_update_status == STATE_UPDATE_ALREADY_CURRENT
    assert repeated.output_market_state_hash == first.output_market_state_hash
    assert repeated.added_event_ids == ()
    assert len(repeated.reused_event_ids) == 2
    assert repeated.event_ledger_hash == first.event_ledger_hash
    assert repeated.event_count == first.event_count == 2


def test_missed_completed_session_fails_before_state_append(monkeypatch) -> None:
    current = market_state()
    direct_next = current.sessions[-1] + timedelta(days=1)
    skipped_snapshot = qualified_snapshot(
        current,
        session=direct_next + timedelta(days=1),
    )

    with pytest.raises(ValueError, match="not the direct next completed session"):
        prepare_sector_radar_daily_run(
            market_state=current,
            catalog=catalog(),
            qualified_snapshot=skipped_snapshot,
            parent_hints=parent_hints(),
            prepared_at=PREPARED,
            next_completed_session_after_state=direct_next,
        )


def test_acquisition_budget_excess_keeps_all_candidates_and_blocks_finalize(
    monkeypatch,
) -> None:
    broad = candidate("881101.TI", "种植业与林业", BROAD_881)
    granular = candidate("884001.TI", "种子生产", GRANULAR_884)
    _, prepared = prepared_run(
        monkeypatch,
        broad_candidates=(broad,),
        granular_candidates=(granular,),
        max_membership_requests=1,
    )

    assert prepared.acquisition_plan.status == PREPARATION_BUDGET_EXCEEDED
    assert prepared.acquisition_plan.candidate_thscodes == (
        "881101.TI",
        "884001.TI",
    )
    assert prepared.acquisition_plan.distinct_membership_request_count == 2
    assert len(prepared.acquisition_plan.membership_requests) == 2
    serialized = serialize_sector_radar_daily_preparation(prepared)
    assert "881101.TI" in serialized
    assert "884001.TI" in serialized
    summary = render_sector_radar_daily_preparation_markdown(prepared)
    assert "No candidate was silently truncated" in summary

    with pytest.raises(ValueError, match="budget-exceeded"):
        finalize_sector_radar_daily_run(
            preparation=prepared,
            parent_hints=parent_hints(),
            memberships=memberships_for_plan(prepared.acquisition_plan),
            constituent_points=market_points(prepared.market_session),
            event_ledger=empty_ledger(),
            produced_at=PRODUCED,
        )


def test_quiet_run_requests_no_live_enrichment_and_keeps_ledger_unchanged(
    monkeypatch,
) -> None:
    _, prepared = prepared_run(monkeypatch)

    assert prepared.acquisition_plan.status == PREPARATION_QUIET
    assert prepared.acquisition_plan.membership_requests == ()
    assert prepared.acquisition_plan.all_market_snapshot_required is False
    ledger = empty_ledger()
    result = finalize_sector_radar_daily_run(
        preparation=prepared,
        parent_hints=parent_hints(),
        memberships=(),
        constituent_points=(),
        event_ledger=ledger,
        produced_at=PRODUCED,
    )

    assert result.composition.all_candidates == ()
    assert result.composition.surfaced_groups == ()
    assert result.event_ledger is ledger
    assert result.event_ledger_hash == ledger.ledger_hash
    assert "Nothing new qualified" in render_sector_radar_daily_summary(result)


def test_candidate_time_containment_drift_fails_closed(monkeypatch) -> None:
    granular = candidate("884001.TI", "种子生产", GRANULAR_884)
    _, prepared = prepared_run(
        monkeypatch,
        granular_candidates=(granular,),
    )

    with pytest.raises(ValueError, match="no longer fully contained"):
        finalize_sector_radar_daily_run(
            preparation=prepared,
            parent_hints=parent_hints(),
            memberships=memberships_for_plan(
                prepared.acquisition_plan,
                valid_containment=False,
            ),
            constituent_points=market_points(prepared.market_session),
            event_ledger=empty_ledger(),
            produced_at=PRODUCED,
        )


def test_candidate_without_any_priced_members_fails_breadth(monkeypatch) -> None:
    broad = candidate("881101.TI", "种植业与林业", BROAD_881)
    _, prepared = prepared_run(
        monkeypatch,
        broad_candidates=(broad,),
    )
    unrelated_points = (
        ConstituentMarketPoint(
            thscode="600999.SH",
            market_session=prepared.market_session,
            last_price=Decimal("101"),
            prev_price=Decimal("100"),
            turnover=Decimal("1000"),
        ),
    )

    with pytest.raises(ValueError, match="at least one priced constituent"):
        finalize_sector_radar_daily_run(
            preparation=prepared,
            parent_hints=parent_hints(),
            memberships=memberships_for_plan(prepared.acquisition_plan),
            constituent_points=unrelated_points,
            event_ledger=empty_ledger(),
            produced_at=PRODUCED,
        )


def test_full_artifact_retains_groups_omitted_from_bounded_summary(
    monkeypatch,
) -> None:
    broad_candidates = (
        candidate("881101.TI", "种植业与林业", BROAD_881),
        candidate(
            "881102.TI",
            "养殖业",
            BROAD_881,
            accelerating=True,
        ),
    )
    _, prepared = prepared_run(
        monkeypatch,
        broad_candidates=broad_candidates,
    )
    result = finalize_sector_radar_daily_run(
        preparation=prepared,
        parent_hints=parent_hints(),
        memberships=memberships_for_plan(prepared.acquisition_plan),
        constituent_points=market_points(prepared.market_session),
        event_ledger=empty_ledger(),
        produced_at=PRODUCED,
        max_surfaced_groups=1,
    )

    assert len(result.composition.all_groups) == 2
    assert len(result.composition.surfaced_groups) == 1
    assert len(result.composition.omitted_groups) == 1
    artifact = serialize_sector_radar_daily_result(result)
    for code in ("881101.TI", "881102.TI"):
        assert code in artifact
    assert "1 additional complete group" in render_sector_radar_daily_summary(
        result
    )
