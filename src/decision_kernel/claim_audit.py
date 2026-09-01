from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import DeepResearchSupplement
from .evidence import EvidenceArtifact
from .identity import canonical_hash
from .primitives import DomainValidationError, KernelModel
from .research_funnel import (
    PreResearchResult,
    QuickResearchResult,
    ResearchClaim,
    ResearchClaimKind,
)


class AuditCheckStatus(StrEnum):
    VERIFIED = "VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FAILED = "FAILED"


class NumericalOperation(StrEnum):
    IDENTITY = "IDENTITY"
    SUM = "SUM"
    DIFFERENCE = "DIFFERENCE"
    PRODUCT = "PRODUCT"
    RATIO = "RATIO"


_ALLOWED_CODE_CONSTANT_OPERANDS = frozenset(
    Decimal(value)
    for value in (
        "-1",
        "0.0001",
        "0.001",
        "0.01",
        "0.1",
        "10",
        "100",
        "1000",
        "10000",
        "1000000",
        "100000000",
        "1000000000",
    )
)


class EvidenceNumericalInput(KernelModel):
    evidence_artifact_id: UUID
    field_name: str = Field(min_length=1, max_length=128)
    value: Decimal
    unit: str = Field(min_length=1, max_length=64)


class DeterministicNumericalCheck(KernelModel):
    operation: NumericalOperation
    operands: tuple[Decimal, ...] = Field(min_length=1)
    claimed_result: Decimal
    unit: str = Field(min_length=1, max_length=64)
    evidence_inputs: tuple[EvidenceNumericalInput, ...] = ()
    code_constant_operands: tuple[Decimal, ...] = ()

    @model_validator(mode="after")
    def validate_recalculation(self) -> "DeterministicNumericalCheck":
        calculated = calculate_numerical_result(self.operation, self.operands)
        if calculated != self.claimed_result:
            raise ValueError("numerical claim does not match deterministic recalculation")
        if any(item.value not in self.operands for item in self.evidence_inputs):
            raise ValueError(
                "evidence numerical inputs must be explicit calculation operands"
            )
        if any(item not in self.operands for item in self.code_constant_operands):
            raise ValueError("code constants must be explicit calculation operands")
        if any(
            item not in _ALLOWED_CODE_CONSTANT_OPERANDS
            for item in self.code_constant_operands
        ):
            raise ValueError("numerical check contains an unapproved code constant")
        if self.code_constant_operands:
            if self.operation not in {
                NumericalOperation.PRODUCT,
                NumericalOperation.RATIO,
            }:
                raise ValueError("code constants are limited to scale/sign operations")
            if (
                len(self.code_constant_operands) != 1
                or len(self.evidence_inputs) != 1
                or len(self.operands) != 2
            ):
                raise ValueError(
                    "scale/sign operations require one Evidence operand and one code constant"
                )
            if (
                self.operation is NumericalOperation.RATIO
                and self.operands[1] != self.code_constant_operands[0]
            ):
                raise ValueError("a RATIO code constant must be the denominator scale")
        return self


class MaterialClaimAudit(KernelModel):
    claim: ResearchClaim
    accepted: bool
    identity: AuditCheckStatus
    period_or_date: AuditCheckStatus
    units: AuditCheckStatus
    source_location: AuditCheckStatus
    evidence_support: AuditCheckStatus
    classification: AuditCheckStatus
    numerical_recalculation: AuditCheckStatus
    numerical_checks: tuple[DeterministicNumericalCheck, ...] = ()
    resolution: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_numerical_check_shape(self) -> "MaterialClaimAudit":
        if self.numerical_recalculation is AuditCheckStatus.VERIFIED:
            if not self.numerical_checks:
                raise ValueError(
                    "verified numerical claims require deterministic recalculation"
                )
        elif self.numerical_checks:
            raise ValueError(
                "numerical checks require numerical_recalculation=VERIFIED"
            )
        return self


