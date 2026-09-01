from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .evidence import EvidenceArtifactLink
from .primitives import (
    AwareDateTime,
    CurrencyCode,
    DomainValidationError,
    KernelModel,
)
from .valuation import ValuationBasis


PROBABILITY_TOLERANCE = Decimal("0.000001")


class ResearchStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    COMMITTED = "COMMITTED"


class ModelRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class CashFlowBasis(StrEnum):
    PER_SHARE = "PER_SHARE"
    TOTAL_EQUITY = "TOTAL_EQUITY"


class CashFlowType(StrEnum):
    DIVIDEND = "DIVIDEND"
    SPECIAL_DIVIDEND = "SPECIAL_DIVIDEND"
    RETURN_OF_CAPITAL = "RETURN_OF_CAPITAL"
    OTHER_DISTRIBUTION = "OTHER_DISTRIBUTION"


class ExpectedCashFlow(KernelModel):
    id: UUID
    scenario_id: UUID
    cash_flow_date: date
    amount: Decimal
    basis: CashFlowBasis
    currency: CurrencyCode
    cash_flow_type: CashFlowType
    provenance_artifact_ids: tuple[UUID, ...] = Field(min_length=1)
    assumption_notes: str | None = None
    schema_version: int = Field(default=1, ge=1)


class Scenario(KernelModel):
    id: UUID
    research_snapshot_id: UUID
    name: str = Field(min_length=1, max_length=64)
    probability: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    description: str
    assumptions: dict[str, Any] = Field(default_factory=dict)
    financial_driver_values: dict[str, Any] = Field(default_factory=dict)
    normalized_earnings: Decimal | None = None
    valuation_method: str = Field(min_length=1, max_length=64)
    terminal_equity_value_per_share: Decimal
    valuation_basis_id: UUID
    expected_cash_flows: tuple[ExpectedCashFlow, ...] = ()
    notes: str | None = None

    @model_validator(mode="after")
    def validate_children(self) -> "Scenario":
        if any(flow.scenario_id != self.id for flow in self.expected_cash_flows):
            raise ValueError("expected cash flow scenario_id must match its Scenario")
        if len({flow.id for flow in self.expected_cash_flows}) != len(
            self.expected_cash_flows
        ):
            raise ValueError("expected cash flow ids must be unique")
        return self


