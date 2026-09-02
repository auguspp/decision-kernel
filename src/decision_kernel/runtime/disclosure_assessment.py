from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from ..adapters.cninfo import reference_evidence_from_cninfo_announcement
from ..adapters.pdf_text import PagedPdfText, PdfTextStatus, extract_pdf_text
from ..evidence import EvidenceArtifact
from ..research import ResearchSnapshot
from .cninfo_http import fetch_cninfo_pdf_bytes
from .disclosure_radar import DisclosureBatch
from .disclosure_receipts import CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID


_FetchPdf = Callable[..., bytes]
_ExtractPdf = Callable[[bytes], PagedPdfText]


class DisclosureAssessmentPacketError(ValueError):
    """A disclosure batch cannot become one auditable Research assessment input."""


@dataclass(frozen=True)
class DisclosureAssessmentPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class DisclosureAssessmentEvidence:
    announcement_id: str
    title: str
    published_at: datetime
    source_locator: str
    evidence_artifact: EvidenceArtifact
    pdf_sha256: str
    text_sha256: str
    page_count: int
    extracted_char_count: int
    text_status: PdfTextStatus
    pages: tuple[DisclosureAssessmentPage, ...]


@dataclass(frozen=True)
class DisclosureAssessmentPacket:
    """Harness handoff for semantic Research assessment of one exact official batch.

    This packet carries frozen Research context plus exact official Evidence text. It has no
    Recommendation, Human wake, Research commit, Odds, or investment authority semantics.
    """

    source_lane: str
    stock_code: str
    publication_date: date
    announcement_ids: tuple[str, ...]
    research_snapshot_id: UUID
    research_as_of: datetime
    research_information_bundle_hash: str | None
    assessment_semantics_id: str
    prepared_at: datetime
    core_thesis: str
    market_expectations_narrative: str | None
    model_risk_level: str
    model_risk_notes: str | None
    open_questions: tuple[str, ...]
    thesis_invalidation: tuple[str, ...]
    monitoring_triggers: tuple[str, ...]
    evidence: tuple[DisclosureAssessmentEvidence, ...]
    assessment_input_hash: str


def prepare_disclosure_assessment_packet(
    *,
    research_snapshot: ResearchSnapshot,
    batch: DisclosureBatch,
    prepared_at: datetime,
    fetch_pdf: _FetchPdf = fetch_cninfo_pdf_bytes,
    extract_pdf: _ExtractPdf = extract_pdf_text,
) -> DisclosureAssessmentPacket:
    """Prepare one exact CNINFO batch for an external semantic Research producer.

    Acquisition and deterministic Evidence qualification happen here. Interpreting the text and
    choosing WAIT / DROP / CONTINUE remain Research Method responsibilities outside this module.
    """

    if prepared_at.utcoffset() is None:
        raise DisclosureAssessmentPacketError("disclosure assessment prepared_at must be aware")
    ticker = research_snapshot.ticker.strip()
    if batch.stock_code != ticker:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment batch must belong to the frozen Research security"
        )
    if batch.last_published_at <= research_snapshot.as_of_datetime:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment batch is already covered by frozen Research"
        )
    if prepared_at < batch.last_published_at:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet cannot be prepared before official publication"
        )

    ordered_announcements = tuple(
        sorted(batch.announcements, key=lambda item: item.announcement_id)
    )
    announcement_ids = tuple(item.announcement_id for item in ordered_announcements)
    if announcement_ids != tuple(sorted(set(announcement_ids))):
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet requires unique announcement ids"
        )

    evidence_items: list[DisclosureAssessmentEvidence] = []
    for announcement in ordered_announcements:
        pdf_bytes = fetch_pdf(source_locator=announcement.source_locator)
        extracted = extract_pdf(pdf_bytes)
        artifact_id = uuid5(
            NAMESPACE_URL,
            f"decision-kernel:CNINFO:{ticker}:ANNOUNCEMENT:{announcement.announcement_id}",
        )
        evidence_artifact = reference_evidence_from_cninfo_announcement(
            announcement,
            artifact_id=artifact_id,
            pdf_sha256=extracted.pdf_sha256,
            retrieved_at=prepared_at,
        )
        published_at = announcement.published_at
        if published_at is None or published_at.utcoffset() is None:
            raise DisclosureAssessmentPacketError(
                "disclosure assessment Evidence requires an aware publication timestamp"
            )
        evidence_items.append(
            DisclosureAssessmentEvidence(
                announcement_id=announcement.announcement_id,
                title=announcement.title,
                published_at=published_at,
                source_locator=announcement.source_locator,
                evidence_artifact=evidence_artifact,
                pdf_sha256=extracted.pdf_sha256,
                text_sha256=extracted.text_sha256,
                page_count=extracted.page_count,
                extracted_char_count=extracted.extracted_char_count,
                text_status=extracted.status,
                pages=tuple(
                    DisclosureAssessmentPage(
                        page_number=page.page_number,
                        text=page.text,
                    )
                    for page in extracted.pages
                ),
            )
        )

    evidence = tuple(evidence_items)
    input_hash = _assessment_input_hash(
        research_snapshot=research_snapshot,
        batch=batch,
        announcement_ids=announcement_ids,
        evidence=evidence,
    )
    return DisclosureAssessmentPacket(
        source_lane="CNINFO",
        stock_code=ticker,
        publication_date=batch.publication_date,
        announcement_ids=announcement_ids,
        research_snapshot_id=research_snapshot.id,
        research_as_of=research_snapshot.as_of_datetime,
        research_information_bundle_hash=research_snapshot.information_bundle_hash,
        assessment_semantics_id=CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
        prepared_at=prepared_at,
        core_thesis=research_snapshot.core_thesis,
        market_expectations_narrative=research_snapshot.market_expectations_narrative,
        model_risk_level=research_snapshot.model_risk_level.value,
        model_risk_notes=research_snapshot.model_risk_notes,
        open_questions=research_snapshot.open_questions,
        thesis_invalidation=research_snapshot.thesis_invalidation,
        monitoring_triggers=research_snapshot.monitoring_triggers,
        evidence=evidence,
        assessment_input_hash=input_hash,
    )


