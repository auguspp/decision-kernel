from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from decision_kernel.adapters.hithink_index import (
    HithinkIndustryCatalog,
    HithinkQualifiedIndexSnapshotBatch,
)
from decision_kernel.identity import canonical_hash, canonical_json

from .sector_breadth import (
    ConstituentMarketPoint,
    SectorCurrentBreadthObservation,
    SectorMembershipSnapshot,
    calculate_current_sector_breadth,
)
from .sector_parent_hints import (
    SectorParentHintIndex,
    SectorParentHintRevalidation,
    sector_parent_hint_for_child,
    revalidate_current_sector_parent_hint,
    validate_sector_parent_hint_catalog,
)
from .sector_radar_events import (
    SectorRadarCandidateEventLedger,
    SectorRadarCandidateEventLedgerUpdate,
    append_sector_radar_candidate_events,
)
from .sector_radar_shadow import (
    BROAD_881,
    GRANULAR_884,
    SECTOR_RADAR_SHADOW_MAX_SURFACED_GROUPS,
    SectorRadarShadowCandidate,
    SectorRadarShadowComposition,
    SectorRadarShadowStateEntries,
    compose_sector_radar_shadow,
    select_sector_radar_state_entries,
)
from .sector_radar_state import (
    STATE_UPDATE_ALREADY_CURRENT,
    STATE_UPDATE_APPENDED,
    SectorRadarMarketState,
    SectorRadarStateSnapshotPair,
    SectorRadarStateUpdate,
    append_qualified_sector_snapshot,
    calculate_sector_radar_state_snapshot_pair,
)


SECTOR_RADAR_DAILY_SCHEMA_VERSION = 1
SECTOR_RADAR_DAILY_ARTIFACT_SEMANTICS = (
    "PURE_PROSPECTIVE_SHADOW_COMPOSITION_AUDIT_ONLY"
)
SECTOR_RADAR_DAILY_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_DAILY_INVESTMENT_AUTHORITY = "NONE"
SECTOR_RADAR_DAILY_DEFAULT_MAX_MEMBERSHIP_REQUESTS = 32
SECTOR_RADAR_DAILY_ACQUISITION_BUDGET_SEMANTICS = (
    "OPERATIONS_SAFETY_BUDGET_ONLY_NOT_A_SIGNAL_OR_RANKING_THRESHOLD"
)

PREPARATION_READY = "READY_FOR_CURRENT_BREADTH_ENRICHMENT"
PREPARATION_QUIET = "QUIET_NO_NEW_STATE_ENTRY"
PREPARATION_BUDGET_EXCEEDED = "DEGRADED_ACQUISITION_BUDGET_EXCEEDED"

CANDIDATE_BREADTH_ROLE = "CURRENT_BREADTH_FOR_FALSE_TO_TRUE_CANDIDATE"
GRANULAR_CHILD_REVALIDATION_ROLE = (
    "CURRENT_GRANULAR_CHILD_CONTAINMENT_REVALIDATION"
)
HINTED_PARENT_REVALIDATION_ROLE = (
    "CURRENT_HINTED_PARENT_CONTAINMENT_REVALIDATION"
)


