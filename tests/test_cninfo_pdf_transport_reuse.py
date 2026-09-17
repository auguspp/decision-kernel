from __future__ import annotations

import pytest

from decision_kernel.runtime import hithink_dump_trial as transport
from decision_kernel.runtime.cninfo_http import (
    CninfoPdfByteLimitError,
    CninfoPdfContainerError,
    CninfoPdfHttpError,
    CninfoPdfTransportError,
    fetch_cninfo_pdf_bytes,
)

URL = "https://static.cninfo.com.cn/finalpage/2026-08-22/1225490206.PDF"


class Response:
    def __init__(self, payload: bytes, *, status=200, headers=None, chunks=None):
        self.payload = payload
        self.status_code = status
        self.headers = ({"Content-Encoding": "identity", "Content-Length": str(len(payload))}
                        if headers is None else headers)
        self._chunks = list(chunks) if chunks is not None else [payload]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_content(self, *, chunk_size):
        assert chunk_size == 65536
        yield from self._chunks


class Session:
    def __init__(self, response: Response, seen: list[tuple]):
        self.response = response
        self.seen = seen

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, url, **kwargs):
        self.seen.append((url, kwargs))
        return self.response


def install(monkeypatch, response):
    seen = []
    monkeypatch.setattr(transport, "_session", lambda: Session(response, seen))
    return seen


def test_default_pdf_transport_reuses_identity_encoded_no_redirect_stream(monkeypatch):
    payload = b"%PDF-1.7\nqualified"
    seen = install(monkeypatch, Response(payload))

    assert fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024, timeout_seconds=45) == payload
    assert len(seen) == 1
    url, kwargs = seen[0]
    assert url == URL
    assert kwargs == {
        "headers": {"Accept": "application/pdf", "Accept-Encoding": "identity"},
        "timeout": (10, 45),
        "stream": True,
        "allow_redirects": False,
    }


def test_static_pdf_http_rejection_has_finite_retained_error_type(monkeypatch):
    install(monkeypatch, Response(b"", status=403,
        headers={"Content-Encoding": "identity", "Content-Length": "1"}))
    with pytest.raises(CninfoPdfHttpError) as caught:
        fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024)
    assert type(caught.value).__name__ == "CninfoPdfHttpError"
    assert not hasattr(caught.value, "response")


def test_pdf_byte_length_encoding_and_container_fail_closed(monkeypatch):
    payload = b"%PDF-1.7-too-large"
    install(monkeypatch, Response(payload))
    with pytest.raises(CninfoPdfByteLimitError):
        fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=8)

    install(monkeypatch, Response(b"%PDF-x", headers={"Content-Encoding": "gzip"}))
    with pytest.raises(CninfoPdfTransportError):
        fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024)

    install(monkeypatch, Response(b"<html>not pdf</html>"))
    with pytest.raises(CninfoPdfContainerError):
        fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024)


def test_response_length_mismatch_is_transport_failure(monkeypatch):
    response = Response(b"%PDF-1.7\nbody", headers={"Content-Encoding": "identity", "Content-Length": "99"})
    install(monkeypatch, response)
    with pytest.raises(CninfoPdfTransportError):
        fetch_cninfo_pdf_bytes(source_locator=URL, max_bytes=1024)
