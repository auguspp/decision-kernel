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
PACKAGE_PATH = CASE_DIR / "600233-yto-deep-research-v1.json"
CONTRACT_PATH = CASE_DIR / "600233-yto-research-contract-v1.json"
AUDIT_PATH = CASE_DIR / "600233-yto-claim-audit-v1.json"
WORKFLOW_PATH = Path(".github/workflows/decision-inbox.yml")


def _load():
    package = DeepResearchPackage.model_validate_json(PACKAGE_PATH.read_text(encoding="utf-8"))
    contract = ResearchContractV1Payload.model_validate_json(CONTRACT_PATH.read_text(encoding="utf-8"))
    audit = ClaimAuditContractV1Payload.model_validate_json(AUDIT_PATH.read_text(encoding="utf-8"))
    return package, contract, audit


def test_yto_v1_is_conforming_and_committable() -> None:
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


def test_yto_v1_locks_sell_side_first_envelope_and_worlds() -> None:
    package, contract, _ = _load()
    snapshot = package.research_snapshot
    scenarios = {scenario.name: scenario for scenario in snapshot.scenarios}

    assert contract.market_expectation_map["2027_post_h1"] == {
        "min": "6951000000",
        "median": "7300500000",
        "max": "7542000000",
    }
    assert snapshot.model_risk_level.value == "MEDIUM"
    assert scenarios["competitive_relapse"].terminal_equity_value_per_share == Decimal("12.85")
    assert scenarios["partial_normalization"].terminal_equity_value_per_share == Decimal("17.09")
    assert scenarios["fresh_consensus_core"].terminal_equity_value_per_share == Decimal("23.14")
    assert scenarios["efficiency_share_upside"].terminal_equity_value_per_share == Decimal("28.05")
    assert scenarios["strong_right_tail"].terminal_equity_value_per_share == Decimal("34.18")

    weighted = sum(
        (s.probability * s.terminal_equity_value_per_share for s in snapshot.scenarios),
        Decimal("0"),
    )
    assert weighted == Decimal("21.6180")
    basis = snapshot.valuation_bases[0]
    assert basis.other_explicit_inputs["market_regime_rule"] == "EXCLUDED_FROM_FUNDAMENTAL_BELIEF"
    assert basis.other_explicit_inputs["legacy_decision_os_yto_fixture"] == "IGNORED_DEMO_NOT_LIVE_INVESTMENT_DATA"


def test_yto_v1_is_in_current_inbox_and_disclosure_universe() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    path = "research_cases/600233-yto-deep-research-v1.json"
    assert workflow.count(path) == 2