@dataclass(frozen=True)
class SectorRadarMembershipRequest:
    thscode: str
    name: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class SectorRadarAcquisitionPlan:
    market_session: date
    status: str
    candidate_thscodes: tuple[str, ...]
    membership_requests: tuple[SectorRadarMembershipRequest, ...]
    candidate_count: int
    distinct_membership_request_count: int
    max_membership_requests: int
    all_market_snapshot_required: bool
    budget_semantics: str
    plan_hash: str
    human_attention_authority: str = SECTOR_RADAR_DAILY_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_DAILY_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarDailyPreparation:
    """Pure first phase: update market state, select entries, and plan acquisition.

    The object may contain an in-memory updated market state, but callers must persist
    it only after successful finalization. A budget-exceeded preparation is an
    auditable failed/degraded operation, never a partially enriched success.
    """

    schema_version: int
    prepared_at: datetime
    latest_cached_session: date
    next_completed_session_after_state: date
    market_session: date
    input_market_state_hash: str
    output_market_state_hash: str
    state_update_status: str
    catalog_hash: str
    benchmark_thscode: str
    qualified_snapshot_hash: str
    parent_hint_mapping_hash: str
    broad_entries: SectorRadarShadowStateEntries
    granular_entries: SectorRadarShadowStateEntries
    acquisition_plan: SectorRadarAcquisitionPlan
    preparation_hash: str
    state_update: SectorRadarStateUpdate
    snapshot_pair: SectorRadarStateSnapshotPair
    qualified_snapshot: HithinkQualifiedIndexSnapshotBatch
    catalog: HithinkIndustryCatalog
    artifact_semantics: str = SECTOR_RADAR_DAILY_ARTIFACT_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_DAILY_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_DAILY_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarDailyResult:
    schema_version: int
    produced_at: datetime
    market_session: date
    preparation_hash: str
    input_market_state_hash: str
    output_market_state_hash: str
    state_update_status: str
    catalog_hash: str
    benchmark_thscode: str
    qualified_snapshot_hash: str
    parent_hint_mapping_hash: str
    acquisition_plan: SectorRadarAcquisitionPlan
    broad_entries: SectorRadarShadowStateEntries
    granular_entries: SectorRadarShadowStateEntries
    parent_revalidations: tuple[SectorParentHintRevalidation, ...]
    breadth_observations: tuple[SectorCurrentBreadthObservation, ...]
    composition: SectorRadarShadowComposition
    previous_event_ledger_hash: str
    event_ledger_hash: str
    added_event_ids: tuple[str, ...]
    reused_event_ids: tuple[str, ...]
    event_count: int
    result_hash: str
    market_state: SectorRadarMarketState
    event_ledger: SectorRadarCandidateEventLedger
    artifact_semantics: str = SECTOR_RADAR_DAILY_ARTIFACT_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_DAILY_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_DAILY_INVESTMENT_AUTHORITY


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _require_positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _canonical_object(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _request_sort_key(request: SectorRadarMembershipRequest) -> tuple[Any, ...]:
    return (request.thscode, request.name, request.roles)


def _plan_payload_without_hash(
    plan: SectorRadarAcquisitionPlan,
) -> dict[str, Any]:
    return {
        "market_session": plan.market_session,
        "status": plan.status,
        "candidate_thscodes": plan.candidate_thscodes,
        "membership_requests": [
            asdict(request) for request in plan.membership_requests
        ],
        "candidate_count": plan.candidate_count,
        "distinct_membership_request_count": (
            plan.distinct_membership_request_count
        ),
        "max_membership_requests": plan.max_membership_requests,
        "all_market_snapshot_required": plan.all_market_snapshot_required,
        "budget_semantics": plan.budget_semantics,
        "human_attention_authority": plan.human_attention_authority,
        "investment_authority": plan.investment_authority,
    }


def _with_plan_hash(
    plan: SectorRadarAcquisitionPlan,
) -> SectorRadarAcquisitionPlan:
    return replace(plan, plan_hash=canonical_hash(_plan_payload_without_hash(plan)))


def _validate_plan(plan: SectorRadarAcquisitionPlan) -> None:
    if plan.status not in {
        PREPARATION_READY,
        PREPARATION_QUIET,
        PREPARATION_BUDGET_EXCEEDED,
    }:
        raise ValueError("Sector Radar acquisition plan status is unsupported")
    _require_positive_int(
        plan.max_membership_requests,
        field="Sector Radar max membership requests",
    )
    if plan.candidate_count != len(plan.candidate_thscodes):
        raise ValueError("Sector Radar plan candidate count disagrees")
    if len(set(plan.candidate_thscodes)) != len(plan.candidate_thscodes):
        raise ValueError("Sector Radar plan contains duplicate candidate identities")
    if plan.membership_requests != tuple(
        sorted(plan.membership_requests, key=_request_sort_key)
    ):
        raise ValueError("Sector Radar membership requests must be sorted")
    request_codes = [request.thscode for request in plan.membership_requests]
    if len(request_codes) != len(set(request_codes)):
        raise ValueError("Sector Radar plan contains duplicate membership requests")
    if plan.distinct_membership_request_count != len(plan.membership_requests):
        raise ValueError("Sector Radar membership request count disagrees")
    for request in plan.membership_requests:
        if not request.thscode or request.thscode != request.thscode.strip().upper():
            raise ValueError("Sector Radar membership request identity is invalid")
        if not request.name or request.name != request.name.strip():
            raise ValueError("Sector Radar membership request name is invalid")
        if not request.roles or request.roles != tuple(sorted(set(request.roles))):
            raise ValueError("Sector Radar membership request roles are invalid")
    if plan.budget_semantics != SECTOR_RADAR_DAILY_ACQUISITION_BUDGET_SEMANTICS:
        raise ValueError("Sector Radar acquisition-budget semantics disagree")
    if plan.human_attention_authority != "NONE":
        raise ValueError("Sector Radar plan cannot carry Human attention authority")
    if plan.investment_authority != "NONE":
        raise ValueError("Sector Radar plan cannot carry investment authority")

    if not plan.candidate_thscodes:
        if plan.status != PREPARATION_QUIET:
            raise ValueError("empty Sector Radar candidate plan must be quiet")
        if plan.membership_requests or plan.all_market_snapshot_required:
            raise ValueError("quiet Sector Radar plan must not request live enrichment")
    else:
        if not plan.all_market_snapshot_required:
            raise ValueError("candidate plan requires one all-market snapshot")
        if plan.status == PREPARATION_READY:
            if len(plan.membership_requests) > plan.max_membership_requests:
                raise ValueError("ready Sector Radar plan exceeds its operations budget")
        elif plan.status == PREPARATION_BUDGET_EXCEEDED:
            if len(plan.membership_requests) <= plan.max_membership_requests:
                raise ValueError("budget-exceeded Sector Radar plan is within budget")
        else:
            raise ValueError("non-empty Sector Radar candidate plan cannot be quiet")
    if plan.plan_hash != canonical_hash(_plan_payload_without_hash(plan)):
        raise ValueError("Sector Radar acquisition plan hash mismatch")


def _preparation_payload_without_hash(
    preparation: SectorRadarDailyPreparation,
) -> dict[str, Any]:
    return {
        "schema_version": preparation.schema_version,
        "prepared_at": preparation.prepared_at,
        "latest_cached_session": preparation.latest_cached_session,
        "next_completed_session_after_state": (
            preparation.next_completed_session_after_state
        ),
        "market_session": preparation.market_session,
        "input_market_state_hash": preparation.input_market_state_hash,
        "output_market_state_hash": preparation.output_market_state_hash,
        "state_update_status": preparation.state_update_status,
        "catalog_hash": preparation.catalog_hash,
        "benchmark_thscode": preparation.benchmark_thscode,
        "qualified_snapshot_hash": preparation.qualified_snapshot_hash,
        "parent_hint_mapping_hash": preparation.parent_hint_mapping_hash,
        "broad_entries": asdict(preparation.broad_entries),
        "granular_entries": asdict(preparation.granular_entries),
        "acquisition_plan": {
            **_plan_payload_without_hash(preparation.acquisition_plan),
            "plan_hash": preparation.acquisition_plan.plan_hash,
        },
        "artifact_semantics": preparation.artifact_semantics,
        "human_attention_authority": preparation.human_attention_authority,
        "investment_authority": preparation.investment_authority,
    }


def _with_preparation_hash(
    preparation: SectorRadarDailyPreparation,
) -> SectorRadarDailyPreparation:
    return replace(
        preparation,
        preparation_hash=canonical_hash(
            _preparation_payload_without_hash(preparation)
        ),
    )


def _validate_preparation(preparation: SectorRadarDailyPreparation) -> None:
    if preparation.schema_version != SECTOR_RADAR_DAILY_SCHEMA_VERSION:
        raise ValueError("unsupported Sector Radar daily schema version")
    _require_aware(preparation.prepared_at, field="preparation prepared_at")
    if (
        preparation.next_completed_session_after_state
        <= preparation.latest_cached_session
    ):
        raise ValueError("next completed session must follow the cached session")
    if preparation.state_update_status not in {
        STATE_UPDATE_APPENDED,
        STATE_UPDATE_ALREADY_CURRENT,
    }:
        raise ValueError("Sector Radar preparation state-update status is invalid")
    if (
        preparation.state_update.previous_state_hash
        != preparation.input_market_state_hash
    ):
        raise ValueError("Sector Radar preparation input state hash disagrees")
    if (
        preparation.state_update.state.state_hash
        != preparation.output_market_state_hash
    ):
        raise ValueError("Sector Radar preparation output state hash disagrees")
    if preparation.snapshot_pair.state_hash != preparation.output_market_state_hash:
        raise ValueError("Sector Radar preparation snapshot-pair state hash disagrees")
    if preparation.qualified_snapshot.market_session != preparation.market_session:
        raise ValueError("Sector Radar preparation snapshot session disagrees")
    if preparation.catalog.catalog_hash != preparation.catalog_hash:
        raise ValueError("Sector Radar preparation catalog hash disagrees")
    if preparation.snapshot_pair.current_session != preparation.market_session:
        raise ValueError("Sector Radar preparation pair session disagrees")
    if preparation.broad_entries.family != BROAD_881:
        raise ValueError("Sector Radar preparation broad entries are mislabelled")
    if preparation.granular_entries.family != GRANULAR_884:
        raise ValueError("Sector Radar preparation granular entries are mislabelled")
    if (
        preparation.broad_entries.as_of_session != preparation.market_session
        or preparation.granular_entries.as_of_session != preparation.market_session
    ):
        raise ValueError("Sector Radar preparation entry session disagrees")
    if (
        preparation.broad_entries.benchmark_thscode
        != preparation.benchmark_thscode
        or preparation.granular_entries.benchmark_thscode
        != preparation.benchmark_thscode
    ):
        raise ValueError("Sector Radar preparation benchmark disagrees")
    _validate_plan(preparation.acquisition_plan)
    if preparation.acquisition_plan.market_session != preparation.market_session:
        raise ValueError("Sector Radar preparation plan session disagrees")
    if preparation.artifact_semantics != SECTOR_RADAR_DAILY_ARTIFACT_SEMANTICS:
        raise ValueError("Sector Radar preparation semantics disagree")
    if preparation.human_attention_authority != "NONE":
        raise ValueError("Sector Radar preparation cannot carry Human attention authority")
    if preparation.investment_authority != "NONE":
        raise ValueError("Sector Radar preparation cannot carry investment authority")
    if preparation.preparation_hash != canonical_hash(
        _preparation_payload_without_hash(preparation)
    ):
        raise ValueError("Sector Radar preparation hash mismatch")


def _build_acquisition_plan(
    *,
    market_session: date,
    broad_entries: SectorRadarShadowStateEntries,
    granular_entries: SectorRadarShadowStateEntries,
    parent_hints: SectorParentHintIndex,
    max_membership_requests: int,
) -> SectorRadarAcquisitionPlan:
    request_names: dict[str, str] = {}
    request_roles: dict[str, set[str]] = {}

    def add_request(*, thscode: str, name: str, role: str) -> None:
        previous_name = request_names.setdefault(thscode, name)
        if previous_name != name:
            raise ValueError(
                f"Sector Radar acquisition identity name disagrees for {thscode}"
            )
        request_roles.setdefault(thscode, set()).add(role)

    all_candidates = broad_entries.candidates + granular_entries.candidates
    candidate_thscodes = tuple(candidate.thscode for candidate in all_candidates)
    if len(set(candidate_thscodes)) != len(candidate_thscodes):
        raise ValueError("Sector Radar daily entries contain duplicate candidates")

    for candidate in broad_entries.candidates:
        add_request(
            thscode=candidate.thscode,
            name=candidate.name,
            role=CANDIDATE_BREADTH_ROLE,
        )
    for candidate in granular_entries.candidates:
        add_request(
            thscode=candidate.thscode,
            name=candidate.name,
            role=CANDIDATE_BREADTH_ROLE,
        )
        add_request(
            thscode=candidate.thscode,
            name=candidate.name,
            role=GRANULAR_CHILD_REVALIDATION_ROLE,
        )
        hint = sector_parent_hint_for_child(
            parent_hints,
            child_thscode=candidate.thscode,
        )
        add_request(
            thscode=hint.parent_thscode,
            name=hint.parent_name,
            role=HINTED_PARENT_REVALIDATION_ROLE,
        )

    requests = tuple(
        sorted(
            (
                SectorRadarMembershipRequest(
                    thscode=thscode,
                    name=request_names[thscode],
                    roles=tuple(sorted(request_roles[thscode])),
                )
                for thscode in request_names
            ),
            key=_request_sort_key,
        )
    )
    if not all_candidates:
        status = PREPARATION_QUIET
    elif len(requests) > max_membership_requests:
        status = PREPARATION_BUDGET_EXCEEDED
    else:
        status = PREPARATION_READY

    plan = SectorRadarAcquisitionPlan(
        market_session=market_session,
        status=status,
        candidate_thscodes=candidate_thscodes,
        membership_requests=requests,
        candidate_count=len(all_candidates),
        distinct_membership_request_count=len(requests),
        max_membership_requests=max_membership_requests,
        all_market_snapshot_required=bool(all_candidates),
        budget_semantics=SECTOR_RADAR_DAILY_ACQUISITION_BUDGET_SEMANTICS,
        plan_hash="",
    )
    plan = _with_plan_hash(plan)
    _validate_plan(plan)
    return plan


def prepare_sector_radar_daily_run(
    *,
    market_state: SectorRadarMarketState,
    catalog: HithinkIndustryCatalog,
    qualified_snapshot: HithinkQualifiedIndexSnapshotBatch,
    parent_hints: SectorParentHintIndex,
    prepared_at: datetime,
    next_completed_session_after_state: date,
    max_membership_requests: int = (
        SECTOR_RADAR_DAILY_DEFAULT_MAX_MEMBERSHIP_REQUESTS
    ),
) -> SectorRadarDailyPreparation:
    """Compute state entries and an exact enrichment plan without any I/O."""

    _require_aware(prepared_at, field="Sector Radar daily prepared_at")
    _require_positive_int(
        max_membership_requests,
        field="Sector Radar max membership requests",
    )
    latest_cached_session = market_state.sessions[-1]
    if next_completed_session_after_state <= latest_cached_session:
        raise ValueError(
            "next completed session after state must follow the cached session"
        )
    if (
        qualified_snapshot.market_session > latest_cached_session
        and qualified_snapshot.market_session
        != next_completed_session_after_state
    ):
        raise ValueError(
            "qualified Sector Radar snapshot is not the direct next completed "
            "session after cached state"
        )

    catalog_validation = validate_sector_parent_hint_catalog(
        hints=parent_hints,
        catalog=catalog,
    )
    state_update = append_qualified_sector_snapshot(
        state=market_state,
        catalog=catalog,
        snapshot=qualified_snapshot,
        observed_at=prepared_at,
    )
    pair = calculate_sector_radar_state_snapshot_pair(state_update.state)
    broad_entries = select_sector_radar_state_entries(
        current=pair.broad_current,
        previous=pair.broad_previous,
    )
    granular_entries = select_sector_radar_state_entries(
        current=pair.granular_current,
        previous=pair.granular_previous,
    )
    plan = _build_acquisition_plan(
        market_session=pair.current_session,
        broad_entries=broad_entries,
        granular_entries=granular_entries,
        parent_hints=parent_hints,
        max_membership_requests=max_membership_requests,
    )
    preparation = SectorRadarDailyPreparation(
        schema_version=SECTOR_RADAR_DAILY_SCHEMA_VERSION,
        prepared_at=prepared_at,
        latest_cached_session=latest_cached_session,
        next_completed_session_after_state=next_completed_session_after_state,
        market_session=pair.current_session,
        input_market_state_hash=market_state.state_hash,
        output_market_state_hash=state_update.state.state_hash,
        state_update_status=state_update.status,
        catalog_hash=catalog.catalog_hash,
        benchmark_thscode=state_update.state.benchmark_thscode,
        qualified_snapshot_hash=canonical_hash(asdict(qualified_snapshot)),
        parent_hint_mapping_hash=catalog_validation.mapping_hash,
        broad_entries=broad_entries,
        granular_entries=granular_entries,
        acquisition_plan=plan,
        preparation_hash="",
        state_update=state_update,
        snapshot_pair=pair,
        qualified_snapshot=qualified_snapshot,
        catalog=catalog,
    )
    preparation = _with_preparation_hash(preparation)
    _validate_preparation(preparation)
    return preparation


def serialize_sector_radar_daily_preparation(
    preparation: SectorRadarDailyPreparation,
) -> str:
    _validate_preparation(preparation)
    payload = _preparation_payload_without_hash(preparation)
    payload["preparation_hash"] = preparation.preparation_hash
    return json.dumps(
        _canonical_object(payload),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_sector_radar_daily_preparation_markdown(
    preparation: SectorRadarDailyPreparation,
) -> str:
    _validate_preparation(preparation)
    plan = preparation.acquisition_plan
    lines = [
        f"## Sector Discovery Radar preparation — {preparation.market_session.isoformat()}",
        "",
        "**SHADOW OBSERVATION ONLY**",
        "",
        "`NOT RESEARCH` · `NOT A RECOMMENDATION`",
        "",
        "`HUMAN ATTENTION AUTHORITY = NONE` · `INVESTMENT AUTHORITY = NONE`",
        "",
        f"Operations state: `{plan.status}`",
        "",
        f"New false→true candidates: **{plan.candidate_count}**",
        "",
        (
            "Distinct current-membership requests: "
            f"**{plan.distinct_membership_request_count} / "
            f"{plan.max_membership_requests}**"
        ),
        "",
        f"Preparation hash: `{preparation.preparation_hash}`",
    ]
    if plan.status == PREPARATION_BUDGET_EXCEEDED:
        lines.extend(
            [
                "",
                "The operations-only acquisition budget was exceeded.",
                "",
                "No candidate was silently truncated, no incomplete breadth "
                "composition was produced, and the in-memory market-state update "
                "must not be persisted as a successful run.",
            ]
        )
    elif plan.status == PREPARATION_QUIET:
        lines.extend(
            [
                "",
                "No new qualified state entry requires current-membership or "
                "all-market enrichment.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "The exact acquisition plan is ready for current membership, "
                "candidate-time containment revalidation, and one same-session "
                "all-A-share snapshot.",
            ]
        )
    return "\n".join(lines) + "\n"


def _membership_by_code(
    memberships: Sequence[SectorMembershipSnapshot],
) -> dict[str, SectorMembershipSnapshot]:
    by_code = {membership.sector_thscode: membership for membership in memberships}
    if len(by_code) != len(tuple(memberships)):
        raise ValueError("Sector Radar daily run contains duplicate memberships")
    return by_code


def _candidate_sequence(
    preparation: SectorRadarDailyPreparation,
) -> tuple[SectorRadarShadowCandidate, ...]:
    return (
        preparation.broad_entries.candidates
        + preparation.granular_entries.candidates
    )


def _validate_enrichment_inputs(
    *,
    preparation: SectorRadarDailyPreparation,
    memberships: Sequence[SectorMembershipSnapshot],
    constituent_points: Sequence[ConstituentMarketPoint],
) -> dict[str, SectorMembershipSnapshot]:
    expected_codes = tuple(
        request.thscode
        for request in preparation.acquisition_plan.membership_requests
    )
    by_code = _membership_by_code(memberships)
    if set(by_code) != set(expected_codes):
        missing = sorted(set(expected_codes) - set(by_code))
        extra = sorted(set(by_code) - set(expected_codes))
        raise ValueError(
            "Sector Radar daily membership inputs disagree with the exact plan; "
            f"missing={missing}; extra={extra}"
        )
    expected_names = {
        request.thscode: request.name
        for request in preparation.acquisition_plan.membership_requests
    }
    for code, membership in by_code.items():
        if membership.sector_name != expected_names[code]:
            raise ValueError(
                f"Sector Radar daily membership name disagrees for {code}"
            )

    if preparation.acquisition_plan.status == PREPARATION_QUIET:
        if memberships or constituent_points:
            raise ValueError(
                "quiet Sector Radar preparation must not receive live enrichment"
            )
    elif preparation.acquisition_plan.status == PREPARATION_READY:
        if not constituent_points:
            raise ValueError(
                "candidate Sector Radar preparation requires an all-market snapshot"
            )
    else:
        raise ValueError(
            "budget-exceeded Sector Radar preparation cannot be finalized"
        )
    return by_code


def _result_payload_without_hash(
    result: SectorRadarDailyResult,
) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "produced_at": result.produced_at,
        "market_session": result.market_session,
        "preparation_hash": result.preparation_hash,
        "input_market_state_hash": result.input_market_state_hash,
        "output_market_state_hash": result.output_market_state_hash,
        "state_update_status": result.state_update_status,
        "catalog_hash": result.catalog_hash,
        "benchmark_thscode": result.benchmark_thscode,
        "qualified_snapshot_hash": result.qualified_snapshot_hash,
        "parent_hint_mapping_hash": result.parent_hint_mapping_hash,
        "acquisition_plan": {
            **_plan_payload_without_hash(result.acquisition_plan),
            "plan_hash": result.acquisition_plan.plan_hash,
        },
        "broad_entries": asdict(result.broad_entries),
        "granular_entries": asdict(result.granular_entries),
        "parent_revalidations": [
            asdict(item) for item in result.parent_revalidations
        ],
        "breadth_observations": [
            asdict(item) for item in result.breadth_observations
        ],
        "composition": asdict(result.composition),
        "event_ledger_update": {
            "previous_event_ledger_hash": result.previous_event_ledger_hash,
            "event_ledger_hash": result.event_ledger_hash,
            "added_event_ids": result.added_event_ids,
            "reused_event_ids": result.reused_event_ids,
            "event_count": result.event_count,
        },
        "artifact_semantics": result.artifact_semantics,
        "human_attention_authority": result.human_attention_authority,
        "investment_authority": result.investment_authority,
    }


def _with_result_hash(result: SectorRadarDailyResult) -> SectorRadarDailyResult:
    return replace(
        result,
        result_hash=canonical_hash(_result_payload_without_hash(result)),
    )


def _validate_result(result: SectorRadarDailyResult) -> None:
    if result.schema_version != SECTOR_RADAR_DAILY_SCHEMA_VERSION:
        raise ValueError("unsupported Sector Radar daily result schema")
    _require_aware(result.produced_at, field="Sector Radar result produced_at")
    _validate_plan(result.acquisition_plan)
    if result.market_state.state_hash != result.output_market_state_hash:
        raise ValueError("Sector Radar result market-state hash disagrees")
    if result.event_ledger.ledger_hash != result.event_ledger_hash:
        raise ValueError("Sector Radar result event-ledger hash disagrees")
    if result.event_count != len(result.event_ledger.events):
        raise ValueError("Sector Radar result event count disagrees")
    if result.composition.as_of_session != result.market_session:
        raise ValueError("Sector Radar result composition session disagrees")
    if result.artifact_semantics != SECTOR_RADAR_DAILY_ARTIFACT_SEMANTICS:
        raise ValueError("Sector Radar result semantics disagree")
    if result.human_attention_authority != "NONE":
        raise ValueError("Sector Radar result cannot carry Human attention authority")
    if result.investment_authority != "NONE":
        raise ValueError("Sector Radar result cannot carry investment authority")
    if result.result_hash != canonical_hash(_result_payload_without_hash(result)):
        raise ValueError("Sector Radar daily result hash mismatch")


def finalize_sector_radar_daily_run(
    *,
    preparation: SectorRadarDailyPreparation,
    parent_hints: SectorParentHintIndex,
    memberships: Sequence[SectorMembershipSnapshot],
    constituent_points: Sequence[ConstituentMarketPoint],
    event_ledger: SectorRadarCandidateEventLedger,
    produced_at: datetime,
    max_surfaced_groups: int = SECTOR_RADAR_SHADOW_MAX_SURFACED_GROUPS,
) -> SectorRadarDailyResult:
    """Finalize one pure daily run from inputs acquired exactly from its plan."""

    _validate_preparation(preparation)
    _require_aware(produced_at, field="Sector Radar daily produced_at")
    if produced_at < preparation.prepared_at:
        raise ValueError("Sector Radar result predates its preparation")
    if max_surfaced_groups < 0:
        raise ValueError("Sector Radar max surfaced groups must be non-negative")
    if parent_hints.mapping_hash != preparation.parent_hint_mapping_hash:
        raise ValueError("Sector Radar parent-hint mapping changed after preparation")

    membership_by_code = _validate_enrichment_inputs(
        preparation=preparation,
        memberships=memberships,
        constituent_points=constituent_points,
    )
    snapshot_by_code = {
        point.thscode: point for point in preparation.qualified_snapshot.points
    }
    candidates = _candidate_sequence(preparation)

    breadth_observations: list[SectorCurrentBreadthObservation] = []
    for candidate in candidates:
        membership = membership_by_code[candidate.thscode]
        index_point = snapshot_by_code[candidate.thscode]
        breadth_observations.append(
            calculate_current_sector_breadth(
                membership=membership,
                market_session=preparation.market_session,
                observed_at=produced_at,
                sector_last_price=index_point.last_price,
                sector_prev_price=index_point.prev_price,
                constituent_points=constituent_points,
            )
        )

    parent_revalidations: list[SectorParentHintRevalidation] = []
    for candidate in preparation.granular_entries.candidates:
        hint = sector_parent_hint_for_child(
            parent_hints,
            child_thscode=candidate.thscode,
        )
        parent_revalidations.append(
            revalidate_current_sector_parent_hint(
                hints=parent_hints,
                catalog=preparation.catalog,
                child_thscode=candidate.thscode,
                child_membership=membership_by_code[candidate.thscode],
                parent_membership=membership_by_code[hint.parent_thscode],
            )
        )

    composition = compose_sector_radar_shadow(
        broad_entries=preparation.broad_entries,
        granular_entries=preparation.granular_entries,
        breadth_observations=tuple(breadth_observations),
        parent_links=tuple(
            item.current_parent_link for item in parent_revalidations
        ),
        max_surfaced_groups=max_surfaced_groups,
    )
    ledger_update = append_sector_radar_candidate_events(
        ledger=event_ledger,
        composition=composition,
        source_market_state_hash=preparation.output_market_state_hash,
        catalog_hash=preparation.catalog_hash,
        parent_hint_mapping_hash=preparation.parent_hint_mapping_hash,
        benchmark_thscode=preparation.benchmark_thscode,
        formula_version=preparation.broad_entries.formula_version,
        recorded_at=produced_at,
    )
    result = SectorRadarDailyResult(
        schema_version=SECTOR_RADAR_DAILY_SCHEMA_VERSION,
        produced_at=produced_at,
        market_session=preparation.market_session,
        preparation_hash=preparation.preparation_hash,
        input_market_state_hash=preparation.input_market_state_hash,
        output_market_state_hash=preparation.output_market_state_hash,
        state_update_status=preparation.state_update_status,
        catalog_hash=preparation.catalog_hash,
        benchmark_thscode=preparation.benchmark_thscode,
        qualified_snapshot_hash=preparation.qualified_snapshot_hash,
        parent_hint_mapping_hash=preparation.parent_hint_mapping_hash,
        acquisition_plan=preparation.acquisition_plan,
        broad_entries=preparation.broad_entries,
        granular_entries=preparation.granular_entries,
        parent_revalidations=tuple(parent_revalidations),
        breadth_observations=tuple(breadth_observations),
        composition=composition,
        previous_event_ledger_hash=ledger_update.previous_ledger_hash,
        event_ledger_hash=ledger_update.ledger.ledger_hash,
        added_event_ids=ledger_update.added_event_ids,
        reused_event_ids=ledger_update.reused_event_ids,
        event_count=len(ledger_update.ledger.events),
        result_hash="",
        market_state=preparation.state_update.state,
        event_ledger=ledger_update.ledger,
    )
    result = _with_result_hash(result)
    _validate_result(result)
    return result


def serialize_sector_radar_daily_result(result: SectorRadarDailyResult) -> str:
    _validate_result(result)
    payload = _result_payload_without_hash(result)
    payload["result_hash"] = result.result_hash
    return json.dumps(
        _canonical_object(payload),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_sector_radar_daily_result(
    path: Path,
    result: SectorRadarDailyResult,
) -> None:
    serialized = serialize_sector_radar_daily_result(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _percent(value: Decimal) -> str:
    return f"{value * Decimal(100):.2f}%"


def _ratio(value: Decimal | None) -> str:
    return "unavailable" if value is None else f"{value:.2f}x"


def render_sector_radar_daily_summary(
    result: SectorRadarDailyResult,
) -> str:
    # Presentation only: serialize validates the original result/state/ledger.
    # Keep detector, composition order, 0-3 budget and result JSON unchanged.
    from .sector_radar_discovery import render_sector_radar_discovery

    return render_sector_radar_discovery(
        json.loads(serialize_sector_radar_daily_result(result))
    )
