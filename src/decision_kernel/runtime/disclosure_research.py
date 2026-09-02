from __future__ import annotations

from pydantic import Field

from ..evidence import EvidenceArtifact
from ..primitives import DomainValidationError, KernelModel
from ..research_funnel import DiscoveryInput, PreResearchResult, QuickResearchResult
from ..research_workflow_v1 import ResearchFunnelResult, run_research_funnel
from .disclosure_assessment import DisclosureAssessmentPacket


class DisclosureResearchAssessment(KernelModel):
    """External Research Method v1 output bound to one exact disclosure assessment input.

    The semantic producer supplies the existing Discovery / Pre / optional Quick objects rather
    than inventing a Radar-specific route. Supplemental evidence is allowed for Research
    enrichment, but terminal state and investment authority remain owned by the existing funnel.
    """

    assessment_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    discovery: DiscoveryInput
    pre_research: PreResearchResult
    quick_research: QuickResearchResult | None = None
    supplemental_evidence_artifacts: tuple[EvidenceArtifact, ...] = ()
    schema_version: int = Field(default=1, ge=1)


def run_disclosure_research_assessment(
    *,
    packet: DisclosureAssessmentPacket,
    assessment: DisclosureResearchAssessment,
) -> ResearchFunnelResult:
    """Validate an external semantic assessment and reuse Research Method v1 routing unchanged."""

    if assessment.assessment_input_hash != packet.assessment_input_hash:
        raise DomainValidationError(
            "disclosure Research assessment does not reference the exact assessment input"
        )

    discovery = assessment.discovery
    if discovery.source_lane != packet.source_lane:
        raise DomainValidationError(
            "disclosure Research assessment changed the official source lane"
        )
    if discovery.ticker != packet.stock_code:
        raise DomainValidationError(
            "disclosure Research assessment changed the frozen Research security"
        )
    if discovery.as_of != packet.prepared_at:
        raise DomainValidationError(
            "disclosure Research assessment changed the packet PIT cutoff"
        )

    packet_evidence = tuple(item.evidence_artifact for item in packet.evidence)
    packet_evidence_ids = {artifact.id for artifact in packet_evidence}
    discovery_evidence_ids = {
        source.evidence_artifact_id for source in discovery.source_lineage
    }
    if discovery_evidence_ids != packet_evidence_ids:
        raise DomainValidationError(
            "disclosure Discovery must preserve the exact official Evidence batch"
        )

    supplemental = assessment.supplemental_evidence_artifacts
    supplemental_ids = {artifact.id for artifact in supplemental}
    if len(supplemental_ids) != len(supplemental):
        raise DomainValidationError(
            "disclosure Research supplemental Evidence ids must be unique"
        )
    overlap = packet_evidence_ids & supplemental_ids
    if overlap:
        raise DomainValidationError(
            "disclosure Research supplemental Evidence cannot replace packet Evidence"
        )

    return run_research_funnel(
        discovery=discovery,
        pre_research=assessment.pre_research,
        quick_research=assessment.quick_research,
        evidence_artifacts=packet_evidence + supplemental,
    )
