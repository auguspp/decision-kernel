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
)
from decision_kernel.research import ResearchStatus
from decision_kernel.research_contract_v1 import (
    ResearchContractV1Payload,
    ResearchContractV1Status,
    assess_research_contract_v1,
)


CASE_DIR = Path("research_cases")
DEEP_PATH = CASE_DIR / "603986-gigadevice-deep-research-v1.json"
CONTRACT_PATH = CASE_DIR / "603986-gigadevice-research-contract-v1.json"
AUDIT_PATH = CASE_DIR / "603986-gigadevice-claim-audit-v1.json"


def _load():
    package = DeepResearchPackage.model_validate_json(DEEP_PATH.read_text(encoding="utf-8"))
    contract = ResearchContractV1Payload.model_validate_json(
        CONTRACT_PATH.read_text(encoding="utf-8")
    )
    audit = ClaimAuditContractV1Payload.model_validate_json(
        AUDIT_PATH.read_text(encoding="utf-8")
    )
    return package, contract, audit


def test_gigadevice_full_research_golden_path_conforms_and_commits() -> None:
    package, contract, audit = _load()

    method = assess_research_method_v1_acceptance(package)
    research_contract = assess_research_contract_v1(package, contract)
    claim_audit = assess_claim_audit_contract_v1(package, audit)
    committed = commit_deep_research_package(package)

    assert method.status is ResearchMethodV1AcceptanceStatus.ACCEPTED
    assert method.issues == ()
    assert research_contract.status is ResearchContractV1Status.CONFORMING
    assert research_contract.issues == ()
    assert claim_audit.status is ClaimAuditContractV1Status.CONFORMING
    assert claim_audit.issues == ()
    assert committed.research_snapshot.status is ResearchStatus.COMMITTED
    assert committed.research_snapshot.ticker == "603986"
    assert committed.research_snapshot.information_bundle_hash == (
        package.research_snapshot.information_bundle_hash
    )


def test_gigadevice_valuation_normalizes_peak_h1() -> None:
    package, _, _ = _load()
    snapshot = package.research_snapshot
    scenarios = {scenario.name: scenario for scenario in snapshot.scenarios}

    assert snapshot.model_risk_level.value == "VERY_HIGH"
    assert scenarios["downside"].terminal_equity_value_per_share == Decimal("166.73")
    assert scenarios["base"].terminal_equity_value_per_share == Decimal("356.25")
    assert scenarios["upside"].terminal_equity_value_per_share == Decimal("615.60")
    assert sum((s.probability for s in snapshot.scenarios), Decimal("0")) == Decimal("1")
    assert "非经常性" in snapshot.model_risk_notes
