from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence

from .sector_breadth import (
    SectorCurrentBreadthObservation,
    SectorMembershipSnapshot,
    calculate_current_membership_overlap,
)
from .sector_radar import SectorRadarObservation, SectorRadarSnapshot


SECTOR_RADAR_SHADOW_POLICY_VERSION = "sector-shadow-state-entry-hierarchy-v0"
SECTOR_RADAR_SHADOW_SEMANTICS = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
SECTOR_RADAR_SHADOW_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_SHADOW_INVESTMENT_AUTHORITY = "NONE"
SECTOR_RADAR_SHADOW_MAX_SURFACED_GROUPS = 3

BROAD_881 = "BROAD_881"
GRANULAR_884 = "GRANULAR_884"
PERSISTENT_TOP_DECILE = "PERSISTENT_TOP_DECILE_ENTRY"
ACCELERATING = "ACCELERATING_ENTRY"
ACCELERATING_AND_PERSISTENT = "ACCELERATING_AND_PERSISTENT_ENTRY"

_BROAD_CODE = re.compile(r"^881\d{3}\.TI$")
_GRANULAR_CODE = re.compile(r"^884\d{3}\.TI$")


@dataclass(frozen=True)
class SectorRadarShadowCandidate:
    """One false-to-true price-path state entry for shadow evaluation only."""

    thscode: str
    name: str
    family: str
    as_of_session: date
    event_type: str
    horizon_5_rank: Decimal
    horizon_5_rating: int
    horizon_20_rank: Decimal
    horizon_20_rating: int
    horizon_60_rating: int
    horizon_5_excess_return: Decimal
    horizon_20_excess_return: Decimal
    horizon_60_excess_return: Decimal
    rank_change_5_sessions_20d: Decimal
    excess_acceleration_5_sessions_20d: Decimal
    positive_20d_excess_persistence_sessions: int
    top_quartile_20d_persistence_sessions: int
    turnover_pulse_5_vs_prior_20: Decimal | None
    persistent_gate_entered: bool
    acceleration_gate_entered: bool


@dataclass(frozen=True)
class SectorRadarShadowStateEntries:
    """All state entries from one homogeneous 881 or 884 universe."""

    policy_version: str
    family: str
    as_of_session: date
    previous_session: date | None
    benchmark_thscode: str
    formula_version: str
    candidates: tuple[SectorRadarShadowCandidate, ...]
    quiet_reason: str | None
    shadow_semantics: str = SECTOR_RADAR_SHADOW_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_SHADOW_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_SHADOW_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarCurrentParentLink:
    """One explicit current parent-child relationship backed by exact memberships."""

    parent_thscode: str
    parent_name: str
    parent_member_count: int
    parent_constituent_set_hash: str
    parent_membership_captured_at: datetime
    child_thscode: str
    child_name: str
    child_member_count: int
    child_constituent_set_hash: str
    child_membership_captured_at: datetime
    intersection_count: int
    jaccard: Decimal
    child_fully_contained: bool
    relation_semantics: str = "CURRENT_CONSTITUENT_PARENT_LINK_ONLY"
    historical_membership_authority: str = "NONE"
    human_attention_authority: str = "NONE"
    investment_authority: str = "NONE"


@dataclass(frozen=True)
class SectorRadarShadowGroup:
    """One Human-compressed shadow group with all child drivers retained."""

    group_key: str
    primary_candidate: SectorRadarShadowCandidate
    primary_breadth: SectorCurrentBreadthObservation
    parent_context_thscode: str | None
    parent_context_name: str | None
    granular_drivers: tuple[SectorRadarShadowCandidate, ...]
    granular_driver_breadth: tuple[SectorCurrentBreadthObservation, ...]
    all_candidates: tuple[SectorRadarShadowCandidate, ...]
    grouping_reason: str
    shadow_semantics: str = SECTOR_RADAR_SHADOW_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_SHADOW_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_SHADOW_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarShadowComposition:
    """Deterministic 0-3 shadow summary plus the complete auditable group set."""

    policy_version: str
    as_of_session: date
    all_candidates: tuple[SectorRadarShadowCandidate, ...]
    all_groups: tuple[SectorRadarShadowGroup, ...]
    surfaced_groups: tuple[SectorRadarShadowGroup, ...]
    omitted_groups: tuple[SectorRadarShadowGroup, ...]
    truncated_group_count: int
    quiet_reason: str | None
    shadow_semantics: str = SECTOR_RADAR_SHADOW_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_SHADOW_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_SHADOW_INVESTMENT_AUTHORITY


