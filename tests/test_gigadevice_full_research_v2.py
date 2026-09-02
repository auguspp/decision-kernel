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
V1_PATH = CASE_DIR / "603986-gigadevice-deep-research-v1.json"
V2_PATH = CASE_DIR / "603986-gigadevice-deep-research-v2.json"
CONTRACT_PATH = CASE_DIR / "603986-gigadevice-research-contract-v2.json"
AUDIT_PATH = CASE_DIR / "603986-gigadevice-claim-audit-v2.json"
WORKFLOW_PATH = Path(".github/workflows/decision-inbox.yml")


def _load_v2():
    package = DeepResearchPackage.model_validate_json(V2_PATH.read_text(encoding="utf-8"))
    contract = ResearchContractV1Payload.model_validate_json(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )
    audit = ClaimAuditContractV1Payload.model_validate_json(
        AUDIT_PATH.read_text(encoding="utf-8")
    )
    return package, contract, audit


def test_gigadevice_v2_is_append_only_and_conforming() -> None:
    v1 = DeepResearchPackage.model_validate_json(V1_PATH.read_text(encoding="utf-8"))
    v2, contract, audit = _load_v2()

    assert v1.research_snapshot.version == 1
    assert v2.research_snapshot.version == 2
    assert v2.research_snapshot.supersedes_snapshot_id == v1.research_snapshot.id
    assert v2.research_snapshot.id != v1.research_snapshot.id

    method = assess_research_method_v1_acceptance(v2)
    research_contract = assess_research_contract_v1(v2, contract)
    claim_audit = assess_claim_audit_contract_v1(v2, audit)
    committed = commit_deep_research_package(v2)

    assert method.status is ResearchMethodV1AcceptanceStatus.ACCEPTED, method.issues
    assert research_contract.status is ResearchContractV1Status.CONFORMING, research_contract.issues
    assert audit.research_package_hash == deep_research_package_hash(v2)
    assert claim_audit.status is ClaimAuditContractV1Status.CONFORMING, claim_audit.issues
    assert committed.research_snapshot.status is ResearchStatus.COMMITTED


def test_gigadevice_v2_reconstructs_expectation_envelope_before_probability() -> None:
    package, contract, _ = _load_v2()
    snapshot = package.research_snapshot
    basis = snapshot.valuation_bases[0]
    scenarios = {scenario.name: scenario for scenario in snapshot.scenarios}

    updated = contract.market_expectation_map["post_h1_updated_2027_net_profit_cny"]
    assert updated == {
        "min": "13977000000",
        "median": "16868000000",
        "max": "17872000000",
    }
    assert basis.other_explicit_inputs["expectation_envelope_rule"] == (
        "EXPECTATION_ENVELOPE_BEFORE_PROBABILITY"
    )
    assert snapshot.model_risk_level.value == "VERY_HIGH"
    assert len(snapshot.scenarios) == 5
    assert scenarios["rapid_normalization"].probability == Decimal("0.10")
    assert scenarios["partial_normalization"].probability == Decimal("0.20")
    assert scenarios["research_low_core"].probability == Decimal("0.30")
    assert scenarios["research_high_core"].probability == Decimal("0.30")
    assert scenarios["right_tail"].probability == Decimal("0.10")
    assert scenarios["rapid_normalization"].terminal_equity_value_per_share == Decimal("203.06")
    assert scenarios["partial_normalization"].terminal_equity_value_per_share == Decimal("310.08")
    assert scenarios["research_low_core"].terminal_equity_value_per_share == Decimal("427.79")
    assert scenarios["research_high_core"].terminal_equity_value_per_share == Decimal("538.65")
    assert scenarios["right_tail"].terminal_equity_value_per_share == Decimal("642.68")

    weighted_terminal = sum(
        (
            scenario.probability * scenario.terminal_equity_value_per_share
            for scenario in snapshot.scenarios
        ),
        Decimal("0"),
    )
    assert weighted_terminal == Decimal("436.5220")


def test_decision_inbox_uses_only_current_gigadevice_v2() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "research_cases/603986-gigadevice-deep-research-v2.json" in workflow
    assert "research_cases/*-deep-research-v1.json" not in workflow
    assert "research_cases/603986-gigadevice-deep-research-v1.json" not in workflow
