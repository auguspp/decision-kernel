from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from decision_kernel.deep_research import (
    DEEP_RESEARCH_CONTRACT_VERSION,
    AdversarialFinding,
    AdversarialSeverity,
    DeepResearchPackage,
    DeepResearchSupplement,
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
    commit_deep_research_package,
    deep_research_information_bundle_hash,
)
from decision_kernel.evidence import (
    EvidenceArtifact,
    EvidenceArtifactLink,
    EvidenceRelationship,
    ReplayabilityLevel,
    RetentionMode,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research import (
    ModelRiskLevel,
    ResearchSnapshot,
    ResearchStatus,
    Scenario,
)
from decision_kernel.research_contract_v1 import (
    ResearchContractV1Payload,
    ResearchContractV1ScenarioDetail,
    ResearchContractV1Status,
    assess_research_contract_v1,
)
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
from decision_kernel.valuation import ValuationBasis


AS_OF = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
COMMIT_AT = AS_OF + timedelta(hours=1)
HORIZON = date(2027, 9, 1)
FIRST_ID = UUID("50000000-0000-0000-0000-000000000001")
SECOND_ID = UUID("50000000-0000-0000-0000-000000000002")


def _evidence(artifact_id: UUID, *, locator: str, token: str) -> EvidenceArtifact:
    return EvidenceArtifact(
        id=artifact_id,
        source_type="OFFICIAL_FILING",
        source_identifier=f"filing-{token}",
        source_locator=locator,
        published_at=AS_OF - timedelta(days=2),
        available_at=AS_OF - timedelta(days=1),
        retrieved_at=AS_OF,
        content_hash=token * 64,
        idempotency_key=f"filing:{token}",
        retention_mode=RetentionMode.EXTRACTED_VALUES,
        replayability_level=ReplayabilityLevel.PARTIAL,
        extracted_structured_values={"claim": token},
    )


def _components():
    first = _evidence(FIRST_ID, locator="fixture://first", token="a")
    second = _evidence(SECOND_ID, locator="fixture://second", token="b")
    evidence = (first, second)

    discovery = DiscoveryInput(
        discovery_id="deep-research-demo",
        source_lane="OFFICIAL_CHANGE",
        ticker="600000",
        security_id=None,
        economic_direction="earnings inflection",
        as_of=AS_OF,
        factual_observations=(
            DiscoveryObservation(
                statement="A formal source changed the evidence set.",
                evidence_artifact_ids=(first.id,),
            ),
        ),
        source_lineage=(
            DiscoverySource(
                evidence_artifact_id=first.id,
                source_locator=first.source_locator,
                available_at=first.available_at,
            ),
        ),
        why_now="new formal evidence",
        current_market_expression="listed equity",
        next_discriminating_search="test unit economics",
        known_stop_or_downgrade_condition="economics fail to improve",
    )

    pre = PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=AS_OF,
        what_is_this="listed operating company",
        economic_direction=discovery.economic_direction,
        why_surfaced_now=discovery.why_now,
        current_expression_or_leadership=discovery.current_market_expression,
        basic_business_role="converts demand into earnings",
        potential_fundamental_driver="margin improvement",
        current_market_expectation_hypothesis="market expects flat margins",
        material_claims=(
            ResearchClaim(
                statement="formal evidence is available",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(first.id,),
            ),
        ),
        obvious_contradiction="competition may offset margin gains",
        largest_unknown="margin durability",
        next_discriminating_search="compare margin disclosures",
        route=PreResearchRoute.CONTINUE_TO_QUICK,
        route_reason="bounded uncertainty remains",
    )

    quick = QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=AS_OF,
        business_model="operating network",
        segment_mix="core operations",
        economic_role="converts network density into earnings",
        major_profit_drivers=("volume", "margin"),
        industry_supply_demand_variables=("demand", "competition"),
        value_chain_position="direct operator",
        current_industry_state="competitive but rational",
        market_expectation_hypothesis="flat margins",
        current_expression_or_leadership="listed equity",
        supporting_claims=(
            ResearchClaim(
                statement="primary filing supports scale",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(first.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="second filing exposes margin risk",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(second.id,),
            ),
        ),
        evidence_authority_assessment="official evidence dominates",
        variant_perception="margin durability may be mispriced",
        unresolved_questions=("can margins hold?",),
        next_discriminating_evidence=("next margin disclosure",),
        route=QuickResearchRoute.DEEPEN,
        route_reason="material variant remains testable",
    )

    falsifiers = (
        "margin improvement reverses",
        "volume growth fails to convert into earnings",
    )
    deep = DeepResearchSupplement(
        discovery_id=discovery.discovery_id,
        quick_research_hash=canonical_hash(quick),
        as_of=AS_OF,
        material_claims=(
            ResearchClaim(
                statement="primary filing supports current scale",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(first.id,),
            ),
            ResearchClaim(
                statement="network density may support margins",
                kind=ResearchClaimKind.INFERENCE,
                evidence_artifact_ids=(first.id,),
            ),
            ResearchClaim(
                statement="competition remains inside scenario bounds",
                kind=ResearchClaimKind.ASSUMPTION,
            ),
            ResearchClaim(
                statement="contradictory filing is decision-relevant context",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(second.id,),
            ),
        ),
        explicit_falsifiers=falsifiers,
        adversarial_findings=(
            AdversarialFinding(
                question="Are favorable drivers being peak-stacked?",
                finding="scenarios separate volume and margin assumptions",
                severity=AdversarialSeverity.WARN,
                resolution="downside scenario compresses margin",
            ),
        ),
    )

    snapshot_id = uuid4()
    basis = ValuationBasis(
        id=uuid4(),
        research_snapshot_id=snapshot_id,
        version=1,
        as_of_datetime=AS_OF,
        valuation_horizon_date=HORIZON,
        valuation_method="scenario_equity_value",
        model_version="v1",
        currency="CNY",
        fundamental_inputs={"earnings": "scenario-driven"},
        valuation_parameter_inputs={"multiple": "scenario-driven"},
        provenance_artifact_ids=(first.id,),
    )

    def scenario(name: str, probability: str, terminal: str) -> Scenario:
        return Scenario(
            id=uuid4(),
            research_snapshot_id=snapshot_id,
            name=name,
            probability=probability,
            terminal_equity_value_per_share=terminal,
            valuation_basis_id=basis.id,
        )

    monitoring = ("volume", "margin", "pricing")
    snapshot = ResearchSnapshot(
        id=snapshot_id,
        ticker="600000",
        company_name="Sample Co",
        exchange="SSE",
        currency="CNY",
        created_at=AS_OF,
        as_of_datetime=AS_OF,
        valuation_horizon_date=HORIZON,
        version=1,
        core_thesis="earnings can exceed current expectations",
        market_expectations_narrative="market expects flat margins",
        model_risk_level=ModelRiskLevel.MEDIUM,
        model_risk_notes="terminal value and margin durability",
        open_questions=("can margins hold?",),
        thesis_invalidation=falsifiers,
        monitoring_triggers=monitoring,
        created_by="deep-research-test",
        research_engine_version="replaceable-executor-v7",
        information_bundle_hash="0" * 64,
        research_origin=f"DISCOVERY_INPUT:{discovery.discovery_id}",
        valuation_bases=(basis,),
        scenarios=(
            scenario("up", "0.6", "15"),
            scenario("down", "0.4", "8"),
        ),
        evidence_links=(
            EvidenceArtifactLink(
                id=uuid4(),
                research_snapshot_id=snapshot_id,
                evidence_artifact_id=first.id,
                relationship=EvidenceRelationship.SUPPORTS,
                relevance="supports scale and thesis",
            ),
            EvidenceArtifactLink(
                id=uuid4(),
                research_snapshot_id=snapshot_id,
                evidence_artifact_id=second.id,
                relationship=EvidenceRelationship.OPPOSES,
                relevance="preserves contradiction",
            ),
            EvidenceArtifactLink(
                id=uuid4(),
                research_snapshot_id=snapshot_id,
                evidence_artifact_id=second.id,
                relationship=EvidenceRelationship.CONTEXT,
                relevance="preserves market context",
            ),
        ),
    )
    return discovery, pre, quick, deep, evidence, snapshot


