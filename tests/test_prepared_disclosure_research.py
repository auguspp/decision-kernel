"""Synthetic prepared inputs through original admission/Funnel; all sockets denied."""
from __future__ import annotations

import copy
import json
import socket
from types import SimpleNamespace

import pytest

import test_external_research_admission as admission_fixture
import test_external_research_execution as execution_fixture
import test_incremental_disclosure as disclosure_fixture
from test_saved_research_once import pre, quick
from decision_kernel.research_funnel import DiscoveryInput
from decision_kernel.runtime import prepared_disclosure_research as prepared
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime.current_state_delivery import GitHubReadError
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("NETWORK IS NOT ALLOWED IN THIS SYNTHETIC TEST")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


class Case:
    def __init__(self, monkeypatch, code="600036"):
        p, self.pf, self.catalogue, self.values, self.commits = admission_fixture.setup()
        self.code = "d" * 40
        self.reserved = disclosure_fixture.packet(code=code, prepared="2026-09-08T08:30:00Z")
        saved = prepared.work._packet(self.reserved)
        self.prefix = prepared.work.request_path(saved.assessment_input_hash).removesuffix("packet.json")
        self.context = {"disclosure_packet": json.loads(self.reserved),
                        "source_limitations": ["Synthetic saved body, not live company Research."]}
        self.context_source = once.source_ref(self.prefix+"source.json", "e"*40,
                                             once.raw(self.context), "MODEL_CONTEXT")
        seed = p["seed_evidence_artifacts"][0]
        seed.update(content_hash=self.context_source["sha256"], source_locator=once.locator(self.context_source))
        p.update(ticker=code, case_id=code+".SH", security_id="SSE:"+code,
                 source_lane="CNINFO_INCREMENTAL", candidate_output_prefix=self.prefix,
                 execution_id="synthetic-prepared-disclosure-"+code, allowed_tools=["OTHER_READ"])
        p["budget"].update(max_tool_calls=6, max_search_queries=0, max_source_reads=4,
                           max_technical_retries=0, max_elapsed_minutes=15)
        self.pf.update(**{k:p[k] for k in ("case_id", "ticker", "security_id")})
        self.pf["seed_publications"][0]["source"] = self.context_source
        self.packet = p
        self.heads = {"main": self.code, prepared.work.WORK_REF: "c"*40}
        self.reads, self.writes, self.calls = [], [], []
        self.time = "2026-09-08T11:02:01Z"
        self.lost_write = self.corrupt_read = self.change_after_launch = None
        self.pre_route, self.quick_route, self.provider_failure = "WAIT_FOR_TRIGGER", "WAIT_FOR_TRIGGER", None
        self.extra_refs = []
        monkeypatch.setattr(once.Retainer, "native", lambda retainer, method, endpoint, body:
                            self.native(retainer, method, endpoint, body))
        self.bind()

    def bind(self):
        pf_source = once.source_ref("preflight.json", "f"*40, once.raw(self.pf), once.admission.PREFLIGHT_PURPOSE)
        reserved_source = once.source_ref(self.prefix+"packet.json", "b"*40, self.reserved,
                                          prepared.work.PACKET_PURPOSE)
        p = copy.deepcopy(self.packet)
        p["source_refs"] = [self.context_source, pf_source, reserved_source, *self.extra_refs]
        self.discovery = execution_fixture.discovery(ExternalResearchInputPacket.model_validate(p))
        discovery_source = once.source_ref(self.prefix+"discovery.json", "a"*40,
                                           once.raw(self.discovery), prepared.DISCOVERY_PURPOSE)
        p["source_refs"].append(discovery_source)
        self.parsed = ExternalResearchInputPacket.model_validate(p)
        self.input_source = once.source_ref(self.prefix+"input.json", "c"*40, once.raw(self.parsed), "INPUT")
        self.values.update({("e"*40,self.context_source["path"]):once.raw(self.context),
            ("f"*40,pf_source["path"]):once.raw(self.pf),
            ("b"*40,reserved_source["path"]):self.reserved,
            ("c"*40,reserved_source["path"]):self.reserved,
            ("a"*40,discovery_source["path"]):once.raw(self.discovery),
            ("c"*40,self.input_source["path"]):once.raw(self.parsed),
            (self.code,once.identity.CATALOG_PATH):once.raw(self.catalogue)})
        self.commits["a"*40] = {"sha":"a"*40, "committer":{"date":"2026-09-08T10:54:00Z"}}
        self.expected = once.identity.input_key(self.parsed).as_dict()
        self.egress = prepared.public_egress_hash(self.parsed, self.discovery, self.context)

    def _call(self, method, endpoint):
        assert method == "GET"
        self.reads.append(endpoint)
        return SimpleNamespace(json=lambda:{"object":{"sha":self.heads[endpoint.removeprefix("git/ref/heads/")]}})

    def file(self, path, ref):
        self.reads.append((ref,path))
        if self.corrupt_read and path.endswith(self.corrupt_read) and any(w["path"] == path for w in self.writes):
            return b"corrupt saved output"
        try:
            return self.values[ref,path]
        except KeyError:
            raise GitHubReadError("GitHub HTTP 404")

    def get(self, endpoint):
        self.reads.append(endpoint)
        return self.commits[endpoint.removeprefix("git/commits/")]

    def native(self, retainer, method, endpoint, body):
        assert method == "PUT" and endpoint.startswith("contents/")
        assert "sha" not in body and body["branch"] == prepared.work.WORK_REF
        path = endpoint.removeprefix("contents/")
        assert path.startswith(self.prefix)
        retainer.uncertain = True
        head = self.heads[prepared.work.WORK_REF]
        if (head,path) in self.values:
            raise ValueError("existing marker, no retry")
        raw = once.base64.b64decode(body["content"])
        new = f"{1000+len(self.writes):040x}"
        self.values.update({(new,p):v for (r,p),v in list(self.values.items()) if r == head})
        self.values[new,path] = raw
        self.heads[prepared.work.WORK_REF] = new
        self.writes.append({"path":path,"raw":raw,"ref":new})
        if path.endswith("launch.json"):
            if self.change_after_launch == "main": self.heads["main"] = "0"*40
            if self.change_after_launch == "expiry": self.time = "2026-09-08T12:01:00Z"
        if self.lost_write and path.endswith(self.lost_write):
            raise RuntimeError("PRIVATE_PROVIDER_OR_TOKEN_TEXT_MUST_NOT_BE_ECHOED")
        retainer.uncertain = False
        return {"commit":{"sha":new},"content":{"sha":once.blob(raw)}}

    def model(self, stage, prompt, model, out, usage):
        self.calls.append((stage,prompt))
        if stage == self.provider_failure:
            raise RuntimeError("PRIVATE_PROVIDER_OR_TOKEN_TEXT_MUST_NOT_BE_ECHOED")
        return pre(prompt,self.pre_route) if stage == "pre" else quick(prompt,self.quick_route)

    def run(self, output):
        return prepared.run_prepared(api=self,code_commit=self.code,input_source=self.input_source,
            expected_key=self.expected,approved_egress_hash=self.egress,output=output,
            clock=lambda:self.time,call=self.model)


