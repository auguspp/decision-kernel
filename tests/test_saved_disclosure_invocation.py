"""Request-only Git events compose with the ORIGINAL host; no real provider calls."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import saved_disclosure_invocation as invocation

R, W = "a" * 40, "b" * 40
NOW = "2026-09-14T11:01:00+00:00"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*_):
        raise AssertionError("synthetic invocation tests may not connect")
    monkeypatch.setattr(socket.socket, "connect", refused)


@pytest.fixture
def case(tmp_path):
    def make(change=None, *, extra=False, symlink=False, duplicate=False, continuation=False):
        root = tmp_path / "repo"
        root.mkdir()
        def git(*args):
            return subprocess.run(["git", *args], cwd=root, check=True,
                                  capture_output=True, timeout=10).stdout
        git("init", "-q"); git("config", "user.email", "synthetic@example.invalid")
        git("config", "user.name", "Synthetic test")
        (root / "README.md").write_text("synthetic\n")
        old = root / invocation.CONTINUATION_PATH
        old.parent.mkdir(parents=True)
        old.write_bytes(b'{"synthetic":"not a permission"}')
        git("add", "."); git("commit", "-qm", "reviewed code")
        before = git("rev-parse", "HEAD").decode().strip()
        digest = read.sha256(old.read_bytes()) if continuation else None
        request = {"schema_version": 1, "profile": invocation.PROFILE,
                   "approved_parent": before, "source_run_id": 10,
                   "reading_commit": R, "work_commit": W,
                   "continuation_sha256": digest, "expires_at": "2026-09-14T12:00:00+00:00"}
        if change:
            change(request)
        name = "continue-" + digest if continuation else "scan-10"
        path = invocation.DIRECTORY + name + ".json"
        target = root / path
        target.parent.mkdir(parents=True)
        raw = read.json_bytes(request)
        if duplicate:
            raw = raw.replace(b'{', b'{"schema_version":1,', 1)
        if symlink:
            target.symlink_to("../../README.md")
        else:
            target.write_bytes(raw)
        if extra:
            (root / "extra.py").write_text("raise RuntimeError('must not execute')")
        git("add", "."); git("commit", "-qm", "explicit invocation only")
        head = git("rev-parse", "HEAD").decode().strip()
        env = {"GITHUB_REPOSITORY": read.REPOSITORY, "GITHUB_REF": "refs/heads/main",
               "GITHUB_EVENT_NAME": "push", "GITHUB_RUN_ATTEMPT": "1",
               "GITHUB_SHA": head, "SOURCE_BASE": before}
        reading = read.assemble(code_commit=before, checked_at="2026-09-14T11:00:00+00:00",
            check_started_at="2026-09-14T10:59:00+00:00", lanes={},
            research={"handoffs": {"active": []}}, capabilities=[], refresh_identity={})
        class API:
            refs = {"main": head, read.READ_REF: R, invocation.WORK_REF: W}
            history = []
            closed = False
            def _call(self, method, endpoint):
                assert method == "GET" and endpoint.startswith("git/ref/heads/")
                name = endpoint.removeprefix("git/ref/heads/")
                return SimpleNamespace(json=lambda: {"object": {"type": "commit", "sha": self.refs[name]}})
            def get(self, endpoint):
                assert endpoint.startswith("commits?sha=" + before + "&path=")
                return deepcopy(self.history)
            def file(self, name, ref):
                assert (name, ref) == ("current-state.json", R)
                return read.json_bytes(reading)
            def close(self):
                self.closed = True
        api = API(); api.refs = dict(api.refs); api.session = api
        return SimpleNamespace(root=root, git=git, env=env, api=api, reading=reading,
                               request=request, path=path, raw=raw, head=head, before=before)
    return make


def resolve(c):
    return invocation.resolve(api=c.api, env=c.env, git=c.git, checked_at=NOW)


@pytest.mark.parametrize("continuation", [False, True])
def test_request_only_commit_resolves_original_inputs_not_research(case, continuation):
    c = case(continuation=continuation)
    result = resolve(c)
    assert result["status"] == "REQUEST_CHECKED_NOT_RESEARCH"
    assert result["source_run_id"] == 10 and result["request_path"] == c.path
    assert result["request_git_blob"] == read.blob_sha(c.raw)
    assert result["reading_commit"] == R and result["work_commit"] == W
    assert result["continuation_sha256"] == c.request["continuation_sha256"]
    assert all(result[k] == v for k, v in read.AUTHORITY.items())
    assert result["automatic_retry"] is False


@pytest.mark.parametrize("key,value", [
    ("GITHUB_REPOSITORY", "other/repo"), ("GITHUB_REF", "refs/heads/test"),
    ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_RUN_ATTEMPT", "2"),
    ("SOURCE_BASE", "0" * 40), ("GITHUB_SHA", "c" * 40),
    ("SOURCE_BASE", "d" * 40)])
def test_non_main_retries_and_changed_commit_identity_fail(case, key, value):
    c = case(); c.env[key] = value
    with pytest.raises(ValueError):
        resolve(c)


@pytest.mark.parametrize("kwargs", [{"extra": True}, {"symlink": True}, {"duplicate": True}])
def test_mixed_changes_symlink_and_duplicate_json_are_not_activation(case, kwargs):
    with pytest.raises(ValueError):
        resolve(case(**kwargs))


@pytest.mark.parametrize("key,value", [
    ("source_run_id", True), ("source_run_id", 11), ("reading_commit", "main"),
    ("work_commit", "branch"), ("approved_parent", "c" * 40),
    ("profile", "dispatch anything"), ("schema_version", True),
    ("continuation_sha256", "e" * 64), ("extra", "arbitrary command"),
    ("expires_at", NOW), ("expires_at", "2026-09-17T12:00:00+00:00")])
def test_request_binding_and_clock_are_not_reinterpreted(case, key, value):
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        resolve(case(lambda r: r.update({key: value})))


@pytest.mark.parametrize("name", ["main", read.READ_REF, invocation.WORK_REF])
def test_moved_refs_fail_closed(case, name):
    c = case(); c.api.refs[name] = "f" * 40
    with pytest.raises(ValueError):
        resolve(c)


@pytest.mark.parametrize("history", [[{"sha": "c" * 40}], None])
def test_deleted_readded_request_or_unknown_history_is_rejected(case, history):
    c = case(); c.api.history = history
    with pytest.raises(ValueError):
        resolve(c)


def test_original_reading_hash_check_is_actually_used(case):
    c = case(); c.reading["reading_hash"] = "0" * 64
    with pytest.raises(ValueError):
        resolve(c)


def test_editing_existing_request_is_not_first_addition(case):
    c = case(); prior = c.head
    (c.root / c.path).write_text('{}')
    c.git("add", "."); c.git("commit", "-qm", "old request edit")
    c.env.update(SOURCE_BASE=prior, GITHUB_SHA=c.git("rev-parse", "HEAD").decode().strip())
    with pytest.raises(ValueError):
        resolve(c)


@pytest.mark.parametrize("bad", [False, True])
def test_cli_retains_separate_audit_and_exports_only_checked_arguments(case, tmp_path, monkeypatch, bad):
    from decision_kernel.runtime import current_state_delivery
    c = case(); monkeypatch.chdir(c.root)
    for key, value in c.env.items(): monkeypatch.setenv(key, value)
    monkeypatch.setenv("GH_TOKEN", "synthetic")
    monkeypatch.setattr(invocation, "datetime", SimpleNamespace(now=lambda _: read.clock(NOW)))
    output = tmp_path / "outputs"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(current_state_delivery, "GitHubAPI", lambda _: c.api)
    if bad: c.reading["reading_hash"] = "0" * 64
    audit = tmp_path / "invocation"
    assert invocation.main(["--output", str(audit)]) == (2 if bad else 0)
    result = json.loads((audit / "invocation.json").read_bytes())
    assert c.api.closed and not result["automatic_retry"]
    if bad:
        assert result["status"] == "INVOCATION_REJECTED_NOT_RESEARCH" and not output.exists()
    else:
        assert (audit / "request.json").read_bytes() == c.raw
        assert output.read_text().splitlines() == ["source_run_id=10", "continuation=false",
                                                  "reading_commit=" + R, "work_commit=" + W]


def test_workflow_reuses_same_host_job_and_publishes_push_completion():
    root = Path(__file__).parents[1]
    wf = (root / ".github/workflows/saved-disclosure-research.yml").read_text()
    pub = (root / ".github/workflows/current-state-read-entry.yml").read_text()
    assert "paths: [.github/saved-disclosure-invocations/*.json]" in wf
    assert "workflows: [decision-inbox]" in wf and "workflow_dispatch:" in wf
    assert "schedule:" not in wf and "cancel-in-progress: false" in wf
    assert wf.count("python -m decision_kernel.runtime.saved_disclosure_host") == 1
    validation = wf.split("      - name: Validate explicit first-addition")[1].split("      - name: Original FIFO")[0]
    assert "SUB2API" not in validation and "SOURCE_BASE: ${{ github.event.before }}" in validation
    assert '--expected-reading-commit "$EXPECTED_READING" --expected-work-commit "$EXPECTED_WORK"' in wf
    assert "run-output/invocation" in wf and "path: run-output/" in wf
    assert "github.event.workflow_run.name == 'saved-disclosure-research' &&\n          github.event.workflow_run.event == 'push'" in pub
    assert "SUB2API" not in pub


def test_original_host_accepts_bound_snapshot_and_preserves_repeat_noop(tmp_path, monkeypatch):
    from test_saved_disclosure_host import setup_host, READING, WORK, host, intake, work
    args, api, calls = setup_host(tmp_path, monkeypatch)
    result = host.consume(**args, expected_reading_commit=READING, expected_work_commit=WORK)
    assert result["status"] == "NO_UNRESERVED_PACKET_IN_SAVED_SCAN", result
    assert calls == ["pre", "pre"]
    current_work = intake.mutable_ref(api, work.WORK_REF)
    before = deepcopy(api.snapshots)
    result = host.consume(**dict(args, output=tmp_path / "repeat"),
                          expected_reading_commit=READING, expected_work_commit=current_work)
    assert result["items"] == [] and api.snapshots == before and calls == ["pre", "pre"]


@pytest.mark.parametrize("r,w", [(None, W), (R, None), ("c" * 40, W), (R, "d" * 40)])
def test_original_host_ref_recheck_rejects_before_any_new_work(tmp_path, monkeypatch, r, w):
    from test_saved_disclosure_host import setup_host, host
    args, api, calls = setup_host(tmp_path, monkeypatch)
    result = host.consume(**args, expected_reading_commit=r, expected_work_commit=w)
    assert result["status"] == "BATCH_INCOMPLETE" and calls == [] and api.writes == []


def test_original_host_rechecks_first_work_snapshot_after_preparation(tmp_path, monkeypatch):
    from test_saved_disclosure_host import setup_host, READING, WORK, host, work
    args, api, calls = setup_host(tmp_path, monkeypatch)
    original = api._call; reads = []
    def shifted(method, endpoint):
        if endpoint == "git/ref/heads/" + work.WORK_REF:
            reads.append(endpoint)
            if len(reads) > 1:
                return SimpleNamespace(json=lambda: {"object": {"type": "commit", "sha": ("d" * 40 if WORK != "d" * 40 else "e" * 40)}})
        return original(method, endpoint)
    monkeypatch.setattr(api, "_call", shifted)
    result = host.consume(**args, expected_reading_commit=READING, expected_work_commit=WORK)
    assert result["status"] == "BATCH_INCOMPLETE" and calls == [] and api.writes == []
    assert len(reads) == 2
