from __future__ import annotations

from datetime import date, datetime
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .market import MoneyDecimal, ObservedMarket
from .primitives import CurrencyCode, KernelModel
from .research import (
    PROBABILITY_TOLERANCE,
    CashFlowBasis,
    CashFlowType,
    ResearchSnapshot,
    ResearchStatus,
)


ENGINE_VERSION = "phase2a-valuation-odds-v1"
DECIMAL_PRECISION = 80
DECIMAL_ROUNDING = ROUND_HALF_EVEN
CALCULATION_CONTEXT = Context(
    prec=DECIMAL_PRECISION,
    rounding=DECIMAL_ROUNDING,
)
ZERO = Decimal("0")
ONE = Decimal("1")


class CalculationStatus(StrEnum):
    CALCULATED = "CALCULATED"
    NO_CALCULATION = "NO_CALCULATION"


class CalculationFailureCode(StrEnum):
    TOTAL_EQUITY_UNSUPPORTED = "TOTAL_EQUITY_UNSUPPORTED"
    FX_CONVERSION_REQUIRED = "FX_CONVERSION_REQUIRED"
    INCOMPLETE_SCENARIO_DISTRIBUTION = "INCOMPLETE_SCENARIO_DISTRIBUTION"
    PIT_VIOLATION = "PIT_VIOLATION"
    UNSUPPORTED_CALCULATION_INPUT = "UNSUPPORTED_CALCULATION_INPUT"


class CalculationConvention(StrEnum):
    UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1 = (
        "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1"
    )


class CalculationFailure(KernelModel):
    code: CalculationFailureCode
    location: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ExpectedDistributionCalculationInput(KernelModel):
    expected_cash_flow_id: UUID
    cash_flow_date: date
    amount_per_share: Decimal
    currency: CurrencyCode
    cash_flow_type: CashFlowType


class ScenarioCalculationInput(KernelModel):
    scenario_id: UUID
    scenario_name: str = Field(min_length=1, max_length=64)
    probability: Decimal = Field(ge=ZERO, le=ONE)
    terminal_equity_value_per_share: Decimal
    expected_distributions: tuple[ExpectedDistributionCalculationInput, ...]


