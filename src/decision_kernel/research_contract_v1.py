from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import (
    DEEP_RESEARCH_CONTRACT_VERSION,
    AdversarialSeverity,
    DeepResearchPackage,
)
from .primitives import KernelModel
from .research_funnel import ResearchClaimKind


class ResearchContractV1ScenarioDetail(KernelModel):
    """Method-specific scenario explanation keyed to one kernel Scenario."""

    scenario_id: UUID
    description: str = Field(min_length=1)
    assumptions: dict[str, Any] = Field(default_factory=dict)
    financial_driver_values: dict[str, Any] = Field(default_factory=dict)
    normalized_earnings: Decimal | None = None
    notes: str | None = None


class ResearchContractV1Payload(KernelModel):
    """Decision OS research method payload kept outside ResearchSnapshot constitution."""

    research_snapshot_id: UUID
    contract_version: str = Field(min_length=1, max_length=64)
    doctrine_version_reference: str = Field(min_length=1, max_length=128)
    research_mode: str = Field(default="FULL", min_length=1, max_length=64)
    sector: str | None = Field(default=None, max_length=128)
    industry: str | None = Field(default=None, max_length=128)
    variant_perception: str | None = None
    market_expectation_map: dict[str, Any] = Field(default_factory=dict)
    normalized_earnings_notes: str | None = None
    valuation_framework: str | None = None
    fundamental_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    expectation_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    liquidity_clock_assessment: dict[str, Any] = Field(default_factory=dict)
    monitoring_indicators: tuple[str, ...] = ()
    monitoring_falsifiers: tuple[str, ...] = ()
    valuation_stress_spec: dict[str, Any] = Field(default_factory=dict)
    scenario_details: tuple[ResearchContractV1ScenarioDetail, ...] = ()
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_method_payload(self) -> "ResearchContractV1Payload":
        if any(not item.strip() for item in self.monitoring_indicators):
            raise ValueError("monitoring indicators cannot be blank")
        if any(not item.strip() for item in self.monitoring_falsifiers):
            raise ValueError("monitoring falsifiers cannot be blank")
        if len({item.scenario_id for item in self.scenario_details}) != len(
            self.scenario_details
        ):
            raise ValueError("Research Contract v1 scenario details must be unique")
        return self


class ResearchContractV1Status(StrEnum):
    NONCONFORMING = "NONCONFORMING"
    CONFORMING = "CONFORMING"


