from __future__ import annotations

from decision_kernel.deep_research import (
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
)
from decision_kernel.research_contract_v1 import assess_research_contract_v1
from decision_kernel.research_funnel import ResearchClaimKind
from test_deep_research import _contract_payload, _package, _rehash


def _contract_codes(package, payload=None) -> set[str]:
    return {
        issue.code
        for issue in assess_research_contract_v1(
            package,
            payload or _contract_payload(package),
        ).issues
    }


def test_contract_version_is_metadata_policy_not_kernel_constitution() -> None:
    package = _package()
    payload = _contract_payload(package).model_copy(
        update={"contract_version": "different-method-v2"}
    )

    assert (
        assess_research_method_v1_acceptance(package).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert "CONTRACT_VERSION_UNSUPPORTED" in _contract_codes(package, payload)


def test_claim_class_recipe_is_research_method_policy() -> None:
    package = _package()
    facts = tuple(
        claim
        for claim in package.deep_research.material_claims
        if claim.kind is ResearchClaimKind.FACT
    )
    deep = package.deep_research.model_copy(update={"material_claims": facts})
    changed = _rehash(package, deep_research=deep)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert "CLAIM_CLASS_SET_INCOMPLETE" in _contract_codes(changed)


def test_empty_open_questions_and_monitoring_are_not_kernel_commit_blockers() -> None:
    package = _package()
    snapshot = package.research_snapshot.model_copy(
        update={"open_questions": (), "monitoring_triggers": ()}
    )
    changed = _rehash(package, research_snapshot=snapshot)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    codes = _contract_codes(changed)
    assert "OPEN_QUESTIONS_MISSING" in codes
    assert "MONITORING_INDICATORS_INVALID" in codes


def test_method_payload_must_bind_to_exact_kernel_snapshot() -> None:
    package = _package()
    payload = _contract_payload(package).model_copy(
        update={"research_snapshot_id": package.research_snapshot.id.__class__(int=1)}
    )

    assert (
        assess_research_method_v1_acceptance(package).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    assert "SNAPSHOT_ID_MISMATCH" in _contract_codes(package, payload)
