"""Probability-free conditional-world analysis bound to exact frozen Research.

This is a #321-B decision-use adapter, not canonical Odds. It accepts only a
HumanPriceContext from #405, never ObservedMarket, and never invents scenario
probabilities or a probability-weighted aggregate. Canonical Market/Odds policy
remains unchanged.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .calculation import (
    CALCULATION_CONTEXT,
    ENGINE_VERSION,
    ONE,
    ZERO,
    CalculationConvention,
    CalculationFailure,
    CalculationFailureCode,
    CalculationStatus,
    DatedExpectedDistributionResult,
    _normalized,
)
from .identity import canonical_hash
from .primitives import AwareDateTime, CurrencyCode, DomainValidationError, KernelModel
from .provisional_odds import HumanPriceContext, _committed
from .research import CashFlowBasis, CashFlowType, ResearchSnapshot


Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ClockSemantics = Literal[
    "AT_OR_AFTER_RESEARCH_CUTOFF_CONTEXT_ONLY",
    "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT",
]
OrdinalStatus = Literal[
    "ALL_DECLARED_WORLDS_POSITIVE",
    "ALL_DECLARED_WORLDS_NEGATIVE",
    "ALL_DECLARED_WORLDS_BREAK_EVEN",
    "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS",
    "ORDINAL_NOT_ESTABLISHED",
]
BASE_LIMITATIONS = (
    "DECLARED_CONDITIONAL_WORLDS_NOT_COMPLETE_DOWNSIDE",
    "NO_WORLD_PROBABILITIES_OR_WEIGHTED_AGGREGATE",
    "SIGN_PATTERN_NOT_ODDS_JUDGMENT_OR_RECOMMENDATION",
    "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_NOT_ANNUALIZED",
    "HUMAN_PRICE_CONTEXT_ONLY_NOT_MARKET_QUALIFICATION",
)
RETROSPECTIVE_LIMITATION = (
    "RETROSPECTIVE_REFERENCE_PRICE_USES_LATER_FROZEN_RESEARCH_NOT_PIT_ANALYSIS"
)


class ConditionalExpectedDistribution(KernelModel):
    id: UUID
    world_id: UUID
    cash_flow_date: date
    amount_per_share: Decimal
    currency: CurrencyCode
    cash_flow_type: CashFlowType
    provenance_artifact_ids: tuple[UUID, ...] = Field(min_length=1)
    basis: Literal["PER_SHARE"] = "PER_SHARE"


class DeclaredConditionalWorld(KernelModel):
    """A declared outcome conditional on assumptions, never a probability state."""

    id: UUID
    name: str = Field(min_length=1, max_length=64)
    terminal_equity_value_per_share: Decimal
    operating_conditions: tuple[str, ...] = Field(min_length=1, max_length=32)
    valuation_expression: str = Field(min_length=1, max_length=2048)
    provenance_artifact_ids: tuple[UUID, ...] = Field(min_length=1)
    expected_distributions: tuple[ConditionalExpectedDistribution, ...] = ()
    valuation_basis_id: UUID | None = None
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_world(self):
        if any(not condition.strip() for condition in self.operating_conditions):
            raise ValueError("conditional-world operating conditions cannot be blank")
        if not self.valuation_expression.strip():
            raise ValueError("conditional-world valuation expression cannot be blank")
        if any(flow.world_id != self.id for flow in self.expected_distributions):
            raise ValueError("conditional-world distribution must reference its world")
        if len({flow.id for flow in self.expected_distributions}) != len(
            self.expected_distributions
        ):
            raise ValueError("conditional-world distribution ids must be unique")
        return self


class ConditionalWorldSetArtifact(KernelModel):
    id: UUID
    created_at: AwareDateTime
    research_snapshot_id: UUID
    research_information_bundle_hash: Hash
    research_snapshot_hash: Hash
    currency: CurrencyCode
    valuation_horizon_date: date
    worlds: tuple[DeclaredConditionalWorld, ...] = Field(min_length=1, max_length=12)
    probability_status: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    semantics: Literal[
        "DECLARED_CONDITIONAL_WORLDS_NOT_PROBABILITY_DISTRIBUTION"
    ] = "DECLARED_CONDITIONAL_WORLDS_NOT_PROBABILITY_DISTRIBUTION"
    human_acceptance: Literal[
        "NOT_ESTABLISHED_BY_THIS_DECLARATION"
    ] = "NOT_ESTABLISHED_BY_THIS_DECLARATION"
    investment_authority: Literal["NONE"] = "NONE"
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_world_set(self):
        if len({world.id for world in self.worlds}) != len(self.worlds):
            raise ValueError("conditional-world ids must be unique")
        if len({world.name for world in self.worlds}) != len(self.worlds):
            raise ValueError("conditional-world names must be unique")
        if any(
            flow.cash_flow_date > self.valuation_horizon_date
            for world in self.worlds
            for flow in world.expected_distributions
        ):
            raise ValueError("conditional-world distribution cannot follow the horizon")
        if any(
            flow.currency != self.currency
            for world in self.worlds
            for flow in world.expected_distributions
        ):
            raise ValueError("conditional-world distributions must use set currency")
        return self


class FrozenConditionalWorldSet(KernelModel):
    world_set_hash: Hash
    world_set: ConditionalWorldSetArtifact

    @model_validator(mode="after")
    def validate_hash(self):
        if self.world_set_hash != canonical_hash(self.world_set):
            raise ValueError("conditional-world hash must cover the exact world set")
        return self


class ConditionalWorldReturn(KernelModel):
    world_id: UUID
    world_name: str = Field(min_length=1, max_length=64)
    terminal_equity_value_per_share: Decimal
    expected_distributions: tuple[DatedExpectedDistributionResult, ...]
    total_expected_distributions_per_share: Decimal
    total_payoff_per_share: Decimal
    undiscounted_holding_period_return: Decimal


def _ordinal(worlds: tuple[ConditionalWorldReturn, ...]) -> OrdinalStatus:
    returns = tuple(world.undiscounted_holding_period_return for world in worlds)
    if not returns:
        return "ORDINAL_NOT_ESTABLISHED"
    if all(value > ZERO for value in returns):
        return "ALL_DECLARED_WORLDS_POSITIVE"
    if all(value < ZERO for value in returns):
        return "ALL_DECLARED_WORLDS_NEGATIVE"
    if all(value == ZERO for value in returns):
        return "ALL_DECLARED_WORLDS_BREAK_EVEN"
    return "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"


class ConditionalProvisionalOddsArtifact(KernelModel):
    id: UUID
    created_at: AwareDateTime
    research_snapshot_id: UUID
    research_information_bundle_hash: Hash
    research_snapshot_hash: Hash
    conditional_worlds: FrozenConditionalWorldSet
    price_context: HumanPriceContext
    price_clock_semantics: ClockSemantics
    valuation_horizon_date: date
    calculation_status: CalculationStatus
    ordinal_status: OrdinalStatus
    world_results: tuple[ConditionalWorldReturn, ...] = ()
    failures: tuple[CalculationFailure, ...] = ()
    odds_status: Literal[
        "PROVISIONAL_CONDITIONAL_ORDINAL"
    ] = "PROVISIONAL_CONDITIONAL_ORDINAL"
    cardinal_probability: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    probability_input: Literal["ABSENT_BY_DESIGN"] = "ABSENT_BY_DESIGN"
    weighted_aggregate: Literal["NOT_COMPUTED"] = "NOT_COMPUTED"
    market_qualification: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    canonical_odds: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    human_acceptance: Literal[
        "NOT_ESTABLISHED_BY_THIS_OPERATION"
    ] = "NOT_ESTABLISHED_BY_THIS_OPERATION"
    research_reexecuted: Literal[False] = False
    investment_authority: Literal["NONE"] = "NONE"
    calculation_convention: Literal[
        "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1"
    ] = CalculationConvention.UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1.value
    calculation_engine_version: Literal[
        "phase2a-valuation-odds-v1"
    ] = ENGINE_VERSION
    adapter_version: Literal[
        "probability-free-conditional-worlds-v1"
    ] = "probability-free-conditional-worlds-v1"
    limitations: tuple[str, ...] = BASE_LIMITATIONS
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_result_shape(self):
        expected_limitations = BASE_LIMITATIONS
        if self.price_clock_semantics == "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT":
            expected_limitations = (*BASE_LIMITATIONS, RETROSPECTIVE_LIMITATION)
        if self.limitations != expected_limitations:
            raise ValueError("conditional result limitations must match clock semantics")
        if self.calculation_status is CalculationStatus.CALCULATED:
            if not self.world_results or self.failures:
                raise ValueError("CALCULATED requires world results without failures")
        elif self.world_results or not self.failures:
            raise ValueError("NO_CALCULATION requires failures and forbids partial results")
        if self.ordinal_status != _ordinal(self.world_results):
            raise ValueError("conditional result ordinal state must match world returns")
        if self.conditional_worlds.world_set.valuation_horizon_date != self.valuation_horizon_date:
            raise ValueError("conditional result horizon must match declared worlds")
        return self


class FrozenConditionalProvisionalOdds(KernelModel):
    artifact_hash: Hash
    artifact: ConditionalProvisionalOddsArtifact

    @model_validator(mode="after")
    def validate_hash(self):
        if self.artifact_hash != canonical_hash(self.artifact):
            raise ValueError("conditional provisional hash must cover exact artifact")
        return self


def _evidence_ids(snapshot: ResearchSnapshot) -> set[UUID]:
    return {link.evidence_artifact_id for link in snapshot.evidence_links}


def build_conditional_world_set(
    *,
    research_snapshot: ResearchSnapshot,
    worlds: tuple[DeclaredConditionalWorld, ...],
    valuation_horizon_date: date,
    world_set_id: UUID,
    created_at: datetime,
) -> FrozenConditionalWorldSet:
    """Freeze probability-free decision-use worlds against exact COMMITTED Research."""

    snapshot = _committed(research_snapshot)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise DomainValidationError("conditional-world creation time must be timezone-aware")
    if snapshot.committed_at is None or created_at < snapshot.committed_at:
        raise DomainValidationError("conditional worlds cannot precede Research commit")
    if valuation_horizon_date <= snapshot.as_of_datetime.date():
        raise DomainValidationError("conditional-world horizon must follow Research cutoff")
    if (
        snapshot.valuation_horizon_date is not None
        and valuation_horizon_date != snapshot.valuation_horizon_date
    ):
        raise DomainValidationError(
            "existing frozen Research horizon cannot be silently replaced"
        )

    evidence_ids = _evidence_ids(snapshot)
    basis_ids = {basis.id for basis in snapshot.valuation_bases}
    for world in worlds:
        if not set(world.provenance_artifact_ids).issubset(evidence_ids):
            raise DomainValidationError(
                "conditional world cites Evidence outside frozen Research"
            )
        if world.valuation_basis_id is not None and world.valuation_basis_id not in basis_ids:
            raise DomainValidationError(
                "conditional world cites ValuationBasis outside frozen Research"
            )
        for flow in world.expected_distributions:
            if not set(flow.provenance_artifact_ids).issubset(evidence_ids):
                raise DomainValidationError(
                    "conditional distribution cites Evidence outside frozen Research"
                )

    artifact = ConditionalWorldSetArtifact(
        id=world_set_id,
        created_at=created_at,
        research_snapshot_id=snapshot.id,
        research_information_bundle_hash=snapshot.information_bundle_hash,
        research_snapshot_hash=canonical_hash(snapshot),
        currency=snapshot.currency,
        valuation_horizon_date=valuation_horizon_date,
        worlds=worlds,
    )
    return FrozenConditionalWorldSet(
        world_set_hash=canonical_hash(artifact),
        world_set=artifact,
    )


def verify_conditional_world_set(
    result: FrozenConditionalWorldSet,
    research_snapshot: ResearchSnapshot,
) -> FrozenConditionalWorldSet:
    snapshot = _committed(research_snapshot)
    result = FrozenConditionalWorldSet.model_validate(result.model_dump(mode="python"))
    artifact = result.world_set
    if (
        artifact.research_snapshot_id != snapshot.id
        or artifact.research_information_bundle_hash != snapshot.information_bundle_hash
        or artifact.research_snapshot_hash != canonical_hash(snapshot)
    ):
        raise DomainValidationError(
            "REUNDERWRITE_REQUIRED: conditional worlds bind different Research"
        )
    expected = build_conditional_world_set(
        research_snapshot=snapshot,
        worlds=artifact.worlds,
        valuation_horizon_date=artifact.valuation_horizon_date,
        world_set_id=artifact.id,
        created_at=artifact.created_at,
    )
    if result != expected:
        raise DomainValidationError(
            "conditional-world set differs from deterministic reconstruction"
        )
    return result


def _clock_semantics(
    snapshot: ResearchSnapshot, context: HumanPriceContext
) -> ClockSemantics:
    if context.price_timestamp < snapshot.as_of_datetime:
        return "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT"
    return "AT_OR_AFTER_RESEARCH_CUTOFF_CONTEXT_ONLY"


def _failures(
    snapshot: ResearchSnapshot,
    world_set: ConditionalWorldSetArtifact,
    context: HumanPriceContext,
) -> tuple[CalculationFailure, ...]:
    failures: list[CalculationFailure] = []

    def fail(code, location, message):
        failures.append(
            CalculationFailure(code=code, location=location, message=message)
        )

    if world_set.valuation_horizon_date <= context.price_date:
        fail(
            CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
            "valuation_horizon_date",
            "conditional-world horizon must follow the reference price date",
        )
    for world in world_set.worlds:
        for flow in world.expected_distributions:
            location = f"conditional_distribution:{flow.id}"
            if flow.currency != snapshot.currency:
                fail(
                    CalculationFailureCode.FX_CONVERSION_REQUIRED,
                    location,
                    "conditional distribution currency differs from Research",
                )
            if flow.cash_flow_date <= context.price_date:
                fail(
                    CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT,
                    location,
                    "conditional distribution must follow the reference price date",
                )
    return tuple(
        sorted(
            failures,
            key=lambda item: (item.code.value, item.location, item.message),
        )
    )


def _calculate_world(
    world: DeclaredConditionalWorld,
    reference_price: Decimal,
) -> ConditionalWorldReturn:
    """Use the canonical calculation context/normalization without probability."""

    distributions = tuple(
        DatedExpectedDistributionResult(
            expected_cash_flow_id=flow.id,
            cash_flow_date=flow.cash_flow_date,
            amount_per_share=_normalized(flow.amount_per_share),
            basis=CashFlowBasis.PER_SHARE,
            currency=flow.currency,
            cash_flow_type=flow.cash_flow_type,
        )
        for flow in sorted(
            world.expected_distributions,
            key=lambda item: (item.cash_flow_date, str(item.id)),
        )
    )
    total_distributions = _normalized(
        sum((distribution.amount_per_share for distribution in distributions), ZERO)
    )
    terminal_value = _normalized(world.terminal_equity_value_per_share)
    total_payoff = _normalized(terminal_value + total_distributions)
    holding_period_return = _normalized((total_payoff / reference_price) - ONE)
    return ConditionalWorldReturn(
        world_id=world.id,
        world_name=world.name,
        terminal_equity_value_per_share=terminal_value,
        expected_distributions=distributions,
        total_expected_distributions_per_share=total_distributions,
        total_payoff_per_share=total_payoff,
        undiscounted_holding_period_return=holding_period_return,
    )


def build_conditional_provisional_odds(
    *,
    research_snapshot: ResearchSnapshot,
    conditional_worlds: FrozenConditionalWorldSet,
    price_context: HumanPriceContext,
    artifact_id: UUID,
    created_at: datetime,
) -> FrozenConditionalProvisionalOdds:
    """Calculate declared-world returns at Human CONTEXT_ONLY price, no probability."""

    snapshot = _committed(research_snapshot)
    worlds = verify_conditional_world_set(conditional_worlds, snapshot)
    if not isinstance(price_context, HumanPriceContext):
        raise DomainValidationError(
            "conditional provisional analysis requires HumanPriceContext"
        )
    context = HumanPriceContext.model_validate(
        price_context.model_dump(mode="python")
    )
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise DomainValidationError(
            "conditional provisional creation time must be timezone-aware"
        )
    if (
        (context.ticker, context.exchange, context.currency)
        != (snapshot.ticker, snapshot.exchange, snapshot.currency)
    ):
        raise DomainValidationError(
            "conditional price and Research security/currency must match"
        )
    if snapshot.committed_at is None:
        raise DomainValidationError("conditional provisional requires committed Research")
    if max(
        snapshot.committed_at,
        worlds.world_set.created_at,
        context.supplied_at,
    ) > created_at:
        raise DomainValidationError(
            "conditional Research/world/price/result chronology is invalid"
        )

    failures = _failures(snapshot, worlds.world_set, context)
    results: tuple[ConditionalWorldReturn, ...] = ()
    if not failures:
        with localcontext(CALCULATION_CONTEXT):
            results = tuple(
                _calculate_world(world, context.price)
                for world in sorted(
                    worlds.world_set.worlds,
                    key=lambda item: (item.name, str(item.id)),
                )
            )
    clock = _clock_semantics(snapshot, context)
    limitations = BASE_LIMITATIONS
    if clock == "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT":
        limitations = (*BASE_LIMITATIONS, RETROSPECTIVE_LIMITATION)
    artifact = ConditionalProvisionalOddsArtifact(
        id=artifact_id,
        created_at=created_at,
        research_snapshot_id=snapshot.id,
        research_information_bundle_hash=snapshot.information_bundle_hash,
        research_snapshot_hash=canonical_hash(snapshot),
        conditional_worlds=worlds,
        price_context=context,
        price_clock_semantics=clock,
        valuation_horizon_date=worlds.world_set.valuation_horizon_date,
        calculation_status=(
            CalculationStatus.NO_CALCULATION
            if failures
            else CalculationStatus.CALCULATED
        ),
        ordinal_status=_ordinal(results),
        world_results=results,
        failures=failures,
        limitations=limitations,
    )
    return FrozenConditionalProvisionalOdds(
        artifact_hash=canonical_hash(artifact),
        artifact=artifact,
    )


def verify_conditional_provisional_odds(
    result: FrozenConditionalProvisionalOdds,
    research_snapshot: ResearchSnapshot,
) -> FrozenConditionalProvisionalOdds:
    """Rebuild result from exact Research + embedded frozen conditional worlds."""

    snapshot = _committed(research_snapshot)
    result = FrozenConditionalProvisionalOdds.model_validate(
        result.model_dump(mode="python")
    )
    artifact = result.artifact
    if (
        artifact.research_snapshot_id != snapshot.id
        or artifact.research_information_bundle_hash != snapshot.information_bundle_hash
        or artifact.research_snapshot_hash != canonical_hash(snapshot)
    ):
        raise DomainValidationError(
            "REUNDERWRITE_REQUIRED: conditional result binds different Research"
        )
    expected = build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=artifact.conditional_worlds,
        price_context=artifact.price_context,
        artifact_id=artifact.id,
        created_at=artifact.created_at,
    )
    if result != expected:
        raise DomainValidationError(
            "conditional provisional result differs from deterministic reconstruction"
        )
    return result
