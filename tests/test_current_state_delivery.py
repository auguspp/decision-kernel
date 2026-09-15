"""Bounded metadata acquisition and atomic derived-ref publication, with no provider."""
import base64
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state import AT, SHA, archive_fixture, run


class API:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.writes = []
        self.reads = []
        self.blobs = {}

    def get(self, endpoint):
        self.reads.append(endpoint)
        return self.responses[endpoint]

    def write(self, endpoint, body, method="POST"):
        self.writes.append((endpoint, body, method))
        if endpoint == "git/blobs":
            raw = base64.b64decode(body["content"])
            key = read.blob_sha(raw)
            self.blobs[key] = raw
            return {"sha": key}
        if endpoint == "git/trees":
            return {"sha": "b" * 40}
        if endpoint == "git/commits":
            return {"sha": "c" * 40}
        return {"ref": body.get("ref")}

    def file(self, path, ref):
        assert ref == "c" * 40 and path == "current-state.json"
        return b"index"


def test_latest_success_rejection_does_not_try_older_success(monkeypatch, tmp_path):
    collector = delivery.Collector(API(), SHA, tmp_path, now=lambda: AT)
    monkeypatch.setattr(collector, "runs", lambda lane: ([run(10), run(9, day=7)], True))
    attempted = []
    def reject(lane, selected):
        attempted.append(selected["id"])
        raise ValueError("latest archive rejected")
    monkeypatch.setattr(collector, "saved_product", reject)
    result = collector.lane("sector")
    assert attempted == [10]
    assert result["health"] == "LATEST_SUCCESS_INPUT_REJECTED"
    assert result["last_qualified_result"] is None


def test_failure_keeps_current_attempt_and_last_success_separate(monkeypatch, tmp_path):
    collector = delivery.Collector(API(), SHA, tmp_path, now=lambda: AT)
    # Inbox failure does not attempt to infer a typed result from absent HTML.
    monkeypatch.setattr(collector, "runs", lambda lane: ([run(10, lane="inbox", conclusion="failure"), run(9, lane="inbox", day=7)], True))
    monkeypatch.setattr(collector, "saved_product", lambda lane, chosen: {"run": chosen, "market_session": "2026-09-07"})
    result = collector.lane("inbox")
    assert result["latest_attempt"]["id"] == 10
    assert result["last_qualified_result"]["run"]["id"] == 9
    assert result["health"] == "LATEST_ATTEMPT_FAILED"


def test_stock_other_trial_success_is_not_a_stock_result(tmp_path):
    stock, unrelated = run(10, lane="stock"), run(11, lane="stock")
    api = API({
        "actions/workflows/hithink-stock-dump-trial.yml/runs?branch=main&per_page=20": {"total_count": 2, "workflow_runs": [unrelated, stock]},
        "actions/runs/10/jobs?per_page=100": {"total_count": 1, "jobs": [{"name": "stock-reading", "conclusion": "success"}]},
        "actions/runs/11/jobs?per_page=100": {"total_count": 1, "jobs": [{"name": "stock-reading", "conclusion": "skipped"}]},
    })
    selected, complete = delivery.Collector(api, SHA, tmp_path).runs("stock")
    assert selected == [stock] and complete


def test_running_stock_purpose_not_yet_exposed_is_check_incomplete(tmp_path):
    candidate = run(lane="stock", status="queued", conclusion=None)
    api = API({
        "actions/workflows/hithink-stock-dump-trial.yml/runs?branch=main&per_page=20": {"total_count": 1, "workflow_runs": [candidate]},
        "actions/runs/10/jobs?per_page=100": {"total_count": 0, "jobs": []},
    })
    assert delivery.Collector(api, SHA, tmp_path).runs("stock") == ([], False)


def test_same_source_is_loaded_once_and_pinned_in_all_references(monkeypatch, tmp_path):
    calls = []
    def source(root, ref, path):
        calls.append((ref, path))
        return b"frozen source"
    monkeypatch.setattr(delivery, "git_file", source)
    collector = delivery.Collector(API(), SHA, tmp_path)
    first = collector.source({"path": "docs/a.md"})
    assert collector.source({"path": "docs/a.md"}) == first
    assert calls == [(SHA, "docs/a.md")]
    assert first[1]["ref"] == SHA
    with pytest.raises(ValueError, match="frozen blob"):
        collector.source({"path": "docs/a.md", "git_blob": "0" * 40})


def test_repeated_archive_uses_same_bytes_without_second_download(tmp_path):
    raw, metadata = archive_fixture()
    class Download(API):
        def archive(self, artifact):
            self.reads.append(artifact["id"])
            return raw
    api = Download()
    collector = delivery.Collector(api, SHA, tmp_path)
    assert collector.archive(metadata, run()) == collector.archive(metadata, run())
    assert api.reads == [100]
    assert len(collector.files) == 1


def test_previous_exact_archive_can_accelerate_read_but_not_expired_admission(tmp_path):
    raw, metadata = archive_fixture()
    old = {"lanes": {"sector": {"last_qualified_result": {"archive": {
        "artifact_id": 100, "sha256": read.sha256(raw), "git_blob": read.blob_sha(raw)}}}}}
    api = API({"git/blobs/" + read.blob_sha(raw): {"content": base64.b64encode(raw).decode()}})
    collector = delivery.Collector(api, SHA, tmp_path, previous=old)
    assert collector.archive(metadata, run())[0] == {"summary.md": b"saved content"}
    assert len(api.reads) == 1
    other = delivery.Collector(api, SHA, tmp_path, previous=old)
    with pytest.raises(ValueError, match="expired"):
        other.archive(dict(metadata, expired=True), run())


