from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkIndexSnapshotPoint,
    HithinkQualifiedIndexSnapshotBatch,
    normalize_hithink_industry_catalog,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_http, sector_radar_daily
from decision_kernel.runtime.sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    normalize_sector_membership,
)
from decision_kernel.runtime.sector_parent_hints import parse_sector_parent_hints
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_events import (
    create_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_persistence import (
    SOURCE_COMMITTED_BOOTSTRAP,
    SectorRadarPersistenceResolution,
    load_sector_radar_persistent_bundle,
)
from decision_kernel.runtime.sector_radar_producer import (
    PRODUCER_STATUS_APPENDED_QUIET,
    PRODUCER_STATUS_APPENDED_WITH_CANDIDATES,
    PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
    SECTOR_RADAR_STATE_ARTIFACT_NAME,
    SECTOR_RADAR_WORKFLOW_PATH,
    SectorRadarProducerContext,
    SectorRadarProducerError,
    discover_previous_sector_radar_artifact,
    run_sector_radar_producer,
    write_github_output,
)
from decision_kernel.runtime.sector_radar_shadow import (
    BROAD_881,
    GRANULAR_884,
    PERSISTENT_TOP_DECILE,
    SECTOR_RADAR_SHADOW_POLICY_VERSION,
    SectorRadarShadowCandidate,
    SectorRadarShadowStateEntries,
)
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
START = date(2026, 1, 1)
SESSIONS = tuple(START + timedelta(days=index) for index in range(127))
CACHED_SESSION = SESSIONS[-1]
NEXT_SESSION = CACHED_SESSION + timedelta(days=1)
SECOND_MISSED_SESSION = NEXT_SESSION + timedelta(days=1)
CREATED = datetime.combine(CACHED_SESSION, time(15), tzinfo=SHANGHAI)
VALIDATION_AT = datetime.combine(CACHED_SESSION, time(16), tzinfo=SHANGHAI)
APPEND_AT = datetime.combine(NEXT_SESSION, time(16), tzinfo=SHANGHAI)
PRODUCED_AT = datetime.combine(NEXT_SESSION, time(16, 5), tzinfo=SHANGHAI)
REPOSITORY = "auguspp/decision-kernel"
COMMIT = "a" * 40
FORMULA = "sector-rs-5-20-60-persistence126-v0"


def catalog():
    return normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": int(APPEND_AT.timestamp() * 1000),
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
        "captured_at": "2026-05-07T15:50:00+08:00",
        "membership_capture_window": {
            "start": "2026-05-07T15:30:00+08:00",
            "end": "2026-05-07T16:00:00+08:00",
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
                "child_membership_captured_at": "2026-05-07T15:40:00+08:00",
                "parent_thscode": "881101.TI",
                "parent_name": "种植业与林业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "d" * 64,
                "parent_membership_captured_at": "2026-05-07T15:35:00+08:00",
                "intersection_count_at_capture": 1,
                "child_fully_contained_at_capture": True,
            },
            {
                "child_thscode": "884275.TI",
                "child_name": "生猪养殖",
                "child_member_count_at_capture": 1,
                "child_constituent_set_hash_at_capture": "e" * 64,
                "child_membership_captured_at": "2026-05-07T15:50:00+08:00",
                "parent_thscode": "881102.TI",
                "parent_name": "养殖业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "f" * 64,
                "parent_membership_captured_at": "2026-05-07T15:45:00+08:00",
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


def resolution():
    return SectorRadarPersistenceResolution(
        source_kind=SOURCE_COMMITTED_BOOTSTRAP,
        market_state=market_state(),
        event_ledger=create_sector_radar_candidate_event_ledger(
            created_at=CREATED,
            source="producer test ledger",
        ),
        source_bundle_manifest=None,
        bootstrap_manifest_hash="c" * 64,
    )


def context(observed_at: datetime):
    return SectorRadarProducerContext(
        repository=REPOSITORY,
        workflow_path=SECTOR_RADAR_WORKFLOW_PATH,
        run_id=100,
        run_attempt=1,
        commit_sha=COMMIT,
        observed_at=observed_at,
    )


def snapshot(current_state, *, session: date, same_session: bool):
    points = []
    for item in current_state.series:
        if same_session:
            previous = item.closes[-2]
            last = item.closes[-1]
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
        provider_timestamp_ms=int(
            datetime.combine(session, time(15, 5), tzinfo=SHANGHAI).timestamp()
            * 1000
        ),
        qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
        points=tuple(reversed(points)),
    )


def calendar(*sessions: date):
    return tuple(sorted(set((*SESSIONS, *sessions))))


def quiet_selector(monkeypatch) -> None:
    def select(*, current, previous):
        family = (
            BROAD_881
            if current.observations[0].thscode.startswith("881")
            else GRANULAR_884
        )
        return SectorRadarShadowStateEntries(
            policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
            family=family,
            as_of_session=current.as_of_session,
            previous_session=previous.as_of_session,
            benchmark_thscode=current.benchmark_thscode,
            formula_version=current.formula_version,
            candidates=(),
            quiet_reason="NO_NEW_QUALIFIED_STATE_ENTRY",
        )

    monkeypatch.setattr(
        sector_radar_daily,
        "select_sector_radar_state_entries",
        select,
    )


def candidate(code: str, name: str, family: str):
    return SectorRadarShadowCandidate(
        thscode=code,
        name=name,
        family=family,
        as_of_session=NEXT_SESSION,
        event_type=PERSISTENT_TOP_DECILE,
        horizon_5_rank=Decimal("4"),
        horizon_5_rating=95,
        horizon_20_rank=Decimal("5"),
        horizon_20_rating=95,
        horizon_60_rating=85,
        horizon_5_excess_return=Decimal("0.03"),
        horizon_20_excess_return=Decimal("0.08"),
        horizon_60_excess_return=Decimal("0.12"),
        rank_change_5_sessions_20d=Decimal("5"),
        excess_acceleration_5_sessions_20d=Decimal("0.01"),
        positive_20d_excess_persistence_sessions=8,
        top_quartile_20d_persistence_sessions=5,
        turnover_pulse_5_vs_prior_20=Decimal("1.3"),
        persistent_gate_entered=True,
        acceleration_gate_entered=False,
    )


def candidate_selector(monkeypatch) -> None:
    broad = candidate("881101.TI", "种植业与林业", BROAD_881)
    granular = candidate("884001.TI", "种子生产", GRANULAR_884)

    def select(*, current, previous):
        family = (
            BROAD_881
            if current.observations[0].thscode.startswith("881")
            else GRANULAR_884
        )
        selected = broad if family == BROAD_881 else granular
        return SectorRadarShadowStateEntries(
            policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
            family=family,
            as_of_session=current.as_of_session,
            previous_session=previous.as_of_session,
            benchmark_thscode=current.benchmark_thscode,
            formula_version=current.formula_version,
            candidates=(replace(selected, as_of_session=current.as_of_session),),
            quiet_reason=None,
        )

    monkeypatch.setattr(
        sector_radar_daily,
        "select_sector_radar_state_entries",
        select,
    )


def membership(code: str):
    definitions = {
        "881101.TI": ("种植业与林业", ("600001.SH", "600002.SH")),
        "884001.TI": ("种子生产", ("600001.SH",)),
    }
    name, members = definitions[code]
    return normalize_sector_membership(
        sector_thscode=code,
        sector_name=name,
        captured_at=datetime.combine(NEXT_SESSION, time(15, 30), tzinfo=SHANGHAI),
        members=tuple(
            SectorConstituentIdentity(
                thscode=member,
                ticker=member[:6],
                name=member,
            )
            for member in members
        ),
    )


def all_market_points():
    return (
        ConstituentMarketPoint(
            thscode="600001.SH",
            market_session=NEXT_SESSION,
            last_price=Decimal("103"),
            prev_price=Decimal("100"),
            turnover=Decimal("1000"),
        ),
        ConstituentMarketPoint(
            thscode="600002.SH",
            market_session=NEXT_SESSION,
            last_price=Decimal("101"),
            prev_price=Decimal("100"),
            turnover=Decimal("500"),
        ),
    )


def test_public_calendar_fetch_normalizes_exact_provider_sessions() -> None:
    sessions = (CACHED_SESSION, NEXT_SESSION)

    def request_json(path, params):
        assert path == hithink_http.HITHINK_CALENDAR_PATH
        assert dict(params) == {}
        return {
            "code": 0,
            "data": {
                "item": [
                    {"date": session.strftime("%Y%m%d")}
                    for session in sessions
                ]
            },
        }

    assert hithink_http.fetch_hithink_trading_calendar(
        observed_at=VALIDATION_AT,
        api_key="fixture-secret",
        request_json=request_json,
    ) == sessions


def test_artifact_discovery_uses_only_latest_successful_run() -> None:
    urls = []

    def request_json(url):
        urls.append(url)
        if "/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "id": 90,
                        "run_attempt": 1,
                        "head_sha": "d" * 40,
                        "head_branch": "main",
                        "conclusion": "success",
                    },
                    {
                        "id": 80,
                        "run_attempt": 1,
                        "head_sha": "e" * 40,
                        "head_branch": "main",
                        "conclusion": "success",
                    },
                ]
            }
        assert "/runs/90/artifacts" in url
        return {
            "artifacts": [
                {
                    "id": 900,
                    "name": SECTOR_RADAR_STATE_ARTIFACT_NAME,
                    "expired": True,
                    "size_in_bytes": 100,
                }
            ]
        }

    discovery = discover_previous_sector_radar_artifact(
        repository=REPOSITORY,
        workflow_file="sector-radar-shadow.yml",
        current_run_id=100,
        token=None,
        request_json=request_json,
    )

    assert discovery.prior_success_found is True
    assert discovery.artifact_available is False
    assert discovery.prior_run_id == 90
    assert discovery.artifact_expired is True
    assert all("/runs/80/artifacts" not in url for url in urls)


