"""Credential-safe HiThink HTTP error diagnostics; no live provider calls."""
from __future__ import annotations

import hashlib
import io
import json
from urllib.error import HTTPError

import pytest

from decision_kernel.runtime import hithink_http as http


def make_error(*, body: bytes, headers: dict[str, str] | None = None) -> HTTPError:
    return HTTPError(
        f"{http.HITHINK_BASE_URL}{http.HITHINK_CALENDAR_PATH}",
        429,
        "synthetic provider throttle",
        {} if headers is None else headers,
        io.BytesIO(body),
    )


def test_safe_http_diagnostics_keep_support_fields_and_redact_credential():
    api_key = "pytest-private-canary"
    body = json.dumps(
        {
            "code": 4001,
            "message": f"dynamic throttle for {api_key}",
            "request_id": "body-request-123",
            "ignored": "must-not-be-copied",
        }
    ).encode("utf-8")
    exc = make_error(
        body=body,
        headers={
            "Retry-After": "37",
            "X-Request-Id": "edge-request-456",
            "Server": "synthetic-edge",
            "X-Untrusted": f"do-not-copy-{api_key}",
        },
    )

    text = "; ".join(http._http_error_diagnostics(exc, api_key=api_key))

    assert "Retry-After=37" in text
    assert "X-Request-Id=edge-request-456" in text
    assert "Server=synthetic-edge" in text
    assert "body.request_id=body-request-123" in text
    assert "body.code=4001" in text
    assert "body.message=dynamic throttle for ***" in text
    assert f"body_sample_bytes={len(body)}" in text
    assert f"body_sample_sha256={hashlib.sha256(body).hexdigest()}" in text
    assert api_key not in text
    assert "X-Untrusted" not in text
    assert "must-not-be-copied" not in text


def test_non_json_error_body_is_hashed_but_never_copied():
    body = b"<html><body>synthetic gateway policy detail</body></html>"
    exc = make_error(body=body, headers={"Via": "synthetic-proxy"})

    text = "; ".join(http._http_error_diagnostics(exc, api_key="private"))

    assert "Via=synthetic-proxy" in text
    assert f"body_sample_sha256={hashlib.sha256(body).hexdigest()}" in text
    assert "synthetic gateway policy detail" not in text
    assert "body.message=" not in text


def test_truncated_body_is_not_interpreted_as_json(monkeypatch):
    monkeypatch.setattr(http, "HITHINK_HTTP_ERROR_BODY_SAMPLE_BYTES", 16)
    body = b'{"request_id":"unsafe-beyond-bound"}'
    exc = make_error(body=body)

    text = "; ".join(http._http_error_diagnostics(exc, api_key="private"))

    assert "body_sample_bytes=16" in text
    assert "body_sample_truncated=true" in text
    assert "body.request_id=" not in text
    assert "unsafe-beyond-bound" not in text


def test_request_error_message_exposes_safe_support_diagnostics_without_retry(
    monkeypatch,
):
    monkeypatch.delenv(http.HITHINK_SECTOR_PACING_ENV, raising=False)
    calls: list[str] = []
    body = b'{"code":4001,"message":"rate limited","request_id":"req-live-shape"}'

    def limited(request, *, timeout):
        calls.append(request.full_url)
        assert timeout == 10.0
        raise make_error(
            body=body,
            headers={"Retry-After": "60", "X-Correlation-Id": "corr-789"},
        )

    monkeypatch.setattr(http, "urlopen", limited)

    with pytest.raises(http.HithinkRuntimeError) as caught:
        http._request_hithink_json(
            api_key="pytest-private-canary",
            path=http.HITHINK_CALENDAR_PATH,
            params={},
            timeout_seconds=10.0,
        )

    text = str(caught.value)
    assert "status 429" in text
    assert "Retry-After=60" in text
    assert "X-Correlation-Id=corr-789" in text
    assert "body.request_id=req-live-shape" in text
    assert "body.code=4001" in text
    assert "pytest-private-canary" not in text
    assert len(calls) == 1


