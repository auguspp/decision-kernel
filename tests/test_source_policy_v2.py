from decision_kernel.research_funnel import ResearchClaimKind
from decision_kernel.source_policy_v2 import (
    AssertionScope,
    SourceEpistemicRole,
    is_source_use_admissible,
)


def test_analyst_model_cannot_promote_forecast_to_fact() -> None:
    assert not is_source_use_admissible(
        claim_kind=ResearchClaimKind.FACT,
        source_role=SourceEpistemicRole.ANALYST_MODEL,
        assertion_scope=AssertionScope.MODEL_FORECAST,
    )
    assert is_source_use_admissible(
        claim_kind=ResearchClaimKind.MARKET_CONTEXT,
        source_role=SourceEpistemicRole.ANALYST_MODEL,
        assertion_scope=AssertionScope.MODEL_FORECAST,
    )


def test_primary_statement_proves_the_statement_not_the_future_outcome() -> None:
    assert is_source_use_admissible(
        claim_kind=ResearchClaimKind.FACT,
        source_role=SourceEpistemicRole.PRIMARY_STATEMENT,
        assertion_scope=AssertionScope.ATTRIBUTED_STATEMENT,
    )
    assert not is_source_use_admissible(
        claim_kind=ResearchClaimKind.FACT,
        source_role=SourceEpistemicRole.PRIMARY_STATEMENT,
        assertion_scope=AssertionScope.REALIZED_OUTCOME,
    )


def test_primary_realized_supports_realized_fact_and_market_context() -> None:
    assert is_source_use_admissible(
        claim_kind=ResearchClaimKind.FACT,
        source_role=SourceEpistemicRole.PRIMARY_REALIZED,
        assertion_scope=AssertionScope.REALIZED_OUTCOME,
    )
    assert is_source_use_admissible(
        claim_kind=ResearchClaimKind.MARKET_CONTEXT,
        source_role=SourceEpistemicRole.PRIMARY_REALIZED,
        assertion_scope=AssertionScope.REALIZED_OUTCOME,
    )


def test_analyst_target_price_is_opinion_not_fact() -> None:
    assert not is_source_use_admissible(
        claim_kind=ResearchClaimKind.FACT,
        source_role=SourceEpistemicRole.ANALYST_OPINION,
        assertion_scope=AssertionScope.OPINION,
    )
    assert is_source_use_admissible(
        claim_kind=ResearchClaimKind.MARKET_CONTEXT,
        source_role=SourceEpistemicRole.ANALYST_OPINION,
        assertion_scope=AssertionScope.OPINION,
    )