def test_artifact_discovery_outputs_download_identity(tmp_path: Path) -> None:
    def request_json(url):
        if "/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "id": 90,
                        "run_attempt": 2,
                        "head_sha": "d" * 40,
                        "head_branch": "main",
                        "conclusion": "success",
                    }
                ]
            }
        return {
            "artifacts": [
                {
                    "id": 900,
                    "name": SECTOR_RADAR_STATE_ARTIFACT_NAME,
                    "expired": False,
                    "size_in_bytes": 100,
                }
            ]
        }

    discovery = discover_previous_sector_radar_artifact(
        repository=REPOSITORY,
        workflow_file="sector-radar-shadow.yml",
        current_run_id=100,
        token=None,
        request_json=request_json,
    )
    output = tmp_path / "github-output"
    write_github_output(output, discovery)
    values = dict(
        line.split("=", maxsplit=1)
        for line in output.read_text(encoding="utf-8").splitlines()
    )

    assert values["prior_success_found"] == "true"
    assert values["artifact_available"] == "true"
    assert values["artifact_run_id"] == "90"
    assert values["artifact_run_attempt"] == "2"
    assert values["artifact_id"] == "900"


def test_same_session_run_validates_without_membership_or_event_append(
    tmp_path: Path,
) -> None:
    restored = resolution()
    membership_calls = []
    all_market_calls = []

    outcome = run_sector_radar_producer(
        resolution=restored,
        parent_hints=parent_hints(),
        context=context(VALIDATION_AT),
        state_directory=tmp_path / "state",
        output_directory=tmp_path / "run",
        api_key="fixture-secret",
        fetch_calendar=lambda **kwargs: calendar(NEXT_SESSION),
        fetch_catalog=lambda **kwargs: catalog(),
        fetch_snapshot=lambda **kwargs: snapshot(
            restored.market_state,
            session=CACHED_SESSION,
            same_session=True,
        ),
        fetch_membership=lambda **kwargs: membership_calls.append(kwargs),
        fetch_all_market=lambda **kwargs: all_market_calls.append(kwargs),
        now=lambda: VALIDATION_AT + timedelta(minutes=5),
        sleep=lambda seconds: None,
    )

    assert outcome.status == PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT
    assert outcome.result is None
    assert outcome.persistent_bundle.market_state.state_hash == (
        restored.market_state.state_hash
    )
    assert outcome.persistent_bundle.event_ledger.ledger_hash == (
        restored.event_ledger.ledger_hash
    )
    assert outcome.persistent_bundle.event_ledger.events == ()
    assert membership_calls == []
    assert all_market_calls == []
    assert outcome.operations.candidate_count is not None
    assert "validation only" in (
        tmp_path / "run" / "operations.md"
    ).read_text(encoding="utf-8").lower()
    load_sector_radar_persistent_bundle(
        tmp_path / "state",
        expected_repository=REPOSITORY,
        expected_workflow=SECTOR_RADAR_WORKFLOW_PATH,
        expected_parent_hint_mapping_hash=parent_hints().mapping_hash,
    )


