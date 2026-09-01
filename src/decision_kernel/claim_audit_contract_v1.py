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


class ClaimAuditV1Check(StrEnum):
    IDENTITY = "IDENTITY"
    PERIOD_OR_DATE = "PERIOD_OR_DATE"
    UNITS = "UNITS"
    SOURCE_LOCATION = "SOURCE_LOCATION"
    EVIDENCE_SUPPORT = "EVIDENCE_SUPPORT"
    CLASSIFICATION = "CLASSIFICATION"
    NUMERICAL_RECALCULATION = "NUMERICAL_RECALCULATION"


class ClaimAuditV1NumericalOperation(StrEnum):
    IDENTITY = "IDENTITY"
    SUM = "SUM"
    DIFFERENCE = "DIFFERENCE"
    PRODUCT = "PRODUCT"
    RATIO = "RATIO"


class ClaimAuditV1EvidenceInput(KernelModel):
    evidence_artifact_id: UUID
    field_name: str = Field(min_length=1, max_length=128)
    value: Decimal
    unit: str = Field(min_length=1, max_length=64)


class ClaimAuditV1LiteralInput(KernelModel):
    value: Decimal
    reason: str = Field(min_length=1, max_length=255)


class ClaimAuditV1NumericalCheck(KernelModel):
    operation: ClaimAuditV1NumericalOperation
    operands: tuple[Decimal, ...] = Field(min_length=1)
    claimed_result: Decimal
    unit: str = Field(min_length=1, max_length=64)
    evidence_inputs: tuple[ClaimAuditV1EvidenceInput, ...] = ()
    literal_inputs: tuple[ClaimAuditV1LiteralInput, ...] = ()

    @model_validator(mode="after")
    def validate_recalculation(self) -> "ClaimAuditV1NumericalCheck":
        if calculate_claim_audit_v1_result(self.operation, self.operands) != self.claimed_result:
            raise ValueError("numerical claim does not match deterministic recalculation")
        bound = (
            *(item.value for item in self.evidence_inputs),
            *(item.value for item in self.literal_inputs),
        )
        if Counter(self.operands) != Counter(bound):
            raise ValueError(
                "every numerical operand must bind to Evidence or an explicit literal"
            )
        return self


