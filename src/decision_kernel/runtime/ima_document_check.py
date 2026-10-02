"""One explicitly requested IMA candidate; private bytes never leave this process.

Reuses the IMA get_media_info contract inspected in Tencent/WeKnora, not its
sync engine. A successful parser check is not report reading or Research.
"""
from __future__ import annotations

import http.client
import io
import ipaddress
import multiprocessing
import os
import re
import socket
import ssl
import time
from hashlib import sha256
from urllib.parse import unquote, urlsplit

from . import ima_private_probe as p

MAX_PDF = 8 * 1024 * 1024
MAX_PAGES = 80
# Only returned Tencent storage URLs, not an arbitrary URL downloader.
HOST_SUFFIXES = (".myqcloud.com", ".qq.com", ".qpic.cn", ".tencentcos.cn")


def select_document(rows: list[dict], terms: str) -> tuple[dict | None, int]:
    """First provider-order title match; no claim of date, ranking or uniqueness."""
    tokens = p.query(terms).casefold().split()
    p.require(1 <= len(tokens) <= 6, "TITLE_TERMS")
    matches = {}
    for row in rows:
        if all(t in row["title"].casefold() for t in tokens):
            key = row["media_id"]
            p.require(key not in matches or matches[key]["title"] == row["title"], "CANDIDATE_ID_CONFLICT")
            matches.setdefault(key, row)
    return next(iter(matches.values()), None), len(matches)


def media_spec(media_id: str) -> dict:
    p._private_string(media_id, "MEDIA_ID", limit=256)
    return {"endpoint": "get_media_info", "url": p.BASE + "get_media_info", "body": {"media_id": media_id}}


def download_target(url_info: dict) -> tuple[str, str, dict]:
    p.require(isinstance(url_info, dict), "FILE_ACCESS_SHAPE")
    url = url_info.get("url")
    p.require(isinstance(url, str) and 0 < len(url) <= 16384 and url.isascii()
              and not any(ord(c) <= 32 or ord(c) == 127 for c in url) and "\\" not in url, "FILE_URL")
    try:
        u = urlsplit(url)
        port = u.port
    except ValueError:
        raise p.ProbeError("FILE_URL") from None
    host = u.hostname or ""
    p.require(u.scheme == "https" and port in (None, 443) and not u.username and not u.password
              and not u.fragment and any(host.endswith(s) for s in HOST_SUFFIXES)
              and re.fullmatch(r"[a-z0-9.-]+", host) is not None, "FILE_HOST_NOT_ALLOWED")
    supplied = url_info.get("headers", {})
    p.require(isinstance(supplied, dict) and len(supplied) <= 12, "FILE_HEADERS")
    headers = {}
    for k, v in supplied.items():
        p.require(isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9-]{1,64}", k) is not None
                  and isinstance(v, str) and len(v) <= 8192 and v.isascii()
                  and not any(ord(c) < 32 or ord(c) == 127 for c in v), "FILE_HEADERS")
        name = k.lower()
        p.require(name not in headers and (name in {"authorization", "referer", "origin"}
                  or name.startswith("x-cos-")), "FILE_HEADER_NOT_ALLOWED")
        headers[name] = v
    access_text = unquote(unquote(url)) + " " + " ".join(headers.values())
    for name in ("IMA_OPENAPI_CLIENTID", "IMA_OPENAPI_APIKEY"):
        value = os.environ.get(name)
        p.require(not value or value not in access_text, "FILE_CREDENTIAL_REFLECTION")
    headers.update({"Host": host, "Accept-Encoding": "identity", "User-Agent": "DecisionKernel-IMA-Document/1"})
    return host, (u.path or "/") + ("?" + u.query if u.query else ""), headers


class _PinnedHTTPS(http.client.HTTPSConnection):
    """One prevalidated IP; original hostname still verified by TLS and Host."""
    def __init__(self, host: str, address: str):
        super().__init__(host, timeout=10, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), timeout=10)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
            self.sock.settimeout(20)
        except Exception:
            sock.close()
            raise


