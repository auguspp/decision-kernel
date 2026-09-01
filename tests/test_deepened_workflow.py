from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from decision_kernel.market import ObservedMarket
from decision_kernel.odds import OddsResearchPolicy
from decision_kernel.primitives import DomainValidationError
from decision_kernel.rehearsal import NonAuthoritativeRehearsalFraming
from decision_kernel.research import ResearchStatus
from decision_kernel.workflow import (
    DecisionSpineTerminalState,
    run_deepened_decision_path,
)
from test_deep_research import AS_OF, _package


def _policy() -> OddsResearchPolicy:
    return OddsResearchPolicy(
        policy_version="integration-v1",
        minimum_holding_period_days=1,
        maximum_holding_period_days=800,
        acceptable_min_expected_return="0.10",
        attractive_min_expected_return="0.20",
        exceptional_min_expected_return="0.30",
        acceptable_min_positive_probability="0.50",
        attractive_min_positive_probability="0.60",
        exceptional_min_positive_probability="0.70",
        low_model_risk_addon="0",
        medium_model_risk_addon="0",
        high_model_risk_addon="0.10",
        very_high_model_risk_addon="0.15",
        elevated_uncertainty_addon="0.03",
        high_uncertainty_addon="0.08",
    )


def _run(package):
    return run_deepened_decision_path(
        deep_research_package=package,
        observed_market=ObservedMarket(
            market_price="10",
            market_timestamp=AS_OF + timedelta(hours=2),
            market_utc_offset_minutes=480,
            market_data_source="HiThink",
            price_convention="CLOSE",
            currency="CNY",
        ),
        odds_policy=_policy(),
        odds_artifact_id=uuid4(),
        odds_created_at=AS_OF + timedelta(hours=3),
        rehearsal_artifact_id=uuid4(),
        rehearsal_created_at=AS_OF + timedelta(hours=4),
        framing=NonAuthoritativeRehearsalFraming(
            why_now="accepted Deep Research exposes a material valuation gap",
            current_expression="research review only; no trade instruction",
        ),
    )


def test_deep_research_commit_flows_into_exact_decision_spine_and_human_gate() -> None:
    package = _package()

    result = _run(package)

    committed = result.research_commit.research_snapshot
    assert committed.status is ResearchStatus.COMMITTED
    assert result.decision.odds.artifact.research_snapshot_id == committed.id
    assert (
        result.decision.odds.artifact.research_information_bundle_hash
        == committed.information_bundle_hash
    )
    assert result.decision.terminal_state is DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    assert result.decision.human_surface.attention_eligible is True
    assert result.investment_authority == "NONE"


def test_deepened_workflow_fails_closed_before_decision_spine_on_tampered_research() -> None:
    package = _package()
    tampered = package.model_copy(
        update={
            "research_snapshot": package.research_snapshot.model_copy(
                update={"core_thesis": "silently changed thesis"}
            )
        }
    )

    with pytest.raises(DomainValidationError, match="not decision-ready"):
        _run(tampered)
