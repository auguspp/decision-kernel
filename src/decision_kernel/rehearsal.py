from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .authority import InvestmentAuthority, NO_INVESTMENT_AUTHORITY
from .identity import canonical_hash
from .market import MoneyDecimal
from .odds import (
    ODDS_DECIMAL_CONTEXT,
    FrozenOddsResearchArtifact,
    OddsResearchArtifact,
    ParticipationZone,
)
from .primitives import AwareDateTime, CurrencyCode, DomainValidationError, KernelModel
from .research import ResearchSnapshot, ResearchStatus


DECISION_REHEARSAL_ENGINE_VERSION = "decision-rehearsal-v1"
DECISION_REHEARSAL_LIMITATIONS = (
    "NON_BINDING_RESEARCH_ONLY",
    "FRAMING_IS_NON_AUTHORITATIVE",
    "NO_SYSTEM_INVESTMENT_DECISION",
    "NO_POSITION_SIZE_OR_TARGET_WEIGHT",
    "HUMAN_DECISION_REQUIRED",
)


class NonAuthoritativeRehearsalFraming(KernelModel):
    why_now: str = Field(min_length=1)
    current_expression: str = Field(min_length=1)
    authority: Literal["NON_AUTHORITATIVE_REHEARSAL_FRAMING"] = (
        "NON_AUTHORITATIVE_REHEARSAL_FRAMING"
    )
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_framing_text(self) -> "NonAuthoritativeRehearsalFraming":
        if not self.why_now.strip() or not self.current_expression.strip():
            raise ValueError("Decision Rehearsal framing text cannot be blank")
        return self


class RehearsalOddsSummary(KernelModel):
    valuation_horizon_date: date
    holding_period_days: int = Field(ge=1)
    expected_holding_period_return: Decimal
    positive_return_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    minimum_scenario_return: Decimal
    maximum_scenario_return: Decimal
    participation_zone: ParticipationZone
    calculation_limitations: tuple[str, ...]


class RehearsalParticipationCondition(KernelModel):
    threshold_basis_zone: ParticipationZone
    required_expected_return: Decimal
    required_positive_return_probability: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )
    model_risk_addon: Decimal = Field(ge=Decimal("0"))
    odds_context_addon: Decimal = Field(ge=Decimal("0"))
    policy_version: str = Field(min_length=1, max_length=128)


class OddsImprovementCondition(KernelModel):
    target_zone: ParticipationZone
    additional_expected_return_required: Decimal = Field(ge=Decimal("0"))
    additional_positive_return_probability_required: Decimal = Field(
        ge=Decimal("0"), le=Decimal("1")
    )