def _persistent_gate(observation: SectorRadarObservation) -> bool:
    return (
        observation.horizon_20.cross_sectional_rating >= 90
        and observation.horizon_20.excess_return > 0
        and observation.positive_20d_excess_persistence_sessions >= 5
    )


def _acceleration_gate(observation: SectorRadarObservation) -> bool:
    return (
        observation.horizon_5.cross_sectional_rating >= 90
        and observation.rank_change_5_sessions_20d >= Decimal(20)
        and observation.excess_acceleration_5_sessions_20d > 0
        and observation.horizon_20.excess_return > 0
        and observation.positive_20d_excess_persistence_sessions >= 5
        and observation.turnover_pulse_5_vs_prior_20 is not None
        and observation.turnover_pulse_5_vs_prior_20 >= Decimal("1.2")
    )


def _family_for_codes(codes: Sequence[str]) -> str:
    if not codes:
        raise ValueError("Sector Radar shadow requires a non-empty universe")
    if all(_BROAD_CODE.fullmatch(code) for code in codes):
        return BROAD_881
    if all(_GRANULAR_CODE.fullmatch(code) for code in codes):
        return GRANULAR_884
    raise ValueError("Sector Radar shadow universe must be homogeneous 881 or 884")


def _validate_snapshot_pair(
    *,
    current: SectorRadarSnapshot,
    previous: SectorRadarSnapshot,
) -> tuple[
    str,
    dict[str, SectorRadarObservation],
    dict[str, SectorRadarObservation],
]:
    if current.formula_version != previous.formula_version:
        raise ValueError("Sector Radar shadow snapshots use different formula versions")
    if current.benchmark_thscode != previous.benchmark_thscode:
        raise ValueError("Sector Radar shadow snapshots use different benchmarks")
    if current.as_of_session <= previous.as_of_session:
        raise ValueError("Sector Radar shadow current session must follow previous session")
    if current.exclusions or previous.exclusions:
        raise ValueError("Sector Radar shadow requires complete, exclusion-free snapshots")

    current_by_code = {item.thscode: item for item in current.observations}
    previous_by_code = {item.thscode: item for item in previous.observations}
    if len(current_by_code) != len(current.observations):
        raise ValueError("Sector Radar shadow current snapshot contains duplicate identities")
    if len(previous_by_code) != len(previous.observations):
        raise ValueError("Sector Radar shadow previous snapshot contains duplicate identities")
    if set(current_by_code) != set(previous_by_code):
        raise ValueError("Sector Radar shadow universe changed between snapshots")
    if any(item.as_of_session != current.as_of_session for item in current.observations):
        raise ValueError("Sector Radar shadow current observation session mismatch")
    if any(item.as_of_session != previous.as_of_session for item in previous.observations):
        raise ValueError("Sector Radar shadow previous observation session mismatch")
    if any(
        current_by_code[code].name != previous_by_code[code].name
        for code in current_by_code
    ):
        raise ValueError("Sector Radar shadow universe names changed between snapshots")

    family = _family_for_codes(tuple(sorted(current_by_code)))
    return family, current_by_code, previous_by_code


def _candidate(
    observation: SectorRadarObservation,
    *,
    family: str,
    persistent_entered: bool,
    acceleration_entered: bool,
) -> SectorRadarShadowCandidate:
    if acceleration_entered and persistent_entered:
        event_type = ACCELERATING_AND_PERSISTENT
    elif acceleration_entered:
        event_type = ACCELERATING
    elif persistent_entered:
        event_type = PERSISTENT_TOP_DECILE
    else:
        raise ValueError("Sector Radar shadow candidate requires a state-entry event")

    return SectorRadarShadowCandidate(
        thscode=observation.thscode,
        name=observation.name,
        family=family,
        as_of_session=observation.as_of_session,
        event_type=event_type,
        horizon_5_rank=observation.horizon_5.cross_sectional_rank,
        horizon_5_rating=observation.horizon_5.cross_sectional_rating,
        horizon_20_rank=observation.horizon_20.cross_sectional_rank,
        horizon_20_rating=observation.horizon_20.cross_sectional_rating,
        horizon_60_rating=observation.horizon_60.cross_sectional_rating,
        horizon_5_excess_return=observation.horizon_5.excess_return,
        horizon_20_excess_return=observation.horizon_20.excess_return,
        horizon_60_excess_return=observation.horizon_60.excess_return,
        rank_change_5_sessions_20d=observation.rank_change_5_sessions_20d,
        excess_acceleration_5_sessions_20d=(
            observation.excess_acceleration_5_sessions_20d
        ),
        positive_20d_excess_persistence_sessions=(
            observation.positive_20d_excess_persistence_sessions
        ),
        top_quartile_20d_persistence_sessions=(
            observation.top_quartile_20d_persistence_sessions
        ),
        turnover_pulse_5_vs_prior_20=observation.turnover_pulse_5_vs_prior_20,
        persistent_gate_entered=persistent_entered,
        acceleration_gate_entered=acceleration_entered,
    )


