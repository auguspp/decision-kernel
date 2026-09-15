from __future__ import annotations

import json
from types import SimpleNamespace

from decision_kernel.runtime import disclosure_work_capacity as capacity


class Collector:
    def __init__(self):
        self.sources = {("baseline", "a" * 40): (b"baseline", {})}
        self.files = {"baseline.txt": b"baseline"}
        self.api = SimpleNamespace(calls=41)
        self.seen_sources = None
        self.calls = 0

    def source(self, spec):
        assert spec == {"path": "current_state/registry.json"}
        return json.dumps({"research_work_read": {"ref": "research-work/disclosures-v0"}}).encode(), {}

    def research_work(self, config):
        self.calls += 1
        self.seen_sources = dict(self.sources)
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
    result = capacity.retry_if_source_budget(collector, baseline())
    assert collector.calls == 1
    assert collector.seen_sources == {}
    assert collector.sources is original_sources
    assert result["research"]["candidate_work"]["status"] == "READ_OK"
    assert result["research"]["gaps"] == [{"status": "OTHER_GAP"}]
    assert collector.files["sources/git/work.json"] == b"work"


def test_unrelated_rejection_is_not_retried_or_reclassified():
    collector = Collector()
    before = baseline("WORK_ITEM_BOUND")
    result = capacity.retry_if_source_budget(collector, before)
    assert result is before
    assert collector.calls == 0
    assert collector.sources


def test_failed_separate_projection_keeps_original_visible_gap(monkeypatch):
    collector = Collector()
    def fail(config):
        collector.calls += 1
        assert collector.sources == {}
        raise ValueError("still rejected")
    monkeypatch.setattr(collector, "research_work", fail)
    before = baseline()
    result = capacity.retry_if_source_budget(collector, before)
    assert result is before
    assert collector.calls == 1
    assert collector.sources
    assert before["research"]["candidate_work"]["diagnostic"]["code"] == "SOURCE_FILE_BUDGET"
