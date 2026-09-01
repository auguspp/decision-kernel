from __future__ import annotations

from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .calculation import (
    CalculationStatus,
    ValuationOddsCalculationResult,
    calculate_research_economics,
)
from .identity import canonical_hash
from .market import ObservedMarket
from .primitives import AwareDateTime, DomainValidationError, KernelModel
from .research import ModelRiskLevel, ResearchSnapshot


ODDS_LIMITATIONS = (
    "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF",
    "NOT_ANNUALIZED",
    "PARTICIPATION_ZONE_IS_RESEARCH_NOT_RECOMMENDATION",
)
ODDS_DECIMAL_CONTEXT = Context(prec=80, rounding=ROUND_HALF_EVEN)


class ParticipationZone(StrEnum):
    INSUFFICIENT_ODDS = "INSUFFICIENT_ODDS"
    ACCEPTABLE_ODDS = "ACCEPTABLE_ODDS"
    ATTRACTIVE_ODDS = "ATTRACTIVE_ODDS"
    EXCEPTIONAL_ODDS = "EXCEPTIONAL_ODDS"


class OddsUncertaintyLevel(StrEnum):
    BASELINE = "BASELINE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"


class OddsContext(KernelModel):
    as_of: AwareDateTime
    source_reference: str = Field(min_length=1, max_length=255)
    regime_state: str | None = Field(default=None, max_length=128)
    breadth_state: str | None = Field(default=None, max_length=128)
    drawdown_state: str | None = Field(default=None, max_length=128)
    trend_participation: str | None = Field(default=None, max_length=128)
    uncertainty_level: OddsUncertaintyLevel
    schema_version: Literal[1] = 1


class OddsResearchPolicy(KernelModel):
    policy_version: str = Field(min_length=1, max_length=128)
    minimum_holding_period_days: int = Field(ge=1)
    maximum_holding_period_days: int = Field(ge=1)
    acceptable_min_expected_return: Decimal = Field(ge=Decimal("0"))
    attractive_min_expected_return: Decimal = Field(ge=Decimal("0"))
    exceptional_min_expected_return: Decimal = Field(ge=Decimal("0"))
    acceptable_min_positive_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    attractive_min_positive_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    exceptional_min_positive_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    low_model_risk_addon: Decimal = Field(ge=Decimal("0"))
    medium_model_risk_addon: Decimal = Field(ge=Decimal("0"))
    high_model_risk_addon: Decimal = Field(ge=Decimal("0"))
    very_high_model_risk_addon: Decimal = Field(ge=Decimal("0"))
    elevated_uncertainty_addon: Decimal = Field(ge=Decimal("0"))
    high_uncertainty_addon: Decimal = Field(ge=Decimal("0"))
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_monotonic_thresholds(self) -> "OddsResearchPolicy":
        if self.maximum_holding_period_days < self.minimum_holding_period_days:
            raise ValueError("holding-period policy range is invalid")
        if not (
            self.acceptable_min_expected_return
            < self.attractive_min_expected_return
            < self.exceptional_min_expected_return
        ):
            raise ValueError(
                "expected-return thresholds must increase by participation zone"
            )
        if not (
            self.acceptable_min_positive_probability
            <= self.attractive_min_positive_probability
            <= self.exceptional_min_positive_probability
        ):
            raise ValueError(
                "positive-return probability thresholds must not decrease by zone"
            )
        if not (
            self.low_model_risk_addon
            <= self.medium_model_risk_addon
            <= self.high_model_risk_addon
            <= self.very_high_model_risk_addon
        ):
            raise ValueError("model-risk required-return add-ons must be monotonic")
        if self.elevated_uncertainty_addon > self.high_uncertainty_addon:
            raise ValueError("OddsContext uncertainty add-ons must be monotonic")
        return self

    def model_risk_addon(self, level: ModelRiskLevel) -> Decimal:
        return {
            ModelRiskLevel.LOW: self.low_model_risk_addon,
            ModelRiskLevel.MEDIUM: self.medium_model_risk_addon,
            ModelRiskLevel.HIGH: self.high_model_risk_addon,
            ModelRiskLevel.VERY_HIGH: self.very_high_model_risk_addon,
        }[level]

    def context_addon(self, level: OddsUncertaintyLevel) -> Decimal:
        return {
            OddsUncertaintyLevel.BASELINE: Decimal("0"),
            OddsUncertaintyLevel.ELEVATED: self.elevated_uncertainty_addon,
            OddsUncertaintyLevel.HIGH: self.high_uncertainty_addon,
        }[level]


class AdjustedParticipationThresholds(KernelModel):
    model_risk_addon: Decimal = Field(ge=Decimal("0"))
    odds_context_addon: Decimal = Field(ge=Decimal("0"))
    acceptable_required_return: Decimal
    attractive_required_return: Decimal
    exceptional_required_return: Decimal
    acceptable_min_positive_probability: Decimal
    attractive_min_positive_probability: Decimal
    exceptional_min_positive_probability: Decimal


