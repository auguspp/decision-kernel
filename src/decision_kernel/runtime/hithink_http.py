from __future__ import annotations

import hashlib
import json
import math
import sys
import os
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..adapters.hithink import (
    SHANGHAI_TZ,
    HithinkCompletedPriceHistory,
    HithinkCompletedSessionPrice,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
    normalize_hithink_completed_price_history,
    observed_market_from_completed_price,
)
from ..market import ObservedMarket


HITHINK_API_KEY_ENV = "HITHINK_FINANCE_API_KEY"
HITHINK_BASE_URL = "https://fuyao.aicubes.cn"
HITHINK_CALENDAR_PATH = "/api/a-share/calendar/trading-days"
HITHINK_HISTORY_PATH = "/api/a-share/prices/historical"
_RequestJSON = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class HithinkRuntimeError(RuntimeError):
    """The outer HiThink runtime could not produce the required qualified market input."""


# Explicitly enabled by the Sector workflow only. This is a conservative client
# interval, NOT a verified provider/account quota or a cross-process Key lock.
HITHINK_SECTOR_PACING_ENV = "HITHINK_SECTOR_REQUEST_PACING"
HITHINK_SECTOR_REQUEST_GAP_SECONDS = 20.0
_sector_request_lock = Lock()
_sector_request_finished_at: float | None = None
_sector_rate_limited = False

# Persist only bounded, credential-free provider diagnostics. HiThink's own public
# support guidance asks for request_id and call times when reduced-frequency calls
# still hit dynamic limits. Raw error bodies are never copied into runtime errors.
HITHINK_HTTP_ERROR_BODY_SAMPLE_BYTES = 4096
_HITHINK_HTTP_DIAGNOSTIC_HEADERS = (
    "Date",
    "Retry-After",
    "X-Request-Id",
    "Request-Id",
    "X-Correlation-Id",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "Server",
    "Via",
    "CF-Ray",
    "X-Azure-Ref",
)
_HITHINK_HTTP_DIAGNOSTIC_JSON_FIELDS = (
    "request_id",
    "requestId",
    "code",
    "message",
)


def _safe_http_diagnostic_value(value: object, *, api_key: str) -> str:
    text = " ".join(str(value).split())[:256]
    if api_key:
        text = text.replace(api_key, "***")
    return text