class ValuationOddsCalculationInput(KernelModel):
    research_snapshot_id: UUID
    calculation_currency: CurrencyCode
    observed_market_price: MoneyDecimal = Field(gt=ZERO)
    scenarios: tuple[ScenarioCalculationInput, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_supported_distribution(self) -> "ValuationOddsCalculationInput":
        with localcontext(CALCULATION_CONTEXT):
            probability_sum = sum(
                (scenario.probability for scenario in self.scenarios), ZERO
            )
        if abs(probability_sum - ONE) > PROBABILITY_TOLERANCE:
            raise ValueError(
                "calculation input requires a complete probability distribution"
            )
        if len({scenario.scenario_id for scenario in self.scenarios}) != len(
            self.scenarios
        ):
            raise ValueError("calculation input Scenario ids must be unique")
        if any(
            distribution.currency != self.calculation_currency
            for scenario in self.scenarios
            for distribution in scenario.expected_distributions
        ):
            raise ValueError(
                "calculation input distributions must use the calculation currency"
            )
        return self


class DatedExpectedDistributionResult(KernelModel):
    expected_cash_flow_id: UUID
    cash_flow_date: date
    amount_per_share: Decimal
    basis: CashFlowBasis
    currency: CurrencyCode
    cash_flow_type: CashFlowType


class ScenarioCalculationResult(KernelModel):
    scenario_id: UUID
    scenario_name: str = Field(min_length=1, max_length=64)
    probability: Decimal
    terminal_equity_value_per_share: Decimal
    expected_distributions: tuple[DatedExpectedDistributionResult, ...]
    total_expected_distributions_per_share: Decimal
    total_payoff_per_share: Decimal
    undiscounted_holding_period_return: Decimal


class AggregateCalculationResult(KernelModel):
    probability_weighted_terminal_equity_value_per_share: Decimal
    probability_weighted_expected_distributions_per_share: Decimal
    probability_weighted_total_payoff_per_share: Decimal
    probability_weighted_undiscounted_holding_period_return: Decimal
    positive_return_scenario_probability: Decimal


class ValuationOddsCalculationResult(KernelModel):
    status: CalculationStatus
    research_snapshot_id: UUID
    calculation_currency: CurrencyCode
    calculation_convention: CalculationConvention
    engine_version: str = Field(min_length=1, max_length=64)
    decimal_precision: int = Field(ge=1)
    decimal_rounding: str = Field(min_length=1, max_length=64)
    expected_cash_flow_timing: str = Field(min_length=1, max_length=128)
    is_discounted: bool
    is_annualized: bool
    scenario_results: tuple[ScenarioCalculationResult, ...] = ()
    aggregate: AggregateCalculationResult | None = None
    failures: tuple[CalculationFailure, ...] = ()
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_result_shape(self) -> "ValuationOddsCalculationResult":
        if self.status is CalculationStatus.CALCULATED:
            if self.failures or self.aggregate is None or not self.scenario_results:
                raise ValueError(
                    "CALCULATED requires scenario results and aggregate without failures"
                )
        elif self.scenario_results or self.aggregate is not None or not self.failures:
            raise ValueError(
                "NO_CALCULATION requires failures and forbids partial results"
            )
        if self.is_discounted or self.is_annualized:
            raise ValueError("Phase 2A results cannot be discounted or annualized")
        return self


def calculate_research_economics(
    snapshot: ResearchSnapshot,
    observed_market: ObservedMarket,
    *,
    created_at: datetime,
) -> ValuationOddsCalculationResult:
    """Validate frozen Research + Market inputs and apply deterministic arithmetic."""

    with localcontext(CALCULATION_CONTEXT):
        failures = _validate_calculation_inputs(
            snapshot,
            observed_market,
            created_at=created_at,
        )
        if failures:
            return _no_calculation(snapshot, failures)
        calculation_input = _build_calculation_input(snapshot, observed_market)
    return calculate_valuation_odds(calculation_input)


def calculate_valuation_odds(
    calculation_input: ValuationOddsCalculationInput,
) -> ValuationOddsCalculationResult:
    """Apply deterministic Phase 2A arithmetic to a validated input."""

    with localcontext(CALCULATION_CONTEXT):
        scenario_results = tuple(
            _calculate_scenario(scenario, calculation_input.observed_market_price)
            for scenario in sorted(
                calculation_input.scenarios,
                key=lambda item: (item.scenario_name, str(item.scenario_id)),
            )
        )
        aggregate = AggregateCalculationResult(
            probability_weighted_terminal_equity_value_per_share=_normalized(
                sum(
                    (
                        result.probability
                        * result.terminal_equity_value_per_share
                        for result in scenario_results
                    ),
                    ZERO,
                )
            ),
            probability_weighted_expected_distributions_per_share=_normalized(
                sum(
                    (
                        result.probability
                        * result.total_expected_distributions_per_share
                        for result in scenario_results
                    ),
                    ZERO,
                )
            ),
            probability_weighted_total_payoff_per_share=_normalized(
                sum(
                    (
                        result.probability * result.total_payoff_per_share
                        for result in scenario_results
                    ),
                    ZERO,
                )
            ),
            probability_weighted_undiscounted_holding_period_return=_normalized(
                sum(
                    (
                        result.probability
                        * result.undiscounted_holding_period_return
                        for result in scenario_results
                    ),
                    ZERO,
                )
            ),
            positive_return_scenario_probability=_normalized(
                sum(
                    (
                        result.probability
                        for result in scenario_results
                        if result.undiscounted_holding_period_return > ZERO
                    ),
                    ZERO,
                )
            ),
        )

    return ValuationOddsCalculationResult(
        status=CalculationStatus.CALCULATED,
        research_snapshot_id=calculation_input.research_snapshot_id,
        calculation_currency=calculation_input.calculation_currency,
        calculation_convention=(
            CalculationConvention.UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1
        ),
        engine_version=ENGINE_VERSION,
        decimal_precision=DECIMAL_PRECISION,
        decimal_rounding=str(DECIMAL_ROUNDING),
        expected_cash_flow_timing="DATED_INPUTS_PRESERVED_WITHOUT_DISCOUNTING",
        is_discounted=False,
        is_annualized=False,
        scenario_results=scenario_results,
        aggregate=aggregate,
    )


def _validate_calculation_inputs(
    snapshot: ResearchSnapshot,
    observed_market: ObservedMarket,
    *,
    created_at: datetime,
) -> tuple[CalculationFailure, ...]:
    failures: list[CalculationFailure] = []
    creation_time_is_aware = (
        created_at.tzinfo is not None and created_at.utcoffset() is not None
    )
    if not creation_time_is_aware:
        failures.append(
            _failure(
                CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                "created_at",
                "calculation creation time must be timezone-aware",
            )
        )

    if snapshot.status is not ResearchStatus.COMMITTED or snapshot.committed_at is None:
        failures.append(
            _failure(
                CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                "research_snapshot",
                "Phase 2A requires a COMMITTED ResearchSnapshot",
            )
        )
    elif creation_time_is_aware:
        chronology_is_valid = (
            snapshot.as_of_datetime <= snapshot.committed_at <= created_at
            and snapshot.as_of_datetime
            <= observed_market.market_timestamp
            <= created_at
        )
        if not chronology_is_valid:
            failures.append(
                _failure(
                    CalculationFailureCode.PIT_VIOLATION,
                    "calculation_chronology",
                    "required chronology is research as-of <= committed <= calculation and research as-of <= market <= calculation",
                )
            )

    if snapshot.valuation_horizon_date is None:
        failures.append(
            _failure(
                CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                "valuation_horizon_date",
                "numerical calculation requires a valuation horizon",
            )
        )
    elif snapshot.valuation_horizon_date < observed_market.market_date:
        failures.append(
            _failure(
                CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                "valuation_horizon_date",
                "valuation horizon precedes the frozen exchange-local market date",
            )
        )

    probability_sum = sum(
        (scenario.probability for scenario in snapshot.scenarios), ZERO
    )
    if not snapshot.scenarios or abs(probability_sum - ONE) > PROBABILITY_TOLERANCE:
        failures.append(
            _failure(
                CalculationFailureCode.INCOMPLETE_SCENARIO_DISTRIBUTION,
                "research_snapshot.scenarios",
                "the complete Scenario probability distribution is required",
            )
        )

    if observed_market.currency != snapshot.currency:
        failures.append(
            _failure(
                CalculationFailureCode.FX_CONVERSION_REQUIRED,
                "observed_market.currency",
                "observed market price currency differs from calculation currency",
            )
        )

    referenced_basis_ids = {
        scenario.valuation_basis_id for scenario in snapshot.scenarios
    }
    referenced_bases = (
        basis
        for basis in snapshot.valuation_bases
        if basis.id in referenced_basis_ids
    )
    for basis in sorted(referenced_bases, key=lambda item: str(item.id)):
        if basis.currency != snapshot.currency:
            failures.append(
                _failure(
                    CalculationFailureCode.FX_CONVERSION_REQUIRED,
                    f"valuation_basis:{basis.id}",
                    "ValuationBasis currency differs from calculation currency",
                )
            )
        if basis.as_of_datetime > snapshot.as_of_datetime:
            failures.append(
                _failure(
                    CalculationFailureCode.PIT_VIOLATION,
                    f"valuation_basis:{basis.id}",
                    "ValuationBasis as-of time is later than the ResearchSnapshot cutoff",
                )
            )

    for scenario in sorted(snapshot.scenarios, key=lambda item: str(item.id)):
        for flow in sorted(scenario.expected_cash_flows, key=lambda item: str(item.id)):
            location = f"expected_cash_flow:{flow.id}"
            if flow.basis is CashFlowBasis.TOTAL_EQUITY:
                failures.append(
                    _failure(
                        CalculationFailureCode.TOTAL_EQUITY_UNSUPPORTED,
                        location,
                        "Phase 2A supports PER_SHARE ExpectedCashFlow only",
                    )
                )
            if flow.currency != snapshot.currency:
                failures.append(
                    _failure(
                        CalculationFailureCode.FX_CONVERSION_REQUIRED,
                        location,
                        "ExpectedCashFlow currency differs from calculation currency",
                    )
                )
            if flow.cash_flow_date <= observed_market.market_date:
                failures.append(
                    _failure(
                        CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                        location,
                        "expected distribution must be dated after the frozen exchange-local market date",
                    )
                )

    return tuple(
        sorted(
            failures,
            key=lambda item: (item.code.value, item.location, item.message),
        )
    )


def _build_calculation_input(
    snapshot: ResearchSnapshot,
    observed_market: ObservedMarket,
) -> ValuationOddsCalculationInput:
    return ValuationOddsCalculationInput(
        research_snapshot_id=snapshot.id,
        calculation_currency=snapshot.currency,
        observed_market_price=observed_market.market_price,
        scenarios=tuple(
            ScenarioCalculationInput(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                probability=scenario.probability,
                terminal_equity_value_per_share=(
                    scenario.terminal_equity_value_per_share
                ),
                expected_distributions=tuple(
                    ExpectedDistributionCalculationInput(
                        expected_cash_flow_id=flow.id,
                        cash_flow_date=flow.cash_flow_date,
                        amount_per_share=flow.amount,
                        currency=flow.currency,
                        cash_flow_type=flow.cash_flow_type,
                    )
                    for flow in scenario.expected_cash_flows
                ),
            )
            for scenario in snapshot.scenarios
        ),
    )


def _calculate_scenario(
    scenario: ScenarioCalculationInput,
    observed_market_price: Decimal,
) -> ScenarioCalculationResult:
    distributions = tuple(
        DatedExpectedDistributionResult(
            expected_cash_flow_id=flow.expected_cash_flow_id,
            cash_flow_date=flow.cash_flow_date,
            amount_per_share=_normalized(flow.amount_per_share),
            basis=CashFlowBasis.PER_SHARE,
            currency=flow.currency,
            cash_flow_type=flow.cash_flow_type,
        )
        for flow in sorted(
            scenario.expected_distributions,
            key=lambda item: (
                item.cash_flow_date,
                str(item.expected_cash_flow_id),
            ),
        )
    )
    total_distributions = _normalized(
        sum((distribution.amount_per_share for distribution in distributions), ZERO)
    )
    terminal_value = _normalized(scenario.terminal_equity_value_per_share)
    total_payoff = _normalized(terminal_value + total_distributions)
    holding_period_return = _normalized(
        (total_payoff / observed_market_price) - ONE
    )
    return ScenarioCalculationResult(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.scenario_name,
        probability=_normalized(scenario.probability),
        terminal_equity_value_per_share=terminal_value,
        expected_distributions=distributions,
        total_expected_distributions_per_share=total_distributions,
        total_payoff_per_share=total_payoff,
        undiscounted_holding_period_return=holding_period_return,
    )


def _failure(
    code: CalculationFailureCode,
    location: str,
    message: str,
) -> CalculationFailure:
    return CalculationFailure(code=code, location=location, message=message)


def _no_calculation(
    snapshot: ResearchSnapshot,
    failures: tuple[CalculationFailure, ...],
) -> ValuationOddsCalculationResult:
    return ValuationOddsCalculationResult(
        status=CalculationStatus.NO_CALCULATION,
        research_snapshot_id=snapshot.id,
        calculation_currency=snapshot.currency,
        calculation_convention=(
            CalculationConvention.UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1
        ),
        engine_version=ENGINE_VERSION,
        decimal_precision=DECIMAL_PRECISION,
        decimal_rounding=str(DECIMAL_ROUNDING),
        expected_cash_flow_timing="DATED_INPUTS_PRESERVED_WITHOUT_DISCOUNTING",
        is_discounted=False,
        is_annualized=False,
        failures=failures,
    )


def _normalized(value: Decimal) -> Decimal:
    if value == ZERO:
        return ZERO
    return value.normalize()
