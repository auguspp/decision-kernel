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
    SHANGHAI_TZ,
    CninfoAdapterError,
    CninfoAnnouncement,
    normalize_cninfo_announcement_page,
    resolve_cninfo_org_id,
)
from ..adapters.pdf_text import MAX_PDF_BYTES


CNINFO_LEGACY_STOCK_MAP_URL = "https://www.cninfo.com.cn/new/data/szse_stock.json"
CNINFO_STOCK_MAP_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_ORG_SEARCH_URL = CNINFO_STOCK_MAP_URL  # compatibility alias for the current identity lookup
CNINFO_ANNOUNCEMENT_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_ANNOUNCEMENT_HTTPS_URL = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_DISCLOSURE_STOCK_URL = "http://www.cninfo.com.cn/new/disclosure/stock"
DEFAULT_PAGE_SIZE = 30
_MAX_PAGE_SIZE = 30
_GetJSON = Callable[[str], Mapping[str, Any]]
_PostJSON = Callable[[str, Mapping[str, str]], Any]
_GetBytes = Callable[[str], bytes]


class CninfoRuntimeError(RuntimeError):
    """The outer CNINFO runtime could not produce a coherent official-disclosure batch."""


# Finite PDF-stage exception types are deliberately safe to retain by class name.
# They never contain response bodies, cookies, headers, source bytes or credentials.
class CninfoPdfSourceError(CninfoRuntimeError):
    """The selected source is not the exact reviewed CNINFO static-PDF destination."""


class CninfoPdfHttpError(CninfoRuntimeError):
    """The official static host rejected the bounded request."""


class CninfoPdfTransportError(CninfoRuntimeError):
    """The bounded official static-host request could not complete coherently."""


class CninfoPdfByteLimitError(CninfoRuntimeError):
    """The official body exceeded the declared acquisition byte budget."""


class CninfoPdfContainerError(CninfoRuntimeError):
    """The returned body was not an exact PDF container."""


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
        org_rows = post_json(
            CNINFO_STOCK_MAP_URL,
            {"keyWord": stock_code.strip(), "maxNum": "10"},
        )
        if not isinstance(org_rows, list):
            raise CninfoRuntimeError("CNINFO org search response is not a JSON array")
        org_id = resolve_cninfo_org_id(
            {"stockList": org_rows},
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
            end_date=end_date,
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

    The default byte transport reuses the repository's already-live-accepted fresh
    Requests session pattern used for bounded CNINFO static-PDF capture: identity
    encoding, no redirects, no retries/cookies/proxies/credentials and streaming
    under the caller's exact byte limit. Metadata acquisition remains separate.
    """

    locator = source_locator.strip()
    if not locator.startswith(f"{CNINFO_STATIC_BASE_URL}/"):
        raise CninfoPdfSourceError("CNINFO PDF source must use the official static host")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise CninfoPdfByteLimitError("CNINFO PDF max_bytes must be a positive integer")

    if get_bytes is None:
        payload = _request_pdf_bytes(
            url=locator,
            max_bytes=max_bytes,
            timeout_seconds=timeout_seconds,
        )
    else:
        payload = get_bytes(locator)

    if not isinstance(payload, bytes):
        raise CninfoPdfTransportError("CNINFO PDF fetcher did not return bytes")
    if len(payload) > max_bytes:
        raise CninfoPdfByteLimitError(f"CNINFO PDF exceeds the {max_bytes}-byte acquisition limit")
    if not payload.startswith(b"%PDF-"):
        raise CninfoPdfContainerError("CNINFO PDF response does not start with a PDF header")
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


def _announcement_disclosure_referer(form: Mapping[str, str] | None) -> str:
    """Build only CNINFO's issuer disclosure-page locator from the exact bound form."""

    stock = None if form is None else form.get("stock")
    if isinstance(stock, str) and stock.count(",") == 1:
        stock_code, org_id = (part.strip() for part in stock.split(",", 1))
        if stock_code and org_id:
            return CNINFO_DISCLOSURE_STOCK_URL + "?" + urlencode(
                {"stockCode": stock_code, "orgId": org_id}
            )
    return "http://www.cninfo.com.cn/new/disclosure"


def _request_json(
    *,
    url: str,
    method: str,
    form: Mapping[str, str] | None,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    stage = {
        ("GET", CNINFO_LEGACY_STOCK_MAP_URL): "SECURITY_MAP",
        ("GET", CNINFO_STOCK_MAP_URL): "SECURITY_MAP",
        ("POST", CNINFO_STOCK_MAP_URL): "ORG_SEARCH",
        ("POST", CNINFO_ANNOUNCEMENT_QUERY_URL): "ANNOUNCEMENT_QUERY",
        ("POST", CNINFO_ANNOUNCEMENT_HTTPS_URL): "ANNOUNCEMENT_QUERY",
    }.get((method, url), "UNCLASSIFIED_JSON_ENDPOINT")
    body = None if form is None else urlencode(form).encode("utf-8")
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.cninfo.com.cn/",
    }
    if stage == "ANNOUNCEMENT_QUERY":
        headers["Referer"] = _announcement_disclosure_referer(form)
    if form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise CninfoRuntimeError(
            f"CNINFO HTTP request failed with status {exc.code} [stage={stage}]"
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CninfoRuntimeError(f"CNINFO request or response decoding failed [stage={stage}]") from exc
    if stage == "ORG_SEARCH":
        if not isinstance(payload, list):
            raise CninfoRuntimeError(f"CNINFO response is not a JSON array [stage={stage}]")
        return payload
    if not isinstance(payload, Mapping):
        raise CninfoRuntimeError(f"CNINFO response is not a JSON object [stage={stage}]")
    return payload


def _request_pdf_bytes(*, url: str, max_bytes: int, timeout_seconds: float) -> bytes:
    """Reuse the proven bounded Requests transport; never retry or follow redirects."""
    from .hithink_dump_trial import DumpTrialError, _check_response, _session
    import requests

    try:
        with _session() as session:
            with session.get(
                url,
                headers={"Accept": "application/pdf", "Accept-Encoding": "identity"},
                timeout=(10, timeout_seconds),
                stream=True,
                allow_redirects=False,
            ) as response:
                length = _check_response(response)
                if length is not None and length > max_bytes:
                    raise CninfoPdfByteLimitError("CNINFO PDF response exceeds acquisition limit")
                chunks: list[bytes] = []
                count = 0
                for chunk in response.iter_content(chunk_size=65536):
                    count += len(chunk)
                    if count > max_bytes:
                        raise CninfoPdfByteLimitError("CNINFO PDF response exceeds acquisition limit")
                    chunks.append(chunk)
                if length is not None and count != length:
                    raise CninfoPdfTransportError("CNINFO PDF response length differs")
                return b"".join(chunks)
    except CninfoRuntimeError:
        raise
    except DumpTrialError as exc:
        if exc.code == "HTTP_REJECTED":
            raise CninfoPdfHttpError("CNINFO PDF HTTP request rejected") from exc
        raise CninfoPdfTransportError("CNINFO PDF HTTP response qualification failed") from exc
    except requests.RequestException as exc:
        raise CninfoPdfTransportError("CNINFO PDF request failed") from exc