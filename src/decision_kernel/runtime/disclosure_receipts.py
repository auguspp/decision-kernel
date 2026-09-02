from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence
from uuid import UUID

from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState

from .disclosure_radar import DisclosureBatch


CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID = "research-funnel-v1"
LEGACY_UNVERSIONED_DISCLOSURE_ASSESSMENT_SEMANTICS_ID = "legacy-unversioned"
ReceiptIdentity = tuple[str, tuple[str, ...], UUID, datetime, str]


def _validate_assessment_semantics_id(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("disclosure assessment semantics id must be non-empty and trimmed")
    return value


@dataclass(frozen=True)
class DisclosureAssessmentReceipt:
    """One Harness receipt for one exact CNINFO batch assessed against frozen Research.

    This is deliberately not a Kernel event, recommendation, queue record, or persistence model.
    It only carries enough identity to avoid re-assessing the same official disclosure batch
    against the same frozen Research state under the same assessment semantics on a later Harness
    run.
    """

    stock_code: str
    announcement_ids: tuple[str, ...]
    research_snapshot_id: UUID
    research_as_of: datetime
    assessment_result: ResearchFunnelTerminalState
    assessed_at: datetime
    assessment_semantics_id: str = CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID
    source_lane: str = "CNINFO"

    def __post_init__(self) -> None:
        if self.source_lane != "CNINFO":
            raise ValueError("disclosure assessment receipt source lane must be CNINFO")
        if not self.stock_code.strip():
            raise ValueError("disclosure assessment receipt requires stock code")
        if not self.announcement_ids:
            raise ValueError("disclosure assessment receipt requires announcement ids")
        if any(not item.strip() for item in self.announcement_ids):
            raise ValueError("disclosure assessment receipt announcement ids must be non-empty")
        if tuple(sorted(set(self.announcement_ids))) != self.announcement_ids:
            raise ValueError("disclosure assessment receipt announcement ids must be unique and sorted")
        if self.research_as_of.utcoffset() is None:
            raise ValueError("disclosure assessment receipt research_as_of must be timezone-aware")
        if self.assessed_at.utcoffset() is None:
            raise ValueError("disclosure assessment receipt assessed_at must be timezone-aware")
        if self.assessed_at < self.research_as_of:
            raise ValueError("disclosure assessment receipt cannot precede frozen Research")
        _validate_assessment_semantics_id(self.assessment_semantics_id)


def disclosure_assessment_receipt_identity(
    receipt: DisclosureAssessmentReceipt,
) -> ReceiptIdentity:
    """Return the exact Harness seen identity, excluding result and observation clock."""

    return (
        receipt.stock_code,
        receipt.announcement_ids,
        receipt.research_snapshot_id,
        receipt.research_as_of,
        receipt.assessment_semantics_id,
    )


def _validate_unique_receipts(
    receipts: Sequence[DisclosureAssessmentReceipt],
) -> tuple[DisclosureAssessmentReceipt, ...]:
    by_identity: dict[ReceiptIdentity, DisclosureAssessmentReceipt] = {}
    for receipt in receipts:
        identity = disclosure_assessment_receipt_identity(receipt)
        previous = by_identity.get(identity)
        if previous is None:
            by_identity[identity] = receipt
            continue
        if previous.assessment_result is not receipt.assessment_result:
            raise ValueError(
                "conflicting disclosure assessment receipts for the same exact batch, frozen Research, and assessment semantics"
            )
        raise ValueError(
            "duplicate disclosure assessment receipt for the same exact batch, frozen Research, and assessment semantics"
        )
    return tuple(receipts)


def parse_disclosure_assessment_receipts(raw_receipts: str) -> tuple[DisclosureAssessmentReceipt, ...]:
    """Parse one explicit JSON receipt file and fail closed on malformed memory state.

    Legacy receipt files without an assessment-semantics field remain readable, but they are marked
    ``legacy-unversioned``. They therefore cannot silently suppress work under the current explicit
    semantics id.
    """

    try:
        payload = json.loads(raw_receipts)
    except json.JSONDecodeError as exc:
        raise ValueError("disclosure receipt file must contain valid JSON") from exc

    if not isinstance(payload, list):
        raise ValueError("disclosure receipt file must be a JSON array")

    required_fields = {
        "source_lane",
        "stock_code",
        "announcement_ids",
        "research_snapshot_id",
        "research_as_of",
        "assessment_result",
        "assessed_at",
    }
    optional_fields = {"assessment_semantics_id"}
    receipts: list[DisclosureAssessmentReceipt] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"disclosure receipt {index} must be a JSON object")
        fields = set(item)
        missing = required_fields - fields
        unknown = fields - required_fields - optional_fields
        if missing:
            raise ValueError(
                f"disclosure receipt {index} missing fields: {', '.join(sorted(missing))}"
            )
        if unknown:
            raise ValueError(
                f"disclosure receipt {index} has unknown fields: {', '.join(sorted(unknown))}"
            )

        string_fields = [
            "source_lane",
            "stock_code",
            "research_snapshot_id",
            "research_as_of",
            "assessment_result",
            "assessed_at",
        ]
        if "assessment_semantics_id" in item:
            string_fields.append("assessment_semantics_id")
        if any(not isinstance(item[field], str) for field in string_fields):
            raise ValueError(f"disclosure receipt {index} scalar fields must be strings")

        announcement_ids = item["announcement_ids"]
        if not isinstance(announcement_ids, list) or not all(
            isinstance(identifier, str) for identifier in announcement_ids
        ):
            raise ValueError(f"disclosure receipt {index} announcement_ids must be a string array")

        try:
            receipt = DisclosureAssessmentReceipt(
                source_lane=item["source_lane"],
                stock_code=item["stock_code"],
                announcement_ids=tuple(announcement_ids),
                research_snapshot_id=UUID(item["research_snapshot_id"]),
                research_as_of=datetime.fromisoformat(item["research_as_of"]),
                assessment_result=ResearchFunnelTerminalState(item["assessment_result"]),
                assessed_at=datetime.fromisoformat(item["assessed_at"]),
                assessment_semantics_id=item.get(
                    "assessment_semantics_id",
                    LEGACY_UNVERSIONED_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
                ),
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"disclosure receipt {index} is invalid: {exc}") from exc
        receipts.append(receipt)

    return _validate_unique_receipts(receipts)


