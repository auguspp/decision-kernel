"""One pre-I/O failure resumes by appending; original markers never disappear."""
import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
from types import SimpleNamespace
import zipfile

import pytest

from decision_kernel.runtime import industry_question_preparation as prep
from decision_kernel.runtime import saved_research_once as once, current_state as reading
from decision_kernel.runtime import stock_retained_source_import as imports
from decision_kernel.runtime import stock_daily_question as daily

FIXTURES = Path(__file__).parent / "fixtures"
NOW = "2026-09-23T02:00:00Z"
CODE, WORK = "a" * 40, "b" * 40


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("continuation tests cannot use network")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


class API:
    """Synthetic Git edge using the real failure bytes, not a live-run claim."""
    def __init__(self):
        self.plan = json.loads(Path(prep.REQUEST).read_bytes())
        self.resume = self.plan["resume_from"]
        self.prepared = (FIXTURES / "industry-input-failure-20260923-prepare.json").read_bytes()
        self.receipt = (FIXTURES / "industry-input-failure-20260923-receipt.json").read_bytes()
        self.source = self.resume["prepare_source"]
        self.run = {**self.resume["run"], "status": "completed", "conclusion": "failure", "run_attempt": 1,
            "repository": {"full_name": once.REPO}, "head_repository": {"full_name": once.REPO},
            "run_started_at": "2026-09-23T01:11:42Z", "updated_at": "2026-09-23T01:12:00Z"}
        self.files = {CODE: {prep.REQUEST: once.raw(self.plan), imports.IMPORTS_PATH: once.raw({"imports": {
            self.plan["profile"]: {"case_id": "600362.SH", "run": {"id": 1}, "artifact": {}}}})},
            WORK: {self.source["path"]: self.prepared},
            self.source["ref"]: {self.source["path"]: self.prepared},
            self.run["head_sha"]: {prep.REQUEST: once.raw(json.loads(self.prepared)["plan"])}}
        self.heads = {"main": CODE, prep.WORK_REF: WORK}
        permission = (FIXTURES / "industry_daily_question_permission.txt").read_text().removesuffix("\n")
        p = self.plan["permission"]
        self.comment = {"id": p["comment_id"], "body": permission, "created_at": p["created_at"],
            "issue_url": "https://api.github.com/repos/" + once.REPO + "/issues/297"}
        self.archive_calls, self.writes, self.member_extra = [], [], {}
        self.reseal()

    def reseal(self):
        # ZIP metadata/digest below are synthetic because the archive is rebuilt.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("prepare.json", self.prepared)
            z.writestr("preparation-receipt.json", self.receipt)
            for name, data in self.member_extra.items(): z.writestr(name, data)
        self.zip = buf.getvalue()
        self.resume["artifact"].update(size_in_bytes=len(self.zip), digest="sha256:" + once.sha(self.zip))
        self.resume["receipt_sha256"] = once.sha(self.receipt)
        self.artifact = {**self.resume["artifact"], "expired": False,
            "workflow_run": {"id": self.run["id"], "head_sha": self.run["head_sha"]}}
        self.files[CODE][prep.REQUEST] = once.raw(self.plan)

    def file(self, path, ref): return self.files[ref][path]

    def rows(self):
        return {p: {"path": p, "type": "blob", "mode": "100644", "size": len(b), "sha": once.blob(b)}
                for p, b in self.files[self.heads[prep.WORK_REF]].items()}

    def get(self, path):
        if path == "actions/runs/" + str(self.run["id"]): return deepcopy(self.run)
        if path == f"actions/runs/{self.run['id']}/artifacts?per_page=100":
            return {"total_count": 1, "artifacts": [deepcopy(self.artifact)]}
        if path == "git/commits/" + self.source["ref"]:
            return {"sha": self.source["ref"], "committer": {"date": "2026-09-23T01:11:56Z"}}
        if path == "git/trees/" + self.heads[prep.WORK_REF] + "?recursive=1":
            return {"truncated": False, "tree": list(self.rows().values())}
        raise AssertionError("unexpected GET " + path)

    def archive(self, artifact):
        self.archive_calls.append(artifact["id"])
        return self.zip

    def _call(self, method, path):
        assert method == "GET"
        if path.startswith("git/ref/heads/"):
            value = {"object": {"type": "commit", "sha": self.heads[path.removeprefix("git/ref/heads/")]}}
        elif path == "issues/comments/" + str(self.comment["id"]): value = self.comment
        else: raise AssertionError("unexpected native GET " + path)
        return SimpleNamespace(json=lambda: deepcopy(value))


class Retainer(once.Retainer):
    def native(self, method, endpoint, body):
        # Only native Git mutation is replaced. Original serializer/readback stays.
        assert method == "PUT" and endpoint.startswith("contents/") and "sha" not in body
        assert body["branch"] == prep.WORK_REF
        assert not self.uncertain
        self.uncertain = True
        path = endpoint.removeprefix("contents/")
        current = self.api.heads[prep.WORK_REF]
        assert path not in self.api.files[current], "create-only conflict"
        data = base64.b64decode(body["content"], validate=True)
        new = f"{len(self.api.writes) + 1:040x}"
        self.api.files[new] = {**self.api.files[current], path: data}
        self.api.heads[prep.WORK_REF] = new
        self.api.writes.append((path, data))
        self.uncertain = False
        return {"commit": {"sha": new}, "content": {"sha": once.blob(data)}}


