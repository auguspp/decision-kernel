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
        self.sessions = list(sessions)
        self._remaining = list(sessions)

    def __call__(self):
        return self._remaining.pop(0)


def _org_rows():
    return [{"code": "600036", "orgId": "gssh0600036"}]


def _request_json_all_403(*, url, method, form, timeout_seconds):
    if url == CNINFO_STOCK_MAP_URL:
        assert method == "POST"
        return _org_rows()
    assert url == CNINFO_ANNOUNCEMENT_QUERY_URL and method == "POST"
    raise CninfoRuntimeError(
        "CNINFO HTTP request failed with status 403 [stage=ANNOUNCEMENT_QUERY]"
    )


def _request_json_production_success(*, url, method, form, timeout_seconds):
    if url == CNINFO_STOCK_MAP_URL:
        return _org_rows()
    assert url == CNINFO_ANNOUNCEMENT_QUERY_URL and method == "POST"
    return {"totalAnnouncement": 0, "announcements": None, "hasMore": False}


def _four_403_sessions():
    return _SessionFactory([
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
    ])


def test_all_http_and_https_control_variants_403_stays_unknown_and_non_authoritative():
    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=_four_403_sessions(),
    )

    assert result["schema_version"] == 2
    assert result["disposition"] == "ALL_TESTED_ANNOUNCEMENT_CONTRACTS_403"
    assert result["cause"] == "UNKNOWN"
    assert result["working_variants"] == []
    assert result["production_contract_observed"] is False
    assert result["request_count"] == 6
    assert result["max_requests"] == 7
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["research_authority"] == result["human_attention_authority"] == "NONE"
    assert result["investment_authority"] == "NONE"
    assert result["market_state_writes"] == result["events_created"] == 0


def test_exact_production_http_success_is_observed_without_granting_authority():
    result = probe.run_probe(
        request_json=_request_json_production_success,
        session_factory=_four_403_sessions(),
    )

    assert result["disposition"] == "PRODUCTION_HTTP_ANNOUNCEMENT_CONTRACT_OBSERVED"
    assert result["production_contract_observed"] is True
    assert result["working_variants"] == ["urllib_current_production"]
    production = result["announcement_attempts"][0]
    assert production["url_scheme"] == "http"
    assert production["status"] == 200
    assert production["contract_shape"] == "CNINFO_ANNOUNCEMENT_PAGE"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["cause"] == "UNKNOWN"


def test_nonproduction_http_success_is_request_contract_observation_only():
    payload = {"totalAnnouncement": 0, "announcements": None, "hasMore": False}
    factory = _SessionFactory([
        _Session([_Response(200, payload)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
    ])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["disposition"] == "HTTP_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED_NOT_PRODUCTION"
    assert result["production_contract_observed"] is False
    assert result["working_variants"] == ["requests_http_current_form_prior_headers"]
    observed = next(
        item for item in result["announcement_attempts"]
        if item["variant"] == "requests_http_current_form_prior_headers"
    )
    assert observed["url_scheme"] == "http"
    assert observed["contract_shape"] == "CNINFO_ANNOUNCEMENT_PAGE"


def test_https_only_success_does_not_certify_current_http_production_contract():
    payload = {"totalAnnouncement": 0, "announcements": None, "hasMore": False}
    factory = _SessionFactory([
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(200, payload)]),
        _Session([_Response(403)]),
    ])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["disposition"] == "HTTPS_ONLY_ANNOUNCEMENT_REQUEST_CONTRACT_OBSERVED"
    assert result["production_contract_observed"] is False
    assert result["working_variants"] == ["requests_https_legacy_browser_headers"]


def test_prior_source_study_variant_uses_its_reviewed_form_shape():
    payload = {"totalAnnouncement": 0, "announcements": None, "hasMore": False}
    current = _Session([_Response(403)])
    prior = _Session([_Response(200, payload)])
    legacy_https = _Session([_Response(403)])
    warm = _Session([_Response(403)])
    factory = _SessionFactory([current, prior, legacy_https, warm])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["working_variants"] == ["requests_http_prior_source_study"]
    _, prior_url, kwargs = prior.calls[0]
    assert prior_url.startswith("http://")
    assert kwargs["data"]["column"] == "szse"
    assert kwargs["data"]["searchkey"] == "权益分派实施公告"
    assert kwargs["data"]["isHLtitle"] == "false"
    assert kwargs["data"]["pageSize"] == "30"
    _, current_url, current_kwargs = current.calls[0]
    assert current_url.startswith("http://")
    assert current_kwargs["data"]["column"] == ""
    assert current_kwargs["data"]["searchkey"] == ""
    assert current_kwargs["data"]["isHLtitle"] == "true"


def test_warmed_http_variant_uses_exact_issuer_page_and_no_redirects():
    payload = {"totalAnnouncement": 0, "announcements": None, "hasMore": False}
    warm = _Session([_Response(200, {}), _Response(200, payload)])
    factory = _SessionFactory([
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        _Session([_Response(403)]),
        warm,
    ])

    result = probe.run_probe(
        request_json=_request_json_all_403,
        session_factory=factory,
    )

    assert result["working_variants"] == ["requests_warmed_http_browser_session"]
    get_method, issuer_url, get_kwargs = warm.calls[0]
    post_method, post_url, post_kwargs = warm.calls[1]
    assert get_method == "GET" and post_method == "POST"
    assert issuer_url == (
        "http://www.cninfo.com.cn/new/disclosure/stock?"
        "stockCode=600036&orgId=gssh0600036"
    )
    assert post_url == CNINFO_ANNOUNCEMENT_QUERY_URL
    assert get_kwargs["allow_redirects"] is False
    assert post_kwargs["allow_redirects"] is False
    assert post_kwargs["headers"]["Referer"] == issuer_url
    assert result["request_count"] == 7


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
    assert "python -m pip install -e '.[dump-study]'" in text
    assert "python -m pip install -e .\n" not in text
    assert "cninfo_announcement_probe" in text
    assert "scan-disclosures" not in text
    assert "saved-disclosure-research" not in text
    assert "Odds" not in text and "Action" not in text
