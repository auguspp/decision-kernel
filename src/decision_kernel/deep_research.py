from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .evidence import EvidenceArtifact, EvidenceRelationship
from .identity import canonical_hash
from .primitives import AwareDateTime, DomainValidationError, KernelModel
from .research import (
    ResearchSnapshot,
    ResearchStatus,
    commit_snapshot,
    submit_for_review,
)
from .research_funnel import (
    DiscoveryInput,
    PreResearchResult,
    QuickResearchResult,
    QuickResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
    validate_funnel_transition,
)


DEEP_RESEARCH_CONTRACT_VERSION = "research-odds-rehearsal-v1"


class AdversarialSeverity(StrEnum):
    BLOCK = "BLOCK"
    WARN = "WARN"
    NOTE = "NOTE"


class AdversarialFinding(KernelModel):
    question: str = Field(min_length=1)
    finding: str = Field(min_length=1)
    severity: AdversarialSeverity
    resolution: str | None = None


class DeepResearchSupplement(KernelModel):
    """Executor-agnostic Deep Research result bound to one exact Quick Research state."""

    discovery_id: str = Field(min_length=1, max_length=255)
    quick_research_hash: str = Field(min_length=64, max_length=64)
    as_of: AwareDateTime
    material_claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    explicit_falsifiers: tuple[str, ...] = Field(min_length=1)
    adversarial_findings: tuple[AdversarialFinding, ...] = Field(min_length=1)
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_claim_classes(self) -> "DeepResearchSupplement":
        kinds = {claim.kind for claim in self.material_claims}
        required = {
            ResearchClaimKind.FACT,
            ResearchClaimKind.INFERENCE,
            ResearchClaimKind.ASSUMPTION,
        }
        if not required.issubset(kinds):
            raise ValueError(
                "Deep Research requires classified FACT, INFERENCE, and ASSUMPTION claims"
            )
        if any(not item.strip() for item in self.explicit_falsifiers):
            raise ValueError("Deep Research falsifiers cannot be blank")
        return self


class ResearchReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    DECISION_READY = "DECISION_READY"


