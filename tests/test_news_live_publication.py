"""Exact News live ref is a derived delivery cache, not another source or Research lane."""
import base64
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import news_daily as source
from decision_kernel.runtime import news_live_publication as live
from test_news_daily import captured, IDENTITY, IMAGE, TIME


class API:
    def __init__(self, prior=None):
        self.ref = prior
        self.writes = []
        self.blobs = {}
        self.files = {}

    def get(self, endpoint):
        if endpoint == "git/matching-refs/heads/" + live.REF:
            return [] if self.ref is None else [{"ref": "refs/heads/" + live.REF,
                                                  "object": {"sha": self.ref}}]
        raise KeyError(endpoint)

    def fresh_get(self, endpoint):
        return deepcopy(self.get(endpoint))

    def write(self, endpoint, body, method="POST"):
        self.writes.append((endpoint, deepcopy(body), method))
        if endpoint == "git/blobs":
            raw = base64.b64decode(body["content"])
            sha = m.blob_sha(raw); self.blobs[sha] = raw
            return {"sha": sha}
        if endpoint == "git/trees":
            return {"sha": "b" * 40}
        if endpoint == "git/commits":
            return {"sha": "c" * 40}
        if endpoint == "git/refs":
            self.ref = body["sha"]; return {"ref": body["ref"]}
        if endpoint == "git/refs/heads/" + live.REF:
            assert body["force"] is True
            self.ref = body["sha"]; return {"ref": "refs/heads/" + live.REF}
        raise AssertionError(endpoint)

    def file(self, path, ref):
        if ref == "c" * 40:
            if path == live.MANIFEST:
                raw = next(v for v in self.blobs.values()
                           if json.loads(v).get("projection", {}).get("entry_ref") == live.REF)
                return raw
            if path == live.HISTORY:
                return next(v for v in self.blobs.values()
                            if json.loads(v).get("projection", {}).get("version") == source.HISTORY_VERSION)
        return self.files[(ref, path)]


def make(tmp_path, *, run_id=901, when=TIME):
    identity = {**IDENTITY, "run_id": run_id}
    root, files, current = captured(tmp_path, clock=lambda: when, identity=identity)
    report, history = live.build(files, published_at="2026-09-20T04:01:00+00:00")
    return files, current, report, history


def test_live_manifest_replays_exact_current_and_history(tmp_path):
    files, current, report, history = make(tmp_path)
    p = live.validate(report, json.loads(history))["projection"]
    assert p["capture_hash"] == current["projection"]["capture_hash"]
    assert p["source_run"]["run_id"] == 901
    assert p["rolling"]["coverage"]["observation_count"] == 7
    assert p["complete_news_coverage"] is False
    assert p["research_authority"] == p["investment_authority"] == "NONE"
    assert p["history"]["sha256"] == m.sha256(history)
    assert files[live.HISTORY] == history


def test_live_publication_is_latest_only_orphan_and_force_is_ref_scoped(tmp_path):
    _, _, report, history = make(tmp_path)
    api = API()
    commit = live.publish(api, report, history)
    assert commit == api.ref == "c" * 40
    body = next(body for endpoint, body, _ in api.writes if endpoint == "git/commits")
    tree = next(body for endpoint, body, _ in api.writes if endpoint == "git/trees")
    assert body["parents"] == [] and "base_tree" not in tree
    assert api.writes[-1][0] == "git/refs"
    # A later capture replaces only the dedicated ephemeral pointer.
    prior = "d" * 40
    api = API(prior)
    prior_report = deepcopy(report)
    prior_report["projection"]["captured_through"] = "2026-09-20T03:59:00+00:00"
    api.files[(prior, live.MANIFEST)] = m.json_bytes(prior_report)
    live.publish(api, report, history)
    assert api.writes[-1] == ("git/refs/heads/" + live.REF,
                              {"sha": "c" * 40, "force": True}, "PATCH")


def test_live_rejects_history_or_host_identity_tamper(tmp_path):
    files, _, report, history = make(tmp_path)
    bad = json.loads(history); bad["projection_hash"] = "0" * 64
    with pytest.raises(ValueError):
        live.validate(report, bad)
    bad_files = dict(files); bad_files[live.HISTORY] += b" "
    with pytest.raises(ValueError):
        live.build(bad_files, published_at="2026-09-20T04:01:00+00:00")


def test_live_write_scope_is_explicit_without_changing_current_state_transport(monkeypatch):
    default = delivery.GitHubAPI("synthetic")
    assert not hasattr(default, "write_ref") and not hasattr(default, "allow_force")
    api = live.NewsLiveGitHubAPI("synthetic", max_calls=10)

    class Response:
        status_code = 200
        content = b'{}'
        def json(self): return {}
    calls = []
    def request(method, url, json=None, **kwargs):
        calls.append((method, url, json)); return Response()
    monkeypatch.setattr(api.session, "request", request)

    api.write("git/refs/heads/" + live.REF, {"sha": "c" * 40, "force": True}, "PATCH")
    assert calls[-1][0] == "PATCH"
    with pytest.raises(ValueError, match="outside News live"):
        api.write("git/refs/heads/" + m.READ_REF, {"sha": "c" * 40, "force": True}, "PATCH")
    with pytest.raises(ValueError, match="exact force"):
        api.write("git/refs/heads/" + live.REF, {"sha": "c" * 40, "force": False}, "PATCH")


def test_workflow_publishes_live_ref_without_fanning_out_full_current_state():
    text = open(source.WORKFLOW, encoding="utf-8").read()
    assert "contents: write" in text
    assert "decision_kernel.runtime.news_live_publication" in text
    assert "--capture-dir" in text
    assert "read-model/news-live" not in text  # ref ownership stays in trusted module, not YAML input
    current = open(".github/workflows/current-state-read-entry.yml", encoding="utf-8").read()
    assert "github.event.workflow_run.event == 'schedule'" not in current.split("radar-newsnow-daily",1)[1].split("radar-industry-breadth",1)[0]
