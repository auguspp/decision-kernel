from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from .adapters.hithink import fetch_hithink_observed_market, to_hithink_thscode
from .deep_research import DeepResearchPackage
from .market import ObservedMarket
from .policy import load_live_odds_v0_1
from .rehearsal import NonAuthoritativeRehearsalFraming
from .workflow import DeepenedDecisionResult, run_deepened_decision_path


_MarketFetcher = Callable[..., ObservedMarket]


def run_live_deep_research_package(
    *,
    package: DeepResearchPackage,
    api_key: str | None,
    observed_at: datetime | None = None,
    fetch_market: _MarketFetcher | None = None,
) -> DeepenedDecisionResult:
    """Run one accepted Deep Research package through live price and the Decision Spine."""

    if observed_at is None:
        observed_at = datetime.now(timezone.utc)
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("live observed_at must be timezone-aware")
    if fetch_market is None:
        fetch_market = fetch_hithink_observed_market

    snapshot = package.research_snapshot
    thscode = to_hithink_thscode(ticker=snapshot.ticker, exchange=snapshot.exchange)
    market = fetch_market(
        thscode=thscode,
        observed_at=observed_at,
        api_key=api_key,
    )
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
