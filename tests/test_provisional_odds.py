"""Synthetic engineering contracts, never a real-company Odds acceptance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

from pydantic import ValidationError
import pytest

from decision_kernel.calculation import CALCULATION_CONTEXT, CalculationStatus, calculate_research_economics
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import build_odds_research
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.primitives import DomainValidationError
from decision_kernel.provisional_odds import (
    HumanPriceContext, FrozenProvisionalOdds, SameResearchOddsComparison,
    build_provisional_odds, verify_provisional_odds, recompute_canonical_odds,
    verify_same_research_comparison,
)
from decision_kernel.research import CashFlowBasis, CashFlowType, ExpectedCashFlow, ResearchStatus
from decision_kernel.research_commit import commit_research_package, research_commit_information_bundle_hash
from decision_kernel.runtime import research_commit_only as retained
from test_generic_research_commit import AS_OF, _generic_package
from test_research_only_commit_v2 import v2_package

CREATED = AS_OF + timedelta(hours=4)
CONVENTION = "RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("provisional/recompute contract must not use network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def snapshot():
    return commit_research_package(_generic_package()).research_snapshot


def context(price="10", **changes):
    data = dict(ticker="600000", exchange="SSE", currency="CNY", price=price,
                price_timestamp=AS_OF + timedelta(hours=2), utc_offset_minutes=480,
                supplied_at=AS_OF + timedelta(hours=3),
                source_reference="SYNTHETIC Human-price fixture, not an actual Human instruction",
                price_convention=CONVENTION)
    data.update(changes)
    return HumanPriceContext(**data)


def market(price="8", **changes):
    data = dict(market_price=price, market_timestamp=AS_OF + timedelta(hours=2),
                market_utc_offset_minutes=480, currency="CNY", price_convention=CONVENTION,
                market_data_source="SYNTHETIC separately supplied market; not live qualification")
    data.update(changes)
    return ObservedMarket(**data)


def provisional(s=None, p=None, **changes):
    return build_provisional_odds(research_snapshot=s if s is not None else snapshot(),
                                 price_context=p if p is not None else context(),
                                 artifact_id=changes.pop("artifact_id", uuid4()),
                                 created_at=changes.pop("created_at", CREATED), **changes)


def compare(prior, s, m=None, **changes):
    kwargs = dict(provisional=prior, research_snapshot=s, observed_market=m or market(),
                  market_ticker="600000", market_exchange="SSE", artifact_id=uuid4(),
                  created_at=CREATED + timedelta(hours=1), policy=load_live_odds_v0_1())
    kwargs.update(changes)
    return recompute_canonical_odds(**kwargs)


def rehash(package):
    s = package.research_snapshot
    return package.model_copy(update={"research_snapshot": s.model_copy(update={
        "information_bundle_hash": research_commit_information_bundle_hash(
            research_snapshot=s, evidence_artifacts=package.evidence_artifacts)})})


def all_keys(value):
    if isinstance(value, dict):
        return set(value).union(*(all_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(all_keys(v) for v in value))
    return set()


def test_first_class_provisional_roundtrip_uses_existing_world_arithmetic_without_probability():
    s = snapshot()
    before = canonical_json(s)
    p = provisional(s)
    original = calculate_research_economics(s, market("10"), created_at=CREATED)
    assert p.artifact.calculation_status is CalculationStatus.CALCULATED
    assert [w.model_dump() for w in p.artifact.world_results] == [
        w.model_dump(exclude={"probability"}) for w in original.scenario_results]
    assert p.artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert p.artifact.odds_status == "PROVISIONAL" and p.artifact.investment_authority == "NONE"
    assert not ({"probability", "aggregate", "positive_return_probability",
                 "expected_holding_period_return", "participation_zone", "observed_market"}
                & all_keys(json.loads(p.model_dump_json())))
    loaded = FrozenProvisionalOdds.model_validate_json(p.model_dump_json())
    assert verify_provisional_odds(loaded, s) == p and canonical_json(s) == before


@pytest.mark.parametrize("price,pattern", [
    ("5", "ALL_DECLARED_WORLDS_POSITIVE"),
    ("10", "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"),
    ("20", "ALL_DECLARED_WORLDS_NEGATIVE"),
    ("8", "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"),
    ("15", "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"),
])
def test_sign_patterns_are_not_recommendations_or_world_probabilities(price, pattern):
    p = provisional(p=context(price))
    assert p.artifact.ordinal_status == pattern
    assert "SIGN_PATTERN_NOT_ODDS_JUDGMENT_OR_RECOMMENDATION" in p.artifact.limitations


def test_exact_break_even_has_its_own_sign_pattern():
    package = _generic_package()
    s = package.research_snapshot
    s = s.model_copy(update={"scenarios": tuple(w.model_copy(update={
        "terminal_equity_value_per_share": Decimal("10")}) for w in s.scenarios)})
    s = commit_research_package(rehash(package.model_copy(update={"research_snapshot": s}))).research_snapshot
    assert provisional(s).artifact.ordinal_status == "ALL_DECLARED_WORLDS_BREAK_EVEN"


@pytest.mark.parametrize("field,value", [
    ("price", "0"), ("price", "-1"), ("price", "NaN"), ("price", "Infinity"),
    ("price", 10.0), ("price", "0.0000000000000000001"),
    ("price", "100000000000000000000"),
    ("price_timestamp", datetime(2026, 9, 1)), ("supplied_at", AS_OF),
    ("utc_offset_minutes", 841), ("utc_offset_minutes", True),
    ("source", "QUALIFIED"), ("authority", "CANONICAL"),
    ("qualified_market_observation", True), ("canonical_market_state", True),
    ("source_reference", "  "), ("price_convention", ""), ("schema_version", 2),
    ("ticker", " "), ("exchange", " "),
])
def test_bad_or_authority_smuggling_human_inputs_are_rejected(field, value):
    with pytest.raises(ValueError):
        context(**{field: value})


@pytest.mark.parametrize("field,value", [
    ("ticker", "600001"), ("exchange", "SZSE"), ("currency", "USD"),
    ("price_timestamp", AS_OF - timedelta(seconds=1)),
])
def test_context_must_match_research_and_cutoff(field, value):
    with pytest.raises(DomainValidationError):
        provisional(p=context(**{field: value}))


@pytest.mark.parametrize("at", [AS_OF, datetime(2026, 9, 1)])
def test_invalid_provisional_creation_clock_is_rejected(at):
    with pytest.raises(DomainValidationError):
        provisional(created_at=at)


def test_model_copy_does_not_bypass_input_checks():
    with pytest.raises(ValueError):
        provisional(p=context().model_copy(update={"price": Decimal("-1")}))
    with pytest.raises(ValueError):
        provisional(p=context().model_copy(update={"authority": "CANONICAL"}))
    s = snapshot()
    with pytest.raises(ValueError):
        provisional(s.model_copy(update={"committed_at": AS_OF - timedelta(days=1)}))
    with pytest.raises(ValueError):
        provisional(s.model_copy(update={"status": ResearchStatus.REVIEW, "committed_at": None}))


def test_human_context_has_no_implicit_conversion_to_observed_market():
    c = context()
    with pytest.raises(ValueError):
        ObservedMarket.model_validate(c.model_dump())
    with pytest.raises(ValueError):
        HumanPriceContext.model_validate(market().model_dump())
    with pytest.raises(DomainValidationError):
        provisional(p=market())
    s = snapshot()
    with pytest.raises(DomainValidationError):
        compare(provisional(s), s, c)
    with pytest.raises(DomainValidationError):
        compare(provisional(s), s, market(market_data_source="HUMAN_SUPPLIED_PROVISIONAL_PRICE"))


def test_research_only_commit_is_retained_without_fake_numerical_state(tmp_path):
    package = v2_package()
    source = tmp_path / "input.json"
    source.write_text(package.model_dump_json(), encoding="utf-8")
    output = tmp_path / "retained"
    s = retained.commit_research_file(source, output=output).research_snapshot
    before = {f.name: f.read_bytes() for f in output.iterdir()}
    p = provisional(s)
    assert p.artifact.calculation_status is CalculationStatus.NO_CALCULATION
    assert p.artifact.ordinal_status == "ORDINAL_NOT_ESTABLISHED"
    assert p.artifact.world_results == () and p.artifact.valuation_horizon_date is None
    assert {f.location for f in p.artifact.failures} == {"valuation_horizon_date", "research_snapshot.scenarios"}
    assert verify_provisional_odds(p, s) == p
    with pytest.raises(DomainValidationError):
        compare(p, s)
    assert {f.name: f.read_bytes() for f in output.iterdir()} == before
    assert retained.read_retained_commit(output).research_snapshot == s


def with_flow(**changes):
    package = _generic_package()
    s = package.research_snapshot
    w = s.scenarios[0]
    values = dict(id=uuid4(), scenario_id=w.id, cash_flow_date=AS_OF.date() + timedelta(days=10),
                  amount=Decimal("1.25"), basis=CashFlowBasis.PER_SHARE, currency="CNY",
                  cash_flow_type=CashFlowType.DIVIDEND,
                  provenance_artifact_ids=(package.evidence_artifacts[0].id,))
    values.update(changes)
    flow = ExpectedCashFlow(**values)
    s = s.model_copy(update={"scenarios": (w.model_copy(update={"expected_cash_flows": (flow,)}),
                                           *s.scenarios[1:])})
    return commit_research_package(rehash(package.model_copy(update={"research_snapshot": s}))).research_snapshot


def test_existing_dated_cashflow_arithmetic_is_used_without_new_rounding():
    s = with_flow()
    p = provisional(s)
    result = calculate_research_economics(s, market("10"), created_at=CREATED)
    assert [w.model_dump() for w in p.artifact.world_results] == [
        w.model_dump(exclude={"probability"}) for w in result.scenario_results]
    assert any(w.expected_distributions for w in p.artifact.world_results)


@pytest.mark.parametrize("changes,code", [
    ({"basis": CashFlowBasis.TOTAL_EQUITY}, "TOTAL_EQUITY_UNSUPPORTED"),
    ({"currency": "USD"}, "FX_CONVERSION_REQUIRED"),
    ({"cash_flow_date": AS_OF.date()}, "UNSUPPORTED_CALCULATION_INPUT"),
])
def test_unsupported_cashflows_match_existing_engine_fail_closed(changes, code):
    s = with_flow(**changes)
    p = provisional(s)
    canonical_attempt = calculate_research_economics(s, market("10"), created_at=CREATED)
    assert p.artifact.calculation_status is canonical_attempt.status is CalculationStatus.NO_CALCULATION
    assert {f.code.value for f in p.artifact.failures} == {f.code.value for f in canonical_attempt.failures} == {code}
    assert p.artifact.world_results == ()


def test_expired_horizon_is_not_rolled_forward_to_manufacture_odds():
    s = snapshot()
    at = datetime.combine(s.valuation_horizon_date, datetime.min.time(), tzinfo=timezone.utc)
    p = provisional(s, context(price_timestamp=at, supplied_at=at), created_at=at)
    assert p.artifact.calculation_status is CalculationStatus.NO_CALCULATION
    assert p.artifact.valuation_horizon_date == s.valuation_horizon_date
    assert s.valuation_horizon_date == at.date()


def test_canonical_comparison_calls_original_builder_with_identical_hash():
    s = snapshot()
    p = provisional(s)
    m = market()
    artifact_id = uuid4()
    at = CREATED + timedelta(hours=1)
    result = compare(p, s, m, artifact_id=artifact_id, created_at=at)
    expected = build_odds_research(artifact_id=artifact_id, created_at=at, research_snapshot=s,
                                  observed_market=m, policy=load_live_odds_v0_1())
    assert result.canonical == expected
    assert result.price_change == Decimal("-2")
    assert result.provisional == p and result.provisional.artifact.price_context.authority == "CONTEXT_ONLY"
    assert result.provisional.artifact.market_qualification == "NOT_ESTABLISHED"
    assert result.research_reexecuted is False and result.investment_authority == "NONE"
    assert SameResearchOddsComparison.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("field,value", [
    ("core_thesis", "SYNTHETIC different interpretation"),
    ("information_bundle_hash", "e" * 64),
    ("research_engine_version", "different-method"),
    ("model_risk_notes", "different model risk"),
    ("created_by", "other-researcher"),
    ("monitoring_triggers", ("new evidence trigger",)),
])
def test_same_id_is_insufficient_full_research_change_blocks_before_canonical_builder(monkeypatch, field, value):
    import decision_kernel.provisional_odds as adapter
    s = snapshot()
    p = provisional(s)
    def denied(**kwargs):
        raise AssertionError("changed Research must not reach canonical arithmetic")
    monkeypatch.setattr(adapter, "build_odds_research", denied)
    with pytest.raises(DomainValidationError, match="REUNDERWRITE_REQUIRED"):
        compare(p, s.model_copy(update={field: value}))


def test_changed_world_probabilities_cannot_be_mislabelled_price_only():
    s = snapshot()
    p = provisional(s)
    changed = s.model_copy(update={"scenarios": tuple(w.model_copy(update={"probability": prob})
        for w, prob in zip(s.scenarios, (Decimal("0.7"), Decimal("0.3")), strict=True))})
    with pytest.raises(DomainValidationError, match="REUNDERWRITE_REQUIRED"):
        compare(p, changed)


def test_invalid_supplied_probability_state_is_not_erased_or_defaulted():
    s = snapshot()
    changed = s.model_copy(update={"scenarios": tuple(w.model_copy(update={"probability": Decimal("0")})
                                                     for w in s.scenarios)})
    with pytest.raises(DomainValidationError):
        provisional(changed)


@pytest.mark.parametrize("changes", [
    {"market_ticker": "600001"}, {"market_exchange": "SZSE"},
    {"observed_market": market(currency="USD")},
    {"observed_market": market(price_convention="QFQ")},
    {"observed_market": market(market_utc_offset_minutes=0)},
    {"observed_market": market(market_timestamp=AS_OF)},
    {"created_at": CREATED - timedelta(seconds=1)},
    {"created_at": datetime(2026, 9, 1)},
])
def test_canonical_comparison_rejects_incompatible_identity_and_clocks(changes):
    s = snapshot()
    p = provisional(s)
    with pytest.raises(DomainValidationError):
        compare(p, s, **changes)


def test_market_failure_and_passed_cashflows_preserve_original_research_and_provisional():
    s = with_flow()
    p = provisional(s)
    before = (canonical_json(s), canonical_json(p))
    at = CREATED + timedelta(days=20)
    with pytest.raises(DomainValidationError):
        compare(p, s, market(market_timestamp=at), created_at=at)
    assert (canonical_json(s), canonical_json(p)) == before


def test_rehashed_wrong_world_arithmetic_is_rejected_by_rebuild():
    s = snapshot()
    p = provisional(s)
    payload = p.model_dump(mode="python")
    payload["artifact"]["world_results"][0]["total_payoff_per_share"] = Decimal("999")
    payload["artifact_hash"] = canonical_hash(payload["artifact"])
    forged = FrozenProvisionalOdds.model_validate(payload)
    with pytest.raises(DomainValidationError, match="deterministic recomputation"):
        verify_provisional_odds(forged, s)
    with pytest.raises(DomainValidationError):
        compare(forged, s)


@pytest.mark.parametrize("field,value", [
    ("odds_status", "CANONICAL"), ("cardinal_probability", "CALIBRATED"),
    ("market_qualification", "QUALIFIED"), ("human_acceptance", "ACCEPTED"),
    ("investment_authority", "BUY"), ("research_reexecuted", True),
    ("schema_version", 2), ("ordinal_status", "FAVORABLE"), ("aggregate", {}),
    ("limitations", ()),
])
def test_result_wire_rejects_authority_and_unknown_fields(field, value):
    p = provisional()
    payload = p.model_dump(mode="python")
    payload["artifact"][field] = value
    payload["artifact_hash"] = canonical_hash(payload["artifact"])
    with pytest.raises(ValueError):
        FrozenProvisionalOdds.model_validate(payload)


def test_comparison_wire_does_not_allow_different_price_delta_or_authority():
    s = snapshot()
    result = compare(provisional(s), s)
    for field, value in (("price_change", Decimal("0")), ("investment_authority", "BUY"),
                         ("route", "NEW_BELIEF"), ("research_reexecuted", True)):
        with pytest.raises(ValueError):
            SameResearchOddsComparison.model_validate({**result.model_dump(mode="python"), field: value})


def test_module_import_never_requests_optional_provider_or_model_dependencies():
    code = '''
import builtins, socket, sys
sys.path.insert(0, sys.argv[1])

def denied(*a, **k):
    raise AssertionError("no network")
socket.create_connection = denied
socket.socket.connect = denied
original_import = builtins.__import__
def guarded(name, *a, **k):
    if name.split(".")[0] in {"openai", "requests"} or name.startswith((
        "decision_kernel.runtime.hithink_http", "decision_kernel.live")):
        raise AssertionError("optional provider/model import: " + name)
    return original_import(name, *a, **k)
builtins.__import__ = guarded
import decision_kernel.provisional_odds
'''
    subprocess.run([sys.executable, "-I", "-c", code, str(Path(__file__).resolve().parents[1] / "src")],
                   check=True, timeout=15)


def test_comparison_verifier_rebuilds_both_sides_and_rejects_rehashed_probability_edit():
    s = snapshot()
    result = compare(provisional(s), s)
    assert verify_same_research_comparison(result, s) == result
    payload = result.model_dump(mode="python")
    # Keep summary and shape internally consistent, change only a non-driving
    # serialized detail; a checksum alone cannot prove original computation.
    artifact = payload["canonical"]["artifact"]
    artifact["calculation"]["scenario_results"][0]["probability"] = Decimal("0.123")
    payload["canonical"]["artifact_hash"] = canonical_hash(artifact)
    forged = SameResearchOddsComparison.model_validate(payload)
    with pytest.raises(DomainValidationError, match="original canonical recomputation"):
        verify_same_research_comparison(forged, s)


def test_comparison_wire_rejects_rehashed_payoff_or_source_relabel():
    s = snapshot()
    result = compare(provisional(s), s)
    for damage in ("payoff", "source"):
        payload = result.model_dump(mode="python")
        c = payload["canonical"]["artifact"]
        if damage == "payoff":
            c["calculation"]["scenario_results"][0]["total_payoff_per_share"] = Decimal("999")
        else:
            c["observed_market"]["market_data_source"] = "HUMAN_SUPPLIED_PROVISIONAL_PRICE"
        payload["canonical"]["artifact_hash"] = canonical_hash(c)
        with pytest.raises(ValueError):
            SameResearchOddsComparison.model_validate(payload)


@pytest.mark.parametrize("field,value,code", [
    ("currency", "USD", "FX_CONVERSION_REQUIRED"),
    ("as_of_datetime", AS_OF + timedelta(seconds=1), "PIT_VIOLATION"),
])
def test_valuation_basis_consistency_agrees_with_existing_numerical_engine(field, value, code):
    s = snapshot()
    s = s.model_copy(update={"valuation_bases": tuple(b.model_copy(update={field: value})
                                                     for b in s.valuation_bases)})
    p = provisional(s)
    original = calculate_research_economics(s, market("10"), created_at=CREATED)
    assert p.artifact.calculation_status is original.status is CalculationStatus.NO_CALCULATION
    assert {f.code.value for f in p.artifact.failures} == {f.code.value for f in original.failures} == {code}


def test_price_can_change_without_changing_research_or_declared_payoffs():
    s = snapshot()
    research_before = canonical_json(s)
    old = provisional(s, context("10"))
    new = provisional(s, context("9"))
    assert old.artifact.research_snapshot_hash == new.artifact.research_snapshot_hash
    assert old.artifact_hash != new.artifact_hash
    assert [w.total_payoff_per_share for w in old.artifact.world_results] == [
        w.total_payoff_per_share for w in new.artifact.world_results]
    assert canonical_json(s) == research_before


def test_low_ambient_decimal_precision_does_not_change_price_or_return_arithmetic():
    s = snapshot()
    human = context("10.123456789012345678")
    ident = uuid4()
    expected = provisional(s, human, artifact_id=ident)
    with localcontext() as ctx:
        ctx.prec = 6
        actual = provisional(s, human, artifact_id=ident)
    assert actual == expected


@pytest.mark.parametrize("field,value", [("schema_version", True), ("schema_version", "1"),
                                         ("qualified_market_observation", 0), ("canonical_market_state", 0)])
def test_price_boundary_literals_are_not_coerced_from_different_types(field, value):
    with pytest.raises(ValueError):
        context(**{field: value})


def test_result_boundary_literals_are_not_coerced_from_different_types():
    p = provisional()
    for field, value in (("schema_version", True), ("research_reexecuted", 0)):
        payload = p.model_dump(mode="python")
        payload["artifact"][field] = value
        payload["artifact_hash"] = canonical_hash(payload["artifact"])
        with pytest.raises(ValueError):
            FrozenProvisionalOdds.model_validate(payload)
