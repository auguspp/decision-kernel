"""The original work reader budgets actual proven-blob publication, not file count."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime.read_blob_reuse import GitHubReadReuseAPI, pending_blob_writes
from test_current_state_research_work_read import (
    CODE, CONFIG, WorkAPI, candidate_files, failure_files,
)

PRIOR = "c" * 40
TREE = "d" * 40


class ReusingWorkAPI(WorkAPI, GitHubReadReuseAPI):
    """Memory transport; exercise the real immutable-tree proof and work reader."""
    def __init__(self, files, previous_files, *, starting_calls=75):
        WorkAPI.__init__(self, files, starting_calls=starting_calls)
        self.max_calls = delivery.MAX_API_CALLS
        self.proven_read_blobs = frozenset()
        self.blob_reuse_origin = self.blob_reuse_attempt = None
        self.blob_reuse_hits = 0
        self.previous_objects = {
            "git/commits/" + PRIOR: {"sha": PRIOR, "tree": {"sha": TREE}},
            "git/trees/" + TREE + "?recursive=1": {
                "sha": TREE, "truncated": False,
                "tree": [{"path": path, "sha": model.blob_sha(raw),
                          "mode": "100644", "type": "blob", "size": len(raw)}
                         for path, raw in previous_files.items()],
            },
        }

    def get(self, endpoint):
        if endpoint in self.previous_objects:
            self.calls += 1
            self.reads.append(endpoint)
            result = deepcopy(self.previous_objects[endpoint])
        else:
            result = WorkAPI.get(self, endpoint)
        assert self.calls <= self.max_calls
        return result

    def file(self, path, ref):
        result = WorkAPI.file(self, path, ref)
        assert self.calls <= self.max_calls
        return result


def saved_files():
    return {f"already/{i}.json": str(i).encode() for i in range(111)}


def reader(tmp_path, work_files, *, before=None, previous=None, calls=75):
    before = saved_files() if before is None else before
    previous = before if previous is None else previous
    api = ReusingWorkAPI(work_files, previous, starting_calls=calls)
    api.prime_previous_reading(PRIOR)
    c = delivery.Collector(api, CODE, tmp_path, now=lambda: "2026-09-12T08:00:00Z")
    c.files = dict(before)
    return c, api


def test_proven_111_file_baseline_at_77_calls_keeps_candidate_and_failure(tmp_path):
    _, good = candidate_files()
    _, failed = failure_files()
    c, api = reader(tmp_path, {**good, **failed})
    before = dict(c.files)
    assert api.calls == 77 and pending_blob_writes(api, before) == 0
    result = c.research_work(CONFIG)
    assert result["status"] == "READ_OK"
    assert result["counts"]["VALIDATED_FUNNEL_CANDIDATE"] == 1
    assert result["counts"]["PRE_EXECUTION_FAILURE"] == 1
    assert all(c.files[path] == raw for path, raw in before.items())
    for item in result["items"]:
        assert not item["registered_current_handoff"]
        assert all(item[key] == "NONE" for key in model.AUTHORITY)
    assert api.calls > 77
    # Two future entry files plus the unchanged native publication operations.
    assert api.calls + pending_blob_writes(api, c.files) + 2 + 5 <= delivery.MAX_API_CALLS
    assert api.max_calls == delivery.MAX_API_CALLS == 180
    assert delivery.MAX_SOURCE_FILES == 60


def test_missing_or_spoofed_reuse_proof_gets_no_budget_credit(tmp_path):
    _, files = candidate_files()
    for mode in ("unprimed", "unrelated_api"):
        before = saved_files()
        api = (ReusingWorkAPI(files, before, starting_calls=77) if mode == "unprimed"
               else WorkAPI(files, starting_calls=77))
        if mode == "unrelated_api":
            api.proven_read_blobs = frozenset(model.blob_sha(raw) for raw in before.values())
        c = delivery.Collector(api, CODE, tmp_path)
        c.files = before
        with pytest.raises(ValueError, match="base publication budget"):
            c.research_work(CONFIG)
        assert api.calls == 77 and api.reads == [] and c.files == before


def test_changed_bytes_cannot_borrow_previous_path_identity(tmp_path):
    _, files = candidate_files()
    previous = saved_files()
    before = {path: raw + b"changed" for path, raw in previous.items()}
    c, api = reader(tmp_path, files, before=before, previous=previous)
    assert pending_blob_writes(api, c.files) == 111
    reads = list(api.reads)
    with pytest.raises(ValueError, match="base publication budget"):
        c.research_work(CONFIG)
    assert api.reads == reads and api.calls == 77 and c.files == before


def test_unassembled_entries_still_reserve_two_fresh_writes(tmp_path):
    _, files = candidate_files()
    before = {**saved_files(), "README.md": b"old entry", "current-state.json": b"old index"}
    c, api = reader(tmp_path, files, before=before, calls=170)
    assert api.calls == 172 and pending_blob_writes(api, c.files) == 0
    reads = list(api.reads)
    with pytest.raises(ValueError, match="base publication budget"):
        c.research_work(CONFIG)
    assert api.reads == reads and api.calls == 172


def test_unread_work_paths_reserve_writes_even_when_tree_blobs_are_known(tmp_path):
    _, files = candidate_files()
    before = saved_files()
    previous = dict(list(before.items())[16:])  # Sixteen retained bytes are new.
    previous.update({"work/" + str(i): raw for i, raw in enumerate(files.values())})
    c, api = reader(tmp_path, files, before=before, previous=previous, calls=145)
    assert api.calls == 147 and pending_blob_writes(api, c.files) == 16
    with pytest.raises(ValueError, match="exhaust publication API reserve"):
        c.research_work(CONFIG)
    assert api.calls == 149  # Only work ref/tree metadata, no candidate bodies.
    assert not any(path.startswith("file:") for path in api.reads)
    assert c.files == before


def test_blob_reuse_does_not_change_sixty_source_limit(tmp_path):
    _, files = candidate_files()
    c, api = reader(tmp_path, files)
    c.sources = {(str(i), CODE): (b"old", {}) for i in range(58)}
    sources = dict(c.sources)
    with pytest.raises(ValueError, match="source-file budget"):
        c.research_work(CONFIG)
    assert c.sources == sources and api.calls == 79
    assert not any(path.startswith("file:") for path in api.reads)


def test_reuse_does_not_hide_invalid_candidate_or_restore_spent_calls(tmp_path):
    _, files = candidate_files()
    path = next(p for p in files if p.endswith("candidate.json"))
    damaged = json.loads(files[path])
    damaged["input_hash"] = "0" * 64
    files[path] = model.json_bytes(damaged)
    c, api = reader(tmp_path, files)
    before = dict(c.files)
    research = {"gaps": [{"status": "OTHER_GAP"}]}
    c.include_research_work({"research_work_read": CONFIG}, research)
    assert research["candidate_work"]["status"] == "UNAVAILABLE_OR_REJECTED"
    assert research["gaps"][0] == {"status": "OTHER_GAP"}
    assert research["gaps"][1]["status"] == "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET"
    assert c.files == before and c.sources == {} and api.calls > 79
