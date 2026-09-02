from decimal import Decimal
from pathlib import Path

from decision_kernel.claim_audit_contract_v1 import (
    ClaimAuditContractV1Payload,
    ClaimAuditContractV1Status,
    assess_claim_audit_contract_v1,
)
from decision_kernel.deep_research import (
    DeepResearchPackage,
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
    commit_deep_research_package,
    deep_research_package_hash,
)
from decision_kernel.research import ResearchStatus
from decision_kernel.research_contract_v1 import (
    ResearchContractV1Payload,
    ResearchContractV1Status,
    assess_research_contract_v1,
)

CASE_DIR = Path("research_cases")
PACKAGE_PATH = CASE_DIR / "002050-sanhua-deep-research-v1.json"
CONTRACT_PATH = CASE_DIR / "002050-sanhua-research-contract-v1.json"
AUDIT_PATH = CASE_DIR / "002050-sanhua-claim-audit-v1.json"
WORKFLOW_PATH = Path(".github/workflows/decision-inbox.yml")


def _load():
    package = DeepResearchPackage.model_validate_json(PACKAGE_PATH.read_text(encoding="utf-8"))
    contract = ResearchContractV1Payload.model_validate_json(CONTRACT_PATH.read_text(encoding="utf-8"))
    audit = ClaimAuditContractV1Payload.model_validate_json(AUDIT_PATH.read_text(encoding="utf-8"))
    return package, contract, audit


def test_sanhua_v1_is_conforming_and_committable() -> None:
    package, contract, audit = _load()
    method = assess_research_method_v1_acceptance(package)
    research_contract = assess_research_contract_v1(package, contract)
    claim_audit = assess_claim_audit_contract_v1(package, audit)
    committed = commit_deep_research_package(package)

    assert method.status is ResearchMethodV1AcceptanceStatus.ACCEPTED, method.issues
    assert research_contract.status is ResearchContractV1Status.CONFORMING, research_contract.issues
    assert audit.research_package_hash == deep_research_package_hash(package)
    assert claim_audit.status is ClaimAuditContractV1Status.CONFORMING, claim_audit.issues
    assert committed.research_snapshot.status is ResearchStatus.COMMITTED


def test_sanhua_v1_locks_expectation_envelope_and_worlds() -> None:
    package, contract, _ = _load()
    snapshot = package.research_snapshot
    scenarios = {scenario.name: scenario for scenario in snapshot.scenarios}

    assert contract.market_expectation_map["2027_post_h1"] == {
        "min": "5256000000",
        "median": "5422000000",
        "max": "5774000000",
    }
    assert snapshot.model_risk_level.value == "HIGH"
    assert scenarios["core_slowdown"].terminal_equity_value_per_share == Decimal("26.89")
    assert scenarios["sell_side_low_core"].terminal_equity_value_per_share == Decimal("31.28")
    assert scenarios["consensus_core"].terminal_equity_value_per_share == Decimal("36.71")
    assert scenarios["new_business_success"].terminal_equity_value_per_share == Decimal("46.48")
    assert scenarios["robot_right_tail"].terminal_equity_value_per_share == Decimal("70.91")

    weighted = sum(
        (s.probability * s.terminal_equity_value_per_share for s in snapshot.scenarios),
        Decimal("0"),
    )
    assert weighted == Decimal("37.5435")
    assert snapshot.valuation_bases[0].other_explicit_inputs["market_regime_rule"] == (
        "EXCLUDED_FROM_FUNDAMENTAL_BELIEF"
    )


def test_sanhua_v1_is_in_current_inbox_and_disclosure_universe() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    path = "research_cases/002050-sanhua-deep-research-v1.json"
    assert workflow.count(path) == 2
