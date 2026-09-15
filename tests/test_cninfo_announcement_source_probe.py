from __future__ import annotations

import json

from decision_kernel.runtime import cninfo_announcement_probe as probe
from decision_kernel.runtime.cninfo_http import (
    CNINFO_ANNOUNCEMENT_QUERY_URL,
    CNINFO_STOCK_MAP_URL,
    CninfoRuntimeError,
)


class _Response:
    def __init__(self, status: int, payload=None):
        self.status_code = status
        self.headers = {}
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_content(self, chunk_size=65536):
        assert self.status_code == 200, "non-200 response bodies must not be read"
        raw = json.dumps(self._payload).encode("utf-8")
        yield raw


class _Session:
    def __init__(self, responses):
        self._responses = list(responses)
        self.cookies = []
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self._responses.pop(0)
        if method == "GET" and response.status_code == 200:
            self.cookies.append("opaque-cookie-not-retained")
        return response


class _SessionFactory:
    def __init__(self, sessions):
        self._sessions = list(sessions)

    def __call__(self):
        return self._sessions.pop(0)


def _request_json_all_403(*, url, method, form, timeout_seconds):
    if url == CNINFO_STOCK_MAP_URL:
        assert method == "POST"
        return [{"code": "600036", "orgId": "gssh0600036"}]
    assert url == CNINFO_ANNOUNCEMENT_QUERY_URL and method == "POST"
    raise CninfoRuntimeError(
        "CNINFO HTTP request failed with status 403 [stage=ANNOUNCEMENT_QUERY]"
    )


def test_all_https_variants_403_stays_unknown_and_non_authoritative():
    factory = _SessionFactory([
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
    ])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["disposition"] == "ALL_TESTED_HTTPS_ANNOUNCEMENT_CONTRACTS_403"
    assert result["cause"] == "UNKNOWN"
    assert result["working_variants"] == []
    assert result["request_count"] == 5
    assert result["max_requests"] == 6
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["research_authority"] == result["human_attention_authority"] == "NONE"
    assert result["investment_authority"] == "NONE"
    assert result["market_state_writes"] == result["events_created"] == 0


def test_requests_browser_success_is_request_contract_observation_only():
    payload = {"totalAnnouncement": 0, "announcements": None, "hasMore": False}
    factory = _SessionFactory([
        _Session([_Response(403)]),
        _Session([_Response(200, payload)]),
        _Session([_Response(403)]),
    ])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["disposition"] == "HTTPS_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED"
    assert result["working_variants"] == ["requests_browser_headers"]
    browser = next(
        item for item in result["announcement_attempts"]
        if item["variant"] == "requests_browser_headers"
    )
    assert browser["status"] == 200
    assert browser["json_shape"] == "OBJECT"
    assert browser["announcement_count"] is None
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["cause"] == "UNKNOWN"


def test_probe_workflow_is_manual_read_only_and_not_a_production_lane():
    text = open(
        ".github/workflows/cninfo-announcement-source-probe.yml",
        encoding="utf-8",
    ).read()
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text and "push:" not in text and "pull_request:" not in text
    assert "contents: read" in text and "contents: write" not in text
    assert "secrets." not in text
    assert "actions/cache" not in text and "decision-state" not in text
    assert 'test "$GITHUB_RUN_ATTEMPT" = "1"' in text
    assert "timeout-minutes: 5" in text
    assert "cninfo_announcement_probe" in text
    assert "scan-disclosures" not in text
    assert "saved-disclosure-research" not in text
    assert "Odds" not in text and "Action" not in text
