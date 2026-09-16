"""Bounded Human-price analysis; never manufacture an ObservedMarket.

Consumes previously validated COMMITTED Research. Source qualification and
current Research eligibility belong to the caller, not to object construction.
No I/O, Research execution, persistence, provider, or investment authority.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .calculation import (
    CALCULATION_CONTEXT, ENGINE_VERSION, CalculationConvention,
    CalculationFailure, CalculationFailureCode, CalculationStatus,
    DatedExpectedDistributionResult, ExpectedDistributionCalculationInput,
    ScenarioCalculationInput, ValuationOddsCalculationInput, calculate_valuation_odds,
)
from .identity import canonical_hash
from .market import MoneyDecimal, ObservedMarket
from .odds import FrozenOddsResearchArtifact, OddsContext, OddsResearchPolicy, build_odds_research
from .primitives import AwareDateTime, CurrencyCode, DomainValidationError, KernelModel
from .research import CashFlowBasis, ResearchSnapshot, ResearchStatus

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OrdinalStatus = Literal[
    "ALL_DECLARED_WORLDS_POSITIVE", "ALL_DECLARED_WORLDS_NEGATIVE",
    "ALL_DECLARED_WORLDS_BREAK_EVEN", "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS",
    "ORDINAL_NOT_ESTABLISHED",
]
LIMITATIONS = (
    "DECLARED_WORLDS_ONLY_NOT_COMPLETE_DOWNSIDE",
    "SIGN_PATTERN_NOT_ODDS_JUDGMENT_OR_RECOMMENDATION",
    "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_NOT_ANNUALIZED",
    "NO_PROBABILITY_CALIBRATION_OR_MARKET_QUALIFICATION",
)


def _strict_boundary_literals(value: Any) -> Any:
    if isinstance(value, dict):
        if "schema_version" in value and type(value["schema_version"]) is not int:
            raise ValueError("schema_version must be an integer, not a coerced literal")
        for name in ("qualified_market_observation", "canonical_market_state", "research_reexecuted"):
            if name in value and type(value[name]) is not bool:
                raise ValueError(f"{name} must be an explicit boolean")
    return value


class HumanPriceContext(KernelModel):
    _literal_types = model_validator(mode="before")(_strict_boundary_literals)
    ticker: str = Field(min_length=1, max_length=32)
    exchange: str = Field(min_length=1, max_length=32)
    currency: CurrencyCode
    price: MoneyDecimal = Field(gt=Decimal("0"))
    price_timestamp: AwareDateTime
    utc_offset_minutes: int = Field(ge=-840, le=840, strict=True)
    supplied_at: AwareDateTime
    source_reference: str = Field(min_length=1, max_length=512)
    price_convention: str = Field(min_length=1, max_length=128)
    source: Literal["HUMAN_SUPPLIED_PROVISIONAL_PRICE"] = "HUMAN_SUPPLIED_PROVISIONAL_PRICE"
    authority: Literal["CONTEXT_ONLY"] = "CONTEXT_ONLY"
    qualified_market_observation: Literal[False] = False
    canonical_market_state: Literal[False] = False
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_context(self):
        if self.price_timestamp > self.supplied_at:
            raise ValueError("Human price cannot be supplied before its declared timestamp")
        if any(not getattr(self, n).strip() for n in
               ("ticker", "exchange", "source_reference", "price_convention")):
            raise ValueError("Human price identity and source declarations cannot be blank")
        return self

    @property
    def price_date(self) -> date:
        return self.price_timestamp.astimezone(
            timezone(timedelta(minutes=self.utc_offset_minutes))).date()


class ProvisionalWorldReturn(KernelModel):
    """Existing arithmetic projection without probability or weighted aggregate."""
    scenario_id: UUID
    scenario_name: str = Field(min_length=1, max_length=64)
    terminal_equity_value_per_share: Decimal
    expected_distributions: tuple[DatedExpectedDistributionResult, ...]
    total_expected_distributions_per_share: Decimal
    total_payoff_per_share: Decimal
    undiscounted_holding_period_return: Decimal


def _ordinal(worlds: tuple[ProvisionalWorldReturn, ...]) -> OrdinalStatus:
    returns = tuple(w.undiscounted_holding_period_return for w in worlds)
    if not returns:
        return "ORDINAL_NOT_ESTABLISHED"
    if all(r > 0 for r in returns):
        return "ALL_DECLARED_WORLDS_POSITIVE"
    if all(r < 0 for r in returns):
        return "ALL_DECLARED_WORLDS_NEGATIVE"
    if all(r == 0 for r in returns):
        return "ALL_DECLARED_WORLDS_BREAK_EVEN"
    return "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"


class ProvisionalOddsArtifact(KernelModel):
    _literal_types = model_validator(mode="before")(_strict_boundary_literals)
    id: UUID
    created_at: AwareDateTime
    research_snapshot_id: UUID
    research_information_bundle_hash: Hash
    research_snapshot_hash: Hash
    price_context: HumanPriceContext
    valuation_horizon_date: date | None
    calculation_status: CalculationStatus
    ordinal_status: OrdinalStatus
    world_results: tuple[ProvisionalWorldReturn, ...] = ()
    failures: tuple[CalculationFailure, ...] = ()
    odds_status: Literal["PROVISIONAL"] = "PROVISIONAL"
    cardinal_probability: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    market_qualification: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"
    human_acceptance: Literal["NOT_ESTABLISHED_BY_THIS_OPERATION"] = "NOT_ESTABLISHED_BY_THIS_OPERATION"
    research_reexecuted: Literal[False] = False
    investment_authority: Literal["NONE"] = "NONE"
    calculation_convention: Literal["UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1"] = (
        CalculationConvention.UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1.value)
    engine_version: Literal["phase2a-valuation-odds-v1"] = ENGINE_VERSION
    limitations: tuple[str, ...] = LIMITATIONS
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_projection_shape(self):
        if self.created_at < self.price_context.supplied_at:
            raise ValueError("provisional result cannot precede the supplied price")
        if self.calculation_status is CalculationStatus.CALCULATED:
            if not self.world_results or self.failures or self.valuation_horizon_date is None:
                raise ValueError("CALCULATED requires declared worlds and horizon without failures")
            if self.valuation_horizon_date <= self.price_context.price_date:
                raise ValueError("provisional horizon must remain in the future")
        elif self.world_results or not self.failures:
            raise ValueError("NO_CALCULATION requires failures and forbids partial results")
        if len({w.scenario_id for w in self.world_results}) != len(self.world_results):
            raise ValueError("provisional world identities must be unique")
        if self.ordinal_status != _ordinal(self.world_results) or self.limitations != LIMITATIONS:
            raise ValueError("provisional sign pattern and limitations must match the projection")
        return self


class FrozenProvisionalOdds(KernelModel):
    artifact_hash: Hash
    artifact: ProvisionalOddsArtifact

    @model_validator(mode="after")
    def validate_hash(self):
        if self.artifact_hash != canonical_hash(self.artifact):
            raise ValueError("provisional hash must cover the exact artifact")
        return self


def _committed(snapshot: ResearchSnapshot) -> ResearchSnapshot:
    if not isinstance(snapshot, ResearchSnapshot):
        raise DomainValidationError("a validated ResearchSnapshot is required")
    snapshot = ResearchSnapshot.model_validate(snapshot.model_dump(mode="python"))
    if snapshot.status is not ResearchStatus.COMMITTED or snapshot.committed_at is None:
        raise DomainValidationError("provisional analysis requires COMMITTED Research")
    if snapshot.committed_at < max(snapshot.created_at, snapshot.as_of_datetime):
        raise DomainValidationError("invalid committed Research chronology")
    if snapshot.schema_version == 1:
        snapshot.assert_decision_spine_ready()
    else:
        snapshot.assert_research_ready()
    return snapshot


def _failures(snapshot: ResearchSnapshot, context: HumanPriceContext) -> tuple[CalculationFailure, ...]:
    """Context-only input checks. No qualification or ObservedMarket is created."""
    failures = []
    def fail(code, location, message):
        failures.append(CalculationFailure(code=code, location=location, message=message))
    unsupported = CalculationFailureCode.UNSUPPORTED_CALCULATION_INPUT
    if snapshot.valuation_horizon_date is None or snapshot.valuation_horizon_date <= context.price_date:
        fail(unsupported, "valuation_horizon_date", "a future frozen valuation horizon is required")
    if not snapshot.scenarios:
        fail(CalculationFailureCode.INCOMPLETE_SCENARIO_DISTRIBUTION,
             "research_snapshot.scenarios", "no declared numerical worlds; do not invent probabilities")
    used = {s.valuation_basis_id for s in snapshot.scenarios}
    for basis in snapshot.valuation_bases:
        if basis.id not in used:
            continue
        if basis.currency != snapshot.currency:
            fail(CalculationFailureCode.FX_CONVERSION_REQUIRED, f"valuation_basis:{basis.id}",
                 "ValuationBasis currency differs from Research")
        if basis.as_of_datetime > snapshot.as_of_datetime:
            fail(CalculationFailureCode.PIT_VIOLATION, f"valuation_basis:{basis.id}",
                 "ValuationBasis is later than frozen Research cutoff")
    for scenario in snapshot.scenarios:
        for flow in scenario.expected_cash_flows:
            loc = f"expected_cash_flow:{flow.id}"
            if flow.basis is not CashFlowBasis.PER_SHARE:
                fail(CalculationFailureCode.TOTAL_EQUITY_UNSUPPORTED, loc, "PER_SHARE cash flows only")
            if flow.currency != snapshot.currency:
                fail(CalculationFailureCode.FX_CONVERSION_REQUIRED, loc, "cash flow currency differs")
            if flow.cash_flow_date <= context.price_date:
                fail(unsupported, loc, "do not silently reuse or remove a past expected distribution")
    return tuple(sorted(failures, key=lambda f: (f.code.value, f.location, f.message)))


def build_provisional_odds(*, research_snapshot: ResearchSnapshot, price_context: HumanPriceContext,
                           artifact_id: UUID, created_at: datetime) -> FrozenProvisionalOdds:
    snapshot = _committed(research_snapshot)
    if not isinstance(price_context, HumanPriceContext):
        raise DomainValidationError("a HumanPriceContext is required, not an ObservedMarket")
    context = HumanPriceContext.model_validate(price_context.model_dump(mode="python"))
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise DomainValidationError("provisional creation time must be timezone-aware")
    if ((context.ticker, context.exchange, context.currency)
            != (snapshot.ticker, snapshot.exchange, snapshot.currency)):
        raise DomainValidationError("Human price and Research security/currency must match")
    if not (snapshot.as_of_datetime <= context.price_timestamp <= context.supplied_at <= created_at
            and snapshot.committed_at <= created_at):
        raise DomainValidationError("provisional Research/price/creation chronology is invalid")
    failures = _failures(snapshot, context)
    worlds = ()
    if not failures:
        # Reuse only explicitly declared numerical state. The existing arithmetic
        # internally calculates its aggregate; neither it nor probability fields
        # enter the provisional projection. No fake market observation is needed.
        calculated = calculate_valuation_odds(ValuationOddsCalculationInput(
            research_snapshot_id=snapshot.id, calculation_currency=snapshot.currency,
            observed_market_price=context.price,
            scenarios=tuple(ScenarioCalculationInput(
                scenario_id=s.id, scenario_name=s.name, probability=s.probability,
                terminal_equity_value_per_share=s.terminal_equity_value_per_share,
                expected_distributions=tuple(ExpectedDistributionCalculationInput(
                    expected_cash_flow_id=f.id, cash_flow_date=f.cash_flow_date,
                    amount_per_share=f.amount, currency=f.currency, cash_flow_type=f.cash_flow_type,
                ) for f in s.expected_cash_flows),
            ) for s in snapshot.scenarios),
        ))
        worlds = tuple(ProvisionalWorldReturn.model_validate(
            w.model_dump(mode="python", exclude={"probability"})) for w in calculated.scenario_results)
    artifact = ProvisionalOddsArtifact(
        id=artifact_id, created_at=created_at, research_snapshot_id=snapshot.id,
        research_information_bundle_hash=snapshot.information_bundle_hash,
        research_snapshot_hash=canonical_hash(snapshot), price_context=context,
        valuation_horizon_date=snapshot.valuation_horizon_date,
        calculation_status=CalculationStatus.NO_CALCULATION if failures else CalculationStatus.CALCULATED,
        ordinal_status=_ordinal(worlds), world_results=worlds, failures=failures,
    )
    return FrozenProvisionalOdds(artifact_hash=canonical_hash(artifact), artifact=artifact)


def verify_provisional_odds(result: FrozenProvisionalOdds, research_snapshot: ResearchSnapshot) -> FrozenProvisionalOdds:
    """Rebuild from the frozen Research; even a rehashed edited result is rejected."""
    snapshot = _committed(research_snapshot)
    result = FrozenProvisionalOdds.model_validate(result.model_dump(mode="python"))
    prior = result.artifact
    if (prior.research_snapshot_hash != canonical_hash(snapshot)
            or prior.research_snapshot_id != snapshot.id
            or prior.research_information_bundle_hash != snapshot.information_bundle_hash):
        raise DomainValidationError("REUNDERWRITE_REQUIRED: frozen Research identity changed")
    expected = build_provisional_odds(research_snapshot=snapshot, price_context=prior.price_context,
                                     artifact_id=prior.id, created_at=prior.created_at)
    if result != expected:
        raise DomainValidationError("provisional result differs from deterministic recomputation")
    return result


class SameResearchOddsComparison(KernelModel):
    _literal_types = model_validator(mode="before")(_strict_boundary_literals)
    provisional: FrozenProvisionalOdds
    canonical: FrozenOddsResearchArtifact
    market_ticker: str
    market_exchange: str
    price_change: Decimal
    route: Literal["PRICE_ONLY_SAME_FROZEN_RESEARCH"] = "PRICE_ONLY_SAME_FROZEN_RESEARCH"
    meaning: Literal["SIDE_BY_SIDE_NOT_PROVISIONAL_PROMOTION"] = "SIDE_BY_SIDE_NOT_PROVISIONAL_PROMOTION"
    research_reexecuted: Literal[False] = False
    market_qualification: Literal["CALLER_RESPONSIBILITY_NOT_ESTABLISHED_BY_TYPE"] = "CALLER_RESPONSIBILITY_NOT_ESTABLISHED_BY_TYPE"
    probability_calibration: Literal["NOT_ESTABLISHED_BY_THIS_OPERATION"] = "NOT_ESTABLISHED_BY_THIS_OPERATION"
    human_acceptance: Literal["NOT_ESTABLISHED_BY_THIS_OPERATION"] = "NOT_ESTABLISHED_BY_THIS_OPERATION"
    investment_authority: Literal["NONE"] = "NONE"
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_comparison(self):
        p, c = self.provisional.artifact, self.canonical.artifact
        pc, market = p.price_context, c.observed_market
        if p.calculation_status is not CalculationStatus.CALCULATED:
            raise ValueError("a non-numerical provisional result cannot become a numerical comparison")
        if "HUMAN_SUPPLIED" in market.market_data_source.upper():
            raise ValueError("Human-supplied context is not a separately qualified Market")
        before = {w.scenario_id: w.model_dump(mode="python", exclude={
            "undiscounted_holding_period_return"}) for w in p.world_results}
        after = {w.scenario_id: w.model_dump(mode="python", exclude={
            "undiscounted_holding_period_return", "probability"})
                 for w in c.calculation.scenario_results}
        if before != after:
            raise ValueError("comparison must preserve each declared world and dated payoff")
        if (p.research_snapshot_id != c.research_snapshot_id
                or p.research_information_bundle_hash != c.research_information_bundle_hash
                or p.valuation_horizon_date != c.valuation_horizon_date):
            raise ValueError("comparison must preserve Research identity and horizon")
        if ((self.market_ticker, self.market_exchange) != (pc.ticker, pc.exchange)
                or market.currency != pc.currency or market.price_convention != pc.price_convention
                or market.market_utc_offset_minutes != pc.utc_offset_minutes):
            raise ValueError("comparison security/currency/convention/offset must match")
        if c.created_at < p.created_at or market.market_timestamp < pc.price_timestamp:
            raise ValueError("comparison cannot reverse result or price chronology")
        with localcontext(CALCULATION_CONTEXT):
            if self.price_change != market.market_price - pc.price:
                raise ValueError("price change must match the two distinct inputs")
        return self


def recompute_canonical_odds(*, provisional: FrozenProvisionalOdds, research_snapshot: ResearchSnapshot,
                             observed_market: ObservedMarket, market_ticker: str, market_exchange: str,
                             artifact_id: UUID, created_at: datetime, policy: OddsResearchPolicy,
                             odds_context: OddsContext | None = None) -> SameResearchOddsComparison:
    """Use an independently qualified same-security Market, never a Human price.