def _candidate_priority(candidate: SectorRadarShadowCandidate) -> tuple:
    if candidate.acceleration_gate_entered:
        return (
            0,
            candidate.horizon_5_rank,
            -candidate.rank_change_5_sessions_20d,
            candidate.horizon_20_rank,
            candidate.thscode,
        )
    return (
        1,
        candidate.horizon_20_rank,
        Decimal(0),
        candidate.horizon_5_rank,
        candidate.thscode,
    )


def select_sector_radar_state_entries(
    *,
    current: SectorRadarSnapshot,
    previous: SectorRadarSnapshot | None,
) -> SectorRadarShadowStateEntries:
    """Emit false-to-true entries only; unchanged strong sectors stay quiet."""

    current_codes = tuple(item.thscode for item in current.observations)
    family = _family_for_codes(current_codes)
    if current.exclusions:
        raise ValueError("Sector Radar shadow current snapshot must be complete")

    if previous is None:
        return SectorRadarShadowStateEntries(
            policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
            family=family,
            as_of_session=current.as_of_session,
            previous_session=None,
            benchmark_thscode=current.benchmark_thscode,
            formula_version=current.formula_version,
            candidates=(),
            quiet_reason="NO_PREVIOUS_COMPLETED_SNAPSHOT",
        )

    family, current_by_code, previous_by_code = _validate_snapshot_pair(
        current=current,
        previous=previous,
    )
    candidates: list[SectorRadarShadowCandidate] = []
    for thscode in sorted(current_by_code):
        observation = current_by_code[thscode]
        prior = previous_by_code[thscode]
        persistent_entered = _persistent_gate(observation) and not _persistent_gate(
            prior
        )
        acceleration_entered = _acceleration_gate(observation) and not _acceleration_gate(
            prior
        )
        if persistent_entered or acceleration_entered:
            candidates.append(
                _candidate(
                    observation,
                    family=family,
                    persistent_entered=persistent_entered,
                    acceleration_entered=acceleration_entered,
                )
            )

    candidates.sort(key=_candidate_priority)
    return SectorRadarShadowStateEntries(
        policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
        family=family,
        as_of_session=current.as_of_session,
        previous_session=previous.as_of_session,
        benchmark_thscode=current.benchmark_thscode,
        formula_version=current.formula_version,
        candidates=tuple(candidates),
        quiet_reason=None if candidates else "NO_NEW_QUALIFIED_STATE_ENTRY",
    )


def build_current_parent_link(
    *,
    parent: SectorMembershipSnapshot,
    child: SectorMembershipSnapshot,
) -> SectorRadarCurrentParentLink:
    """Build one explicit 881-parent / 884-child link from current memberships."""

    if not _BROAD_CODE.fullmatch(parent.sector_thscode):
        raise ValueError("Sector Radar parent link requires an 881 parent")
    if not _GRANULAR_CODE.fullmatch(child.sector_thscode):
        raise ValueError("Sector Radar parent link requires an 884 child")
    overlap = calculate_current_membership_overlap(left=parent, right=child)
    return SectorRadarCurrentParentLink(
        parent_thscode=parent.sector_thscode,
        parent_name=parent.sector_name,
        parent_member_count=len(parent.members),
        parent_constituent_set_hash=parent.constituent_set_hash,
        parent_membership_captured_at=parent.captured_at,
        child_thscode=child.sector_thscode,
        child_name=child.sector_name,
        child_member_count=len(child.members),
        child_constituent_set_hash=child.constituent_set_hash,
        child_membership_captured_at=child.captured_at,
        intersection_count=overlap.intersection_count,
        jaccard=overlap.jaccard,
        child_fully_contained=overlap.left_contains_right,
    )


