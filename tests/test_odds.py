from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.calculation import (
    CalculationFailureCode,
    CalculationStatus,
    calculate_research_economics,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import (
    ODDS_LIMITATIONS,
    FrozenOddsResearchArtifact,
    OddsContext,
    OddsResearchPolicy,
    OddsUncertaintyLevel,
    ParticipationZone,
    build_odds_research,
)
from decision_kernel.primitives import DomainValidationError
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


AS_OF = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
COMMITTED_AT = AS_OF + timedelta(hours=1)
MARKET_AT = AS_OF + timedelta(hours=2)
CREATED_AT = AS_OF + timedelta(hours=3)
HORIZON = date(2027, 9, 1)


def _basis(snapshot_id: UUID, **updates: object) -> ValuationBasis:
    values: dict[str, object] = {
        "id": uuid4(),
        "research_snapshot_id": snapshot_id,
        "version": 1,
        "as_of_datetime": AS_OF,
        "valuation_horizon_date": HORIZON,
        "valuation_method": "scenario_equity_value",
        "model_version": "v1",
        "currency": "CNY",
    }
    values.update(updates)
    return ValuationBasis.model_validate(values)


def _scenario(
    snapshot_id: UUID,
    basis: ValuationBasis,
    *,
    name: str,
    probability: str,
    terminal: str,
    distribution: str | None = None,
    cash_flow_basis: CashFlowBasis = CashFlowBasis.PER_SHARE,
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
                basis=cash_flow_basis,
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
        terminal_equity_value_per_share=terminal,
        valuation_basis_id=basis.id,
        expected_cash_flows=flows,
    )


def _committed_snapshot(
    *,
    model_risk_level: ModelRiskLevel = ModelRiskLevel.LOW,
    model_risk_notes: str | None = "terminal value uncertainty",
    basis_updates: dict[str, object] | None = None,
    cash_flow_basis: CashFlowBasis = CashFlowBasis.PER_SHARE,
) -> ResearchSnapshot:
    snapshot_id = uuid4()
    basis = _basis(snapshot_id, **(basis_updates or {}))
    scenarios = (
        _scenario(
            snapshot_id,
            basis,
            name="up",
            probability="0.6",
            terminal="15",
            distribution="0.5",
            cash_flow_basis=cash_flow_basis,
        ),
        _scenario(
            snapshot_id,
            basis,
            name="down",
            probability="0.4",
            terminal="8",
        ),
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
        thesis_invalidation=("margin collapse",),
        model_risk_level=model_risk_level,
        model_risk_notes=model_risk_notes,
        open_questions=("pricing power?",),
        created_by="research",
        information_bundle_hash="a" * 64,
        valuation_bases=(basis,),
        scenarios=scenarios,
    )
    return commit_snapshot(submit_for_review(draft), COMMITTED_AT)


def _market(**updates: object) -> ObservedMarket:
    values: dict[str, object] = {
        "market_price": "10",
        "market_timestamp": MARKET_AT,
        "market_utc_offset_minutes": 480,
        "market_data_source": "HiThink",
        "price_convention": "CLOSE",
        "currency": "CNY",
    }
    values.update(updates)
    return ObservedMarket.model_validate(values)


def _policy(**updates: object) -> OddsResearchPolicy:
    values: dict[str, object] = {
        "policy_version": "test-v1",
        "minimum_holding_period_days": 1,
        "maximum_holding_period_days": 800,
        "acceptable_min_expected_return": "0.10",
        "attractive_min_expected_return": "0.20",
        "exceptional_min_expected_return": "0.30",
        "acceptable_min_positive_probability": "0.50",
        "attractive_min_positive_probability": "0.60",
        "exceptional_min_positive_probability": "0.70",
        "low_model_risk_addon": "0",
        "medium_model_risk_addon": "0.06",
        "high_model_risk_addon": "0.10",
        "very_high_model_risk_addon": "0.15",
        "elevated_uncertainty_addon": "0.03",
        "high_uncertainty_addon": "0.08",
    }
    values.update(updates)
    return OddsResearchPolicy.model_validate(values)


def test_observed_market_freezes_exchange_local_price_clock() -> None:
    market = _market(
        market_timestamp=datetime(2026, 9, 1, 16, 30, tzinfo=timezone.utc),
    )
    assert market.market_date == date(2026, 9, 2)
    assert market.market_data_source == "HiThink"


def test_observed_market_rejects_binary_float_price() -> None:
    with pytest.raises(ValidationError, match="binary float"):
        _market(market_price=10.5)


def test_deterministic_calculation_preserves_research_and_price_clocks() -> None:
    snapshot = _committed_snapshot()
    market = _market()

    result = calculate_research_economics(
        snapshot,
        market,
        created_at=CREATED_AT,
    )

    assert result.status is CalculationStatus.CALCULATED
    assert result.aggregate is not None
    assert (
        result.aggregate.probability_weighted_undiscounted_holding_period_return
        == Decimal("0.25")
    )
    assert result.aggregate.positive_return_scenario_probability == Decimal("0.6")
    assert snapshot.as_of_datetime == AS_OF
    assert market.market_timestamp == MARKET_AT


def test_calculation_fails_closed_on_non_committed_research() -> None:
    committed = _committed_snapshot()
    draft = committed.model_copy(
        update={"status": "DRAFT", "committed_at": None}
    )
    result = calculate_research_economics(
        draft,
        _market(),
        created_at=CREATED_AT,
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT
        and failure.location == "research_snapshot"
        for failure in result.failures
    )


def test_calculation_allows_market_event_before_research_commit() -> None:
    market_at = AS_OF + timedelta(minutes=30)
    result = calculate_research_economics(
        _committed_snapshot(),
        _market(market_timestamp=market_at),
        created_at=CREATED_AT,
    )
    assert market_at < COMMITTED_AT
    assert result.status is CalculationStatus.CALCULATED


def test_calculation_fails_closed_on_market_before_research_as_of() -> None:
    result = calculate_research_economics(
        _committed_snapshot(),
        _market(market_timestamp=AS_OF - timedelta(minutes=1)),
        created_at=CREATED_AT,
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.PIT_VIOLATION
        and failure.location == "calculation_chronology"
        for failure in result.failures
    )


def test_calculation_fails_closed_when_calculation_precedes_commit() -> None:
    result = calculate_research_economics(
        _committed_snapshot(),
        _market(market_timestamp=AS_OF + timedelta(minutes=30)),
        created_at=COMMITTED_AT - timedelta(minutes=1),
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.PIT_VIOLATION
        and failure.location == "calculation_chronology"
        for failure in result.failures
    )


def test_calculation_fails_closed_on_currency_mismatch() -> None:
    result = calculate_research_economics(
        _committed_snapshot(),
        _market(currency="USD"),
        created_at=CREATED_AT,
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.FX_CONVERSION_REQUIRED
        for failure in result.failures
    )


def test_calculation_rejects_future_valuation_basis_at_research_pit() -> None:
    snapshot = _committed_snapshot(
        basis_updates={"as_of_datetime": AS_OF + timedelta(minutes=1)}
    )
    result = calculate_research_economics(
        snapshot,
        _market(),
        created_at=CREATED_AT,
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.PIT_VIOLATION
        and failure.location.startswith("valuation_basis:")
        for failure in result.failures
    )


def test_calculation_rejects_total_equity_cash_flow() -> None:
    result = calculate_research_economics(
        _committed_snapshot(cash_flow_basis=CashFlowBasis.TOTAL_EQUITY),
        _market(),
        created_at=CREATED_AT,
    )
    assert result.status is CalculationStatus.NO_CALCULATION
    assert any(
        failure.code is CalculationFailureCode.TOTAL_EQUITY_UNSUPPORTED
        for failure in result.failures
    )


def test_odds_policy_thresholds_must_be_monotonic() -> None:
    with pytest.raises(ValidationError, match="expected-return thresholds"):
        _policy(
            acceptable_min_expected_return="0.20",
            attractive_min_expected_return="0.10",
        )


def test_build_odds_research_classifies_from_frozen_inputs() -> None:
    frozen = build_odds_research(
        artifact_id=uuid4(),
        created_at=CREATED_AT,
        research_snapshot=_committed_snapshot(),
        observed_market=_market(),
        policy=_policy(),
    )
    artifact = frozen.artifact

    assert artifact.expected_holding_period_return == Decimal("0.25")
    assert artifact.positive_return_probability == Decimal("0.6")
    assert artifact.participation_zone is ParticipationZone.ATTRACTIVE_ODDS
    assert artifact.observed_market.market_data_source == "HiThink"
    assert artifact.limitations == ODDS_LIMITATIONS
    assert "RESEARCH_NOT_RECOMMENDATION" in artifact.limitations[-1]


def test_model_risk_adjusts_odds_without_mutating_belief_or_price() -> None:
    snapshot = _committed_snapshot(model_risk_level=ModelRiskLevel.MEDIUM)
    market = _market()
    frozen = build_odds_research(
        artifact_id=uuid4(),
        created_at=CREATED_AT,
        research_snapshot=snapshot,
        observed_market=market,
        policy=_policy(),
    )
    artifact = frozen.artifact

    assert artifact.participation_zone is ParticipationZone.ACCEPTABLE_ODDS
    assert snapshot.core_thesis == "earnings can exceed expectations"
    assert artifact.observed_market.market_price == Decimal("10")


def test_odds_context_cannot_look_past_market_price_clock() -> None:
    context = OddsContext(
        as_of=MARKET_AT + timedelta(seconds=1),
        source_reference="context",
        uncertainty_level=OddsUncertaintyLevel.BASELINE,
    )
    with pytest.raises(ValidationError, match="cannot be later"):
        build_odds_research(
            artifact_id=uuid4(),
            created_at=CREATED_AT,
            research_snapshot=_committed_snapshot(),
            observed_market=_market(),
            policy=_policy(),
            odds_context=context,
        )


def test_odds_defensively_rejects_missing_model_risk_source() -> None:
    committed = _committed_snapshot()
    tampered = committed.model_copy(update={"model_risk_notes": None})

    with pytest.raises(DomainValidationError, match="model-risk source"):
        build_odds_research(
            artifact_id=uuid4(),
            created_at=CREATED_AT,
            research_snapshot=tampered,
            observed_market=_market(),
            policy=_policy(),
        )


def test_frozen_odds_hash_covers_exact_artifact() -> None:
    frozen = build_odds_research(
        artifact_id=uuid4(),
        created_at=CREATED_AT,
        research_snapshot=_committed_snapshot(),
        observed_market=_market(),
        policy=_policy(),
    )
    assert frozen.artifact_hash == canonical_hash(frozen.artifact)

    tampered = frozen.artifact.model_copy(
        update={"largest_model_risk_source": "different"}
    )
    with pytest.raises(ValidationError, match="hash must cover"):
        FrozenOddsResearchArtifact(
            artifact_hash=frozen.artifact_hash,
            artifact=tampered,
        )
