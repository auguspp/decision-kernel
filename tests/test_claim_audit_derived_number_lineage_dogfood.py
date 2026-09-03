from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from decision_kernel.claim_audit_contract_v1 import (
    ClaimAuditV1EvidenceInput,
    ClaimAuditV1NumericalCheck,
    ClaimAuditV1NumericalOperation,
)
from decision_kernel.deep_research import DeepResearchPackage
from decision_kernel.identity import canonical_hash
from decision_kernel.research_funnel import ResearchClaim


PACKAGE_PATH = Path("research_cases/600233-yto-deep-research-v2.json")
FORMULA_NAME = "ocf_minus_cash_capex"
FORMULA_VERSION = "v1"


def _load_package() -> DeepResearchPackage:
    return DeepResearchPackage.model_validate_json(
        PACKAGE_PATH.read_text(encoding="utf-8")
    )


def _material_claims(package: DeepResearchPackage) -> tuple[ResearchClaim, ...]:
    return (
        *package.pre_research.material_claims,
        *package.quick_research.supporting_claims,
        *package.quick_research.contradictory_claims,
        *package.deep_research.material_claims,
    )


def _claim_containing(package: DeepResearchPackage, text: str) -> ResearchClaim:
    return next(claim for claim in _material_claims(package) if text in claim.statement)


def _assert_derived_lineage(
    package: DeepResearchPackage,
    *,
    formula_name: str,
    formula_version: str,
    input_claim_hashes: tuple[str, ...],
    numerical_check: ClaimAuditV1NumericalCheck,
    pit: datetime,
) -> None:
    """Zero-schema harness assertion for one derived-number lineage experiment."""

    if not formula_name.strip() or not formula_version.strip():
        raise AssertionError("derived number requires an explicit formula name and version")
    if len(input_claim_hashes) != len(set(input_claim_hashes)):
        raise AssertionError("derived number input claim hashes must be unique")

    claims_by_hash = {
        canonical_hash(claim): claim
        for claim in _material_claims(package)
    }
    missing_claims = set(input_claim_hashes) - set(claims_by_hash)
    if missing_claims:
        raise AssertionError("derived number references unknown exact input claim lineage")

    allowed_evidence_ids = {
        evidence_id
        for claim_hash in input_claim_hashes
        for evidence_id in claims_by_hash[claim_hash].evidence_artifact_ids
    }
    evidence_by_id = {artifact.id: artifact for artifact in package.evidence_artifacts}

    for source in numerical_check.evidence_inputs:
        if source.evidence_artifact_id not in allowed_evidence_ids:
            raise AssertionError("numeric input falls outside exact input claim lineage")
        artifact = evidence_by_id.get(source.evidence_artifact_id)
        if artifact is None:
            raise AssertionError("numeric input references missing EvidenceArtifact")
        if artifact.available_at > pit:
            raise AssertionError("numeric input EvidenceArtifact was unavailable at PIT")

        raw = (artifact.extracted_structured_values or {}).get(source.field_name)
        if raw is None or isinstance(raw, bool):
            raise AssertionError("numeric input field is not replayable from structured Evidence")
        if Decimal(str(raw)) != source.value:
            raise AssertionError("numeric input value does not match structured Evidence")


def _h1_ocf_surplus_check(package: DeepResearchPackage) -> ClaimAuditV1NumericalCheck:
    h1_filing = next(
        artifact
        for artifact in package.evidence_artifacts
        if artifact.id.hex == "047e2546389b5274a8dce4a0ce3931f4"
    )
    return ClaimAuditV1NumericalCheck(
        operation=ClaimAuditV1NumericalOperation.DIFFERENCE,
        operands=("3958827124.74", "3482399714.60"),
        claimed_result="476427410.14",
        unit="CNY",
        evidence_inputs=(
            ClaimAuditV1EvidenceInput(
                evidence_artifact_id=h1_filing.id,
                field_name="ocf",
                value="3958827124.74",
                unit="CNY",
            ),
            ClaimAuditV1EvidenceInput(
                evidence_artifact_id=h1_filing.id,
                field_name="capex",
                value="3482399714.60",
                unit="CNY",
            ),
        ),
    )


def test_yto_derived_number_preserves_formula_claim_source_and_pit_lineage() -> None:
    package = _load_package()
    input_claim = _claim_containing(package, "H1 OCF/cash capex")
    check = _h1_ocf_surplus_check(package)

    _assert_derived_lineage(
        package,
        formula_name=FORMULA_NAME,
        formula_version=FORMULA_VERSION,
        input_claim_hashes=(canonical_hash(input_claim),),
        numerical_check=check,
        pit=package.research_snapshot.as_of_datetime,
    )

    assert check.claimed_result == Decimal("476427410.14")
    assert check.operation is ClaimAuditV1NumericalOperation.DIFFERENCE


def test_yto_derived_number_rejects_unrelated_claim_lineage() -> None:
    package = _load_package()
    unrelated_claim = _claim_containing(package, "sampled CICC and Huachuang")
    check = _h1_ocf_surplus_check(package)

    with pytest.raises(AssertionError, match="outside exact input claim lineage"):
        _assert_derived_lineage(
            package,
            formula_name=FORMULA_NAME,
            formula_version=FORMULA_VERSION,
            input_claim_hashes=(canonical_hash(unrelated_claim),),
            numerical_check=check,
            pit=package.research_snapshot.as_of_datetime,
        )