@pytest.mark.parametrize("case,kind", [
    ("timeout_open", "TIMEOUT"), ("timeout_read", "TIMEOUT"),
    ("wrapped_timeout", "TIMEOUT"), ("dns", "URL_ERROR"),
    ("text_timeout", "URL_ERROR"), ("json", "JSON_DECODE_ERROR"),
    ("unicode", "UNICODE_DECODE_ERROR"),
    ("http401", "HTTP_OTHER"), ("http403", "HTTP_OTHER"),
    ("http429", "HTTP_429"), ("http500", "HTTP_OTHER"),
])
def test_request_failure_kind_and_elapsed_reach_original_operations(
    tmp_path, monkeypatch, case, kind,
):
    from datetime import datetime, timezone
    import socket
    from urllib.error import URLError
    from decision_kernel.runtime.sector_radar_producer import (
        SectorRadarProducerContext, write_sector_radar_failure_operations,
    )

    secret = "synthetic-private-canary"
    clock = [1.0]
    calls, sleeps = [], []
    monkeypatch.setenv(http.HITHINK_SECTOR_PACING_ENV, "1")
    monkeypatch.setattr(http, "_sector_request_finished_at", 0.0)
    monkeypatch.setattr(http, "_sector_rate_limited", False)
    monkeypatch.setattr(http.time, "monotonic", lambda: clock[0])
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr(http.time, "sleep", sleep)
    def forbidden_network(*args, **kwargs):
        pytest.fail("unexpected real network access")
    monkeypatch.setattr(socket, "create_connection", forbidden_network)

    class Response(io.BytesIO):
        def read(self, *args):
            clock[0] += 0.125
            if case == "timeout_read":
                raise TimeoutError(secret)
            return super().read(*args)

    def opener(request, *, timeout):
        calls.append(request.full_url)
        assert timeout == 10.0
        assert request.get_header("X-api-key") == secret
        if case in {"timeout_open", "wrapped_timeout", "dns", "text_timeout"}:
            clock[0] += 0.125
            errors = {
                "timeout_open": TimeoutError(secret),
                "wrapped_timeout": URLError(TimeoutError(secret)),
                "dns": URLError(socket.gaierror(-2, secret)),
                "text_timeout": URLError("timed out: " + secret),
            }
            raise errors[case]
        if case.startswith("http"):
            clock[0] += 0.125
            # Diagnostic-body reading takes another .125s, excluded from elapsed.
            raise HTTPError(request.full_url, int(case[4:]), secret, {},
                            Response(secret.encode()))
        body = (b"{" + secret.encode()) if case == "json" else b"\xff" + secret.encode()
        return Response(body)

    monkeypatch.setattr(http, "urlopen", opener)
    with pytest.raises(http.HithinkRuntimeError) as caught:
        http._request_hithink_json(api_key=secret, path=http.HITHINK_CALENDAR_PATH,
                                  params={}, timeout_seconds=10.0)
    text = str(caught.value)
    assert f"failure_kind={kind}; elapsed_ms=125" in text
    assert sleeps == [19.0] and len(calls) == 1
    assert secret not in text and "timed out:" not in text
    stamp = datetime(2026, 9, 11, 2, tzinfo=timezone.utc)
    context = SectorRadarProducerContext("auguspp/decision-kernel",
        ".github/workflows/sector-radar-shadow.yml", 1, 1, "a"*40, stamp)
    operations = write_sector_radar_failure_operations(
        output_directory=tmp_path, context=context, error=caught.value,
        completed_at=stamp,
    )
    assert operations.status == "FAILED_CLOSED"
    assert operations.candidate_count is None and operations.result_hash is None
    for name in ("operations.json", "operations.md"):
        saved = (tmp_path/name).read_text()
        assert f"failure_kind={kind}; elapsed_ms=125" in saved
        assert secret not in saved
    if case == "http429":
        with pytest.raises(http.HithinkRuntimeError, match="stopped after HTTP 429"):
            http._request_hithink_json(api_key=secret, path=http.HITHINK_CALENDAR_PATH,
                                      params={}, timeout_seconds=10.0)
        assert len(calls) == 1 and sleeps == [19.0]


@pytest.mark.parametrize("body,expected", [(b'{"ok":true}', {"ok": True}), (b'[]', None)])
def test_success_and_existing_non_object_rejection_are_unchanged(monkeypatch, body, expected):
    monkeypatch.delenv(http.HITHINK_SECTOR_PACING_ENV, raising=False)
    calls = []
    def opener(*args, **kwargs):
        calls.append(1)
        return io.BytesIO(body)
    monkeypatch.setattr(http, "urlopen", opener)
    if expected is None:
        with pytest.raises(http.HithinkRuntimeError, match="not a JSON object"):
            http._request_hithink_json(api_key="synthetic", path=http.HITHINK_CALENDAR_PATH,
                                      params={}, timeout_seconds=10.0)
    else:
        assert http._request_hithink_json(api_key="synthetic", path=http.HITHINK_CALENDAR_PATH,
                                         params={}, timeout_seconds=10.0) == expected
    assert calls == [1]


def test_interrupted_local_pacing_has_no_invented_request_elapsed(monkeypatch):
    monkeypatch.setenv(http.HITHINK_SECTOR_PACING_ENV, "1")
    monkeypatch.setattr(http, "_sector_request_finished_at", 0.0)
    monkeypatch.setattr(http, "_sector_rate_limited", False)
    monkeypatch.setattr(http.time, "monotonic", lambda: 1.0)
    def interrupt(seconds):
        raise TimeoutError("synthetic-private-canary")
    monkeypatch.setattr(http.time, "sleep", interrupt)
    monkeypatch.setattr(http, "urlopen", lambda *a, **k: pytest.fail("no request allowed"))
    with pytest.raises(http.HithinkRuntimeError) as caught:
        http._request_hithink_json(api_key="synthetic-private-canary",
            path=http.HITHINK_CALENDAR_PATH, params={}, timeout_seconds=10.0)
    assert "elapsed_ms=None" in str(caught.value)
    assert "synthetic-private-canary" not in str(caught.value)
