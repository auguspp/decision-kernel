"""Existing checkpoint re-entry: real validators, synthetic native Git/archive edges."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.runtime import industry_preparation_reentry as reentry
from decision_kernel.runtime import industry_question_preparation as prep
from decision_kernel.runtime import saved_research_once as once, reviewed_full_input as full
from test_industry_input_continuation import API as PriorAPI, Retainer, CODE, WORK, NOW
from test_reviewed_full_input import simple_context
from test_declared_report_input import setup_declared


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("context re-entry tests must be offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


class API(PriorAPI):
    def __init__(self):
        self.building_prior = True
        super().__init__()
        self.building_prior = False
        previous = deepcopy(self.plan)
        self.plan = json.loads(Path(prep.REQUEST).read_bytes())
        self.resume = self.plan["resume_from"]
        self.prefix = prep.PREFIX + self.plan["id"] + "/"
        self.context = full.pack(once.raw(simple_context(1000)), ticker="600362")
        self.cs = once.source_ref(self.prefix + "context.json", "c" * 40, self.context, "MODEL_CONTEXT")
        continuation = {"plan": previous, "code_commit": self.resume["run"]["head_sha"],
            "run_id": str(self.resume["run"]["id"]), "event": "issues", "automatic_retry": False,
            "started_at": "2026-09-23T01:54:12Z", "proof": {"parent": previous["resume_from"]}, **prep.reading.AUTHORITY}
        self.continuation = once.raw(continuation)
        self.conts = once.source_ref(self.prefix + "continuation.json", "d" * 40,
                                    self.continuation, "EXPLICIT_INPUT_PREPARATION_CONTINUATION")
        self.resume.update(context_source=self.cs, continuation_source=self.conts)
        self.run = {**self.resume["run"], "status": "completed", "conclusion": "failure", "run_attempt": 1,
            "repository": {"full_name": once.REPO}, "head_repository": {"full_name": once.REPO},
            "run_started_at": "2026-09-23T01:53:56Z", "updated_at": "2026-09-23T01:54:50Z"}
        self.files[self.run["head_sha"]] = {prep.REQUEST: once.raw(previous)}
        for spec, data in ((self.cs, self.context), (self.conts, self.continuation)):
            self.files[spec["ref"]] = {spec["path"]: data}
            self.files[WORK][spec["path"]] = data
        failure = json.loads((Path(__file__).parent / "fixtures/industry-origin-size-failure-receipt.json").read_bytes())
        failure.update(continuation_source=self.conts, context_bytes=len(full.unpack(self.context, ticker="600362")),
                       stored_context_bytes=len(self.context))
        self.receipt = once.raw(failure)
        self.reseal()

    def reseal(self):
        if getattr(self, "building_prior", False):
            return super().reseal()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name, raw in {"context.json": self.context, "continuation.json": self.continuation,
                              "preparation-receipt.json": self.receipt, **self.member_extra}.items():
                z.writestr(name, raw)
        self.zip = buf.getvalue()
        self.resume["artifact"].update(size_in_bytes=len(self.zip), digest="sha256:" + once.sha(self.zip))
        self.resume["receipt_sha256"] = once.sha(self.receipt)
        self.artifact = {**self.resume["artifact"], "expired": False,
            "workflow_run": {"id": self.run["id"], "head_sha": self.run["head_sha"]}}
        self.files[CODE][prep.REQUEST] = once.raw(self.plan)

    def get(self, path):
        for spec, when in ((self.conts, "2026-09-23T01:54:13Z"), (self.cs, "2026-09-23T01:54:45Z")):
            if path == "git/commits/" + spec["ref"]:
                return {"sha": spec["ref"], "committer": {"date": when}}
        return super().get(path)


def test_exact_checkpoint_proof_preserves_context_and_prior_markers():
    api = API()
    proof = prep.check_continuation(api, api.plan, WORK, api.rows(), lambda: NOW)
    assert proof["parent"]["context_source"] == api.cs
    assert proof["failure_receipt"]["error_code"] == "INDUSTRY_REPORT_SIZE"
    assert api.writes == []


@pytest.mark.parametrize("damage", ["context", "continuation", "plan", "later", "missing", "queried", "model",
    "uncertain", "other-error", "decoded-size", "clock", "expired", "zip", "extra-member"])
def test_invalid_checkpoint_or_uncertain_prior_work_never_allows_reentry(damage):
    api = API()
    failure = json.loads(api.receipt)
    if damage == "queried": failure["query_events"] = [{"status": "SUCCEEDED"}]
    elif damage == "model": failure["model_calls"] = 1
    elif damage == "uncertain": failure["mutation_uncertain"] = True
    elif damage == "other-error": failure["error_code"] = "OTHER_ERROR"
    elif damage == "decoded-size": failure["context_bytes"] += 1
    elif damage == "clock": failure["finished_at"] = "2026-09-23T01:54:11Z"
    api.receipt = once.raw(failure)
    if damage == "extra-member": api.member_extra["question.json"] = b"{}"
    api.reseal()
    if damage == "context": api.files[WORK][api.cs["path"]] += b" "
    elif damage == "continuation": api.files[WORK][api.conts["path"]] += b" "
    elif damage == "plan": api.plan["question"]["question_id"] = "another-question"
    elif damage == "later": api.files[WORK][api.prefix + "question.json"] = b"{}"
    elif damage == "missing": del api.files[WORK][api.cs["path"]]
    elif damage == "expired": api.artifact["expired"] = True
    elif damage == "zip": api.zip += b"corrupt"
    with pytest.raises((ValueError, KeyError)):
        prep.check_continuation(api, api.plan, WORK, api.rows(), lambda: NOW)
    assert api.writes == []


def test_run_appends_new_marker_and_never_replaces_old_context_or_repeats(tmp_path, monkeypatch):
    api = API()
    before = deepcopy(api.files[WORK])
    def reached(*args, **kwargs): raise once.TrialError("SYNTHETIC_STOP_BEFORE_ADOPTION")
    monkeypatch.setattr(prep.adopted, "load", reached)
    result = prep.run(api=api, code=CODE, output=tmp_path / "first", clock=lambda: NOW, retainer_factory=Retainer)
    assert result["error_code"] == "SYNTHETIC_STOP_BEFORE_ADOPTION", result
    assert [p for p, _ in api.writes] == [api.prefix + reentry.MARKER]
    saved = api.files[api.heads[prep.WORK_REF]]
    assert all(saved[p] == raw for p, raw in before.items())
    again = prep.run(api=api, code=CODE, output=tmp_path / "again", clock=lambda: NOW, retainer_factory=Retainer)
    assert again["status"] == "EXISTING_PREPARATION_NOT_REPEATED" and len(api.writes) == 1


def test_uncertain_new_marker_stops_before_adoption(tmp_path, monkeypatch):
    api = API()
    class Uncertain(Retainer):
        def native(self, *args):
            self.uncertain = True
            raise once.TrialError("SYNTHETIC_UNCERTAIN")
    def forbidden(*args): raise AssertionError("adoption forbidden")
    monkeypatch.setattr(prep.adopted, "load", forbidden)
    result = prep.run(api=api, code=CODE, output=tmp_path / "uncertain", clock=lambda: NOW, retainer_factory=Uncertain)
    assert result["error_code"] == "SYNTHETIC_UNCERTAIN" and result["mutation_uncertain"] is True
    assert api.writes == []


@pytest.mark.parametrize("damage", [None, "title", "document", "hash"])
def test_reuse_context_rebuilds_original_custody_without_repacking_or_reading_new_pdf(tmp_path, monkeypatch, damage):
    c = setup_declared(tmp_path, monkeypatch, image=True)
    _, _, records = prep.adopted.project(c.profile, c.declared_files)
    doc = c.context["issuer_documents"][0]
    plan = {"titles": {"2026H1": doc["title"]}, "resume_from": {"context_source": c.request["context_source"]}}
    if damage == "title": plan["titles"]["2026H1"] = "wrong"
    elif damage == "document": records = []
    elif damage == "hash": records[0]["route"]["pdf_sha256"] = "0" * 64
    def forbidden(*args, **kwargs): raise AssertionError("existing context must not be repacked")
    monkeypatch.setattr(full, "pack", forbidden)
    if damage:
        with pytest.raises(ValueError):
            reentry.retained_context(c.api, plan, c.profile, records, c.args["clock"])
    else:
        context, custody, spec, bound = reentry.retained_context(c.api, plan, c.profile, records, c.args["clock"])
        assert context == c.context and custody == c.custody["documents"] and spec == c.request["context_source"]
        assert bound.stored_raw == c.api.file(spec["path"], spec["ref"])
    assert c.calls == [] and c.writes == []
