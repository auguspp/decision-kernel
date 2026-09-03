from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from decision_kernel.market import ObservedMarket
from decision_kernel.odds import (
    OddsContext,
    OddsUncertaintyLevel,
    ParticipationZone,
    adjusted_participation_thresholds,
    build_odds_research,
)
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.research import (
    ModelRiskLevel,
    ResearchSnapshot,
    Scenario,
    commit_snapshot,
    submit_for_review,
)
from decision_kernel.valuation import ValuationBasis


AS_OF = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
COMMITTED_AT = AS_OF + timedelta(hours=1)
MARKET_AT = AS_OF + timedelta(hours=2)
CREATED_AT = AS_OF + timedelta(hours=3)
MARKET_DATE = date(2026, 9, 1)
CURRENT_PRICE = Decimal("10")
UP_PROBABILITY = Decimal("0.8")
FLAT_PROBABILITY = Decimal("0.2")


def _annualized_equivalent(cumulative_return: Decimal, holding_days: int) -> float:
    """Audit-only economic comparison; production Odds remain explicitly non-annualized."""

    return (1.0 + float(cumulative_return)) ** (365.0 / holding_days) - 1.0


def _market() -> ObservedMarket:
    return ObservedMarket.model_validate(
        {
            "market_price": str(CURRENT_PRICE),
            "market_timestamp": MARKET_AT,
            "market_utc_offset_minutes": 480,
            "market_data_source": "HiThink",
            "price_convention": "CLOSE",
            "currency": "CNY",
        }
    )


def _basis(snapshot_id: UUID, horizon: date) -> ValuationBasis:
    return ValuationBasis.model_validate(
        {
            "id": uuid4(),
            "research_snapshot_id": snapshot_id,
            "version": 1,
            "as_of_datetime": AS_OF,
            "valuation_horizon_date": horizon,
            "valuation_method": "odds-validity-audit-v0",
            "model_version": "counterfactual-v0",
            "currency": "CNY",
        }
    )


def _committed_snapshot(
    *,
    holding_days: int,
    target_expected_cumulative_return: Decimal,
    model_risk_level: ModelRiskLevel = ModelRiskLevel.LOW,
) -> ResearchSnapshot:
    horizon = MARKET_DATE + timedelta(days=holding_days)
    snapshot_id = uuid4()
    basis = _basis(snapshot_id, horizon)

    # Keep positive-return probability fixed at 80% so this audit isolates the
    # expected-return / holding-period semantics rather than the probability gate.
    up_return = target_expected_cumulative_return / UP_PROBABILITY
    up_terminal = CURRENT_PRICE * (Decimal("1") + up_return)
    scenarios = (
        Scenario(
            id=uuid4(),
            research_snapshot_id=snapshot_id,
            name="up",
            probability=UP_PROBABILITY,
            terminal_equity_value_per_share=up_terminal,
            valuation_basis_id=basis.id,
        ),
        Scenario(
            id=uuid4(),
            research_snapshot_id=snapshot_id,
            name="flat",
            probability=FLAT_PROBABILITY,
            terminal_equity_value_per_share=CURRENT_PRICE,
            valuation_basis_id=basis.id,
        ),
    )
    draft = ResearchSnapshot(
        id=snapshot_id,
        ticker="600000",
        company_name="Odds Validity Audit Counterfactual",
        exchange="SSE",
        currency="CNY",
        created_at=AS_OF,
        as_of_datetime=AS_OF,
        valuation_horizon_date=horizon,
        version=1,
        core_thesis="same economic worlds for holding-period semantics audit",
        market_expectations_narrative="counterfactual audit only",
        thesis_invalidation=("audit construction invalid",),
        model_risk_level=model_risk_level,
        model_risk_notes="counterfactual audit keeps model-risk input explicit",
        open_questions=("does cumulative-return classification preserve economic meaning?",),
        created_by="odds-validity-audit-v0",
        information_bundle_hash="a" * 64,
        valuation_bases=(basis,),
        scenarios=scenarios,
    )
    return commit_snapshot(submit_for_review(draft), COMMITTED_AT)


