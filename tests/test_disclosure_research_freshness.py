from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime.disclosure_radar import (
    DisclosureResearchFreshnessError,
    filter_research_uncovered_disclosure_batches,
    group_disclosures_by_publication_date,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = ZoneInfo("UTC")


def _announcement(identifier: str, *, published_at: datetime) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="600036",
        org_id="ORG:600036",
        title=f"公告 {identifier}",
        announcement_type=None,
        published_at=published_at,
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-29/{identifier}.PDF",
    )


def test_freshness_keeps_only_batches_not_fully_covered_by_research() -> None:
    covered = _announcement(
        "A1",
        published_at=datetime(2026, 8, 29, 18, 0, tzinfo=SHANGHAI),
    )
    new = _announcement(
        "A2",
        published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI),
    )
    batches = group_disclosures_by_publication_date((new, covered))

    result = filter_research_uncovered_disclosure_batches(
        batches,
        research_as_of_by_stock={
            "600036": datetime(2026, 8, 30, 0, 0, tzinfo=UTC),
        },
    )

    assert len(result) == 1
    assert [item.announcement_id for item in result[0].announcements] == ["A2"]


def test_freshness_treats_exact_research_as_of_as_covered() -> None:
    item = _announcement(
        "A1",
        published_at=datetime(2026, 8, 29, 18, 0, tzinfo=SHANGHAI),
    )
    batch = group_disclosures_by_publication_date((item,))[0]

    result = filter_research_uncovered_disclosure_batches(
        (batch,),
        research_as_of_by_stock={"600036": item.published_at},
    )

    assert result == ()


def test_freshness_keeps_whole_batch_when_it_straddles_research_clock() -> None:
    earlier = _announcement(
        "A1",
        published_at=datetime(2026, 8, 29, 10, 0, tzinfo=SHANGHAI),
    )
    later = _announcement(
        "A2",
        published_at=datetime(2026, 8, 29, 12, 0, tzinfo=SHANGHAI),
    )
    batch = group_disclosures_by_publication_date((later, earlier))[0]

    result = filter_research_uncovered_disclosure_batches(
        (batch,),
        research_as_of_by_stock={
            "600036": datetime(2026, 8, 29, 11, 0, tzinfo=SHANGHAI),
        },
    )

    assert result == (batch,)
    assert [item.announcement_id for item in result[0].announcements] == ["A1", "A2"]


def test_freshness_requires_exact_aware_research_clock() -> None:
    item = _announcement(
        "A1",
        published_at=datetime(2026, 8, 29, 18, 0, tzinfo=SHANGHAI),
    )
    batch = group_disclosures_by_publication_date((item,))[0]

    with pytest.raises(DisclosureResearchFreshnessError, match="missing frozen Research"):
        filter_research_uncovered_disclosure_batches(
            (batch,),
            research_as_of_by_stock={},
        )

    with pytest.raises(DisclosureResearchFreshnessError, match="timezone-aware"):
        filter_research_uncovered_disclosure_batches(
            (batch,),
            research_as_of_by_stock={"600036": datetime(2026, 8, 30, 0, 0)},
        )
