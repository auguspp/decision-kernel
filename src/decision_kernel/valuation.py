from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from .primitives import AwareDateTime, CurrencyCode, KernelModel


class ValuationChangeReason(StrEnum):
    FUNDAMENTAL_REVISION = "FUNDAMENTAL_REVISION"
    HORIZON_ROLL = "HORIZON_ROLL"
    VALUATION_PARAMETER_CHANGE = "VALUATION_PARAMETER_CHANGE"
    CASH_DISTRIBUTION = "CASH_DISTRIBUTION"
    CAPITAL_STRUCTURE = "CAPITAL_STRUCTURE"
    FX = "FX"
    MODEL_CHANGE = "MODEL_CHANGE"
    OTHER_EXPLICIT = "OTHER_EXPLICIT"


class ValuationBasis(KernelModel):
    """Frozen valuation assumptions owned by one ResearchSnapshot."""

    id: UUID
    research_snapshot_id: UUID
    version: int = Field(ge=1)
    as_of_datetime: AwareDateTime
    valuation_horizon_date: date
    valuation_method: str = Field(min_length=1, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    model_version: str = Field(min_length=1, max_length=64)
    currency: CurrencyCode
    fundamental_inputs: dict[str, Any] = Field(default_factory=dict)
    valuation_parameter_inputs: dict[str, Any] = Field(default_factory=dict)
    capital_structure_inputs: dict[str, Any] = Field(default_factory=dict)
    fx_inputs: dict[str, Any] = Field(default_factory=dict)
    other_explicit_inputs: dict[str, Any] = Field(default_factory=dict)
    supersedes_valuation_basis_id: UUID | None = None
    declared_change_reasons: tuple[ValuationChangeReason, ...] = ()
    provenance_artifact_ids: tuple[UUID, ...] = ()
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_version_lineage(self) -> "ValuationBasis":
        if self.supersedes_valuation_basis_id == self.id:
            raise ValueError("ValuationBasis cannot supersede itself")
        if self.supersedes_valuation_basis_id is not None and self.version == 1:
            raise ValueError("a superseding ValuationBasis must have version greater than one")
        if self.version > 1 and self.supersedes_valuation_basis_id is None:
            raise ValueError("ValuationBasis versions after one must identify their predecessor")
        if len(set(self.declared_change_reasons)) != len(self.declared_change_reasons):
            raise ValueError("declared change reasons must be unique")
        return self
