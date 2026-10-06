"""Regressions for opted-in work reading under the existing publication budget.

The fixture marks prior blobs as proven only to exercise the accounting seam;
the actual immutable-tree proof is owned/tested by read_blob_reuse.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime.read_blob_reuse import GitHubReadReuseAPI, pending_blob_writes
from test_current_state_research_work_read import (
    CODE, CONFIG, WORK, WorkAPI, candidate_files, failure_files,
)


class ReusableWorkAPI(WorkAPI, GitHubReadReuseAPI):
    """Original work fixture with the real publisher's typed reuse capability."""


def prepared(tmp_path, *, files=None, calls=77, proven=True, ordinary=False):
    if files is None:
        _, files = candidate_files()
    api_type = WorkAPI if ordinary else ReusableWorkAPI
    api = api_type(files, starting_calls=calls)
    c = delivery.Collector(api, CODE, tmp_path)
    # Reproduce the retained production failure's 77 calls / 111 files / 58
    # shared sources without using live data, credentials or provider requests.
    c.files = {f"baseline/{i}.json": f"retained-{i}".encode() for i in range(111)}
    c.sources = {(f"registered-{i}", CODE): (f"source-{i}".encode(), {"id": i})
                 for i in range(58)}
    api.proven_read_blobs = frozenset(read.blob_sha(raw) for raw in c.files.values()) if proven else frozenset()
    return c, api


def include(c):
    result = {"gaps": [], "handoffs": {"active": [], "background": []}}
    c.include_research_work({"research_work_read": CONFIG}, result)
    return result


def test_proven_blobs_admit_work_and_leave_shared_cache_unchanged(tmp_path):
    c, api = prepared(tmp_path)
    original_files, shared = dict(c.files), c.sources
    shared_value = deepcopy(shared)
    result = include(c)
    value = result["candidate_work"]
    assert value["status"] == "READ_OK"
    assert value["item_count"] == 1
    assert value["counts"]["VALIDATED_FUNNEL_CANDIDATE"] == 1
    assert c.sources is shared and c.sources == shared_value
    assert all(c.files[path] == raw for path, raw in original_files.items())
    for item in value["items"]:
        assert not item["registered_current_handoff"]
        assert item["semantic_acceptance"] == "NOT_ESTABLISHED_BY_READER"
        assert all(item[name] == "NONE" for name in read.AUTHORITY)
        for source in item["sources"].values():
            raw = c.files[source["read_path"]]
            assert source["ref"] == WORK
            assert read.blob_sha(raw) == source["git_blob"]
            assert read.sha256(raw) == source["sha256"]
    assert result["handoffs"] == {"active": [], "background": []}
    # Four work bodies plus two not-yet-generated entry files and five Git ops.
    assert pending_blob_writes(api, c.files) == 4
    assert api.calls + pending_blob_writes(api, c.files) + 2 + 5 <= delivery.MAX_API_CALLS


@pytest.mark.parametrize("ordinary, proven", [(False, False), (True, True)])
def test_absent_or_untyped_proof_cannot_discount_publication(tmp_path, ordinary, proven):
    c, api = prepared(tmp_path, ordinary=ordinary, proven=proven)
    original_files, shared = dict(c.files), c.sources
    result = include(c)
    assert result["candidate_work"]["diagnostic"]["code"] == "BASE_PUBLICATION_RESERVE"
    assert result["candidate_work"]["diagnostic"]["source_count_after_rollback"] == 58
    assert api.reads == [] and api.calls == 77
    assert c.files == original_files and c.sources is shared


def test_old_entry_blobs_still_reserve_two_fresh_entry_writes(tmp_path):
    c, api = prepared(tmp_path, calls=172)
    c.files = {"README.md": b"old summary", "current-state.json": b"old entry"}
    api.proven_read_blobs = frozenset(read.blob_sha(raw) for raw in c.files.values())
    result = include(c)
    assert result["candidate_work"]["diagnostic"]["code"] == "BASE_PUBLICATION_RESERVE"
    assert api.reads == []  # 172 + 2 metadata + 2 replacements + 5 > 180


def test_unread_work_blobs_are_conservatively_budgeted_before_packet_reads(tmp_path):
    _, candidate = candidate_files()
    _, failure = failure_files()
    files = {**candidate, **failure}
    assert len(files) == 6
    c, api = prepared(tmp_path, files=files, calls=159)
    # Declared work hashes being present is NOT a reason to skip source reads or
    # drop their conservative prospective write reserve.
    api.proven_read_blobs |= frozenset(read.blob_sha(raw) for raw in files.values())
    before, shared = dict(c.files), c.sources
    result = include(c)
    assert result["candidate_work"]["diagnostic"]["code"] == "WORK_PUBLICATION_RESERVE"
    assert api.calls == 161
    assert not any(row.startswith("file:") for row in api.reads)
    assert c.files == before and c.sources is shared


def test_work_local_source_limit_still_rejects_before_packet_reads(tmp_path, monkeypatch):
    c, api = prepared(tmp_path)
    before, shared = dict(c.files), c.sources
    monkeypatch.setattr(delivery, "MAX_SOURCE_FILES", 3)
    result = include(c)
    assert result["candidate_work"]["diagnostic"]["code"] == "SOURCE_FILE_BUDGET"
    assert result["candidate_work"]["diagnostic"]["source_count_after_rollback"] == 58
    assert not any(row.startswith("file:") for row in api.reads)
    assert c.files == before and c.sources is shared


def test_rejected_work_restores_shared_cache_and_bytes_without_refunding_calls(tmp_path):
    c, api = prepared(tmp_path)
    before, shared = dict(c.files), c.sources
    target = next(path for path in api.files if path.endswith("candidate.json"))
    # Keep the original tree binding while corrupting the body actually read.
    api.files[target] += b"\n"
    result = include(c)
    assert result["candidate_work"]["status"] == "UNAVAILABLE_OR_REJECTED"
    assert result["candidate_work"]["diagnostic"]["code"] == "WORK_BLOB_MISMATCH"
    assert result["candidate_work"]["diagnostic"]["source_count_after_rollback"] == 58
    assert result["candidate_work"]["diagnostic"]["api_calls_after_attempt"] == api.calls
    assert api.calls > 79
    assert c.files == before and c.sources is shared


def test_retained_failure_does_not_become_a_candidate_after_budget_repair(tmp_path):
    _, files = failure_files()
    c, api = prepared(tmp_path, files=files)
    shared = c.sources
    value = include(c)["candidate_work"]
    assert value["status"] == "READ_OK"
    assert value["counts"]["PRE_EXECUTION_FAILURE"] == 1
    assert value["counts"]["VALIDATED_FUNNEL_CANDIDATE"] == 0
    assert value["items"][0]["research_execution"] == "NOT_EXECUTED"
    assert value["items"][0]["terminal_state"] is None
    assert c.sources is shared
    assert api.calls <= delivery.MAX_API_CALLS


def test_unconfigured_inclusion_preserves_cache_object_without_reads(tmp_path):
    c, api = prepared(tmp_path)
    shared, files = c.sources, dict(c.files)
    result = {"candidate_work": {"status": "NOT_CONFIGURED"}, "gaps": []}
    c.include_research_work({}, result)
    assert result == {"candidate_work": {"status": "NOT_CONFIGURED"}, "gaps": []}
    assert c.sources is shared and c.files == files and api.reads == []
