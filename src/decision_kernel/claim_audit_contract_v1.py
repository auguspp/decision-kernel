from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import DeepResearchPackage, deep_research_package_hash
from .evidence import EvidenceArtifact
from .identity import canonical_hash
from .primitives import KernelModel
from .research_funnel import ResearchClaim, ResearchClaimKind


class ClaimAuditV1CheckStatus(StrEnum):
    VERIFIED = "VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FAILED = "FAILED"


class ClaimAuditV1NumericalOperation(StrEnum):
    IDENTITY = "IDENTITY"
    SUM = "SUM"
    DIFFERENCE = "DIFFERENCE"
    PRODUCT = "PRODUCT"
    RATIO = "RATIO"


class ClaimAuditV1EvidenceNumericalInput(KernelModel):
    evidence_artifact_id: UUID
    field_name: str = Field(min_length=1, max_length=128)
    value: Decimal
    unit: str = Field(min_length=1, max_length=64)


class ClaimAuditV1LiteralOperand(KernelModel):
    value: Decimal
    reason: str = Field(min_length=1, max_length=255)


class ClaimAuditV1NumericalCheck(KernelModel):
    operation: ClaimAuditV1NumericalOperation
    operands: tuple[Decimal, ...] = Field(min_length=1)
    claimed_result: Decimal
    unit: str = Field(min_length=1, max_length=64)
    evidence_inputs: tuple[ClaimAuditV1EvidenceNumericalInput, ...] = ()
    literal_operands: tuple[ClaimAuditV1LiteralOperand, ...] = ()

    @model_validator(mode="after")
    def validate_exact_recalculation(self) -> "ClaimAuditV1NumericalCheck":
        calculated = calculate_claim_audit_v1_result(self.operation, self.operands)
        if calculated != self.claimed_result:
            raise ValueError("numerical claim does not match deterministic recalculation")

        bound_operands = (
            *(item.value for item in self.evidence_inputs),
            *(item.value for item in self.literal_operands),
        )
        if Counter(self.operands) != Counter(bound_operands):
            raise ValueError(
                "every numerical operand must bind to an EvidenceArtifact value or explicit literal"
            )
        return self


class ClaimAuditV1ClaimReview(KernelModel):
    claim: ResearchClaim
    accepted: bool
    identity: ClaimAuditV1CheckStatus
    period_or_date: ClaimAuditV1CheckStatus
    units: ClaimAuditV1CheckStatus
    source_location: ClaimAuditV1CheckStatus
    evidence_support: ClaimAuditV1CheckStatus
    classification: ClaimAuditV1CheckStatus
    numerical_recalculation: ClaimAuditV1CheckStatus
    numerical_assertions: tuple[Decimal, ...] = ()
    numerical_checks: tuple[ClaimAuditV1NumericalCheck, ...] = ()
    resolution: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_numerical_shape(self) -> "ClaimAuditV1ClaimReview":
        if self.numerical_assertions:
            if self.numerical_recalculation is ClaimAuditV1CheckStatus.NOT_APPLICABLE:
                raise ValueError(
                    "declared numerical assertions cannot be NOT_APPLICABLE"
                )
            if self.numerical_recalculation is ClaimAuditV1CheckStatus.VERIFIED:
                if not self.numerical_checks:
                    raise ValueError(
                        "verified numerical assertions require deterministic checks"
                    )
                checked = tuple(check.claimed_result for check in self.numerical_checks)
                if Counter(checked) != Counter(self.numerical_assertions):
                    raise ValueError(
                        "numerical checks must cover every declared numerical assertion exactly"
                    )
        else:
            if self.numerical_recalculation is ClaimAuditV1CheckStatus.VERIFIED:
                raise ValueError(
                    "VERIFIED numerical recalculation requires declared numerical assertions"
                )
            if self.numerical_checks:
                raise ValueError(
                    "numerical checks require declared numerical assertions"
                )
        return self


class ClaimAuditContractV1Payload(KernelModel):
    research_snapshot_id: UUID
    research_package_hash: str = Field(min_length=64, max_length=64)
    reviews: tuple[ClaimAuditV1ClaimReview, ...]
    schema_version: int = Field(default=1, ge=1)


class ClaimAuditContractV1Status(StrEnum):
    NONCONFORMING = "NONCONFORMING"
    CONFORMING = "CONFORMING"


