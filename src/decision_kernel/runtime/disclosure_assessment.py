from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from pydantic import Field, ValidationError

from ..adapters.cninfo import reference_evidence_from_cninfo_announcement
from ..adapters.pdf_text import PagedPdfText, PdfTextStatus, extract_pdf_text
from ..evidence import EvidenceArtifact, ReplayabilityLevel, RetentionMode
from ..primitives import AwareDateTime, KernelModel
from ..research import ResearchSnapshot
from .cninfo_http import fetch_cninfo_pdf_bytes
from .disclosure_radar import DisclosureBatch
from .disclosure_receipts import CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID


_FetchPdf = Callable[..., bytes]
_ExtractPdf = Callable[[bytes], PagedPdfText]
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


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


class _SerializedResearchContext(KernelModel):
    research_snapshot_id: UUID
    research_as_of: AwareDateTime
    research_information_bundle_hash: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    core_thesis: str = Field(min_length=1)
    market_expectations_narrative: str | None = None
    model_risk_level: str = Field(min_length=1)
    model_risk_notes: str | None = None
    open_questions: tuple[str, ...]
    thesis_invalidation: tuple[str, ...]
    monitoring_triggers: tuple[str, ...]


class _SerializedAssessmentPage(KernelModel):
    page_number: int = Field(ge=1)
    text: str


class _SerializedAssessmentEvidence(KernelModel):
    announcement_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    published_at: AwareDateTime
    source_locator: str = Field(min_length=1, max_length=2048)
    evidence_artifact: EvidenceArtifact
    pdf_sha256: str = Field(pattern=_SHA256_PATTERN)
    text_sha256: str = Field(pattern=_SHA256_PATTERN)
    page_count: int = Field(ge=0)
    extracted_char_count: int = Field(ge=0)
    text_status: PdfTextStatus
    pages: tuple[_SerializedAssessmentPage, ...]


