"""Offline tests of bounded Responses wiring, never real research/provider proof."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from decision_kernel.runtime import saved_research_once as w
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from decision_kernel.research_funnel import DiscoveryInput, PreResearchResult, QuickResearchResult
from decision_kernel.identity import canonical_hash


def fixture():
    stamp = (datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    context = {"issuer_report": {"pages": [{"text": "Synthetic public issuer body."}]}, "market_observation": {"reading": "Synthetic saved observation, not a live market."}}
    spec = w.source_ref("research_runs/candidates/test/case/source.json", "b"*40, w.raw(context), "MODEL_CONTEXT")
    eid = "a2a253cd-f8b9-5cf8-95c0-678b887a3ced"
    seed = dict(id=eid, source_type="SAVED_RESEARCH_OBSERVATION", source_identifier="synthetic", source_locator=w.locator(spec),
        published_at=stamp, available_at=stamp, retrieved_at=stamp, content_hash=spec["sha256"], idempotency_key="synthetic",
        retention_mode="FULL_ARTIFACT", replayability_level="PARTIAL", raw_storage_ref=w.locator(spec))
    p = ExternalResearchInputPacket(execution_id="synthetic-once", case_id="601952.SH", ticker="601952", security_id="SSE:601952",
        source_lane="SECTOR_SAVED_MEMBER_READING", selected_at=stamp, research_cutoff=stamp, code_commit="a"*40,
        current_state_commit="c"*40, current_state_reading_hash="d"*64, source_refs=[spec], seed_evidence_artifacts=[seed],
        research_question="Synthetic question", known_unknowns=["Unknown economics"], next_discriminating_search="Read source",
        method_version="research-funnel-v1", prompt_version="test", allowed_tools=["OTHER_READ"], candidate_output_prefix="research_runs/candidates/test/case/",
        budget={"max_tool_calls":6,"max_search_queries":0,"max_source_reads":4,"max_technical_retries":0,"max_elapsed_minutes":15,
            **{k+"_enforcement":"SOFT_EXECUTOR" for k in ["tool_calls","search_queries","source_reads","technical_retries","elapsed_time"]}})
    d = DiscoveryInput(discovery_id=p.execution_id, source_lane=p.source_lane, ticker=p.ticker,security_id=p.security_id,
        economic_direction="Synthetic",as_of=p.research_cutoff,
        factual_observations=[{"statement":"Synthetic observation", "evidence_artifact_ids":[eid]}],
        source_lineage=[{"evidence_artifact_id":eid,"source_locator":w.locator(spec),"available_at":stamp}],
        why_now="Synthetic", next_discriminating_search="Synthetic",known_stop_or_downgrade_condition="No evidence")
    return p,d,context


def pre(prompt, route="WAIT_FOR_TRIGGER"):
    return PreResearchResult(discovery_id=prompt["binding"]["discovery_id"],as_of=prompt["binding"]["as_of"],
        what_is_this="Synthetic source",economic_direction="Synthetic",why_surfaced_now="Saved observation",
        basic_business_role="Unknown",potential_fundamental_driver="Unknown",current_market_expectation_hypothesis="Unknown",
        material_claims=[{"statement":"Synthetic source exists", "kind":"FACT", "evidence_artifact_ids":prompt["evidence_ids"]}],
        largest_unknown="Material economics unknown",next_discriminating_search="Find differentiated evidence",route=route,route_reason="Synthetic route")


def quick(prompt, route="WAIT_FOR_TRIGGER"):
    claim={"statement":"Synthetic evidence", "kind":"FACT", "evidence_artifact_ids":prompt["evidence_ids"]}
    return QuickResearchResult(discovery_id=prompt["binding"]["discovery_id"],as_of=prompt["binding"]["as_of"],
        pre_research_hash=prompt["pre_research_hash"],business_model="Synthetic",segment_mix="UNKNOWN",economic_role="Synthetic",
        major_profit_drivers=["Unknown"], industry_supply_demand_variables=["Unknown"],value_chain_position="Unknown",
        market_expectation_hypothesis="Unknown",supporting_claims=[claim], contradictory_claims=[claim],
        evidence_authority_assessment="Synthetic",variant_perception="Synthetic alternative only",unresolved_questions=["Unknown"],
        next_discriminating_evidence=["Unknown"],route=route,route_reason="Synthetic route")


@pytest.mark.parametrize("route", ["WAIT_FOR_TRIGGER", "STOP"])
def test_pre_terminal_does_not_call_quick(tmp_path, route):
    p,d,c=fixture(); calls=[]
    def call(stage,prompt,model,out,usage):
        calls.append(stage);return pre(prompt,route)
    candidate,result,usage=w.research(p,d,c,tmp_path,call=call)
    assert calls==["pre"] and candidate.quick_research is None
    assert result.status.value=="VALIDATED_FUNNEL_RESULT" and result.investment_authority=="NONE"
    assert candidate.receipt.tool_calls_used==2 and candidate.receipt.technical_retries_used==0


@pytest.mark.parametrize("route", ["WAIT_FOR_TRIGGER", "STOP", "DEEPEN"])
def test_only_valid_continue_calls_one_quick_and_never_deep(tmp_path, route):
    p,d,c=fixture();calls=[]
    def call(stage,prompt,model,out,usage):
        calls.append(stage)
        return pre(prompt,"CONTINUE_TO_QUICK") if stage=="pre" else quick(prompt,route)
    candidate,result,_=w.research(p,d,c,tmp_path,call=call)
    assert calls==["pre","quick"] and result.status.value=="VALIDATED_FUNNEL_RESULT"
    assert candidate.receipt.tool_calls_used==3 and candidate.receipt.search_queries_used==0


@pytest.mark.parametrize("failure_stage", ["pre", "quick"])
def test_provider_failure_is_gap_with_no_retry(tmp_path, failure_stage):
    p,d,c=fixture();calls=[]
    def call(stage,prompt,model,out,usage):
        calls.append(stage)
        if stage==failure_stage: raise RuntimeError("untrusted exception text")
        return pre(prompt,"CONTINUE_TO_QUICK")
    candidate,result,_=w.research(p,d,c,tmp_path,call=call)
    assert calls==(["pre"] if failure_stage=="pre" else ["pre","quick"])
    assert result.status.value=="EXECUTION_GAP" and result.funnel_result is None
    assert candidate.quick_research is None and "untrusted exception text" not in candidate.model_dump_json()


def test_context_changed_before_call_is_not_wait(tmp_path):
    p,d,c=fixture();c["private_human_note"]="must not be sent"
    candidate,result,_=w.research(p,d,c,tmp_path,call=lambda *_:pytest.fail("must not call provider"))
    assert result.status.value=="EXECUTION_GAP"


def test_bad_pre_identity_stops_before_quick_and_retains_raw_candidate(tmp_path):
    p,d,c=fixture();calls=[]
    def call(stage,prompt,model,out,usage):
        calls.append(stage)
        return pre(prompt,"CONTINUE_TO_QUICK").model_copy(update={"discovery_id":"wrong"})
    with pytest.raises(ValueError):
        w.research(p,d,c,tmp_path,call=call)
    assert calls==["pre"] and (tmp_path/"model-usage.json").exists()
    assert (tmp_path/"candidate-before-validation.json").exists()


def test_native_write_uncertainty_does_not_retry(tmp_path, monkeypatch):
    r=w.Retainer(None,{"prefix":"research_runs/candidates/test/case/","work_ref":"research-candidate/test","id":"test"},"a"*40,tmp_path)
    calls=[]
    def fail(*args,**kwargs):
        calls.append(args);return SimpleNamespace(returncode=1, stdout=b"", stderr=b"secret-bearing detail")
    monkeypatch.setattr(w.subprocess,"run",fail)
    with pytest.raises(ValueError, match="uncertain"):
        r.native("PUT","contents/fixed",{})
    with pytest.raises(ValueError, match="uncertain"):
        r.native("PUT","contents/fixed",{})
    assert len(calls)==1


def test_write_paths_are_not_model_controlled(tmp_path):
    r=w.Retainer(None,{},"a"*40,tmp_path)
    with pytest.raises(ValueError,match="fixed candidate"):
        r.save("../../.github/workflows/evil.yml",b"bad")


def test_original_admission_denial_never_calls_executor(monkeypatch):
    calls=[]
    monkeypatch.setattr(w.admission,"assess_admission", lambda **_: {"research_execution_allowed":False,"reason":"SOURCE_PREFLIGHT_INCOMPLETE"})
    report, output=w.admission.execute_after_admission(executor=lambda *_:calls.append(1), input_raw=b"{}")
    assert output is None and calls==[]


@pytest.mark.parametrize("unexpected_tool", [False, True])
def test_sdk_is_tool_free_pinned_and_does_not_retain_reasoning(tmp_path, monkeypatch, unexpected_tool):
    import sys
    p,d,c=fixture(); kwargs_seen={}
    prompt={"binding":{"discovery_id":p.execution_id,"as_of":p.research_cutoff.isoformat()},"evidence_ids":[str(p.seed_evidence_artifacts[0].id)]}
    response=SimpleNamespace(output_text=pre(prompt).model_dump_json(), status="completed", id="synthetic-response",
        usage=None, output=[SimpleNamespace(type="function_call" if unexpected_tool else "reasoning", content="DO_NOT_RETAIN_PRIVATE_REASONING")])
    class Context:
        def __enter__(self): return self
        def __exit__(self,*_): pass
        def get_final_response(self): return response
    class Client(Context):
        def __init__(self,**kwargs): kwargs_seen.update(kwargs); self.responses=self
        def stream(self,**kwargs): kwargs_seen["request"]=kwargs; return Context()
    monkeypatch.setitem(sys.modules,"openai",SimpleNamespace(OpenAI=Client,DefaultHttpxClient=lambda **kwargs:kwargs))
    monkeypatch.setenv("SUB2API_API_KEY","synthetic-key-never-real")
    usage=[]
    if unexpected_tool:
        with pytest.raises(ValueError,match="tool"):
            w.model_call("pre",prompt,PreResearchResult,tmp_path,usage)
    else:
        assert w.model_call("pre",prompt,PreResearchResult,tmp_path,usage).route.value=="WAIT_FOR_TRIGGER"
    assert kwargs_seen["max_retries"]==0 and kwargs_seen["base_url"]==w.BASE_URL
    assert kwargs_seen["http_client"]["follow_redirects"] is False
    assert kwargs_seen["request"]["tools"]==[] and kwargs_seen["request"]["store"] is False
    assert kwargs_seen["request"]["model"]=="gpt-6-astra"
    assert kwargs_seen["request"]["max_output_tokens"]==6000
    saved="\n".join(p.read_text() for p in tmp_path.iterdir())
    assert "DO_NOT_RETAIN_PRIVATE_REASONING" not in saved and "synthetic-key-never-real" not in saved


def test_oversized_payload_is_rejected_before_provider_import(tmp_path):
    with pytest.raises(ValueError,match="byte budget"):
        w.model_call("pre",{"body":"x"*w.MAX_PROMPT_BYTES},PreResearchResult,tmp_path,[])
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize("backdated", [None, "preflight.json", "input.json"])
def test_full_host_uses_original_gate_and_retains_exact_input_before_model(tmp_path, monkeypatch, backdated):
    """Fake I/O only; actual packet/admission/Funnel/receipt models execute."""
    from decision_kernel.runtime import current_state_delivery as delivery
    original_request=json.loads((Path(__file__).parents[1]/w.REQUEST_PATH).read_text())
    p,_,_=fixture(); code="a"*40; reading_ref="c"*40
    market=b"Synthetic retained comparison 14.48 24.91 9.87 15.52; PRIVATE_HUMAN_NOTE_NOT_FOR_MODEL"
    original_request["market_source"]=w.source_ref("market.md","b"*40,market,"market")
    p_raw=w.raw(p); old_spec=w.source_ref("old-input.json","b"*40,p_raw,"old")
    catalog={"schema_version":1,"inputs":[{**w.identity.input_key(p).as_dict(),"input":old_spec}]}
    reading={"schema_version":1};reading["reading_hash"]=canonical_hash(reading)
    files={code:{w.identity.CATALOG_PATH:w.raw(catalog)},"b"*40:{"market.md":market,"old-input.json":p_raw},
        reading_ref:{"current-state.json":w.raw(reading)}}
    heads={"main":code,"read-model/current-state":reading_ref}
    commits={}; mutations=[]; model_prompts=[]
    # Real Git clocks have whole seconds; the old mock's microseconds hid the bug.
    stamp = (datetime.now(timezone.utc)-timedelta(minutes=1)).replace(microsecond=261214)
    sleeps = []
    def clock():
        nonlocal stamp
        stamp += timedelta(milliseconds=10)
        return stamp.isoformat()
    def sleep(seconds):
        nonlocal stamp
        sleeps.append(seconds)
        stamp += timedelta(seconds=seconds)
    monkeypatch.setattr(w, "now", clock)
    monkeypatch.setattr(w.time, "sleep", sleep)
    class API:
        def __init__(self,token): self.calls=0
        def get(self,path):
            self.calls+=1
            if path.startswith("git/ref/heads/"):
                name=path.removeprefix("git/ref/heads/")
                if name not in heads: raise delivery.GitHubReadError("GitHub HTTP 404")
                return {"object":{"sha":heads[name]}}
            if path.startswith("git/commits/"):
                return commits[path.removeprefix("git/commits/")]
            raise AssertionError(path)
        def _call(self,method,path):
            assert method=="GET"; data=self.get(path); return SimpleNamespace(json=lambda:data)
        def file(self,path,ref): self.calls+=1;return files[ref][path]
    def native(self,method,endpoint,body):
        mutations.append((method,endpoint,body))
        if endpoint=="git/refs":
            name=body["ref"].removeprefix("refs/heads/");heads[name]=body["sha"]
            return {"ref":body["ref"],"object":{"sha":body["sha"]}}
        assert method=="PUT" and endpoint.startswith("contents/"), endpoint
        assert "sha" not in body and body["branch"]==original_request["work_ref"]
        path=endpoint.removeprefix("contents/")
        before=heads[body["branch"]]
        if path in files[before]:
            self.uncertain=True
            raise ValueError("existing create-only file; do not retry")
        new=f"{len(mutations):040x}"; new_files=dict(files[before]);new_files[path]=w.base64.b64decode(body["content"])
        files[new]=new_files;heads[body["branch"]]=new
        committed = datetime.fromisoformat(w.now()).replace(microsecond=0)
        if backdated and path.endswith("/"+backdated):
            committed -= timedelta(seconds=2)  # Actual bad order must still fail.
        commits[new]={"sha":new,"committer":{"date":committed.isoformat()}}
        return {"commit":{"sha":new},"content":{"sha":w.blob(new_files[path])}}
    def acquire(request,out):
        return {"source_url":request["source_url"],"retrieved_at":w.now(),"pdf_sha256":"f"*64,
            "pages":[{"page_number":11,"text":"Synthetic public body. All results are mocked fixtures."}]}
    def call(stage,prompt,model,out,usage):
        assert stage=="pre"
        assert any(name.endswith("/input.json") for name in files[heads[original_request["work_ref"]]])
        model_prompts.append(prompt)
        assert "PRIVATE_HUMAN_NOTE_NOT_FOR_MODEL" not in json.dumps(prompt)
        return pre(prompt)
    monkeypatch.setattr(delivery,"GitHubAPI",API)
    monkeypatch.setattr(w.Retainer,"native",native)
    monkeypatch.setattr(w,"acquire",acquire)
    monkeypatch.setattr(w,"model_call",call)
    monkeypatch.setenv("GH_TOKEN","synthetic-only")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT","1")
    monkeypatch.setenv("GITHUB_REF","refs/heads/main")
    exit_code = w.run(original_request,code,tmp_path/"first")
    local = tmp_path/"first"
    prepared_raw = (local/"input-preparation.json").read_bytes()
    prepared = json.loads(prepared_raw)
    assert prepared["research_cutoff"].split(".")[-1] != "000000+00:00"
    prepare_report = json.loads((local/"prepare.json").read_bytes())
    prepare_path = original_request["prefix"]+"prepare.json"
    assert files[heads[original_request["work_ref"]]][prepare_path] == (local/"prepare.json").read_bytes()
    assert prepare_report["input_file_sha256"] == w.sha(prepared_raw)
    if backdated:
        expected = ("PREFLIGHT_NOT_COMMITTED_BEFORE_SELECTION" if backdated == "preflight.json"
                    else "INPUT_COMMIT_CLOCK_INVALID")
        report = prepare_report if backdated == "preflight.json" else json.loads((local/"admission.json").read_bytes())
        assert report["reason"] == expected and not report["research_execution_allowed"]
        host = json.loads((local/"host-receipt.json").read_bytes())
        assert host["status"] == "NOT_EXECUTED" and host["formal_research_started"] is False
        if backdated == "preflight.json":
            assert host["error_code"] == expected
            assert not (local/"input.json").exists()
        assert exit_code == 2 and model_prompts == [] and not (local/"candidate.json").exists()
        assert w.run(original_request,code,tmp_path/"repeat")==2 and model_prompts == []
        return
    assert exit_code == 0
    assert prepared_raw == (local/"input.json").read_bytes()
    assert prepare_report["reason"] == "INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION"
    assert not prepare_report["research_execution_allowed"]
    assert len(sleeps) == 2 and all(0 < n <= 1 for n in sleeps)
    result=json.loads((tmp_path/"first"/"validation.json").read_text())
    assert result["status"]=="VALIDATED_FUNNEL_RESULT" and len(model_prompts)==1
    adm=json.loads((tmp_path/"first"/"admission.json").read_text())
    assert adm["reason"]=="RESEARCH_EXECUTION_ALLOWED"
    assert heads["main"]==code
    assert w.run(original_request,code,tmp_path/"repeat")==2
    assert len(model_prompts)==1


def test_actual_sdk_stream_shape_with_mock_http_only(tmp_path, monkeypatch):
    sdk=pytest.importorskip("openai")
    if not hasattr(sdk, "OpenAI"):
        import os
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("declared development SDK was not installed")
        pytest.skip("official SDK is unavailable in this local execution environment")
    import httpx2 as httpx
    p,d,c=fixture()
    prompt={"binding":{"discovery_id":p.execution_id,"as_of":p.research_cutoff.isoformat()},"evidence_ids":[str(p.seed_evidence_artifacts[0].id)]}
    text=pre(prompt).model_dump_json()
    part={"type":"output_text","text":text,"annotations":[]}
    item={"id":"msg_fixture","type":"message","role":"assistant","status":"completed","content":[part]}
    final={"id":"resp_fixture","object":"response","created_at":1789056000,"status":"completed","model":w.MODEL,
        "output":[item],"parallel_tool_calls":False,"tool_choice":"auto","tools":[],"error":None,"incomplete_details":None,
        "usage":{"input_tokens":1,"input_tokens_details":{"cached_tokens":0},"output_tokens":1,"output_tokens_details":{"reasoning_tokens":0},"total_tokens":2}}
    events=[
      {"type":"response.created","response":{**final,"status":"in_progress","output":[]}},
      {"type":"response.output_item.added","output_index":0,"item":{**item,"status":"in_progress","content":[]}},
      {"type":"response.content_part.added","output_index":0,"content_index":0,"item_id":"msg_fixture","part":{**part,"text":""}},
      {"type":"response.output_text.delta","output_index":0,"content_index":0,"item_id":"msg_fixture","delta":text},
      {"type":"response.output_text.done","output_index":0,"content_index":0,"item_id":"msg_fixture","text":text},
      {"type":"response.content_part.done","output_index":0,"content_index":0,"item_id":"msg_fixture","part":part},
      {"type":"response.output_item.done","output_index":0,"item":item},
      {"type":"response.completed","response":final}]
    data="".join("data: "+json.dumps({**e,"sequence_number":i})+"\n\n" for i,e in enumerate(events)).encode()
    seen=[]
    def transport(request):
        body=json.loads(request.content);seen.append(body)
        assert request.url==w.BASE_URL+"/responses"
        assert body["model"]==w.MODEL and body["tools"]==[] and body["stream"] is True
        assert "GH_FAKE_TOKEN_MUST_NOT_LEAVE" not in request.content.decode()
        assert request.headers["authorization"]=="Bearer fake-sdk-test-key"
        return httpx.Response(200, headers={"content-type":"text/event-stream"},content=data)
    monkeypatch.setattr(sdk,"DefaultHttpxClient",lambda **kw:httpx.Client(transport=httpx.MockTransport(transport),**kw))
    monkeypatch.setenv("SUB2API_API_KEY","fake-sdk-test-key")
    monkeypatch.setenv("GH_TOKEN","GH_FAKE_TOKEN_MUST_NOT_LEAVE")
    usage=[]
    result=w.model_call("pre",prompt,PreResearchResult,tmp_path,usage)
    assert result.route.value=="WAIT_FOR_TRIGGER" and len(seen)==1
    assert usage[0]["usage"]["total_tokens"]==2


@pytest.mark.parametrize("name,field", [("preflight.json", "finished_at"), ("input.json", "research_cutoff")])
@pytest.mark.parametrize("stamp,elapsed,expected_wait", [
    ("2026-09-10T14:37:59.261214+00:00", 0, 0.738786),
    ("2026-09-10T22:37:59.261214+08:00", 0, 0.738786),
    ("2026-09-10T14:37:59.999999+00:00", 0, 0.000001),
    ("2026-09-10T14:38:00+00:00", 0, 0),
    ("2026-09-10T14:37:59.261214+00:00", 2, 0),
])
def test_commit_wait_keeps_original_bytes_and_only_delays_native_write(
        tmp_path, monkeypatch, name, field, stamp, elapsed, expected_wait):
    # First row is the real failed run's boundary, not a reconstructed admission.
    event = w.admission.clock(stamp)
    current = event + timedelta(seconds=elapsed)
    sent = []
    waits = []
    data = w.raw({field: stamp})
    request = {"prefix":"research_runs/candidates/test/case/", "work_ref":"research-candidate/test", "id":"test"}
    def sleep(delay):
        nonlocal current
        waits.append(delay)
        current += timedelta(seconds=delay)
    def native(method, path, body):
        assert method == "PUT" and "sha" not in body
        assert w.base64.b64decode(body["content"]) == data
        # Git serializes an actual next-second commit, never edits the event.
        committed = current.replace(microsecond=0)
        w.admission.require(event <= committed, "PREFLIGHT_NOT_COMMITTED_BEFORE_SELECTION")
        sent.append(path)
        return {"commit":{"sha":"b"*40},"content":{"sha":w.blob(data)}}
    api = SimpleNamespace(file=lambda path, ref: data)
    retainer = w.Retainer(api, request, "a"*40, tmp_path)
    monkeypatch.setattr(retainer, "native", native)
    monkeypatch.setattr(w, "now", lambda: current.isoformat())
    monkeypatch.setattr(w.time, "sleep", sleep)
    result = retainer.save(name, data)
    assert len(sent) == 1 and result["git_blob"] == w.blob(data)
    assert (tmp_path/name).read_bytes() == data
    assert waits == ([pytest.approx(expected_wait)] if expected_wait else [])


@pytest.mark.parametrize("failure", ["reversed", "sleep_did_not_advance", "naive_clock"])
def test_bad_commit_clock_never_writes_or_retries(tmp_path, monkeypatch, failure):
    stamp = "2026-09-10T14:37:59.261214+00:00"
    event = w.admission.clock(stamp)
    current = event-timedelta(seconds=1) if failure == "reversed" else event
    retainer = w.Retainer(None, {"prefix":"fixed/"}, "a"*40, tmp_path)
    monkeypatch.setattr(retainer, "native", lambda *_: pytest.fail("must not mutate GitHub"))
    monkeypatch.setattr(w, "now", lambda: current.replace(tzinfo=None).isoformat()
                        if failure == "naive_clock" else current.isoformat())
    waits = []
    monkeypatch.setattr(w.time, "sleep", lambda delay: waits.append(delay))
    data = w.raw({"finished_at":stamp})
    with pytest.raises(ValueError):
        retainer.save("preflight.json", data)
    assert len(waits) == (1 if failure == "sleep_did_not_advance" else 0)
    assert (tmp_path/"preflight.json").read_bytes() == data


def test_actual_old_commit_still_fails_original_order_check():
    # Values from run34490271156 / commit72ecf07; no old record is corrected.
    with pytest.raises(w.admission.AdmissionRejected, match="PREFLIGHT_NOT_COMMITTED_BEFORE_SELECTION"):
        w.admission.require(w.admission.clock("2026-09-10T14:37:59.261214+00:00")
                            <= w.admission.clock("2026-09-10T14:37:59Z"),
                            "PREFLIGHT_NOT_COMMITTED_BEFORE_SELECTION")
