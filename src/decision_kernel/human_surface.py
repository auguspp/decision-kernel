from __future__ import annotations

from enum import StrEnum
from pydantic import Field, model_validator

from .authority import InvestmentAuthority, NO_INVESTMENT_AUTHORITY
from .odds import FrozenOddsResearchArtifact, ParticipationZone
from .primitives import DomainValidationError, KernelModel
from .rehearsal import (
    FrozenDecisionRehearsalArtifact,
    HumanDecisionBrief,
    build_human_decision_brief,
)


class HumanSurfaceStatus(StrEnum):
    DECISION_WORTHY_REVIEW = "DECISION_WORTHY_REVIEW"
    NOT_ELIGIBLE_INSUFFICIENT_ODDS = "NOT_ELIGIBLE_INSUFFICIENT_ODDS"


class HumanResearchSurface(KernelModel):
    status: HumanSurfaceStatus
    attention_eligible: bool
    eligibility_reason: str = Field(min_length=1)
    brief: HumanDecisionBrief
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY

    @model_validator(mode="after")
    def validate_attention_boundary(self) -> "HumanResearchSurface":
        expected = self.status is HumanSurfaceStatus.DECISION_WORTHY_REVIEW
        if self.attention_eligible is not expected:
            raise ValueError("Human attention eligibility must match the surface status")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("Human surface cannot gain investment authority")
        return self


def build_human_surface(
    rehearsal: FrozenDecisionRehearsalArtifact,
    odds: FrozenOddsResearchArtifact,
) -> HumanResearchSurface:
    """Project the only kernel-owned Human wake gate from frozen Rehearsal + Odds."""

    artifact = rehearsal.artifact
    if (
        artifact.odds_artifact_id != odds.artifact.id
        or artifact.odds_artifact_hash != odds.artifact_hash
    ):
        raise DomainValidationError(
            "Human surface requires the exact Odds artifact used by Decision Rehearsal"
        )

    brief = build_human_decision_brief(rehearsal)
    zone = odds.artifact.participation_zone
    if zone is ParticipationZone.INSUFFICIENT_ODDS:
        return HumanResearchSurface(
            status=HumanSurfaceStatus.NOT_ELIGIBLE_INSUFFICIENT_ODDS,
            attention_eligible=False,
            eligibility_reason=(
                "current research odds do not satisfy the declared ACCEPTABLE_ODDS "
                "threshold; no Human wake is created by default"
            ),
            brief=brief,
        )

    return HumanResearchSurface(
        status=HumanSurfaceStatus.DECISION_WORTHY_REVIEW,
        attention_eligible=True,
        eligibility_reason=(
            f"current research odds satisfy the declared {zone.value} threshold"
        ),
        brief=brief,
    )
