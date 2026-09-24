"""Offline tests of shared Responses wiring, never real research/provider proof."""
from datetime import datetime, timedelta, timezone
import json
from copy import deepcopy
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
    from test_saved_research_raw_retention import format_converter
    format_converter(monkeypatch)
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


@pytest.mark.parametrize("stage,output_type,make_result", [
    ("pre", PreResearchResult, pre), ("quick", QuickResearchResult, quick)])
@pytest.mark.parametrize("foreign_reference", [False, True])
def test_actual_sdk_stream_shape_with_mock_http_only(tmp_path, monkeypatch, stage, output_type, make_result, foreign_reference):
    sdk=pytest.importorskip("openai")
    if not hasattr(sdk, "OpenAI"):
        import os
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("declared development SDK was not installed")
        pytest.skip("official SDK is unavailable in this local execution environment")
    import httpx2 as httpx
    p,d,c=fixture()
    prompt={"binding":{"discovery_id":p.execution_id,"as_of":p.research_cutoff.isoformat()},"evidence_ids":[str(p.seed_evidence_artifacts[0].id)]}
    if stage == "quick": prompt["pre_research_hash"] = canonical_hash(pre(prompt, "CONTINUE_TO_QUICK"))
    value=make_result(prompt).model_dump(mode="json")
    foreign="d761d18c-37dd-58ff-ba02-3826e25bd988"
    field="material_claims" if stage == "pre" else "supporting_claims"
    if foreign_reference: value[field][0]["evidence_artifact_ids"]=[foreign]
    text=json.dumps(value)
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
        claim_schema=body["text"]["format"]["schema"]["$defs"]["ResearchClaim"]
        assert claim_schema["properties"]["evidence_artifact_ids"]["items"]["enum"] == prompt["evidence_ids"]
        assert body["text"]["format"]["strict"] is True
        assert "GH_FAKE_TOKEN_MUST_NOT_LEAVE" not in request.content.decode()
        assert request.headers["authorization"]=="Bearer fake-sdk-test-key"
        return httpx.Response(200, headers={"content-type":"text/event-stream"},content=data)
    monkeypatch.setattr(sdk,"DefaultHttpxClient",lambda **kw:httpx.Client(transport=httpx.MockTransport(transport),**kw))
    monkeypatch.setenv("SUB2API_API_KEY","fake-sdk-test-key")
    monkeypatch.setenv("GH_TOKEN","GH_FAKE_TOKEN_MUST_NOT_LEAVE")
    usage=[]
    result=w.model_call(stage,prompt,output_type,tmp_path,usage)
    assert type(result) is output_type and result.route.value=="WAIT_FOR_TRIGGER" and len(seen)==1
    assert usage[0]["usage"]["total_tokens"]==2
    assert (tmp_path/(stage+"-model-output.txt")).read_text()==text
    if foreign_reference:
        # A provider ignoring the requested enum must not cause eager SDK
        # citation admission or silent ID repair before retaining raw output.
        assert str(getattr(result,field)[0].evidence_artifact_ids[0])==foreign
        from decision_kernel.research_funnel import validate_pre_research_transition, validate_funnel_transition
        with pytest.raises(ValueError,match="missing evidence"):
            if stage=="pre": validate_pre_research_transition(d,result,p.seed_evidence_artifacts)
            else: validate_funnel_transition(d,pre(prompt,"CONTINUE_TO_QUICK"),result,p.seed_evidence_artifacts)


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


def test_retired_fixed_case_cli_fails_without_launch_or_output(tmp_path):
    import os
    import subprocess
    import sys
    assert not any(hasattr(w, name) for name in ("run", "main", "acquire", "checked_request"))
    assert not hasattr(w.Retainer, "begin")
    out = tmp_path / "retired"
    env = {k: v for k, v in os.environ.items()
           if k not in {"GH_TOKEN", "GITHUB_TOKEN", "SUB2API_API_KEY", "DEEPSEEK_API_KEY"}}
    result = subprocess.run(
        [sys.executable, "-m", w.__name__, "--code-commit", "a" * 40, "--output", str(out)],
        capture_output=True, text=True, timeout=10, check=False, env=env)
    assert result.returncode == 1 and "SAVED_ONE_SHOT_RETIRED" in result.stderr
    assert not out.exists()