def test_one_new_session_quiet_run_appends_without_breadth_calls(
    monkeypatch,
    tmp_path: Path,
) -> None:
    quiet_selector(monkeypatch)
    restored = resolution()

    outcome = run_sector_radar_producer(
        resolution=restored,
        parent_hints=parent_hints(),
        context=context(APPEND_AT),
        state_directory=tmp_path / "state",
        output_directory=tmp_path / "run",
        api_key="fixture-secret",
        fetch_calendar=lambda **kwargs: calendar(NEXT_SESSION),
        fetch_catalog=lambda **kwargs: catalog(),
        fetch_snapshot=lambda **kwargs: snapshot(
            restored.market_state,
            session=NEXT_SESSION,
            same_session=False,
        ),
        fetch_membership=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("quiet run fetched membership")
        ),
        fetch_all_market=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("quiet run fetched all-market snapshot")
        ),
        now=lambda: PRODUCED_AT,
        sleep=lambda seconds: None,
    )

    assert outcome.status == PRODUCER_STATUS_APPENDED_QUIET
    assert outcome.result is not None
    assert outcome.persistent_bundle.market_state.sessions[-1] == NEXT_SESSION
    assert outcome.persistent_bundle.event_ledger.events == ()
    assert outcome.operations.candidate_count == 0