@pytest.mark.parametrize("code", ["600036", "603986", "002050"])
@pytest.mark.parametrize("route", ["WAIT_FOR_TRIGGER", "STOP", "DEEPEN"])
def test_reuses_original_loop_and_retention_across_issuers(tmp_path, monkeypatch, code, route):
    c = Case(monkeypatch,code)
    c.pre_route, c.quick_route = "CONTINUE_TO_QUICK", route
    before = copy.deepcopy(c.values)
    result = c.run(tmp_path/"first")
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert [s for s,_ in c.calls] == ["pre","quick"]
    candidate = once.identity._json((tmp_path/"first/candidate.json").read_bytes())
    assert candidate["discovery"]["ticker"] == code
    assert candidate["receipt"]["technical_retries_used"] == 0
    assert result["semantic_acceptance"] == "NOT_ESTABLISHED" and not result["current_state_published"]
    assert result["investment_authority"] == "NONE"
    assert all(c.values[k] == v for k,v in before.items())
    writes = len(c.writes)
    again = c.run(tmp_path/"second")
    assert again["status"] == "ALREADY_LAUNCHED_NO_EXECUTION"
    assert len(c.writes) == writes and len(c.calls) == 2


def test_pre_wait_does_not_call_quick_and_keeps_discovery_id_distinct(tmp_path, monkeypatch):
    c=Case(monkeypatch); result=c.run(tmp_path/"run")
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert len(c.calls)==1 and c.discovery.discovery_id != c.parsed.execution_id


