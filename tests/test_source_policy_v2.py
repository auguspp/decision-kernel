from decision_kernel.research_funnel import ResearchClaimKind
from decision_kernel.source_policy_v2 import (
    AssertionScope,
    SourceEpistemicRole,
    is_source_role_compatible_with_artifact,
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


def test_artifact_type_cannot_be_relabelled_into_primary_truth() -> None:
    assert is_source_role_compatible_with_artifact(
        source_type="MARKET_CONSENSUS",
        source_role=SourceEpistemicRole.MARKET_EXPECTATION,
    )
    assert not is_source_role_compatible_with_artifact(
        source_type="MARKET_CONSENSUS",
        source_role=SourceEpistemicRole.PRIMARY_REALIZED,
    )
    assert is_source_role_compatible_with_artifact(
        source_type="SELL_SIDE_RESEARCH",
        source_role=SourceEpistemicRole.ANALYST_MODEL,
    )
    assert not is_source_role_compatible_with_artifact(
        source_type="SELL_SIDE_RESEARCH",
        source_role=SourceEpistemicRole.PRIMARY_REALIZED,
    )


def test_unknown_source_type_fails_closed() -> None:
    assert not is_source_role_compatible_with_artifact(
        source_type="MYSTERY_SOURCE",
        source_role=SourceEpistemicRole.PRIMARY_REALIZED,
    )