def test_one_new_session_fetches_exact_candidate_plan_and_appends_events(
    monkeypatch,
    tmp_path: Path,
) -> None:
    candidate_selector(monkeypatch)
    restored = resolution()
    membership_codes = []
    all_market_sessions = []

    def fetch_membership(**kwargs):
        membership_codes.append(kwargs["sector_thscode"])
        return membership(kwargs["sector_thscode"])

    def fetch_all_market(**kwargs):
        all_market_sessions.append(kwargs["market_session"])
        return SimpleNamespace(points=all_market_points())

    outcome = run_sector_radar_producer(
        resolution=restored,
        parent_hints=parent_hints(),
        context=context(APPEND_AT),
        state_directory=tmp_path / "state",
        output_directory=tmp_path / "run",
        api_key="fixture-secret",
        fetch_calendar=lambda **kwargs: calendar(NEXT_SESSION),
        fetch_catalog=lambda **kwargs: catalog(),
        fetch_snapshot=lambda **kwargs: snapshot(
            restored.market_state,
            session=NEXT_SESSION,
            same_session=False,
        ),
        fetch_membership=fetch_membership,
        fetch_all_market=fetch_all_market,
        now=lambda: PRODUCED_AT,
        sleep=lambda seconds: None,
    )

    assert outcome.status == PRODUCER_STATUS_APPENDED_WITH_CANDIDATES
    assert membership_codes == ["881101.TI", "884001.TI"]
    assert all_market_sessions == [NEXT_SESSION]
    assert outcome.result is not None
    assert len(outcome.result.composition.all_candidates) == 2
    assert len(outcome.result.composition.all_groups) == 1
    assert len(outcome.persistent_bundle.event_ledger.events) == 2
    assert outcome.operations.candidate_count == 2
    assert outcome.operations.membership_request_count == 2
    assert (tmp_path / "run" / "result.json").is_file()
    assert (tmp_path / "run" / "summary.md").is_file()


def test_more_than_one_completed_session_after_state_fails_before_market_fetch(
    tmp_path: Path,
) -> None:
    restored = resolution()
    catalog_calls = []

    with pytest.raises(SectorRadarProducerError, match="missed one or more"):
        run_sector_radar_producer(
            resolution=restored,
            parent_hints=parent_hints(),
            context=context(
                datetime.combine(
                    SECOND_MISSED_SESSION,
                    time(16),
                    tzinfo=SHANGHAI,
                )
            ),
            state_directory=tmp_path / "state",
            output_directory=tmp_path / "run",
            api_key="fixture-secret",
            fetch_calendar=lambda **kwargs: calendar(
                NEXT_SESSION,
                SECOND_MISSED_SESSION,
            ),
            fetch_catalog=lambda **kwargs: catalog_calls.append(kwargs),
            fetch_snapshot=lambda **kwargs: None,
            now=lambda: PRODUCED_AT,
            sleep=lambda seconds: None,
        )

    assert catalog_calls == []
    assert not (tmp_path / "state").exists()
