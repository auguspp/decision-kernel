"""Probability-free conditional worlds; synthetic engineering contract tests only."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.calculation import CalculationStatus, calculate_research_economics
from decision_kernel.conditional_odds import (
    ConditionalExpectedDistribution,
    DeclaredConditionalWorld,
    FrozenConditionalProvisionalOdds,
    FrozenConditionalWorldSet,
    build_conditional_provisional_odds,
    build_conditional_world_set,
    verify_conditional_provisional_odds,
    verify_conditional_world_set,
)
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.market import ObservedMarket
from decision_kernel.primitives import DomainValidationError
from decision_kernel.provisional_odds import HumanPriceContext
from decision_kernel.research import Scenario
from decision_kernel.research_commit import commit_research_package
from test_deep_research import AS_OF, COMMIT_AT
from test_generic_research_commit import _generic_package
from test_research_only_commit_v2 import v2_package


CONVENTION = "RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE"
AFTER_COMMIT = COMMIT_AT + timedelta(hours=1)


def committed_v2():
    return commit_research_package(v2_package()).research_snapshot


def evidence_id(snapshot):
    return snapshot.evidence_links[0].evidence_artifact_id


def declared_world(snapshot, *, name="base", terminal="10", flow=None, **changes):
    wid = changes.pop("id", uuid4())
    data = dict(
        id=wid,
        name=name,
        terminal_equity_value_per_share=Decimal(terminal),
        operating_conditions=("SYNTHETIC operating condition; not probability",),
        valuation_expression="SYNTHETIC terminal value assumption for contract testing",
        provenance_artifact_ids=(evidence_id(snapshot),),
        expected_distributions=(),
    )
    if flow is not None:
        data["expected_distributions"] = (
            ConditionalExpectedDistribution(
                id=uuid4(),
                world_id=wid,
                cash_flow_date=flow["date"],
                amount_per_share=Decimal(flow["amount"]),
                currency=snapshot.currency,
                cash_flow_type=flow["type"],
                provenance_artifact_ids=(evidence_id(snapshot),),
            ),
        )
    data.update(changes)
    return DeclaredConditionalWorld(**data)


def world_set(snapshot=None, *, worlds=None, horizon_days=1095, created_at=AFTER_COMMIT):
    snapshot = snapshot or committed_v2()
    worlds = worlds or (
        declared_world(snapshot, name="downside", terminal="8"),
        declared_world(snapshot, name="middle", terminal="10"),
        declared_world(snapshot, name="upside", terminal="14"),
    )
    return build_conditional_world_set(
        research_snapshot=snapshot,
        worlds=worlds,
        valuation_horizon_date=AS_OF.date() + timedelta(days=horizon_days),
        world_set_id=uuid4(),
        created_at=created_at,
    )


def context(snapshot=None, *, price="10", price_timestamp=None, supplied_at=None, **changes):
    snapshot = snapshot or committed_v2()
    price_timestamp = price_timestamp or AS_OF + timedelta(hours=2)
    supplied_at = supplied_at or COMMIT_AT + timedelta(hours=2)
    data = dict(
        ticker=snapshot.ticker,
        exchange=snapshot.exchange,
        currency=snapshot.currency,
        price=price,
        price_timestamp=price_timestamp,
        utc_offset_minutes=480,
        supplied_at=supplied_at,
        source_reference="SYNTHETIC Human context price; not a market qualification",
        price_convention=CONVENTION,
    )
    data.update(changes)
    return HumanPriceContext(**data)


def result(snapshot=None, *, worlds=None, ctx=None, created_at=None):
    snapshot = snapshot or committed_v2()
    worlds = worlds or world_set(snapshot)
    ctx = ctx or context(snapshot)
    created_at = created_at or COMMIT_AT + timedelta(hours=3)
    return build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=worlds,
        price_context=ctx,
        artifact_id=uuid4(),
        created_at=created_at,
    )


def all_keys(value):
    if isinstance(value, dict):
        return set(value).union(*(all_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(all_keys(item) for item in value))
    return set()


def test_research_only_v2_can_gain_declared_worlds_without_probability_or_rewriting_research():
    snapshot = committed_v2()
    before = canonical_json(snapshot)
    frozen = world_set(snapshot)
    outcome = result(snapshot, worlds=frozen)

    assert snapshot.scenarios == () and snapshot.valuation_horizon_date is None
    assert frozen.world_set.probability_status == "NOT_ESTABLISHED"
    assert outcome.artifact.calculation_status is CalculationStatus.CALCULATED
    assert outcome.artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert outcome.artifact.probability_input == "ABSENT_BY_DESIGN"
    assert outcome.artifact.weighted_aggregate == "NOT_COMPUTED"
    assert outcome.artifact.odds_status == "PROVISIONAL_CONDITIONAL_ORDINAL"
    assert outcome.artifact.investment_authority == "NONE"
    assert canonical_json(snapshot) == before
    payload = json.loads(outcome.model_dump_json())
    keys = all_keys(payload)
    assert "probability" not in keys and "aggregate" not in keys


@pytest.mark.parametrize(
    "price,expected",
    [
        ("5", "ALL_DECLARED_WORLDS_POSITIVE"),
        ("10", "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"),
        ("20", "ALL_DECLARED_WORLDS_NEGATIVE"),
    ],
)
def test_declared_world_sign_pattern_has_no_probability_or_recommendation(price, expected):
    snapshot = committed_v2()
    outcome = result(snapshot, ctx=context(snapshot, price=price))
    assert outcome.artifact.ordinal_status == expected
    assert "SIGN_PATTERN_NOT_ODDS_JUDGMENT_OR_RECOMMENDATION" in outcome.artifact.limitations
    assert outcome.artifact.canonical_odds == "NOT_ESTABLISHED"


def test_three_year_horizon_is_allowed_without_changing_canonical_policy():
    snapshot = committed_v2()
    frozen = world_set(snapshot, horizon_days=1095)
    outcome = result(snapshot, worlds=frozen)
    assert frozen.world_set.valuation_horizon_date == AS_OF.date() + timedelta(days=1095)
    assert outcome.artifact.calculation_status is CalculationStatus.CALCULATED
    assert outcome.artifact.calculation_engine_version == "phase2a-valuation-odds-v1"
    assert "UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_NOT_ANNUALIZED" in outcome.artifact.limitations


def test_historical_reference_price_before_research_cutoff_is_explicitly_retrospective():
    snapshot = committed_v2()
    human = context(
        snapshot,
        price_timestamp=AS_OF - timedelta(days=1),
        supplied_at=COMMIT_AT + timedelta(hours=2),
    )
    outcome = result(snapshot, ctx=human)
    assert outcome.artifact.price_clock_semantics == "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT"
    assert (
        "RETROSPECTIVE_REFERENCE_PRICE_USES_LATER_FROZEN_RESEARCH_NOT_PIT_ANALYSIS"
        in outcome.artifact.limitations
    )
    assert outcome.artifact.market_qualification == "NOT_ESTABLISHED"


def test_post_cutoff_human_price_stays_context_only():
    snapshot = committed_v2()
    outcome = result(snapshot)
    assert outcome.artifact.price_clock_semantics == "AT_OR_AFTER_RESEARCH_CUTOFF_CONTEXT_ONLY"
    assert outcome.artifact.price_context.authority == "CONTEXT_ONLY"
    assert outcome.artifact.price_context.qualified_market_observation is False
    assert outcome.artifact.price_context.canonical_market_state is False


def test_probability_field_is_forbidden_on_declared_world():
    snapshot = committed_v2()
    payload = declared_world(snapshot).model_dump(mode="python")
    payload["probability"] = Decimal("0.5")
    with pytest.raises(ValidationError):
        DeclaredConditionalWorld.model_validate(payload)


def test_existing_canonical_scenario_still_requires_probability():
    package = _generic_package()
    payload = package.research_snapshot.scenarios[0].model_dump(mode="python")
    payload.pop("probability")
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


def test_probability_bearing_legacy_research_has_identical_per_world_arithmetic():
    snapshot = commit_research_package(_generic_package()).research_snapshot
    worlds = []
    for scenario in snapshot.scenarios:
        distributions = tuple(
            ConditionalExpectedDistribution(
                id=flow.id,
                world_id=scenario.id,
                cash_flow_date=flow.cash_flow_date,
                amount_per_share=flow.amount,
                currency=flow.currency,
                cash_flow_type=flow.cash_flow_type,
                provenance_artifact_ids=flow.provenance_artifact_ids,
            )
            for flow in scenario.expected_cash_flows
        )
        worlds.append(
            DeclaredConditionalWorld(
                id=scenario.id,
                name=scenario.name,
                terminal_equity_value_per_share=scenario.terminal_equity_value_per_share,
                operating_conditions=("SYNTHETIC parity projection of existing Scenario",),
                valuation_expression="SYNTHETIC parity projection",
                provenance_artifact_ids=(evidence_id(snapshot),),
                expected_distributions=distributions,
                valuation_basis_id=scenario.valuation_basis_id,
            )
        )
    frozen = build_conditional_world_set(
        research_snapshot=snapshot,
        worlds=tuple(worlds),
        valuation_horizon_date=snapshot.valuation_horizon_date,
        world_set_id=uuid4(),
        created_at=COMMIT_AT + timedelta(minutes=1),
    )
    human = context(
        snapshot,
        price="10",
        price_timestamp=AS_OF + timedelta(hours=2),
        supplied_at=AS_OF + timedelta(hours=3),
    )
    actual = build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=frozen,
        price_context=human,
        artifact_id=uuid4(),
        created_at=AS_OF + timedelta(hours=4),
    )
    market = ObservedMarket(
        market_price="10",
        market_timestamp=AS_OF + timedelta(hours=2),
        market_utc_offset_minutes=480,
        market_data_source="SYNTHETIC separately qualified fixture",
        price_convention=CONVENTION,
        currency=snapshot.currency,
    )
    original = calculate_research_economics(
        snapshot, market, created_at=AS_OF + timedelta(hours=4)
    )
    before = {
        item.scenario_id: item.model_dump(mode="python", exclude={"probability"})
        for item in original.scenario_results
    }
    after = {
        item.world_id: {
            "scenario_id": item.world_id,
            "scenario_name": item.world_name,
            "terminal_equity_value_per_share": item.terminal_equity_value_per_share,
            "expected_distributions": tuple(
                distribution.model_dump(mode="python")
                for distribution in item.expected_distributions
            ),
            "total_expected_distributions_per_share": item.total_expected_distributions_per_share,
            "total_payoff_per_share": item.total_payoff_per_share,
            "undiscounted_holding_period_return": item.undiscounted_holding_period_return,
        }
        for item in actual.artifact.world_results
    }
    assert after == before


@pytest.mark.parametrize("field,value", [
    ("ticker", "600001"),
    ("exchange", "SZSE"),
    ("currency", "USD"),
])
def test_price_identity_must_match_frozen_research(field, value):
    snapshot = committed_v2()
    with pytest.raises(DomainValidationError):
        result(snapshot, ctx=context(snapshot, **{field: value}))


def test_observed_market_cannot_be_substituted_for_human_context():
    snapshot = committed_v2()
    market = ObservedMarket(
        market_price="10",
        market_timestamp=AS_OF + timedelta(hours=2),
        market_utc_offset_minutes=480,
        market_data_source="SYNTHETIC market",
        price_convention=CONVENTION,
        currency=snapshot.currency,
    )
    with pytest.raises(DomainValidationError, match="HumanPriceContext"):
        build_conditional_provisional_odds(
            research_snapshot=snapshot,
            conditional_worlds=world_set(snapshot),
            price_context=market,
            artifact_id=uuid4(),
            created_at=COMMIT_AT + timedelta(hours=3),
        )


def test_world_evidence_must_belong_to_exact_research():
    snapshot = committed_v2()
    bad = declared_world(
        snapshot,
        provenance_artifact_ids=(uuid4(),),
    )
    with pytest.raises(DomainValidationError, match="Evidence outside frozen Research"):
        world_set(snapshot, worlds=(bad,))


def test_distribution_evidence_must_belong_to_exact_research():
    snapshot = committed_v2()
    wid = uuid4()
    bad = DeclaredConditionalWorld(
        id=wid,
        name="bad-flow",
        terminal_equity_value_per_share=Decimal("10"),
        operating_conditions=("SYNTHETIC",),
        valuation_expression="SYNTHETIC",
        provenance_artifact_ids=(evidence_id(snapshot),),
        expected_distributions=(
            ConditionalExpectedDistribution(
                id=uuid4(),
                world_id=wid,
                cash_flow_date=AS_OF.date() + timedelta(days=100),
                amount_per_share=Decimal("1"),
                currency=snapshot.currency,
                cash_flow_type="DIVIDEND",
                provenance_artifact_ids=(uuid4(),),
            ),
        ),
    )
    with pytest.raises(DomainValidationError, match="distribution cites Evidence"):
        world_set(snapshot, worlds=(bad,))


def test_world_set_rejects_silent_horizon_change_when_research_already_has_one():
    snapshot = commit_research_package(_generic_package()).research_snapshot
    with pytest.raises(DomainValidationError, match="horizon cannot be silently replaced"):
        build_conditional_world_set(
            research_snapshot=snapshot,
            worlds=(declared_world(snapshot),),
            valuation_horizon_date=snapshot.valuation_horizon_date + timedelta(days=1),
            world_set_id=uuid4(),
            created_at=COMMIT_AT + timedelta(minutes=1),
        )


def test_world_set_rejects_pre_commit_creation():
    snapshot = committed_v2()
    with pytest.raises(DomainValidationError, match="cannot precede Research commit"):
        world_set(snapshot, created_at=COMMIT_AT - timedelta(seconds=1))


def test_expired_horizon_returns_no_calculation_not_fake_zero():
    snapshot = committed_v2()
    frozen = world_set(snapshot, horizon_days=30)
    human = context(
        snapshot,
        price_timestamp=AS_OF + timedelta(days=40),
        supplied_at=AS_OF + timedelta(days=40, hours=1),
    )
    outcome = result(
        snapshot,
        worlds=frozen,
        ctx=human,
        created_at=AS_OF + timedelta(days=40, hours=2),
    )
    assert outcome.artifact.calculation_status is CalculationStatus.NO_CALCULATION
    assert outcome.artifact.ordinal_status == "ORDINAL_NOT_ESTABLISHED"
    assert not outcome.artifact.world_results
    assert {failure.location for failure in outcome.artifact.failures} == {"valuation_horizon_date"}


def test_past_distribution_returns_no_calculation_without_dropping_cash_flow():
    snapshot = committed_v2()
    world = declared_world(
        snapshot,
        flow={
            "date": AS_OF.date() + timedelta(days=10),
            "amount": "1.25",
            "type": "DIVIDEND",
        },
    )
    frozen = world_set(snapshot, worlds=(world,))
    human = context(
        snapshot,
        price_timestamp=AS_OF + timedelta(days=20),
        supplied_at=AS_OF + timedelta(days=20, hours=1),
    )
    outcome = result(
        snapshot,
        worlds=frozen,
        ctx=human,
        created_at=AS_OF + timedelta(days=20, hours=2),
    )
    assert outcome.artifact.calculation_status is CalculationStatus.NO_CALCULATION
    assert len(outcome.artifact.failures) == 1
    assert outcome.artifact.conditional_worlds.world_set.worlds[0].expected_distributions[0].amount_per_share == Decimal("1.25")


def test_world_set_verifier_rejects_different_research_even_with_same_security():
    snapshot = committed_v2()
    frozen = world_set(snapshot)
    changed = snapshot.model_copy(update={"core_thesis": "SYNTHETIC changed thesis"})
    with pytest.raises(DomainValidationError, match="REUNDERWRITE_REQUIRED"):
        verify_conditional_world_set(frozen, changed)


def test_result_verifier_rebuilds_and_rejects_rehashed_return_edit():
    snapshot = committed_v2()
    original = result(snapshot)
    assert verify_conditional_provisional_odds(original, snapshot) == original
    payload = original.model_dump(mode="python")
    payload["artifact"]["world_results"][0]["total_payoff_per_share"] = Decimal("999")
    payload["artifact_hash"] = canonical_hash(payload["artifact"])
    forged = FrozenConditionalProvisionalOdds.model_validate(payload)
    with pytest.raises(DomainValidationError, match="deterministic reconstruction"):
        verify_conditional_provisional_odds(forged, snapshot)


def test_world_set_hash_rejects_unrehashable_edit():
    snapshot = committed_v2()
    original = world_set(snapshot)
    payload = original.model_dump(mode="python")
    payload["world_set"]["worlds"][0]["terminal_equity_value_per_share"] = Decimal("999")
    with pytest.raises(ValueError, match="hash must cover"):
        FrozenConditionalWorldSet.model_validate(payload)


@pytest.mark.parametrize("field,value", [
    ("odds_status", "CANONICAL"),
    ("cardinal_probability", "CALIBRATED"),
    ("market_qualification", "QUALIFIED"),
    ("canonical_odds", "ESTABLISHED"),
    ("investment_authority", "BUY"),
    ("research_reexecuted", True),
])
def test_result_wire_rejects_authority_smuggling(field, value):
    snapshot = committed_v2()
    original = result(snapshot)
    payload = original.model_dump(mode="python")
    payload["artifact"][field] = value
    payload["artifact_hash"] = canonical_hash(payload["artifact"])
    with pytest.raises(ValidationError):
        FrozenConditionalProvisionalOdds.model_validate(payload)