@pytest.mark.parametrize("damage", ["egress", "scope", "budget", "input", "context", "seed", "discovery-clock"])
def test_unsupported_or_changed_input_never_spends(tmp_path, monkeypatch, damage):
    c=Case(monkeypatch)
    if damage=="egress": c.egress="0"*64
    if damage=="scope": c.packet["source_lane"]="SECTOR_SAVED_MEMBER_READING"; c.bind()
    if damage=="budget": c.packet["budget"]["max_search_queries"]=1; c.bind()
    if damage=="input": c.input_source["git_blob"]="0"*40
    if damage=="context": c.values["e"*40,c.context_source["path"]]=b'{"unapproved":true}'
    if damage=="seed":
        c.packet["seed_evidence_artifacts"][0]["content_hash"]="0"*64; c.bind()
    if damage=="discovery-clock": c.commits["a"*40]["committer"]["date"]="2026-09-08T11:03:00Z"
    result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and not c.calls and not c.writes


@pytest.mark.parametrize("damage", ["shell", "expiry", "missing-class", "wrong-input-clock"])
def test_original_admission_rejection_is_not_wait(tmp_path, monkeypatch, damage):
    c=Case(monkeypatch)
    if damage=="shell": c.pf["reads"][0]["kind"]="SHELL"
    if damage=="expiry": c.pf["valid_until"]="2026-09-08T11:00:00Z"
    if damage=="missing-class": c.pf["required_classes"]=c.pf["required_classes"][1:]
    if damage=="wrong-input-clock": c.commits["c"*40]["committer"]["date"]="2026-09-08T10:59:00Z"
    c.bind(); result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and result.get("reason") and not c.calls and not c.writes
    assert not (tmp_path/"run/funnel.json").exists()


@pytest.mark.parametrize("change", ["main", "expiry"])
def test_fresh_admission_after_marker_prevents_late_launch(tmp_path, monkeypatch, change):
    c=Case(monkeypatch); c.change_after_launch=change
    result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and not c.calls and c.writes
    assert not result["formal_research_started"] and (tmp_path/"run/launch.json").exists()


@pytest.mark.parametrize("stage", ["pre", "quick"])
def test_provider_failure_retains_gap_no_retry_no_funnel(tmp_path, monkeypatch, stage):
    c=Case(monkeypatch); c.pre_route="CONTINUE_TO_QUICK"; c.provider_failure=stage
    result=c.run(tmp_path/"run")
    assert result["status"]=="EXECUTION_GAP", result
    assert len(c.calls)==(1 if stage=="pre" else 2)
    assert (tmp_path/"run/candidate-before-validation.json").exists()
    assert not (tmp_path/"run/funnel.json").exists()
    assert "PRIVATE_PROVIDER_OR_TOKEN_TEXT" not in (tmp_path/"run/host-receipt.json").read_text()


@pytest.mark.parametrize("name", ["launch.json", "candidate.json", "host-receipt.json"])
def test_uncertain_writes_never_compensate_or_launch_again(tmp_path, monkeypatch, name):
    c=Case(monkeypatch); c.lost_write=name
    result=c.run(tmp_path/"run")
    assert result["mutation_uncertain"]
    assert c.writes[-1]["path"].endswith(name)
    assert len(c.calls)==(0 if name=="launch.json" else 1)
    count=len(c.writes); c.lost_write=None
    again=c.run(tmp_path/"again")
    assert again["status"]=="ALREADY_LAUNCHED_NO_EXECUTION" and len(c.writes)==count


def test_private_authorization_source_is_never_model_context(tmp_path, monkeypatch):
    c=Case(monkeypatch)
    private=b'PRIVATE_HUMAN_PERMISSION_NOT_MODEL_CONTEXT'
    source=once.source_ref("human.md","b"*40,private,"HUMAN_PERMISSION_REFERENCE_ONLY")
    c.extra_refs=[source]; c.values[source["ref"],source["path"]]=private; c.bind()
    result=c.run(tmp_path/"run")
    assert result["status"]=="VALIDATED_FUNNEL_RESULT",result
    assert private.decode() not in json.dumps(c.calls)
    assert (source["ref"],source["path"]) not in c.reads


