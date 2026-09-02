from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence

from decision_kernel.adapters.cninfo import CninfoAnnouncement


class DisclosureBatchError(ValueError):
    """Official disclosures cannot be grouped into one trustworthy dated batch set."""


class DisclosureResearchFreshnessError(ValueError):
    """Disclosure freshness cannot be compared against frozen Research clocks."""


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


def filter_research_uncovered_disclosure_batches(
    batches: Sequence[DisclosureBatch],
    *,
    research_as_of_by_stock: Mapping[str, datetime],
) -> tuple[DisclosureBatch, ...]:
    """Keep batches containing at least one disclosure newer than frozen Research.

    Research ``as_of`` is inclusive: a batch whose last underlying announcement was published at
    or before the frozen Research clock is already covered. If a batch straddles the Research
    clock, the whole auditable batch remains eligible because at least one underlying disclosure is
    new; this function does not claim that every announcement in that batch is new or material.

    This is a Harness freshness relation only. It does not infer materiality, route Research,
    trigger Human attention, or carry investment authority.
    """

    uncovered: list[DisclosureBatch] = []
    for batch in batches:
        research_as_of = research_as_of_by_stock.get(batch.stock_code)
        if research_as_of is None:
            raise DisclosureResearchFreshnessError(
                f"missing frozen Research as-of for {batch.stock_code}"
            )
        if research_as_of.utcoffset() is None:
            raise DisclosureResearchFreshnessError(
                f"frozen Research as-of for {batch.stock_code} must be timezone-aware"
            )
        if (
            batch.first_published_at.utcoffset() is None
            or batch.last_published_at.utcoffset() is None
            or batch.first_published_at > batch.last_published_at
        ):
            raise DisclosureResearchFreshnessError(
                f"disclosure batch timestamps for {batch.stock_code} are invalid"
            )

        if batch.last_published_at > research_as_of:
            uncovered.append(batch)

    return tuple(uncovered)
