from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from decision_kernel.adapters.hithink_index import HithinkIndustryCatalog
from decision_kernel.identity import canonical_hash

from .sector_breadth import SectorMembershipSnapshot
from .sector_radar_shadow import (
    SectorRadarCurrentParentLink,
    build_current_parent_link,
)


SECTOR_PARENT_HINT_SCHEMA_VERSION = 1
SECTOR_PARENT_HINT_SEMANTICS = (
    "CURRENT_PARENT_HINT_FOR_CANDIDATE_TIME_REVALIDATION"
)
SECTOR_PARENT_HINT_REVALIDATION_SEMANTICS = (
    "CURRENT_CATALOG_AND_MEMBERSHIP_CONTAINMENT_REVALIDATED"
)
SECTOR_PARENT_HINT_HISTORICAL_TAXONOMY_AUTHORITY = "NONE"
SECTOR_PARENT_HINT_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_PARENT_HINT_INVESTMENT_AUTHORITY = "NONE"

_BROAD_CODE = re.compile(r"^881\d{3}\.TI$")
_GRANULAR_CODE = re.compile(r"^884\d{3}\.TI$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")

_ROOT_FIELDS = {
    "schema_version",
    "captured_at",
    "membership_capture_window",
    "source",
    "source_workflow_run_id",
    "source_artifact_id",
    "source_artifact_digest",
    "source_result_hash",
    "catalog_hash",
    "catalog_shape",
    "mapping_result",
    "parent_hints",
    "use_semantics",
    "mapping_hash",
}
_WINDOW_FIELDS = {"start", "end"}
_CATALOG_SHAPE_FIELDS = {"broad_881", "granular_884"}
_MAPPING_RESULT_FIELDS = {
    "unique_full_containment",
    "ambiguous",
    "unmapped",
    "exact_duplicate_granular_member_sets",
    "overlapping_broad_member_sets",
    "parents_with_granular_children",
    "broad_parents_without_granular_children",
}
_HINT_FIELDS = {
    "child_thscode",
    "child_name",
    "child_member_count_at_capture",
    "child_constituent_set_hash_at_capture",
    "child_membership_captured_at",
    "parent_thscode",
    "parent_name",
    "parent_member_count_at_capture",
    "parent_constituent_set_hash_at_capture",
    "parent_membership_captured_at",
    "intersection_count_at_capture",
    "child_fully_contained_at_capture",
}
_USE_FIELDS = {
    "purpose",
    "catalog_rule",
    "membership_rule",
    "failure_rule",
    "historical_taxonomy_authority",
    "research_authority",
    "human_attention_authority",
    "investment_authority",
}


@dataclass(frozen=True)
class SectorParentHint:
    """One frozen current-PIT child-to-parent lookup hint.

    The relationship carries no permanent taxonomy authority. Current catalog and
    memberships must be revalidated before it can be used for shadow grouping.
    """

    child_thscode: str
    child_name: str
    child_member_count_at_capture: int
    child_constituent_set_hash_at_capture: str
    child_membership_captured_at: datetime
    parent_thscode: str
    parent_name: str
    parent_member_count_at_capture: int
    parent_constituent_set_hash_at_capture: str
    parent_membership_captured_at: datetime
    intersection_count_at_capture: int
    child_fully_contained_at_capture: bool


