"""Safe failure detail only; no retries, source access, research or authority."""
from io import BytesIO
import json
import socket
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from decision_kernel.runtime import cninfo_http as cninfo
from decision_kernel.runtime import current_state_delivery as delivery


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("diagnostic tests must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.mark.parametrize("message, code", [
    ("research work API accounting unavailable", "API_ACCOUNTING_UNAVAILABLE"),
    ("research work API reserve would consume base publication budget", "BASE_PUBLICATION_RESERVE"),
    ("research work item bound exceeded", "WORK_ITEM_BOUND"),
    ("research work read would exceed source-file budget", "SOURCE_FILE_BUDGET"),
    ("research work would exhaust reading retention bound", "RETENTION_BYTE_BUDGET"),
    ("research work read would exhaust publication API reserve", "WORK_PUBLICATION_RESERVE"),
    ("research work tree incomplete", "INCOMPLETE_WORK_TREE"),
    ("research work reserved packet unavailable", "RESERVED_PACKET_UNAVAILABLE"),
    ("research work item contains both candidate and pre-execution failure", "CANDIDATE_FAILURE_CONFLICT"),
    ("research work blob differs", "WORK_BLOB_MISMATCH"),
    ("research work failure packet binding differs", "FAILURE_PACKET_MISMATCH"),
    ("saved Funnel differs from original candidate revalidation", "SAVED_FUNNEL_MISMATCH"),
])
def test_only_known_internal_checks_get_a_reason(message, code):
    detail = delivery.research_work_diagnostic(ValueError(message), api_calls=17,
        source_count=44, retained_file_count=50)
    assert detail["code"] == code
    assert detail["api_calls_after_attempt"] == 17
    assert detail["source_count_after_rollback"] == 44
    assert detail["meaning"] == "DIAGNOSTIC_ONLY_NOT_RECOVERY_OR_RESEARCH_ACCEPTANCE"


@pytest.mark.parametrize("exc", [
    ValueError("Bearer secret; https://example.test/?token=secret; BUY now"),
    RuntimeError("research work tree incomplete"),
    KeyError("secret"),
    ValueError("research work tree incomplete", "secret"),
])
def test_unknown_or_nonexact_exceptions_do_not_leak_or_invent_a_cause(exc):
    detail = delivery.research_work_diagnostic(exc, api_calls=True,
        source_count=0, retained_file_count=0)
    assert detail["code"] == "UNCLASSIFIED_READ_REJECTION"
    assert detail["api_calls_after_attempt"] is None
    assert "secret" not in json.dumps(detail) and "BUY" not in json.dumps(detail)


def test_exception_stringifier_is_not_called():
    class Unsafe(ValueError):
        def __str__(self):
            raise AssertionError("never stringify an unknown exception")
    detail = delivery.research_work_diagnostic(Unsafe("secret"), api_calls=None,
        source_count=0, retained_file_count=0)
    assert detail["code"] == "UNCLASSIFIED_READ_REJECTION"


def test_original_optional_rollback_and_gap_are_preserved(tmp_path, monkeypatch):
    api = SimpleNamespace(calls=20)
    collector = delivery.Collector(api, "a" * 40, tmp_path)
    collector.files = {"baseline.txt": b"keep"}
    collector.sources = {("baseline.txt", "a" * 40): (b"keep", {})}
    before_files, before_sources = dict(collector.files), dict(collector.sources)
    def fail(config):
        collector.files["partial.txt"] = b"reject"
        collector.sources[("partial.txt", "b" * 40)] = (b"reject", {})
        api.calls += 1
        raise ValueError("research work read would exceed source-file budget")
    monkeypatch.setattr(collector, "_research_work", fail)
    research = {"gaps": [], "handoffs": {"active": [], "background": []}}
    collector.include_research_work({"research_work_read": {}}, research)
    assert collector.files == before_files and collector.sources == before_sources
    assert api.calls == 21  # Calls are not rolled back or retried.
    item = research["candidate_work"]
    assert item["status"] == "UNAVAILABLE_OR_REJECTED"
    assert item["diagnostic"]["code"] == "SOURCE_FILE_BUDGET"
    assert item["diagnostic"]["source_count_after_rollback"] == 1
    assert research["gaps"] == [{"status": "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET",
                                 "error_type": "ValueError"}]
    assert research["handoffs"] == {"active": [], "background": []}
    assert (delivery.MAX_API_CALLS, delivery.MAX_SOURCE_FILES) == (180, 60)


@pytest.mark.parametrize("url, method, stage", [
    (cninfo.CNINFO_STOCK_MAP_URL, "GET", "SECURITY_MAP"),
    (cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL, "POST", "ANNOUNCEMENT_QUERY"),
    ("https://example.test/?token=secret", "GET", "UNCLASSIFIED_JSON_ENDPOINT"),
])
def test_json_403_retains_phase_without_retry_or_sensitive_text(monkeypatch, url, method, stage):
    calls = []
    def reject(request, **kwargs):
        calls.append(request)
        raise HTTPError(url, 403, "Bearer secret", {}, BytesIO(b"secret response"))
    monkeypatch.setattr(cninfo, "urlopen", reject)
    with pytest.raises(cninfo.CninfoRuntimeError) as caught:
        cninfo._request_json(url=url, method=method,
            form={"stock": "secret"} if method == "POST" else None, timeout_seconds=1)
    text = str(caught.value)
    assert text == f"CNINFO HTTP request failed with status 403 [stage={stage}]"
    assert "secret" not in text and "https" not in text
    assert len(calls) == 1 and calls[0].method == method


@pytest.mark.parametrize("failure", [URLError("secret"), TimeoutError("secret")])
def test_json_transport_failure_is_not_reclassified_as_success(monkeypatch, failure):
    def reject(*args, **kwargs):
        raise failure
    monkeypatch.setattr(cninfo, "urlopen", reject)
    with pytest.raises(cninfo.CninfoRuntimeError, match=r"decoding failed \[stage=SECURITY_MAP\]"):
        cninfo._request_json(url=cninfo.CNINFO_STOCK_MAP_URL, method="GET",
                             form=None, timeout_seconds=1)


@pytest.mark.parametrize("body", [b"{", b"[]"])
def test_invalid_json_stays_rejected(monkeypatch, body):
    monkeypatch.setattr(cninfo, "urlopen", lambda *a, **k: BytesIO(body))
    with pytest.raises(cninfo.CninfoRuntimeError, match=r"stage=SECURITY_MAP"):
        cninfo._request_json(url=cninfo.CNINFO_STOCK_MAP_URL, method="GET",
                             form=None, timeout_seconds=1)


def test_success_payload_and_request_are_unchanged(monkeypatch):
    calls = []
    def respond(request, **kwargs):
        calls.append(request)
        return BytesIO(b'{"announcements": [], "totalAnnouncement": 0}')
    monkeypatch.setattr(cninfo, "urlopen", respond)
    result = cninfo._request_json(url=cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL,
        method="POST", form={"stock": "600036,org", "pageNum": "1"}, timeout_seconds=1)
    assert result == {"announcements": [], "totalAnnouncement": 0}
    assert len(calls) == 1 and calls[0].data == b"stock=600036%2Corg&pageNum=1"
    assert calls[0].get_header("User-agent") == "Mozilla/5.0"
    assert calls[0].get_header("Referer") == "https://www.cninfo.com.cn/"
