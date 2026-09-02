from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..adapters.cninfo import (
    CNINFO_STATIC_BASE_URL,
    CninfoAdapterError,
    CninfoAnnouncement,
    normalize_cninfo_announcement_page,
    resolve_cninfo_org_id,
)
from ..adapters.pdf_text import MAX_PDF_BYTES


CNINFO_STOCK_MAP_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_ANNOUNCEMENT_QUERY_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
DEFAULT_PAGE_SIZE = 30
_MAX_PAGE_SIZE = 30
_GetJSON = Callable[[str], Mapping[str, Any]]
_PostJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]
_GetBytes = Callable[[str], bytes]


class CninfoRuntimeError(RuntimeError):
    """The outer CNINFO runtime could not produce a coherent official-disclosure batch."""


@dataclass(frozen=True)
class CninfoDisclosureBatch:
    stock_code: str
    org_id: str
    start_date: date
    end_date: date
    announcements: tuple[CninfoAnnouncement, ...]


def fetch_cninfo_disclosures(
    *,
    stock_code: str,
    start_date: date,
    end_date: date,
    page_size: int = DEFAULT_PAGE_SIZE,
    get_json: _GetJSON | None = None,
    post_json: _PostJSON | None = None,
    timeout_seconds: float = 15.0,
) -> CninfoDisclosureBatch:
    """Fetch one exact CNINFO security/date window without fallback providers or guessed orgIds."""

    if start_date > end_date:
        raise CninfoRuntimeError("CNINFO disclosure start_date must not exceed end_date")
    if isinstance(page_size, bool) or not 1 <= page_size <= _MAX_PAGE_SIZE:
        raise CninfoRuntimeError(
            f"CNINFO page_size must be between 1 and {_MAX_PAGE_SIZE}"
        )

    if get_json is None:
        get_json = lambda url: _request_json(
            url=url,
            method="GET",
            form=None,
            timeout_seconds=timeout_seconds,
        )
    if post_json is None:
        post_json = lambda url, form: _request_json(
            url=url,
            method="POST",
            form=form,
            timeout_seconds=timeout_seconds,
        )

    try:
        org_id = resolve_cninfo_org_id(
            get_json(CNINFO_STOCK_MAP_URL),
            stock_code=stock_code,
        )
    except CninfoAdapterError:
        raise

    collected: list[CninfoAnnouncement] = []
    seen_ids: set[str] = set()
    expected_total: int | None = None
    page_number = 1

    while True:
        form = _announcement_query_form(
            stock_code=stock_code,
            org_id=org_id,
            start_date=start_date,
            end_date=end,
            page_size=page_size,
            page_number=page_number,
        )
        page = normalize_cninfo_announcement_page(
            post_json(CNINFO_ANNOUNCEMENT_QUERY_URL, form),
            stock_code=stock_code,
            org_id=org_id,
        )

        if expected_total is None:
            expected_total = page.total_announcement_count
        elif page.total_announcement_count != expected_total:
            raise CninfoRuntimeError(
                "CNINFO totalAnnouncement changed during pagination; batch is not coherent"
            )

        if expected_total == 0:
            if page.announcements:
                raise CninfoRuntimeError(
                    "CNINFO returned rows while totalAnnouncement is zero"
                )
            break

        if not page.announcements:
            raise CninfoRuntimeError(
                "CNINFO pagination ended before the advertised announcement total"
            )

        for announcement in page.announcements:
            if announcement.announcement_id in seen_ids:
                raise CninfoRuntimeError(
                    "CNINFO pagination repeated an announcement ID; batch is not coherent"
                )
            seen_ids.add(announcement.announcement_id)
            collected.append(announcement)

        if len(collected) >= expected_total:
            break
        page_number += 1

        # A moving upstream result set can otherwise trap the caller in an unbounded loop.
        maximum_pages = (expected_total + page_size - 1) // page_size
        if page_number > maximum_pages:
            raise CninfoRuntimeError(
                "CNINFO pagination exceeded the page count implied by totalAnnouncement"
            )

    if expected_total is None:
        raise CninfoRuntimeError("CNINFO announcement query returned no page metadata")
    if len(collected) != expected_total:
        raise CninfoRuntimeError(
            "CNINFO collected announcement count does not match totalAnnouncement"
        )

    return CninfoDisclosureBatch(
        stock_code=stock_code.strip(),
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        announcements=tuple(collected),
    )


def fetch_cninfo_pdf_bytes(
    *,
    source_locator: str,
    max_bytes: int = MAX_PDF_BYTES,
    get_bytes: _GetBytes | None = None,
    timeout_seconds: float = 15.0,
) -> bytes:
    """Fetch one bounded PDF from CNINFO's official static host only.

    This owns transport qualification only. PDF parsing, text extraction, persistence, OCR,
    caching, retry/fallback and Research interpretation stay outside this runtime seam.
    """

    locator = source_locator.strip()
    if not locator.startswith(f"{CNINFO_STATIC_BASE_URL}/"):
        raise CninfoRuntimeError("CNINFO PDF source must use the official static host")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise CninfoRuntimeError("CNINFO PDF max_bytes must be a positive integer")

    if get_bytes is None:
        payload = _request_pdf_bytes(
            url=locator,
            max_bytes=max_bytes,
            timeout_seconds=timeout_seconds,
        )
    else:
        payload = get_bytes(locator)

    if not isinstance(payload, bytes):
        raise CninfoRuntimeError("CNINFO PDF fetcher did not return bytes")
    if len(payload) > max_bytes:
        raise CninfoRuntimeError(f"CNINFO PDF exceeds the {max_bytes}-byte acquisition limit")
    if not payload.startswith(b"%PDF-"):
        raise CninfoRuntimeError("CNINFO PDF response does not start with a PDF header")
    return payload


def _announcement_query_form(
    *,
    stock_code: str,
    org_id: str,
    start_date: date,
    end_date: date,
    page_size: int,
    page_number: int,
) -> dict[str, str]:
    return {
        "pageSize": str(page_size),
        "pageNum": str(page_number),
        "column": "",
        "tabName": "fulltext",
        "plate": "",
        "stock": f"{stock_code.strip()},{org_id}",
        "searchkey": "",
        "secid": "",
        "category": "",
        "trade": "",
        "seDate": f"{start_date.isoformat()}~{end_date.isoformat()}",
        "sortName": "",
        "sortType": "",
        "isHLtitle": "true",
    }


def _request_json(
    *,
    url: str,
    method: str,
    form: Mapping[str, str] | None,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    body = None if form is None else urlencode(form).encode("utf-8")
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.cninfo.com.cn/",
    }
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise CninfoRuntimeError(
            f"CNINFO HTTP request failed with status {exc.code}"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CninfoRuntimeError("CNINFO request or response decoding failed") from exc
    if not isinstance(payload, Mapping):
        raise CninfoRuntimeError("CNINFO response is not a JSON object")
    return payload


def _request_pdf_bytes(*, url: str, max_bytes: int, timeout_seconds: float) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/pdf,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.cninfo.com.cn/",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            return response.read(max_bytes + 1)
    except HTTPError as exc:
        raise CninfoRuntimeError(
            f"CNINFO PDF request failed with status {exc.code}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise CninfoRuntimeError("CNINFO PDF request failed") from exc