def test_publication_is_one_dedicated_ref_fast_forward_with_old_tree_retained():
    prior = "d" * 40
    api = API({"git/commits/" + prior: {"tree": {"sha": "e" * 40}}})
    result = delivery.publish(api, {"current-state.json": b"index", "details/x.md": b"source"}, prior, SHA, "f" * 64)
    assert result == "c" * 40
    assert api.writes[-1] == ("git/refs/heads/" + read.READ_REF, {"sha": "c" * 40, "force": False}, "PATCH")
    tree = next(body for endpoint, body, _ in api.writes if endpoint == "git/trees")
    assert tree["base_tree"] == "e" * 40
    assert all(endpoint.startswith("git/") for endpoint, _, _ in api.writes)


def test_concurrent_publication_failure_does_not_force_or_retry():
    class Conflict(API):
        def write(self, endpoint, body, method="POST"):
            result = super().write(endpoint, body, method)
            if method == "PATCH":
                raise delivery.GitHubReadError("GitHub HTTP 422")
            return result
    prior = "d" * 40
    api = Conflict({"git/commits/" + prior: {"tree": {"sha": "e" * 40}}})
    with pytest.raises(delivery.GitHubReadError):
        delivery.publish(api, {"current-state.json": b"index"}, prior, SHA, "f" * 64)
    refs = [(body, method) for endpoint, body, method in api.writes if endpoint.startswith("git/refs")]
    assert refs == [({"sha": "c" * 40, "force": False}, "PATCH")]


def test_initial_read_ref_is_orphan_not_a_copy_of_code_main():
    api = API()
    delivery.publish(api, {"current-state.json": b"index"}, None, SHA, "f" * 64)
    tree = next(body for endpoint, body, _ in api.writes if endpoint == "git/trees")
    commit = next(body for endpoint, body, _ in api.writes if endpoint == "git/commits")
    assert "base_tree" not in tree and commit["parents"] == []
    assert api.writes[-1][1]["ref"] == "refs/heads/" + read.READ_REF


@pytest.mark.parametrize("endpoint,method", [("actions/workflows/x/dispatches", "POST"),
    ("git/refs/heads/main", "PATCH"), ("contents/a.md", "PUT"), ("issues", "POST")])
def test_transport_rejects_any_non_read_ref_mutation(endpoint, method):
    api = delivery.GitHubAPI("synthetic-test-token-not-a-secret")
    with pytest.raises(ValueError, match="write outside"):
        api.write(endpoint, {}, method)
    assert api.calls == 0


def test_source_text_cannot_publish_a_workflow_on_read_ref():
    with pytest.raises(ValueError, match="executable"):
        delivery.publish(API(), {".github/workflows/attack.yml": b"bad"}, None, SHA, "f" * 64)


def test_refresh_workflow_only_aggregates_saved_results_and_executes_trusted_main():
    raw = Path(".github/workflows/current-state-read-entry.yml").read_text()
    assert "workflow_run:" in raw and "types: [requested, completed]" in raw
    assert "schedule:" not in raw and "workflow_dispatch:" not in raw
    assert "ref: ${{ github.sha }}" in raw and "persist-credentials: false" in raw
    assert "head_repository.full_name == github.repository" in raw
    assert "github.event.workflow_run.event == 'push'" in raw
    assert "github.event.workflow_run.conclusion == 'success'" in raw
    assert "current_state_delivery" in raw and "--publish" in raw
    assert "secrets." not in raw and "HITHINK_FINANCE_API_KEY" not in raw
    assert "cancel-in-progress: false" in raw
    producer = Path(read.WORKFLOWS["sector"]).read_text()
    trigger = producer.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in trigger and "schedule:" not in trigger and "cron:" not in trigger
    assert "current_state_delivery" not in producer


def test_bad_candidate_readback_does_not_advance_previous_read_ref():
    class BadRead(API):
        def file(self, path, ref):
            return b"wrong"
    prior = "d" * 40
    api = BadRead({"git/commits/" + prior: {"tree": {"sha": "e" * 40}}})
    with pytest.raises(ValueError, match="readback"):
        delivery.publish(api, {"current-state.json": b"index"}, prior, SHA, "f" * 64)
    assert not any(endpoint.startswith("git/refs") for endpoint, _, _ in api.writes)


def test_cached_archive_does_not_bypass_new_identity_or_expiry_check(tmp_path):
    raw, metadata = archive_fixture()
    class Download(API):
        def archive(self, artifact):
            return raw
    collector = delivery.Collector(Download(), SHA, tmp_path)
    collector.archive(metadata, run())
    with pytest.raises(ValueError, match="identity"):
        collector.archive(metadata, run(11))
    with pytest.raises(ValueError, match="expired"):
        collector.archive(dict(metadata, expired=True), run())


def test_history_versions_at_same_path_are_not_collapsed(monkeypatch, tmp_path):
    from test_current_state import handoff
    values = {"a" * 40: handoff("v1"), "b" * 40: handoff("v2")}
    history = [{"source": {"path": "same.json", "ref": ref}, "registered_current": False} for ref in values]
    collector = delivery.Collector(API(), SHA, tmp_path)
    def source(spec):
        if spec["path"] == read.WORKFLOWS["inbox"]:
            raw = b"decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n"
        else:
            raw = values[spec["ref"]]
        return raw, {"path": spec["path"], "ref": spec.get("ref", SHA)}
    monkeypatch.setattr(collector, "source", source)
    result = collector.research({"references": [], "historical_handoffs": history})
    assert not result["gaps"] and not result["handoffs"]["gaps"]
    assert len(result["handoffs"]["background"]) == 2
    assert len({r["request_id"] for r in result["handoffs"]["background"]}) == 2
