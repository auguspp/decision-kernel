from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.authority import NO_SYSTEM_AUTHORITY, SystemAuthorityBoundary
from decision_kernel.human_surface import (
    HumanResearchSurface,
    HumanSurfaceStatus,
    build_human_surface,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import (
    OddsResearchPolicy,
    ParticipationZone,
    build_odds_research,
)
from decision_kernel.primitives import DomainValidationError
from decision_kernel.rehearsal import (
    DECISION_REHEARSAL_LIMITATIONS,
    FrozenDecisionRehearsalArtifact,
    NonAuthoritativeRehearsalFraming,
    build_decision_rehearsal,
    build_human_decision_brief,
)
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
ODDS_AT = AS_OF + timedelta(hours=3)
REHEARSAL_AT = AS_OF + timedelta(hours=4)
HORIZON = date(2027, 9, 1)


def _committed_snapshot() -> ResearchSnapshot:
    snapshot_id = uuid4()
    basis = ValuationBasis(
        id=uuid4(),
        research_snapshot_id=snapshot_id,
        version=1,
        as_of_datetime=AS_OF,
        valuation_horizon_date=HORIZON,
        valuation_method="scenario_equity_value",
        model_version="v1",
        currency="CNY",
    )
    scenario = Scenario(
        id=uuid4(),
        research_snapshot_id=snapshot_id,
        name="base",
        probability="1",
        terminal_equity_value_per_share="12",
        valuation_basis_id=basis.id,
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
        monitoring_triggers=("earnings release",),
        model_risk_level=ModelRiskLevel.LOW,
        model_risk_notes="terminal value uncertainty",
        open_questions=("pricing power?", "capex discipline?"),
        created_by="research",
        information_bundle_hash="a" * 64,
        valuation_bases=(basis,),
        scenarios=(scenario,),
    )
    return commit_snapshot(submit_for_review(draft), COMMITTED_AT)


def _market() -> ObservedMarket:
    return ObservedMarket(
        market_price="10",
        market_timestamp=MARKET_AT,
        market_utc_offset_minutes=480,
        market_data_source="HiThink",
        price_convention="CLOSE",
        currency="CNY",
    )


def _policy(*, insufficient: bool = False) -> OddsResearchPolicy:
    if insufficient:
        acceptable, attractive, exceptional = "0.25", "0.35", "0.45"
    else:
        acceptable, attractive, exceptional = "0.10", "0.20", "0.30"
    return OddsResearchPolicy(
        policy_version="test-v1",
        minimum_holding_period_days=1,
        maximum_holding_period_days=800,
        acceptable_min_expected_return=acceptable,
        attractive_min_expected_return=attractive,
        exceptional_min_expected_return=exceptional,
        acceptable_min_positive_probability="0.50",
        attractive_min_positive_probability="0.60",
        exceptional_min_positive_probability="0.70",
        low_model_risk_addon="0",
        medium_model_risk_addon="0.06",
        high_model_risk_addon="0.10",
        very_high_model_risk_addon="0.15",
        elevated_uncertainty_addon="0.03",
        high_uncertainty_addon="0.08",
    )


def _odds(snapshot: ResearchSnapshot, *, insufficient: bool = False):
    return build_odds_research(
        artifact_id=uuid4(),
        created_at=ODDS_AT,
        research_snapshot=snapshot,
        observed_market=_market(),
        policy=_policy(insufficient=insufficient),
    )


def _rehearsal(snapshot: ResearchSnapshot, *, insufficient: bool = False):
    odds = _odds(snapshot, insufficient=insufficient)
    rehearsal = build_decision_rehearsal(
        artifact_id=uuid4(),
        created_at=REHEARSAL_AT,
        research_snapshot=snapshot,
        odds_research=odds,
        framing=NonAuthoritativeRehearsalFraming(
            why_now="price now exposes the research question",
            current_expression="observe only; no system action",
        ),
    )
    return rehearsal, odds


def test_decision_rehearsal_is_non_binding_and_has_no_investment_authority() -> None:
    rehearsal, _ = _rehearsal(_committed_snapshot())
    artifact = rehearsal.artifact

    assert artifact.system_status == "DECISION_REHEARSAL_ONLY"
    assert artifact.human_status == "HUMAN_DECISION_REQUIRED"
    assert artifact.investment_authority == "NONE"
    assert artifact.limitations == DECISION_REHEARSAL_LIMITATIONS
    assert "NO_SYSTEM_INVESTMENT_DECISION" in artifact.limitations
    assert "NO_POSITION_SIZE_OR_TARGET_WEIGHT" in artifact.limitations


def test_rehearsal_requires_exact_research_and_odds_lineage() -> None:
    snapshot_a = _committed_snapshot()
    snapshot_b = _committed_snapshot()
    odds_a = _odds(snapshot_a)

    with pytest.raises(DomainValidationError, match="must belong"):
        build_decision_rehearsal(
            artifact_id=uuid4(),
            created_at=REHEARSAL_AT,
            research_snapshot=snapshot_b,
            odds_research=odds_a,
            framing=NonAuthoritativeRehearsalFraming(
                why_now="why now",
                current_expression="observe only",
            ),
        )


def test_human_brief_preserves_frozen_unknowns_without_ranking_them() -> None:
    rehearsal, _ = _rehearsal(_committed_snapshot())
    brief = build_human_decision_brief(rehearsal)

    assert brief.open_questions == ("pricing power?", "capex discipline?")
    assert brief.invalidation == ("margin collapse",)
    assert brief.monitoring_triggers == ("earnings release",)
    assert brief.investment_authority == "NONE"


def test_insufficient_odds_does_not_wake_human_even_when_rehearsal_says_human_required() -> None:
    rehearsal, odds = _rehearsal(_committed_snapshot(), insufficient=True)
    surface = build_human_surface(rehearsal, odds)

    assert odds.artifact.participation_zone is ParticipationZone.INSUFFICIENT_ODDS
    assert rehearsal.artifact.human_status == "HUMAN_DECISION_REQUIRED"
    assert surface.status is HumanSurfaceStatus.NOT_ELIGIBLE_INSUFFICIENT_ODDS
    assert surface.attention_eligible is False
    assert surface.investment_authority == "NONE"


def test_acceptable_or_better_odds_wake_human_through_surface_gate() -> None:
    rehearsal, odds = _rehearsal(_committed_snapshot())
    surface = build_human_surface(rehearsal, odds)

    assert odds.artifact.participation_zone is ParticipationZone.ATTRACTIVE_ODDS
    assert surface.status is HumanSurfaceStatus.DECISION_WORTHY_REVIEW
    assert surface.attention_eligible is True


def test_human_surface_requires_exact_odds_used_by_rehearsal() -> None:
    snapshot = _committed_snapshot()
    rehearsal, _ = _rehearsal(snapshot)
    different_odds = _odds(snapshot)

    with pytest.raises(DomainValidationError, match="exact Odds artifact"):
        build_human_surface(rehearsal, different_odds)


def test_human_surface_status_and_attention_eligibility_cannot_diverge() -> None:
    rehearsal, odds = _rehearsal(_committed_snapshot())
    brief = build_human_decision_brief(rehearsal)

    with pytest.raises(ValidationError, match="must match"):
        HumanResearchSurface(
            status=HumanSurfaceStatus.DECISION_WORTHY_REVIEW,
            attention_eligible=False,
            eligibility_reason="invalid",
            brief=brief,
        )


def test_rehearsal_hash_covers_exact_non_binding_artifact() -> None:
    rehearsal, _ = _rehearsal(_committed_snapshot())
    assert rehearsal.artifact_hash == canonical_hash(rehearsal.artifact)

    tampered = rehearsal.artifact.model_copy(
        update={"what_we_believe": "different belief"}
    )
    with pytest.raises(ValidationError, match="hash must cover"):
        FrozenDecisionRehearsalArtifact(
            artifact_hash=rehearsal.artifact_hash,
            artifact=tampered,
        )


def test_system_authority_boundary_cannot_encode_a_recommendation_or_action() -> None:
    assert NO_SYSTEM_AUTHORITY.recommendation == "NONE"
    assert NO_SYSTEM_AUTHORITY.position_size == "NONE"
    assert NO_SYSTEM_AUTHORITY.portfolio == "NONE"
    assert NO_SYSTEM_AUTHORITY.human_decision == "NONE"
    assert NO_SYSTEM_AUTHORITY.execution == "NONE"
    assert NO_SYSTEM_AUTHORITY.capital_deployment == "NONE"

    with pytest.raises(ValidationError):
        SystemAuthorityBoundary.model_validate({"recommendation": "BUY"})
