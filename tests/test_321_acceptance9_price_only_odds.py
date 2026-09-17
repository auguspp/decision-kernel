"""#321 Acceptance 9: price changes Odds, not frozen Research Belief."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import build_odds_research
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    ResearchCommitResult,
    commit_research_package,
)


ROOT = Path(__file__).resolve().parents[1]
MOUTAI = ROOT / "dogfood/600519-moutai.json"
HENGRUI_COMMIT = (
    ROOT / "docs/readings/600276-hengrui-research-commit-2026-09-17/research-commit.json"
)
QUALIFIED_MARKET = ROOT / "docs/dogfood/321-acceptance9-qualified-market-2026-09-17.json"
SH = ZoneInfo("Asia/Shanghai")


def _market(price: str) -> ObservedMarket:
    return ObservedMarket(
        market_price=Decimal(price),
        market_timestamp=datetime(2026, 9, 17, 15, 0, tzinfo=SH),
        market_utc_offset_minutes=480,
        market_data_source="SYNTHETIC_ACCEPTANCE9_NUMERICAL_MECHANICS | 600519.SH",
        price_convention="SYNTHETIC_PRICE_ONLY_ACCEPTANCE_FIXTURE",
        currency="CNY",
    )


def test_already_numerical_committed_research_recomputes_canonical_odds_price_only():
    package = ResearchCommitPackage.model_validate_json(MOUTAI.read_bytes())
    committed = commit_research_package(package).research_snapshot
    assert committed.status is ResearchStatus.COMMITTED
    frozen_before = canonical_json(committed)

    created_at = datetime(2026, 9, 17, 15, 1, tzinfo=SH)
    low_price = build_odds_research(
        artifact_id=UUID("0caa305a-bfcf-53d8-a5cf-b271cc2ad193"),
        created_at=created_at,
        research_snapshot=committed,
        observed_market=_market("1200"),
        policy=load_live_odds_v0_1(),
    )
    high_price = build_odds_research(
        artifact_id=UUID("f39fb5ce-e18f-5e2a-9183-a214ab90bb6f"),
        created_at=created_at,
        research_snapshot=committed,
        observed_market=_market("1800"),
        policy=load_live_odds_v0_1(),
    )

    assert canonical_json(committed) == frozen_before
    for odds in (low_price.artifact, high_price.artifact):
        assert odds.research_snapshot_id == committed.id
        assert odds.research_information_bundle_hash == committed.information_bundle_hash
        assert odds.observed_market.market_timestamp == datetime(2026, 9, 17, 15, 0, tzinfo=SH)

    assert low_price.artifact.expected_holding_period_return > high_price.artifact.expected_holding_period_return
    assert low_price.artifact.minimum_scenario_return > high_price.artifact.minimum_scenario_return
    assert low_price.artifact.maximum_scenario_return > high_price.artifact.maximum_scenario_return
    assert low_price.artifact.observed_market.market_price == Decimal("1200")
    assert high_price.artifact.observed_market.market_price == Decimal("1800")
    assert canonical_json(committed) == frozen_before


def test_real_qualified_price_cannot_promote_probability_free_hengrui_to_canonical_odds():
    retained = ResearchCommitResult.model_validate_json(HENGRUI_COMMIT.read_bytes())
    snapshot = retained.research_snapshot
    before = canonical_json(snapshot)
    fixture = json.loads(QUALIFIED_MARKET.read_text(encoding="utf-8"))
    assert fixture["price_contract"] == "QUALIFIED_LATEST_COMPLETED_A_SHARE_RAW_CLOSE_VIA_EXISTING_HITHINK_RUNTIME"
    raw = fixture["observed_market"]
    market = ObservedMarket(
        market_price=Decimal(raw["market_price"]),
        market_timestamp=datetime.fromisoformat(raw["market_timestamp"]),
        market_utc_offset_minutes=raw["market_utc_offset_minutes"],
        market_data_source=raw["market_data_source"],
        price_convention=raw["price_convention"],
        currency=raw["currency"],
    )
    assert market.market_price == Decimal("43.23")
    assert snapshot.status is ResearchStatus.COMMITTED
    assert snapshot.scenarios == ()

    with pytest.raises(DomainValidationError) as exc:
        build_odds_research(
            artifact_id=UUID("f561f75c-52ac-52d4-b91f-3e15778cc627"),
            created_at=datetime(2026, 9, 17, 15, 1, tzinfo=SH),
            research_snapshot=snapshot,
            observed_market=market,
            policy=load_live_odds_v0_1(),
        )
    message = str(exc.value)
    assert "INCOMPLETE_SCENARIO_DISTRIBUTION:research_snapshot.scenarios" in message
    assert canonical_json(snapshot) == before


def test_acceptance9_fixture_does_not_claim_current_numerical_odds_result():
    fixture = json.loads(QUALIFIED_MARKET.read_text(encoding="utf-8"))
    assert fixture["purpose"].endswith("not a new Odds result")
    assert fixture["authority"] == {
        "research_authority": "NONE",
        "investment_authority": "NONE",
        "action_authority": "NONE",
    }
    assert fixture["code_commit"] == "1c6530be702af08107b799a8d52453c20f925c46"
    assert fixture["read_entry_commit"] == "36a466aab671b609869fd0af6103d8771e28ad34"
