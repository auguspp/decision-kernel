"""Read-only retained Research work projection; no provider, Research execution or promotion."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from decision_kernel.research_workflow_v1 import ResearchFunnelResult
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import incremental_disclosure as work
from test_incremental_disclosure import NOW, external_pair, packet

CODE = "a" * 40
WORK = "b" * 40
CONFIG = {
    "ref": work.WORK_REF,
    "prefix": work.WORK_PREFIX,
    "mode": "RETAINED_DISCLOSURE_CANDIDATE_READ_ONLY",
    "max_items": 8,
}


class WorkAPI:
    def __init__(self, files, *, starting_calls=0):
        self.files = dict(files)
        self.calls = starting_calls
        rows = [{"path": "README.md", "mode": "100644", "type": "blob",
                 "sha": read.blob_sha(b"data-only work ref"), "size": len(b"data-only work ref")}]
        for path, raw in sorted(self.files.items()):
            rows.append({"path": path, "mode": "100644", "type": "blob",
                         "sha": read.blob_sha(raw), "size": len(raw)})
        self.tree = {"sha": WORK, "tree": rows, "truncated": False}
        self.reads = []

    def get(self, endpoint):
        self.calls += 1
        self.reads.append(endpoint)
        if endpoint == "git/ref/heads/" + work.WORK_REF:
            return {"object": {"type": "commit", "sha": WORK}}
        if endpoint == "git/trees/" + WORK + "?recursive=1":
            return deepcopy(self.tree)
        raise AssertionError(endpoint)

    def file(self, path, ref):
        self.calls += 1
        self.reads.append("file:" + path)
        assert ref == WORK
        return self.files[path]


def candidate_files(*, offset_funnel=False):
    raw = packet(code="600036", day=8)
    key = work._packet(raw).assessment_input_hash
    input_raw, candidate_raw = external_pair(raw, complete=True)
    outcome = work.describe_outcome(reserved_packet=raw, input_raw=input_raw, candidate_raw=candidate_raw)
    funnel = ResearchFunnelResult.model_validate(outcome["validation"]["funnel_result"]).model_dump(mode="json")
    if offset_funnel:
        # Same instants, different ISO representation. Reader must compare parsed
        # original models rather than raw timestamp strings.
        def rewrite(value):
            if isinstance(value, dict):
                return {k: rewrite(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rewrite(v) for v in value]
            if value == NOW:
                return "2026-09-10T00:00:00+08:00"
            return value
        funnel = rewrite(funnel)
    base = work.WORK_PREFIX + key + "/"
    return key, {
        base + "packet.json": raw,
        base + "input.json": input_raw,
        base + "candidate.json": candidate_raw,
        base + "funnel.json": read.json_bytes(funnel),
    }


def failure_files():
    raw = packet(code="603986", day=5)
    key = work._packet(raw).assessment_input_hash
    failure = {
        "schema_version": 1,
        "record_kind": "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT",
        "assessment_input_hash": key,
        "packet_blob": read.blob_sha(raw),
        "packet_sha256": read.sha256(raw),
        "status": "SOURCE_PREFLIGHT_INCOMPLETE",
        "research_execution": "NOT_EXECUTED",
        "funnel_status": "NOT_REACHED",
        "formal_research_budget_used": 0,
        "started_at": "2026-09-09T16:00:00Z",
        "finished_at": "2026-09-09T16:01:00+00:00",
        **read.AUTHORITY,
    }
    base = work.WORK_PREFIX + key + "/"
    return key, {base + "packet.json": raw, base + "failure.json": read.json_bytes(failure)}


def collector(tmp_path, files, *, starting_calls=0):
    api = WorkAPI(files, starting_calls=starting_calls)
    return delivery.Collector(api, CODE, tmp_path, now=lambda: "2026-09-12T08:00:00Z"), api


def test_validated_candidate_is_discoverable_without_becoming_handoff(tmp_path, monkeypatch):
    key, files = candidate_files(offset_funnel=True)
    c, api = collector(tmp_path, files)
    # The ordinary production registration is independent and empty in this test.
    monkeypatch.setattr(c, "source", lambda spec: (
        b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n",
        {"path": spec["path"], "ref": CODE},
    ))
    result = c.research({"references": [], "historical_handoffs": [],
                         "additional_registered_handoffs": [], "research_work_read": CONFIG})
    work_read = result["candidate_work"]
    assert work_read["status"] == "READ_OK" and work_read["work_commit"] == WORK
    assert work_read["counts"]["VALIDATED_FUNNEL_CANDIDATE"] == 1
    item = work_read["items"][0]
    assert item["assessment_input_hash"] == key
    assert item["ticker"] == "600036" and item["terminal_state"] == "WAIT_FOR_TRIGGER"
    assert item["semantic_acceptance"] == "NOT_ESTABLISHED_BY_READER"
    assert not item["registered_current_handoff"]
    assert all(item[name] == "NONE" for name in read.AUTHORITY)
    assert result["handoffs"]["active"] == [] and result["handoffs"]["background"] == []
    assert not api.reads.count("file:" + work.WORK_PREFIX + key + "/README.md")


def test_pre_execution_failure_remains_failure_not_wait(tmp_path):
    key, files = failure_files()
    c, _ = collector(tmp_path, files)
    value = c.research_work(CONFIG)
    item = value["items"][0]
    assert item["assessment_input_hash"] == key
    assert item["status"] == "PRE_EXECUTION_FAILURE"
    assert item["failure_status"] == "SOURCE_PREFLIGHT_INCOMPLETE"
    assert item["research_execution"] == "NOT_EXECUTED" and item["terminal_state"] is None
    assert value["counts"]["VALIDATED_FUNNEL_CANDIDATE"] == 0


def test_reserved_packet_without_result_is_visible_not_quiet(tmp_path):
    raw = packet(code="300750", day=8)
    key = work._packet(raw).assessment_input_hash
    path = work.request_path(key)
    c, _ = collector(tmp_path, {path: raw})
    value = c.research_work(CONFIG)
    assert value["items"][0]["status"] == "RETAINED_NO_RESEARCH_RESULT"
    assert value["items"][0]["ticker"] == "300750"


def test_candidate_and_failure_on_same_key_fail_closed(tmp_path):
    _, files = candidate_files()
    key = next(iter({p[len(work.WORK_PREFIX):].split("/")[0] for p in files}))
    files[work.WORK_PREFIX + key + "/failure.json"] = failure_files()[1][next(
        p for p in failure_files()[1] if p.endswith("failure.json"))]
    c, _ = collector(tmp_path, files)
    with pytest.raises(ValueError, match="both candidate"):
        c.research_work(CONFIG)


def test_invalid_candidate_is_a_visible_research_gap_not_fallback(tmp_path, monkeypatch):
    _, files = candidate_files()
    candidate_path = next(p for p in files if p.endswith("candidate.json"))
    damaged = json.loads(files[candidate_path])
    damaged["input_hash"] = "0" * 64
    files[candidate_path] = read.json_bytes(damaged)
    c, _ = collector(tmp_path, files)
    monkeypatch.setattr(c, "source", lambda spec: (
        b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n",
        {"path": spec["path"], "ref": CODE},
    ))
    result = c.research({"references": [], "historical_handoffs": [],
                         "additional_registered_handoffs": [], "research_work_read": CONFIG})
    assert result["candidate_work"]["status"] == "UNAVAILABLE_OR_REJECTED"
    assert any(gap["status"] == "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET" for gap in result["gaps"])
    assert not result["handoffs"]["active"]


def test_unconfigured_registry_does_not_touch_work_ref(tmp_path, monkeypatch):
    c, api = collector(tmp_path, {})
    monkeypatch.setattr(c, "source", lambda spec: (
        b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n",
        {"path": spec["path"], "ref": CODE},
    ))
    result = c.research({"references": [], "historical_handoffs": [],
                         "additional_registered_handoffs": []})
    assert result["candidate_work"]["status"] == "NOT_CONFIGURED"
    assert api.reads == []


def test_item_bound_stops_before_packet_reads(tmp_path):
    files = {}
    for i in range(9):
        raw = packet(code="600036", day=8, version=hex(i + 1)[-1])
        key = work._packet(raw).assessment_input_hash
        files[work.request_path(key)] = raw
    c, api = collector(tmp_path, files)
    with pytest.raises(ValueError, match="item bound"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)


def test_api_reserve_stops_before_packet_reads(tmp_path):
    key, files = candidate_files()
    c, api = collector(tmp_path, files, starting_calls=delivery.MAX_API_CALLS - delivery.RESEARCH_WORK_API_RESERVE - 2)
    with pytest.raises(ValueError, match="API reserve"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)
    assert work.request_path(key) in files


def test_source_file_budget_stops_before_packet_reads(tmp_path):
    key, files = candidate_files()
    c, api = collector(tmp_path, files)
    c.sources = {(f"existing-{i}", CODE): (b"x", {})
                 for i in range(delivery.MAX_SOURCE_FILES - 3)}
    with pytest.raises(ValueError, match="source-file budget"):
        c.research_work(CONFIG)
    assert not any(row.startswith("file:") for row in api.reads)
    assert work.request_path(key) in files


@pytest.mark.parametrize("change", [
    {"mode": "AUTO_PROMOTE"},
    {"ref": "other"},
    {"prefix": "other/"},
    {"max_items": 999},
])
def test_read_config_cannot_expand_scope_or_authority(tmp_path, change):
    config = dict(CONFIG); config.update(change)
    c, _ = collector(tmp_path, {})
    with pytest.raises(ValueError):
        c.research_work(config)
