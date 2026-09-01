from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.evidence import (
    EvidenceArtifact,
    ReplayabilityLevel,
    RetentionMode,
)


BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _artifact(**updates: object) -> EvidenceArtifact:
    values: dict[str, object] = {
        "id": uuid4(),
        "source_type": "official_disclosure",
        "source_identifier": "sample-001",
        "source_locator": "https://example.test/disclosure/001",
        "published_at": BASE_TIME,
        "available_at": BASE_TIME + timedelta(minutes=5),
        "retrieved_at": BASE_TIME + timedelta(minutes=10),
        "content_hash": "a" * 64,
        "idempotency_key": "sample-001-v1",
        "retention_mode": RetentionMode.FULL_ARTIFACT,
        "replayability_level": ReplayabilityLevel.FULL,
        "raw_storage_ref": "evidence/sample-001.pdf",
    }
    values.update(updates)
    return EvidenceArtifact.model_validate(values)


def test_evidence_is_available_only_after_real_availability_time() -> None:
    artifact = _artifact()

    assert artifact.is_available_at(BASE_TIME + timedelta(minutes=4)) is False
    assert artifact.is_available_at(BASE_TIME + timedelta(minutes=5)) is True


def test_evidence_rejects_naive_pit_cutoff() -> None:
    artifact = _artifact()

    with pytest.raises(ValueError, match="timezone-aware"):
        artifact.is_available_at(datetime(2026, 9, 1, 12, 5))


def test_evidence_rejects_naive_recorded_timestamps() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _artifact(available_at=datetime(2026, 9, 1, 12, 5))


def test_evidence_rejects_backfilled_or_impossible_clock_order() -> None:
    with pytest.raises(
        ValidationError,
        match="published_at <= available_at <= retrieved_at",
    ):
        _artifact(
            available_at=BASE_TIME - timedelta(minutes=1),
            retrieved_at=BASE_TIME + timedelta(minutes=10),
        )

    with pytest.raises(
        ValidationError,
        match="published_at <= available_at <= retrieved_at",
    ):
        _artifact(retrieved_at=BASE_TIME + timedelta(minutes=4))


def test_metadata_only_is_reference_only_and_retains_no_content() -> None:
    artifact = _artifact(
        retention_mode=RetentionMode.METADATA_ONLY,
        replayability_level=ReplayabilityLevel.REFERENCE_ONLY,
        raw_storage_ref=None,
    )
    assert artifact.raw_storage_ref is None

    with pytest.raises(ValidationError, match="METADATA_ONLY evidence is REFERENCE_ONLY"):
        _artifact(
            retention_mode=RetentionMode.METADATA_ONLY,
            replayability_level=ReplayabilityLevel.PARTIAL,
            raw_storage_ref=None,
        )

    with pytest.raises(ValidationError, match="cannot retain raw or extracted content"):
        _artifact(
            retention_mode=RetentionMode.METADATA_ONLY,
            replayability_level=ReplayabilityLevel.REFERENCE_ONLY,
            raw_storage_ref="should-not-exist",
        )


def test_extracted_values_cannot_claim_full_replayability() -> None:
    artifact = _artifact(
        retention_mode=RetentionMode.EXTRACTED_VALUES,
        replayability_level=ReplayabilityLevel.PARTIAL,
        raw_storage_ref=None,
        extracted_structured_values={"revenue": "100"},
    )
    assert artifact.replayability_level is ReplayabilityLevel.PARTIAL

    with pytest.raises(ValidationError, match="cannot claim FULL replayability"):
        _artifact(
            retention_mode=RetentionMode.EXTRACTED_VALUES,
            replayability_level=ReplayabilityLevel.FULL,
            raw_storage_ref=None,
            extracted_structured_values={"revenue": "100"},
        )

    with pytest.raises(ValidationError, match="requires structured values"):
        _artifact(
            retention_mode=RetentionMode.EXTRACTED_VALUES,
            replayability_level=ReplayabilityLevel.PARTIAL,
            raw_storage_ref=None,
            extracted_structured_values=None,
        )


def test_full_replayability_requires_retained_full_artifact() -> None:
    with pytest.raises(ValidationError, match="FULL_ARTIFACT requires raw_storage_ref"):
        _artifact(raw_storage_ref=None)


def test_authoritative_evidence_rejects_binary_float_values() -> None:
    with pytest.raises(ValidationError, match="binary float"):
        _artifact(
            retention_mode=RetentionMode.EXTRACTED_VALUES,
            replayability_level=ReplayabilityLevel.PARTIAL,
            raw_storage_ref=None,
            extracted_structured_values={"margin": 0.25},
        )
