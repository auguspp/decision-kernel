from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.conditional_odds import (
    DeclaredConditionalWorld,
    build_conditional_provisional_odds,
    build_conditional_world_set,
)
from decision_kernel.primitives import DomainValidationError
from decision_kernel.provisional_odds import HumanPriceContext
from decision_kernel.research import ModelRiskLevel, ResearchSnapshot, ResearchStatus
from decision_kernel.research_commit import commit_research_package
from test_generic_research_commit import _generic_package
from test_research_only_commit_v2 import rehash, v2_package


def _unknown_risk_package(*, numerical: bool = False):
    package = v2_package(numerical=numerical)
    snapshot = package.research_snapshot.model_copy(
        update={
            "model_risk_level": ModelRiskLevel.NOT_ESTABLISHED,
            "model_risk_notes": (
                "Scalar model-risk severity is not established by the frozen Research; "
                "preserve the explicit UNKNOWN instead of defaulting it for numerical Odds."
            ),
        }
    )
    return rehash(package.model_copy(update={"research_snapshot": snapshot}))


def test_schema_v2_research_only_can_commit_unestablished_model_risk() -> None:
    package = _unknown_risk_package()

    result = commit_research_package(package)

    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.research_snapshot.schema_version == 2
    assert result.research_snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert result.research_snapshot.scenarios == ()
    assert result.research_snapshot.valuation_bases == ()


def test_legacy_schema_v1_cannot_use_unestablished_model_risk() -> None:
    legacy = _generic_package().research_snapshot.model_dump(mode="python")
    legacy["model_risk_level"] = "NOT_ESTABLISHED"

    with pytest.raises((DomainValidationError, ValidationError), match="Research-only"):
        ResearchSnapshot.model_validate(legacy)


def test_v2_numerical_state_cannot_use_unestablished_model_risk() -> None:
    package = _unknown_risk_package(numerical=True)

    with pytest.raises((DomainValidationError, ValidationError), match="Research-only"):
        commit_research_package(package)


def test_legacy_default_model_risk_is_unchanged() -> None:
    assert _generic_package().research_snapshot.model_risk_level is ModelRiskLevel.MEDIUM


def test_probability_free_conditional_analysis_accepts_committed_unknown_model_risk() -> None:
    result = commit_research_package(_unknown_risk_package())
    snapshot = result.research_snapshot
    evidence_id = snapshot.evidence_links[0].evidence_artifact_id
    committed_at = snapshot.committed_at
    assert committed_at is not None

    horizon = snapshot.as_of_datetime.date() + timedelta(days=1095)
    world = DeclaredConditionalWorld(
        id=uuid4(),
        name="declared operating world",
        terminal_equity_value_per_share=Decimal("12"),
        operating_conditions=("Frozen business thesis remains intact",),
        valuation_expression="Declared terminal per-share value; probability not established.",
        provenance_artifact_ids=(evidence_id,),
    )
    worlds = build_conditional_world_set(
        research_snapshot=snapshot,
        worlds=(world,),
        valuation_horizon_date=horizon,
        world_set_id=uuid4(),
        created_at=committed_at + timedelta(minutes=1),
    )
    context = HumanPriceContext(
        ticker=snapshot.ticker,
        exchange=snapshot.exchange,
        currency=snapshot.currency,
        price=Decimal("10"),
        price_timestamp=snapshot.as_of_datetime + timedelta(minutes=1),
        utc_offset_minutes=0,
        supplied_at=committed_at + timedelta(minutes=2),
        source_reference="synthetic Human context price for contract regression only",
        price_convention="DECLARED_CONTEXT_PRICE_NOT_MARKET_OBSERVATION",
    )

    conditional = build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=worlds,
        price_context=context,
        artifact_id=uuid4(),
        created_at=committed_at + timedelta(minutes=3),
    )

    assert conditional.artifact.calculation_status.value == "CALCULATED"
    assert conditional.artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert conditional.artifact.probability_input == "ABSENT_BY_DESIGN"
    assert conditional.artifact.weighted_aggregate == "NOT_COMPUTED"
    assert conditional.artifact.world_results[0].undiscounted_holding_period_return == Decimal("0.2")
    assert snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
