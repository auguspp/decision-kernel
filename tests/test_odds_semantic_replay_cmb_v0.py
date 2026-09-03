from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import pow
from pathlib import Path

from decision_kernel.market import ObservedMarket
from decision_kernel.odds import (
    AdjustedParticipationThresholds,
    ParticipationZone,
    build_odds_research,
    classify_participation_zone,
)
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    commit_research_package,
)


CMB_PACKAGE = Path("dogfood/600036-cmb.json")
MARKET_PRICE = Decimal("40.86")
MARKET_AT = datetime(
    2026,
    9,
    1,
    15,
    0,
    tzinfo=timezone(timedelta(hours=8)),
)
CREATED_AT = datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc)
ZONE_ORDER = (
    ParticipationZone.EXCEPTIONAL_ODDS,
    ParticipationZone.ATTRACTIVE_ODDS,
    ParticipationZone.ACCEPTABLE_ODDS,
)


def _load_real_cmb_odds():
    package = ResearchCommitPackage.model_validate_json(
        CMB_PACKAGE.read_text(encoding="utf-8")
    )
    committed = commit_research_package(package).research_snapshot
    market = ObservedMarket(
        market_price=MARKET_PRICE,
        market_timestamp=MARKET_AT,
        market_utc_offset_minutes=480,
        market_data_source="HiThink fixture",
        price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
        currency="CNY",
    )
    odds = build_odds_research(
        artifact_id=committed.id,
        created_at=CREATED_AT,
        research_snapshot=committed,
        observed_market=market,
        policy=load_live_odds_v0_1(),
    ).artifact
    return odds


def _annualized(cumulative_return: Decimal, holding_days: int) -> Decimal:
    return Decimal(
        str(pow(1.0 + float(cumulative_return), 365.0 / holding_days) - 1.0)
    )


def _cumulative_from_annual(annual_return: Decimal, holding_days: int) -> Decimal:
    return Decimal(
        str(pow(1.0 + float(annual_return), holding_days / 365.0) - 1.0)
    )


def _annualized_zone(
    *,
    cumulative_return: Decimal,
    holding_days: int,
    positive_probability: Decimal,
    annual_thresholds: AdjustedParticipationThresholds,
) -> ParticipationZone:
    return classify_participation_zone(
        expected_return=_annualized(cumulative_return, holding_days),
        positive_return_probability=positive_probability,
        thresholds=annual_thresholds,
    )


def _horizon_normalized_cumulative_zone(
    *,
    cumulative_return: Decimal,
    holding_days: int,
    positive_probability: Decimal,
    annual_thresholds: AdjustedParticipationThresholds,
) -> ParticipationZone:
    normalized_thresholds = annual_thresholds.model_copy(
        update={
            "acceptable_required_return": _cumulative_from_annual(
                annual_thresholds.acceptable_required_return,
                holding_days,
            ),
            "attractive_required_return": _cumulative_from_annual(
                annual_thresholds.attractive_required_return,
                holding_days,
            ),
            "exceptional_required_return": _cumulative_from_annual(
                annual_thresholds.exceptional_required_return,
                holding_days,
            ),
        }
    )
    return classify_participation_zone(
        expected_return=cumulative_return,
        positive_return_probability=positive_probability,
        thresholds=normalized_thresholds,
    )


def _discount_rate_zone(
    *,
    weighted_terminal_payoff: Decimal,
    current_price: Decimal,
    holding_days: int,
    positive_probability: Decimal,
    annual_thresholds: AdjustedParticipationThresholds,
) -> ParticipationZone:
    threshold_by_zone = {
        ParticipationZone.ACCEPTABLE_ODDS: (
            annual_thresholds.acceptable_required_return,
            annual_thresholds.acceptable_min_positive_probability,
        ),
        ParticipationZone.ATTRACTIVE_ODDS: (
            annual_thresholds.attractive_required_return,
            annual_thresholds.attractive_min_positive_probability,
        ),
        ParticipationZone.EXCEPTIONAL_ODDS: (
            annual_thresholds.exceptional_required_return,
            annual_thresholds.exceptional_min_positive_probability,
        ),
    }
    for zone in ZONE_ORDER:
        annual_hurdle, probability_hurdle = threshold_by_zone[zone]
        discounted_payoff = weighted_terminal_payoff / Decimal(
            str(pow(1.0 + float(annual_hurdle), holding_days / 365.0))
        )
        if (
            discounted_payoff >= current_price
            and positive_probability >= probability_hurdle
        ):
            return zone
    return ParticipationZone.INSUFFICIENT_ODDS


def _nearest_anchor_bucket_zone(
    *,
    cumulative_return: Decimal,
    holding_days: int,
    positive_probability: Decimal,
    annual_thresholds: AdjustedParticipationThresholds,
) -> ParticipationZone:
    # Audit-only proxy for the generic idea of horizon buckets. The anchors and
    # nearest-anchor rule are deliberately not proposed as policy.
    anchor = min((180, 365, 730), key=lambda days: (abs(days - holding_days), days))
    return _horizon_normalized_cumulative_zone(
        cumulative_return=cumulative_return,
        holding_days=anchor,
        positive_probability=positive_probability,
        annual_thresholds=annual_thresholds,
    )