class DecisionRehearsalArtifact(KernelModel):
    id: UUID
    created_at: AwareDateTime
    as_of: AwareDateTime
    research_snapshot_id: UUID
    research_information_bundle_hash: str = Field(min_length=64, max_length=64)
    odds_artifact_id: UUID
    odds_artifact_hash: str = Field(min_length=64, max_length=64)
    ticker: str = Field(min_length=1, max_length=32)
    company_name: str = Field(min_length=1, max_length=255)
    exchange: str = Field(min_length=1, max_length=32)
    framing: NonAuthoritativeRehearsalFraming
    what_we_believe: str = Field(min_length=1)
    what_market_appears_to_believe: str = Field(min_length=1)
    current_price: MoneyDecimal = Field(gt=Decimal("0"))
    currency: CurrencyCode
    market_data_source: str = Field(min_length=1, max_length=128)
    price_convention: str = Field(min_length=1, max_length=128)
    odds: RehearsalOddsSummary
    participation_condition: RehearsalParticipationCondition
    odds_improvement_condition: OddsImprovementCondition
    open_questions: tuple[str, ...] = ()
    thesis_invalidation: tuple[str, ...] = Field(min_length=1)
    what_would_destroy_case: tuple[str, ...] = Field(min_length=1)
    monitoring_triggers: tuple[str, ...] = ()
    system_status: Literal["DECISION_REHEARSAL_ONLY"] = "DECISION_REHEARSAL_ONLY"
    human_status: Literal["HUMAN_DECISION_REQUIRED"] = "HUMAN_DECISION_REQUIRED"
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY
    limitations: tuple[str, ...]
    rehearsal_engine_version: Literal["decision-rehearsal-v1"] = (
        DECISION_REHEARSAL_ENGINE_VERSION
    )
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_non_binding_projection(self) -> "DecisionRehearsalArtifact":
        if self.created_at < self.as_of:
            raise ValueError("Decision Rehearsal cannot precede its frozen Odds as-of")
        expected_threshold_zone = (
            ParticipationZone.ACCEPTABLE_ODDS
            if self.odds.participation_zone is ParticipationZone.INSUFFICIENT_ODDS
            else self.odds.participation_zone
        )
        if self.participation_condition.threshold_basis_zone is not expected_threshold_zone:
            raise ValueError("participation condition must use the current or next Odds zone")
        if self.thesis_invalidation != self.what_would_destroy_case:
            raise ValueError("case destroyers must preserve the frozen thesis falsifiers")
        if tuple(self.limitations) != DECISION_REHEARSAL_LIMITATIONS:
            raise ValueError("Decision Rehearsal must expose its non-binding limitations")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("Decision Rehearsal cannot gain investment authority")
        return self


class FrozenDecisionRehearsalArtifact(KernelModel):
    artifact_hash: str = Field(min_length=64, max_length=64)
    artifact: DecisionRehearsalArtifact

    @model_validator(mode="after")
    def validate_artifact_hash(self) -> "FrozenDecisionRehearsalArtifact":
        if self.artifact_hash != canonical_hash(self.artifact):
            raise ValueError("Decision Rehearsal hash must cover the exact artifact")
        return self


class HumanDecisionBrief(KernelModel):
    decision_rehearsal_id: UUID
    decision_rehearsal_hash: str = Field(min_length=64, max_length=64)
    research_snapshot_id: UUID
    research_information_bundle_hash: str = Field(min_length=64, max_length=64)
    odds_artifact_id: UUID
    odds_artifact_hash: str = Field(min_length=64, max_length=64)
    ticker: str
    company_name: str
    as_of: AwareDateTime
    why_now: str
    current_belief: str
    market_expectation: str
    current_expression: str
    framing_authority: Literal["NON_AUTHORITATIVE_REHEARSAL_FRAMING"]
    current_price: MoneyDecimal
    currency: CurrencyCode
    market_data_source: str
    price_convention: str
    odds: RehearsalOddsSummary
    participation_condition: RehearsalParticipationCondition
    odds_improvement_condition: OddsImprovementCondition
    open_questions: tuple[str, ...]
    invalidation: tuple[str, ...]
    monitoring_triggers: tuple[str, ...]
    system_status: Literal["DECISION_REHEARSAL_ONLY"]
    human_status: Literal["HUMAN_DECISION_REQUIRED"]
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY
    schema_version: Literal[1] = 1


