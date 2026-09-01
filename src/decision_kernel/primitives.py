from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator


class DomainValidationError(ValueError):
    """Raised when a domain operation would violate a kernel invariant."""


def _validate_authoritative_value(value: Any) -> None:
    if isinstance(value, float):
        raise DomainValidationError(
            "binary float is not allowed in authoritative domain inputs"
        )
    if isinstance(value, BaseModel):
        _validate_authoritative_value(value.model_dump(mode="python"))
    elif isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise DomainValidationError(
                "authoritative domain input keys must be strings"
            )
        for item in value.values():
            _validate_authoritative_value(item)
    elif isinstance(value, (set, frozenset)):
        raise DomainValidationError(
            "unordered containers are not allowed in authoritative domain inputs"
        )
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_authoritative_value(item)


class KernelModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def validate_authoritative_inputs(cls, value: Any) -> Any:
        _validate_authoritative_value(value)
        return value


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


def _currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("currency must be a three-letter code")
    return normalized


AwareDateTime = Annotated[datetime, AfterValidator(_aware)]
CurrencyCode = Annotated[str, AfterValidator(_currency)]
