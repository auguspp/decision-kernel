from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.adapters.pdf_text import PagedPdfText, PdfPageText, PdfTextStatus
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.runtime.disclosure_assessment import (
    DisclosureAssessmentPacketError,
    prepare_disclosure_assessment_packet,
    serialize_disclosure_assessment_packet,
)
from decision_kernel.runtime.disclosure_radar import DisclosureBatch


SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = ZoneInfo("UTC")


def _snapshot():
    return ResearchCommitPackage.model_validate_json(
        Path("dogfood/300750-catl.json").read_text(encoding="utf-8")
    ).research_snapshot


def _announcement(identifier: str, *, published_at: datetime) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="300750",
        org_id="9900025790",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=published_at,
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-27/{identifier}.PDF",
    )


def _batch(*announcements: CninfoAnnouncement) -> DisclosureBatch:
    ordered = tuple(sorted(announcements, key=lambda item: item.published_at))
    return DisclosureBatch(
        stock_code="300750",
        publication_date=date(2026, 8, 27),
        first_published_at=ordered[0].published_at,
        last_published_at=ordered[-1].published_at,
        announcements=ordered,
    )


def _extract(pdf_sha: str = "a" * 64, text_sha: str = "b" * 64):
    def fake_extract(_payload: bytes) -> PagedPdfText:
        return PagedPdfText(
            pdf_sha256=pdf_sha,
            text_sha256=text_sha,
            page_count=2,
            extracted_char_count=13,
            status=PdfTextStatus.EXTRACTED,
            pages=(
                PdfPageText(page_number=1, text="第一页正文"),
                PdfPageText(page_number=2, text="第二页正文"),
            ),
        )

    return fake_extract


def _fetch_pdf(*, source_locator: str) -> bytes:
    assert source_locator.startswith("https://static.cninfo.com.cn/")
    return b"%PDF-test"


def test_packet_binds_exact_frozen_research_and_official_evidence() -> None:
    snapshot = _snapshot()
    announcement = _announcement(
        "1225519101",
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
    )
    prepared_at = datetime(2026, 9, 2, 6, 0, tzinfo=UTC)

    packet = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=_batch(announcement),
        prepared_at=prepared_at,
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )

    assert packet.stock_code == "300750"
    assert packet.announcement_ids == ("1225519101",)
    assert packet.research_snapshot_id == snapshot.id
    assert packet.research_as_of == snapshot.as_of_datetime
    assert packet.core_thesis == snapshot.core_thesis
    assert packet.open_questions == snapshot.open_questions
    assert packet.assessment_semantics_id == "research-funnel-v1"
    assert len(packet.assessment_input_hash) == 64
    assert len(packet.evidence) == 1
    evidence = packet.evidence[0]
    assert evidence.pdf_sha256 == "a" * 64
    assert evidence.text_sha256 == "b" * 64
    assert evidence.evidence_artifact.content_hash == "a" * 64
    assert [page.text for page in evidence.pages] == ["第一页正文", "第二页正文"]

    serialized = serialize_disclosure_assessment_packet(packet)
    assert '"assessment_input_hash"' in serialized
    assert '"research_status": "UNASSESSED"' in serialized
    assert '"investment_authority": "NONE"' in serialized
    assert "第一页正文" in serialized


def test_assessment_input_hash_ignores_retrieval_clock_but_changes_with_evidence() -> None:
    snapshot = _snapshot()
    announcement = _announcement(
        "1225519101",
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
    )
    batch = _batch(announcement)
    first = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=batch,
        prepared_at=datetime(2026, 9, 2, 6, 0, tzinfo=UTC),
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )
    later = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=batch,
        prepared_at=datetime(2026, 9, 2, 7, 0, tzinfo=UTC),
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )
    changed = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=batch,
        prepared_at=datetime(2026, 9, 2, 7, 0, tzinfo=UTC),
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(text_sha="c" * 64),
    )

    assert first.assessment_input_hash == later.assessment_input_hash
    assert first.assessment_input_hash != changed.assessment_input_hash
    assert first.evidence[0].evidence_artifact.retrieved_at != later.evidence[0].evidence_artifact.retrieved_at


def test_assessment_input_hash_binds_research_context_even_if_snapshot_id_is_reused() -> None:
    snapshot = _snapshot()
    changed_snapshot = snapshot.model_copy(
        update={"core_thesis": snapshot.core_thesis + " changed context"}
    )
    announcement = _announcement(
        "1225519101",
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
    )
    batch = _batch(announcement)
    prepared_at = datetime(2026, 9, 2, 6, 0, tzinfo=UTC)

    original = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=batch,
        prepared_at=prepared_at,
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )
    changed = prepare_disclosure_assessment_packet(
        research_snapshot=changed_snapshot,
        batch=batch,
        prepared_at=prepared_at,
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )

    assert original.research_snapshot_id == changed.research_snapshot_id
    assert original.assessment_input_hash != changed.assessment_input_hash


def test_packet_rejects_batch_already_covered_by_frozen_research_before_pdf_fetch() -> None:
    snapshot = _snapshot()
    calls = 0

    def should_not_fetch(*, source_locator: str) -> bytes:
        nonlocal calls
        calls += 1
        return b"%PDF-test"

    covered_time = snapshot.as_of_datetime.astimezone(SHANGHAI) - timedelta(minutes=1)
    covered = _announcement("COVERED", published_at=covered_time)
    batch = DisclosureBatch(
        stock_code="300750",
        publication_date=covered_time.date(),
        first_published_at=covered_time,
        last_published_at=covered_time,
        announcements=(covered,),
    )

    with pytest.raises(
        DisclosureAssessmentPacketError,
        match="already covered by frozen Research",
    ):
        prepare_disclosure_assessment_packet(
            research_snapshot=snapshot,
            batch=batch,
            prepared_at=datetime(2026, 9, 2, 6, 0, tzinfo=UTC),
            fetch_pdf=should_not_fetch,
            extract_pdf=_extract(),
        )

    assert calls == 0


def test_packet_orders_evidence_by_exact_announcement_identity() -> None:
    snapshot = _snapshot()
    first = _announcement(
        "B",
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
    )
    second = _announcement(
        "A",
        published_at=datetime(2026, 8, 27, 17, 49, 11, tzinfo=SHANGHAI),
    )

    packet = prepare_disclosure_assessment_packet(
        research_snapshot=snapshot,
        batch=_batch(first, second),
        prepared_at=datetime(2026, 9, 2, 6, 0, tzinfo=UTC),
        fetch_pdf=_fetch_pdf,
        extract_pdf=_extract(),
    )

    assert packet.announcement_ids == ("A", "B")
    assert tuple(item.announcement_id for item in packet.evidence) == ("A", "B")