def _validate_composition_inputs(
    *,
    broad_entries: SectorRadarShadowStateEntries,
    granular_entries: SectorRadarShadowStateEntries,
    breadth_observations: Sequence[SectorCurrentBreadthObservation],
    parent_links: Sequence[SectorRadarCurrentParentLink],
) -> tuple[
    tuple[SectorRadarShadowCandidate, ...],
    dict[str, SectorCurrentBreadthObservation],
    dict[str, SectorRadarCurrentParentLink],
]:
    if broad_entries.family != BROAD_881:
        raise ValueError("Sector Radar composition requires an 881 broad entry set")
    if granular_entries.family != GRANULAR_884:
        raise ValueError("Sector Radar composition requires an 884 granular entry set")
    if broad_entries.as_of_session != granular_entries.as_of_session:
        raise ValueError("Sector Radar composition entry sessions disagree")
    if broad_entries.policy_version != granular_entries.policy_version:
        raise ValueError("Sector Radar composition policy versions disagree")
    if broad_entries.formula_version != granular_entries.formula_version:
        raise ValueError("Sector Radar composition formula versions disagree")
    if broad_entries.benchmark_thscode != granular_entries.benchmark_thscode:
        raise ValueError("Sector Radar composition benchmarks disagree")

    all_candidates = broad_entries.candidates + granular_entries.candidates
    by_candidate = {item.thscode: item for item in all_candidates}
    if len(by_candidate) != len(all_candidates):
        raise ValueError("Sector Radar composition contains duplicate candidates")
    for candidate in broad_entries.candidates:
        if candidate.family != BROAD_881 or not _BROAD_CODE.fullmatch(candidate.thscode):
            raise ValueError("Sector Radar broad entry contains a non-881 candidate")
        if candidate.as_of_session != broad_entries.as_of_session:
            raise ValueError("Sector Radar broad candidate session mismatch")
    for candidate in granular_entries.candidates:
        if candidate.family != GRANULAR_884 or not _GRANULAR_CODE.fullmatch(candidate.thscode):
            raise ValueError("Sector Radar granular entry contains a non-884 candidate")
        if candidate.as_of_session != granular_entries.as_of_session:
            raise ValueError("Sector Radar granular candidate session mismatch")

    breadth_by_code = {item.sector_thscode: item for item in breadth_observations}
    if len(breadth_by_code) != len(tuple(breadth_observations)):
        raise ValueError("Sector Radar composition contains duplicate breadth observations")
    missing_breadth = sorted(set(by_candidate) - set(breadth_by_code))
    if missing_breadth:
        raise ValueError(
            "Sector Radar composition lacks current breadth for candidates: "
            + ", ".join(missing_breadth)
        )
    for code, candidate in by_candidate.items():
        breadth = breadth_by_code[code]
        if breadth.market_session != candidate.as_of_session:
            raise ValueError("Sector Radar composition breadth session mismatch")
        if breadth.sector_name != candidate.name:
            raise ValueError("Sector Radar composition breadth identity name mismatch")

    link_by_child: dict[str, SectorRadarCurrentParentLink] = {}
    broad_candidate_by_code = {item.thscode: item for item in broad_entries.candidates}
    granular_candidate_codes = {item.thscode for item in granular_entries.candidates}
    for link in parent_links:
        if link.child_thscode in link_by_child:
            raise ValueError("Sector Radar composition contains duplicate child parent links")
        if not _BROAD_CODE.fullmatch(link.parent_thscode):
            raise ValueError("Sector Radar composition parent link is not 881")
        if not _GRANULAR_CODE.fullmatch(link.child_thscode):
            raise ValueError("Sector Radar composition child link is not 884")
        if link.child_thscode not in granular_candidate_codes:
            raise ValueError("Sector Radar composition parent link has no child candidate")
        child_candidate = by_candidate[link.child_thscode]
        child_breadth = breadth_by_code[link.child_thscode]
        if link.child_name != child_candidate.name:
            raise ValueError("Sector Radar composition child link name mismatch")
        if link.child_constituent_set_hash != child_breadth.constituent_set_hash:
            raise ValueError("Sector Radar composition child membership hash mismatch")
        if link.child_membership_captured_at != child_breadth.membership_captured_at:
            raise ValueError("Sector Radar composition child membership clock mismatch")
        parent_candidate = broad_candidate_by_code.get(link.parent_thscode)
        if parent_candidate is not None:
            parent_breadth = breadth_by_code[link.parent_thscode]
            if link.parent_name != parent_candidate.name:
                raise ValueError("Sector Radar composition parent link name mismatch")
            if link.parent_constituent_set_hash != parent_breadth.constituent_set_hash:
                raise ValueError("Sector Radar composition parent membership hash mismatch")
            if link.parent_membership_captured_at != parent_breadth.membership_captured_at:
                raise ValueError("Sector Radar composition parent membership clock mismatch")
        link_by_child[link.child_thscode] = link

    return all_candidates, breadth_by_code, link_by_child


