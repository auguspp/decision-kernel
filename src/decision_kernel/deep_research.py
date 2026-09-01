from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .evidence import EvidenceArtifact, EvidenceRelationship
from .identity import canonical_hash
from .primitives import AwareDateTime, DomainValidationError, KernelModel
from .research import (
    PROBABILITY_TOLERANCE,
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


# Historical method identity retained for the versioned Research Contract v1 layer.
# Kernel acceptance does not require or interpret this value.
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
    """Executor-agnostic research output bound to one exact Quick Research state.

    The kernel freezes lineage and PIT here. Method-specific requirements such as a particular
    mixture of FACT/INFERENCE/ASSUMPTION claims or adversarial-review shape belong to a versioned
    Research Contract, not this constitutional model.
    """

    discovery_id: str = Field(min_length=1, max_length=255)
    quick_research_hash: str = Field(min_length=64, max_length=64)
    as_of: AwareDateTime
    material_claims: tuple[ResearchClaim, ...] = Field(min_length=1)
    explicit_falsifiers: tuple[str, ...] = ()
    adversarial_findings: tuple[AdversarialFinding, ...] = ()
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_text(self) -> "DeepResearchSupplement":
        if any(not item.strip() for item in self.explicit_falsifiers):
            raise ValueError("Deep Research falsifiers cannot be blank")
        return self


class ResearchAcceptanceStatus(StrEnum):
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"


class ResearchAcceptanceIssue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ResearchAcceptanceAssessment(KernelModel):
    status: ResearchAcceptanceStatus
    issues: tuple[ResearchAcceptanceIssue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ResearchAcceptanceAssessment":
        expected = (
            ResearchAcceptanceStatus.ACCEPTED
            if not self.issues
            else ResearchAcceptanceStatus.REJECTED
        )
        if self.status is not expected:
            raise ValueError("Research acceptance status must match its issue set")
        return self


class DeepResearchPackage(KernelModel):
    """Pure research acceptance package; execution and method policy live outside."""

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


def assess_deep_research_acceptance(
    package: DeepResearchPackage,
) -> ResearchAcceptanceAssessment:
    """Check only invariants required to freeze research for Odds and Human accountability."""

    issues: list[ResearchAcceptanceIssue] = []
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

    _validate_snapshot_invariants(issues, discovery, deep, snapshot)
    _validate_evidence_invariants(issues, package)

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

    return ResearchAcceptanceAssessment(
        status=(
            ResearchAcceptanceStatus.ACCEPTED
            if not issues
            else ResearchAcceptanceStatus.REJECTED
        ),
        issues=tuple(issues),
    )


def freeze_deep_research_package(
    package: DeepResearchPackage,
) -> FrozenDeepResearchPackage:
    assessment = assess_deep_research_acceptance(package)
    if assessment.status is not ResearchAcceptanceStatus.ACCEPTED:
        codes = ", ".join(issue.code for issue in assessment.issues)
        raise DomainValidationError(
            f"Deep Research package violates kernel acceptance: {codes}"
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
    """Pure state transition from kernel-accepted DRAFT package to COMMITTED snapshot."""

    artifact = freeze_deep_research_package(package)
    reviewed = submit_for_review(package.research_snapshot)
    committed = commit_snapshot(reviewed, package.proposed_committed_at)
    return DeepResearchCommitResult(
        package_artifact=artifact,
        research_snapshot=committed,
    )


def _validate_snapshot_invariants(
    issues: list[ResearchAcceptanceIssue],
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

    required_accountability_text = {
        "core_thesis": snapshot.core_thesis,
        "market_expectations_narrative": snapshot.market_expectations_narrative,
        "model_risk_notes": snapshot.model_risk_notes,
    }
    for field, value in required_accountability_text.items():
        if value is None or not value.strip():
            _issue(
                issues,
                "CORE_ACCOUNTABILITY_FIELD_MISSING",
                f"research_snapshot.{field}",
                f"kernel decision path requires {field}",
            )

    if not snapshot.thesis_invalidation:
        _issue(
            issues,
            "THESIS_INVALIDATION_MISSING",
            "research_snapshot.thesis_invalidation",
            "Human accountability requires explicit thesis invalidation conditions",
        )
    if deep.explicit_falsifiers and tuple(snapshot.thesis_invalidation) != tuple(
        deep.explicit_falsifiers
    ):
        _issue(
            issues,
            "FALSIFIER_LINEAGE_MISMATCH",
            "research_snapshot.thesis_invalidation",
            "when Deep Research declares falsifiers, the snapshot must preserve them exactly",
        )

    probability_sum = sum(
        (scenario.probability for scenario in snapshot.scenarios), Decimal("0")
    )
    if not snapshot.scenarios or abs(probability_sum - Decimal("1")) > PROBABILITY_TOLERANCE:
        _issue(
            issues,
            "SCENARIO_DISTRIBUTION_INCOMPLETE",
            "research_snapshot.scenarios",
            "Odds requires at least one complete Scenario probability distribution",
        )


def _validate_evidence_invariants(
    issues: list[ResearchAcceptanceIssue],
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

    for artifact_id in sorted(referenced_ids - package_ids, key=str):
        _issue(
            issues,
            "EVIDENCE_MISSING",
            f"evidence_artifacts.{artifact_id}",
            "referenced Research evidence is absent from the accepted package",
        )

    for artifact_id in sorted(package_ids - referenced_ids, key=str):
        _issue(
            issues,
            "EVIDENCE_NOT_REFERENCED",
            f"evidence_artifacts.{artifact_id}",
            "accepted Deep Research package cannot contain unreferenced evidence",
        )

    for artifact_id in sorted(semantic_ids - link_ids, key=str):
        _issue(
            issues,
            "SNAPSHOT_EVIDENCE_LINEAGE_MISSING",
            f"research_snapshot.evidence_links.{artifact_id}",
            "all semantic evidence must reach ResearchSnapshot lineage",
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
    issues: list[ResearchAcceptanceIssue],
    code: str,
    location: str,
    message: str,
) -> None:
    issues.append(
        ResearchAcceptanceIssue(code=code, location=location, message=message)
    )