def _odds(
    *,
    holding_days: int,
    target_expected_cumulative_return: Decimal,
    model_risk_level: ModelRiskLevel = ModelRiskLevel.LOW,
    context_uncertainty: OddsUncertaintyLevel | None = None,
):
    context = None
    if context_uncertainty is not None:
        context = OddsContext(
            as_of=MARKET_AT,
            source_reference="odds-validity-audit-v0",
            uncertainty_level=context_uncertainty,
        )
    return build_odds_research(
        artifact_id=uuid4(),
        created_at=CREATED_AT,
        research_snapshot=_committed_snapshot(
            holding_days=holding_days,
            target_expected_cumulative_return=target_expected_cumulative_return,
            model_risk_level=model_risk_level,
        ),
        observed_market=_market(),
        policy=load_live_odds_v0_1(),
        odds_context=context,
    ).artifact


def test_same_cumulative_return_gets_same_zone_but_not_same_annualized_economics() -> None:
    artifacts = {
        days: _odds(
            holding_days=days,
            target_expected_cumulative_return=Decimal("0.20"),
        )
        for days in (180, 365, 730)
    }

    assert {
        artifact.participation_zone for artifact in artifacts.values()
    } == {ParticipationZone.ACCEPTABLE_ODDS}
    assert all(
        artifact.expected_holding_period_return == Decimal("0.2")
        for artifact in artifacts.values()
    )
    assert all(
        artifact.positive_return_probability == Decimal("0.8")
        for artifact in artifacts.values()
    )

    annualized = {
        days: _annualized_equivalent(Decimal("0.20"), days)
        for days in artifacts
    }
    assert annualized[180] == pytest.approx(0.447311, abs=1e-6)
    assert annualized[365] == pytest.approx(0.20, abs=1e-12)
    assert annualized[730] == pytest.approx(0.095445, abs=1e-6)


def test_same_twenty_percent_annualized_economics_get_different_zones() -> None:
    # Rounded cumulative equivalents of a 20% annualized return at each horizon.
    target_returns = {
        180: Decimal("0.094078"),
        365: Decimal("0.20"),
        730: Decimal("0.44"),
    }
    artifacts = {
        days: _odds(
            holding_days=days,
            target_expected_cumulative_return=target_return,
        )
        for days, target_return in target_returns.items()
    }

    assert artifacts[180].participation_zone is ParticipationZone.INSUFFICIENT_ODDS
    assert artifacts[365].participation_zone is ParticipationZone.ACCEPTABLE_ODDS
    assert artifacts[730].participation_zone is ParticipationZone.ATTRACTIVE_ODDS

    for days, target_return in target_returns.items():
        assert _annualized_equivalent(target_return, days) == pytest.approx(
            0.20,
            abs=2e-6,
        )


def test_fixed_risk_addons_impose_horizon_dependent_annualized_burden() -> None:
    policy = load_live_odds_v0_1()
    baseline = adjusted_participation_thresholds(
        policy,
        model_risk_addon=policy.low_model_risk_addon,
        odds_context_addon=Decimal("0"),
    )
    stressed = adjusted_participation_thresholds(
        policy,
        model_risk_addon=policy.very_high_model_risk_addon,
        odds_context_addon=policy.high_uncertainty_addon,
    )

    assert baseline.acceptable_required_return == Decimal("0.2")
    assert stressed.acceptable_required_return == Decimal("0.39")

    short_baseline = _annualized_equivalent(
        baseline.acceptable_required_return,
        180,
    )
    short_stressed = _annualized_equivalent(
        stressed.acceptable_required_return,
        180,
    )
    long_baseline = _annualized_equivalent(
        baseline.acceptable_required_return,
        730,
    )
    long_stressed = _annualized_equivalent(
        stressed.acceptable_required_return,
        730,
    )

    assert short_baseline == pytest.approx(0.447311, abs=1e-6)
    assert short_stressed == pytest.approx(0.949855, abs=1e-6)
    assert long_baseline == pytest.approx(0.095445, abs=1e-6)
    assert long_stressed == pytest.approx(0.178983, abs=1e-6)
    assert (short_stressed - short_baseline) > Decimal("0.50")
    assert (long_stressed - long_baseline) < Decimal("0.09")
