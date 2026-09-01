from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from decision_kernel.human_surface import HumanSurfaceStatus
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import OddsResearchPolicy, ParticipationZone
from decision_kernel.primitives import DomainValidationError
from decision_kernel.rehearsal import NonAuthoritativeRehearsalFraming
from decision_kernel.research import (
    CashFlowBasis,
    CashFlowType,
    ExpectedCashFlow,
    ModelRiskLevel,
    ResearchSnapshot,
    Scenario,
    commit_snapshot,
    submit_for_review,
)
from decision_kernel.valuation import ValuationBasis
from decision_kernel.workflow import (
    DecisionSpineTerminalState,
    run_decision_spine,
)


AS_OF = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
COMMITTED_AT = AS_OF + timedelta(hours=1)
MARKET_AT = AS_OF + timedelta(hours=2)
ODDS_AT = AS_OF + timedelta(hours=3)
REHEARSAL_AT = AS_OF + timedelta(hours=4)
HORIZON = date(2027, 9, 1)


def _snapshot(*, committed: bool = True) -> ResearchSnapshot:
    snapshot_id = uuid4()
    basis = ValuationBasis(
        id=uuid4(),
        research_snapshot_id=snapshot_id,
        version=1,
        as_of_datetime=AS_OF,
        valuation_horizon_date=HORIZON,
        valuation_method="scenario_equity_value",
        model_version="v1",
        currency="CNY",
    )

    def scenario(
        *,
        name: str,
        probability: str,
        terminal: str,
        distribution: str | None = None,
    ) -> Scenario:
        scenario_id = uuid4()
        flows = ()
        if distribution is not None:
            flows = (
                ExpectedCashFlow(
                    id=uuid4(),
                    scenario_id=scenario_id,
                    cash_flow_date=date(2027, 6, 1),
                    amount=distribution,
                    basis=CashFlowBasis.PER_SHARE,
                    currency="CNY",
                    cash_flow_type=CashFlowType.DIVIDEND,
                    provenance_artifact_ids=(uuid4(),),
                ),
            )
        return Scenario(
            id=scenario_id,
            research_snapshot_id=snapshot_id,
            name=name,
            probability=probability,
            description=name,
            valuation_method=basis.valuation_method,
            terminal_equity_value_per_share=terminal,
            valuation_basis_id=basis.id,
            expected_cash_flows=flows,
        )

    draft = ResearchSnapshot(
        id=snapshot_id,
        ticker="600000",
        company_name="Sample Co",
        exchange="SSE",
        currency="CNY",
        created_at=AS_OF,
        as_of_datetime=AS_OF,
        valuation_horizon_date=HORIZON,
        version=1,
        core_thesis="earnings can exceed expectations",
        market_expectations_narrative="market expects flat earnings",
        monitoring_plan={
            "indicators": ["earnings release"],
            "falsifiers": ["margin collapse"],
        },
        model_risk_level=ModelRiskLevel.LOW,
        model_risk_notes="terminal value uncertainty",
        open_questions=("pricing power?",),
        created_by="research",
        information_bundle_hash="a" * 64,
        doctrine_version_reference="doctrine-v1",
        research_contract_version="research-v1",
        valuation_bases=(basis,),
        scenarios=(
            scenario(name="up", probability="0.6", terminal="15", distribution="0.5"),
            scenario(name="down", probability="0.4", terminal="8"),
        ),
    )
    if not committed:
        return draft
    return commit_snapshot(submit_for_review(draft), COMMITTED_AT)


def _market(price: str) -> ObservedMarket:
    return ObservedMarket(
        market_price=price,
        market_timestamp=MARKET_AT,
        market_utc_offset_minutes=480,
        market_data_source="HiThink",
        price_convention="CLOSE",
        currency="CNY",
    )


def _policy() -> OddsResearchPolicy:
    return OddsResearchPolicy(
        policy_version="test-v1",
        minimum_holding_period_days=1,
        maximum_holding_period_days=800,
        acceptable_min_expected_return="0.10",
        attractive_min_expected_return="0.20",
        exceptional_min_expected_return="0.30",
        acceptable_min_positive_probability="0.50",
        attractive_min_positive_probability="0.60",
        exceptional_min_positive_probability="0.70",
        low_model_risk_addon="0",
        medium_model_risk_addon="0.06",
        high_model_risk_addon="0.10",
        very_high_model_risk_addon="0.15",
        elevated_uncertainty_addon="0.03",
        high_uncertainty_addon="0.08",
    )


def _run(snapshot: ResearchSnapshot, price: str):
    return run_decision_spine(
        research_snapshot=snapshot,
        observed_market=_market(price),
        odds_policy=_policy(),
        odds_artifact_id=uuid4(),
        odds_created_at=ODDS_AT,
        rehearsal_artifact_id=uuid4(),
        rehearsal_created_at=REHEARSAL_AT,
        framing=NonAuthoritativeRehearsalFraming(
            why_now="valuation gap is worth examining",
            current_expression="observe only; no trade instruction",
        ),
    )


def test_workflow_routes_decision_worthy_odds_to_human_attention() -> None:
    result = _run(_snapshot(), "10")

    assert result.odds.artifact.participation_zone is ParticipationZone.ATTRACTIVE_ODDS
    assert result.human_surface.status is HumanSurfaceStatus.DECISION_WORTHY_REVIEW
    assert result.human_surface.attention_eligible is True
    assert result.terminal_state is DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    assert result.investment_authority == "NONE"


def test_workflow_keeps_insufficient_odds_quiet_despite_rehearsal_human_status() -> None:
    result = _run(_snapshot(), "14")

    assert result.odds.artifact.participation_zone is ParticipationZone.INSUFFICIENT_ODDS
    assert result.rehearsal.artifact.human_status == "HUMAN_DECISION_REQUIRED"
    assert result.human_surface.status is HumanSurfaceStatus.NOT_ELIGIBLE_INSUFFICIENT_ODDS
    assert result.human_surface.attention_eligible is False
    assert result.terminal_state is DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS


def test_workflow_does_not_translate_domain_failure_into_a_fake_terminal_state() -> None:
    with pytest.raises(DomainValidationError, match="Odds Research calculation failed"):
        _run(_snapshot(committed=False), "10")