class OddsResearchArtifact(KernelModel):
    id: UUID
    created_at: AwareDateTime
    research_snapshot_id: UUID
    research_information_bundle_hash: str = Field(min_length=64, max_length=64)
    valuation_horizon_date: date
    holding_period_days: int = Field(ge=1)
    observed_market: ObservedMarket
    calculation: ValuationOddsCalculationResult
    policy: OddsResearchPolicy
    odds_context: OddsContext | None = None
    model_risk_level: ModelRiskLevel
    largest_model_risk_source: str = Field(min_length=1)
    adjusted_thresholds: AdjustedParticipationThresholds
    expected_holding_period_return: Decimal
    positive_return_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    minimum_scenario_return: Decimal
    maximum_scenario_return: Decimal
    participation_zone: ParticipationZone
    limitations: tuple[str, ...]
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_deterministic_projection(self) -> "OddsResearchArtifact":
        if self.calculation.status is not CalculationStatus.CALCULATED:
            raise ValueError("Odds Research requires a CALCULATED result")
        if self.calculation.research_snapshot_id != self.research_snapshot_id:
            raise ValueError(
                "Odds Research calculation must reference its ResearchSnapshot"
            )
        if self.calculation.calculation_currency != self.observed_market.currency:
            raise ValueError("Odds Research price and calculation currency must match")
        if self.created_at < self.observed_market.market_timestamp:
            raise ValueError("Odds Research cannot precede its observed market input")
        expected_holding_period_days = (
            self.valuation_horizon_date - self.observed_market.market_date
        ).days
        if self.holding_period_days != expected_holding_period_days:
            raise ValueError(
                "Odds Research holding period must match its frozen horizon"
            )
        if not (
            self.policy.minimum_holding_period_days
            <= self.holding_period_days
            <= self.policy.maximum_holding_period_days
        ):
            raise ValueError(
                "Odds Research policy does not cover the valuation horizon"
            )
        if self.odds_context is not None and (
            self.odds_context.as_of > self.observed_market.market_timestamp
        ):
            raise ValueError(
                "OddsContext cannot be later than the frozen market observation"
            )
        if tuple(self.limitations) != ODDS_LIMITATIONS:
            raise ValueError(
                "Odds Research must expose the calculation limitations"
            )

        aggregate = self.calculation.aggregate
        if aggregate is None:
            raise ValueError(
                "Odds Research requires aggregate calculation results"
            )
        scenario_returns = tuple(
            scenario.undiscounted_holding_period_return
            for scenario in self.calculation.scenario_results
        )
        if (
            self.expected_holding_period_return
            != aggregate.probability_weighted_undiscounted_holding_period_return
            or self.positive_return_probability
            != aggregate.positive_return_scenario_probability
            or self.minimum_scenario_return != min(scenario_returns)
            or self.maximum_scenario_return != max(scenario_returns)
        ):
            raise ValueError(
                "Odds Research summary must match deterministic calculation"
            )

        model_addon = self.policy.model_risk_addon(self.model_risk_level)
        context_addon = (
            self.policy.context_addon(self.odds_context.uncertainty_level)
            if self.odds_context is not None
            else Decimal("0")
        )
        expected_thresholds = adjusted_participation_thresholds(
            self.policy,
            model_risk_addon=model_addon,
            odds_context_addon=context_addon,
        )
        if self.adjusted_thresholds != expected_thresholds:
            raise ValueError(
                "Odds Research thresholds must match policy and context"
            )
        expected_zone = classify_participation_zone(
            expected_return=self.expected_holding_period_return,
            positive_return_probability=self.positive_return_probability,
            thresholds=self.adjusted_thresholds,
        )
        if self.participation_zone is not expected_zone:
            raise ValueError(
                "participation zone must be derived from declared thresholds"
            )
        return self


class FrozenOddsResearchArtifact(KernelModel):
    artifact_hash: str = Field(min_length=64, max_length=64)
    artifact: OddsResearchArtifact

    @model_validator(mode="after")
    def validate_artifact_hash(self) -> "FrozenOddsResearchArtifact":
        if self.artifact_hash != canonical_hash(self.artifact):
            raise ValueError(
                "Odds Research artifact hash must cover the exact artifact"
            )
        return self


