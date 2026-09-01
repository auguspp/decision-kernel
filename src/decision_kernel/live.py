"""Default executable composition root for the current live path.

This module may wire existing capabilities: security-id mapping, the default
Odds policy, a supplied market fetch capability, and the Decision Spine. It
must not become an operating system. Provider fallback, retry/backoff,
scheduling, persistence, research routing, Radar logic, notifications, and
similar runtime policy belong outside this composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import model_validator

from .adapters.hithink import to_hithink_thscode
from .authority import InvestmentAuthority, NO_INVESTMENT_AUTHORITY
from .deep_research import DeepResearchPackage
from .market import ObservedMarket
from .policy import load_live_odds_v0_1
from .rehearsal import NonAuthoritativeRehearsalFraming
from .research_commit import (
    ResearchCommitPackage,
    ResearchCommitResult,
    commit_research_package,
)
from .research_workflow_v1 import DeepenedDecisionResult, run_deepened_decision_path
from .primitives import KernelModel
from .workflow import DecisionSpineResult, run_decision_spine


MarketFetcher = Callable[..., ObservedMarket]


class LiveResearchDecisionResult(KernelModel):
    research_commit: ResearchCommitResult
    decision: DecisionSpineResult
    investment_authority: InvestmentAuthority = NO_INVESTMENT_AUTHORITY

    @model_validator(mode="after")
    def validate_exact_handoff(self) -> "LiveResearchDecisionResult":
        snapshot = self.research_commit.research_snapshot
        odds = self.decision.odds.artifact
        if odds.research_snapshot_id != snapshot.id:
            raise ValueError("Decision Spine must use the generic committed ResearchSnapshot")
        if odds.research_information_bundle_hash != snapshot.information_bundle_hash:
            raise ValueError("Decision Spine must preserve generic research information identity")
        if self.investment_authority != NO_INVESTMENT_AUTHORITY:
            raise ValueError("generic live research path cannot gain investment authority")
        return self


def _resolve_observed_at(observed_at: datetime | None) -> datetime:
    resolved = observed_at or datetime.now(timezone.utc)
    if resolved.tzinfo is None or resolved.utcoffset() is None:
        raise ValueError("live observed_at must be timezone-aware")
    return resolved


def run_live_research_commit_package(
    *,
    package: ResearchCommitPackage,
    fetch_market: MarketFetcher,
    observed_at: datetime | None = None,
) -> LiveResearchDecisionResult:
    """Wire a generic reviewed research handoff into the live Decision Spine."""

    observed_at = _resolve_observed_at(observed_at)
    research_commit = commit_research_package(package)
    snapshot = research_commit.research_snapshot
    thscode = to_hithink_thscode(ticker=snapshot.ticker, exchange=snapshot.exchange)
    market = fetch_market(thscode=thscode, observed_at=observed_at)
    decision_created_at = max(
        observed_at.astimezone(timezone.utc),
        package.proposed_committed_at.astimezone(timezone.utc),
    )
    decision = run_decision_spine(
        research_snapshot=snapshot,
        observed_market=market,
        odds_policy=load_live_odds_v0_1(),
        odds_artifact_id=uuid4(),
        odds_created_at=decision_created_at,
        rehearsal_artifact_id=uuid4(),
        rehearsal_created_at=decision_created_at,
        framing=package.framing,
    )
    return LiveResearchDecisionResult(
        research_commit=research_commit,
        decision=decision,
    )


def run_live_deep_research_package(
    *,
    package: DeepResearchPackage,
    fetch_market: MarketFetcher,
    observed_at: datetime | None = None,
) -> DeepenedDecisionResult:
    """Wire Research Method v1 output into the live Decision Spine."""

    observed_at = _resolve_observed_at(observed_at)
    snapshot = package.research_snapshot
    thscode = to_hithink_thscode(ticker=snapshot.ticker, exchange=snapshot.exchange)
    market = fetch_market(thscode=thscode, observed_at=observed_at)
    policy = load_live_odds_v0_1()

    decision_created_at = max(
        observed_at.astimezone(timezone.utc),
        package.proposed_committed_at.astimezone(timezone.utc),
    )
    expression = package.discovery.current_market_expression
    framing = NonAuthoritativeRehearsalFraming(
        why_now=package.discovery.why_now,
        current_expression=(
            expression.strip()
            if expression is not None and expression.strip()
            else "research review only; no trade instruction"
        ),
    )

    return run_deepened_decision_path(
        deep_research_package=package,
        observed_market=market,
        odds_policy=policy,
        odds_artifact_id=uuid4(),
        odds_created_at=decision_created_at,
        rehearsal_artifact_id=uuid4(),
        rehearsal_created_at=decision_created_at,
        framing=framing,
    )