def build_decision_rehearsal(
    *,
    artifact_id: UUID,
    created_at: AwareDateTime,
    research_snapshot: ResearchSnapshot,
    odds_research: FrozenOddsResearchArtifact,
    framing: NonAuthoritativeRehearsalFraming,
) -> FrozenDecisionRehearsalArtifact:
    odds = odds_research.artifact
    if research_snapshot.status is not ResearchStatus.COMMITTED:
        raise DomainValidationError(
            "Decision Rehearsal requires a COMMITTED ResearchSnapshot"
        )
    if not research_snapshot.information_bundle_hash:
        raise DomainValidationError("Decision Rehearsal requires Research lineage")
    if (
        odds.research_snapshot_id != research_snapshot.id
        or odds.research_information_bundle_hash
        != research_snapshot.information_bundle_hash
    ):
        raise DomainValidationError(
            "Decision Rehearsal Odds must belong to its ResearchSnapshot"
        )
    if created_at < odds.created_at:
        raise DomainValidationError("Decision Rehearsal cannot precede Odds Research")

    market_expectation = research_snapshot.market_expectations_narrative
    if not research_snapshot.core_thesis.strip() or not (
        market_expectation and market_expectation.strip()
    ):
        raise DomainValidationError(
            "Decision Rehearsal requires explicit thesis and market expectations"
        )

    open_questions = _string_tuple(
        research_snapshot.open_questions,
        field="open_questions",
    )
    monitoring_triggers = _string_tuple(
        research_snapshot.monitoring_triggers,
        field="monitoring_triggers",
    )
    falsifiers = _required_string_tuple(
        research_snapshot.thesis_invalidation,
        field="thesis_invalidation",
    )
    threshold_zone, required_return, required_probability = _threshold_for_zone(odds)
    improvement_zone, improvement_return, improvement_probability = _improvement_for_zone(
        odds
    )

    artifact = DecisionRehearsalArtifact(
        id=artifact_id,
        created_at=created_at,
        as_of=odds.observed_market.market_timestamp,
        research_snapshot_id=research_snapshot.id,
        research_information_bundle_hash=research_snapshot.information_bundle_hash,
        odds_artifact_id=odds.id,
        odds_artifact_hash=odds_research.artifact_hash,
        ticker=research_snapshot.ticker,
        company_name=research_snapshot.company_name,
        exchange=research_snapshot.exchange,
        framing=framing,
        what_we_believe=research_snapshot.core_thesis,
        what_market_appears_to_believe=market_expectation,
        current_price=odds.observed_market.market_price,
        currency=odds.observed_market.currency,
        market_data_source=odds.observed_market.market_data_source,
        price_convention=odds.observed_market.price_convention,
        odds=RehearsalOddsSummary(
            valuation_horizon_date=odds.valuation_horizon_date,
            holding_period_days=odds.holding_period_days,
            expected_holding_period_return=odds.expected_holding_period_return,
            positive_return_probability=odds.positive_return_probability,
            minimum_scenario_return=odds.minimum_scenario_return,
            maximum_scenario_return=odds.maximum_scenario_return,
            participation_zone=odds.participation_zone,
            calculation_limitations=odds.limitations,
        ),
        participation_condition=RehearsalParticipationCondition(
            threshold_basis_zone=threshold_zone,
            required_expected_return=required_return,
            required_positive_return_probability=required_probability,
            model_risk_addon=odds.adjusted_thresholds.model_risk_addon,
            odds_context_addon=odds.adjusted_thresholds.odds_context_addon,
            policy_version=odds.policy.policy_version,
        ),
        odds_improvement_condition=OddsImprovementCondition(
            target_zone=improvement_zone,
            additional_expected_return_required=improvement_return,
            additional_positive_return_probability_required=improvement_probability,
        ),
        open_questions=open_questions,
        thesis_invalidation=falsifiers,
        what_would_destroy_case=falsifiers,
        monitoring_triggers=monitoring_triggers,
        limitations=DECISION_REHEARSAL_LIMITATIONS,
    )
    return freeze_decision_rehearsal(artifact)


def build_human_decision_brief(
    frozen: FrozenDecisionRehearsalArtifact,
) -> HumanDecisionBrief:
    artifact = frozen.artifact
    return HumanDecisionBrief(
        decision_rehearsal_id=artifact.id,
        decision_rehearsal_hash=frozen.artifact_hash,
        research_snapshot_id=artifact.research_snapshot_id,
        research_information_bundle_hash=artifact.research_information_bundle_hash,
        odds_artifact_id=artifact.odds_artifact_id,
        odds_artifact_hash=artifact.odds_artifact_hash,
        ticker=artifact.ticker,
        company_name=artifact.company_name,
        as_of=artifact.as_of,
        why_now=artifact.framing.why_now,
        current_belief=artifact.what_we_believe,
        market_expectation=artifact.what_market_appears_to_believe,
        current_expression=artifact.framing.current_expression,
        framing_authority=artifact.framing.authority,
        current_price=artifact.current_price,
        currency=artifact.currency,
        market_data_source=artifact.market_data_source,
        price_convention=artifact.price_convention,
        odds=artifact.odds,
        participation_condition=artifact.participation_condition,
        odds_improvement_condition=artifact.odds_improvement_condition,
        open_questions=artifact.open_questions,
        invalidation=artifact.thesis_invalidation,
        monitoring_triggers=artifact.monitoring_triggers,
        system_status=artifact.system_status,
        human_status=artifact.human_status,
        investment_authority=artifact.investment_authority,
    )


