from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping
from zoneinfo import ZoneInfo


CNINFO_STOCK_MAP_SOURCE = "CNINFO official stock organization mapping"
CNINFO_ANNOUNCEMENT_SOURCE = "CNINFO official announcement search"
CNINFO_STATIC_BASE_URL = "https://static.cninfo.com.cn"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
_STOCK_CODE = re.compile(r"^\d{6}$")


class CninfoAdapterError(ValueError):
    """A CNINFO payload cannot satisfy the bounded official-disclosure contract."""


@dataclass(frozen=True)
class CninfoAnnouncement:
    announcement_id: str
    stock_code: str
    org_id: str
    title: str
    announcement_type: str | None
    published_at: datetime | None
    source_locator: str


@dataclass(frozen=True)
class CninfoAnnouncementPage:
    total_announcement_count: int
    announcements: tuple[CninfoAnnouncement, ...]


def normalize_cninfo_org_map(payload: Mapping[str, Any]) -> dict[str, str]:
    """Normalize CNINFO's official stock-code -> orgId table without guessing IDs."""

    stock_list = payload.get("stockList")
    if not isinstance(stock_list, list) or not stock_list:
        raise CninfoAdapterError("CNINFO stock organization mapping is empty")

    result: dict[str, str] = {}
    for row in stock_list:
        if not isinstance(row, Mapping):
            raise CninfoAdapterError("CNINFO stock organization mapping has a malformed row")
        code = row.get("code")
        org_id = row.get("orgId")
        if not isinstance(code, str) or not _STOCK_CODE.fullmatch(code.strip()):
            raise CninfoAdapterError("CNINFO stock organization mapping has an invalid code")
        if not isinstance(org_id, str) or not org_id.strip():
            raise CninfoAdapterError("CNINFO stock organization mapping has an empty orgId")
        normalized_code = code.strip()
        normalized_org_id = org_id.strip()
        existing = result.get(normalized_code)
        if existing is not None and existing != normalized_org_id:
            raise CninfoAdapterError(
                "CNINFO stock organization mapping contains conflicting orgIds"
            )
        result[normalized_code] = normalized_org_id
    return result


def resolve_cninfo_org_id(payload: Mapping[str, Any], *, stock_code: str) -> str:
    """Resolve one exact official orgId; a missing mapping is an acquisition failure."""

    normalized_code = _normalize_stock_code(stock_code)
    org_id = normalize_cninfo_org_map(payload).get(normalized_code)
    if org_id is None:
        raise CninfoAdapterError(
            f"CNINFO official organization mapping has no row for {normalized_code}"
        )
    return org_id


def normalize_cninfo_announcement_page(
    payload: Mapping[str, Any],
    *,
    stock_code: str,
    org_id: str,
) -> CninfoAnnouncementPage:
    """Normalize one CNINFO page while preserving official identity and source location."""

    normalized_code = _normalize_stock_code(stock_code)
    normalized_org_id = org_id.strip()
    if not normalized_org_id:
        raise CninfoAdapterError("CNINFO orgId must be non-empty")

    total = payload.get("totalAnnouncement")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise CninfoAdapterError("CNINFO announcement total is invalid")
    rows = payload.get("announcements")
    if not isinstance(rows, list):
        raise CninfoAdapterError("CNINFO announcements are not a list")

    announcements: list[CninfoAnnouncement] = []
    seen_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise CninfoAdapterError("CNINFO announcement page has a malformed row")

        announcement_id = _required_text(row.get("announcementId"), "announcementId")
        title = _required_text(row.get("announcementTitle"), "announcementTitle")
        adjunct_url = _required_text(row.get("adjunctUrl"), "adjunctUrl")
        row_code = row.get("secCode")
        if row_code is not None and str(row_code).strip() != normalized_code:
            raise CninfoAdapterError("CNINFO announcement row belongs to another security")
        row_org_id = row.get("orgId")
        if row_org_id is not None and str(row_org_id).strip() != normalized_org_id:
            raise CninfoAdapterError("CNINFO announcement row belongs to another orgId")
        if announcement_id in seen_ids:
            raise CninfoAdapterError("CNINFO announcement page contains duplicate IDs")
        seen_ids.add(announcement_id)

        announcement_type = row.get("announcementTypeName")
        if announcement_type is not None:
            announcement_type = str(announcement_type).strip() or None
        published_at = _announcement_timestamp(row.get("announcementTime"))
        announcements.append(
            CninfoAnnouncement(
                announcement_id=announcement_id,
                stock_code=normalized_code,
                org_id=normalized_org_id,
                title=title,
                announcement_type=announcement_type,
                published_at=published_at,
                source_locator=_official_static_url(adjunct_url),
            )
        )

    return CninfoAnnouncementPage(
        total_announcement_count=total,
        announcements=tuple(announcements),
    )


def _normalize_stock_code(stock_code: str) -> str:
    normalized = stock_code.strip()
    if not _STOCK_CODE.fullmatch(normalized):
        raise CninfoAdapterError("CNINFO stock code must be exactly six digits")
    return normalized


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, (str, int)):
        raise CninfoAdapterError(f"CNINFO {field} is missing")
    normalized = str(value).strip()
    if not normalized:
        raise CninfoAdapterError(f"CNINFO {field} is empty")
    return normalized


def _announcement_timestamp(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise CninfoAdapterError("CNINFO announcementTime is invalid")
    try:
        milliseconds = int(value)
    except (TypeError, ValueError) as exc:
        raise CninfoAdapterError("CNINFO announcementTime is invalid") from exc
    if milliseconds <= 0:
        raise CninfoAdapterError("CNINFO announcementTime is invalid")
    try:
        return datetime.fromtimestamp(milliseconds / 1000, tz=SHANGHAI_TZ)
    except (OverflowError, OSError, ValueError) as exc:
        raise CninfoAdapterError("CNINFO announcementTime is out of range") from exc


def _official_static_url(adjunct_url: str) -> str:
    normalized = adjunct_url.strip()
    if normalized.startswith("https://static.cninfo.com.cn/"):
        return normalized
    if "://" in normalized:
        raise CninfoAdapterError("CNINFO adjunctUrl points outside the official static host")
    return f"{CNINFO_STATIC_BASE_URL}/{normalized.lstrip('/')}"
