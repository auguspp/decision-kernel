from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.evidence import EvidenceArtifact, ReplayabilityLevel, RetentionMode
from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research_funnel import (
    DiscoveryInput,
    DiscoveryObservation,
    DiscoverySource,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    QuickResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.workflow import (
    ResearchFunnelStage,
    ResearchFunnelTerminalState,
    run_research_funnel,
)


PUBLISHED_AT = datetime(2026, 9, 1, 7, 0, tzinfo=timezone.utc)
AVAILABLE_AT = PUBLISHED_AT + timedelta(minutes=10)
CUTOFF = PUBLISHED_AT + timedelta(hours=1)
RETRIEVED_AT = CUTOFF + timedelta(hours=1)


def _evidence(*, available_at: datetime = AVAILABLE_AT) -> EvidenceArtifact:
    evidence_id = uuid4()
    return EvidenceArtifact(
        id=evidence_id,
        source_type="official_disclosure",
        source_identifier=str(evidence_id),
        source_locator=f"https://example.test/{evidence_id}",
        published_at=PUBLISHED_AT,
        available_at=available_at,
        retrieved_at=max(RETRIEVED_AT, available_at),
        content_hash="a" * 64,
        idempotency_key=str(evidence_id),
        retention_mode=RetentionMode.FULL_ARTIFACT,
        replayability_level=ReplayabilityLevel.FULL,
        raw_storage_ref=f"evidence/{evidence_id}.pdf",
    )


def _discovery(primary: EvidenceArtifact) -> DiscoveryInput:
    return DiscoveryInput(
        discovery_id="disc-1",
        source_lane="EXTERNAL_REALITY",
        ticker="600000",
        security_id="SSE:600000",
        economic_direction="possible earnings expectation gap",
        as_of=CUTOFF,
        factual_observations=(
            DiscoveryObservation(
                statement="official disclosure changed the earnings picture",
                evidence_artifact_ids=(primary.id,),
            ),
        ),
        source_lineage=(
            DiscoverySource(
                evidence_artifact_id=primary.id,
                source_locator=primary.source_locator,
                available_at=primary.available_at,
            ),
        ),
        why_now="new official evidence became available",
        current_market_expression="observe only",
        next_discriminating_search="check whether margins confirm the change",
        known_stop_or_downgrade_condition="drop if the change is accounting-only",
    )


def _pre(
    primary: EvidenceArtifact,
    *,
    route: PreResearchRoute = PreResearchRoute.CONTINUE_TO_QUICK,
    extra_claim: ResearchClaim | None = None,
) -> PreResearchResult:
    claims = [
        ResearchClaim(
            statement="reported earnings changed",
            kind=ResearchClaimKind.FACT,
            evidence_artifact_ids=(primary.id,),
        )
    ]
    if extra_claim is not None:
        claims.append(extra_claim)
    return PreResearchResult(
        discovery_id="disc-1",
        as_of=CUTOFF,
        what_is_this="an earnings expectation question",
        economic_direction="potential positive earnings revision",
        why_surfaced_now="official evidence changed",
        current_expression_or_leadership="observe only",
        basic_business_role="operating company",
        potential_fundamental_driver="margin expansion",
        current_market_expectation_hypothesis="market expects flat margins",
        material_claims=tuple(claims),
        largest_unknown="whether margin change is durable",
        next_discriminating_search="check segment margins",
        route=route,
        route_reason=f"route={route.value}",
    )


def _quick(
    pre: PreResearchResult,
    supporting: EvidenceArtifact,
    contradicting: EvidenceArtifact,
    *,
    route: QuickResearchRoute = QuickResearchRoute.DEEPEN,
    pre_hash: str | None = None,
) -> QuickResearchResult:
    return QuickResearchResult(
        discovery_id="disc-1",
        pre_research_hash=pre_hash or canonical_hash(pre),
        as_of=CUTOFF,
        business_model="operating company",
        segment_mix="two segments",
        economic_role="earnings compounder candidate",
        major_profit_drivers=("margin",),
        industry_supply_demand_variables=("capacity",),
        value_chain_position="producer",
        market_expectation_hypothesis="market expects flat margins",
        supporting_claims=(
            ResearchClaim(
                statement="reported margins improved",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(supporting.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="industry capacity is increasing",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(contradicting.id,),
            ),
        ),
        evidence_authority_assessment="official evidence plus market context",
        variant_perception="margin durability may be underappreciated",
        unresolved_questions=("is margin durable?",),
        next_discriminating_evidence=("next segment disclosure",),
        route=route,
        route_reason=f"route={route.value}",
    )


def test_fact_requires_evidence_but_inference_does_not() -> None:
    with pytest.raises(ValidationError, match="claims require evidence lineage"):
        ResearchClaim(statement="fact", kind=ResearchClaimKind.FACT)

    inference = ResearchClaim(
        statement="possible interpretation",
        kind=ResearchClaimKind.INFERENCE,
    )
    assert inference.evidence_artifact_ids == ()


def test_pre_research_wait_is_a_legal_cognitive_budget_stop() -> None:
    evidence = _evidence()
    result = run_research_funnel(
        discovery=_discovery(evidence),
        pre_research=_pre(evidence, route=PreResearchRoute.WAIT_FOR_TRIGGER),
        evidence_artifacts=(evidence,),
    )

    assert result.terminal_stage is ResearchFunnelStage.PRE_RESEARCH
    assert result.terminal_state is ResearchFunnelTerminalState.WAIT_FOR_TRIGGER
    assert result.quick_research is None
    assert result.investment_authority == "NONE"


def test_pre_research_stop_maps_to_drop_for_now() -> None:
    evidence = _evidence()
    result = run_research_funnel(
        discovery=_discovery(evidence),
        pre_research=_pre(evidence, route=PreResearchRoute.STOP),
        evidence_artifacts=(evidence,),
    )
    assert result.terminal_state is ResearchFunnelTerminalState.DROP_FOR_NOW


def test_continue_to_quick_cannot_skip_quick_research() -> None:
    evidence = _evidence()
    with pytest.raises(DomainValidationError, match="requires a QuickResearchResult"):
        run_research_funnel(
            discovery=_discovery(evidence),
            pre_research=_pre(evidence),
            evidence_artifacts=(evidence,),
        )


def test_quick_deepen_requires_exact_lineage_and_returns_deepen_required() -> None:
    supporting = _evidence()
    contradicting = _evidence()
    discovery = _discovery(supporting)
    pre = _pre(supporting)
    quick = _quick(pre, supporting, contradicting)

    result = run_research_funnel(
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        evidence_artifacts=(supporting, contradicting),
    )

    assert result.terminal_stage is ResearchFunnelStage.QUICK_RESEARCH
    assert result.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED
    assert result.quick_research is quick


def test_quick_wait_and_stop_are_normal_product_endpoints() -> None:
    supporting = _evidence()
    contradicting = _evidence()
    discovery = _discovery(supporting)
    pre = _pre(supporting)

    wait = run_research_funnel(
        discovery=discovery,
        pre_research=pre,
        quick_research=_quick(
            pre,
            supporting,
            contradicting,
            route=QuickResearchRoute.WAIT_FOR_TRIGGER,
        ),
        evidence_artifacts=(supporting, contradicting),
    )
    assert wait.terminal_state is ResearchFunnelTerminalState.WAIT_FOR_TRIGGER

    stop = run_research_funnel(
        discovery=discovery,
        pre_research=pre,
        quick_research=_quick(
            pre,
            supporting,
            contradicting,
            route=QuickResearchRoute.STOP,
        ),
        evidence_artifacts=(supporting, contradicting),
    )
    assert stop.terminal_state is ResearchFunnelTerminalState.DROP_FOR_NOW


def test_quick_research_cannot_reference_a_different_pre_state() -> None:
    supporting = _evidence()
    contradicting = _evidence()
    discovery = _discovery(supporting)
    pre = _pre(supporting)
    quick = _quick(
        pre,
        supporting,
        contradicting,
        pre_hash="f" * 64,
    )

    with pytest.raises(DomainValidationError, match="exact Pre-Research state"):
        run_research_funnel(
            discovery=discovery,
            pre_research=pre,
            quick_research=quick,
            evidence_artifacts=(supporting, contradicting),
        )


def test_wait_or_stop_cannot_hide_future_pre_research_evidence() -> None:
    primary = _evidence()
    future = _evidence(available_at=CUTOFF + timedelta(minutes=1))
    discovery = _discovery(primary)
    future_claim = ResearchClaim(
        statement="future disclosure",
        kind=ResearchClaimKind.FACT,
        evidence_artifact_ids=(future.id,),
    )
    pre = _pre(
        primary,
        route=PreResearchRoute.WAIT_FOR_TRIGGER,
        extra_claim=future_claim,
    )

    with pytest.raises(DomainValidationError, match="not available at the Discovery PIT cutoff"):
        run_research_funnel(
            discovery=discovery,
            pre_research=pre,
            evidence_artifacts=(primary, future),
        )