class ClaimAuditV1ClaimReview(KernelModel):
    claim: ResearchClaim
    accepted: bool
    verified_checks: frozenset[ClaimAuditV1Check] = frozenset()
    failed_checks: frozenset[ClaimAuditV1Check] = frozenset()
    numerical_assertions: tuple[Decimal, ...] = ()
    numerical_checks: tuple[ClaimAuditV1NumericalCheck, ...] = ()
    resolution: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_review_shape(self) -> "ClaimAuditV1ClaimReview":
        if self.verified_checks & self.failed_checks:
            raise ValueError("an audit check cannot be both verified and failed")
        checked_results = tuple(check.claimed_result for check in self.numerical_checks)
        if Counter(checked_results) != Counter(self.numerical_assertions):
            raise ValueError(
                "numerical checks must cover every declared numerical assertion exactly"
            )
        if self.numerical_assertions and (
            ClaimAuditV1Check.NUMERICAL_RECALCULATION not in self.verified_checks
            and ClaimAuditV1Check.NUMERICAL_RECALCULATION not in self.failed_checks
        ):
            raise ValueError(
                "declared numerical assertions require an explicit recalculation result"
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
            raise ValueError("Claim Audit Contract v1 status must match its issues")
        return self


def calculate_claim_audit_v1_result(
    operation: ClaimAuditV1NumericalOperation,
    operands: tuple[Decimal, ...],
) -> Decimal:
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
        if operation is ClaimAuditV1NumericalOperation.PRODUCT:
            result = Decimal("1")
            for operand in operands:
                result *= operand
            return result
        if operation is ClaimAuditV1NumericalOperation.DIFFERENCE:
            if len(operands) != 2:
                raise ValueError("DIFFERENCE requires exactly two operands")
            return operands[0] - operands[1]
        if operation is ClaimAuditV1NumericalOperation.RATIO:
            if len(operands) != 2 or operands[1] == 0:
                raise ValueError("RATIO requires two operands and a non-zero denominator")
            return operands[0] / operands[1]
    raise ValueError("unsupported numerical operation")


def assess_claim_audit_contract_v1(
    package: DeepResearchPackage,
    payload: ClaimAuditContractV1Payload,
) -> ClaimAuditContractV1Assessment:
    """Assess independent claim-audit quality; never decide Kernel commit authority."""

    issues: list[ClaimAuditContractV1Issue] = []
    if payload.research_snapshot_id != package.research_snapshot.id:
        _issue(issues, "SNAPSHOT_ID_MISMATCH", "payload.research_snapshot_id")
    if payload.research_package_hash != deep_research_package_hash(package):
        _issue(issues, "PACKAGE_HASH_MISMATCH", "payload.research_package_hash")

    claims = _material_claims(package)
    claim_hashes = tuple(canonical_hash(claim) for claim in claims)
    review_hashes = tuple(canonical_hash(review.claim) for review in payload.reviews)
    if Counter(claim_hashes) != Counter(review_hashes):
        _issue(issues, "CLAIM_COVERAGE_MISMATCH", "payload.reviews")

    evidence = {item.id: item for item in package.evidence_artifacts}
    if len(evidence) != len(package.evidence_artifacts):
        _issue(issues, "EVIDENCE_ID_DUPLICATE", "package.evidence_artifacts")

    claims_by_hash = {canonical_hash(claim): claim for claim in claims}
    for index, review in enumerate(payload.reviews):
        claim = claims_by_hash.get(canonical_hash(review.claim))
        if claim is not None:
            _assess_review(issues, index, claim, review, evidence)

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


def _assess_review(
    issues: list[ClaimAuditContractV1Issue],
    index: int,
    claim: ResearchClaim,
    review: ClaimAuditV1ClaimReview,
    evidence: dict[UUID, EvidenceArtifact],
) -> None:
    location = f"payload.reviews.{index}"
    if not review.accepted:
        _issue(issues, "CLAIM_REJECTED", location)
    if review.failed_checks:
        _issue(issues, "AUDIT_CHECK_FAILED", location)
    if ClaimAuditV1Check.CLASSIFICATION not in review.verified_checks:
        _issue(issues, "CLASSIFICATION_UNVERIFIED", location)

    evidenced = claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}
    if evidenced:
        required = {
            ClaimAuditV1Check.IDENTITY,
            ClaimAuditV1Check.PERIOD_OR_DATE,
            ClaimAuditV1Check.UNITS,
            ClaimAuditV1Check.SOURCE_LOCATION,
            ClaimAuditV1Check.EVIDENCE_SUPPORT,
        }
        if not required.issubset(review.verified_checks):
            _issue(issues, "EVIDENCE_AUDIT_INCOMPLETE", location)
        if not set(claim.evidence_artifact_ids).issubset(evidence):
            _issue(issues, "EVIDENCE_MISSING", location)

    if review.numerical_assertions and (
        ClaimAuditV1Check.NUMERICAL_RECALCULATION not in review.verified_checks
    ):
        _issue(issues, "NUMERICAL_RECALCULATION_UNVERIFIED", location)

    for check_index, check in enumerate(review.numerical_checks):
        check_location = f"{location}.numerical_checks.{check_index}"
        if evidenced and not check.evidence_inputs:
            _issue(issues, "NUMERIC_EVIDENCE_INPUT_MISSING", check_location)
        for source in check.evidence_inputs:
            if source.evidence_artifact_id not in claim.evidence_artifact_ids:
                _issue(issues, "NUMERIC_INPUT_OUTSIDE_LINEAGE", check_location)
                continue
            artifact = evidence.get(source.evidence_artifact_id)
            if artifact is None:
                _issue(issues, "NUMERIC_EVIDENCE_MISSING", check_location)
                continue
            raw = (artifact.extracted_structured_values or {}).get(source.field_name)
            try:
                resolved = None if isinstance(raw, bool) else Decimal(str(raw))
            except (InvalidOperation, ValueError):
                resolved = None
            if resolved is None:
                _issue(issues, "NUMERIC_SOURCE_VALUE_INVALID", check_location)
            elif resolved != source.value:
                _issue(issues, "NUMERIC_SOURCE_VALUE_MISMATCH", check_location)


def _issue(
    issues: list[ClaimAuditContractV1Issue],
    code: str,
    location: str,
) -> None:
    issues.append(
        ClaimAuditContractV1Issue(
            code=code,
            location=location,
            message=code.replace("_", " ").title(),
        )
    )
