from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.claim_audit_contract_v1 import (
    ClaimAuditContractV1Payload,
    ClaimAuditContractV1Status,
    ClaimAuditV1Check,
    ClaimAuditV1ClaimReview,
    ClaimAuditV1EvidenceInput,
    ClaimAuditV1LiteralInput,
    ClaimAuditV1NumericalCheck,
    ClaimAuditV1NumericalOperation,
    assess_claim_audit_contract_v1,
)
from decision_kernel.deep_research import (
    DeepResearchPackage,
    commit_deep_research_package,
    deep_research_package_hash,
)
from decision_kernel.research import ResearchStatus
from decision_kernel.research_funnel import ResearchClaim, ResearchClaimKind
from test_deep_research import _package, _rehash


EVIDENCE_CHECKS = (
    ClaimAuditV1Check.IDENTITY,
    ClaimAuditV1Check.PERIOD_OR_DATE,
    ClaimAuditV1Check.UNITS,
    ClaimAuditV1Check.SOURCE_LOCATION,
    ClaimAuditV1Check.EVIDENCE_SUPPORT,
)


def _claims(package: DeepResearchPackage) -> tuple[ResearchClaim, ...]:
    return (
        *package.pre_research.material_claims,
        *package.quick_research.supporting_claims,
        *package.quick_research.contradictory_claims,
        *package.deep_research.material_claims,
    )


def _review(claim: ResearchClaim) -> ClaimAuditV1ClaimReview:
    verified = (ClaimAuditV1Check.CLASSIFICATION,)
    if claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
        verified = (*verified, *EVIDENCE_CHECKS)
    return ClaimAuditV1ClaimReview(
        claim=claim,
        accepted=True,
        verified_checks=verified,
        resolution="independent audit accepted the exact material claim",
    )


def _payload(
    package: DeepResearchPackage,
    *,
    reviews: tuple[ClaimAuditV1ClaimReview, ...] | None = None,
) -> ClaimAuditContractV1Payload:
    return ClaimAuditContractV1Payload(
        research_snapshot_id=package.research_snapshot.id,
        research_package_hash=deep_research_package_hash(package),
        reviews=(
            reviews
            if reviews is not None
            else tuple(_review(claim) for claim in _claims(package))
        ),
    )


def _codes(
    package: DeepResearchPackage,
    payload: ClaimAuditContractV1Payload,
) -> set[str]:
    return {
        issue.code
        for issue in assess_claim_audit_contract_v1(package, payload).issues
    }


def test_complete_independent_claim_audit_conforms() -> None:
    package = _package()
    assessment = assess_claim_audit_contract_v1(package, _payload(package))

    assert assessment.status is ClaimAuditContractV1Status.CONFORMING
    assert assessment.issues == ()


def test_exact_material_claim_coverage_is_required_once() -> None:
    package = _package()
    reviews = tuple(_review(claim) for claim in _claims(package))
    payload = _payload(package, reviews=reviews[:-1])

    assessment = assess_claim_audit_contract_v1(package, payload)

    assert assessment.status is ClaimAuditContractV1Status.NONCONFORMING
    assert "CLAIM_COVERAGE_MISMATCH" in _codes(package, payload)


def test_rejected_or_incompletely_verified_fact_is_nonconforming() -> None:
    package = _package()
    reviews = list(_payload(package).reviews)

    reviews[0] = reviews[0].model_copy(update={"accepted": False})
    rejected = _payload(package, reviews=tuple(reviews))
    assert "CLAIM_REJECTED" in _codes(package, rejected)

    reviews = list(_payload(package).reviews)
    reviews[0] = reviews[0].model_copy(
        update={
            "verified_checks": tuple(
                check
                for check in reviews[0].verified_checks
                if check is not ClaimAuditV1Check.SOURCE_LOCATION
            )
        }
    )
    incomplete = _payload(package, reviews=tuple(reviews))
    assert "EVIDENCE_AUDIT_INCOMPLETE" in _codes(package, incomplete)