def test_exact_zero_io_failure_is_readable_but_not_a_successful_source():
    api = API()
    with pytest.raises(ValueError, match="DAILY_IMPORT_RUN_IDENTITY"):
        imports._archive(api, api.resume, {})
    assert api.archive_calls == []
    proof = prep.check_continuation(api, api.plan, WORK, api.rows(), lambda: NOW)
    assert proof["failure_receipt"]["query_events"] == []
    assert proof["parent"]["prepare_source"]["git_blob"] == "8706b856680a7ac786f98d375c9871f4019c1337"
    assert api.writes == [] and api.archive_calls == [api.artifact["id"]]


@pytest.mark.parametrize("damage", ["queried", "model", "pdf", "research", "uncertain", "other-error",
    "success", "attempt2", "foreign", "expired", "zip-changed", "extra-member", "plan-change",
    "array-order", "current-prepare", "later-output", "missing-prepare", "clock", "authority", "missing-counter"])
def test_unsafe_or_different_failure_is_not_continuable(damage):
    api = API()
    failed = json.loads(api.receipt)
    if damage == "queried": failed["query_events"] = [{"status": "FAILED"}]
    elif damage == "model": failed["model_calls"] = 1
    elif damage == "pdf": failed["pdf_acquisitions"] = 1
    elif damage == "research": failed["research_executions"] = 1
    elif damage == "uncertain": failed["mutation_uncertain"] = True
    elif damage == "other-error": failed["error_code"] = "INDUSTRY_REPORT_CORRECTION_BODY_REVIEW_REQUIRED"
    elif damage == "clock": failed["finished_at"] = "2026-09-23T03:00:00Z"
    elif damage == "authority": failed["research_authority"] = "GRANTED"
    elif damage == "missing-counter": del failed["model_calls"]
    api.receipt = once.raw(failed)
    if damage == "extra-member": api.member_extra["context.json"] = b"{}"
    api.reseal()
    if damage == "success": api.run["conclusion"] = "success"
    elif damage == "attempt2": api.run["run_attempt"] = 2
    elif damage == "foreign": api.run["repository"]["full_name"] = "foreign/repo"
    elif damage == "expired": api.artifact["expired"] = True
    elif damage == "zip-changed": api.zip += b"changed"
    elif damage == "plan-change": api.plan["question"]["question_id"] = "different-root"
    elif damage == "array-order": api.plan["question"]["known_unknowns"].reverse()
    elif damage == "current-prepare": api.files[WORK][api.source["path"]] += b" "
    elif damage == "later-output": api.files[WORK][api.source["path"].replace("prepare.json", "context.json")] = b"{}"
    elif damage == "missing-prepare": del api.files[WORK][api.source["path"]]
    with pytest.raises((ValueError, KeyError)):
        prep.check_continuation(api, api.plan, WORK, api.rows(), lambda: NOW)
    assert api.writes == []


def test_original_run_appends_marker_before_adoption_and_second_signal_does_not_repeat(tmp_path, monkeypatch):
    api = API()
    original = deepcopy(api.files[WORK])
    handoffs = []
    def reached(*args, **kwargs):
        handoffs.append(1)
        raise once.TrialError("TEST_STOP_AT_ORIGINAL_ADOPTION")
    monkeypatch.setattr(prep.adopted, "load", reached)
    monkeypatch.setenv("GITHUB_RUN_ID", "999")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    def no_fetch(**kwargs): raise AssertionError("no directory query before full adoption")
    result = prep.run(api=api, code=CODE, output=tmp_path / "first", clock=lambda: NOW,
                      fetch=no_fetch, retainer_factory=Retainer)
    assert result["error_code"] == "TEST_STOP_AT_ORIGINAL_ADOPTION", result
    assert result["mutation_uncertain"] is False and result["model_calls"] == 0
    assert handoffs == [1] and len(api.writes) == 1
    path, data = api.writes[0]
    assert path == api.source["path"].replace("prepare.json", "continuation.json")
    marker = json.loads(data)
    assert marker["proof"]["failure_receipt"] == json.loads(api.receipt)
    assert marker["automatic_retry"] is False and marker["investment_authority"] == "NONE"
    assert api.files[api.heads[prep.WORK_REF]][api.source["path"]] == original[api.source["path"]]
    result2 = prep.run(api=api, code=CODE, output=tmp_path / "second", clock=lambda: NOW,
                       fetch=no_fetch, retainer_factory=Retainer)
    assert result2["status"] == "EXISTING_PREPARATION_NOT_REPEATED"
    assert handoffs == [1] and len(api.writes) == 1


def test_without_explicit_continuation_existing_prepare_still_stops(tmp_path):
    api = API()
    api.plan.pop("resume_from")
    api.files[CODE][prep.REQUEST] = once.raw(api.plan)
    result = prep.run(api=api, code=CODE, output=tmp_path / "plain", clock=lambda: NOW,
                      retainer_factory=Retainer)
    assert result["status"] == "EXISTING_PREPARATION_NOT_REPEATED"
    assert api.writes == [] and api.archive_calls == []


def test_uncertain_continuation_write_never_reaches_adoption(tmp_path, monkeypatch):
    api = API()
    class Uncertain(Retainer):
        def native(self, *args):
            self.uncertain = True
            raise once.TrialError("TEST_UNCERTAIN_WRITE")
    def forbidden(*args, **kwargs): raise AssertionError("adoption after uncertain write")
    monkeypatch.setattr(prep.adopted, "load", forbidden)
    result = prep.run(api=api, code=CODE, output=tmp_path / "uncertain", clock=lambda: NOW,
                      retainer_factory=Uncertain)
    assert result["error_code"] == "TEST_UNCERTAIN_WRITE", result
    assert result["mutation_uncertain"] is True and api.writes == []
