"""Offline probes exercise the original Kernel transport; synthetic response bytes."""
import importlib.util
import json
from pathlib import Path
import socket

import pytest
import requests

spec = importlib.util.spec_from_file_location("pdf_transport_probe", Path(__file__).with_name("cninfo_pdf_transport_probe.py"))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BODY = b"%PDF-1.7\nSYNTHETIC NOT COMPANY EVIDENCE\n"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(p, "ROWS", tuple((r[0], r[1], r[2], None) for r in p.ROWS))


class Response:
    def __init__(self, body=BODY, status=200, headers=None):
        self.body, self.status_code = body, status
        self.headers = headers if headers is not None else {"Content-Length": str(len(body))}
        self.reads = 0
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def iter_content(self, **kwargs):
        self.reads += 1
        assert self.status_code == 200, "must not consume a rejected response body"
        yield self.body


def install(monkeypatch, response=None, error=None):
    calls = []
    def send(session, request, **kwargs):
        assert session.trust_env is False and session.auth is None and not session.cookies
        assert not kwargs.get("proxies") and kwargs["allow_redirects"] is False and kwargs["stream"] is True
        assert session.adapters["https://"].max_retries.total == 0
        calls.append(request)
        if error is not None: raise error
        return response if response is not None else Response()
    monkeypatch.setattr(requests.Session, "send", send)
    return calls


def test_six_original_calls_and_candidate_headers(monkeypatch, tmp_path):
    from decision_kernel.runtime import cninfo_http as cninfo, hithink_dump_trial as transport
    original, factory = cninfo.fetch_cninfo_pdf_bytes, transport._session
    invoked = []
    def spy(**kwargs):
        invoked.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(cninfo, "fetch_cninfo_pdf_bytes", spy)
    calls = install(monkeypatch)
    result = p.capture(tmp_path / "out")
    assert len(calls) == len(invoked) == result["request_count"] == 6
    assert transport._session is factory
    assert all(r["status"] == "PDF_RETAINED" for r in result["results"])
    for i, request in enumerate(calls):
        assert request.headers["Accept-Encoding"] == "identity"
        assert "Cookie" not in request.headers and "Authorization" not in request.headers
        if i % 2:
            assert all(request.headers[k] == v for k, v in p.CANDIDATE_HEADERS.items())
        else:
            assert request.headers["Accept"] == "application/pdf" and "Referer" not in request.headers
    assert p.verify(tmp_path / "out") == "RETAINED_PROBE_VERIFIED_NOT_SOURCE_TRUTH"


@pytest.mark.parametrize("status", [301, 403, 404, 429, 500, 503])
def test_rejected_body_never_read_no_retry(monkeypatch, tmp_path, status):
    response = Response(b"SECRET_REMOTE_BODY", status)
    calls = install(monkeypatch, response)
    result = p.capture(tmp_path / "out")
    assert len(calls) == (1 if status == 429 else 6) and response.reads == 0
    first = result["results"][0]
    assert first["diagnostic"] == {"reason_code": "HTTP_REJECTED", "http_status": status}
    assert not list((tmp_path / "out").glob("*.pdf"))
    assert "SECRET" not in json.dumps(result)
    if status == 429:
        assert all(r["status"] == "NOT_ATTEMPTED" for r in result["results"][1:])


def test_dns_failure_stops_not_remote_http(monkeypatch, tmp_path):
    error = requests.ConnectionError("DO_NOT_RETAIN_SECRET")
    error.__cause__ = socket.gaierror(-2, "DO_NOT_RETAIN_HOST")
    calls = install(monkeypatch, error=error)
    result = p.capture(tmp_path / "out")
    assert len(calls) == 1 and result["stop_reason"] == "ENVIRONMENT_DNS_FAILURE"
    assert result["results"][0]["http_status"] is None
    assert "DO_NOT_RETAIN" not in json.dumps(result)


@pytest.mark.parametrize("headers", [{"Content-Encoding": "gzip"}, {"Content-Length": "bad"}, {"Content-Length": str(p.MAX_PDF + 1)}])
def test_original_header_and_size_guards_reused(monkeypatch, tmp_path, headers):
    response = Response(headers=headers)
    install(monkeypatch, response)
    result = p.capture(tmp_path / "out")
    assert response.reads == 0
    assert all(r["status"] == "REJECTED" for r in result["results"])


def test_non_pdf_never_retained(monkeypatch, tmp_path):
    install(monkeypatch, Response(b"<html>not a PDF</html>"))
    result = p.capture(tmp_path / "out")
    assert all(r["diagnostic"]["reason_code"] == "PDF_CONTAINER_REJECTED" for r in result["results"])
    assert not list((tmp_path / "out").glob("*.pdf"))


def test_control_change_stops_and_keeps_actual_bytes(monkeypatch, tmp_path):
    rows = list(p.ROWS)
    rows[0] = (*rows[0][:3], "0" * 64)
    monkeypatch.setattr(p, "ROWS", tuple(rows))
    calls = install(monkeypatch)
    result = p.capture(tmp_path / "out")
    assert len(calls) == 1 and result["stop_reason"] == "CONTROL_CONTENT_CHANGED"
    assert result["results"][0]["expected_hash_match"] is False
    assert len(list((tmp_path / "out").glob("*.pdf"))) == 1


def test_hash_tamper_rejected_and_output_is_create_only(monkeypatch, tmp_path):
    calls = install(monkeypatch)
    p.capture(tmp_path / "out")
    with pytest.raises(FileExistsError): p.capture(tmp_path / "out")
    assert len(calls) == 6
    path = next((tmp_path / "out").glob("*.pdf"))
    path.write_bytes(BODY + b"tampered")
    with pytest.raises(AssertionError): p.verify(tmp_path / "out")


def test_nonempty_query_parameters_still_fail_before_send(monkeypatch, tmp_path):
    original_get = requests.Session.get
    def get_with_query(self, url, **kwargs):
        return original_get(self, url, params={"unexpected": "query"}, **kwargs)
    monkeypatch.setattr(requests.Session, "get", get_with_query)
    calls = install(monkeypatch)
    result = p.capture(tmp_path / "out")
    assert not calls and result["request_count"] == 0
    assert result["stop_reason"] == "ORIGINAL_TRANSPORT_CONTRACT_CHANGED"
    assert all(r["status"] == "NOT_ATTEMPTED" for r in result["results"][1:])
