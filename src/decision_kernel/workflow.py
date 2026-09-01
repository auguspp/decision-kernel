from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import model_validator

from .authority import InvestmentAuthority, NO_INVESTMENT_AUTHORITY
from .deep_research import (
    DeepResearchCommitResult,
    DeepResearchPackage,
    commit_deep_research_package,
)
from .evidence import EvidenceArtifact
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
from .research_funnel import (
    DiscoveryInput,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    QuickResearchRoute,
    validate_funnel_transition,
    validate_pre_research_transition,
)


class ResearchFunnelStage(StrEnum):
    PRE_RESEARCH = "PRE_RESEARCH"
    QUICK_RESEARCH = "QUICK_RESEARCH"


class ResearchFunnelTerminalState(StrEnum):
    WAIT_FOR_TRIGGER = "WAIT_FOR_TRIGGER"
    DROP_FOR_NOW = "DROP_FOR_NOW"
    DEEPEN_REQUIRED = "DEEPEN_REQUIRED"


class ResearchFunnelResult(KernelModel):
    terminal_state: ResearchFunnelTerminalState
    terminal_stage: ResearchFunnelStage
    terminal_reason: str
    discovery: DiscoveryInput
    pre_research: PreResearchResult
    quick_research: QuickResearchResult | None = None
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY

    @model_validator(mode="after")
    def validate_cognitive_budget_terminal(self) -> "ResearchFunnelResult":
        if self.terminal_stage is ResearchFunnelStage.PRE_RESEARCH:
            if self.quick_research is not None:
                raise ValueError("Pre-Research terminal state cannot contain Quick Research")
            expected = {
                PreResearchRoute.WAIT_FOR_TRIGGER: ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
                PreResearchRoute.STOP: ResearchFunnelTerminalState.DROP_FOR_NOW,
            }.get(self.pre_research.route)
        else:
            if self.quick_research is None:
                raise ValueError("Quick-Research terminal state requires Quick Research")
            if self.pre_research.route is not PreResearchRoute.CONTINUE_TO_QUICK:
                raise ValueError("Quick Research requires CONTINUE_TO_QUICK")
            expected = {
                QuickResearchRoute.DEEPEN: ResearchFunnelTerminalState.DEEPEN_REQUIRED,
                QuickResearchRoute.WAIT_FOR_TRIGGER: ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
                QuickResearchRoute.STOP: ResearchFunnelTerminalState.DROP_FOR_NOW,
            }[self.quick_research.route]

        if expected is None or self.terminal_state is not expected:
            raise ValueError("research funnel terminal state must match cognitive-budget route")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("research funnel cannot gain investment authority")
        return self


def run_research_funnel(
    *,
    discovery: DiscoveryInput,
    pre_research: PreResearchResult,
    evidence_artifacts: tuple[EvidenceArtifact, ...],
    quick_research: QuickResearchResult | None = None,
) -> ResearchFunnelResult:
    """Route cognitive budget without performing sensing or deep research execution."""

    validate_pre_research_transition(discovery, pre_research, evidence_artifacts)

    if pre_research.route is PreResearchRoute.WAIT_FOR_TRIGGER:
        if quick_research is not None:
            raise DomainValidationError("WAIT_FOR_TRIGGER Pre-Research cannot enter Quick Research")
        return ResearchFunnelResult(
            terminal_state=ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
            terminal_stage=ResearchFunnelStage.PRE_RESEARCH,
            terminal_reason=pre_research.route_reason,
            discovery=discovery,
            pre_research=pre_research,
        )

    if pre_research.route is PreResearchRoute.STOP:
        if quick_research is not None:
            raise DomainValidationError("STOP Pre-Research cannot enter Quick Research")
        return ResearchFunnelResult(
            terminal_state=ResearchFunnelTerminalState.DROP_FOR_NOW,
            terminal_stage=ResearchFunnelStage.PRE_RESEARCH,
            terminal_reason=pre_research.route_reason,
            discovery=discovery,
            pre_research=pre_research,
        )

    if quick_research is None:
        raise DomainValidationError("CONTINUE_TO_QUICK requires a QuickResearchResult")

    validate_funnel_transition(
        discovery,
        pre_research,
        quick_research,
        evidence_artifacts,
    )
    terminal_state = {
        QuickResearchRoute.DEEPEN: ResearchFunnelTerminalState.DEEPEN_REQUIRED,
        QuickResearchRoute.WAIT_FOR_TRIGGER: ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
        QuickResearchRoute.STOP: ResearchFunnelTerminalState.DROP_FOR_NOW,
    }[quick_research.route]
    return ResearchFunnelResult(
        terminal_state=terminal_state,
        terminal_stage=ResearchFunnelStage.QUICK_RESEARCH,
        terminal_reason=quick_research.route_reason,
        discovery=discovery,
        pre_research=pre_research,
        quick_research=quick_research,
    )


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
    """Compose the proven decision modules without owning their judgments."""

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


class DeepenedDecisionResult(KernelModel):
    research_commit: DeepResearchCommitResult
    decision: DecisionSpineResult
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY

    @model_validator(mode="after")
    def validate_exact_handoff(self) -> "DeepenedDecisionResult":
        snapshot = self.research_commit.research_snapshot
        odds = self.decision.odds.artifact
        if odds.research_snapshot_id != snapshot.id:
            raise ValueError("Decision Spine must use the committed Deep Research snapshot")
        if odds.research_information_bundle_hash != snapshot.information_bundle_hash:
            raise ValueError("Decision Spine must preserve the committed research information hash")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("Deepened decision workflow cannot gain investment authority")
        return self


def run_deepened_decision_path(
    *,
    deep_research_package: DeepResearchPackage,
    observed_market: ObservedMarket,
    odds_policy: OddsResearchPolicy,
    odds_artifact_id: UUID,
    odds_created_at: AwareDateTime,
    rehearsal_artifact_id: UUID,
    rehearsal_created_at: AwareDateTime,
    framing: NonAuthoritativeRehearsalFraming,
    odds_context: OddsContext | None = None,
) -> DeepenedDecisionResult:
    """Compose accepted Deep Research into the existing Decision Spine."""

    research_commit = commit_deep_research_package(deep_research_package)
    decision = run_decision_spine(
        research_snapshot=research_commit.research_snapshot,
        observed_market=observed_market,
        odds_policy=odds_policy,
        odds_artifact_id=odds_artifact_id,
        odds_created_at=odds_created_at,
        rehearsal_artifact_id=rehearsal_artifact_id,
        rehearsal_created_at=rehearsal_created_at,
        framing=framing,
        odds_context=odds_context,
    )
    return DeepenedDecisionResult(
        research_commit=research_commit,
        decision=decision,
    )
