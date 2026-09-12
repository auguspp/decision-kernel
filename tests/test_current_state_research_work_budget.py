"""Regression-first checks: optional work must not consume base publication capacity."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state_research_work_read import CONFIG, CODE, candidate_files, collector


def quiet_registration(c, monkeypatch):
    monkeypatch.setattr(c, "source", lambda spec: (
        b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n",
        {"path": spec["path"], "ref": CODE},
    ))
    return {"references": [], "historical_handoffs": [],
            "additional_registered_handoffs": [], "research_work_read": CONFIG}


def test_optional_work_reserves_all_publish_blobs_before_body_reads(tmp_path):
    _, files = candidate_files()
    c, api = collector(tmp_path, files, starting_calls=72)
    c.files = {f"details/baseline/{n}.json": b"{}" for n in range(100)}
    # The original baseline needs 100 retained blobs + 2 entry blobs + 5
    # publication operations: 72 + 107 = 179, within the unchanged 180 cap.
    assert api.calls + len(c.files) + 7 <= delivery.MAX_API_CALLS
    before = dict(c.files)
    with pytest.raises(ValueError, match="API reserve"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)
    assert c.files == before
    assert api.calls + len(c.files) + 7 <= delivery.MAX_API_CALLS


def test_optional_work_obeys_existing_source_file_ceiling(tmp_path):
    _, files = candidate_files()
    c, api = collector(tmp_path, files)
    c.sources = {(f"docs/existing-{n}.md", CODE): (b"existing", {})
                 for n in range(delivery.MAX_SOURCE_FILES)}
    before = dict(c.sources)
    with pytest.raises(ValueError, match="source"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)
    assert c.sources == before


def test_work_sources_participate_in_existing_cache_and_ceiling(tmp_path):
    _, files = candidate_files()
    c, _ = collector(tmp_path, files)
    value = c.research_work(CONFIG)
    assert len(c.sources) == len(value["items"][0]["sources"]) == 4


def test_failed_optional_read_cannot_leave_unreferenced_retention(tmp_path, monkeypatch):
    _, files = candidate_files()
    path = next(p for p in files if p.endswith("candidate.json"))
    damaged = json.loads(files[path]); damaged["input_hash"] = "0" * 64
    files[path] = read.json_bytes(damaged)
    c, _ = collector(tmp_path, files)
    c.files = {"details/baseline.json": b"already qualified"}
    baseline = dict(c.files)
    registry = quiet_registration(c, monkeypatch)
    result = c.research(registry)
    assert result["candidate_work"]["status"] == "UNAVAILABLE_OR_REJECTED"
    assert c.files == baseline
    assert not c.sources


def test_optional_work_rejects_retention_limit_before_source_reads(tmp_path, monkeypatch):
    _, files = candidate_files()
    c, api = collector(tmp_path, files)
    c.files = {"details/baseline.json": b"already qualified"}
    before = dict(c.files)
    monkeypatch.setattr(delivery, "MAX_RETAINED_OUTPUT", sum(map(len, before.values())) + 1)
    with pytest.raises(ValueError, match="retention"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)
    assert c.files == before


def test_original_handoffs_are_read_before_optional_work(tmp_path, monkeypatch):
    c, _ = collector(tmp_path, {})
    registry = quiet_registration(c, monkeypatch)
    order = []
    def handoffs(*args):
        order.append("handoffs")
        return {"active": [], "background": []}
    def work(config):
        order.append("work")
        return {"status": "READ_OK", "items": []}
    monkeypatch.setattr(delivery, "project_registered_handoffs", handoffs)
    monkeypatch.setattr(c, "research_work", work)
    c.research(registry)
    assert order == ["handoffs", "work"]


def test_collection_reads_capability_sources_before_optional_work(tmp_path, monkeypatch):
    c, _ = collector(tmp_path, {})
    order = []
    registry = {"schema_version": 1, "references": [], "historical_handoffs": [],
                "additional_registered_handoffs": [], "research_work_read": CONFIG,
                "capability_gaps": [{"id": "cap", "status": "UNKNOWN",
                                     "source": {"path": "docs/cap.md"}}]}
    def source(spec):
        path = spec["path"]
        if path == delivery.REGISTRY_PATH:
            return read.json_bytes(registry), {"path": path}
        if path == "docs/cap.md":
            order.append("capability")
        return b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n", {"path": path}
    def work(config):
        order.append("work")
        return {"status": "READ_OK", "items": []}
    monkeypatch.setattr(c, "source", source)
    monkeypatch.setattr(c, "lane", lambda lane: {})
    monkeypatch.setattr(c, "research_work", work)
    monkeypatch.setattr(read, "assemble", lambda **kwargs: {"research": kwargs["research"]})
    monkeypatch.setattr(read, "render_summary", lambda payload: "reading")
    c.collect({})
    assert order == ["capability", "work"]


def test_final_entry_overflow_drops_optional_projection_not_base(tmp_path, monkeypatch):
    c, _ = collector(tmp_path, {})
    c.files = {"details/base.json": b"preserved"}
    registry = {"schema_version": 1, "references": [], "historical_handoffs": [],
                "additional_registered_handoffs": [], "research_work_read": CONFIG,
                "capability_gaps": []}
    def source(spec):
        if spec["path"] == delivery.REGISTRY_PATH:
            return read.json_bytes(registry), {"path": spec["path"]}
        return b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n", {"path": spec["path"]}
    def work(config):
        c.files["sources/git/optional.json"] = b"optional saved copy"
        return {"status": "READ_OK", "items": [], "large_reason": "X" * 4000}
    monkeypatch.setattr(c, "source", source)
    monkeypatch.setattr(c, "lane", lambda lane: {})
    monkeypatch.setattr(c, "research_work", work)
    monkeypatch.setattr(read, "assemble", lambda **kwargs: {"research": kwargs["research"]})
    monkeypatch.setattr(read, "render_summary", lambda payload: "reading")
    monkeypatch.setattr(delivery, "MAX_RETAINED_OUTPUT", 2500)
    value = c.collect({})
    assert value["research"]["candidate_work"]["status"] == "UNAVAILABLE_OR_REJECTED"
    assert value["research"]["candidate_work"]["error_type"] == "ReadingEntryRetentionLimit"
    assert c.files["details/base.json"] == b"preserved"
    assert "sources/git/optional.json" not in c.files
    assert sum(map(len, c.files.values())) <= delivery.MAX_RETAINED_OUTPUT
    assert set(c.files) == {"details/base.json", "current-state.json", "README.md"}