def _package() -> DeepResearchPackage:
    discovery, pre, quick, deep, evidence, snapshot = _components()
    information_hash = deep_research_information_bundle_hash(
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        deep_research=deep,
        evidence_artifacts=evidence,
        research_snapshot=snapshot,
    )
    snapshot = snapshot.model_copy(update={"information_bundle_hash": information_hash})
    return DeepResearchPackage(
        label="Deep Research fixture",
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        deep_research=deep,
        evidence_artifacts=evidence,
        research_snapshot=snapshot,
        proposed_committed_at=COMMIT_AT,
    )


def _contract_payload(package: DeepResearchPackage) -> ResearchContractV1Payload:
    margins = {"up": "0.12", "down": "0.06"}
    return ResearchContractV1Payload(
        research_snapshot_id=package.research_snapshot.id,
        contract_version=DEEP_RESEARCH_CONTRACT_VERSION,
        doctrine_version_reference="doctrine-v1",
        variant_perception="margin durability may be mispriced",
        market_expectation_map={"margin": "flat"},
        normalized_earnings_notes="normalized earnings use scenario drivers",
        valuation_framework="scenario equity value",
        fundamental_clock_assessment={"state": "improving"},
        expectation_clock_assessment={"state": "lagging"},
        liquidity_clock_assessment={"state": "neutral"},
        monitoring_indicators=package.research_snapshot.monitoring_triggers,
        monitoring_falsifiers=package.deep_research.explicit_falsifiers,
        valuation_stress_spec={"margin_downside": "included"},
        scenario_details=tuple(
            ResearchContractV1ScenarioDetail(
                scenario_id=scenario.id,
                description=scenario.name,
                assumptions={"competition": "bounded"},
                financial_driver_values={"margin": margins.get(scenario.name, "0.10")},
                normalized_earnings="1.0",
            )
            for scenario in package.research_snapshot.scenarios
        ),
    )