def test_module_has_no_production_trigger_and_legacy_request_is_unchanged():
    from pathlib import Path
    # The frozen Suken launcher is retired; its input and shared readers remain.
    assert not Path('.github/workflows/saved-research-once.yml').exists()
    workflows=list(Path('.github/workflows').glob('*.yml'))
    assert workflows
    for path in workflows:
        workflow=path.read_text()
        assert 'decision_kernel.runtime.saved_research_once' not in workflow
        assert 'prepared_disclosure_research' not in workflow
    assert json.loads(Path(once.REQUEST_PATH).read_bytes())["id"]=='p0-suken-api-20260910-v2'


@pytest.mark.parametrize("name", ["launch.json", "candidate.json"])
def test_corrupt_readback_stops_all_later_writes(tmp_path, monkeypatch, name):
    c=Case(monkeypatch); c.corrupt_read=name
    result=c.run(tmp_path/"run")
    assert result["mutation_uncertain"] and c.writes[-1]["path"].endswith(name)
    assert len(c.calls)==(0 if name=="launch.json" else 1)


def test_context_cannot_substitute_a_different_reserved_packet(tmp_path, monkeypatch):
    c=Case(monkeypatch)
    c.context["disclosure_packet"]=json.loads(disclosure_fixture.packet(code="603986"))
    c.context_source=once.source_ref(c.context_source["path"],"e"*40,once.raw(c.context),"MODEL_CONTEXT")
    c.packet["seed_evidence_artifacts"][0]["content_hash"]=c.context_source["sha256"]
    c.bind(); result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and not c.writes and not c.calls
    assert result["error_code"]=="public context changed the reserved disclosure"


def test_concurrent_launch_marker_is_not_overwritten(tmp_path, monkeypatch):
    c=Case(monkeypatch)
    original=c.native
    other=b'{"id":"other launch; do not reset"}'
    def raced(retainer,method,endpoint,body):
        if endpoint.endswith("launch.json"):
            c.values[c.heads[prepared.work.WORK_REF],c.prefix+"launch.json"]=other
        return original(retainer,method,endpoint,body)
    c.native=raced
    result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and not c.calls and not c.writes
    assert c.values[c.heads[prepared.work.WORK_REF],c.prefix+"launch.json"]==other


def test_durable_identity_conflict_still_blocks_before_reservation(tmp_path, monkeypatch):
    c=Case(monkeypatch)
    other=c.parsed.model_copy(update={"research_question":"different frozen question"})
    raw=once.raw(other); source=once.source_ref("conflict/input.json","b"*40,raw,"INPUT")
    c.values[source["ref"],source["path"]]=raw
    c.catalogue["inputs"].append({**once.identity.input_key(other).as_dict(),"input":source})
    c.values[c.code,once.identity.CATALOG_PATH]=once.raw(c.catalogue)
    result=c.run(tmp_path/"run")
    assert result["reason"]=="EXECUTION_ID_CONFLICT" and not c.calls and not c.writes


@pytest.mark.parametrize("field,value", [
    ("max_tool_calls",2), ("max_source_reads",2), ("max_technical_retries",1),
    ("elapsed_time_enforcement","HARD_RUNTIME")])
def test_unsupported_budget_is_rejected_before_spending(tmp_path, monkeypatch, field, value):
    c=Case(monkeypatch); c.packet["budget"][field]=value; c.bind()
    result=c.run(tmp_path/"run")
    assert result["status"]=="NOT_EXECUTED" and not c.calls and not c.writes


def test_reusing_local_directory_cannot_overwrite_evidence(tmp_path, monkeypatch):
    c=Case(monkeypatch); out=tmp_path/"exists"; out.mkdir()
    original=b"original"; (out/"host-receipt.json").write_bytes(original)
    with pytest.raises(FileExistsError): c.run(out)
    assert (out/"host-receipt.json").read_bytes()==original and not c.calls and not c.writes