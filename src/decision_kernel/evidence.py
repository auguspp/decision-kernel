from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


class EvidenceValidationError(ValueError):
    """Raised when evidence would violate an epistemic/PIT invariant."""


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


AwareDateTime = Annotated[datetime, AfterValidator(_aware)]


def _validate_authoritative_value(value: Any) -> None:
    """Keep authoritative evidence inputs deterministic without a shared framework."""

    if isinstance(value, float):
        raise EvidenceValidationError(
            "binary float is not allowed in authoritative evidence inputs"
        )
    if isinstance(value, BaseModel):
        _validate_authoritative_value(value.model_dump(mode="python"))
    elif isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise EvidenceValidationError(
                "authoritative evidence input keys must be strings"
            )
        for item in value.values():
            _validate_authoritative_value(item)
    elif isinstance(value, (set, frozenset)):
        raise EvidenceValidationError(
            "unordered containers are not allowed in authoritative evidence inputs"
        )
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_authoritative_value(item)


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def validate_authoritative_inputs(cls, value: Any) -> Any:
        _validate_authoritative_value(value)
        return value


class RetentionMode(StrEnum):
    FULL_ARTIFACT = "FULL_ARTIFACT"
    EXTRACTED_VALUES = "EXTRACTED_VALUES"
    METADATA_ONLY = "METADATA_ONLY"


class ReplayabilityLevel(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    REFERENCE_ONLY = "REFERENCE_ONLY"


class EvidenceRelationship(StrEnum):
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    CONTEXT = "CONTEXT"


class EvidenceArtifact(_EvidenceModel):
    """A PIT-aware evidence record, independent of fetching or storage implementation."""

    id: UUID
    source_type: str = Field(min_length=1, max_length=64)
    source_identifier: str = Field(min_length=1, max_length=255)
    source_locator: str = Field(min_length=1, max_length=2048)
    published_at: AwareDateTime
    available_at: AwareDateTime
    retrieved_at: AwareDateTime
    content_hash: str = Field(min_length=1, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=255)
    retention_mode: RetentionMode
    replayability_level: ReplayabilityLevel
    raw_storage_ref: str | None = Field(default=None, max_length=2048)
    extracted_structured_values: dict[str, Any] | None = None
    permitted_excerpt: str | None = None
    source_location: str | None = Field(default=None, max_length=512)
    license_terms_note: str | None = None
    report_period_end: date | None = None
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_epistemic_and_retention_contract(self) -> "EvidenceArtifact":
        if not (self.published_at <= self.available_at <= self.retrieved_at):
            raise ValueError("published_at <= available_at <= retrieved_at is required")

        if self.retention_mode is RetentionMode.METADATA_ONLY:
            if self.replayability_level is not ReplayabilityLevel.REFERENCE_ONLY:
                raise ValueError("METADATA_ONLY evidence is REFERENCE_ONLY")
            if (
                self.raw_storage_ref
                or self.extracted_structured_values is not None
                or self.permitted_excerpt
            ):
                raise ValueError("METADATA_ONLY cannot retain raw or extracted content")

        if self.retention_mode is RetentionMode.EXTRACTED_VALUES:
            if self.replayability_level is ReplayabilityLevel.FULL:
                raise ValueError("EXTRACTED_VALUES cannot claim FULL replayability")
            if self.extracted_structured_values is None and not self.permitted_excerpt:
                raise ValueError(
                    "EXTRACTED_VALUES requires structured values or a permitted excerpt"
                )

        if self.retention_mode is RetentionMode.FULL_ARTIFACT and not self.raw_storage_ref:
            raise ValueError("FULL_ARTIFACT requires raw_storage_ref")

        if self.replayability_level is ReplayabilityLevel.FULL:
            if (
                self.retention_mode is not RetentionMode.FULL_ARTIFACT
                or not self.raw_storage_ref
            ):
                raise ValueError("FULL replayability requires a retained full artifact")

        return self

    def is_available_at(self, as_of: datetime) -> bool:
        """Return whether this evidence was actually available by the PIT cutoff."""

        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("PIT cutoff must be timezone-aware")
        return self.available_at <= as_of


class EvidenceArtifactLink(_EvidenceModel):
    """A semantic relationship between a research state and an evidence artifact."""

    id: UUID
    research_snapshot_id: UUID
    evidence_artifact_id: UUID
    relationship: EvidenceRelationship
    relevance: str | None = Field(default=None, max_length=512)
    interpretation_notes: str | None = None