ObservedMarket has no security/receipt fields. Its caller must perform existing
provider qualification and bind ticker/exchange before calling this pure adapter.
Those declarations and this type check do not themselves prove market provenance.
"""
    snapshot = _committed(research_snapshot)
    prior = verify_provisional_odds(provisional, snapshot)
    if not isinstance(observed_market, ObservedMarket):
        raise DomainValidationError("canonical recompute requires a separately qualified ObservedMarket")
    market = ObservedMarket.model_validate(observed_market.model_dump(mode="python"))
    if "HUMAN_SUPPLIED" in market.market_data_source.upper():
        raise DomainValidationError("Human-supplied context cannot be relabelled as canonical Market")
    context = prior.artifact.price_context
    if ((market_ticker, market_exchange, market.currency, market.price_convention,
         market.market_utc_offset_minutes) != (context.ticker, context.exchange, context.currency,
                                              context.price_convention, context.utc_offset_minutes)):
        raise DomainValidationError("independently supplied Market identity/convention differs")
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise DomainValidationError("canonical creation time must be timezone-aware")
    if created_at < prior.artifact.created_at or market.market_timestamp < context.price_timestamp:
        raise DomainValidationError("canonical comparison cannot reverse chronology")
    policy = OddsResearchPolicy.model_validate(policy.model_dump(mode="python"))
    if odds_context is not None:
        odds_context = OddsContext.model_validate(odds_context.model_dump(mode="python"))
    canonical = build_odds_research(artifact_id=artifact_id, created_at=created_at,
                                  research_snapshot=snapshot, observed_market=market,
                                  policy=policy, odds_context=odds_context)
    with localcontext(CALCULATION_CONTEXT):
        delta = market.market_price - context.price
    return SameResearchOddsComparison(provisional=prior, canonical=canonical,
                                      market_ticker=market_ticker, market_exchange=market_exchange,
                                      price_change=delta)


def verify_same_research_comparison(
    result: SameResearchOddsComparison, research_snapshot: ResearchSnapshot,
) -> SameResearchOddsComparison:
    """Verify serialized comparison against the same trusted frozen Research.

    Recomputes both sides; a self-consistent edited hash is not acceptance.
    The caller still owns market-source qualification and Research eligibility.
    """
    result = SameResearchOddsComparison.model_validate(result.model_dump(mode="python"))
    c = result.canonical.artifact
    expected = recompute_canonical_odds(
        provisional=result.provisional, research_snapshot=research_snapshot,
        observed_market=c.observed_market, market_ticker=result.market_ticker,
        market_exchange=result.market_exchange, artifact_id=c.id, created_at=c.created_at,
        policy=c.policy, odds_context=c.odds_context,
    )
    if result != expected:
        raise DomainValidationError("comparison differs from original canonical recomputation")
    return result
