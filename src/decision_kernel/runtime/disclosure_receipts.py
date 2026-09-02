from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence
from uuid import UUID

from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState

from .disclosure_radar import DisclosureBatch


@dataclass(frozen=True)
class DisclosureAssessmentReceipt:
    """One Harness receipt for one exact CNINFO batch assessed against frozen Research.

    This is deliberately not a Kernel event, recommendation, queue record, or persistence model.
    It only carries enough identity to avoid re-assessing the same official disclosure batch
    against the same frozen Research state on a later Harness run.
    """

    stock_code: str
    announcement_ids: tuple[str, ...]
    research_snapshot_id: UUID
    research_as_of: datetime
    assessment_result: ResearchFunnelTerminalState
    assessed_at: datetime
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


def parse_disclosure_assessment_receipts(raw_receipts: str) -> tuple[DisclosureAssessmentReceipt, ...]:
    """Parse one explicit JSON receipt file and fail closed on malformed memory state."""

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
    receipts: list[DisclosureAssessmentReceipt] = []

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"disclosure receipt {index} must be a JSON object")
        fields = set(item)
        missing = required_fields - fields
        unknown = fields - required_fields
        if missing:
            raise ValueError(
                f"disclosure receipt {index} missing fields: {', '.join(sorted(missing))}"
            )
        if unknown:
            raise ValueError(
                f"disclosure receipt {index} has unknown fields: {', '.join(sorted(unknown))}"
            )

        string_fields = (
            "source_lane",
            "stock_code",
            "research_snapshot_id",
            "research_as_of",
            "assessment_result",
            "assessed_at",
        )
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
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"disclosure receipt {index} is invalid: {exc}") from exc
        receipts.append(receipt)

    return tuple(receipts)


def disclosure_batch_announcement_ids(batch: DisclosureBatch) -> tuple[str, ...]:
    """Return the stable exact announcement-set identity for one dated batch."""

    return tuple(sorted(item.announcement_id for item in batch.announcements))


def filter_unassessed_disclosure_batches(
    batches: Sequence[DisclosureBatch],
    *,
    research_identity_by_stock: Mapping[str, tuple[UUID, datetime]],
    receipts: Sequence[DisclosureAssessmentReceipt],
) -> tuple[DisclosureBatch, ...]:
    """Suppress only exact batches already assessed against the same frozen Research.

    A same-day batch with a changed underlying announcement set remains unassessed. A receipt from
    another ResearchSnapshot also does not suppress the batch. The function carries no materiality,
    Research priority, Human wake, or investment-authority semantics.
    """

    seen = {
        (
            receipt.stock_code,
            receipt.announcement_ids,
            receipt.research_snapshot_id,
            receipt.research_as_of,
        )
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
        )
        if identity not in seen:
            unassessed.append(batch)

    return tuple(unassessed)