@dataclass(frozen=True)
class SectorParentHintIndex:
    """Content-hashed frozen parent hints plus their exact source identity."""

    schema_version: int
    captured_at: datetime
    membership_capture_start: datetime
    membership_capture_end: datetime
    source: str
    source_workflow_run_id: int
    source_artifact_id: int
    source_artifact_digest: str
    source_result_hash: str
    catalog_hash: str
    broad_count: int
    granular_count: int
    parents_with_granular_children: int
    broad_parents_without_granular_children: int
    mapping_hash: str
    hints: tuple[SectorParentHint, ...]
    hint_by_child: Mapping[str, SectorParentHint]
    hint_semantics: str = SECTOR_PARENT_HINT_SEMANTICS
    historical_taxonomy_authority: str = (
        SECTOR_PARENT_HINT_HISTORICAL_TAXONOMY_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_PARENT_HINT_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_PARENT_HINT_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorParentHintCatalogValidation:
    """Proof that the current formal-industry catalog still matches the hint index."""

    mapping_hash: str
    frozen_catalog_hash: str
    current_catalog_hash: str
    broad_count: int
    granular_count: int
    validated_child_count: int
    validation_semantics: str = "EXACT_CURRENT_FORMAL_INDUSTRY_CATALOG_MATCH"
    historical_taxonomy_authority: str = (
        SECTOR_PARENT_HINT_HISTORICAL_TAXONOMY_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_PARENT_HINT_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_PARENT_HINT_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorParentHintRevalidation:
    """Candidate-time current membership proof for one frozen parent hint."""

    mapping_hash: str
    catalog_validation: SectorParentHintCatalogValidation
    hint: SectorParentHint
    current_parent_link: SectorRadarCurrentParentLink
    child_membership_changed_since_hint_capture: bool
    parent_membership_changed_since_hint_capture: bool
    child_member_count_changed_since_hint_capture: bool
    parent_member_count_changed_since_hint_capture: bool
    revalidation_semantics: str = SECTOR_PARENT_HINT_REVALIDATION_SEMANTICS
    historical_taxonomy_authority: str = (
        SECTOR_PARENT_HINT_HISTORICAL_TAXONOMY_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_PARENT_HINT_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_PARENT_HINT_INVESTMENT_AUTHORITY


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise ValueError(
            f"{label} fields disagree; missing={missing}; unknown={unknown}"
        )


def _aware_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _non_empty_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


def _positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _sha256(value: Any, *, field: str, prefixed: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a SHA-256 string")
    pattern = _SHA256_PREFIXED if prefixed else _SHA256
    if not pattern.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 string")
    return value


def _parse_hint(
    raw: Any,
    *,
    index: int,
    capture_start: datetime,
    capture_end: datetime,
) -> SectorParentHint:
    if not isinstance(raw, Mapping):
        raise ValueError(f"sector parent hint {index} must be a JSON object")
    _require_exact_fields(raw, _HINT_FIELDS, label=f"sector parent hint {index}")

    child_thscode = _non_empty_string(
        raw["child_thscode"],
        field=f"sector parent hint {index} child_thscode",
    ).upper()
    parent_thscode = _non_empty_string(
        raw["parent_thscode"],
        field=f"sector parent hint {index} parent_thscode",
    ).upper()
    if not _GRANULAR_CODE.fullmatch(child_thscode):
        raise ValueError(f"sector parent hint {index} child is not 884*.TI")
    if not _BROAD_CODE.fullmatch(parent_thscode):
        raise ValueError(f"sector parent hint {index} parent is not 881*.TI")

    child_name = _non_empty_string(
        raw["child_name"],
        field=f"sector parent hint {index} child_name",
    )
    parent_name = _non_empty_string(
        raw["parent_name"],
        field=f"sector parent hint {index} parent_name",
    )
    child_count = _positive_int(
        raw["child_member_count_at_capture"],
        field=f"sector parent hint {index} child_member_count_at_capture",
    )
    parent_count = _positive_int(
        raw["parent_member_count_at_capture"],
        field=f"sector parent hint {index} parent_member_count_at_capture",
    )
    intersection_count = _non_negative_int(
        raw["intersection_count_at_capture"],
        field=f"sector parent hint {index} intersection_count_at_capture",
    )
    if parent_count < child_count:
        raise ValueError(f"sector parent hint {index} parent is smaller than child")
    if raw["child_fully_contained_at_capture"] is not True:
        raise ValueError(f"sector parent hint {index} is not full containment")
    if intersection_count != child_count:
        raise ValueError(
            f"sector parent hint {index} intersection disagrees with child count"
        )

    child_captured_at = _aware_datetime(
        raw["child_membership_captured_at"],
        field=f"sector parent hint {index} child_membership_captured_at",
    )
    parent_captured_at = _aware_datetime(
        raw["parent_membership_captured_at"],
        field=f"sector parent hint {index} parent_membership_captured_at",
    )
    for field, captured_at in (
        ("child", child_captured_at),
        ("parent", parent_captured_at),
    ):
        if captured_at < capture_start or captured_at > capture_end:
            raise ValueError(
                f"sector parent hint {index} {field} capture is outside the frozen window"
            )

    return SectorParentHint(
        child_thscode=child_thscode,
        child_name=child_name,
        child_member_count_at_capture=child_count,
        child_constituent_set_hash_at_capture=_sha256(
            raw["child_constituent_set_hash_at_capture"],
            field=(
                f"sector parent hint {index} "
                "child_constituent_set_hash_at_capture"
            ),
        ),
        child_membership_captured_at=child_captured_at,
        parent_thscode=parent_thscode,
        parent_name=parent_name,
        parent_member_count_at_capture=parent_count,
        parent_constituent_set_hash_at_capture=_sha256(
            raw["parent_constituent_set_hash_at_capture"],
            field=(
                f"sector parent hint {index} "
                "parent_constituent_set_hash_at_capture"
            ),
        ),
        parent_membership_captured_at=parent_captured_at,
        intersection_count_at_capture=intersection_count,
        child_fully_contained_at_capture=True,
    )


def parse_sector_parent_hints(raw_hints: str) -> SectorParentHintIndex:
    """Parse and validate one exact content-hashed parent-hint artifact."""

    try:
        raw = json.loads(raw_hints)
    except json.JSONDecodeError as exc:
        raise ValueError("sector parent hints must contain valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("sector parent hints must be a JSON object")
    _require_exact_fields(raw, _ROOT_FIELDS, label="sector parent hints")

    if raw["schema_version"] != SECTOR_PARENT_HINT_SCHEMA_VERSION:
        raise ValueError("unsupported sector parent-hint schema version")

    claimed_mapping_hash = _sha256(raw["mapping_hash"], field="mapping_hash")
    hash_payload = dict(raw)
    hash_payload.pop("mapping_hash")
    if canonical_hash(hash_payload) != claimed_mapping_hash:
        raise ValueError("sector parent-hint mapping hash mismatch")

    captured_at = _aware_datetime(raw["captured_at"], field="captured_at")
    window = raw["membership_capture_window"]
    if not isinstance(window, Mapping):
        raise ValueError("membership_capture_window must be a JSON object")
    _require_exact_fields(
        window,
        _WINDOW_FIELDS,
        label="membership_capture_window",
    )
    capture_start = _aware_datetime(
        window["start"],
        field="membership_capture_window.start",
    )
    capture_end = _aware_datetime(
        window["end"],
        field="membership_capture_window.end",
    )
    if capture_start > capture_end:
        raise ValueError("membership capture window is reversed")
    if captured_at > capture_end:
        raise ValueError("artifact captured_at follows its membership capture window")

    catalog_shape = raw["catalog_shape"]
    if not isinstance(catalog_shape, Mapping):
        raise ValueError("catalog_shape must be a JSON object")
    _require_exact_fields(
        catalog_shape,
        _CATALOG_SHAPE_FIELDS,
        label="catalog_shape",
    )
    broad_count = _positive_int(catalog_shape["broad_881"], field="broad_881")
    granular_count = _positive_int(
        catalog_shape["granular_884"],
        field="granular_884",
    )

    mapping_result = raw["mapping_result"]
    if not isinstance(mapping_result, Mapping):
        raise ValueError("mapping_result must be a JSON object")
    _require_exact_fields(
        mapping_result,
        _MAPPING_RESULT_FIELDS,
        label="mapping_result",
    )
    unique_count = _non_negative_int(
        mapping_result["unique_full_containment"],
        field="unique_full_containment",
    )
    ambiguous_count = _non_negative_int(
        mapping_result["ambiguous"],
        field="ambiguous",
    )
    unmapped_count = _non_negative_int(
        mapping_result["unmapped"],
        field="unmapped",
    )
    duplicate_count = _non_negative_int(
        mapping_result["exact_duplicate_granular_member_sets"],
        field="exact_duplicate_granular_member_sets",
    )
    broad_overlap_count = _non_negative_int(
        mapping_result["overlapping_broad_member_sets"],
        field="overlapping_broad_member_sets",
    )
    parents_with_children = _non_negative_int(
        mapping_result["parents_with_granular_children"],
        field="parents_with_granular_children",
    )
    broad_without_children = _non_negative_int(
        mapping_result["broad_parents_without_granular_children"],
        field="broad_parents_without_granular_children",
    )
    if unique_count != granular_count or ambiguous_count or unmapped_count:
        raise ValueError("sector parent-hint mapping is not complete and unique")
    if duplicate_count or broad_overlap_count:
        raise ValueError("sector parent-hint source contains unresolved set overlap")
    if parents_with_children + broad_without_children != broad_count:
        raise ValueError("sector parent-hint broad-parent counts do not reconcile")

    use_semantics = raw["use_semantics"]
    if not isinstance(use_semantics, Mapping):
        raise ValueError("use_semantics must be a JSON object")
    _require_exact_fields(use_semantics, _USE_FIELDS, label="use_semantics")
    expected_semantics = {
        "purpose": SECTOR_PARENT_HINT_SEMANTICS,
        "catalog_rule": (
            "CURRENT_CATALOG_IDENTITY_AND_HASH_MUST_BE_CHECKED_EXPLICITLY"
        ),
        "membership_rule": (
            "FETCH_CANDIDATE_CHILD_AND_HINTED_PARENT_CURRENT_MEMBERSHIPS_"
            "AND_REVALIDATE_FULL_CONTAINMENT_BEFORE_GROUPING"
        ),
        "failure_rule": (
            "CATALOG_OR_CONTAINMENT_DRIFT_REMAINS_VISIBLE_AND_PREVENTS_"
            "AUTOMATIC_GROUPING"
        ),
        "historical_taxonomy_authority": "NONE",
        "research_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    if dict(use_semantics) != expected_semantics:
        raise ValueError("sector parent-hint use semantics disagree with v0")

    raw_hint_items = raw["parent_hints"]
    if not isinstance(raw_hint_items, list):
        raise ValueError("parent_hints must be a JSON array")
    hints = tuple(
        _parse_hint(
            item,
            index=index,
            capture_start=capture_start,
            capture_end=capture_end,
        )
        for index, item in enumerate(raw_hint_items)
    )
    if len(hints) != granular_count:
        raise ValueError("parent-hint count disagrees with granular catalog shape")
    if tuple(hint.child_thscode for hint in hints) != tuple(
        sorted(hint.child_thscode for hint in hints)
    ):
        raise ValueError("sector parent hints must be sorted by child identity")
    hint_by_child = {hint.child_thscode: hint for hint in hints}
    if len(hint_by_child) != len(hints):
        raise ValueError("sector parent hints contain duplicate child identities")

    parent_identity: dict[str, tuple[str, int, str, datetime]] = {}
    for hint in hints:
        identity = (
            hint.parent_name,
            hint.parent_member_count_at_capture,
            hint.parent_constituent_set_hash_at_capture,
            hint.parent_membership_captured_at,
        )
        previous = parent_identity.setdefault(hint.parent_thscode, identity)
        if previous != identity:
            raise ValueError(
                "sector parent hints contain inconsistent frozen parent identity"
            )
    if len(parent_identity) != parents_with_children:
        raise ValueError("sector parent-hint distinct parent count disagrees")

    return SectorParentHintIndex(
        schema_version=SECTOR_PARENT_HINT_SCHEMA_VERSION,
        captured_at=captured_at,
        membership_capture_start=capture_start,
        membership_capture_end=capture_end,
        source=_non_empty_string(raw["source"], field="source"),
        source_workflow_run_id=_positive_int(
            raw["source_workflow_run_id"],
            field="source_workflow_run_id",
        ),
        source_artifact_id=_positive_int(
            raw["source_artifact_id"],
            field="source_artifact_id",
        ),
        source_artifact_digest=_sha256(
            raw["source_artifact_digest"],
            field="source_artifact_digest",
            prefixed=True,
        ),
        source_result_hash=_sha256(
            raw["source_result_hash"],
            field="source_result_hash",
        ),
        catalog_hash=_sha256(raw["catalog_hash"], field="catalog_hash"),
        broad_count=broad_count,
        granular_count=granular_count,
        parents_with_granular_children=parents_with_children,
        broad_parents_without_granular_children=broad_without_children,
        mapping_hash=claimed_mapping_hash,
        hints=hints,
        hint_by_child=hint_by_child,
    )


def load_sector_parent_hints(path: Path) -> SectorParentHintIndex:
    """Load one explicit repository-owned hint file; no default or fallback path."""

    return parse_sector_parent_hints(path.read_text(encoding="utf-8"))


def sector_parent_hint_for_child(
    hints: SectorParentHintIndex,
    *,
    child_thscode: str,
) -> SectorParentHint:
    normalized_child = child_thscode.strip().upper()
    hint = hints.hint_by_child.get(normalized_child)
    if hint is None:
        raise ValueError(
            f"no frozen current parent hint exists for {normalized_child}"
        )
    return hint


def validate_sector_parent_hint_catalog(
    *,
    hints: SectorParentHintIndex,
    catalog: HithinkIndustryCatalog,
) -> SectorParentHintCatalogValidation:
    """Require the exact current formal-industry catalog used by the frozen hints."""

    if catalog.unexpected_industries:
        raise ValueError("current industry catalog contains unexpected identity families")
    if catalog.catalog_hash != hints.catalog_hash:
        raise ValueError("current industry catalog hash disagrees with parent hints")
    if len(catalog.broad_industries) != hints.broad_count:
        raise ValueError("current broad-industry count disagrees with parent hints")
    if len(catalog.granular_industries) != hints.granular_count:
        raise ValueError("current granular-industry count disagrees with parent hints")

    broad_by_code = {item.thscode: item.name for item in catalog.broad_industries}
    granular_by_code = {
        item.thscode: item.name for item in catalog.granular_industries
    }
    if set(granular_by_code) != set(hints.hint_by_child):
        raise ValueError("current granular-industry identities disagree with parent hints")

    for hint in hints.hints:
        if granular_by_code.get(hint.child_thscode) != hint.child_name:
            raise ValueError(
                f"current child catalog identity disagrees for {hint.child_thscode}"
            )
        if broad_by_code.get(hint.parent_thscode) != hint.parent_name:
            raise ValueError(
                f"current parent catalog identity disagrees for {hint.parent_thscode}"
            )

    return SectorParentHintCatalogValidation(
        mapping_hash=hints.mapping_hash,
        frozen_catalog_hash=hints.catalog_hash,
        current_catalog_hash=catalog.catalog_hash,
        broad_count=len(catalog.broad_industries),
        granular_count=len(catalog.granular_industries),
        validated_child_count=len(hints.hints),
    )


def revalidate_current_sector_parent_hint(
    *,
    hints: SectorParentHintIndex,
    catalog: HithinkIndustryCatalog,
    child_thscode: str,
    child_membership: SectorMembershipSnapshot,
    parent_membership: SectorMembershipSnapshot,
) -> SectorParentHintRevalidation:
    """Revalidate one hinted parent against exact current candidate memberships.

    The function never searches for a replacement parent. Catalog or containment
    drift remains visible and prevents automatic grouping.
    """

    catalog_validation = validate_sector_parent_hint_catalog(
        hints=hints,
        catalog=catalog,
    )
    hint = sector_parent_hint_for_child(
        hints,
        child_thscode=child_thscode,
    )
    if child_membership.sector_thscode != hint.child_thscode:
        raise ValueError("current child membership does not match the hinted child")
    if child_membership.sector_name != hint.child_name:
        raise ValueError("current child membership name disagrees with parent hint")
    if parent_membership.sector_thscode != hint.parent_thscode:
        raise ValueError("current parent membership is not the hinted parent")
    if parent_membership.sector_name != hint.parent_name:
        raise ValueError("current parent membership name disagrees with parent hint")

    current_link = build_current_parent_link(
        parent=parent_membership,
        child=child_membership,
    )
    if not current_link.child_fully_contained:
        raise ValueError(
            "current child membership is no longer fully contained in the hinted parent"
        )

    return SectorParentHintRevalidation(
        mapping_hash=hints.mapping_hash,
        catalog_validation=catalog_validation,
        hint=hint,
        current_parent_link=current_link,
        child_membership_changed_since_hint_capture=(
            child_membership.constituent_set_hash
            != hint.child_constituent_set_hash_at_capture
        ),
        parent_membership_changed_since_hint_capture=(
            parent_membership.constituent_set_hash
            != hint.parent_constituent_set_hash_at_capture
        ),
        child_member_count_changed_since_hint_capture=(
            len(child_membership.members) != hint.child_member_count_at_capture
        ),
        parent_member_count_changed_since_hint_capture=(
            len(parent_membership.members) != hint.parent_member_count_at_capture
        ),
    )