class ResearchContractV1Issue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ResearchContractV1Assessment(KernelModel):
    status: ResearchContractV1Status
    issues: tuple[ResearchContractV1Issue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ResearchContractV1Assessment":
        expected = (
            ResearchContractV1Status.CONFORMING
            if not self.issues
            else ResearchContractV1Status.NONCONFORMING
        )
        if self.status is not expected:
            raise ValueError("Research Contract v1 status must match its issue set")
        return self


def assess_research_contract_v1(
    package: DeepResearchPackage,
    payload: ResearchContractV1Payload,
) -> ResearchContractV1Assessment:
    """Assess the preserved Decision OS research method without making it kernel law."""

    issues: list[ResearchContractV1Issue] = []
    deep = package.deep_research
    snapshot = package.research_snapshot

    if payload.research_snapshot_id != snapshot.id:
        _issue(
            issues,
            "SNAPSHOT_ID_MISMATCH",
            "payload.research_snapshot_id",
            "Research Contract v1 payload must bind to the exact kernel ResearchSnapshot",
        )
    if payload.contract_version != DEEP_RESEARCH_CONTRACT_VERSION:
        _issue(
            issues,
            "CONTRACT_VERSION_UNSUPPORTED",
            "payload.contract_version",
            "Research Contract v1 requires research-odds-rehearsal-v1",
        )

    required_kinds = {
        ResearchClaimKind.FACT,
        ResearchClaimKind.INFERENCE,
        ResearchClaimKind.ASSUMPTION,
    }
    if not required_kinds.issubset({claim.kind for claim in deep.material_claims}):
        _issue(
            issues,
            "CLAIM_CLASS_SET_INCOMPLETE",
            "deep_research.material_claims",
            "Research Contract v1 requires FACT, INFERENCE, and ASSUMPTION claims",
        )

    required_text = {
        "variant_perception": payload.variant_perception,
        "normalized_earnings_notes": payload.normalized_earnings_notes,
        "valuation_framework": payload.valuation_framework,
    }
    for field, value in required_text.items():
        if value is None or not value.strip():
            _issue(
                issues,
                "METHOD_FIELD_MISSING",
                f"payload.{field}",
                f"Research Contract v1 requires {field}",
            )

    required_structures = {
        "market_expectation_map": payload.market_expectation_map,
        "fundamental_clock_assessment": payload.fundamental_clock_assessment,
        "expectation_clock_assessment": payload.expectation_clock_assessment,
        "liquidity_clock_assessment": payload.liquidity_clock_assessment,
        "valuation_stress_spec": payload.valuation_stress_spec,
    }
    for field, value in required_structures.items():
        if not value:
            _issue(
                issues,
                "METHOD_STRUCTURE_MISSING",
                f"payload.{field}",
                f"Research Contract v1 requires {field}",
            )

    if not snapshot.open_questions:
        _issue(
            issues,
            "OPEN_QUESTIONS_MISSING",
            "research_snapshot.open_questions",
            "Research Contract v1 requires unresolved questions to remain explicit",
        )

    indicators = payload.monitoring_indicators
    if not 3 <= len(indicators) <= 5:
        _issue(
            issues,
            "MONITORING_INDICATORS_INVALID",
            "payload.monitoring_indicators",
            "Research Contract v1 requires three to five monitoring indicators",
        )
    elif indicators != snapshot.monitoring_triggers:
        _issue(
            issues,
            "MONITORING_PROJECTION_MISMATCH",
            "research_snapshot.monitoring_triggers",
            "Research Contract v1 monitoring indicators must project exactly into Human triggers",
        )

    if not deep.explicit_falsifiers:
        _issue(
            issues,
            "FALSIFIERS_MISSING",
            "deep_research.explicit_falsifiers",
            "Research Contract v1 requires explicit falsifiers",
        )
    if payload.monitoring_falsifiers != deep.explicit_falsifiers:
        _issue(
            issues,
            "FALSIFIERS_NOT_FROZEN",
            "payload.monitoring_falsifiers",
            "Research Contract v1 payload must freeze Deep Research falsifiers",
        )
    if tuple(snapshot.thesis_invalidation) != tuple(deep.explicit_falsifiers):
        _issue(
            issues,
            "INVALIDATION_PROJECTION_MISMATCH",
            "research_snapshot.thesis_invalidation",
            "Research Contract v1 falsifiers must project exactly into Human invalidation",
        )

    if not deep.adversarial_findings:
        _issue(
            issues,
            "ADVERSARIAL_REVIEW_MISSING",
            "deep_research.adversarial_findings",
            "Research Contract v1 requires bounded adversarial review",
        )
    if any(
        finding.severity is AdversarialSeverity.BLOCK
        for finding in deep.adversarial_findings
    ):
        _issue(
            issues,
            "ADVERSARIAL_BLOCK_UNRESOLVED",
            "deep_research.adversarial_findings",
            "Research Contract v1 does not conform while an adversarial BLOCK remains",
        )

    if not 2 <= len(snapshot.scenarios) <= 5:
        _issue(
            issues,
            "SCENARIO_SET_NOT_SMALL",
            "research_snapshot.scenarios",
            "Research Contract v1 uses a small two-to-five-scenario distribution",
        )

    kernel_scenario_ids = {scenario.id for scenario in snapshot.scenarios}
    detail_by_id = {detail.scenario_id: detail for detail in payload.scenario_details}
    if set(detail_by_id) != kernel_scenario_ids:
        _issue(
            issues,
            "SCENARIO_DETAIL_COVERAGE_MISMATCH",
            "payload.scenario_details",
            "Research Contract v1 must explain every exact kernel Scenario once",
        )
    for scenario in snapshot.scenarios:
        detail = detail_by_id.get(scenario.id)
        if detail is None:
            continue
        if not detail.assumptions or not detail.financial_driver_values:
            _issue(
                issues,
                "SCENARIO_DRIVER_STRUCTURE_MISSING",
                f"payload.scenario_details.{scenario.name}",
                "Research Contract v1 requires explicit assumptions and financial drivers",
            )

    return ResearchContractV1Assessment(
        status=(
            ResearchContractV1Status.CONFORMING
            if not issues
            else ResearchContractV1Status.NONCONFORMING
        ),
        issues=tuple(issues),
    )


def _issue(
    issues: list[ResearchContractV1Issue],
    code: str,
    location: str,
    message: str,
) -> None:
    issues.append(ResearchContractV1Issue(code=code, location=location, message=message))
