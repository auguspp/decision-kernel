from __future__ import annotations

"""Method-agnostic Decision Spine.

Research methods may change independently. This module starts from a frozen ResearchSnapshot and
owns only the product-level composition into Odds, Decision Rehearsal, and HumanResearchSurface.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import model_validator

from .authority import InvestmentAuthority, NO_INVESTMENT_AUTHORITY
from .human_surface import (
    HumanResearchSurface,
    HumanSurfaceStatus,
    build_human_surface,
)
from .market import ObservedMarket
from .odds import (
    FrozenOddsResearchArtifact,
    OddsContext,
    OddsResearchPolicy,
    build_odds_research,
)
from .primitives import AwareDateTime, DomainValidationError, KernelModel
from .rehearsal import (
    FrozenDecisionRehearsalArtifact,
    NonAuthoritativeRehearsalFraming,
    build_decision_rehearsal,
)
from .research import ResearchSnapshot


class DecisionSpineTerminalState(StrEnum):
    QUIET_INSUFFICIENT_ODDS = "QUIET_INSUFFICIENT_ODDS"
    HUMAN_ATTENTION_REQUIRED = "HUMAN_ATTENTION_REQUIRED"


class DecisionSpineResult(KernelModel):
    terminal_state: DecisionSpineTerminalState
    odds: FrozenOddsResearchArtifact
    rehearsal: FrozenDecisionRehearsalArtifact
    human_surface: HumanResearchSurface
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY

    @model_validator(mode="after")
    def validate_terminal_state(self) -> "DecisionSpineResult":
        expected = (
            DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
            if self.human_surface.attention_eligible
            else DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS
        )
        if self.terminal_state is not expected:
            raise ValueError("workflow terminal state must match HumanResearchSurface")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("decision workflow cannot gain investment authority")
        return self


def run_decision_spine(
    *,
    research_snapshot: ResearchSnapshot,
    observed_market: ObservedMarket,
    odds_policy: OddsResearchPolicy,
    odds_artifact_id: UUID,
    odds_created_at: AwareDateTime,
    rehearsal_artifact_id: UUID,
    rehearsal_created_at: AwareDateTime,
    framing: NonAuthoritativeRehearsalFraming,
    odds_context: OddsContext | None = None,
) -> DecisionSpineResult:
    """Compose proven decision modules without owning research-method judgments."""

    odds = build_odds_research(
        artifact_id=odds_artifact_id,
        created_at=odds_created_at,
        research_snapshot=research_snapshot,
        observed_market=observed_market,
        policy=odds_policy,
        odds_context=odds_context,
    )
    rehearsal = build_decision_rehearsal(
        artifact_id=rehearsal_artifact_id,
        created_at=rehearsal_created_at,
        research_snapshot=research_snapshot,
        odds_research=odds,
        framing=framing,
    )
    human_surface = build_human_surface(rehearsal, odds)

    if human_surface.status is HumanSurfaceStatus.DECISION_WORTHY_REVIEW:
        terminal_state = DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    elif human_surface.status is HumanSurfaceStatus.NOT_ELIGIBLE_INSUFFICIENT_ODDS:
        terminal_state = DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS
    else:
        raise DomainValidationError("unsupported HumanResearchSurface status")

    return DecisionSpineResult(
        terminal_state=terminal_state,
        odds=odds,
        rehearsal=rehearsal,
        human_surface=human_surface,
    )
