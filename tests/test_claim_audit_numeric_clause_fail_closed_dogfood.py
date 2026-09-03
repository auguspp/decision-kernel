from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from decision_kernel.claim_audit_contract_v1 import (
    ClaimAuditV1EvidenceInput,
    ClaimAuditV1NumericalCheck,
    ClaimAuditV1NumericalOperation,
)
from decision_kernel.deep_research import DeepResearchPackage
from decision_kernel.identity import canonical_hash
from decision_kernel.research_funnel import ResearchClaim


PACKAGE_PATH = Path("research_cases/600233-yto-deep-research-v2.json")
FAIL_CLOSED_PREFIX = "Insufficient evidence"
H1_FILING_ID_HEX = "047e2546389b5274a8dce4a0ce3931f4"


@dataclass(frozen=True)
class _NumericClause:
    text: str
    input_claim_hash: str | None
    numerical_check: ClaimAuditV1NumericalCheck | None


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


def _identity_check(
    package: DeepResearchPackage,
    *,
    field_name: str,
    value: str,
    unit: str,
) -> ClaimAuditV1NumericalCheck:
    h1_filing = next(
        artifact
        for artifact in package.evidence_artifacts
        if artifact.id.hex == H1_FILING_ID_HEX
    )
    return ClaimAuditV1NumericalCheck(
        operation=ClaimAuditV1NumericalOperation.IDENTITY,
        operands=(value,),
        claimed_result=value,
        unit=unit,
        evidence_inputs=(
            ClaimAuditV1EvidenceInput(
                evidence_artifact_id=h1_filing.id,
                field_name=field_name,
                value=value,
                unit=unit,
            ),
        ),
    )


def _numeric_clause_is_supported(
    package: DeepResearchPackage,
    clause: _NumericClause,
    *,
    pit: datetime,
) -> bool:
    """Test-only explicit-clause check; deliberately does not parse prose with regex."""

    if clause.input_claim_hash is None or clause.numerical_check is None:
        return False

    claims_by_hash = {
        canonical_hash(claim): claim
        for claim in _material_claims(package)
    }
    claim = claims_by_hash.get(clause.input_claim_hash)
    if claim is None:
        return False

    evidence_by_id = {artifact.id: artifact for artifact in package.evidence_artifacts}
    for source in clause.numerical_check.evidence_inputs:
        if source.evidence_artifact_id not in claim.evidence_artifact_ids:
            return False
        artifact = evidence_by_id.get(source.evidence_artifact_id)
        if artifact is None or artifact.available_at > pit:
            return False
        raw = (artifact.extracted_structured_values or {}).get(source.field_name)
        if raw is None or isinstance(raw, bool):
            return False
        if Decimal(str(raw)) != source.value:
            return False
    return True


def _render_or_fail_closed(
    package: DeepResearchPackage,
    *,
    section_text: str,
    numeric_clauses: tuple[_NumericClause, ...],
    pit: datetime,
) -> str:
    unsupported = tuple(
        clause
        for clause in numeric_clauses
        if not _numeric_clause_is_supported(package, clause, pit=pit)
    )
    if unsupported:
        return (
            f"{FAIL_CLOSED_PREFIX} (numeric-clause provenance missing: "
            + "; ".join(clause.text for clause in unsupported)
            + ")"
        )
    return section_text


def test_every_material_numeric_clause_can_carry_its_own_provenance_path() -> None:
    package = _load_package()
    unit_claim = _claim_containing(package, "2026H1 unit revenue/cost/gross profit")
    aviation_claim = _claim_containing(package, "H1 aviation gross margin")
    section = (
        "YTO H1 unit revenue was CNY2.17/parcel, unit cost was CNY1.90/parcel, "
        "and aviation gross margin was -47.86%."
    )
    clauses = (
        _NumericClause(
            text="unit revenue = CNY2.17/parcel",
            input_claim_hash=canonical_hash(unit_claim),
            numerical_check=_identity_check(
                package,
                field_name="unit_revenue",
                value="2.17",
                unit="CNY/parcel",
            ),
        ),
        _NumericClause(
            text="unit cost = CNY1.90/parcel",
            input_claim_hash=canonical_hash(unit_claim),
            numerical_check=_identity_check(
                package,
                field_name="unit_cost",
                value="1.90",
                unit="CNY/parcel",
            ),
        ),
        _NumericClause(
            text="aviation gross margin = -47.86%",
            input_claim_hash=canonical_hash(aviation_claim),
            numerical_check=_identity_check(
                package,
                field_name="aviation_gm",
                value="-47.86",
                unit="percent",
            ),
        ),
    )

    assert (
        _render_or_fail_closed(
            package,
            section_text=section,
            numeric_clauses=clauses,
            pit=package.research_snapshot.as_of_datetime,
        )
        == section
    )


def test_one_supported_clause_does_not_cover_an_unsupported_numeric_clause() -> None:
    package = _load_package()
    unit_claim = _claim_containing(package, "2026H1 unit revenue/cost/gross profit")
    section = "YTO H1 unit revenue was CNY2.17/parcel and a modeled margin was 90%."
    clauses = (
        _NumericClause(
            text="unit revenue = CNY2.17/parcel",
            input_claim_hash=canonical_hash(unit_claim),
            numerical_check=_identity_check(
                package,
                field_name="unit_revenue",
                value="2.17",
                unit="CNY/parcel",
            ),
        ),
        _NumericClause(
            text="modeled margin = 90%",
            input_claim_hash=None,
            numerical_check=None,
        ),
    )

    rendered = _render_or_fail_closed(
        package,
        section_text=section,
        numeric_clauses=clauses,
        pit=package.research_snapshot.as_of_datetime,
    )

    assert rendered.startswith(FAIL_CLOSED_PREFIX)
    assert "modeled margin = 90%" in rendered
    assert section not in rendered


def test_valid_source_elsewhere_in_research_does_not_rescue_wrong_claim_lineage() -> None:
    package = _load_package()
    sellside_claim = _claim_containing(package, "sampled CICC and Huachuang")
    section = "YTO H1 aviation gross margin was -47.86%."
    clauses = (
        _NumericClause(
            text="aviation gross margin = -47.86%",
            input_claim_hash=canonical_hash(sellside_claim),
            numerical_check=_identity_check(
                package,
                field_name="aviation_gm",
                value="-47.86",
                unit="percent",
            ),
        ),
    )

    rendered = _render_or_fail_closed(
        package,
        section_text=section,
        numeric_clauses=clauses,
        pit=package.research_snapshot.as_of_datetime,
    )

    assert rendered.startswith(FAIL_CLOSED_PREFIX)
    assert section not in rendered
