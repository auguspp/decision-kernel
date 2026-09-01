from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .deep_research import (
    DEEP_RESEARCH_CONTRACT_VERSION,
    AdversarialSeverity,
    DeepResearchPackage,
)
from .primitives import KernelModel
from .research_funnel import ResearchClaimKind


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
) -> ResearchContractV1Assessment:
    """Assess the preserved Decision OS research method without making it kernel law."""

    issues: list[ResearchContractV1Issue] = []
    deep = package.deep_research
    snapshot = package.research_snapshot

    if snapshot.research_contract_version != DEEP_RESEARCH_CONTRACT_VERSION:
        _issue(
            issues,
            "CONTRACT_VERSION_UNSUPPORTED",
            "research_snapshot.research_contract_version",
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
        "variant_perception": snapshot.variant_perception,
        "normalized_earnings_notes": snapshot.normalized_earnings_notes,
        "valuation_framework": snapshot.valuation_framework,
    }
    for field, value in required_text.items():
        if value is None or not value.strip():
            _issue(
                issues,
                "METHOD_FIELD_MISSING",
                f"research_snapshot.{field}",
                f"Research Contract v1 requires {field}",
            )

    required_structures = {
        "market_expectation_map": snapshot.market_expectation_map,
        "fundamental_clock_assessment": snapshot.fundamental_clock_assessment,
        "expectation_clock_assessment": snapshot.expectation_clock_assessment,
        "liquidity_clock_assessment": snapshot.liquidity_clock_assessment,
        "valuation_stress_spec": snapshot.valuation_stress_spec,
    }
    for field, value in required_structures.items():
        if not value:
            _issue(
                issues,
                "METHOD_STRUCTURE_MISSING",
                f"research_snapshot.{field}",
                f"Research Contract v1 requires {field}",
            )

    if not snapshot.open_questions:
        _issue(
            issues,
            "OPEN_QUESTIONS_MISSING",
            "research_snapshot.open_questions",
            "Research Contract v1 requires unresolved questions to remain explicit",
        )

    indicators = snapshot.monitoring_plan.get("indicators")
    falsifiers = snapshot.monitoring_plan.get("falsifiers")
    if not isinstance(indicators, (list, tuple)) or not 3 <= len(indicators) <= 5:
        _issue(
            issues,
            "MONITORING_INDICATORS_INVALID",
            "research_snapshot.monitoring_plan.indicators",
            "Research Contract v1 requires three to five monitoring indicators",
        )
    elif tuple(indicators) != snapshot.monitoring_triggers:
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
    if tuple(falsifiers or ()) != deep.explicit_falsifiers:
        _issue(
            issues,
            "FALSIFIERS_NOT_FROZEN",
            "research_snapshot.monitoring_plan.falsifiers",
            "Research Contract v1 monitoring plan must freeze Deep Research falsifiers",
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
    for scenario in snapshot.scenarios:
        if not scenario.assumptions or not scenario.financial_driver_values:
            _issue(
                issues,
                "SCENARIO_DRIVER_STRUCTURE_MISSING",
                f"research_snapshot.scenarios.{scenario.name}",
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
