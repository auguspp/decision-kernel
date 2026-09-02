from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.adapters.pdf_text import PagedPdfText, PdfPageText, PdfTextStatus
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.runtime.disclosure_assessment import (
    DisclosureAssessmentPacketError,
    parse_disclosure_assessment_packet,
    prepare_disclosure_assessment_packet,
    serialize_disclosure_assessment_packet,
)
from decision_kernel.runtime.disclosure_radar import DisclosureBatch


SHANGHAI = ZoneInfo("Asia/Shanghai")
PREPARED_AT = datetime(2026, 9, 2, 6, 0, tzinfo=timezone.utc)


def _text_hash(pages: tuple[PdfPageText, ...]) -> str:
    encoded = json.dumps(
        [
            {"page_number": page.page_number, "text": page.text}
            for page in pages
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _packet_json() -> str:
    snapshot = ResearchCommitPackage.model_validate_json(
        Path("dogfood/300750-catl.json").read_text(encoding="utf-8")
    ).research_snapshot
    announcement = CninfoAnnouncement(
        announcement_id="1225519101",
        stock_code="300750",
        org_id="9900025790",
        title="关于2026年度第六期绿色科技创新债券发行完成的公告",
        announcement_type=None,
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
        source_locator="https://static.cninfo.com.cn/finalpage/2026-08-27/1225519101.PDF",
    )
    batch = DisclosureBatch(
        stock_code="300750",
        publication_date=date(2026, 8, 27),
        first_published_at=announcement.published_at,
        last_published_at=announcement.published_at,
        announcements=(announcement,),
    )
    pages = (
        PdfPageText(page_number=1, text="第一页正文A"),
        PdfPageText(page_number=2, text="第二页正文B"),
    )

    def fake_fetch(*, source_locator: str) -> bytes:
        assert source_locator == announcement.source_locator
        return b"%PDF-test"

    def fake_extract(_payload: bytes) -> PagedPdfText:
        return PagedPdfText(
            pdf_sha256="a" * 64,
            text_sha256=_text_hash(pages),
            page_count=len(pages),
            extracted_char_count=sum(len(page.text) for page in pages),
            status=PdfTextStatus.EXTRACTED,
            pages=pages,
        )

    packet = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=batch,
        prepared_at=PREPARED_AT,
        fetch_pdf=fake_fetch,
        extract_pdf=fake_extract,
    )
    return serialize_disclosure_assessment_packet(packet)


def test_serialized_packet_round_trips_with_exact_input_identity() -> None:
    raw = _packet_json()
    original = json.loads(raw)

    parsed = parse_disclosure_assessment_packet(raw)

    assert parsed.assessment_input_hash == original["assessment_input_hash"]
    assert parsed.announcement_ids == ("1225519101",)
    assert parsed.evidence[0].pdf_sha256 == "a" * 64
    assert parsed.evidence[0].text_sha256 == original["evidence"][0]["text_sha256"]
    assert serialize_disclosure_assessment_packet(parsed) == raw


def test_packet_rejects_page_text_tampering_even_when_character_count_is_unchanged() -> None:
    payload = json.loads(_packet_json())
    original_text = payload["evidence"][0]["pages"][0]["text"]
    payload["evidence"][0]["pages"][0]["text"] = original_text[:-1] + "Z"

    with pytest.raises(DisclosureAssessmentPacketError, match="text hash does not match"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))


def test_packet_rejects_tampered_assessment_input_hash() -> None:
    payload = json.loads(_packet_json())
    payload["assessment_input_hash"] = "f" * 64

    with pytest.raises(DisclosureAssessmentPacketError, match="input hash does not match"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))


def test_packet_rejects_tampered_evidence_artifact_locator() -> None:
    payload = json.loads(_packet_json())
    payload["evidence"][0]["evidence_artifact"]["source_locator"] = (
        "https://static.cninfo.com.cn/finalpage/2026-08-27/other.PDF"
    )

    with pytest.raises(DisclosureAssessmentPacketError, match="locator does not match"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))


def test_packet_rejects_tampered_evidence_artifact_content_hash() -> None:
    payload = json.loads(_packet_json())
    payload["evidence"][0]["evidence_artifact"]["content_hash"] = "b" * 64

    with pytest.raises(DisclosureAssessmentPacketError, match="content hash does not match"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))


def test_packet_rejects_tampered_evidence_artifact_id() -> None:
    payload = json.loads(_packet_json())
    payload["evidence"][0]["evidence_artifact"]["id"] = (
        "00000000-0000-0000-0000-000000000001"
    )

    with pytest.raises(DisclosureAssessmentPacketError, match="id does not match"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))


def test_packet_rejects_unknown_fields_in_external_handoff() -> None:
    payload = json.loads(_packet_json())
    payload["new_authority"] = "BUY"

    with pytest.raises(DisclosureAssessmentPacketError, match="Extra inputs are not permitted"):
        parse_disclosure_assessment_packet(json.dumps(payload, ensure_ascii=False))
