from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import (
    CNINFO_STATIC_BASE_URL,
    CninfoAdapterError,
    CninfoAnnouncement,
    reference_evidence_from_cninfo_announcement,
)
from decision_kernel.evidence import ReplayabilityLevel, RetentionMode
from decision_kernel.runtime.cninfo_http import CninfoRuntimeError, fetch_cninfo_pdf_bytes


SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = ZoneInfo("UTC")
ARTIFACT_ID = UUID("8509fb60-d499-4ef6-bdce-6420ce55de2f")
PDF_HASH = "A" * 64


def _announcement(
    *,
    published_at: datetime | None = None,
    source_locator: str | None = None,
) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id="1225519101",
        stock_code="300750",
        org_id="GD165627",
        title="关于2026年度第六期绿色科技创新债券发行完成的公告",
        announcement_type=None,
        published_at=(
            published_at
            if published_at is not None
            else datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI)
        ),
        source_locator=(
            source_locator
            if source_locator is not None
            else f"{CNINFO_STATIC_BASE_URL}/finalpage/2026-08-27/1225519101.PDF"
        ),
    )


def test_fetch_cninfo_pdf_bytes_accepts_only_bounded_official_pdf_payload() -> None:
    seen: list[str] = []
    payload = b"%PDF-1.7\nqualified"

    result = fetch_cninfo_pdf_bytes(
        source_locator=_announcement().source_locator,
        max_bytes=len(payload),
        get_bytes=lambda url: seen.append(url) or payload,
    )

    assert result == payload
    assert seen == [_announcement().source_locator]

    with pytest.raises(CninfoRuntimeError, match="official static host"):
        fetch_cninfo_pdf_bytes(
            source_locator="https://example.com/disclosure.pdf",
            get_bytes=lambda _url: payload,
        )


def test_fetch_cninfo_pdf_bytes_fails_closed_on_oversize_or_non_pdf_response() -> None:
    with pytest.raises(CninfoRuntimeError, match="acquisition limit"):
        fetch_cninfo_pdf_bytes(
            source_locator=_announcement().source_locator,
            max_bytes=8,
            get_bytes=lambda _url: b"%PDF-1.7-too-large",
        )

    with pytest.raises(CninfoRuntimeError, match="PDF header"):
        fetch_cninfo_pdf_bytes(
            source_locator=_announcement().source_locator,
            get_bytes=lambda _url: b"<html>upstream error</html>",
        )

    with pytest.raises(CninfoRuntimeError, match="positive integer"):
        fetch_cninfo_pdf_bytes(
            source_locator=_announcement().source_locator,
            max_bytes=0,
            get_bytes=lambda _url: b"%PDF-1.7",
        )


def test_reference_evidence_preserves_exact_cninfo_identity_and_pdf_hash() -> None:
    announcement = _announcement()
    retrieved_at = datetime(2026, 9, 2, 3, 30, tzinfo=UTC)

    artifact = reference_evidence_from_cninfo_announcement(
        announcement,
        artifact_id=ARTIFACT_ID,
        pdf_sha256=PDF_HASH,
        retrieved_at=retrieved_at,
    )

    assert artifact.id == ARTIFACT_ID
    assert artifact.source_type == "OFFICIAL_DISCLOSURE"
    assert artifact.source_identifier == "CNINFO:300750:ANNOUNCEMENT:1225519101"
    assert artifact.idempotency_key == artifact.source_identifier
    assert artifact.source_locator == announcement.source_locator
    assert artifact.published_at == announcement.published_at
    assert artifact.available_at == announcement.published_at
    assert artifact.retrieved_at == retrieved_at
    assert artifact.content_hash == PDF_HASH.lower()
    assert artifact.retention_mode is RetentionMode.METADATA_ONLY
    assert artifact.replayability_level is ReplayabilityLevel.REFERENCE_ONLY
    assert artifact.raw_storage_ref is None
    assert artifact.extracted_structured_values is None
    assert artifact.permitted_excerpt is None


def test_reference_evidence_requires_auditable_clocks_official_locator_and_sha() -> None:
    published = _announcement().published_at
    assert published is not None

    with pytest.raises(CninfoAdapterError, match="publication timestamp"):
        reference_evidence_from_cninfo_announcement(
            _announcement(published_at=datetime(2026, 8, 27, 17, 48, 11)),
            artifact_id=ARTIFACT_ID,
            pdf_sha256=PDF_HASH,
            retrieved_at=datetime(2026, 9, 2, 3, 30, tzinfo=UTC),
        )

    with pytest.raises(CninfoAdapterError, match="official static host"):
        reference_evidence_from_cninfo_announcement(
            _announcement(source_locator="https://example.com/disclosure.pdf"),
            artifact_id=ARTIFACT_ID,
            pdf_sha256=PDF_HASH,
            retrieved_at=datetime(2026, 9, 2, 3, 30, tzinfo=UTC),
        )

    with pytest.raises(CninfoAdapterError, match="SHA256"):
        reference_evidence_from_cninfo_announcement(
            _announcement(),
            artifact_id=ARTIFACT_ID,
            pdf_sha256="not-a-sha256",
            retrieved_at=datetime(2026, 9, 2, 3, 30, tzinfo=UTC),
        )

    with pytest.raises(CninfoAdapterError, match="before publication"):
        reference_evidence_from_cninfo_announcement(
            _announcement(),
            artifact_id=ARTIFACT_ID,
            pdf_sha256=PDF_HASH,
            retrieved_at=published.astimezone(UTC) - timedelta(seconds=1),
        )
