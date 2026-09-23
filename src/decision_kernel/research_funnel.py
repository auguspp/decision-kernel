from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .evidence import EvidenceArtifact
from .identity import canonical_hash
from .primitives import AwareDateTime, DomainValidationError, KernelModel


class ResearchClaimKind(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    MARKET_CONTEXT = "MARKET_CONTEXT"


class PreResearchRoute(StrEnum):
    CONTINUE_TO_QUICK = "CONTINUE_TO_QUICK"
    WAIT_FOR_TRIGGER = "WAIT_FOR_TRIGGER"
    STOP = "STOP"


class QuickResearchRoute(StrEnum):
    DEEPEN = "DEEPEN"
    WAIT_FOR_TRIGGER = "WAIT_FOR_TRIGGER"
    STOP = "STOP"


class DiscoverySource(KernelModel):
    evidence_artifact_id: UUID
    source_locator: str = Field(min_length=1, max_length=2048)
    available_at: AwareDateTime


class DiscoveryObservation(KernelModel):
    statement: str = Field(min_length=1)
    evidence_artifact_ids: tuple[UUID, ...] = Field(min_length=1)


class DiscoveryInput(KernelModel):
    """PIT-frozen handoff into the research funnel; sensing lives outside the kernel."""

    discovery_id: str = Field(min_length=1, max_length=255)
    source_lane: str = Field(min_length=1, max_length=128)
    ticker: str | None = Field(default=None, max_length=32)
    security_id: str | None = Field(default=None, max_length=128)
    economic_direction: str = Field(min_length=1)
    as_of: AwareDateTime
    factual_observations: tuple[DiscoveryObservation, ...] = Field(min_length=1)
    source_lineage: tuple[DiscoverySource, ...] = Field(min_length=1)
    why_now: str = Field(min_length=1)
    current_market_expression: str | None = None
    supporting_securities: tuple[str, ...] = ()
    contradiction_or_mapping_warning: str | None = None
    next_discriminating_search: str = Field(min_length=1)
    known_stop_or_downgrade_condition: str = Field(min_length=1)
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_pit_lineage(self) -> "DiscoveryInput":
        lineage_ids = {source.evidence_artifact_id for source in self.source_lineage}
        if len(lineage_ids) != len(self.source_lineage):
            raise ValueError("Discovery source evidence ids must be unique")
        if any(source.available_at > self.as_of for source in self.source_lineage):
            raise ValueError("Discovery source cannot be available after its PIT cutoff")
        for observation in self.factual_observations:
            if not set(observation.evidence_artifact_ids).issubset(lineage_ids):
                raise ValueError("Discovery observation must reference declared source lineage")
        if self.ticker is None and self.security_id is None:
            raise ValueError("Discovery Input requires ticker or security_id")
        return self


class ResearchClaim(KernelModel):
    # Descriptions explain existing contracts to schema consumers; they add no
    # validators, fields or serialized values and do not certify economic truth.
    statement: str = Field(min_length=1, description=(
        "State the observation or reasoning and its source scope. FACT means a supplied "
        "source observation, not an inferred cause. Never relabel INFERENCE or ASSUMPTION "
        "as FACT to satisfy a route; a source citation does not turn inference into fact."
    ))
    kind: ResearchClaimKind
    evidence_artifact_ids: tuple[UUID, ...] = Field(default=(), description=(
        "FACT and MARKET_CONTEXT require at least one supplied Evidence ID. Use only "
        "the trusted host evidence_ids allowlist, not nested document IDs. Identify the "
        "underlying document/page in statement when citing an admitted bundle."
    ))

    @model_validator(mode="after")
    def validate_evidence_requirement(self) -> "ResearchClaim":
        if self.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
            if not self.evidence_artifact_ids:
                raise ValueError(f"{self.kind} claims require evidence lineage")
        return self


class PreResearchResult(KernelModel):
    discovery_id: str = Field(min_length=1, max_length=255)
    as_of: AwareDateTime
    what_is_this: str = Field(min_length=1)
    economic_direction: str = Field(min_length=1)
    why_surfaced_now: str = Field(min_length=1)
    current_expression_or_leadership: str | None = None
    basic_business_role: str = Field(min_length=1)
    potential_fundamental_driver: str = Field(min_length=1)
    current_market_expectation_hypothesis: str = Field(min_length=1)
    material_claims: tuple[ResearchClaim, ...] = Field(min_length=1, description=(
        "Keep observations, inferences and assumptions honestly labelled. "
        "CONTINUE_TO_QUICK requires at least one evidenced FACT; not all claims must be facts."
    ))
    obvious_contradiction: str | None = None
    largest_unknown: str = Field(min_length=1)
    next_discriminating_search: str = Field(min_length=1)
    route: PreResearchRoute
    route_reason: str = Field(min_length=1, description=(
        "Explain the chosen route without forcing advancement. CONTINUE_TO_QUICK requires "
        "at least one evidenced FACT plus nonblank largest_unknown and next_discriminating_search. "
        "WAIT_FOR_TRIGGER names the missing evidence and trigger; STOP explains the stopping "
        "condition. A required-source or technical failure is not a completed business WAIT."
    ))
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_continue_budget(self) -> "PreResearchResult":
        if self.route is PreResearchRoute.CONTINUE_TO_QUICK:
            if not any(claim.kind is ResearchClaimKind.FACT for claim in self.material_claims):
                raise ValueError("CONTINUE_TO_QUICK requires at least one evidenced FACT")
            if not self.largest_unknown.strip() or not self.next_discriminating_search.strip():
                raise ValueError(
                    "CONTINUE_TO_QUICK requires an unknown and discriminating next search"
                )
        return self


class QuickResearchResult(KernelModel):
    discovery_id: str = Field(min_length=1, max_length=255)
    pre_research_hash: str = Field(min_length=64, max_length=64)
    as_of: AwareDateTime
    business_model: str = Field(min_length=1)
    segment_mix: str = Field(min_length=1)
    economic_role: str = Field(min_length=1)
    major_profit_drivers: tuple[str, ...] = Field(min_length=1)
    industry_supply_demand_variables: tuple[str, ...] = Field(min_length=1)
    value_chain_position: str = Field(min_length=1)
    current_industry_state: str | None = None
    market_expectation_hypothesis: str = Field(min_length=1)
    current_expression_or_leadership: str | None = None
    supporting_claims: tuple[ResearchClaim, ...] = Field(default=(), description=(
        "For DEEPEN this group must be nonempty and EVERY claim must be FACT or "
        "MARKET_CONTEXT with nonempty evidence_artifact_ids. Preserve inference and "
        "assumptions as labelled reasoning in the narrative fields, never relabel them "
        "as facts. WAIT_FOR_TRIGGER and STOP do not impose this all-factual group condition."
    ))
    contradictory_claims: tuple[ResearchClaim, ...] = Field(default=(), description=(
        "For DEEPEN this group must also be nonempty and EVERY claim must be FACT or "
        "MARKET_CONTEXT with nonempty evidence_artifact_ids. Do not discard counterevidence "
        "to pass validation. Explain inferred implications separately in narrative fields. "
        "WAIT_FOR_TRIGGER and STOP do not impose this all-factual group condition."
    ))
    evidence_authority_assessment: str = Field(min_length=1, description=(
        "Separate source identity and declared-scope preflight from economic truth and "
        "whole-issuer coverage. Describe actual missing evidence, not an invented source "
        "failure because internal host receipts were not included in model context. "
        "A checked report-correction inventory is not all subsequent announcements."
    ))
    variant_perception: str | None = Field(default=None, description=(
        "DEEPEN requires a nonblank plausible differentiated hypothesis, its basis and a "
        "way to test it. Do not invent market consensus. If none can be established, use "
        "null and explain the limitation in market_expectation_hypothesis and route_reason; "
        "saying 'no variant established' is not a positive variant. A tentative hypothesis "
        "must be labelled tentative, not presented as a verified market mispricing."
    ))
    unresolved_questions: tuple[str, ...] = Field(min_length=1)
    next_discriminating_evidence: tuple[str, ...] = Field(min_length=1, description=(
        "Distinguish analysis possible now with available sources from evidence requiring "
        "a future publication or event. Name the observation that would change the view. "
        "A future periodic report is a future trigger, not evidence already available now."
    ))
    route: QuickResearchRoute
    route_reason: str = Field(min_length=1, description=(
        "For DEEPEN both evidence groups must be nonempty, every grouped claim must be "
        "evidenced FACT or MARKET_CONTEXT, and variant_perception must be nonblank and "
        "plausible. Explain useful discriminating work possible now; missing quantitative "
        "closure alone does not mandate DEEPEN. Future disclosure alone supports "
        "WAIT_FOR_TRIGGER, not immediate research availability. STOP requires a stated "
        "stopping reason. Keep UNKNOWN and technical/source gaps honest; never rewrite "
        "claim kinds or manufacture evidence to obtain a route. DEEPEN is not permission "
        "for automatic Deep or any investment action."
    ))
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_deepen_budget(self) -> "QuickResearchResult":
        if self.route is QuickResearchRoute.DEEPEN:
            if not self.supporting_claims:
                raise ValueError("DEEPEN requires supporting evidence")
            if not self.contradictory_claims:
                raise ValueError("DEEPEN requires contradictory evidence")
            for claim in (*self.supporting_claims, *self.contradictory_claims):
                if claim.kind not in {
                    ResearchClaimKind.FACT,
                    ResearchClaimKind.MARKET_CONTEXT,
                } or not claim.evidence_artifact_ids:
                    raise ValueError(
                        "DEEPEN evidence groups require evidenced FACT or MARKET_CONTEXT claims"
                    )
            if self.variant_perception is None or not self.variant_perception.strip():
                raise ValueError("DEEPEN requires a plausible variant perception")
        return self


def referenced_evidence_ids(
    pre_research: PreResearchResult,
    quick_research: QuickResearchResult,
) -> frozenset[UUID]:
    claims = (
        *pre_research.material_claims,
        *quick_research.supporting_claims,
        *quick_research.contradictory_claims,
    )
    return frozenset(
        artifact_id for claim in claims for artifact_id in claim.evidence_artifact_ids
    )


def validate_pre_research_transition(
    discovery: DiscoveryInput,
    pre_research: PreResearchResult,
    evidence_artifacts: tuple[EvidenceArtifact, ...],
) -> None:
    """Bind every Pre-Research route to the exact Discovery PIT and evidence set."""

    if pre_research.discovery_id != discovery.discovery_id or pre_research.as_of != discovery.as_of:
        raise DomainValidationError("Pre-Research changed Discovery identity or PIT cutoff")

    artifacts_by_id = {artifact.id: artifact for artifact in evidence_artifacts}
    if len(artifacts_by_id) != len(evidence_artifacts):
        raise DomainValidationError("Research funnel evidence ids must be unique")

    discovery_ids = {source.evidence_artifact_id for source in discovery.source_lineage}
    pre_ids = {
        artifact_id
        for claim in pre_research.material_claims
        for artifact_id in claim.evidence_artifact_ids
    }
    missing_ids = (discovery_ids | pre_ids) - artifacts_by_id.keys()
    if missing_ids:
        missing = ", ".join(sorted(str(item) for item in missing_ids))
        raise DomainValidationError(f"Research funnel references missing evidence: {missing}")

    for source in discovery.source_lineage:
        artifact = artifacts_by_id[source.evidence_artifact_id]
        if (
            artifact.source_locator != source.source_locator
            or artifact.available_at != source.available_at
        ):
            raise DomainValidationError(
                "Discovery source lineage must match the resolved EvidenceArtifact"
            )

    future_ids = sorted(
        (
            artifact_id
            for artifact_id in discovery_ids | pre_ids
            if artifacts_by_id[artifact_id].available_at > discovery.as_of
        ),
        key=str,
    )
    if future_ids:
        raise DomainValidationError(
            "Research funnel evidence was not available at the Discovery PIT cutoff: "
            + ", ".join(str(item) for item in future_ids)
        )


def validate_funnel_transition(
    discovery: DiscoveryInput,
    pre_research: PreResearchResult,
    quick_research: QuickResearchResult,
    evidence_artifacts: tuple[EvidenceArtifact, ...],
) -> None:
    """Fail closed unless Quick Research continues the exact PIT-frozen Pre state."""

    validate_pre_research_transition(discovery, pre_research, evidence_artifacts)
    if pre_research.route is not PreResearchRoute.CONTINUE_TO_QUICK:
        raise DomainValidationError(
            "Quick Research requires a CONTINUE_TO_QUICK Pre-Research route"
        )
    if quick_research.discovery_id != discovery.discovery_id:
        raise DomainValidationError("Quick Research must reference its Discovery Input")
    if quick_research.as_of != discovery.as_of:
        raise DomainValidationError("Research funnel stages must share the Discovery PIT cutoff")
    if quick_research.pre_research_hash != canonical_hash(pre_research):
        raise DomainValidationError("Quick Research must reference the exact Pre-Research state")

    artifacts_by_id = {artifact.id: artifact for artifact in evidence_artifacts}
    referenced_ids = referenced_evidence_ids(pre_research, quick_research)
    missing_ids = referenced_ids - artifacts_by_id.keys()
    if missing_ids:
        missing = ", ".join(sorted(str(item) for item in missing_ids))
        raise DomainValidationError(f"Research funnel references missing evidence: {missing}")

    future_ids = sorted(
        (
            artifact_id
            for artifact_id in referenced_ids
            if artifacts_by_id[artifact_id].available_at > discovery.as_of
        ),
        key=str,
    )
    if future_ids:
        raise DomainValidationError(
            "Research funnel evidence was not available at the Discovery PIT cutoff: "
            + ", ".join(str(item) for item in future_ids)
        )