class ClaimAuditContractV1Issue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ClaimAuditContractV1Assessment(KernelModel):
    status: ClaimAuditContractV1Status
    issues: tuple[ClaimAuditContractV1Issue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ClaimAuditContractV1Assessment":
        expected = (
            ClaimAuditContractV1Status.CONFORMING
            if not self.issues
            else ClaimAuditContractV1Status.NONCONFORMING
        )
        if self.status is not expected:
            raise ValueError("Claim Audit Contract v1 status must match its issue set")
        return self


def calculate_claim_audit_v1_result(
    operation: ClaimAuditV1NumericalOperation,
    operands: tuple[Decimal, ...],
) -> Decimal:
    """Deterministically recalculate one explicitly declared numerical assertion."""

    if not operands:
        raise ValueError("numerical operation requires at least one operand")

    with localcontext() as context:
        context.prec = 80
        if operation is ClaimAuditV1NumericalOperation.IDENTITY:
            if len(operands) != 1:
                raise ValueError("IDENTITY requires exactly one operand")
            return operands[0]
        if operation is ClaimAuditV1NumericalOperation.SUM:
            return sum(operands, Decimal("0"))
        if operation is ClaimAuditV1NumericalOperation.DIFFERENCE:
            if len(operands) != 2:
                raise ValueError("DIFFERENCE requires exactly two operands")
            return operands[0] - operands[1]
        if operation is ClaimAuditV1NumericalOperation.PRODUCT:
            calculated = Decimal("1")
            for operand in operands:
                calculated *= operand
            return calculated
        if operation is ClaimAuditV1NumericalOperation.RATIO:
            if len(operands) != 2 or operands[1] == 0:
                raise ValueError(
                    "RATIO requires two operands and a non-zero denominator"
                )
            return operands[0] / operands[1]

    raise ValueError("unsupported numerical operation")


def assess_claim_audit_contract_v1(
    package: DeepResearchPackage,
    payload: ClaimAuditContractV1Payload,
) -> ClaimAuditContractV1Assessment:
    """Assess independent material-claim audit quality without Kernel authority."""

    issues: list[ClaimAuditContractV1Issue] = []
    snapshot = package.research_snapshot

    if payload.research_snapshot_id != snapshot.id:
        _issue(
            issues,
            "SNAPSHOT_ID_MISMATCH",
            "payload.research_snapshot_id",
            "Claim Audit Contract v1 must bind to the exact ResearchSnapshot",
        )

    expected_package_hash = deep_research_package_hash(package)
    if payload.research_package_hash != expected_package_hash:
        _issue(
            issues,
            "PACKAGE_HASH_MISMATCH",
            "payload.research_package_hash",
            "Claim Audit Contract v1 must bind to the exact Research Method v1 package",
        )

    claims = _material_claims(package)
    claim_hashes = tuple(canonical_hash(claim) for claim in claims)
    review_hashes = tuple(canonical_hash(review.claim) for review in payload.reviews)
    if Counter(claim_hashes) != Counter(review_hashes):
        _issue(
            issues,
            "CLAIM_COVERAGE_MISMATCH",
            "payload.reviews",
            "Claim Audit Contract v1 must cover every exact material claim once",
        )

    evidence_by_id = {artifact.id: artifact for artifact in package.evidence_artifacts}
    if len(evidence_by_id) != len(package.evidence_artifacts):
        _issue(
            issues,
            "EVIDENCE_ID_DUPLICATE",
            "package.evidence_artifacts",
            "Claim Audit Contract v1 requires unique EvidenceArtifact ids",
        )

    claim_by_hash = {canonical_hash(claim): claim for claim in claims}
    for index, review in enumerate(payload.reviews):
        claim = claim_by_hash.get(canonical_hash(review.claim))
        if claim is None:
            continue
        _assess_one_review(
            issues=issues,
            index=index,
            claim=claim,
            review=review,
            evidence_by_id=evidence_by_id,
        )

    return ClaimAuditContractV1Assessment(
        status=(
            ClaimAuditContractV1Status.CONFORMING
            if not issues
            else ClaimAuditContractV1Status.NONCONFORMING
        ),
        issues=tuple(issues),
    )


def _material_claims(package: DeepResearchPackage) -> tuple[ResearchClaim, ...]:
    return (
        *package.pre_research.material_claims,
        *package.quick_research.supporting_claims,
        *package.quick_research.contradictory_claims,
        *package.deep_research.material_claims,
    )


def _assess_one_review(
    *,
    issues: list[ClaimAuditContractV1Issue],
    index: int,
    claim: ResearchClaim,
    review: ClaimAuditV1ClaimReview,
    evidence_by_id: dict[UUID, EvidenceArtifact],
) -> None:
    location = f"payload.reviews.{index}"

    if not review.accepted:
        _issue(
            issues,
            "CLAIM_REJECTED",
            location,
            "unsupported material claims must be removed, downgraded, or unresolved",
        )

    if review.classification is not ClaimAuditV1CheckStatus.VERIFIED:
        _issue(
            issues,
            "CLASSIFICATION_UNVERIFIED",
            f"{location}.classification",
            "material claim classification must be independently verified",
        )

    if ClaimAuditV1CheckStatus.FAILED in {
        review.identity,
        review.period_or_date,
        review.units,
        review.source_location,
        review.evidence_support,
        review.numerical_recalculation,
    }:
        _issue(
            issues,
            "AUDIT_CHECK_FAILED",
            location,
            "material claim audit contains a failed check",
        )

    evidenced = claim.kind in {
        ResearchClaimKind.FACT,
        ResearchClaimKind.MARKET_CONTEXT,
    }
    if evidenced:
        required = (
            review.identity,
            review.period_or_date,
            review.units,
            review.source_location,
            review.evidence_support,
        )
        if any(item is not ClaimAuditV1CheckStatus.VERIFIED for item in required):
            _issue(
                issues,
                "EVIDENCE_AUDIT_INCOMPLETE",
                location,
                "FACT and MARKET_CONTEXT require verified identity, date/period, units, source, and evidence",
            )
        missing = set(claim.evidence_artifact_ids) - set(evidence_by_id)
        if missing:
            _issue(
                issues,
                "EVIDENCE_MISSING",
                location,
                "audited claim references EvidenceArtifacts absent from the package",
            )

    if review.numerical_assertions:
        if review.numerical_recalculation is not ClaimAuditV1CheckStatus.VERIFIED:
            _issue(
                issues,
                "NUMERICAL_RECALCULATION_UNVERIFIED",
                f"{location}.numerical_recalculation",
                "declared numerical assertions require verified deterministic recalculation",
            )
        for check_index, check in enumerate(review.numerical_checks):
            _assess_numerical_check(
                issues=issues,
                location=f"{location}.numerical_checks.{check_index}",
                claim=claim,
                check=check,
                evidenced=evidenced,
                evidence_by_id=evidence_by_id,
            )


def _assess_numerical_check(
    *,
    issues: list[ClaimAuditContractV1Issue],
    location: str,
    claim: ResearchClaim,
    check: ClaimAuditV1NumericalCheck,
    evidenced: bool,
    evidence_by_id: dict[UUID, EvidenceArtifact],
) -> None:
    if evidenced and not check.evidence_inputs:
        _issue(
            issues,
            "NUMERIC_EVIDENCE_INPUT_MISSING",
            location,
            "evidenced numerical claims require structured EvidenceArtifact inputs",
        )

    for source_input in check.evidence_inputs:
        if source_input.evidence_artifact_id not in claim.evidence_artifact_ids:
            _issue(
                issues,
                "NUMERIC_INPUT_OUTSIDE_LINEAGE",
                location,
                "numerical input must stay inside the claim EvidenceArtifact lineage",
            )
            continue

        artifact = evidence_by_id.get(source_input.evidence_artifact_id)
        if artifact is None:
            _issue(
                issues,
                "NUMERIC_EVIDENCE_MISSING",
                location,
                "numerical input references an EvidenceArtifact absent from the package",
            )
            continue

        values = artifact.extracted_structured_values
        if values is None or source_input.field_name not in values:
            _issue(
                issues,
                "NUMERIC_SOURCE_VALUE_MISSING",
                location,
                "numerical input lacks an exact structured EvidenceArtifact source value",
            )
            continue

        raw_value = values[source_input.field_name]
        if isinstance(raw_value, bool):
            _issue(
                issues,
                "NUMERIC_SOURCE_VALUE_INVALID",
                location,
                "boolean evidence cannot support a numerical assertion",
            )
            continue

        try:
            resolved_value = Decimal(str(raw_value))
        except (InvalidOperation, ValueError):
            _issue(
                issues,
                "NUMERIC_SOURCE_VALUE_INVALID",
                location,
                "structured EvidenceArtifact value is not an exact decimal",
            )
            continue

        if resolved_value != source_input.value:
            _issue(
                issues,
                "NUMERIC_SOURCE_VALUE_MISMATCH",
                location,
                "numerical input does not match the structured EvidenceArtifact value",
            )


def _issue(
    issues: list[ClaimAuditContractV1Issue],
    code: str,
    location: str,
    message: str,
) -> None:
    issues.append(
        ClaimAuditContractV1Issue(
            code=code,
            location=location,
            message=message,
        )
    )