def calculate_numerical_result(
    operation: NumericalOperation,
    operands: tuple[Decimal, ...],
) -> Decimal:
    """Deterministically recalculate one explicit numerical claim."""

    if not operands:
        raise ValueError("numerical operation requires at least one operand")
    with localcontext() as context:
        context.prec = 80
        if operation is NumericalOperation.IDENTITY:
            if len(operands) != 1:
                raise ValueError("IDENTITY requires exactly one operand")
            return operands[0]
        if operation is NumericalOperation.SUM:
            return sum(operands, Decimal("0"))
        if operation is NumericalOperation.DIFFERENCE:
            if len(operands) != 2:
                raise ValueError("DIFFERENCE requires exactly two operands")
            return operands[0] - operands[1]
        if operation is NumericalOperation.PRODUCT:
            calculated = Decimal("1")
            for operand in operands:
                calculated *= operand
            return calculated
        if operation is NumericalOperation.RATIO:
            if len(operands) != 2 or operands[1] == 0:
                raise ValueError(
                    "RATIO requires two operands and a non-zero denominator"
                )
            return operands[0] / operands[1]
    raise ValueError("unsupported numerical operation")


def validate_claim_audit(
    *,
    pre_research: PreResearchResult,
    quick_research: QuickResearchResult,
    deep_research: DeepResearchSupplement,
    audits: tuple[MaterialClaimAudit, ...],
    evidence_artifacts: tuple[EvidenceArtifact, ...],
) -> None:
    """Fail closed unless every material claim passes one exact independent audit."""

    claims = (
        *pre_research.material_claims,
        *quick_research.supporting_claims,
        *quick_research.contradictory_claims,
        *deep_research.material_claims,
    )
    claims_by_hash = {canonical_hash(claim): claim for claim in claims}
    audits_by_hash = {canonical_hash(audit.claim): audit for audit in audits}
    if set(audits_by_hash) != set(claims_by_hash) or len(audits_by_hash) != len(
        audits
    ):
        raise DomainValidationError(
            "claim audit must cover every exact material claim once"
        )

    evidence_by_id = {artifact.id: artifact for artifact in evidence_artifacts}
    if len(evidence_by_id) != len(evidence_artifacts):
        raise DomainValidationError("claim audit evidence ids must be unique")

    for claim_hash, claim in claims_by_hash.items():
        audit = audits_by_hash[claim_hash]
        _validate_one_claim_audit(
            claim=claim,
            audit=audit,
            evidence_by_id=evidence_by_id,
        )

    _validate_claim_authority(tuple(claims_by_hash.values()), evidence_by_id)


def _validate_one_claim_audit(
    *,
    claim: ResearchClaim,
    audit: MaterialClaimAudit,
    evidence_by_id: dict[UUID, EvidenceArtifact],
) -> None:
    if not audit.accepted:
        raise DomainValidationError(
            "unsupported material claim must be removed, downgraded, or unresolved"
        )
    if audit.classification is not AuditCheckStatus.VERIFIED:
        raise DomainValidationError("material claim classification was not verified")
    if AuditCheckStatus.FAILED in {
        audit.identity,
        audit.period_or_date,
        audit.units,
        audit.source_location,
        audit.evidence_support,
        audit.numerical_recalculation,
    }:
        raise DomainValidationError("material claim audit contains a failed check")

    if claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
        required = (
            audit.identity,
            audit.period_or_date,
            audit.units,
            audit.source_location,
            audit.evidence_support,
        )
        if any(item is not AuditCheckStatus.VERIFIED for item in required):
            raise DomainValidationError(
                "FACT and MARKET_CONTEXT require verified identity, date/period, units, "
                "source, and evidence"
            )
        if set(audit.claim.evidence_artifact_ids) != set(claim.evidence_artifact_ids):
            raise DomainValidationError("claim audit changed EvidenceArtifact lineage")
        if not set(claim.evidence_artifact_ids).issubset(evidence_by_id):
            raise DomainValidationError(
                "claim audit references missing EvidenceArtifacts"
            )

    numeric_values = numeric_assertion_values(claim.statement)
    if numeric_values:
        _validate_numeric_claim(
            claim=claim,
            audit=audit,
            numeric_values=numeric_values,
            evidence_by_id=evidence_by_id,
        )
    elif audit.numerical_recalculation is AuditCheckStatus.VERIFIED:
        raise DomainValidationError(
            "non-numerical claims must not invent deterministic numerical checks"
        )