def serialize_disclosure_assessment_packet(packet: DisclosureAssessmentPacket) -> str:
    """Serialize one Research-producer handoff without claiming Kernel authority."""

    payload = {
        "source_lane": packet.source_lane,
        "stock_code": packet.stock_code,
        "publication_date": packet.publication_date.isoformat(),
        "announcement_ids": list(packet.announcement_ids),
        "research_context": {
            "research_snapshot_id": str(packet.research_snapshot_id),
            "research_as_of": packet.research_as_of.isoformat(),
            "research_information_bundle_hash": packet.research_information_bundle_hash,
            "core_thesis": packet.core_thesis,
            "market_expectations_narrative": packet.market_expectations_narrative,
            "model_risk_level": packet.model_risk_level,
            "model_risk_notes": packet.model_risk_notes,
            "open_questions": list(packet.open_questions),
            "thesis_invalidation": list(packet.thesis_invalidation),
            "monitoring_triggers": list(packet.monitoring_triggers),
        },
        "assessment_semantics_id": packet.assessment_semantics_id,
        "prepared_at": packet.prepared_at.isoformat(),
        "assessment_input_hash": packet.assessment_input_hash,
        "evidence": [
            {
                "announcement_id": item.announcement_id,
                "title": item.title,
                "published_at": item.published_at.isoformat(),
                "source_locator": item.source_locator,
                "evidence_artifact": item.evidence_artifact.model_dump(mode="json"),
                "pdf_sha256": item.pdf_sha256,
                "text_sha256": item.text_sha256,
                "page_count": item.page_count,
                "extracted_char_count": item.extracted_char_count,
                "text_status": item.text_status.value,
                "pages": [
                    {"page_number": page.page_number, "text": page.text}
                    for page in item.pages
                ],
            }
            for item in packet.evidence
        ],
        "disclosure_assessment_status": "UNASSESSED",
        "investment_authority": "NONE",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _assessment_input_hash(
    *,
    research_snapshot: ResearchSnapshot,
    batch: DisclosureBatch,
    announcement_ids: tuple[str, ...],
    evidence: tuple[DisclosureAssessmentEvidence, ...],
) -> str:
    payload = {
        "source_lane": "CNINFO",
        "stock_code": research_snapshot.ticker.strip(),
        "publication_date": batch.publication_date.isoformat(),
        "announcement_ids": list(announcement_ids),
        "research": {
            "snapshot_id": str(research_snapshot.id),
            "as_of": research_snapshot.as_of_datetime.isoformat(),
            "information_bundle_hash": research_snapshot.information_bundle_hash,
            "core_thesis": research_snapshot.core_thesis,
            "market_expectations_narrative": research_snapshot.market_expectations_narrative,
            "model_risk_level": research_snapshot.model_risk_level.value,
            "model_risk_notes": research_snapshot.model_risk_notes,
            "open_questions": list(research_snapshot.open_questions),
            "thesis_invalidation": list(research_snapshot.thesis_invalidation),
            "monitoring_triggers": list(research_snapshot.monitoring_triggers),
        },
        "assessment_semantics_id": CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
        "evidence": [
            {
                "announcement_id": item.announcement_id,
                "published_at": item.published_at.isoformat(),
                "source_locator": item.source_locator,
                "evidence_artifact_id": str(item.evidence_artifact.id),
                "pdf_sha256": item.pdf_sha256,
                "text_sha256": item.text_sha256,
            }
            for item in evidence
        ],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