def download_pdf(url_info: dict) -> bytes:
    host, path, headers = download_target(url_info)
    addresses = [r[4][0] for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]
    p.require(bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses), "FILE_DNS_NOT_PUBLIC")
    connection = _PinnedHTTPS(host, addresses[0])
    deadline = time.monotonic() + 40
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        p.require(response.status == 200, "FILE_HTTP_REJECTED", http_status=response.status)
        p.require(response.getheader("Content-Encoding", "identity").lower() in {"identity", ""}, "FILE_ENCODING")
        length = response.getheader("Content-Length")
        p.require(length is None or length.isascii() and length.isdigit() and 0 < int(length) <= MAX_PDF, "FILE_SIZE")
        chunks, size = [], 0
        while True:
            p.require(time.monotonic() < deadline, "FILE_DEADLINE")
            chunk = response.read(min(65536, MAX_PDF + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            p.require(size <= MAX_PDF, "FILE_SIZE")
        raw = b"".join(chunks)
        p.require(length is None or len(raw) == int(length), "FILE_LENGTH")
        p.require(raw.startswith(b"%PDF-"), "FILE_NOT_PDF")
        return raw
    finally:
        connection.close()


def _parse_pdf(raw: bytes) -> dict:
    from pypdf import PdfReader
    import pypdfium2 as pdfium
    reader = PdfReader(io.BytesIO(raw), strict=True)
    p.require(not reader.is_encrypted and 0 < len(reader.pages) <= MAX_PAGES, "PDF_SCOPE")
    pages = min(3, len(reader.pages))
    characters = 0
    for page in reader.pages[:pages]:
        text = page.extract_text() or ""
        p.require(len(text) <= 160000, "PDF_TEXT_SIZE")
        characters += len(text.strip())
    with pdfium.PdfDocument(raw) as document:
        p.require(len(document) == len(reader.pages), "PDF_PAGE_COUNT")
        page = document[0]
        try:
            width, height = page.get_size()
            p.require(0 < width <= 4000 and 0 < height <= 4000, "PDF_PAGE_SIZE")
            bitmap = page.render(scale=0.5)
            try:
                p.require(bitmap.width > 0 and bitmap.height > 0, "PDF_RENDER")
            finally:
                bitmap.close()
        finally:
            page.close()
    return {"status": "PDF_MACHINE_READABLE" if characters else "PDF_RENDERABLE_TEXT_UNAVAILABLE",
            "pdf_pages": len(reader.pages), "text_pages_checked": pages, "text_characters": characters,
            "first_page_rendered": True, "semantic_reading": "NOT_PERFORMED"}


def _pdf_worker(raw: bytes, pipe):
    # Native/Python parser diagnostics can contain source text. Suppress at FD
    # level as well as returning only a fixed safe error code. No raw file output.
    with open(os.devnull, "wb") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    for name in ("IMA_OPENAPI_CLIENTID", "IMA_OPENAPI_APIKEY", "GH_TOKEN", "GITHUB_TOKEN"):
        os.environ.pop(name, None)
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
        result = _parse_pdf(raw)
    except Exception:
        result = {"status": "PDF_PARSE_FAILED", "semantic_reading": "NOT_PERFORMED"}
    pipe.send(result)
    pipe.close()


def inspect_pdf(raw: bytes) -> dict:
    p.require(isinstance(raw, bytes) and raw.startswith(b"%PDF-") and len(raw) <= MAX_PDF, "FILE_NOT_PDF")
    ctx = multiprocessing.get_context("spawn")
    receiver, sender = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_pdf_worker, args=(raw, sender), daemon=True)
    try:
        process.start()
        sender.close()
        process.join(20)
        if process.is_alive():
            process.terminate()
            process.join()
            return {"status": "PDF_PARSE_TIMEOUT", "semantic_reading": "NOT_PERFORMED"}
        if process.exitcode != 0 or not receiver.poll():
            return {"status": "PDF_PARSE_FAILED", "semantic_reading": "NOT_PERFORMED"}
        return receiver.recv()
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None and not process.is_alive():
            process.close()


def check_one_document(rows, terms, *, send, clock, download=download_pdf, inspect=inspect_pdf) -> dict:
    result = {"status": "NOT_SELECTED", "selection": "FIRST_PROVIDER_ORDER_TITLE_MATCH_NOT_LATEST_OR_BEST",
              "title_terms_hash": p.canonical_hash(p.query(terms)), "api_call_attempts": 0, "file_get_attempts": 0,
              "pdf_downloads": 0, "private_retention": "EPHEMERAL_MEMORY_ONLY", "research_delivery": "NOT_PERFORMED"}
    phase = "SELECTION"
    try:
        row, count = select_document(rows, terms)
        result["candidate_matches"] = count
        if row is None:
            return result
        result["selected_hash"] = p.canonical_hash({"id": row["media_id"], "title": row["title"]})
        phase = "MEDIA_ACCESS"
        result["api_call_attempts"] = 1
        data, meta = p._call(media_spec(row["media_id"]), send, clock)
        result["media_response"] = meta
        media_type = data.get("media_type")
        p.require(type(media_type) is int, "MEDIA_TYPE")
        result["media_type"] = media_type
        access = data.get("url_info")
        if media_type != 1:
            result["status"] = "NOT_PDF_NO_DOWNLOAD"
            return result
        if access is None or isinstance(access, dict) and access.get("url") in (None, ""):
            result["status"] = "BODY_UNAVAILABLE_NO_URL"
            return result
        # Validate before counting/starting a download. No access route fallback.
        phase = "DOWNLOAD_TARGET"
        download_target(access)
        phase = "FILE_GET"
        result["file_get_attempts"] = 1
        started = p._clock(clock())
        raw = download(access)
        ended = p._clock(clock())
        p.require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_PDF and raw.startswith(b"%PDF-"), "FILE_NOT_PDF")
        result["pdf_downloads"] = 1
        result["file_response"] = {"requested_at": started, "received_at": ended, "bytes": len(raw),
                                   "sha256": sha256(raw).hexdigest()}
        phase = "PDF_PARSE"
        result["pdf_check"] = inspect(raw)
        result["status"] = result["pdf_check"]["status"]
    except Exception as exc:
        # Source/parser/library exceptions must not print IDs, URLs or headers.
        failure = p.safe_failure(exc)
        result.update(status="CHECK_FAILED", failure_phase=phase, failure_code=failure["failure_code"],
                      http_status=failure["http_status"])
        if "business_code" in failure:
            result["business_code"] = failure["business_code"]
    return result