def test_real_cmb_near_one_year_is_a_semantic_convergence_control() -> None:
    odds = _load_real_cmb_odds()
    aggregate = odds.calculation.aggregate
    assert aggregate is not None

    assert odds.holding_period_days == 363
    assert odds.expected_holding_period_return == Decimal(
        "0.363191385217816935878609887"
    )
    assert odds.positive_return_probability == Decimal("0.75")
    assert aggregate.probability_weighted_total_payoff_per_share == Decimal("55.7")
    assert odds.participation_zone is ParticipationZone.ACCEPTABLE_ODDS

    annualized = _annualized_zone(
        cumulative_return=odds.expected_holding_period_return,
        holding_days=odds.holding_period_days,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )
    normalized = _horizon_normalized_cumulative_zone(
        cumulative_return=odds.expected_holding_period_return,
        holding_days=odds.holding_period_days,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )
    discounted = _discount_rate_zone(
        weighted_terminal_payoff=aggregate.probability_weighted_total_payoff_per_share,
        current_price=MARKET_PRICE,
        holding_days=odds.holding_period_days,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )
    bucketed = _nearest_anchor_bucket_zone(
        cumulative_return=odds.expected_holding_period_return,
        holding_days=odds.holding_period_days,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )

    assert {annualized, normalized, discounted, bucketed} == {
        ParticipationZone.ACCEPTABLE_ODDS
    }


def test_same_cmb_payoff_changes_economic_meaning_when_only_time_to_payoff_changes() -> None:
    odds = _load_real_cmb_odds()
    aggregate = odds.calculation.aggregate
    assert aggregate is not None

    current_policy_zones = {
        days: classify_participation_zone(
            expected_return=odds.expected_holding_period_return,
            positive_return_probability=odds.positive_return_probability,
            thresholds=odds.adjusted_thresholds,
        )
        for days in (180, 730)
    }
    annualized_zones = {
        days: _annualized_zone(
            cumulative_return=odds.expected_holding_period_return,
            holding_days=days,
            positive_probability=odds.positive_return_probability,
            annual_thresholds=odds.adjusted_thresholds,
        )
        for days in (180, 730)
    }
    normalized_zones = {
        days: _horizon_normalized_cumulative_zone(
            cumulative_return=odds.expected_holding_period_return,
            holding_days=days,
            positive_probability=odds.positive_return_probability,
            annual_thresholds=odds.adjusted_thresholds,
        )
        for days in (180, 730)
    }
    discounted_zones = {
        days: _discount_rate_zone(
            weighted_terminal_payoff=aggregate.probability_weighted_total_payoff_per_share,
            current_price=MARKET_PRICE,
            holding_days=days,
            positive_probability=odds.positive_return_probability,
            annual_thresholds=odds.adjusted_thresholds,
        )
        for days in (180, 730)
    }

    assert current_policy_zones == {
        180: ParticipationZone.ACCEPTABLE_ODDS,
        730: ParticipationZone.ACCEPTABLE_ODDS,
    }
    assert annualized_zones == {
        180: ParticipationZone.EXCEPTIONAL_ODDS,
        730: ParticipationZone.INSUFFICIENT_ODDS,
    }
    assert normalized_zones == annualized_zones
    assert discounted_zones == annualized_zones

    # Under the existing sole Human wake rule, this semantic choice alone could
    # change whether the same payoff deserves attention at a long horizon.
    assert current_policy_zones[730] is not ParticipationZone.INSUFFICIENT_ODDS
    assert annualized_zones[730] is ParticipationZone.INSUFFICIENT_ODDS


def test_cagr_and_discount_rate_are_not_independent_for_terminal_only_payoff() -> None:
    odds = _load_real_cmb_odds()
    aggregate = odds.calculation.aggregate
    assert aggregate is not None

    for days in (180, 363, 730):
        annualized = _annualized_zone(
            cumulative_return=odds.expected_holding_period_return,
            holding_days=days,
            positive_probability=odds.positive_return_probability,
            annual_thresholds=odds.adjusted_thresholds,
        )
        discounted = _discount_rate_zone(
            weighted_terminal_payoff=aggregate.probability_weighted_total_payoff_per_share,
            current_price=MARKET_PRICE,
            holding_days=days,
            positive_probability=odds.positive_return_probability,
            annual_thresholds=odds.adjusted_thresholds,
        )
        assert annualized is discounted


def test_naive_horizon_buckets_add_a_new_boundary_discontinuity() -> None:
    odds = _load_real_cmb_odds()

    zone_272 = _nearest_anchor_bucket_zone(
        cumulative_return=odds.expected_holding_period_return,
        holding_days=272,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )
    zone_273 = _nearest_anchor_bucket_zone(
        cumulative_return=odds.expected_holding_period_return,
        holding_days=273,
        positive_probability=odds.positive_return_probability,
        annual_thresholds=odds.adjusted_thresholds,
    )

    assert zone_272 is ParticipationZone.EXCEPTIONAL_ODDS
    assert zone_273 is ParticipationZone.ACCEPTABLE_ODDS
