from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from decision_kernel.adapters.cninfo import CninfoAnnouncement


class DisclosureBatchError(ValueError):
    """Official disclosures cannot be grouped into one trustworthy dated batch set."""


@dataclass(frozen=True)
class DisclosureBatch:
    stock_code: str
    publication_date: date
    first_published_at: datetime
    last_published_at: datetime
    announcements: tuple[CninfoAnnouncement, ...]


def group_disclosures_by_publication_date(
    announcements: Sequence[CninfoAnnouncement],
) -> tuple[DisclosureBatch, ...]:
    """Group exact official announcements by security and publication date.

    This is a Harness de-noising primitive only. It preserves every announcement and does not
    infer materiality, Research priority, Human attention, or investment authority.
    """

    grouped: dict[tuple[str, date], list[CninfoAnnouncement]] = {}
    seen_ids: set[str] = set()

    for item in announcements:
        if item.announcement_id in seen_ids:
            raise DisclosureBatchError("duplicate CNINFO announcement id in batch input")
        seen_ids.add(item.announcement_id)

        published_at = item.published_at
        if published_at is None or published_at.utcoffset() is None:
            raise DisclosureBatchError(
                "CNINFO announcement must have an aware publication timestamp for Radar batching"
            )
        key = (item.stock_code, published_at.date())
        grouped.setdefault(key, []).append(item)

    batches: list[DisclosureBatch] = []
    for (stock_code, publication_date), items in grouped.items():
        ordered = tuple(
            sorted(
                items,
                key=lambda item: (
                    item.published_at,
                    item.announcement_id,
                ),
            )
        )
        published_times = tuple(item.published_at for item in ordered)
        batches.append(
            DisclosureBatch(
                stock_code=stock_code,
                publication_date=publication_date,
                first_published_at=published_times[0],
                last_published_at=published_times[-1],
                announcements=ordered,
            )
        )

    return tuple(
        sorted(
            batches,
            key=lambda batch: (
                batch.publication_date,
                batch.stock_code,
                batch.first_published_at,
            ),
        )
    )
