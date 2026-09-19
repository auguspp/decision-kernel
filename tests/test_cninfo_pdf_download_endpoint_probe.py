"""Offline safety regressions for the CNINFO announcement-download endpoint probe."""
import importlib.util
from pathlib import Path
import socket

import pytest
import requests

MODULE = Path(__file__).resolve().parents[1] / "eval" / "cninfo_pdf_download_endpoint_probe.py"
spec = importlib.util.spec_from_file_location("cninfo_download_endpoint_probe", MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BODY = b"%PDF-1.7\nsynthetic announcement-download fixture\n"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected network")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(p, "SAMPLES", (*p.SAMPLES[:2], (*p.SAMPLES[2][:3], p._sha(BODY))))


class Response:
    def __init__(self, *, status=200, body=BODY, headers=None):
        self.status_code = status
        self.body = body
        self.headers = {"Content-Length": str(len(body))} if headers is None else headers
        self.reads = 0
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_content(self, **kwargs):
        self.reads += 1
        if self.status_code != 200:
            raise AssertionError("rejected body read")
        yield self.body


def session_factory(response=None, error=None):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if error is not None:
                raise error("SECRET_REMOTE_TEXT")
            return response if response is not None else Response()
    return Session, calls


def test_three_fixed_downloads_retain_exact_bytes(tmp_path):
    session, calls = session_factory()
    out = tmp_path / "capture"
    result = p.run_probe(out, {"mode": "SYNTHETIC"}, session_factory=session)
    assert len(calls) == result["attempted_requests"] == 3
    assert all(call[0] == p.ENDPOINT for call in calls)
    assert calls[0][1] == {
        "params": {"bulletinId": "1225486756", "announceTime": "2026-08-21"},
        "headers": p.HEADERS, "timeout": (10, 45), "stream": True, "allow_redirects": False,
    }
    assert all(r["status"] == "PDF_BYTES_RETAINED_NOT_QUALIFIED" for r in result["records"])
    assert p.verify(out) == "RETAINED_DOWNLOAD_ENDPOINT_PROBE_INTEGRITY_CHECKED_NOT_SOURCE_TRUTH"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["remote_failure_cause"] == "UNKNOWN"


@pytest.mark.parametrize("status", [301, 302, 307, 403, 404, 500, True, "403"])
def test_non_200_is_rejected_without_body_read(tmp_path, status):
    response = Response(status=status)
    session, calls = session_factory(response)
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    assert len(calls) == 3
    assert response.reads == 0
    assert result["received_bytes"] == 0
    assert all(r["status"] == "REJECTED" for r in result["records"])
    expected = status if type(status) is int else None
    assert result["records"][0]["http_status"] == expected


def test_exact_static_redirect_is_retained_as_finite_booleans_only(tmp_path):
    headers = {
        "Location": "https://static.cninfo.com.cn/finalpage/2026-08-21/1225486756.PDF",
        "Content-Length": "1",
    }
    session, _ = session_factory(Response(status=302, headers=headers))
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    redirect = result["records"][0]["redirect"]
    assert redirect == {
        "present": True, "https": True,
        "official_static_host": True, "expected_finalpage_path": True,
    }
    text = (tmp_path / "capture" / "result.json").read_text()
    assert "Location" not in text and "https://static.cninfo.com.cn" not in text


def test_foreign_or_mismatched_redirect_never_becomes_locator(tmp_path):
    headers = {"Location": "https://evil.test/finalpage/2026-08-21/1225486756.PDF", "Content-Length": "1"}
    session, _ = session_factory(Response(status=302, headers=headers))
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    redirect = result["records"][0]["redirect"]
    assert redirect["present"] is True
    assert redirect["official_static_host"] is False
    assert "evil.test" not in (tmp_path / "capture" / "result.json").read_text()


def test_429_stops_remaining_requests(tmp_path):
    response = Response(status=429)
    session, calls = session_factory(response)
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    assert len(calls) == 1
    assert result["stop_reason"] == "HTTP_429_STOP"
    assert all(r["status"] == "NOT_ATTEMPTED" for r in result["records"][1:])


@pytest.mark.parametrize("error,reason", [
    (requests.ConnectionError, "CONNECTION_FAILED"),
    (requests.Timeout, "REQUEST_TIMEOUT"),
])
def test_transport_failure_stops_without_remote_text(tmp_path, error, reason):
    session, calls = session_factory(error=error)
    out = tmp_path / "capture"
    result = p.run_probe(out, {}, session_factory=session)
    assert len(calls) == 1
    assert result["stop_reason"] == reason
    assert result["received_bytes"] == 0
    assert "SECRET" not in (out / "result.json").read_text()


@pytest.mark.parametrize("headers,reason", [
    ({"Content-Encoding": "gzip"}, "UNEXPECTED_CONTENT_ENCODING"),
    ({"Content-Length": "bad"}, "INVALID_CONTENT_LENGTH"),
    ({"Content-Length": "999"}, "RESPONSE_LENGTH_MISMATCH"),
])
def test_shared_response_guard_is_reused(tmp_path, headers, reason):
    session, _ = session_factory(Response(headers=headers))
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    assert all(r["status"] == "REJECTED" and r["reason"] == reason for r in result["records"])


def test_200_non_pdf_fails_closed(tmp_path):
    body = b"<html>not pdf</html>"
    session, _ = session_factory(Response(body=body))
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    assert all(r["status"] == "REJECTED" and r["reason"] == "PDF_MAGIC_MISSING"
               for r in result["records"])


def test_control_hash_mismatch_is_not_qualified(tmp_path, monkeypatch):
    monkeypatch.setattr(p, "SAMPLES", (*p.SAMPLES[:2], (*p.SAMPLES[2][:3], "0" * 64)))
    session, _ = session_factory()
    result = p.run_probe(tmp_path / "capture", {}, session_factory=session)
    assert result["records"][2]["status"] == "CONTROL_HASH_MISMATCH"
    assert result["stop_reason"] == "CONTROL_HASH_MISMATCH"


def test_corrupt_saved_pdf_fails_verifier(tmp_path):
    session, _ = session_factory()
    out = tmp_path / "capture"
    p.run_probe(out, {}, session_factory=session)
    next(out.glob("*.pdf")).write_bytes(b"changed")
    with pytest.raises(ValueError, match="RETAINED_PDF_IDENTITY_MISMATCH"):
        p.verify(out)


def test_native_identity_exact_main_first_attempt(monkeypatch):
    env = {
        "GITHUB_REPOSITORY": "auguspp/decision-kernel",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": "a" * 40,
        "EXPECTED_CODE_SHA": "a" * 40,
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "456",
    }
    monkeypatch.setattr(p, "version", lambda _: "2.34.2")
    assert p.native_identity(env)["GITHUB_RUN_ID"] == "456"
    for patch in (
        {"GITHUB_RUN_ATTEMPT": "2"},
        {"EXPECTED_CODE_SHA": "b" * 40},
        {"GITHUB_REF": "refs/heads/other"},
        {"GITHUB_EVENT_NAME": "push"},
        {"GITHUB_RUN_ID": ""},
    ):
        with pytest.raises(ValueError):
            p.native_identity({**env, **patch})


def test_existing_kernel_session_has_no_env_proxy_cookie_or_retry():
    with p._session() as session:
        assert session.trust_env is False
        assert session.auth is None
        assert len(session.cookies) == 0
        assert session.get_adapter("https://www.cninfo.com.cn/").max_retries.total == 0