class ResearchReadinessIssue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ResearchReadinessAssessment(KernelModel):
    status: ResearchReadinessStatus
    issues: tuple[ResearchReadinessIssue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ResearchReadinessAssessment":
        expected = (
            ResearchReadinessStatus.DECISION_READY
            if not self.issues
            else ResearchReadinessStatus.NOT_READY
        )
        if self.status is not expected:
            raise ValueError("Research readiness status must match its issue set")
        return self


class DeepResearchPackage(KernelModel):
    """Pure acceptance package; execution, persistence and model calls live outside."""

    label: str = Field(min_length=1, max_length=255)
    discovery: DiscoveryInput
    pre_research: PreResearchResult
    quick_research: QuickResearchResult
    deep_research: DeepResearchSupplement
    evidence_artifacts: tuple[EvidenceArtifact, ...] = Field(min_length=1)
    research_snapshot: ResearchSnapshot
    proposed_committed_at: AwareDateTime
    schema_version: Literal[1] = 1


class FrozenDeepResearchPackage(KernelModel):
    research_snapshot_id: UUID
    package_hash: str = Field(min_length=64, max_length=64)
    information_bundle_hash: str = Field(min_length=64, max_length=64)
    committed_at: AwareDateTime
    package: DeepResearchPackage
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_exact_package(self) -> "FrozenDeepResearchPackage":
        snapshot = self.package.research_snapshot
        if self.research_snapshot_id != snapshot.id:
            raise ValueError("Deep Research package must identify its ResearchSnapshot")
        if self.information_bundle_hash != snapshot.information_bundle_hash:
            raise ValueError("Deep Research package information hash must match ResearchSnapshot")
        if self.committed_at != self.package.proposed_committed_at:
            raise ValueError("Deep Research package commit time must match accepted package")
        if self.package_hash != deep_research_package_hash(self.package):
            raise ValueError("Deep Research package hash must cover the exact package")
        return self


class DeepResearchCommitResult(KernelModel):
    package_artifact: FrozenDeepResearchPackage
    research_snapshot: ResearchSnapshot

    @model_validator(mode="after")
    def validate_commit_result(self) -> "DeepResearchCommitResult":
        artifact = self.package_artifact
        snapshot = self.research_snapshot
        if snapshot.status is not ResearchStatus.COMMITTED:
            raise ValueError("Deep Research commit result requires COMMITTED ResearchSnapshot")
        if snapshot.id != artifact.research_snapshot_id:
            raise ValueError("Committed ResearchSnapshot must match accepted package identity")
        if snapshot.information_bundle_hash != artifact.information_bundle_hash:
            raise ValueError("Committed ResearchSnapshot must preserve accepted information hash")
        if snapshot.committed_at != artifact.committed_at:
            raise ValueError("Committed ResearchSnapshot must preserve accepted commit time")
        return self


def deep_research_information_bundle_hash(
    *,
    discovery: DiscoveryInput,
    pre_research: PreResearchResult,
    quick_research: QuickResearchResult,
    deep_research: DeepResearchSupplement,
    evidence_artifacts: tuple[EvidenceArtifact, ...],
    research_snapshot: ResearchSnapshot,
) -> str:
    """Freeze exact research meaning without creating a circular hash dependency."""

    snapshot_payload = research_snapshot.model_dump(
        mode="python",
        exclude={"information_bundle_hash", "status", "committed_at"},
    )
    return canonical_hash(
        {
            "schema_version": 1,
            "discovery": discovery,
            "pre_research": pre_research,
            "quick_research": quick_research,
            "deep_research": deep_research,
            "evidence_artifacts": tuple(
                sorted(evidence_artifacts, key=lambda item: str(item.id))
            ),
            "research_snapshot": snapshot_payload,
        }
    )


def deep_research_package_hash(package: DeepResearchPackage) -> str:
    return canonical_hash(package)


def assess_deep_research_readiness(
    package: DeepResearchPackage,
) -> ResearchReadinessAssessment:
    issues: list[ResearchReadinessIssue] = []
    discovery = package.discovery
    pre = package.pre_research
    quick = package.quick_research
    deep = package.deep_research
    evidence = package.evidence_artifacts
    snapshot = package.research_snapshot

    try:
        validate_funnel_transition(discovery, pre, quick, evidence)
    except DomainValidationError as exc:
        _issue(issues, "FUNNEL_INVALID", "research_funnel", str(exc))

    if quick.route is not QuickResearchRoute.DEEPEN:
        _issue(
            issues,
            "QUICK_NOT_DEEPENED",
            "quick_research.route",
            "Deep Research acceptance requires an explicit DEEPEN route",
        )
    if deep.discovery_id != discovery.discovery_id:
        _issue(
            issues,
            "DEEP_DISCOVERY_MISMATCH",
            "deep_research.discovery_id",
            "Deep Research must reference its Discovery Input",
        )
    if deep.quick_research_hash != canonical_hash(quick):
        _issue(
            issues,
            "DEEP_QUICK_HASH_MISMATCH",
            "deep_research.quick_research_hash",
            "Deep Research must reference the exact Quick Research state",
        )
    if deep.as_of != discovery.as_of:
        _issue(
            issues,
            "DEEP_PIT_MISMATCH",
            "deep_research.as_of",
            "Deep Research must share the Discovery PIT cutoff",
        )

    _validate_snapshot_contract(issues, discovery, deep, snapshot)
    _validate_evidence_contract(issues, package)

    expected_hash = deep_research_information_bundle_hash(
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        deep_research=deep,
        evidence_artifacts=evidence,
        research_snapshot=snapshot,
    )
    if snapshot.information_bundle_hash != expected_hash:
        _issue(
            issues,
            "INFORMATION_BUNDLE_HASH_MISMATCH",
            "research_snapshot.information_bundle_hash",
            "ResearchSnapshot must freeze the exact funnel, evidence, and research body",
        )

    earliest_commit = max(snapshot.as_of_datetime, snapshot.created_at)
    if package.proposed_committed_at < earliest_commit:
        _issue(
            issues,
            "COMMIT_BEFORE_PIT",
            "proposed_committed_at",
            "ResearchSnapshot commit cannot precede its PIT cutoff or creation time",
        )

    return ResearchReadinessAssessment(
        status=(
            ResearchReadinessStatus.DECISION_READY
            if not issues
            else ResearchReadinessStatus.NOT_READY
        ),
        issues=tuple(issues),
    )


def freeze_deep_research_package(
    package: DeepResearchPackage,
) -> FrozenDeepResearchPackage:
    assessment = assess_deep_research_readiness(package)
    if assessment.status is not ResearchReadinessStatus.DECISION_READY:
        codes = ", ".join(issue.code for issue in assessment.issues)
        raise DomainValidationError(
            f"Deep Research package is not decision-ready: {codes}"
        )
    return FrozenDeepResearchPackage(
        research_snapshot_id=package.research_snapshot.id,
        package_hash=deep_research_package_hash(package),
        information_bundle_hash=package.research_snapshot.information_bundle_hash or "",
        committed_at=package.proposed_committed_at,
        package=package,
    )


def commit_deep_research_package(
    package: DeepResearchPackage,
) -> DeepResearchCommitResult:
    """Pure state transition from accepted DRAFT package to COMMITTED ResearchSnapshot."""

    artifact = freeze_deep_research_package(package)
    reviewed = submit_for_review(package.research_snapshot)
    committed = commit_snapshot(reviewed, package.proposed_committed_at)
    return DeepResearchCommitResult(
        package_artifact=artifact,
        research_snapshot=committed,
    )


def _validate_snapshot_contract(
    issues: list[ResearchReadinessIssue],
    discovery: DiscoveryInput,
    deep: DeepResearchSupplement,
    snapshot: ResearchSnapshot,
) -> None:
    if snapshot.status is not ResearchStatus.DRAFT or snapshot.committed_at is not None:
        _issue(
            issues,
            "SNAPSHOT_NOT_DRAFT",
            "research_snapshot.status",
            "Deep Research acceptance starts from one uncommitted DRAFT snapshot",
        )
    if snapshot.as_of_datetime != discovery.as_of:
        _issue(
            issues,
            "SNAPSHOT_PIT_MISMATCH",
            "research_snapshot.as_of_datetime",
            "ResearchSnapshot must share the Discovery PIT cutoff",
        )

    declared_security_ids = {
        value for value in (discovery.ticker, discovery.security_id) if value is not None
    }
    if snapshot.ticker not in declared_security_ids:
        _issue(
            issues,
            "SNAPSHOT_DISCOVERY_IDENTITY_MISMATCH",
            "research_snapshot.ticker",
            "ResearchSnapshot security identity must be declared by Discovery",
        )

    expected_origin = f"DISCOVERY_INPUT:{discovery.discovery_id}"
    if snapshot.research_origin != expected_origin:
        _issue(
            issues,
            "SNAPSHOT_DISCOVERY_ORIGIN_MISMATCH",
            "research_snapshot.research_origin",
            "ResearchSnapshot origin must exactly identify its Discovery Input",
        )
    if snapshot.research_contract_version != DEEP_RESEARCH_CONTRACT_VERSION:
        _issue(
            issues,
            "CONTRACT_VERSION_UNSUPPORTED",
            "research_snapshot.research_contract_version",
            "Deep Research commit requires the research-odds-rehearsal-v1 contract",
        )

    required_text = {
        "core_thesis": snapshot.core_thesis,
        "variant_perception": snapshot.variant_perception,
        "market_expectations_narrative": snapshot.market_expectations_narrative,
        "normalized_earnings_notes": snapshot.normalized_earnings_notes,
        "valuation_framework": snapshot.valuation_framework,
        "model_risk_notes": snapshot.model_risk_notes,
    }
    for field, value in required_text.items():
        if value is None or not value.strip():
            _issue(
                issues,
                "REQUIRED_RESEARCH_FIELD_MISSING",
                f"research_snapshot.{field}",
                f"decision-ready Deep Research requires {field}",
            )

    required_structures = {
        "market_expectation_map": snapshot.market_expectation_map,
        "fundamental_clock_assessment": snapshot.fundamental_clock_assessment,
        "expectation_clock_assessment": snapshot.expectation_clock_assessment,
        "liquidity_clock_assessment": snapshot.liquidity_clock_assessment,
        "valuation_stress_spec": snapshot.valuation_stress_spec,
    }
    for field, value in required_structures.items():
        if not value:
            _issue(
                issues,
                "REQUIRED_RESEARCH_STRUCTURE_MISSING",
                f"research_snapshot.{field}",
                f"decision-ready Deep Research requires {field}",
            )

    if not snapshot.open_questions:
        _issue(
            issues,
            "OPEN_QUESTIONS_MISSING",
            "research_snapshot.open_questions",
            "decision-ready research must preserve unresolved questions",
        )

    indicators = snapshot.monitoring_plan.get("indicators")
    falsifiers = snapshot.monitoring_plan.get("falsifiers")
    if not isinstance(indicators, (list, tuple)) or not 3 <= len(indicators) <= 5:
        _issue(
            issues,
            "MONITORING_INDICATORS_INVALID",
            "research_snapshot.monitoring_plan.indicators",
            "decision-ready research requires three to five monitoring indicators",
        )
    if tuple(falsifiers or ()) != deep.explicit_falsifiers:
        _issue(
            issues,
            "FALSIFIERS_NOT_FROZEN",
            "research_snapshot.monitoring_plan.falsifiers",
            "ResearchSnapshot monitoring must freeze Deep Research falsifiers",
        )
    if any(
        finding.severity is AdversarialSeverity.BLOCK
        for finding in deep.adversarial_findings
    ):
        _issue(
            issues,
            "ADVERSARIAL_BLOCK_UNRESOLVED",
            "deep_research.adversarial_findings",
            "an adversarial BLOCK requires later re-research before commit",
        )

    if not 2 <= len(snapshot.scenarios) <= 5:
        _issue(
            issues,
            "SCENARIO_SET_NOT_SMALL",
            "research_snapshot.scenarios",
            "Deep Research v1 requires a small two-to-five-scenario distribution",
        )
    for scenario in snapshot.scenarios:
        if not scenario.assumptions or not scenario.financial_driver_values:
            _issue(
                issues,
                "SCENARIO_DRIVER_STRUCTURE_MISSING",
                f"research_snapshot.scenarios.{scenario.name}",
                "every scenario requires explicit assumptions and financial drivers",
            )


def _validate_evidence_contract(
    issues: list[ResearchReadinessIssue],
    package: DeepResearchPackage,
) -> None:
    discovery = package.discovery
    pre = package.pre_research
    quick = package.quick_research
    deep = package.deep_research
    snapshot = package.research_snapshot
    evidence = package.evidence_artifacts

    by_id = {artifact.id: artifact for artifact in evidence}
    if len(by_id) != len(evidence):
        _issue(
            issues,
            "EVIDENCE_ID_DUPLICATE",
            "evidence_artifacts",
            "Deep Research evidence ids must be unique",
        )
        return

    package_ids = set(by_id)
    for artifact in evidence:
        if artifact.available_at > discovery.as_of:
            _issue(
                issues,
                "EVIDENCE_AFTER_PIT",
                f"evidence_artifacts.{artifact.id}",
                "Deep Research cannot use evidence unavailable at the Discovery PIT",
            )

    discovery_ids = {source.evidence_artifact_id for source in discovery.source_lineage}
    pre_ids = _claim_evidence_ids(pre.material_claims)
    quick_support_ids = _claim_evidence_ids(quick.supporting_claims)
    quick_contradictory_ids = _claim_evidence_ids(quick.contradictory_claims)
    deep_ids = _claim_evidence_ids(deep.material_claims)
    cash_flow_ids = {
        artifact_id
        for scenario in snapshot.scenarios
        for flow in scenario.expected_cash_flows
        for artifact_id in flow.provenance_artifact_ids
    }
    link_ids = {link.evidence_artifact_id for link in snapshot.evidence_links}

    semantic_ids = (
        discovery_ids
        | pre_ids
        | quick_support_ids
        | quick_contradictory_ids
        | deep_ids
        | cash_flow_ids
    )
    referenced_ids = semantic_ids | link_ids

    missing = referenced_ids - package_ids
    for artifact_id in sorted(missing, key=str):
        _issue(
            issues,
            "EVIDENCE_MISSING",
            f"evidence_artifacts.{artifact_id}",
            "referenced Research evidence is absent from the accepted package",
        )

    extra = package_ids - referenced_ids
    for artifact_id in sorted(extra, key=str):
        _issue(
            issues,
            "EVIDENCE_NOT_REFERENCED",
            f"evidence_artifacts.{artifact_id}",
            "accepted Deep Research package cannot contain unreferenced evidence",
        )

    missing_snapshot_lineage = semantic_ids - link_ids
    for artifact_id in sorted(missing_snapshot_lineage, key=str):
        _issue(
            issues,
            "SNAPSHOT_EVIDENCE_LINEAGE_MISSING",
            f"research_snapshot.evidence_links.{artifact_id}",
            "all funnel and Deep Research evidence must reach ResearchSnapshot lineage",
        )

    relationships: dict[UUID, set[EvidenceRelationship]] = {}
    for link in snapshot.evidence_links:
        relationships.setdefault(link.evidence_artifact_id, set()).add(link.relationship)

    for artifact_id in sorted(quick_contradictory_ids, key=str):
        if EvidenceRelationship.OPPOSES not in relationships.get(artifact_id, set()):
            _issue(
                issues,
                "CONTRADICTORY_EVIDENCE_MISSING",
                f"research_snapshot.evidence_links.{artifact_id}",
                "Quick Research contradictory evidence must remain explicitly OPPOSES",
            )

    market_context_ids = _claim_evidence_ids(
        tuple(
            claim
            for claim in (*quick.supporting_claims, *quick.contradictory_claims, *deep.material_claims)
            if claim.kind is ResearchClaimKind.MARKET_CONTEXT
        )
    )
    for artifact_id in sorted(market_context_ids, key=str):
        if EvidenceRelationship.CONTEXT not in relationships.get(artifact_id, set()):
            _issue(
                issues,
                "MARKET_CONTEXT_RELATIONSHIP_MISSING",
                f"research_snapshot.evidence_links.{artifact_id}",
                "MARKET_CONTEXT evidence must remain explicitly CONTEXT",
            )

    supporting_fact_ids = _claim_evidence_ids(
        tuple(
            claim
            for claim in (*pre.material_claims, *quick.supporting_claims, *deep.material_claims)
            if claim.kind is ResearchClaimKind.FACT
        )
    )
    for artifact_id in sorted(supporting_fact_ids, key=str):
        if EvidenceRelationship.SUPPORTS not in relationships.get(artifact_id, set()):
            _issue(
                issues,
                "SUPPORTING_EVIDENCE_RELATIONSHIP_MISSING",
                f"research_snapshot.evidence_links.{artifact_id}",
                "supporting FACT evidence must remain explicitly SUPPORTS",
            )


def _claim_evidence_ids(claims: tuple[ResearchClaim, ...]) -> set[UUID]:
    return {
        artifact_id
        for claim in claims
        for artifact_id in claim.evidence_artifact_ids
    }


def _issue(
    issues: list[ResearchReadinessIssue],
    code: str,
    location: str,
    message: str,
) -> None:
    issues.append(
        ResearchReadinessIssue(code=code, location=location, message=message)
    )