def _receipt_sort_key(receipt: DisclosureAssessmentReceipt) -> tuple:
    return (
        receipt.stock_code,
        receipt.research_as_of,
        str(receipt.research_snapshot_id),
        receipt.assessment_semantics_id,
        receipt.announcement_ids,
    )


def merge_disclosure_assessment_receipts(
    existing: Sequence[DisclosureAssessmentReceipt],
    incoming: Sequence[DisclosureAssessmentReceipt],
) -> tuple[DisclosureAssessmentReceipt, ...]:
    """Idempotently merge exact Harness receipts without silently changing an assessment.

    Re-recording the same exact identity with the same terminal assessment is a no-op and keeps the
    original ``assessed_at`` clock. A different terminal assessment under the same exact semantics
    fails closed. The same batch and frozen Research may be reassessed under a new explicit
    assessment-semantics id without overwriting historical memory.
    """

    _validate_unique_receipts(existing)
    _validate_unique_receipts(incoming)
    merged = {
        disclosure_assessment_receipt_identity(receipt): receipt for receipt in existing
    }
    for receipt in incoming:
        identity = disclosure_assessment_receipt_identity(receipt)
        previous = merged.get(identity)
        if previous is None:
            merged[identity] = receipt
            continue
        if previous.assessment_result is not receipt.assessment_result:
            raise ValueError(
                "conflicting disclosure assessment receipt for the same exact batch, frozen Research, and assessment semantics"
            )
        # Same exact identity and same terminal assessment is intentionally idempotent. Preserve
        # the first assessment clock rather than making memory look newer on every write.

    return tuple(sorted(merged.values(), key=_receipt_sort_key))


def serialize_disclosure_assessment_receipts(
    receipts: Sequence[DisclosureAssessmentReceipt],
) -> str:
    """Serialize validated receipt memory deterministically as one small JSON array."""

    validated = _validate_unique_receipts(receipts)
    ordered = sorted(validated, key=_receipt_sort_key)
    payload = [
        {
            "source_lane": receipt.source_lane,
            "stock_code": receipt.stock_code,
            "announcement_ids": list(receipt.announcement_ids),
            "research_snapshot_id": str(receipt.research_snapshot_id),
            "research_as_of": receipt.research_as_of.isoformat(),
            "assessment_semantics_id": receipt.assessment_semantics_id,
            "assessment_result": receipt.assessment_result.value,
            "assessed_at": receipt.assessed_at.isoformat(),
        }
        for receipt in ordered
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_disclosure_assessment_receipts(
    path: Path,
    receipts: Sequence[DisclosureAssessmentReceipt],
) -> None:
    """Atomically replace one explicit Harness receipt JSON file.

    The caller owns the path and lifecycle. This is deliberately a file write, not a repository,
    database, event store, locking service, or scheduler abstraction.
    """

    serialized = serialize_disclosure_assessment_receipts(receipts)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def disclosure_batch_announcement_ids(batch: DisclosureBatch) -> tuple[str, ...]:
    """Return the stable exact announcement-set identity for one dated batch."""

    return tuple(sorted(item.announcement_id for item in batch.announcements))


def filter_unassessed_disclosure_batches(
    batches: Sequence[DisclosureBatch],
    *,
    research_identity_by_stock: Mapping[str, tuple[UUID, datetime]],
    receipts: Sequence[DisclosureAssessmentReceipt],
    assessment_semantics_id: str = CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
) -> tuple[DisclosureBatch, ...]:
    """Suppress only exact batches assessed under the same Research and assessment semantics.

    A same-day batch with a changed underlying announcement set remains unassessed. A receipt from
    another ResearchSnapshot or another assessment-semantics id also does not suppress the batch.
    The function carries no materiality, Research priority, Human wake, or investment-authority
    semantics.
    """

    _validate_unique_receipts(receipts)
    assessment_semantics_id = _validate_assessment_semantics_id(assessment_semantics_id)
    seen = {
        disclosure_assessment_receipt_identity(receipt)
        for receipt in receipts
        if receipt.source_lane == "CNINFO"
    }

    unassessed: list[DisclosureBatch] = []
    for batch in batches:
        research_identity = research_identity_by_stock.get(batch.stock_code)
        if research_identity is None:
            raise ValueError(f"missing frozen Research identity for {batch.stock_code}")
        research_snapshot_id, research_as_of = research_identity
        if research_as_of.utcoffset() is None:
            raise ValueError(f"frozen Research as-of for {batch.stock_code} must be timezone-aware")

        identity = (
            batch.stock_code,
            disclosure_batch_announcement_ids(batch),
            research_snapshot_id,
            research_as_of,
            assessment_semantics_id,
        )
        if identity not in seen:
            unassessed.append(batch)

    return tuple(unassessed)
