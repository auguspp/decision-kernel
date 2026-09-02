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


def test_yto_v1_locks_expectation_envelope_owner_economics_and_worlds() -> None:
    package, contract, _ = _load()
    snapshot = package.research_snapshot
    scenarios = {scenario.name: scenario for scenario in snapshot.scenarios}

    assert contract.market_expectation_map["2027_fresh_post_h1"] == {
        "n": "10",
        "min": "7010000000",
        "median": "7300500000",
        "mean": "7266500000",
        "max": "7542000000",
    }
    assert snapshot.model_risk_level.value == "HIGH"
    assert scenarios["renewed_price_war"].terminal_equity_value_per_share == Decimal("13.69")
    assert scenarios["partial_normalization"].terminal_equity_value_per_share == Decimal("17.80")
    assert scenarios["street_center"].terminal_equity_value_per_share == Decimal("25.53")
    assert scenarios["durable_discipline"].terminal_equity_value_per_share == Decimal("32.98")
    assert scenarios["network_compounder"].terminal_equity_value_per_share == Decimal("38.47")

    weighted_value = sum(
        (s.probability * s.terminal_equity_value_per_share for s in snapshot.scenarios),
        Decimal("0"),
    )
    assert weighted_value == Decimal("23.9585")

    detail_by_id = {item.scenario_id: item for item in contract.scenario_details}
    weighted_earnings = sum(
        (
            scenario.probability
            * detail_by_id[scenario.id].normalized_earnings
            for scenario in snapshot.scenarios
        ),
        Decimal("0"),
    )
    assert weighted_earnings == Decimal("6906900000.00")
    assert snapshot.valuation_bases[0].other_explicit_inputs["market_regime_rule"] == (
        "EXCLUDED_FROM_FUNDAMENTAL_BELIEF"
    )
    assert snapshot.valuation_bases[0].other_explicit_inputs["odds_rule"] == (
        "NO_PRODUCTION_ODDS_WITHOUT_HITHINK_OBSERVED_MARKET"
    )


def test_yto_v1_does_not_inherit_demo_identity_or_enter_live_inbox() -> None:
    package, _, _ = _load()
    raw = PACKAGE_PATH.read_text(encoding="utf-8")
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert package.research_snapshot.version == 1
    assert package.research_snapshot.supersedes_snapshot_id is None
    assert "DEMO" not in raw
    assert "fictional fixture" not in raw.lower()
    assert "yto_demo" not in raw
    assert "research_cases/600233-yto-deep-research-v1.json" not in workflow