def _http_error_diagnostics(exc: HTTPError, *, api_key: str) -> tuple[str, ...]:
    """Extract support-useful HTTP error metadata without retaining credentials.

    Response headers are allow-listed. For the body, retain only a bounded sample
    hash/size plus a few fields when the complete sampled body is a JSON object.
    Arbitrary HTML/text bodies are never copied into logs or audit manifests.
    """

    diagnostics: list[str] = []
    if exc.headers is not None:
        for name in _HITHINK_HTTP_DIAGNOSTIC_HEADERS:
            value = exc.headers.get(name)
            if value:
                diagnostics.append(
                    f"{name}={_safe_http_diagnostic_value(value, api_key=api_key)}"
                )

    try:
        body = exc.read(HITHINK_HTTP_ERROR_BODY_SAMPLE_BYTES + 1)
    except (AttributeError, OSError, ValueError):
        body = b""
    if not body:
        return tuple(diagnostics)

    truncated = len(body) > HITHINK_HTTP_ERROR_BODY_SAMPLE_BYTES
    sample = body[:HITHINK_HTTP_ERROR_BODY_SAMPLE_BYTES]
    diagnostics.append(f"body_sample_bytes={len(sample)}")
    diagnostics.append(f"body_sample_sha256={hashlib.sha256(sample).hexdigest()}")
    if truncated:
        diagnostics.append("body_sample_truncated=true")
        return tuple(diagnostics)

    try:
        payload = json.loads(sample.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return tuple(diagnostics)
    if not isinstance(payload, Mapping):
        return tuple(diagnostics)
    for field in _HITHINK_HTTP_DIAGNOSTIC_JSON_FIELDS:
        value = payload.get(field)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            diagnostics.append(
                f"body.{field}={_safe_http_diagnostic_value(value, api_key=api_key)}"
            )
    return tuple(diagnostics)


@contextmanager
def _sector_request_spacing() -> Iterator[None]:
    """Space actual serial requests; never retry a failure or rewrite a clock.

    The one-run process remembers HTTP 429 even if an outer caller catches it.
    Other workflows retain their existing behavior unless explicitly opted in.
    This cannot establish that another process/account consumer is idle.
    """
    global _sector_request_finished_at, _sector_rate_limited
    enabled = os.environ.get(HITHINK_SECTOR_PACING_ENV, "")
    if enabled == "":
        yield
        return
    if enabled != "1":
        raise HithinkRuntimeError("Sector request pacing must be explicitly enabled with 1")
    with _sector_request_lock:
        if _sector_rate_limited:
            raise HithinkRuntimeError("Sector acquisition stopped after HTTP 429; no retry is permitted")
        if _sector_request_finished_at is not None:
            elapsed = time.monotonic() - _sector_request_finished_at
            remaining = HITHINK_SECTOR_REQUEST_GAP_SECONDS - elapsed
            if remaining > 0:
                time.sleep(remaining)
        try:
            yield
        except HTTPError as exc:
            if exc.code == 429:
                _sector_rate_limited = True
            raise
        finally:
            _sector_request_finished_at = time.monotonic()


# #513: explicit Inbox-only recovery, never a global transport retry policy.
_calendar_recovery: ContextVar[dict | None] = ContextVar("inbox_calendar_recovery", default=None)
CALENDAR_RETRY_BACKOFF_SECONDS = 1.0
CALENDAR_RETRY_START_BUDGET_SECONDS = 30.0


@contextmanager
def inbox_calendar_timeout_recovery() -> Iterator[None]:
    """One batch scope; nested callers share rather than reset its failure latch."""
    if _calendar_recovery.get() is not None:
        yield
        return
    token = _calendar_recovery.set({})
    try:
        yield
    finally:
        _calendar_recovery.reset(token)


def _calendar_timeout_cause(exc: BaseException) -> bool:
    # The native wrapper preserves the exception object. Never classify by text.
    cause = exc.__cause__ if isinstance(exc, HithinkRuntimeError) else None
    return isinstance(cause, TimeoutError) or (
        isinstance(cause, URLError) and not isinstance(cause, HTTPError)
        and isinstance(cause.reason, TimeoutError)
    )


def _calendar_attempt_log(record: dict) -> None:
    # Only locally constructed fields, not credentials or upstream error strings.
    # GitHub owns durable run/job log retention; this is not Market/Research state.
    print("HITHINK_CALENDAR_ATTEMPT " + json.dumps(record, sort_keys=True),
          file=sys.stderr, flush=True)


def _recover_inbox_calendar(*, api_key: str, shanghai_date: date,
                            timeout_seconds: float, scope: dict) -> Mapping[str, Any]:
    if "failure" in scope:
        raise HithinkRuntimeError("Inbox calendar dependency failed; no further attempt in this batch") from scope["failure"]
    if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 10):
        raise HithinkRuntimeError("Inbox calendar recovery timeout must be finite and in (0, 10]")
    if os.environ.get(HITHINK_SECTOR_PACING_ENV, ""):
        raise HithinkRuntimeError("Inbox calendar recovery cannot change Sector pacing semantics")
    identity = (api_key, shanghai_date, timeout_seconds)  # In-memory only; never logged.
    if "identity" in scope and scope["identity"] != identity:
        raise HithinkRuntimeError("Inbox calendar recovery identity changed within the batch")
    scope["identity"] = identity
    started = time.monotonic()
    deadline = started + CALENDAR_RETRY_START_BUDGET_SECONDS
    for attempt in (1, 2):
        budget = min(timeout_seconds, deadline - time.monotonic())
        if budget <= 0:
            raise HithinkRuntimeError("Inbox calendar retry start budget exhausted") from scope.get("failure")
        record = {"policy": "inbox-calendar-timeout-once-v1", "attempt": attempt,
            "max_attempts": 2, "provider": "HITHINK", "method": "GET",
            "source_url": HITHINK_BASE_URL + HITHINK_CALENDAR_PATH,
            "requested_shanghai_date": shanghai_date.isoformat(),
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "timeout_ms": round(budget * 1000), "status": "REQUEST_STARTED",
            "fallback_provider": None, "investment_authority": "NONE"}
        _calendar_attempt_log(record)
        try:
            envelope = _request_hithink_json(api_key=api_key, path=HITHINK_CALENDAR_PATH,
                                            params={}, timeout_seconds=budget)
            sessions = normalize_hithink_calendar(envelope)
        except (HithinkRuntimeError, ValueError) as exc:
            scope["failure"] = exc
            retry = (attempt == 1 and _calendar_timeout_cause(exc)
                     and deadline - time.monotonic() > CALENDAR_RETRY_BACKOFF_SECONDS)
            _calendar_attempt_log({**record, "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "TIMEOUT" if _calendar_timeout_cause(exc) else "NON_RETRYABLE_FAILURE",
                "error_type": type(exc).__name__, "retry_scheduled": retry,
                "backoff_ms": 1000 if retry else 0})
            if not retry:
                raise
            time.sleep(CALENDAR_RETRY_BACKOFF_SECONDS)
        else:
            scope.pop("failure", None)
            _calendar_attempt_log({**record, "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": "NORMALIZED_CALENDAR_NOT_PRICE_QUALIFICATION", "retry_scheduled": False,
                "session_count": len(sessions), "first_session": sessions[0].isoformat(),
                "last_session": sessions[-1].isoformat(),
                "normalized_sessions_sha256": hashlib.sha256(
                    "\n".join(d.isoformat() for d in sessions).encode()).hexdigest(),
                "digest_representation": "NORMALIZED_DATE_LIST_NOT_RAW_HTTP_BYTES"})
            return envelope
    raise AssertionError("calendar attempt loop exhausted without a terminal result")