def test_explicit_numeric_fact_binds_to_exact_structured_evidence_value() -> None:
    package = _package()
    numeric_claim = package.deep_research.material_claims[0].model_copy(
        update={"statement": "Reported revenue was CNY 100 million."}
    )
    deep = package.deep_research.model_copy(
        update={
            "material_claims": (
                numeric_claim,
                *package.deep_research.material_claims[1:],
            )
        }
    )
    first_evidence = package.evidence_artifacts[0].model_copy(
        update={"extracted_structured_values": {"revenue": "100"}}
    )
    changed = _rehash(
        package,
        deep_research=deep,
        evidence_artifacts=(first_evidence, package.evidence_artifacts[1]),
    )

    reviews = list(_payload(changed).reviews)
    index = next(i for i, review in enumerate(reviews) if review.claim == numeric_claim)
    numerical_check = ClaimAuditV1NumericalCheck(
        operation=ClaimAuditV1NumericalOperation.IDENTITY,
        operands=("100",),
        claimed_result="100",
        unit="CNY million",
        evidence_inputs=(
            ClaimAuditV1EvidenceInput(
                evidence_artifact_id=first_evidence.id,
                field_name="revenue",
                value="100",
                unit="CNY million",
            ),
        ),
    )
    reviews[index] = reviews[index].model_copy(
        update={
            "verified_checks": (
                *reviews[index].verified_checks,
                ClaimAuditV1Check.NUMERICAL_RECALCULATION,
            ),
            "numerical_assertions": (Decimal("100"),),
            "numerical_checks": (numerical_check,),
        }
    )
    payload = _payload(changed, reviews=tuple(reviews))

    assert (
        assess_claim_audit_contract_v1(changed, payload).status
        is ClaimAuditContractV1Status.CONFORMING
    )

    wrong_evidence = first_evidence.model_copy(
        update={"extracted_structured_values": {"revenue": "101"}}
    )
    wrong_package = _rehash(
        package,
        deep_research=deep,
        evidence_artifacts=(wrong_evidence, package.evidence_artifacts[1]),
    )
    wrong_payload = payload.model_copy(
        update={
            "research_package_hash": deep_research_package_hash(wrong_package),
            "research_snapshot_id": wrong_package.research_snapshot.id,
        }
    )

    assert "NUMERIC_SOURCE_VALUE_MISMATCH" in _codes(wrong_package, wrong_payload)


def test_every_numerical_operand_requires_explicit_provenance() -> None:
    package = _package()
    evidence_id = package.evidence_artifacts[0].id

    with pytest.raises(ValidationError, match="every numerical operand"):
        ClaimAuditV1NumericalCheck(
            operation=ClaimAuditV1NumericalOperation.PRODUCT,
            operands=("50", "2"),
            claimed_result="100",
            unit="units",
            evidence_inputs=(
                ClaimAuditV1EvidenceInput(
                    evidence_artifact_id=evidence_id,
                    field_name="value",
                    value="50",
                    unit="units",
                ),
            ),
        )


def test_explicit_literal_replaces_fixed_constant_whitelist() -> None:
    package = _package()
    evidence_id = package.evidence_artifacts[0].id

    check = ClaimAuditV1NumericalCheck(
        operation=ClaimAuditV1NumericalOperation.PRODUCT,
        operands=("50", "2"),
        claimed_result="100",
        unit="units",
        evidence_inputs=(
            ClaimAuditV1EvidenceInput(
                evidence_artifact_id=evidence_id,
                field_name="value",
                value="50",
                unit="units",
            ),
        ),
        literal_inputs=(
            ClaimAuditV1LiteralInput(
                value="2",
                reason="explicit conversion factor declared by the independent audit",
            ),
        ),
    )

    assert check.claimed_result == Decimal("100")


def test_source_prefix_does_not_encode_claim_authority_policy() -> None:
    package = _package()
    radar_named = package.evidence_artifacts[0].model_copy(
        update={"source_type": "RADAR_MARKET_CONTEXT"}
    )
    changed = _rehash(
        package,
        evidence_artifacts=(radar_named, package.evidence_artifacts[1]),
    )

    assessment = assess_claim_audit_contract_v1(changed, _payload(changed))

    assert assessment.status is ClaimAuditContractV1Status.CONFORMING


def test_claim_audit_payload_binds_to_exact_snapshot_and_package() -> None:
    package = _package()
    payload = _payload(package)

    wrong_snapshot = payload.model_copy(update={"research_snapshot_id": uuid4()})
    assert "SNAPSHOT_ID_MISMATCH" in _codes(package, wrong_snapshot)

    wrong_hash = payload.model_copy(update={"research_package_hash": "f" * 64})
    assert "PACKAGE_HASH_MISMATCH" in _codes(package, wrong_hash)


def test_nonconforming_claim_audit_does_not_gain_kernel_commit_authority() -> None:
    package = _package()
    reviews = tuple(_review(claim) for claim in _claims(package))
    nonconforming = _payload(package, reviews=reviews[:-1])

    assessment = assess_claim_audit_contract_v1(package, nonconforming)
    committed = commit_deep_research_package(package)

    assert assessment.status is ClaimAuditContractV1Status.NONCONFORMING
    assert committed.research_snapshot.status is ResearchStatus.COMMITTED