def _rehash(
    package: DeepResearchPackage,
    *,
    quick_research: QuickResearchResult | None = None,
    deep_research: DeepResearchSupplement | None = None,
    evidence_artifacts: tuple[EvidenceArtifact, ...] | None = None,
    research_snapshot: ResearchSnapshot | None = None,
) -> DeepResearchPackage:
    quick = quick_research or package.quick_research
    deep = deep_research or package.deep_research
    evidence = evidence_artifacts or package.evidence_artifacts
    snapshot = research_snapshot or package.research_snapshot
    snapshot = snapshot.model_copy(update={"information_bundle_hash": "0" * 64})
    snapshot = snapshot.model_copy(
        update={
            "information_bundle_hash": deep_research_information_bundle_hash(
                discovery=package.discovery,
                pre_research=package.pre_research,
                quick_research=quick,
                deep_research=deep,
                evidence_artifacts=evidence,
                research_snapshot=snapshot,
            )
        }
    )
    return package.model_copy(
        update={
            "quick_research": quick,
            "deep_research": deep,
            "evidence_artifacts": evidence,
            "research_snapshot": snapshot,
        }
    )


def _acceptance_codes(package: DeepResearchPackage) -> set[str]:
    return {
        issue.code
        for issue in assess_research_method_v1_acceptance(package).issues
    }


def _contract_codes(
    package: DeepResearchPackage,
    payload: ResearchContractV1Payload | None = None,
) -> set[str]:
    return {
        issue.code
        for issue in assess_research_contract_v1(
            package,
            payload or _contract_payload(package),
        ).issues
    }


def test_research_method_v1_accepted_package_commits_and_contract_conforms() -> None:
    package = _package()
    payload = _contract_payload(package)

    acceptance = assess_research_method_v1_acceptance(package)
    contract = assess_research_contract_v1(package, payload)
    result = commit_deep_research_package(package)

    assert acceptance.status is ResearchMethodV1AcceptanceStatus.ACCEPTED
    assert acceptance.issues == ()
    assert contract.status is ResearchContractV1Status.CONFORMING
    assert contract.issues == ()
    assert package.research_snapshot.status is ResearchStatus.DRAFT
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.research_snapshot.committed_at == COMMIT_AT
    assert result.research_snapshot.information_bundle_hash == (
        package.research_snapshot.information_bundle_hash
    )


def test_research_method_v1_requires_explicit_deepen_and_exact_quick_state() -> None:
    package = _package()
    waiting = package.quick_research.model_copy(
        update={"route": QuickResearchRoute.WAIT_FOR_TRIGGER}
    )
    deep = package.deep_research.model_copy(
        update={"quick_research_hash": canonical_hash(waiting)}
    )
    changed = _rehash(package, quick_research=waiting, deep_research=deep)
    assert "QUICK_NOT_DEEPENED" in _acceptance_codes(changed)

    wrong_hash = package.deep_research.model_copy(update={"quick_research_hash": "f" * 64})
    changed_hash = _rehash(package, deep_research=wrong_hash)
    assert "DEEP_QUICK_HASH_MISMATCH" in _acceptance_codes(changed_hash)


def test_adversarial_block_is_method_contract_policy_not_kernel_constitution() -> None:
    package = _package()
    blocked = package.deep_research.model_copy(
        update={
            "adversarial_findings": (
                AdversarialFinding(
                    question="Is the causal chain established?",
                    finding="a material gap remains",
                    severity=AdversarialSeverity.BLOCK,
                    resolution="more evidence required",
                ),
            )
        }
    )
    changed = _rehash(package, deep_research=blocked)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert "ADVERSARIAL_BLOCK_UNRESOLVED" in _contract_codes(changed)
    assert commit_deep_research_package(changed).research_snapshot.status is ResearchStatus.COMMITTED