@lru_cache(maxsize=8)
def _request_hithink_calendar(
    *,
    api_key: str,
    shanghai_date: date,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    """Reuse one exact calendar response per credential/date in this process only.

    `shanghai_date` deliberately participates in the cache key even though the
    provider endpoint has no date parameter. A long-lived Harness process therefore
    cannot carry yesterday's calendar into a new Shanghai date. History responses
    are never cached. Exceptions are not cached by ``lru_cache``.
    """

    scope = _calendar_recovery.get()
    if scope is not None:
        return _recover_inbox_calendar(api_key=api_key, shanghai_date=shanghai_date,
                                      timeout_seconds=timeout_seconds, scope=scope)
    del shanghai_date
    return _request_hithink_json(
        api_key=api_key,
        path=HITHINK_CALENDAR_PATH,
        params={},
        timeout_seconds=timeout_seconds,
    )


def fetch_hithink_trading_calendar(
    *,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[date, ...]:
    """Fetch one exact normalized A-share trading calendar.

    The calendar is a market-session qualification input only. It does not infer a
    missing trading day, create a Radar candidate, or carry Research, Human-attention,
    or investment authority.
    """

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkRuntimeError("calendar observed_at must be timezone-aware")
    if not api_key:
        raise HithinkRuntimeError(
            "HiThink credentials are required for the A-share trading calendar"
        )
    if timeout_seconds <= 0:
        raise HithinkRuntimeError("HiThink calendar timeout must be positive")
    if request_json is None:
        envelope = _request_hithink_calendar(
            api_key=api_key,
            shanghai_date=observed_at.astimezone(SHANGHAI_TZ).date(),
            timeout_seconds=timeout_seconds,
        )
    else:
        envelope = request_json(HITHINK_CALENDAR_PATH, {})
    return normalize_hithink_calendar(envelope)


def fetch_hithink_completed_price_history(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> HithinkCompletedPriceHistory:
    """Fetch the existing 45-day raw-close window for Harness consumers.

    This is commodity acquisition only. It does not classify anomalies, allocate
    Research attention, change fundamental state, or carry investment authority.
    The live runtime still requires the provider response to reach the latest
    completed A-share session.
    """

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise HithinkRuntimeError("live observed_at must be timezone-aware")
    if not api_key:
        raise HithinkRuntimeError("HiThink credentials are required for live market data")

    if request_json is None:
        calendar_envelope = _request_hithink_calendar(
            api_key=api_key,
            shanghai_date=observed_at.astimezone(SHANGHAI_TZ).date(),
            timeout_seconds=timeout_seconds,
        )
        request_json = lambda path, params: _request_hithink_json(
            api_key=api_key,
            path=path,
            params=params,
            timeout_seconds=timeout_seconds,
        )
    else:
        calendar_envelope = request_json(HITHINK_CALENDAR_PATH, {})

    calendar = normalize_hithink_calendar(calendar_envelope)
    expected_latest = latest_completed_a_share_session(
        calendar,
        observed_at=observed_at,
    )
    exclusive_end_at = datetime.combine(
        expected_latest + timedelta(days=1),
        datetime.min.time(),
        tzinfo=SHANGHAI_TZ,
    )
    # HiThink daily history can include a bar keyed exactly at `end`. Keep the
    # request inside the latest completed session; the adapter remains fail-closed
    # if any unfinished/future bar is nevertheless returned.
    end_at = exclusive_end_at - timedelta(milliseconds=1)
    start_at = exclusive_end_at - timedelta(days=45)
    envelope = request_json(
        HITHINK_HISTORY_PATH,
        {
            "thscode": thscode,
            "interval": "1d",
            "start": str(int(start_at.timestamp() * 1000)),
            "end": str(int(end_at.timestamp() * 1000)),
            "adjust": "none",
        },
    )
    history = normalize_hithink_completed_price_history(
        envelope,
        thscode=thscode,
        sessions=calendar,
        observed_at=observed_at,
    )
    if history.response_session != history.expected_latest_session:
        raise HithinkRuntimeError(
            "HiThink raw history does not reach the latest completed A-share session"
        )
    return history


def fetch_latest_hithink_observed_market(
    *,
    thscode: str,
    observed_at: datetime,
    api_key: str | None,
    request_json: _RequestJSON | None = None,
    timeout_seconds: float = 10.0,
) -> ObservedMarket:
    """Fetch the latest qualified completed close for live Odds."""

    history = fetch_hithink_completed_price_history(
        thscode=thscode,
        observed_at=observed_at,
        api_key=api_key,
        request_json=request_json,
        timeout_seconds=timeout_seconds,
    )
    latest = history.points[-1]
    return observed_market_from_completed_price(
        HithinkCompletedSessionPrice(
            thscode=history.thscode,
            close=latest.close,
            as_of=latest.as_of,
            expected_latest_session=history.expected_latest_session,
        )
    )


def _request_hithink_json(
    *,
    api_key: str,
    path: str,
    params: Mapping[str, str],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    query = urlencode(params)
    url = f"{HITHINK_BASE_URL}{path}{'?' if query else ''}{query}"
    request = Request(
        url,
        headers={"Accept": "application/json", "X-api-key": api_key},
        method="GET",
    )
    elapsed_ms: int | None = None  # None if interrupted before the request starts.
    try:
        with _sector_request_spacing():
            # Exclude local pacing/lock waits; include open, body read and decode.
            request_started = time.monotonic()
            try:
                with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                    payload = json.loads(response.read().decode("utf-8"))
            finally:
                elapsed_ms = round((time.monotonic() - request_started) * 1000)
    except HTTPError as exc:
        kind = "HTTP_429" if exc.code == 429 else "HTTP_OTHER"
        message = (f"failure_kind={kind}; elapsed_ms={elapsed_ms}; "
                   f"HiThink HTTP request failed for {path} with status {exc.code}")
        diagnostics = _http_error_diagnostics(exc, api_key=api_key)
        if diagnostics:
            message += "; " + "; ".join(diagnostics)
        raise HithinkRuntimeError(message) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        if isinstance(exc, TimeoutError) or (
            isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError)
        ):
            kind = "TIMEOUT"
        elif isinstance(exc, URLError):
            kind = "URL_ERROR"  # Do not guess from a provider's message string.
        elif isinstance(exc, json.JSONDecodeError):
            kind = "JSON_DECODE_ERROR"
        else:
            kind = "UNICODE_DECODE_ERROR"
        raise HithinkRuntimeError(
            f"HiThink request or response decoding failed for {path}; "
            f"failure_kind={kind}; elapsed_ms={elapsed_ms}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HithinkRuntimeError("HiThink response is not a JSON object")
    return payload
