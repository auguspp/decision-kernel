from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.adapters.pdf_text import PagedPdfText, PdfPageText, PdfTextStatus
from decision_kernel.evidence import EvidenceArtifact, ReplayabilityLevel, RetentionMode
from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.research_funnel import (
    DiscoveryInput,
    DiscoveryObservation,
    DiscoverySource,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    QuickResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState
from decision_kernel.runtime.disclosure_assessment import prepare_disclosure_assessment_packet
from decision_kernel.runtime.disclosure_radar import DisclosureBatch
from decision_kernel.runtime.disclosure_research import (
    DisclosureResearchAssessment,
    run_disclosure_research_assessment,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
PREPARED_AT = datetime(2026, 9, 2, 6, 0, tzinfo=timezone.utc)


def _snapshot():
    return ResearchCommitPackage.model_validate_json(
        Path("dogfood/300750-catl.json").read_text(encoding="utf-8")
    ).research_snapshot


def _announcement(identifier: str, minute: int = 48) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="300750",
        org_id="9900025790",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=datetime(2026, 8, 27, 17, minute, 11, tzinfo=SHANGHAI),
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-27/{identifier}.PDF",
    )


def _packet(*announcements: CninfoAnnouncement):
    ordered = tuple(sorted(announcements, key=lambda item: item.published_at))
    batch = DisclosureBatch(
        stock_code="300750",
        publication_date=date(2026, 8, 27),
        first_published_at=ordered[0].published_at,
        last_published_at=ordered[-1].published_at,
        announcements=ordered,
    )

    def fetch_pdf(*, source_locator: str) -> bytes:
        return source_locator.encode("utf-8")

    def extract_pdf(payload: bytes) -> PagedPdfText:
        identifier = payload.decode("utf-8").split("/")[-1].split(".")[0]
        fill = "a" if identifier.endswith("1") else "b"
        return PagedPdfText(
            pdf_sha256=fill * 64,
            text_sha256=("c" if fill == "a" else "d") * 64,
            page_count=1,
            extracted_char_count=8,
            status=PdfTextStatus.EXTRACTED,
            pages=(PdfPageText(page_number=1, text=f"正文 {identifier}"),),
        )

    return prepare_disclosure_assessment_packet(
        research_snapshot=_snapshot(),
        batch=batch,
        prepared_at=PREPARED_AT,
        fetch_pdf=fetch_pdf,
        extract_pdf=extract_pdf,
    )


def _discovery(packet, *, include_all_packet_evidence: bool = True) -> DiscoveryInput:
    evidence = packet.evidence if include_all_packet_evidence else packet.evidence[:1]
    ids = tuple(item.evidence_artifact.id for item in evidence)
    return DiscoveryInput(
        discovery_id=f"CNINFO:{packet.stock_code}:{packet.publication_date.isoformat()}",
        source_lane="CNINFO",
        ticker=packet.stock_code,
        economic_direction="test whether the official disclosure changes frozen Research",
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement="new official disclosure batch requires semantic assessment",
                evidence_artifact_ids=ids,
            ),
        ),
        source_lineage=tuple(
            DiscoverySource(
                evidence_artifact_id=item.evidence_artifact.id,
                source_locator=item.evidence_artifact.source_locator,
                available_at=item.evidence_artifact.available_at,
            )
            for item in evidence
        ),
        why_now="official evidence is newer than frozen Research",
        next_discriminating_search="compare the disclosure with the frozen open questions",
        known_stop_or_downgrade_condition="stop if it does not change a decision-relevant context",
    )


def _pre(packet, discovery: DiscoveryInput, *, route: PreResearchRoute) -> PreResearchResult:
    primary = packet.evidence[0].evidence_artifact
    return PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=discovery.as_of,
        what_is_this="an official company disclosure",
        economic_direction="possible update to the frozen company research",
        why_surfaced_now="the official batch is newer than frozen Research",
        basic_business_role="operating company",
        potential_fundamental_driver="capital allocation or operating evidence",
        current_market_expectation_hypothesis="the market may already expect the disclosed action",
        material_claims=(
            ResearchClaim(
                statement="the company published the official disclosure",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(primary.id,),
            ),
        ),
        largest_unknown="whether the disclosure changes the core research questions",
        next_discriminating_search="look for corroborating operational evidence",
        route=route,
        route_reason=f"route={route.value}",
    )


def _supplemental(*, available_at: datetime | None = None) -> EvidenceArtifact:
    evidence_id = uuid4()
    available = available_at or PREPARED_AT - timedelta(hours=2)
    return EvidenceArtifact(
        id=evidence_id,
        source_type="research_reference",
        source_identifier=str(evidence_id),
        source_locator=f"https://example.test/{evidence_id}",
        published_at=available - timedelta(minutes=5),
        available_at=available,
        retrieved_at=max(PREPARED_AT, available),
        content_hash="e" * 64,
        idempotency_key=str(evidence_id),
        retention_mode=RetentionMode.METADATA_ONLY,
        replayability_level=ReplayabilityLevel.REFERENCE_ONLY,
        raw_storage_ref=None,
    )