class _SerializedAssessmentPacket(KernelModel):
    source_lane: Literal["CNINFO"]
    stock_code: str = Field(pattern=r"^[0-9]{6}$")
    publication_date: date
    announcement_ids: tuple[str, ...] = Field(min_length=1)
    research_context: _SerializedResearchContext
    assessment_semantics_id: str = Field(min_length=1)
    prepared_at: AwareDateTime
    assessment_input_hash: str = Field(pattern=_SHA256_PATTERN)
    evidence: tuple[_SerializedAssessmentEvidence, ...] = Field(min_length=1)
    disclosure_assessment_status: Literal["UNASSESSED"]
    investment_authority: Literal["NONE"]


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
        artifact_id = _official_evidence_artifact_id(ticker, announcement.announcement_id)
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
    input_hash = _compute_assessment_input_hash(
        source_lane="CNINFO",
        stock_code=ticker,
        publication_date=batch.publication_date,
        announcement_ids=announcement_ids,
        research_snapshot_id=research_snapshot.id,
        research_as_of=research_snapshot.as_of_datetime,
        research_information_bundle_hash=research_snapshot.information_bundle_hash,
        core_thesis=research_snapshot.core_thesis,
        market_expectations_narrative=research_snapshot.market_expectations_narrative,
        model_risk_level=research_snapshot.model_risk_level.value,
        model_risk_notes=research_snapshot.model_risk_notes,
        open_questions=research_snapshot.open_questions,
        thesis_invalidation=research_snapshot.thesis_invalidation,
        monitoring_triggers=research_snapshot.monitoring_triggers,
        assessment_semantics_id=CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
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


def parse_disclosure_assessment_packet(raw_packet: str) -> DisclosureAssessmentPacket:
    """Parse one serialized assessment packet and re-validate its exact input identity.

    The JSON artifact is an external Harness handoff, so parsing does not trust its duplicated
    identity fields. Official Evidence identity, page-text identity, PIT clocks and the full
    assessment-input hash are all recomputed before the packet can reach semantic Research.
    """

    try:
        payload = json.loads(raw_packet)
    except json.JSONDecodeError as exc:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet must contain valid JSON"
        ) from exc
    try:
        serialized = _SerializedAssessmentPacket.model_validate(payload)
    except (ValidationError, ValueError, TypeError) as exc:
        raise DisclosureAssessmentPacketError(
            f"disclosure assessment packet is invalid: {exc}"
        ) from exc

    if serialized.assessment_semantics_id != CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet uses unsupported assessment semantics"
        )
    announcement_ids = serialized.announcement_ids
    if tuple(sorted(set(announcement_ids))) != announcement_ids:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet announcement ids must be unique and sorted"
        )
    evidence_ids = tuple(item.announcement_id for item in serialized.evidence)
    if evidence_ids != announcement_ids:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet Evidence must match the exact announcement set"
        )

    evidence_items: list[DisclosureAssessmentEvidence] = []
    for item in serialized.evidence:
        _validate_serialized_evidence(
            stock_code=serialized.stock_code,
            publication_date=serialized.publication_date,
            prepared_at=serialized.prepared_at,
            item=item,
        )
        evidence_items.append(
            DisclosureAssessmentEvidence(
                announcement_id=item.announcement_id,
                title=item.title,
                published_at=item.published_at,
                source_locator=item.source_locator,
                evidence_artifact=item.evidence_artifact,
                pdf_sha256=item.pdf_sha256,
                text_sha256=item.text_sha256,
                page_count=item.page_count,
                extracted_char_count=item.extracted_char_count,
                text_status=item.text_status,
                pages=tuple(
                    DisclosureAssessmentPage(
                        page_number=page.page_number,
                        text=page.text,
                    )
                    for page in item.pages
                ),
            )
        )

    evidence = tuple(evidence_items)
    if max(item.published_at for item in evidence) <= serialized.research_context.research_as_of:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet is already covered by frozen Research"
        )
    if max(item.published_at for item in evidence) > serialized.prepared_at:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet was prepared before official publication"
        )

    context = serialized.research_context
    expected_hash = _compute_assessment_input_hash(
        source_lane=serialized.source_lane,
        stock_code=serialized.stock_code,
        publication_date=serialized.publication_date,
        announcement_ids=announcement_ids,
        research_snapshot_id=context.research_snapshot_id,
        research_as_of=context.research_as_of,
        research_information_bundle_hash=context.research_information_bundle_hash,
        core_thesis=context.core_thesis,
        market_expectations_narrative=context.market_expectations_narrative,
        model_risk_level=context.model_risk_level,
        model_risk_notes=context.model_risk_notes,
        open_questions=context.open_questions,
        thesis_invalidation=context.thesis_invalidation,
        monitoring_triggers=context.monitoring_triggers,
        assessment_semantics_id=serialized.assessment_semantics_id,
        evidence=evidence,
    )
    if expected_hash != serialized.assessment_input_hash:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment packet input hash does not match its exact Research/Evidence state"
        )

    return DisclosureAssessmentPacket(
        source_lane=serialized.source_lane,
        stock_code=serialized.stock_code,
        publication_date=serialized.publication_date,
        announcement_ids=announcement_ids,
        research_snapshot_id=context.research_snapshot_id,
        research_as_of=context.research_as_of,
        research_information_bundle_hash=context.research_information_bundle_hash,
        assessment_semantics_id=serialized.assessment_semantics_id,
        prepared_at=serialized.prepared_at,
        core_thesis=context.core_thesis,
        market_expectations_narrative=context.market_expectations_narrative,
        model_risk_level=context.model_risk_level,
        model_risk_notes=context.model_risk_notes,
        open_questions=context.open_questions,
        thesis_invalidation=context.thesis_invalidation,
        monitoring_triggers=context.monitoring_triggers,
        evidence=evidence,
        assessment_input_hash=serialized.assessment_input_hash,
    )