class ResearchSnapshot(KernelModel):
    """Frozen research state that may be reviewed and explicitly committed."""

    id: UUID
    ticker: str = Field(min_length=1, max_length=32)
    company_name: str = Field(min_length=1, max_length=255)
    exchange: str = Field(min_length=1, max_length=32)
    currency: CurrencyCode
    sector: str | None = Field(default=None, max_length=128)
    industry: str | None = Field(default=None, max_length=128)
    created_at: AwareDateTime
    as_of_datetime: AwareDateTime
    valuation_horizon_date: date
    version: int = Field(ge=1)
    status: ResearchStatus = ResearchStatus.DRAFT
    supersedes_snapshot_id: UUID | None = None
    research_mode: str = Field(default="FULL", min_length=1, max_length=64)
    core_thesis: str = ""
    variant_perception: str | None = None
    market_expectations_narrative: str | None = None
    market_expectation_map: dict[str, Any] = Field(default_factory=dict)
    normalized_earnings_notes: str | None = None
    valuation_framework: str | None = None
    fundamental_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    expectation_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    liquidity_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    monitoring_plan: dict[str, Any] = Field(default_factory=dict)
    valuation_stress_spec: dict[str, Any] = Field(default_factory=dict)
    model_risk_level: ModelRiskLevel = ModelRiskLevel.MEDIUM
    model_risk_notes: str | None = None
    open_questions: tuple[str, ...] = ()
    created_by: str = Field(min_length=1, max_length=128)
    committed_at: AwareDateTime | None = None
    research_engine_version: str = Field(default="manual-v1", min_length=1, max_length=64)
    information_bundle_hash: str | None = Field(default=None, max_length=128)
    doctrine_version_reference: str = Field(min_length=1, max_length=128)
    research_contract_version: str = Field(min_length=1, max_length=64)
    research_origin: str | None = Field(default=None, max_length=128)
    schema_version: int = Field(default=1, ge=1)
    valuation_bases: tuple[ValuationBasis, ...] = ()
    scenarios: tuple[Scenario, ...] = ()
    evidence_links: tuple[EvidenceArtifactLink, ...] = ()

    @model_validator(mode="after")
    def validate_aggregate_references(self) -> "ResearchSnapshot":
        if self.supersedes_snapshot_id == self.id:
            raise ValueError("ResearchSnapshot cannot supersede itself")
        if self.version == 1 and self.supersedes_snapshot_id is not None:
            raise ValueError("ResearchSnapshot version one cannot identify a predecessor")
        if self.version > 1 and self.supersedes_snapshot_id is None:
            raise ValueError(
                "ResearchSnapshot versions after one must identify their predecessor"
            )
        if self.valuation_horizon_date < self.as_of_datetime.date():
            raise ValueError("valuation horizon cannot precede as-of date")
        if self.status is ResearchStatus.COMMITTED and self.committed_at is None:
            raise ValueError("committed snapshot requires committed_at")
        if self.status is not ResearchStatus.COMMITTED and self.committed_at is not None:
            raise ValueError("only committed snapshots may have committed_at")

        basis_ids = {basis.id for basis in self.valuation_bases}
        if len(basis_ids) != len(self.valuation_bases):
            raise ValueError("ValuationBasis ids must be unique")
        for basis in self.valuation_bases:
            if basis.research_snapshot_id != self.id:
                raise ValueError("ValuationBasis must belong to its ResearchSnapshot")
            if basis.valuation_horizon_date != self.valuation_horizon_date:
                raise ValueError("ValuationBasis must use the snapshot valuation horizon")

        if len({scenario.id for scenario in self.scenarios}) != len(self.scenarios):
            raise ValueError("Scenario ids must be unique")
        for scenario in self.scenarios:
            if scenario.research_snapshot_id != self.id:
                raise ValueError("Scenario must belong to its ResearchSnapshot")
            if scenario.valuation_basis_id not in basis_ids:
                raise ValueError("Scenario must reference a ValuationBasis in the snapshot")
            basis = next(
                item for item in self.valuation_bases if item.id == scenario.valuation_basis_id
            )
            if scenario.valuation_method != basis.valuation_method:
                raise ValueError(
                    "Scenario valuation_method must match its ValuationBasis"
                )
            for flow in scenario.expected_cash_flows:
                if flow.cash_flow_date < self.as_of_datetime.date():
                    raise ValueError("expected cash flow cannot precede snapshot as-of date")
                if flow.cash_flow_date > self.valuation_horizon_date:
                    raise ValueError("expected cash flow cannot occur after valuation horizon")

        if any(link.research_snapshot_id != self.id for link in self.evidence_links):
            raise ValueError("EvidenceArtifactLink must belong to its ResearchSnapshot")
        return self

    def assert_commit_ready(self) -> None:
        if self.status is not ResearchStatus.REVIEW:
            raise DomainValidationError("only REVIEW snapshots can be committed")
        if not self.scenarios:
            raise DomainValidationError("commit requires at least one Scenario")
        probability_sum = sum(
            (scenario.probability for scenario in self.scenarios), Decimal("0")
        )
        if abs(probability_sum - Decimal("1")) > PROBABILITY_TOLERANCE:
            raise DomainValidationError("scenario probabilities must sum to one")
        if not self.information_bundle_hash:
            raise DomainValidationError("commit requires information_bundle_hash")


def submit_for_review(snapshot: ResearchSnapshot) -> ResearchSnapshot:
    if snapshot.status is not ResearchStatus.DRAFT:
        raise DomainValidationError("only DRAFT snapshots can enter REVIEW")
    return snapshot.model_copy(update={"status": ResearchStatus.REVIEW})


def return_to_draft(snapshot: ResearchSnapshot) -> ResearchSnapshot:
    if snapshot.status is not ResearchStatus.REVIEW:
        raise DomainValidationError("only REVIEW snapshots can return to DRAFT")
    return snapshot.model_copy(update={"status": ResearchStatus.DRAFT})


def commit_snapshot(
    snapshot: ResearchSnapshot,
    committed_at: AwareDateTime,
) -> ResearchSnapshot:
    snapshot.assert_commit_ready()
    return ResearchSnapshot.model_validate(
        {
            **snapshot.model_dump(mode="python"),
            "status": ResearchStatus.COMMITTED,
            "committed_at": committed_at,
        }
    )
