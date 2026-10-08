from __future__ import annotations

from datetime import date
from enum import Enum, StrEnum
from typing import Any, ClassVar, Mapping, Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from .identity import canonical_hash
from .primitives import AwareDateTime, CurrencyCode, DomainValidationError, KernelModel



def _read_only(*args, **kwargs):
    raise TypeError("valuation inputs are read-only; create a new ValuationBasis version")


class _InputDict(dict):
    """Private dict-shaped value: ordinary mutations reject, native dumps stay dicts."""

    def __new__(cls, values=()):
        value = dict.__new__(cls)
        dict.update(value, values)
        return value

    def __init__(self, values=()):
        pass  # Initial contents are set exactly once in __new__.

    __setitem__ = __delitem__ = __ior__ = clear = pop = popitem = setdefault = update = _read_only

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return type(self), (dict(self),)


class _InputList(list):
    """Keep list (not tuple) semantics in existing Python/JSON serialized payloads."""

    def __new__(cls, values=()):
        value = list.__new__(cls)
        list.extend(value, values)
        return value

    def __init__(self, values=()):
        pass

    __setitem__ = __delitem__ = __iadd__ = __imul__ = _read_only
    append = clear = extend = insert = pop = remove = reverse = sort = _read_only

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        return type(self), (list(self),)


def _input_value(value: Any) -> Any:
    # Take the declared model's serialized value, never retain its mutable alias.
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, Enum):
        if type(value.value) not in (str, int, bool, type(None)):
            raise DomainValidationError("valuation enum inputs require immutable scalar values")
        return value
    if isinstance(value, dict):
        return _InputDict((key, _input_value(item)) for key, item in value.items())
    if isinstance(value, list):
        return _InputList(_input_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_input_value(item) for item in value)
    # Canonical hashing above rejects floats, sets, opaque objects, nonfinite
    # decimals and naive clocks. Remaining canonical leaves have no mutable API.
    return value


def _input_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DomainValidationError("valuation inputs must be dictionaries")
    canonical_hash(value)  # Reuse the existing admissible value/key contract.
    return _input_value(value)


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
    """Frozen valuation assumptions owned by one ResearchSnapshot.

    Input containers reject ordinary mutation, including nested list/dict values.
    Exports are detached normal dicts/lists. This is an accidental-mutation guard,
    not a sandbox against model_construct, object.__setattr__ or base-type calls.
    Exact archived hashes and the original Research commit checks remain required.
    """

    _input_fields: ClassVar[tuple[str, ...]] = (
        "fundamental_inputs", "valuation_parameter_inputs", "capital_structure_inputs",
        "fx_inputs", "other_explicit_inputs",
    )

    id: UUID
    research_snapshot_id: UUID
    version: int = Field(ge=1)
    as_of_datetime: AwareDateTime
    valuation_horizon_date: date
    valuation_method: str = Field(min_length=1, max_length=64)
    model_name: str | None = Field(default=None, max_length=128)
    model_version: str = Field(min_length=1, max_length=64)
    currency: CurrencyCode
    fundamental_inputs: dict[str, Any] = Field(default_factory=dict, validate_default=True)
    valuation_parameter_inputs: dict[str, Any] = Field(default_factory=dict, validate_default=True)
    capital_structure_inputs: dict[str, Any] = Field(default_factory=dict, validate_default=True)
    fx_inputs: dict[str, Any] = Field(default_factory=dict, validate_default=True)
    other_explicit_inputs: dict[str, Any] = Field(default_factory=dict, validate_default=True)
    supersedes_valuation_basis_id: UUID | None = None
    declared_change_reasons: tuple[ValuationChangeReason, ...] = ()
    provenance_artifact_ids: tuple[UUID, ...] = ()
    schema_version: int = Field(default=1, ge=1)

    @field_validator(*_input_fields, mode="after")
    @classmethod
    def isolate_inputs(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _input_mapping(value)

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        # Pydantic copy skips validation. Preserve that documented lineage/status
        # contract, but do not let its input updates reintroduce mutable aliases.
        changes = dict(update) if update is not None else None
        if changes is not None:
            for name in self._input_fields:
                if name in changes:
                    changes[name] = _input_mapping(changes[name])
        return super().model_copy(update=changes, deep=deep)

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
