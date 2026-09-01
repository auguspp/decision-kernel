from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.evidence import EvidenceArtifactLink, EvidenceRelationship
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research import (
    CashFlowBasis,
    CashFlowType,
    ExpectedCashFlow,
    ResearchSnapshot,
    ResearchStatus,
    Scenario,
    commit_snapshot,
    return_to_draft,
    submit_for_review,
)
from decision_kernel.valuation import ValuationBasis


AS_OF = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
HORIZON = date(2027, 9, 1)


def _basis(snapshot_id: UUID, **updates: object) -> ValuationBasis:
    values: dict[str, object] = {
        "id": uuid4(),
        "research_snapshot_id": snapshot_id,
        "version": 1,
        "as_of_datetime": AS_OF,
        "valuation_horizon_date": HORIZON,
        "valuation_method": "scenario_equity_value",
        "model_version": "v1",
        "currency": "cny",
    }
    values.update(updates)
    return ValuationBasis.model_validate(values)


def _scenario(
    snapshot_id: UUID,
    basis: ValuationBasis,
    *,
    probability: str = "1",
    **updates: object,
) -> Scenario:
    scenario_id = uuid4()
    values: dict[str, object] = {
        "id": scenario_id,
        "research_snapshot_id": snapshot_id,
        "name": "base",
        "probability": probability,
        "description": "base case",
        "valuation_method": basis.valuation_method,
        "terminal_equity_value_per_share": "12.5",
        "valuation_basis_id": basis.id,
        "expected_cash_flows": (
            ExpectedCashFlow(
                id=uuid4(),
                scenario_id=scenario_id,
                cash_flow_date=date(2027, 6, 1),
                amount="0.5",
                basis=CashFlowBasis.PER_SHARE,
                currency="CNY",
                cash_flow_type=CashFlowType.DIVIDEND,
                provenance_artifact_ids=(uuid4(),),
            ),
        ),
    }
    values.update(updates)
    return Scenario.model_validate(values)


def _snapshot(
    *,
    status: ResearchStatus = ResearchStatus.DRAFT,
    information_bundle_hash: str | None = "a" * 64,
    probabilities: tuple[str, ...] = ("1",),
    **updates: object,
) -> ResearchSnapshot:
    snapshot_id = uuid4()
    basis = _basis(snapshot_id)
    scenarios = tuple(
        _scenario(
            snapshot_id,
            basis,
            probability=probability,
            name=f"case-{index}",
        )
        for index, probability in enumerate(probabilities)
    )
    values: dict[str, object] = {
        "id": snapshot_id,
        "ticker": "600000",
        "company_name": "Sample Co",
        "exchange": "SSE",
        "currency": "cny",
        "created_at": AS_OF,
        "as_of_datetime": AS_OF,
        "valuation_horizon_date": HORIZON,
        "version": 1,
        "status": status,
        "core_thesis": "earnings can exceed current expectations",
        "market_expectations_narrative": "market expects flat earnings",
        "monitoring_plan": {
            "indicators": ["earnings release"],
            "falsifiers": ["margin collapse"],
        },
        "open_questions": ("pricing power?",),
        "created_by": "research",
        "information_bundle_hash": information_bundle_hash,
        "doctrine_version_reference": "doctrine-v1",
        "research_contract_version": "research-v1",
        "valuation_bases": (basis,),
        "scenarios": scenarios,
    }
    values.update(updates)
    return ResearchSnapshot.model_validate(values)


def test_research_snapshot_preserves_currency_and_frozen_status() -> None:
    snapshot = _snapshot()
    assert snapshot.currency == "CNY"
    assert snapshot.status is ResearchStatus.DRAFT
    with pytest.raises(ValidationError, match="frozen"):
        snapshot.status = ResearchStatus.REVIEW  # type: ignore[misc]


def test_research_version_lineage_is_explicit() -> None:
    with pytest.raises(ValidationError, match="version one cannot identify"):
        _snapshot(supersedes_snapshot_id=uuid4())

    with pytest.raises(ValidationError, match="versions after one"):
        _snapshot(version=2)