def build_odds_research(
    *,
    artifact_id: UUID,
    created_at: AwareDateTime,
    research_snapshot: ResearchSnapshot,
    observed_market: ObservedMarket,
    policy: OddsResearchPolicy,
    odds_context: OddsContext | None = None,
) -> FrozenOddsResearchArtifact:
    """Build Odds from frozen Research + Market without provider or persistence logic."""

    calculation = calculate_research_economics(
        research_snapshot,
        observed_market,
        created_at=created_at,
    )
    if calculation.status is not CalculationStatus.CALCULATED:
        failures = "; ".join(
            f"{failure.code.value}:{failure.location}"
            for failure in calculation.failures
        )
        raise DomainValidationError(
            f"Odds Research calculation failed: {failures}"
        )
    if not research_snapshot.information_bundle_hash:
        raise DomainValidationError(
            "Odds Research requires Research information lineage"
        )
    if not research_snapshot.model_risk_notes:
        raise DomainValidationError(
            "Odds Research requires an explicit model-risk source"
        )

    model_addon = policy.model_risk_addon(research_snapshot.model_risk_level)
    context_addon = (
        policy.context_addon(odds_context.uncertainty_level)
        if odds_context is not None
        else Decimal("0")
    )
    thresholds = adjusted_participation_thresholds(
        policy,
        model_risk_addon=model_addon,
        odds_context_addon=context_addon,
    )
    aggregate = calculation.aggregate
    if aggregate is None:
        raise DomainValidationError(
            "Odds Research calculation has no aggregate result"
        )
    scenario_returns = tuple(
        scenario.undiscounted_holding_period_return
        for scenario in calculation.scenario_results
    )
    artifact = OddsResearchArtifact(
        id=artifact_id,
        created_at=created_at,
        research_snapshot_id=research_snapshot.id,
        research_information_bundle_hash=research_snapshot.information_bundle_hash,
        valuation_horizon_date=research_snapshot.valuation_horizon_date,
        holding_period_days=(
            research_snapshot.valuation_horizon_date
            - observed_market.market_date
        ).days,
        observed_market=observed_market,
        calculation=calculation,
        policy=policy,
        odds_context=odds_context,
        model_risk_level=research_snapshot.model_risk_level,
        largest_model_risk_source=research_snapshot.model_risk_notes,
        adjusted_thresholds=thresholds,
        expected_holding_period_return=(
            aggregate.probability_weighted_undiscounted_holding_period_return
        ),
        positive_return_probability=(
            aggregate.positive_return_scenario_probability
        ),
        minimum_scenario_return=min(scenario_returns),
        maximum_scenario_return=max(scenario_returns),
        participation_zone=classify_participation_zone(
            expected_return=(
                aggregate.probability_weighted_undiscounted_holding_period_return
            ),
            positive_return_probability=(
                aggregate.positive_return_scenario_probability
            ),
            thresholds=thresholds,
        ),
        limitations=ODDS_LIMITATIONS,
    )
    return freeze_odds_research_artifact(artifact)


def adjusted_participation_thresholds(
    policy: OddsResearchPolicy,
    *,
    model_risk_addon: Decimal,
    odds_context_addon: Decimal,
) -> AdjustedParticipationThresholds:
    with localcontext(ODDS_DECIMAL_CONTEXT):
        total_addon = _normalized(model_risk_addon + odds_context_addon)
        return AdjustedParticipationThresholds(
            model_risk_addon=_normalized(model_risk_addon),
            odds_context_addon=_normalized(odds_context_addon),
            acceptable_required_return=_normalized(
                policy.acceptable_min_expected_return + total_addon
            ),
            attractive_required_return=_normalized(
                policy.attractive_min_expected_return + total_addon
            ),
            exceptional_required_return=_normalized(
                policy.exceptional_min_expected_return + total_addon
            ),
            acceptable_min_positive_probability=(
                policy.acceptable_min_positive_probability
            ),
            attractive_min_positive_probability=(
                policy.attractive_min_positive_probability
            ),
            exceptional_min_positive_probability=(
                policy.exceptional_min_positive_probability
            ),
        )


def classify_participation_zone(
    *,
    expected_return: Decimal,
    positive_return_probability: Decimal,
    thresholds: AdjustedParticipationThresholds,
) -> ParticipationZone:
    if (
        expected_return >= thresholds.exceptional_required_return
        and positive_return_probability
        >= thresholds.exceptional_min_positive_probability
    ):
        return ParticipationZone.EXCEPTIONAL_ODDS
    if (
        expected_return >= thresholds.attractive_required_return
        and positive_return_probability
        >= thresholds.attractive_min_positive_probability
    ):
        return ParticipationZone.ATTRACTIVE_ODDS
    if (
        expected_return >= thresholds.acceptable_required_return
        and positive_return_probability
        >= thresholds.acceptable_min_positive_probability
    ):
        return ParticipationZone.ACCEPTABLE_ODDS
    return ParticipationZone.INSUFFICIENT_ODDS


def freeze_odds_research_artifact(
    artifact: OddsResearchArtifact,
) -> FrozenOddsResearchArtifact:
    frozen = OddsResearchArtifact.model_validate(
        artifact.model_dump(mode="python")
    )
    return FrozenOddsResearchArtifact(
        artifact_hash=canonical_hash(frozen),
        artifact=frozen,
    )


def _normalized(value: Decimal) -> Decimal:
    if value == Decimal("0"):
        return Decimal("0")
    return value.normalize()