def freeze_decision_rehearsal(
    artifact: DecisionRehearsalArtifact,
) -> FrozenDecisionRehearsalArtifact:
    frozen = DecisionRehearsalArtifact.model_validate(
        artifact.model_dump(mode="python")
    )
    return FrozenDecisionRehearsalArtifact(
        artifact_hash=canonical_hash(frozen),
        artifact=frozen,
    )


def _threshold_for_zone(
    odds: OddsResearchArtifact,
) -> tuple[ParticipationZone, Decimal, Decimal]:
    thresholds = odds.adjusted_thresholds
    if odds.participation_zone is ParticipationZone.EXCEPTIONAL_ODDS:
        return (
            ParticipationZone.EXCEPTIONAL_ODDS,
            thresholds.exceptional_required_return,
            thresholds.exceptional_min_positive_probability,
        )
    if odds.participation_zone is ParticipationZone.ATTRACTIVE_ODDS:
        return (
            ParticipationZone.ATTRACTIVE_ODDS,
            thresholds.attractive_required_return,
            thresholds.attractive_min_positive_probability,
        )
    return (
        ParticipationZone.ACCEPTABLE_ODDS,
        thresholds.acceptable_required_return,
        thresholds.acceptable_min_positive_probability,
    )


def _improvement_for_zone(
    odds: OddsResearchArtifact,
) -> tuple[ParticipationZone, Decimal, Decimal]:
    thresholds = odds.adjusted_thresholds
    if odds.participation_zone is ParticipationZone.INSUFFICIENT_ODDS:
        target_zone = ParticipationZone.ACCEPTABLE_ODDS
        target_return = thresholds.acceptable_required_return
        target_probability = thresholds.acceptable_min_positive_probability
    elif odds.participation_zone is ParticipationZone.ACCEPTABLE_ODDS:
        target_zone = ParticipationZone.ATTRACTIVE_ODDS
        target_return = thresholds.attractive_required_return
        target_probability = thresholds.attractive_min_positive_probability
    else:
        target_zone = ParticipationZone.EXCEPTIONAL_ODDS
        target_return = thresholds.exceptional_required_return
        target_probability = thresholds.exceptional_min_positive_probability

    with localcontext(ODDS_DECIMAL_CONTEXT):
        return (
            target_zone,
            _nonnegative_difference(
                target_return, odds.expected_holding_period_return
            ),
            _nonnegative_difference(
                target_probability, odds.positive_return_probability
            ),
        )


def _nonnegative_difference(required: Decimal, current: Decimal) -> Decimal:
    difference = required - current
    if difference <= Decimal("0"):
        return Decimal("0")
    return difference.normalize()


def _string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise DomainValidationError(f"Decision Rehearsal requires tuple-like {field}")
    material = tuple(item.strip() for item in value if isinstance(item, str))
    if len(material) != len(value) or any(not item for item in material):
        raise DomainValidationError(
            f"Decision Rehearsal requires valid string values for {field}"
        )
    return material


def _required_string_tuple(value: object, *, field: str) -> tuple[str, ...]:
    material = _string_tuple(value, field=field)
    if not material:
        raise DomainValidationError(f"Decision Rehearsal requires non-empty {field}")
    return material
