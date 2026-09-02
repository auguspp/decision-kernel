from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .primitives import KernelModel
from .research_funnel import ResearchClaimKind


SOURCE_POLICY_V2_VERSION = "research-source-admissibility-v2"


class SourceEpistemicRole(StrEnum):
    """Method-side role of a source in the epistemic chain.

    This deliberately does not live on EvidenceArtifact: EvidenceArtifact freezes
    identity/PIT/replayability, while Research Method decides what a source may
    legitimately support.
    """

    PRIMARY_REALIZED = "PRIMARY_REALIZED"
    PRIMARY_STATEMENT = "PRIMARY_STATEMENT"
    SECONDARY_OBSERVATION = "SECONDARY_OBSERVATION"
    MARKET_EXPECTATION = "MARKET_EXPECTATION"
    ANALYST_MODEL = "ANALYST_MODEL"
    ANALYST_OPINION = "ANALYST_OPINION"


class AssertionScope(StrEnum):
    REALIZED_OUTCOME = "REALIZED_OUTCOME"
    ATTRIBUTED_STATEMENT = "ATTRIBUTED_STATEMENT"
    ATTRIBUTED_SECONDARY_OBSERVATION = "ATTRIBUTED_SECONDARY_OBSERVATION"
    MARKET_EXPECTATION = "MARKET_EXPECTATION"
    MODEL_FORECAST = "MODEL_FORECAST"
    OPINION = "OPINION"


class ClaimSourceUseV2(KernelModel):
    evidence_artifact_id: str = Field(min_length=1, max_length=64)
    source_role: SourceEpistemicRole
    assertion_scope: AssertionScope
    role_basis: str = Field(min_length=1)


def is_source_use_admissible(
    *,
    claim_kind: ResearchClaimKind,
    source_role: SourceEpistemicRole,
    assertion_scope: AssertionScope,
) -> bool:
    """Return whether one declared source use may support a claim kind.

    This is intentionally categorical rather than a pseudo-precise credibility
    score. It answers qualification, not truth probability.
    """

    if claim_kind is ResearchClaimKind.FACT:
        return (source_role, assertion_scope) in {
            (SourceEpistemicRole.PRIMARY_REALIZED, AssertionScope.REALIZED_OUTCOME),
            (SourceEpistemicRole.PRIMARY_STATEMENT, AssertionScope.ATTRIBUTED_STATEMENT),
            (
                SourceEpistemicRole.SECONDARY_OBSERVATION,
                AssertionScope.ATTRIBUTED_SECONDARY_OBSERVATION,
            ),
        }

    if claim_kind is ResearchClaimKind.MARKET_CONTEXT:
        return (source_role, assertion_scope) in {
            (SourceEpistemicRole.MARKET_EXPECTATION, AssertionScope.MARKET_EXPECTATION),
            (SourceEpistemicRole.ANALYST_MODEL, AssertionScope.MODEL_FORECAST),
            (SourceEpistemicRole.ANALYST_OPINION, AssertionScope.OPINION),
            (SourceEpistemicRole.PRIMARY_STATEMENT, AssertionScope.ATTRIBUTED_STATEMENT),
            (
                SourceEpistemicRole.SECONDARY_OBSERVATION,
                AssertionScope.ATTRIBUTED_SECONDARY_OBSERVATION,
            ),
        }

    # INFERENCE and ASSUMPTION are Research-owned cognition rather than source
    # truth claims. Their quality is governed by explicit reasoning, scenario
    # assumptions and falsifiers; source qualification does not promote them to
    # facts.
    return claim_kind in {ResearchClaimKind.INFERENCE, ResearchClaimKind.ASSUMPTION}
