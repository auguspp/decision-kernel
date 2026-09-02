from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime.disclosure_radar import (
    DisclosureBatchError,
    group_disclosures_by_publication_date,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _announcement(
    identifier: str,
    *,
    code: str = "600036",
    published_at: datetime | None = None,
) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code=code,
        org_id=f"ORG:{code}",
        title=f"公告 {identifier}",
        announcement_type=None,
        published_at=published_at or datetime(2026, 8, 29, 18, 0, tzinfo=SHANGHAI),
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-29/{identifier}.PDF",
    )


def test_group_disclosures_collapses_same_company_same_day_without_dropping_items() -> None:
    earlier = _announcement(
        "A1",
        published_at=datetime(2026, 8, 29, 17, 30, tzinfo=SHANGHAI),
    )
    later = _announcement(
        "A2",
        published_at=datetime(2026, 8, 29, 18, 10, tzinfo=SHANGHAI),
    )

    batches = group_disclosures_by_publication_date((later, earlier))

    assert len(batches) == 1
    batch = batches[0]
    assert batch.stock_code == "600036"
    assert batch.publication_date.isoformat() == "2026-08-29"
    assert batch.first_published_at == earlier.published_at
    assert batch.last_published_at == later.published_at
    assert [item.announcement_id for item in batch.announcements] == ["A1", "A2"]


def test_group_disclosures_keeps_different_security_or_date_separate() -> None:
    batches = group_disclosures_by_publication_date(
        (
            _announcement("A1", code="600036"),
            _announcement("B1", code="601088"),
            _announcement(
                "A2",
                code="600036",
                published_at=datetime(2026, 8, 30, 8, 0, tzinfo=SHANGHAI),
            ),
        )
    )

    assert [
        (batch.stock_code, batch.publication_date.isoformat(), len(batch.announcements))
        for batch in batches
    ] == [
        ("600036", "2026-08-29", 1),
        ("601088", "2026-08-29", 1),
        ("600036", "2026-08-30", 1),
    ]


def test_group_disclosures_requires_auditable_publication_time() -> None:
    missing = _announcement("A1")
    missing = CninfoAnnouncement(
        announcement_id=missing.announcement_id,
        stock_code=missing.stock_code,
        org_id=missing.org_id,
        title=missing.title,
        announcement_type=missing.announcement_type,
        published_at=None,
        source_locator=missing.source_locator,
    )
    naive = _announcement(
        "A2",
        published_at=datetime(2026, 8, 29, 18, 0),
    )

    with pytest.raises(DisclosureBatchError, match="publication timestamp"):
        group_disclosures_by_publication_date((missing,))
    with pytest.raises(DisclosureBatchError, match="publication timestamp"):
        group_disclosures_by_publication_date((naive,))


def test_group_disclosures_rejects_duplicate_official_ids() -> None:
    item = _announcement("A1")

    with pytest.raises(DisclosureBatchError, match="duplicate"):
        group_disclosures_by_publication_date((item, item))