def _validate_serialized_evidence(
    *,
    stock_code: str,
    publication_date: date,
    prepared_at: datetime,
    item: _SerializedAssessmentEvidence,
) -> None:
    if item.published_at.astimezone(_SHANGHAI).date() != publication_date:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence publication date does not match its batch"
        )
    if item.source_locator != item.evidence_artifact.source_locator:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence locator does not match its EvidenceArtifact"
        )
    if item.page_count != len(item.pages):
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence page count does not match its pages"
        )
    if tuple(page.page_number for page in item.pages) != tuple(range(1, item.page_count + 1)):
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence pages must be complete and sequential"
        )
    if item.extracted_char_count != sum(len(page.text) for page in item.pages):
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence character count does not match page text"
        )
    expected_text_hash = _page_text_sha256(item.pages)
    if item.text_sha256 != expected_text_hash:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence text hash does not match page text"
        )
    expected_status = (
        PdfTextStatus.EXTRACTED
        if any(page.text for page in item.pages)
        else PdfTextStatus.NO_TEXT
    )
    if item.text_status is not expected_status:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment Evidence text status does not match page text"
        )

    artifact = item.evidence_artifact
    expected_artifact_id = _official_evidence_artifact_id(stock_code, item.announcement_id)
    source_identifier = f"CNINFO:{stock_code}:ANNOUNCEMENT:{item.announcement_id}"
    if artifact.id != expected_artifact_id:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact id does not match announcement identity"
        )
    if artifact.source_type != "OFFICIAL_DISCLOSURE":
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact must remain an official disclosure"
        )
    if artifact.source_identifier != source_identifier or artifact.idempotency_key != source_identifier:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact source identity does not match announcement"
        )
    if artifact.published_at != item.published_at or artifact.available_at != item.published_at:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact publication/PIT identity changed"
        )
    if artifact.retrieved_at != prepared_at:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact retrieval clock changed"
        )
    if artifact.content_hash != item.pdf_sha256:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment EvidenceArtifact content hash does not match official PDF"
        )
    if artifact.retention_mode is not RetentionMode.METADATA_ONLY:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment official Evidence must remain metadata-only"
        )
    if artifact.replayability_level is not ReplayabilityLevel.REFERENCE_ONLY:
        raise DisclosureAssessmentPacketError(
            "disclosure assessment official Evidence must remain reference-only"
        )


def _official_evidence_artifact_id(stock_code: str, announcement_id: str) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"decision-kernel:CNINFO:{stock_code}:ANNOUNCEMENT:{announcement_id}",
    )


def _page_text_sha256(pages: tuple[_SerializedAssessmentPage, ...]) -> str:
    text_identity = json.dumps(
        [
            {"page_number": page.page_number, "text": page.text}
            for page in pages
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(text_identity).hexdigest()


def _compute_assessment_input_hash(
    *,
    source_lane: str,
    stock_code: str,
    publication_date: date,
    announcement_ids: tuple[str, ...],
    research_snapshot_id: UUID,
    research_as_of: datetime,
    research_information_bundle_hash: str | None,
    core_thesis: str,
    market_expectations_narrative: str | None,
    model_risk_level: str,
    model_risk_notes: str | None,
    open_questions: tuple[str, ...],
    thesis_invalidation: tuple[str, ...],
    monitoring_triggers: tuple[str, ...],
    assessment_semantics_id: str,
    evidence: tuple[DisclosureAssessmentEvidence, ...],
) -> str:
    payload = {
        "source_lane": source_lane,
        "stock_code": stock_code,
        "publication_date": publication_date.isoformat(),
        "announcement_ids": list(announcement_ids),
        "research": {
            "snapshot_id": str(research_snapshot_id),
            "as_of": research_as_of.isoformat(),
            "information_bundle_hash": research_information_bundle_hash,
            "core_thesis": core_thesis,
            "market_expectations_narrative": market_expectations_narrative,
            "model_risk_level": model_risk_level,
            "model_risk_notes": model_risk_notes,
            "open_questions": list(open_questions),
            "thesis_invalidation": list(thesis_invalidation),
            "monitoring_triggers": list(monitoring_triggers),
        },
        "assessment_semantics_id": assessment_semantics_id,
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