def _validate_numeric_claim(
    *,
    claim: ResearchClaim,
    audit: MaterialClaimAudit,
    numeric_values: tuple[Decimal, ...],
    evidence_by_id: dict[UUID, EvidenceArtifact],
) -> None:
    if audit.numerical_recalculation is not AuditCheckStatus.VERIFIED:
        raise DomainValidationError(
            "explicit numerical claims require deterministic recalculation"
        )
    checked_values = tuple(check.claimed_result for check in audit.numerical_checks)
    if sorted(numeric_values) != sorted(checked_values):
        raise DomainValidationError(
            "deterministic numerical checks must cover every explicit claim value"
        )

    for check in audit.numerical_checks:
        if claim.kind in {
            ResearchClaimKind.FACT,
            ResearchClaimKind.MARKET_CONTEXT,
        } and not check.evidence_inputs:
            raise DomainValidationError(
                "evidenced numerical claims require structured EvidenceArtifact inputs"
            )
        try:
            recalculated = calculate_numerical_result(
                check.operation,
                check.operands,
            )
        except ValueError as exc:
            raise DomainValidationError(
                "numerical claim cannot be deterministically recalculated"
            ) from exc
        if recalculated != check.claimed_result:
            raise DomainValidationError(
                "numerical claim does not match deterministic recalculation"
            )

        for source_input in check.evidence_inputs:
            if source_input.evidence_artifact_id not in claim.evidence_artifact_ids:
                raise DomainValidationError(
                    "numerical check input is outside the claim EvidenceArtifact lineage"
                )
            artifact = evidence_by_id.get(source_input.evidence_artifact_id)
            values = None if artifact is None else artifact.extracted_structured_values
            if values is None or source_input.field_name not in values:
                raise DomainValidationError(
                    "numerical check lacks a structured EvidenceArtifact source value"
                )
            raw_value = values[source_input.field_name]
            if isinstance(raw_value, bool):
                raise DomainValidationError(
                    "boolean evidence cannot support a numerical claim"
                )
            try:
                resolved_value = Decimal(str(raw_value).rstrip("%"))
            except (InvalidOperation, ValueError) as exc:
                raise DomainValidationError(
                    "structured EvidenceArtifact value is not an exact decimal"
                ) from exc
            if resolved_value != source_input.value:
                raise DomainValidationError(
                    "numerical check does not match the structured EvidenceArtifact value"
                )

        bound_operands = (
            *(item.value for item in check.evidence_inputs),
            *check.code_constant_operands,
        )
        if Counter(check.operands) != Counter(bound_operands):
            raise DomainValidationError(
                "every numerical operand must bind to an exact EvidenceArtifact value "
                "or approved code constant"
            )


def _validate_claim_authority(
    claims: tuple[ResearchClaim, ...],
    evidence_by_id: dict[UUID, EvidenceArtifact],
) -> None:
    for claim in claims:
        if claim.kind is not ResearchClaimKind.FACT:
            continue
        if any(
            evidence_by_id[artifact_id].source_type.startswith("RADAR_")
            for artifact_id in claim.evidence_artifact_ids
            if artifact_id in evidence_by_id
        ):
            raise DomainValidationError(
                "Radar evidence is MARKET_CONTEXT and cannot support a Fundamental FACT"
            )


_NUMERIC_ASSERTION_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)"
    r"(?![0-9]|\.[0-9])"
)
_NUMERIC_UNIT_RE = re.compile(
    r"^\s*(?:%|x\b|bps?\b|[kmgt]?w\b|million\b|billion\b|mn\b|bn\b|m\b|b\b|"
    r"倍|亿|万|元|股|吨|兆瓦|吉瓦)",
    re.IGNORECASE,
)
_CURRENCY_PREFIX_RE = re.compile(
    r"(?:CNY|RMB|USD|HKD|EUR|[$¥])\s*$",
    re.IGNORECASE,
)
_NUMERIC_LABEL_PREFIX_RE = re.compile(
    r"(?:EPS|DPS|NAV|P/?E|P/?B|P/?S|ROE|ROIC|EBITDA|FCF)"
    r"\s*(?:IS|WAS|=|:)?\s*$",
    re.IGNORECASE,
)


def numeric_assertion_values(statement: str) -> tuple[Decimal, ...]:
    """Extract explicit investment-relevant numeric assertions, not dates or identifiers."""

    values: list[Decimal] = []
    for match in _NUMERIC_ASSERTION_RE.finditer(statement):
        raw = match.group(1)
        value = Decimal(raw.replace(",", ""))
        suffix = statement[match.end() :]
        prefix = statement[max(0, match.start() - 32) : match.start()]
        if not (
            _NUMERIC_UNIT_RE.search(suffix)
            or _CURRENCY_PREFIX_RE.search(prefix)
            or _NUMERIC_LABEL_PREFIX_RE.search(prefix)
        ):
            continue
        values.append(value)
    return tuple(values)
