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
