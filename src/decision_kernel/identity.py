from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from hashlib import sha256
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from .primitives import DomainValidationError


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DomainValidationError(
                "non-finite Decimal is not allowed in canonical payloads"
            )
        return format(value, "f")
    if isinstance(value, float):
        raise DomainValidationError(
            "binary float is not allowed in canonical payloads"
        )
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise DomainValidationError(
                "canonical datetime must be timezone-aware"
            )
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise DomainValidationError(
                "canonical payload keys must be strings"
            )
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (set, frozenset)):
        raise DomainValidationError(
            "unordered containers are not allowed in canonical payloads"
        )
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, str)):
        return value
    raise DomainValidationError(
        f"unsupported canonical payload type: {type(value).__name__}"
    )


def canonical_json(value: Any) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()
