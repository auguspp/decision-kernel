from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import DeepResearchPackage
from .primitives import KernelModel
from .research_contract_v1 import (
    ResearchContractV1Payload,
    ResearchContractV1Status,
    assess_research_contract_v1,
)
from .source_policy_v2 import SOURCE_POLICY_V2_VERSION


class ProbabilityEffect(StrEnum):
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"


class ExpectationEventBridgeV2(KernelModel):
    event_id: str = Field(min_length=1, max_length=128)
    event_date: date
    pre_event_expectation: dict[str, Any] = Field(min_length=1)
    actual_event: dict[str, Any] = Field(min_length=1)
    post_event_expectation: dict[str, Any] = Field(min_length=1)
    market_reaction: dict[str, Any] = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    probability_effect: ProbabilityEffect
    probability_effect_reason: str = Field(min_length=1)
    evidence_artifact_ids: tuple[UUID, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_uniqueness(self) -> "ExpectationEventBridgeV2":
        if len(set(self.evidence_artifact_ids)) != len(self.evidence_artifact_ids):
            raise ValueError("event bridge evidence ids must be unique")
        return self


class ResearchContractV2Payload(ResearchContractV1Payload):
    """Method v2: separate reality, market belief and our belief explicitly."""

    source_policy_version: str = Field(default=SOURCE_POLICY_V2_VERSION, min_length=1)
    reality_map: dict[str, Any] = Field(min_length=1)
    our_belief_map: dict[str, Any] = Field(min_length=1)
    expectation_event_bridges: tuple[ExpectationEventBridgeV2, ...] = Field(min_length=1)
    schema_version: Literal[2] = 2


class ResearchContractV2Status(StrEnum):
    NONCONFORMING = "NONCONFORMING"
    CONFORMING = "CONFORMING"


class ResearchContractV2Issue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    location: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)


class ResearchContractV2Assessment(KernelModel):
    status: ResearchContractV2Status
    issues: tuple[ResearchContractV2Issue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "ResearchContractV2Assessment":
        expected = (
            ResearchContractV2Status.CONFORMING
            if not self.issues
            else ResearchContractV2Status.NONCONFORMING
        )
        if self.status is not expected:
            raise ValueError("Research Contract v2 status must match its issue set")
        return self


def assess_research_contract_v2(
    package: DeepResearchPackage,
    payload: ResearchContractV2Payload,
) -> ResearchContractV2Assessment:
    """Assess method v2 without changing Kernel constitution or commit authority."""

    issues: list[ResearchContractV2Issue] = []
    base = ResearchContractV1Payload(
        research_snapshot_id=payload.research_snapshot_id,
        contract_version=payload.contract_version,
        doctrine_version_reference=payload.doctrine_version_reference,
        research_mode=payload.research_mode,
        sector=payload.sector,
        industry=payload.industry,
        variant_perception=payload.variant_perception,
        market_expectation_map=payload.market_expectation_map,
        normalized_earnings_notes=payload.normalized_earnings_notes,
        valuation_framework=payload.valuation_framework,
        fundamental_clock_assessment=payload.fundamental_clock_assessment,
        expectation_clock_assessment=payload.expectation_clock_assessment,
        liquidity_clock_assessment=payload.liquidity_clock_assessment,
        monitoring_indicators=payload.monitoring_indicators,
        monitoring_falsifiers=payload.monitoring_falsifiers,
        valuation_stress_spec=payload.valuation_stress_spec,
        scenario_details=payload.scenario_details,
    )
    base_assessment = assess_research_contract_v1(package, base)
    if base_assessment.status is not ResearchContractV1Status.CONFORMING:
        for item in base_assessment.issues:
            issues.append(
                ResearchContractV2Issue(
                    code=f"V1_{item.code}",
                    location=item.location,
                    message=f"v1 research-contract prerequisite failed: {item.message}",
                )
            )

    if payload.source_policy_version != SOURCE_POLICY_V2_VERSION:
        _issue(issues, "SOURCE_POLICY_VERSION_UNSUPPORTED", "payload.source_policy_version")

    package_evidence = {item.id for item in package.evidence_artifacts}
    if not payload.reality_map:
        _issue(issues, "REALITY_MAP_MISSING", "payload.reality_map")
    if not payload.market_expectation_map:
        _issue(issues, "MARKET_EXPECTATION_MAP_MISSING", "payload.market_expectation_map")
    if not payload.our_belief_map:
        _issue(issues, "OUR_BELIEF_MAP_MISSING", "payload.our_belief_map")

    event_ids: set[str] = set()
    for index, bridge in enumerate(payload.expectation_event_bridges):
        location = f"payload.expectation_event_bridges.{index}"
        if bridge.event_id in event_ids:
            _issue(issues, "EVENT_BRIDGE_ID_DUPLICATE", location)
        event_ids.add(bridge.event_id)
        if not set(bridge.evidence_artifact_ids).issubset(package_evidence):
            _issue(issues, "EVENT_BRIDGE_EVIDENCE_MISSING", f"{location}.evidence_artifact_ids")
        if bridge.event_date > package.research_snapshot.as_of_datetime.date():
            _issue(issues, "EVENT_BRIDGE_AFTER_RESEARCH_PIT", f"{location}.event_date")

    return ResearchContractV2Assessment(
        status=(
            ResearchContractV2Status.CONFORMING
            if not issues
            else ResearchContractV2Status.NONCONFORMING
        ),
        issues=tuple(issues),
    )


def _issue(
    issues: list[ResearchContractV2Issue],
    code: str,
    location: str,
) -> None:
    issues.append(
        ResearchContractV2Issue(
            code=code,
            location=location,
            message=code.replace("_", " ").title(),
        )
    )
