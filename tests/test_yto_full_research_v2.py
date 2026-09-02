from decimal import Decimal
from pathlib import Path
from uuid import UUID

from decision_kernel.claim_audit_contract_v2 import (
    ClaimAuditContractV2Payload,
    ClaimAuditContractV2Status,
    assess_claim_audit_contract_v2,
)
from decision_kernel.deep_research import (
    DeepResearchPackage,
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
    commit_deep_research_package,
    deep_research_package_hash,
)
from decision_kernel.research import ResearchStatus
from decision_kernel.research_contract_v2 import (
    ProbabilityEffect,
    ResearchContractV2Payload,
    ResearchContractV2Status,
    assess_research_contract_v2,
)
from decision_kernel.source_policy_v2 import SourceEpistemicRole

CASE_DIR = Path("research_cases")
PACKAGE_PATH = CASE_DIR / "600233-yto-deep-research-v2.json"
CONTRACT_PATH = CASE_DIR / "600233-yto-research-contract-v2.json"
AUDIT_PATH = CASE_DIR / "600233-yto-claim-audit-v2.json"
V1_PACKAGE_PATH = CASE_DIR / "600233-yto-deep-research-v1.json"
WORKFLOW_PATH = Path(".github/workflows/decision-inbox.yml")
V1_SNAPSHOT_ID = UUID("766470c1-64f5-598e-9dc4-141252ab493b")


def _load():
    package = DeepResearchPackage.model_validate_json(PACKAGE_PATH.read_text(encoding="utf-8"))
    contract = ResearchContractV2Payload.model_validate_json(CONTRACT_PATH.read_text(encoding="utf-8"))
    audit = ClaimAuditContractV2Payload.model_validate_json(AUDIT_PATH.read_text(encoding="utf-8"))
    return package, contract, audit


def test_yto_v2_is_additive_conforming_and_committable() -> None:
    package, contract, audit = _load()
    method = assess_research_method_v1_acceptance(package)
    research_contract = assess_research_contract_v2(package, contract)
    claim_audit = assess_claim_audit_contract_v2(package, audit)
    committed = commit_deep_research_package(package)

    assert method.status is ResearchMethodV1AcceptanceStatus.ACCEPTED, method.issues
    assert research_contract.status is ResearchContractV2Status.CONFORMING, research_contract.issues
    assert audit.research_package_hash == deep_research_package_hash(package)
    assert claim_audit.status is ClaimAuditContractV2Status.CONFORMING, claim_audit.issues
    assert committed.research_snapshot.status is ResearchStatus.COMMITTED
    assert package.research_snapshot.version == 2
    assert package.research_snapshot.supersedes_snapshot_id == V1_SNAPSHOT_ID


def test_yto_v2_repairs_the_expectation_event_bridge_without_price_fitting() -> None:
    package, contract, _ = _load()
    bridge = contract.expectation_event_bridges[0]

    assert bridge.event_id == "YTO-2026-H1-FORMAL-PRINT"
    assert bridge.pre_event_expectation["known_company_h1_parent_np_range"] == [
        "3100000000",
        "3400000000",
    ]
    assert bridge.pre_event_expectation["sampled_2027_sellside_np"] == [
        "7306000000",
        "7500000000",
    ]
    assert bridge.actual_event["formal_h1_parent_np"] == "3175000000"
    assert bridge.actual_event["position_through_preannounced_range"] == "0.25"
    assert bridge.post_event_expectation["fresh_2027_np_mean"] == "7266500000"
    assert bridge.post_event_expectation["huatai_2026_pe_change"] == "16.3x -> 13.3x"
    assert bridge.market_reaction["one_day_return_pct"] == "-6.32"
    assert bridge.probability_effect is ProbabilityEffect.UNCHANGED
    assert contract.our_belief_map["probability_change_from_v1"] == "NONE"

    probabilities = {scenario.name: scenario.probability for scenario in package.research_snapshot.scenarios}
    assert probabilities == {
        "renewed_price_war": Decimal("0.15"),
        "partial_normalization": Decimal("0.25"),
        "street_center": Decimal("0.35"),
        "durable_discipline": Decimal("0.20"),
        "network_compounder": Decimal("0.05"),
    }
    weighted_value = sum(
        (
            scenario.probability * scenario.terminal_equity_value_per_share
            for scenario in package.research_snapshot.scenarios
        ),
        Decimal("0"),
    )
    assert weighted_value == Decimal("23.9585")


def test_yto_v2_separates_reality_market_belief_and_our_belief() -> None:
    _, contract, audit = _load()

    assert contract.reality_map["2026_h1_parent_np"] == "3175000000"
    assert contract.market_expectation_map["pre_formal_report_after_prealert_sample"]["sample_mean"] == (
        "7403000000"
    )
    assert contract.market_expectation_map["post_formal_report_fresh"]["2027_mean"] == (
        "7266500000"
    )
    assert contract.our_belief_map["2027_probability_weighted_parent_np"] == "6906900000.00"

    source_roles = {
        use.source_role
        for item in audit.reviews
        for use in item.source_uses
    }
    assert SourceEpistemicRole.PRIMARY_REALIZED in source_roles
    assert SourceEpistemicRole.PRIMARY_STATEMENT in source_roles
    assert SourceEpistemicRole.MARKET_EXPECTATION in source_roles
    assert SourceEpistemicRole.ANALYST_MODEL in source_roles
    assert SourceEpistemicRole.ANALYST_OPINION in source_roles
    assert SourceEpistemicRole.SECONDARY_OBSERVATION in source_roles


def test_yto_v2_rejects_relabelling_sellside_as_primary_truth() -> None:
    package, _, audit = _load()
    index = next(
        index
        for index, item in enumerate(audit.reviews)
        if "sampled CICC and Huachuang" in item.review.claim.statement
    )
    item = audit.reviews[index]
    bad_use = item.source_uses[0].model_copy(
        update={"source_role": SourceEpistemicRole.PRIMARY_REALIZED}
    )
    bad_item = item.model_copy(update={"source_uses": (bad_use, *item.source_uses[1:])})
    reviews = list(audit.reviews)
    reviews[index] = bad_item
    bad_audit = audit.model_copy(update={"reviews": tuple(reviews)})

    assessment = assess_claim_audit_contract_v2(package, bad_audit)
    assert assessment.status is ClaimAuditContractV2Status.NONCONFORMING
    assert "SOURCE_ROLE_ARTIFACT_MISMATCH" in {issue.code for issue in assessment.issues}


def test_yto_v2_preserves_v1_and_stays_out_of_production_inbox() -> None:
    package, _, _ = _load()
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert V1_PACKAGE_PATH.exists()
    assert package.research_snapshot.supersedes_snapshot_id == V1_SNAPSHOT_ID
    assert "research_cases/600233-yto-deep-research-v2.json" not in workflow
    assert "research_cases/600233-yto-deep-research-v1.json" not in workflow
