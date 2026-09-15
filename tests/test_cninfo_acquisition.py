from __future__ import annotations

from datetime import date

import pytest

from decision_kernel.adapters.cninfo import (
    CninfoAdapterError,
    normalize_cninfo_announcement_page,
    resolve_cninfo_org_id,
)
from decision_kernel.runtime.cninfo_http import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNINFO_ORG_SEARCH_URL,
    CninfoRuntimeError,
    fetch_cninfo_disclosures,
)


ORG_MAP = {
    "stockList": [
        {"code": "601318", "orgId": "9900002221"},
        {"code": "601398", "orgId": "jjxt0000019"},
        {"code": "688017", "orgId": "9900041602"},
    ]
}


def _row(identifier: str, *, code: str = "601318", org_id: str = "9900002221") -> dict:
    return {
        "announcementId": identifier,
        "announcementTitle": f"公告 {identifier}",
        "announcementTypeName": "定期报告",
        "announcementTime": 1787932800000,
        "adjunctUrl": f"finalpage/2026-08-29/{identifier}.PDF",
        "secCode": code,
        "orgId": org_id,
    }


def test_cninfo_org_id_uses_official_irregular_mapping_without_guessing() -> None:
    assert resolve_cninfo_org_id(ORG_MAP, stock_code="601318") == "9900002221"
    assert resolve_cninfo_org_id(ORG_MAP, stock_code="601398") == "jjxt0000019"
    assert resolve_cninfo_org_id(ORG_MAP, stock_code="688017") == "9900041602"

    with pytest.raises(CninfoAdapterError, match="has no row"):
        resolve_cninfo_org_id(ORG_MAP, stock_code="600519")


def test_cninfo_page_preserves_official_identity_and_locator() -> None:
    page = normalize_cninfo_announcement_page(
        {"totalAnnouncement": 1, "announcements": [_row("A1")]},
        stock_code="601318",
        org_id="9900002221",
    )
    assert page.total_announcement_count == 1
    announcement = page.announcements[0]
    assert announcement.announcement_id == "A1"
    assert announcement.stock_code == "601318"
    assert announcement.org_id == "9900002221"
    assert announcement.source_locator == "https://static.cninfo.com.cn/finalpage/2026-08-29/A1.PDF"
    assert announcement.published_at is not None
    assert announcement.published_at.utcoffset() is not None


def test_cninfo_page_accepts_live_null_announcements_only_for_zero_total() -> None:
    page = normalize_cninfo_announcement_page(
        {"totalAnnouncement": 0, "announcements": None},
        stock_code="601318",
        org_id="9900002221",
    )
    assert page.total_announcement_count == 0
    assert page.announcements == ()

    with pytest.raises(CninfoAdapterError, match="not a list"):
        normalize_cninfo_announcement_page(
            {"totalAnnouncement": 1, "announcements": None},
            stock_code="601318",
            org_id="9900002221",
        )


def test_cninfo_page_rejects_cross_security_or_external_locator() -> None:
    with pytest.raises(CninfoAdapterError, match="another security"):
        normalize_cninfo_announcement_page(
            {"totalAnnouncement": 1, "announcements": [_row("A1", code="601398")]},
            stock_code="601318",
            org_id="9900002221",
        )

    external = _row("A2")
    external["adjunctUrl"] = "https://example.com/not-cninfo.pdf"
    with pytest.raises(CninfoAdapterError, match="outside the official static host"):
        normalize_cninfo_announcement_page(
            {"totalAnnouncement": 1, "announcements": [external]},
            stock_code="601318",
            org_id="9900002221",
        )


def test_fetch_cninfo_disclosures_paginates_one_coherent_official_batch() -> None:
    post_calls: list[tuple[str, dict[str, str]]] = []

    def post_json(url: str, form: dict[str, str]):
        post_calls.append((url, dict(form)))
        if url == CNINFO_ORG_SEARCH_URL:
            return ORG_MAP["stockList"]
        if form["pageNum"] == "1":
            return {"totalAnnouncement": 3, "announcements": [_row("A1"), _row("A2")]}
        return {"totalAnnouncement": 3, "announcements": [_row("A3")]}

    batch = fetch_cninfo_disclosures(
        stock_code="601318",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
        page_size=2,
        post_json=post_json,
    )

    assert [item.announcement_id for item in batch.announcements] == ["A1", "A2", "A3"]
    assert batch.org_id == "9900002221"
    assert [call[0] for call in post_calls] == [
        CNINFO_ORG_SEARCH_URL,
        CNINFO_ANNOUNCEMENT_QUERY_URL,
        CNINFO_ANNOUNCEMENT_QUERY_URL,
    ]
    assert post_calls[0][1] == {"keyWord": "601318", "maxNum": "10"}
    assert post_calls[1][1]["stock"] == "601318,9900002221"
    assert post_calls[1][1]["seDate"] == "2026-08-01~2026-08-31"
    assert [call[1]["pageNum"] for call in post_calls[1:]] == ["1", "2"]


def test_fetch_cninfo_disclosures_fails_if_result_set_moves_during_pagination() -> None:
    def post_json(url: str, form: dict[str, str]):
        if url == CNINFO_ORG_SEARCH_URL:
            return ORG_MAP["stockList"]
        if form["pageNum"] == "1":
            return {"totalAnnouncement": 3, "announcements": [_row("A1"), _row("A2")]}
        return {"totalAnnouncement": 4, "announcements": [_row("A3")]}

    with pytest.raises(CninfoRuntimeError, match="changed during pagination"):
        fetch_cninfo_disclosures(
            stock_code="601318",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            page_size=2,
            post_json=post_json,
        )


def test_fetch_cninfo_disclosures_allows_a_truthful_empty_window() -> None:
    batch = fetch_cninfo_disclosures(
        stock_code="601318",
        start_date=date(2026, 8, 31),
        end_date=date(2026, 8, 31),
        post_json=lambda url, _form: (ORG_MAP["stockList"] if url == CNINFO_ORG_SEARCH_URL else {
            "totalAnnouncement": 0,
            "announcements": None,
        }),
    )
    assert batch.announcements == ()


def test_fetch_cninfo_disclosures_rejects_invalid_window_or_page_size() -> None:
    with pytest.raises(CninfoRuntimeError, match="start_date"):
        fetch_cninfo_disclosures(
            stock_code="601318",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 8, 31),
            post_json=lambda _url, _form: {},
        )

    with pytest.raises(CninfoRuntimeError, match="page_size"):
        fetch_cninfo_disclosures(
            stock_code="601318",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 31),
            page_size=31,
            post_json=lambda _url, _form: {},
        )