def test_method_v1_package_rejects_future_and_unreferenced_evidence() -> None:
    package = _package()
    future = package.evidence_artifacts[1].model_copy(
        update={
            "published_at": AS_OF + timedelta(seconds=1),
            "available_at": AS_OF + timedelta(seconds=1),
            "retrieved_at": AS_OF + timedelta(hours=2),
        }
    )
    changed = _rehash(
        package,
        evidence_artifacts=(package.evidence_artifacts[0], future),
    )
    assert "EVIDENCE_AFTER_PIT" in _acceptance_codes(changed)

    extra = _evidence(
        UUID("50000000-0000-0000-0000-000000000099"),
        locator="fixture://extra",
        token="c",
    )
    changed_extra = _rehash(
        package,
        evidence_artifacts=(*package.evidence_artifacts, extra),
    )
    assert "EVIDENCE_NOT_REFERENCED" in _acceptance_codes(changed_extra)


def test_contradiction_and_market_context_are_method_v1_projection_rules() -> None:
    package = _package()
    without_opposes = package.research_snapshot.model_copy(
        update={
            "evidence_links": tuple(
                link
                for link in package.research_snapshot.evidence_links
                if link.relationship is not EvidenceRelationship.OPPOSES
            )
        }
    )
    changed = _rehash(package, research_snapshot=without_opposes)
    assert "CONTRADICTORY_EVIDENCE_MISSING" in _acceptance_codes(changed)

    without_context = package.research_snapshot.model_copy(
        update={
            "evidence_links": tuple(
                link
                for link in package.research_snapshot.evidence_links
                if link.relationship is not EvidenceRelationship.CONTEXT
            )
        }
    )
    changed_context = _rehash(package, research_snapshot=without_context)
    assert "MARKET_CONTEXT_RELATIONSHIP_MISSING" in _acceptance_codes(changed_context)


def test_liquidity_clock_exists_only_in_contract_payload() -> None:
    package = _package()
    payload = _contract_payload(package).model_copy(update={"liquidity_clock_assessment": {}})

    assert (
        assess_research_method_v1_acceptance(package).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert "METHOD_STRUCTURE_MISSING" in _contract_codes(package, payload)


def test_one_complete_scenario_is_kernel_valid_but_not_contract_v1_conforming() -> None:
    package = _package()
    one = package.research_snapshot.scenarios[0].model_copy(
        update={"probability": Decimal("1")}
    )
    snapshot = package.research_snapshot.model_copy(update={"scenarios": (one,)})
    changed = _rehash(package, research_snapshot=snapshot)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert commit_deep_research_package(changed).research_snapshot.status is ResearchStatus.COMMITTED
    assert "SCENARIO_SET_NOT_SMALL" in _contract_codes(changed)


def test_incomplete_scenario_distribution_is_kernel_commit_invariant_not_method_v1() -> None:
    package = _package()
    one = package.research_snapshot.scenarios[0].model_copy(
        update={"probability": Decimal("0.6")}
    )
    snapshot = package.research_snapshot.model_copy(update={"scenarios": (one,)})
    changed = _rehash(package, research_snapshot=snapshot)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    with pytest.raises(DomainValidationError, match="probabilities must sum to one"):
        commit_deep_research_package(changed)


def test_monitoring_and_scenario_driver_richness_are_contract_payload_policy() -> None:
    package = _package()
    payload = _contract_payload(package)
    first_detail = payload.scenario_details[0].model_copy(
        update={"financial_driver_values": {}}
    )
    payload = payload.model_copy(
        update={
            "monitoring_indicators": ("only one",),
            "market_expectation_map": {},
            "scenario_details": (first_detail, *payload.scenario_details[1:]),
        }
    )

    assert (
        assess_research_method_v1_acceptance(package).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    codes = _contract_codes(package, payload)
    assert "MONITORING_INDICATORS_INVALID" in codes
    assert "METHOD_STRUCTURE_MISSING" in codes
    assert "SCENARIO_DRIVER_STRUCTURE_MISSING" in codes


def test_falsifier_projection_is_research_method_v1_lineage_rule() -> None:
    package = _package()
    snapshot = package.research_snapshot.model_copy(
        update={"thesis_invalidation": ("different invalidation",)}
    )
    changed = _rehash(package, research_snapshot=snapshot)

    assert "FALSIFIER_LINEAGE_MISMATCH" in _acceptance_codes(changed)


def test_information_bundle_hash_detects_silent_research_body_change() -> None:
    package = _package()
    tampered = package.model_copy(
        update={
            "research_snapshot": package.research_snapshot.model_copy(
                update={"core_thesis": "materially different thesis"}
            )
        }
    )

    assert "INFORMATION_BUNDLE_HASH_MISMATCH" in _acceptance_codes(tampered)
