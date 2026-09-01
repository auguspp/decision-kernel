from __future__ import annotations

from decimal import Decimal

import pytest

from decision_kernel.claim_audit import (
    AuditCheckStatus,
    DeterministicNumericalCheck,
    EvidenceNumericalInput,
    MaterialClaimAudit,
    NumericalOperation,
    numeric_assertion_values,
    validate_claim_audit,
)
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research_funnel import ResearchClaim, ResearchClaimKind
from test_deep_research import _components


def _claims(pre, quick, deep):
    return (
        *pre.material_claims,
        *quick.supporting_claims,
        *quick.contradictory_claims,
        *deep.material_claims,
    )


def _audit(claim: ResearchClaim) -> MaterialClaimAudit:
    evidenced = claim.kind in {
        ResearchClaimKind.FACT,
        ResearchClaimKind.MARKET_CONTEXT,
    }
    status = AuditCheckStatus.VERIFIED if evidenced else AuditCheckStatus.NOT_APPLICABLE
    return MaterialClaimAudit(
        claim=claim,
        accepted=True,
        identity=status,
        period_or_date=status,
        units=status,
        source_location=status,
        evidence_support=status,
        classification=AuditCheckStatus.VERIFIED,
        numerical_recalculation=AuditCheckStatus.NOT_APPLICABLE,
        resolution="independent audit accepted the exact material claim",
    )


def test_complete_independent_audit_covers_every_exact_material_claim_once() -> None:
    _, pre, quick, deep, evidence, _ = _components()
    audits = tuple(_audit(claim) for claim in _claims(pre, quick, deep))

    validate_claim_audit(
        pre_research=pre,
        quick_research=quick,
        deep_research=deep,
        audits=audits,
        evidence_artifacts=evidence,
    )


def test_missing_or_rejected_material_claim_fails_closed() -> None:
    _, pre, quick, deep, evidence, _ = _components()
    audits = tuple(_audit(claim) for claim in _claims(pre, quick, deep))

    with pytest.raises(DomainValidationError, match="every exact material claim once"):
        validate_claim_audit(
            pre_research=pre,
            quick_research=quick,
            deep_research=deep,
            audits=audits[:-1],
            evidence_artifacts=evidence,
        )

    rejected = audits[0].model_copy(update={"accepted": False})
    with pytest.raises(DomainValidationError, match="unsupported material claim"):
        validate_claim_audit(
            pre_research=pre,
            quick_research=quick,
            deep_research=deep,
            audits=(rejected, *audits[1:]),
            evidence_artifacts=evidence,
        )


def test_fact_requires_verified_identity_period_units_source_and_evidence() -> None:
    _, pre, quick, deep, evidence, _ = _components()
    audits = tuple(_audit(claim) for claim in _claims(pre, quick, deep))
    weakened = audits[0].model_copy(
        update={"source_location": AuditCheckStatus.NOT_APPLICABLE}
    )

    with pytest.raises(DomainValidationError, match="FACT and MARKET_CONTEXT require verified"):
        validate_claim_audit(
            pre_research=pre,
            quick_research=quick,
            deep_research=deep,
            audits=(weakened, *audits[1:]),
            evidence_artifacts=evidence,
        )


def test_radar_context_cannot_be_promoted_to_fundamental_fact() -> None:
    _, pre, quick, deep, evidence, _ = _components()
    radar_first = evidence[0].model_copy(update={"source_type": "RADAR_MARKET_CONTEXT"})
    audits = tuple(_audit(claim) for claim in _claims(pre, quick, deep))

    with pytest.raises(DomainValidationError, match="cannot support a Fundamental FACT"):
        validate_claim_audit(
            pre_research=pre,
            quick_research=quick,
            deep_research=deep,
            audits=audits,
            evidence_artifacts=(radar_first, evidence[1]),
        )


def test_explicit_numeric_fact_binds_to_exact_structured_evidence_value() -> None:
    _, pre, quick, deep, evidence, _ = _components()
    numeric_claim = pre.material_claims[0].model_copy(
        update={"statement": "Reported revenue was CNY 100 million."}
    )
    numeric_pre = pre.model_copy(update={"material_claims": (numeric_claim,)})
    numeric_evidence = evidence[0].model_copy(
        update={"extracted_structured_values": {"revenue": "100"}}
    )
    numeric_check = DeterministicNumericalCheck(
        operation=NumericalOperation.IDENTITY,
        operands=("100",),
        claimed_result="100",
        unit="CNY million",
        evidence_inputs=(
            EvidenceNumericalInput(
                evidence_artifact_id=numeric_evidence.id,
                field_name="revenue",
                value="100",
                unit="CNY million",
            ),
        ),
    )
    numeric_audit = _audit(numeric_claim).model_copy(
        update={
            "numerical_recalculation": AuditCheckStatus.VERIFIED,
            "numerical_checks": (numeric_check,),
        }
    )
    other_audits = tuple(
        _audit(claim) for claim in _claims(numeric_pre, quick, deep)[1:]
    )

    assert numeric_assertion_values(numeric_claim.statement) == (Decimal("100"),)
    validate_claim_audit(
        pre_research=numeric_pre,
        quick_research=quick,
        deep_research=deep,
        audits=(numeric_audit, *other_audits),
        evidence_artifacts=(numeric_evidence, evidence[1]),
    )

    wrong_value = numeric_evidence.model_copy(
        update={"extracted_structured_values": {"revenue": "101"}}
    )
    with pytest.raises(DomainValidationError, match="does not match the structured"):
        validate_claim_audit(
            pre_research=numeric_pre,
            quick_research=quick,
            deep_research=deep,
            audits=(numeric_audit, *other_audits),
            evidence_artifacts=(wrong_value, evidence[1]),
        )


def test_numeric_claim_requires_all_values_and_rejects_unapproved_code_constants() -> None:
    assert numeric_assertion_values("EPS was 1.2 and ROE was 15%.") == (
        Decimal("1.2"),
        Decimal("15"),
    )

    with pytest.raises(ValueError, match="unapproved code constant"):
        DeterministicNumericalCheck(
            operation=NumericalOperation.PRODUCT,
            operands=("50", "2"),
            claimed_result="100",
            unit="units",
            evidence_inputs=(
                EvidenceNumericalInput(
                    evidence_artifact_id=_components()[4][0].id,
                    field_name="value",
                    value="50",
                    unit="units",
                ),
            ),
            code_constant_operands=("2",),
        )