def compose_sector_radar_shadow(
    *,
    broad_entries: SectorRadarShadowStateEntries,
    granular_entries: SectorRadarShadowStateEntries,
    breadth_observations: Sequence[SectorCurrentBreadthObservation],
    parent_links: Sequence[SectorRadarCurrentParentLink],
    max_surfaced_groups: int = SECTOR_RADAR_SHADOW_MAX_SURFACED_GROUPS,
) -> SectorRadarShadowComposition:
    """Group current parent-child duplicates and retain a full auditable shadow set."""

    if max_surfaced_groups < 0:
        raise ValueError("Sector Radar shadow max_surfaced_groups must be non-negative")
    all_candidates, breadth_by_code, link_by_child = _validate_composition_inputs(
        broad_entries=broad_entries,
        granular_entries=granular_entries,
        breadth_observations=breadth_observations,
        parent_links=parent_links,
    )

    broad_by_code = {item.thscode: item for item in broad_entries.candidates}
    granular_by_parent: dict[str, list[SectorRadarShadowCandidate]] = {}
    unlinked_granular: list[SectorRadarShadowCandidate] = []
    for candidate in granular_entries.candidates:
        link = link_by_child.get(candidate.thscode)
        if link is None or not link.child_fully_contained:
            unlinked_granular.append(candidate)
            continue
        granular_by_parent.setdefault(link.parent_thscode, []).append(candidate)

    groups: list[SectorRadarShadowGroup] = []
    grouped_broad_codes = set(broad_by_code) | set(granular_by_parent)
    for parent_code in sorted(grouped_broad_codes):
        broad = broad_by_code.get(parent_code)
        children = sorted(
            granular_by_parent.get(parent_code, []),
            key=_candidate_priority,
        )
        if broad is not None:
            primary = broad
            drivers = tuple(children)
            parent_context_thscode = parent_code
            parent_context_name = broad.name
            grouping_reason = (
                "QUALIFIED_881_PARENT_WITH_FULLY_CONTAINED_884_DRIVERS"
                if children
                else "QUALIFIED_881_PARENT_ONLY"
            )
        else:
            if not children:
                raise ValueError("Sector Radar composition produced an empty parent group")
            primary = children[0]
            drivers = tuple(children[1:])
            link = link_by_child[primary.thscode]
            parent_context_thscode = link.parent_thscode
            parent_context_name = link.parent_name
            grouping_reason = (
                "GRANULAR_PRIMARY_UNDER_NON_CANDIDATE_881_CONTEXT"
                if len(children) == 1
                else "GRANULAR_SIBLINGS_GROUPED_UNDER_NON_CANDIDATE_881_CONTEXT"
            )

        all_group_candidates = tuple(
            sorted(
                ([broad] if broad is not None else []) + children,
                key=_candidate_priority,
            )
        )
        groups.append(
            SectorRadarShadowGroup(
                group_key=parent_code,
                primary_candidate=primary,
                primary_breadth=breadth_by_code[primary.thscode],
                parent_context_thscode=parent_context_thscode,
                parent_context_name=parent_context_name,
                granular_drivers=drivers,
                granular_driver_breadth=tuple(
                    breadth_by_code[item.thscode] for item in drivers
                ),
                all_candidates=all_group_candidates,
                grouping_reason=grouping_reason,
            )
        )

    for candidate in sorted(unlinked_granular, key=_candidate_priority):
        groups.append(
            SectorRadarShadowGroup(
                group_key=candidate.thscode,
                primary_candidate=candidate,
                primary_breadth=breadth_by_code[candidate.thscode],
                parent_context_thscode=None,
                parent_context_name=None,
                granular_drivers=(),
                granular_driver_breadth=(),
                all_candidates=(candidate,),
                grouping_reason="UNLINKED_GRANULAR_CANDIDATE",
            )
        )

    def group_priority(group: SectorRadarShadowGroup) -> tuple:
        return min(_candidate_priority(item) for item in group.all_candidates)

    groups.sort(key=lambda group: (group_priority(group), group.group_key))
    surfaced = tuple(groups[:max_surfaced_groups])
    omitted = tuple(groups[max_surfaced_groups:])
    return SectorRadarShadowComposition(
        policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
        as_of_session=broad_entries.as_of_session,
        all_candidates=tuple(sorted(all_candidates, key=_candidate_priority)),
        all_groups=tuple(groups),
        surfaced_groups=surfaced,
        omitted_groups=omitted,
        truncated_group_count=len(omitted),
        quiet_reason=None if surfaced else "NO_NEW_HIERARCHICAL_STATE_ENTRY_GROUP",
    )