def test_external_wait_reuses_existing_funnel_and_keeps_authority_none() -> None:
    packet = _packet(_announcement("1225519101"))
    discovery = _discovery(packet)
    pre = _pre(packet, discovery, route=PreResearchRoute.WAIT_FOR_TRIGGER)
    assessment = DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
    )

    result = run_disclosure_research_assessment(packet=packet, assessment=assessment)

    assert result.terminal_state is ResearchFunnelTerminalState.WAIT_FOR_TRIGGER
    assert result.pre_research is pre
    assert result.quick_research is None
    assert result.investment_authority == "NONE"


def test_external_assessment_must_bind_exact_packet_input_hash() -> None:
    packet = _packet(_announcement("1225519101"))
    discovery = _discovery(packet)
    assessment = DisclosureResearchAssessment(
        assessment_input_hash="f" * 64,
        discovery=discovery,
        pre_research=_pre(packet, discovery, route=PreResearchRoute.WAIT_FOR_TRIGGER),
    )

    with pytest.raises(DomainValidationError, match="exact assessment input"):
        run_disclosure_research_assessment(packet=packet, assessment=assessment)


def test_discovery_cannot_drop_one_announcement_from_exact_official_batch() -> None:
    packet = _packet(_announcement("1225519101"), _announcement("1225519102", minute=49))
    discovery = _discovery(packet, include_all_packet_evidence=False)
    assessment = DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=_pre(packet, discovery, route=PreResearchRoute.WAIT_FOR_TRIGGER),
    )

    with pytest.raises(DomainValidationError, match="exact official Evidence batch"):
        run_disclosure_research_assessment(packet=packet, assessment=assessment)


def test_quick_research_can_add_supplemental_evidence_without_new_routing_semantics() -> None:
    packet = _packet(_announcement("1225519101"))
    discovery = _discovery(packet)
    pre = _pre(packet, discovery, route=PreResearchRoute.CONTINUE_TO_QUICK)
    official = packet.evidence[0].evidence_artifact
    contrary = _supplemental()
    quick = QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=discovery.as_of,
        business_model="battery manufacturer",
        segment_mix="battery systems and related businesses",
        economic_role="scaled battery supplier",
        major_profit_drivers=("utilization", "pricing", "mix"),
        industry_supply_demand_variables=("capacity", "EV demand", "storage demand"),
        value_chain_position="battery cell and system producer",
        market_expectation_hypothesis="market expects continued scale and cash generation",
        supporting_claims=(
            ResearchClaim(
                statement="the official filing confirms the disclosed corporate action",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(official.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="supplemental evidence leaves an unresolved counterpoint",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(contrary.id,),
            ),
        ),
        evidence_authority_assessment="official filing plus bounded supplemental reference",
        variant_perception="the disclosed action may matter only if later operating evidence confirms it",
        unresolved_questions=("does execution change cash conversion?",),
        next_discriminating_evidence=("actual execution and next operating disclosure",),
        route=QuickResearchRoute.DEEPEN,
        route_reason="the existing funnel requires deeper research",
    )
    assessment = DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        supplemental_evidence_artifacts=(contrary,),
    )

    result = run_disclosure_research_assessment(packet=packet, assessment=assessment)

    assert result.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED
    assert result.quick_research is quick
    assert result.investment_authority == "NONE"


def test_supplemental_evidence_still_cannot_leak_past_packet_pit() -> None:
    packet = _packet(_announcement("1225519101"))
    discovery = _discovery(packet)
    pre = _pre(packet, discovery, route=PreResearchRoute.CONTINUE_TO_QUICK)
    official = packet.evidence[0].evidence_artifact
    future = _supplemental(available_at=PREPARED_AT + timedelta(minutes=1))
    quick = QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=discovery.as_of,
        business_model="battery manufacturer",
        segment_mix="battery systems",
        economic_role="battery producer",
        major_profit_drivers=("utilization",),
        industry_supply_demand_variables=("capacity",),
        value_chain_position="producer",
        market_expectation_hypothesis="market expects continued growth",
        supporting_claims=(
            ResearchClaim(
                statement="official disclosure exists",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(official.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="future market context",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(future.id,),
            ),
        ),
        evidence_authority_assessment="mixed",
        variant_perception="test",
        unresolved_questions=("question",),
        next_discriminating_evidence=("next evidence",),
        route=QuickResearchRoute.DEEPEN,
        route_reason="needs more research",
    )
    assessment = DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        supplemental_evidence_artifacts=(future,),
    )

    with pytest.raises(DomainValidationError, match="not available at the Discovery PIT cutoff"):
        run_disclosure_research_assessment(packet=packet, assessment=assessment)
