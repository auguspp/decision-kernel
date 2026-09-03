from pathlib import Path

from decision_kernel.claim_audit_contract_v2 import (
    ClaimAuditContractV2Payload,
    ClaimAuditContractV2Status,
    assess_claim_audit_contract_v2,
)
from decision_kernel.deep_research import DeepResearchPackage
from decision_kernel.source_policy_v2 import SourceEpistemicRole


CASE_DIR = Path("research_cases")
PACKAGE_PATH = CASE_DIR / "600233-yto-deep-research-v2.json"
AUDIT_PATH = CASE_DIR / "600233-yto-claim-audit-v2.json"


def _load() -> tuple[DeepResearchPackage, ClaimAuditContractV2Payload]:
    package = DeepResearchPackage.model_validate_json(
        PACKAGE_PATH.read_text(encoding="utf-8")
    )
    audit = ClaimAuditContractV2Payload.model_validate_json(
        AUDIT_PATH.read_text(encoding="utf-8")
    )
    return package, audit


def _multi_source_sellside_review(audit: ClaimAuditContractV2Payload):
    return next(
        item
        for item in audit.reviews
        if "sampled CICC and Huachuang" in item.review.claim.statement
    )


def test_yto_multi_source_claim_preserves_every_declared_source_use() -> None:
    package, audit = _load()
    item = _multi_source_sellside_review(audit)

    claim_ids = set(item.review.claim.evidence_artifact_ids)
    source_use_ids = {use.evidence_artifact_id for use in item.source_uses}

    assert len(claim_ids) == 2
    assert source_use_ids == claim_ids
    assert len(item.source_uses) == 2
    assert {use.source_role for use in item.source_uses} == {
        SourceEpistemicRole.ANALYST_MODEL
    }

    assessment = assess_claim_audit_contract_v2(package, audit)
    assert assessment.status is ClaimAuditContractV2Status.CONFORMING, assessment.issues


def test_dropping_one_material_source_is_fail_closed_not_primary_source_collapse() -> None:
    package, audit = _load()
    item = _multi_source_sellside_review(audit)
    assert len(item.source_uses) == 2

    collapsed_item = item.model_copy(update={"source_uses": item.source_uses[:1]})
    reviews = tuple(
        collapsed_item if review is item else review
        for review in audit.reviews
    )
    collapsed_audit = audit.model_copy(update={"reviews": reviews})

    assessment = assess_claim_audit_contract_v2(package, collapsed_audit)

    assert assessment.status is ClaimAuditContractV2Status.NONCONFORMING
    assert "SOURCE_USE_COVERAGE_MISMATCH" in {
        issue.code for issue in assessment.issues
    }