def test_research_horizon_cannot_precede_pit_as_of() -> None:
    with pytest.raises(ValidationError, match="valuation horizon cannot precede"):
        _snapshot(valuation_horizon_date=date(2026, 8, 31))


def test_research_children_must_belong_to_exact_snapshot() -> None:
    snapshot_id = uuid4()
    wrong_basis = _basis(uuid4())
    with pytest.raises(ValidationError, match="ValuationBasis must belong"):
        _snapshot(
            id=snapshot_id,
            valuation_bases=(wrong_basis,),
            scenarios=(),
        )


def test_scenario_must_reference_snapshot_valuation_basis_and_method() -> None:
    snapshot_id = uuid4()
    basis = _basis(snapshot_id)
    scenario = _scenario(snapshot_id, basis)

    with pytest.raises(ValidationError, match="reference a ValuationBasis"):
        _snapshot(
            id=snapshot_id,
            valuation_bases=(basis,),
            scenarios=(scenario.model_copy(update={"valuation_basis_id": uuid4()}),),
        )

    with pytest.raises(ValidationError, match="valuation_method must match"):
        _snapshot(
            id=snapshot_id,
            valuation_bases=(basis,),
            scenarios=(scenario.model_copy(update={"valuation_method": "other"}),),
        )


def test_expected_cash_flow_must_stay_inside_snapshot_horizon() -> None:
    snapshot_id = uuid4()
    basis = _basis(snapshot_id)
    scenario = _scenario(snapshot_id, basis)
    flow = scenario.expected_cash_flows[0].model_copy(
        update={"cash_flow_date": date(2028, 1, 1)}
    )
    invalid = scenario.model_copy(update={"expected_cash_flows": (flow,)})

    with pytest.raises(ValidationError, match="cannot occur after valuation horizon"):
        _snapshot(
            id=snapshot_id,
            valuation_bases=(basis,),
            scenarios=(invalid,),
        )


def test_evidence_link_must_belong_to_exact_snapshot() -> None:
    link = EvidenceArtifactLink(
        id=uuid4(),
        research_snapshot_id=uuid4(),
        evidence_artifact_id=uuid4(),
        relationship=EvidenceRelationship.SUPPORTS,
    )
    with pytest.raises(ValidationError, match="EvidenceArtifactLink must belong"):
        _snapshot(evidence_links=(link,))


def test_commit_requires_review_complete_probability_and_lineage() -> None:
    with pytest.raises(DomainValidationError, match="only REVIEW"):
        commit_snapshot(_snapshot(), AS_OF + timedelta(hours=1))

    review = submit_for_review(_snapshot(probabilities=("0.6", "0.3")))
    with pytest.raises(DomainValidationError, match="probabilities must sum to one"):
        commit_snapshot(review, AS_OF + timedelta(hours=1))

    no_lineage = submit_for_review(_snapshot(information_bundle_hash=None))
    with pytest.raises(DomainValidationError, match="information_bundle_hash"):
        commit_snapshot(no_lineage, AS_OF + timedelta(hours=1))


def test_review_can_return_to_draft_without_creating_a_commit() -> None:
    review = submit_for_review(_snapshot())
    assert review.status is ResearchStatus.REVIEW
    draft = return_to_draft(review)
    assert draft.status is ResearchStatus.DRAFT
    assert draft.committed_at is None


def test_commit_freezes_explicit_commit_time() -> None:
    review = submit_for_review(_snapshot(probabilities=("0.6", "0.4")))
    committed_at = AS_OF + timedelta(hours=2)
    committed = commit_snapshot(review, committed_at)

    assert committed.status is ResearchStatus.COMMITTED
    assert committed.committed_at == committed_at
    assert committed.information_bundle_hash == "a" * 64


def test_authoritative_research_rejects_binary_float_inputs() -> None:
    with pytest.raises(ValidationError, match="binary float"):
        _snapshot(market_expectation_map={"margin": 0.25})
