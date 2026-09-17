from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import disclosure_work_capacity as capacity


class Collector:
    def __init__(self, *, calls=41, max_calls=None):
        self.sources = {("baseline", "a" * 40): (b"baseline", {})}
        self.files = {"baseline.txt": b"baseline"}
        values = {"calls": calls}
        if max_calls is not None:
            values["max_calls"] = max_calls
        self.api = SimpleNamespace(**values)
        self.seen_sources = None
        self.seen_api_calls = None
        self.calls = 0

    def source(self, spec):
        assert spec == {"path": "current_state/registry.json"}
        return json.dumps({"research_work_read": {"ref": "research-work/disclosures-v0"}}).encode(), {}

    def research_work(self, config):
        self.calls += 1
        self.seen_sources = dict(self.sources)
        self.seen_api_calls = self.api.calls
        self.files["sources/git/work.json"] = b"work"
        return {"status": "READ_OK", "items": [], "config": config}


def baseline(code="SOURCE_FILE_BUDGET"):
    return {"research": {
        "candidate_work": {"status": "UNAVAILABLE_OR_REJECTED", "error_type": "ValueError",
                           "diagnostic": {"code": code}},
        "gaps": [{"status": "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET", "error_type": "ValueError"},
                 {"status": "OTHER_GAP"}],
    }}


def test_exact_source_budget_retries_same_reader_with_separate_registry():
    collector = Collector()
    original_sources = collector.sources
    original_api = collector.api
    result = capacity.retry_if_source_budget(collector, baseline())
    assert collector.calls == 1
    assert collector.seen_sources == {}
    assert collector.sources is original_sources
    assert collector.api is original_api
    assert result["research"]["candidate_work"]["status"] == "READ_OK"
    assert result["research"]["gaps"] == [{"status": "OTHER_GAP"}]
    assert collector.files["sources/git/work.json"] == b"work"


def test_existing_optional_api_extension_is_visible_only_as_rebased_accounting():
    collector = Collector(calls=53, max_calls=delivery.MAX_API_CALLS + 72)
    original_api = collector.api
    result = capacity.retry_if_source_budget(collector, baseline())
    assert result["research"]["candidate_work"]["status"] == "READ_OK"
    assert collector.seen_api_calls == 0  # max(0, actual 53 - existing optional 72)
    assert collector.api is original_api
    assert collector.api.calls == 53
    assert collector.api.max_calls == delivery.MAX_API_CALLS + 72


def test_optional_api_view_never_invents_more_than_existing_72_call_envelope():
    api = SimpleNamespace(calls=250, max_calls=delivery.MAX_API_CALLS + 200)
    assert capacity._available_optional_extension(api) == 72
    view = capacity._OptionalApiAccountingView(api, 72)
    assert view.calls == 178
    assert api.calls == 250
    assert view.max_calls == delivery.MAX_API_CALLS
    with pytest.raises(ValueError, match="invalid optional Disclosure API extension"):
        capacity._OptionalApiAccountingView(api, 73)
    with pytest.raises(ValueError, match="exceeds underlying bound"):
        capacity._OptionalApiAccountingView(
            SimpleNamespace(calls=50, max_calls=delivery.MAX_API_CALLS), 1)


def test_unrelated_rejection_is_not_retried_or_reclassified():
    collector = Collector(max_calls=delivery.MAX_API_CALLS + 72)
    before = baseline("WORK_ITEM_BOUND")
    result = capacity.retry_if_source_budget(collector, before)
    assert result is before
    assert collector.calls == 0
    assert collector.sources


def test_failed_separate_projection_keeps_original_gap_and_exposes_safe_retry_diagnostic(monkeypatch):
    collector = Collector(calls=53, max_calls=delivery.MAX_API_CALLS + 72)
    original_sources = collector.sources
    original_api = collector.api

    def fail(config):
        collector.calls += 1
        assert collector.sources == {}
        assert collector.api is not original_api
        raise ValueError("research work read would exhaust publication API reserve")

    monkeypatch.setattr(collector, "research_work", fail)
    before = baseline()
    result = capacity.retry_if_source_budget(collector, before)
    assert result is not before
    assert collector.calls == 1
    assert collector.sources is original_sources
    assert collector.api is original_api
    assert result["research"]["gaps"] == before["research"]["gaps"]
    candidate = result["research"]["candidate_work"]
    assert candidate["diagnostic"]["code"] == "SOURCE_FILE_BUDGET"
    retry = candidate["separate_capacity_retry"]
    assert retry["status"] == "UNAVAILABLE_OR_REJECTED"
    assert retry["error_type"] == "ValueError"
    assert retry["diagnostic"]["code"] == "WORK_PUBLICATION_RESERVE"
    assert retry["diagnostic"]["api_calls_after_attempt"] == 53
    assert retry["meaning"].endswith("NOT_RESEARCH_EXECUTION_OR_ACCEPTANCE")


def test_unknown_retry_failure_never_publishes_exception_text(monkeypatch):
    collector = Collector(calls=60, max_calls=delivery.MAX_API_CALLS + 72)

    def fail(_):
        raise ValueError("PRIVATE_OR_UNTRUSTED_PROVIDER_TEXT")

    monkeypatch.setattr(collector, "research_work", fail)
    result = capacity.retry_if_source_budget(collector, baseline())
    retry = result["research"]["candidate_work"]["separate_capacity_retry"]
    assert retry["diagnostic"]["code"] == "UNCLASSIFIED_READ_REJECTION"
    assert "PRIVATE" not in json.dumps(retry)
