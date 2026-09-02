from __future__ import annotations

from collections import Counter
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .claim_audit_contract_v1 import (
    ClaimAuditContractV1Payload,
    ClaimAuditContractV1Status,
    ClaimAuditV1ClaimReview,
    assess_claim_audit_contract_v1,
)
from .deep_research import DeepResearchPackage, deep_research_package_hash
from .identity import canonical_hash
from .primitives import KernelModel
from .research_funnel import ResearchClaimKind
from .source_policy_v2 import (
    SOURCE_POLICY_V2_VERSION,
    ClaimSourceUseV2,
    is_source_use_admissible,
)


class ClaimAuditContractV2Status(StrEnum):
    NONCONFORMING = "NONCONFORMING"
    CONFORMING = "CONFORMING"


class ClaimAuditV2ClaimReview(KernelModel):
    review: ClaimAuditV1ClaimReview
    source_uses: tuple[ClaimSourceUseV2, ...] = ()

    @model_validator(mode="after")
    def validate_source_use_uniqueness(self) -> "ClaimAuditV2ClaimReview":
        ids = [item.evidence_artifact_id for item in self.source_uses]
        if len(ids) != len(set(ids)):
            raise ValueError("Claim Audit v2 source uses must be unique by EvidenceArtifact")
        return self


class ClaimAuditContractV2Payload(KernelModel):
    research_snapshot_id: UUID
    research_package_hash: str = Field(min_length=64, max_length=64)
    source_policy_version: str = Field(default=SOURCE_POLICY_V2_VERSION, min_length=1)
    reviews: tuple[ClaimAuditV2ClaimReview, ...]
    schema_version: int = Field(default=2, ge=2)


class ClaimAuditContractV2Issue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ClaimAuditContractV2Assessment(KernelModel):
    status: ClaimAuditContractV2Status
    issues: tuple[ClaimAuditContractV2Issue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ClaimAuditContractV2Assessment":
        expected = (
            ClaimAuditContractV2Status.CONFORMING
            if not self.issues
            else ClaimAuditContractV2Status.NONCONFORMING
        )
        if self.status is not expected:
            raise ValueError("Claim Audit Contract v2 status must match its issue set")
        return self


def assess_claim_audit_contract_v2(
    package: DeepResearchPackage,
    payload: ClaimAuditContractV2Payload,
) -> ClaimAuditContractV2Assessment:
    """Add source qualification to v1 source-fidelity checks.

    v2 remains Research Method policy. It never decides Kernel commit authority.
    """

    issues: list[ClaimAuditContractV2Issue] = []
    if payload.source_policy_version != SOURCE_POLICY_V2_VERSION:
        _issue(issues, "SOURCE_POLICY_VERSION_UNSUPPORTED", "payload.source_policy_version")

    v1_payload = ClaimAuditContractV1Payload(
        research_snapshot_id=payload.research_snapshot_id,
        research_package_hash=payload.research_package_hash,
        reviews=tuple(item.review for item in payload.reviews),
    )
    v1_assessment = assess_claim_audit_contract_v1(package, v1_payload)
    if v1_assessment.status is not ClaimAuditContractV1Status.CONFORMING:
        for item in v1_assessment.issues:
            issues.append(
                ClaimAuditContractV2Issue(
                    code=f"V1_{item.code}",
                    location=item.location,
                    message=f"v1 claim-audit prerequisite failed: {item.message}",
                )
            )

    if payload.research_snapshot_id != package.research_snapshot.id:
        _issue(issues, "SNAPSHOT_ID_MISMATCH", "payload.research_snapshot_id")
    if payload.research_package_hash != deep_research_package_hash(package):
        _issue(issues, "PACKAGE_HASH_MISMATCH", "payload.research_package_hash")

    material_claims = (
        *package.pre_research.material_claims,
        *package.quick_research.supporting_claims,
        *package.quick_research.contradictory_claims,
        *package.deep_research.material_claims,
    )
    claim_counts = Counter(canonical_hash(claim) for claim in material_claims)
    review_counts = Counter(canonical_hash(item.review.claim) for item in payload.reviews)
    if claim_counts != review_counts:
        _issue(issues, "CLAIM_COVERAGE_MISMATCH", "payload.reviews")

    for index, item in enumerate(payload.reviews):
        claim = item.review.claim
        location = f"payload.reviews.{index}"
        source_use_ids = {use.evidence_artifact_id for use in item.source_uses}
        claim_ids = set(claim.evidence_artifact_ids)

        if claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
            if source_use_ids != claim_ids:
                _issue(
                    issues,
                    "SOURCE_USE_COVERAGE_MISMATCH",
                    f"{location}.source_uses",
                )
            for use_index, use in enumerate(item.source_uses):
                if not is_source_use_admissible(
                    claim_kind=claim.kind,
                    source_role=use.source_role,
                    assertion_scope=use.assertion_scope,
                ):
                    _issue(
                        issues,
                        "SOURCE_ADMISSIBILITY_FAILED",
                        f"{location}.source_uses.{use_index}",
                    )
        elif item.source_uses:
            # Research-owned INFERENCE/ASSUMPTION may cite inputs, but v2 does not
            # pretend those sources make the cognition factual. Keep any declared
            # source uses inside the claim's exact lineage.
            if not source_use_ids.issubset(claim_ids):
                _issue(
                    issues,
                    "SOURCE_USE_OUTSIDE_LINEAGE",
                    f"{location}.source_uses",
                )

    return ClaimAuditContractV2Assessment(
        status=(
            ClaimAuditContractV2Status.CONFORMING
            if not issues
            else ClaimAuditContractV2Status.NONCONFORMING
        ),
        issues=tuple(issues),
    )


def _issue(
    issues: list[ClaimAuditContractV2Issue],
    code: str,
    location: str,
) -> None:
    issues.append(
        ClaimAuditContractV2Issue(
            code=code,
            location=location,
            message=code.replace("_", " ").title(),
        )
    )
