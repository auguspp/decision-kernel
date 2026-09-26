"""Same existing client; bounded caller control, checkpoints and exact calendar reuse."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
import runpy
import socket
import zipfile

import pytest

from decision_kernel.runtime import smart_money_relay as relay
from decision_kernel.runtime import smart_money_relay_contract as contract
from decision_kernel.runtime import smart_money_sources as source
from decision_kernel.runtime import smart_money_reading as reading
from test_smart_money_relay import IDENT, response, sample_body
from test_smart_money_capture import setup_reader

NOW = "2026-09-26T02:15:00Z"
BOUND = {"identity": IDENT, "capture_hash": "e"*64, "cutoff": "2026-09-26T01:00:00Z",
         "trading_sessions": ["2026-09-24"]}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("no live source calls in execution contract tests")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setenv(relay.relay.SECRET_ENV, "test-not-a-real-key")


def capture(tmp_path, request=None, **kwargs):
    return relay.capture(tmp_path/"supplement", IDENT, "2026-09-24", revision=2,
        source_capture=deepcopy(BOUND), clock=lambda:NOW,
        request=request or (lambda api,params,key,clock:response(api,params,clock)), **kwargs)


def files(tmp_path):
    return {p.name:p.read_bytes() for p in (tmp_path/"supplement").iterdir()}


def test_seven_calendar_day_forecast_window_is_separate_from_market_day(tmp_path):
    out=capture(tmp_path)
    assert out["plan_revision"]==2 and out["execution_complete"]
    saved=source.decode(files(tmp_path)["capture.json"])
    assert saved["as_of_date"]=="2026-09-26" and saved["market_session"]=="2026-09-24"
    assert saved["records"][2]["spec"]["params"]=={
        "start_date":"20260920","end_date":"20260926","limit":"3000"}
    assert out["source_capture"]==BOUND
    assert relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)==out


@pytest.mark.parametrize("date,valid", [("20260919",False),("20260920",True),
    ("20260925",True),("20260926",True),("20260927",False)])
def test_report_weekend_lateness_does_not_rewrite_report_date(date,valid):
    spec=relay.plan("2026-09-24",revision=2,as_of="2026-09-26")[2]
    body=sample_body("report_rc",spec["params"])
    body["data"]["items"][0][0]=date
    result=contract.qualify(body,spec,received_at=NOW)
    assert (result["qualified_row_count"]==1)==valid
    assert result["rows"][0]["report_date"]==date
    assert result["rows"][0]["quarter"]=="2027Q4"


@pytest.mark.parametrize("status", [401,403,429])
def test_refusal_stops_service_for_rest_of_run_without_erasing_first_page(tmp_path,status):
    calls=[]
    def request(api,params,key,clock):
        calls.append(api)
        if api=="hm_detail":
            tag="RATE_LIMIT" if status==429 else "AUTH_OR_ENTITLEMENT"
            result=response(api,params,clock,status=tag)
            result["attempts"][0]["http_status"]=status
            result["attempts"][0]["headers"]["Retry-After"]="60"
            return result
        return response(api,params,clock)
    out=capture(tmp_path,request)
    assert calls==["hm_list","hm_detail"]
    assert out["families"]["hm_list"]["row_count"]==1
    assert out["status"]=="PARTIAL_WITH_EXPLICIT_GAPS"
    assert all(out["families"][api]["status"]=="NOT_ATTEMPTED_SERVICE_STOP" for api in relay.APIS[2:])
    assert relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)==out


def test_interruption_preserves_previous_checkpoint_not_a_fake_complete_capture(tmp_path):
    calls=[]
    def request(api,params,key,clock):
        calls.append(api)
        if api=="hm_detail":raise KeyboardInterrupt()
        return response(api,params,clock)
    with pytest.raises(KeyboardInterrupt):capture(tmp_path,request)
    result=relay.replay(files(tmp_path),identity=IDENT,cutoff=NOW)
    assert result["execution_complete"] is False and result["status"]=="PARTIAL_WITH_EXPLICIT_GAPS"
    assert result["families"]["hm_list"]["row_count"]==1
    assert result["families"]["hm_detail"]["status"]=="NOT_ATTEMPTED"
    assert any(x["status"]=="CAPTURE_CHECKPOINT_NOT_FINAL" for x in result["unresolved"])


@pytest.mark.parametrize("kind", ["exception","header_reflection","unexpected_attempt","bad_api"])
def test_missing_or_unsafe_receipt_stops_without_key_leak_or_invented_attempt_count(tmp_path,kind):
    calls=[]
    def request(api,params,key,clock):
        calls.append(api)
        if kind=="exception":raise relay.relay.RelayError("unsafe "+key)
        result=response(api,params,clock)
        if kind=="header_reflection":result["attempts"][0]["headers"]["X-Cache"]=key
        elif kind=="unexpected_attempt":result["attempts"][0]["attempt"]="../../outside"
        else:result["api"]="not-requested"
        return result
    out=capture(tmp_path,request)
    assert calls==["hm_list"] and out["status"]=="UNAVAILABLE_NOT_QUIET"
    assert out["families"]["hm_list"]["status"]=="REQUEST_RECEIPT_UNAVAILABLE"
    assert out["families"]["hm_list"]["attempts"]==[]
    assert out["families"]["hm_list"]["recorded_http_attempt_count"] is None
    assert out["families"]["hm_list"]["receipt_error_type"] in {"RelayError","SourceError"}
    assert all(b"test-not-a-real-key" not in raw for raw in files(tmp_path).values())
    assert not (tmp_path/"outside").exists()


def test_legacy_v1_plan_and_raw_capture_still_replay(tmp_path):
    out=relay.capture(tmp_path/"legacy",IDENT,"2026-09-24",
        request=lambda api,params,key,clock:response(api,params,clock),clock=lambda:NOW)
    saved={p.name:p.read_bytes() for p in (tmp_path/"legacy").iterdir()}
    manifest=source.decode(saved["capture.json"])
    assert "plan_revision" not in manifest and manifest["records"][2]["spec"]["params"]["report_date"]=="20260924"
    assert relay.replay(saved,identity=IDENT,cutoff=NOW)==out


@pytest.mark.parametrize("damage", ["future","session","source_hash","asof"])
def test_rehashed_capture_cannot_break_calendar_or_window_binding(tmp_path,damage):
    capture(tmp_path);saved=files(tmp_path);manifest=source.decode(saved["capture.json"])
    if damage=="future":manifest["source_capture"]["cutoff"]="2027-01-01T00:00:00Z"
    elif damage=="session":manifest["source_capture"]["trading_sessions"]=["2026-09-23"]
    elif damage=="source_hash":manifest["source_capture"]["capture_hash"]="not-a-hash"
    else:manifest["as_of_date"]="2026-09-25"
    manifest["capture_hash"]=relay._manifest_hash(manifest);saved["capture.json"]=source.encoded(manifest)
    with pytest.raises(ValueError):relay.replay(saved,identity=IDENT,cutoff=NOW)


def control_module():
    return runpy.run_path('.github/scripts/smart-money-control.py')


def test_relay_daily_bound_counts_started_jobs_across_different_code_not_primary_skips():
    mod=control_module();runs=[{"id":i,"head_sha":str(i)*40,"run_attempt":1} for i in range(1,6)]
    def jobs(rid):
        row={"id":100+rid,"name":"capture-tushare-relay","run_id":rid,"head_sha":str(rid)*40,
             "run_attempt":1,"status":"completed","conclusion":"success","started_at":NOW}
        if rid==2:return {"total_count":0,"jobs":[]}
        if rid==3:row["conclusion"]="skipped"
        return {"total_count":1,"jobs":[row]}
    assert mod["relay_started_count"](runs,5,jobs)==2
    runs[0]["head_sha"]="a"*40
    with pytest.raises(ValueError,match="RELAY_JOB_IDENTITY"):
        mod["relay_started_count"](runs,5,jobs)


@pytest.mark.parametrize("damage", ["count","duplicate","attempt","current"])
def test_uncertain_job_enumeration_does_not_reset_relay_budget(damage):
    mod=control_module();runs=[{"id":1,"head_sha":"a"*40,"run_attempt":1},
                              {"id":2,"head_sha":"b"*40,"run_attempt":1}]
    if damage=="duplicate":runs.append(runs[0])
    if damage=="attempt":runs[0]["run_attempt"]=2
    if damage=="current":runs.pop()
    with pytest.raises(ValueError):
        mod["relay_started_count"](runs,2,lambda rid:{"total_count":1,"jobs":[]})


def make_reuse(tmp_path,monkeypatch):
    col,base,old,job,art,observation=setup_reader(tmp_path)
    original=col.api.raw_archive
    rid=old["id"]+1;head="d"*40
    current={**deepcopy(old),"id":rid,"head_sha":head,"created_at":"2026-09-26T02:10:00Z",
             "updated_at":"2026-09-26T02:20:00Z"}
    identity={**observation["identity"],"run_id":rid,"code_commit":head}
    selected={"run_id":old["id"],"head_sha":old["head_sha"],"artifact_id":art["id"],
              "artifact_name":art["name"],"digest":art["digest"],"bytes":art["size_in_bytes"],
              "capture_hash":observation["capture_hash"]}
    control={"run_id":rid,"code_commit":head,"decision":"SKIP_RELAY_ONLY_REUSE_CAPTURE",
             "relay_only":True,"relay_source":selected}
    def zipbytes(values):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,raw in values.items():z.writestr(name,raw)
        return stream.getvalue()
    out=tmp_path/"new-relay"
    relay.capture(out,identity,max(observation["trading_sessions"]),revision=2,
        source_capture=relay.source_binding(observation),clock=lambda:NOW,
        request=lambda api,params,key,clock:response(api,params,clock))
    raw_control=zipbytes({"control.json":json.dumps(control).encode()})
    raw_relay=zipbytes({p.name:p.read_bytes() for p in out.iterdir()})
    archives={900:original,901:raw_control,902:raw_relay}
    def artifact(aid,name):
        raw=archives[aid]
        return {"id":aid,"name":name,"size_in_bytes":len(raw),"digest":"sha256:"+sha256(raw).hexdigest(),
                "expired":False,"workflow_run":{"id":rid,"head_sha":head}}
    ctr=artifact(901,f"smart-money-control-{rid}-1");sup=artifact(902,f"smart-money-relay-{rid}-1")
    def archive(item):col.api.calls+=1;return archives[item["id"]]
    col.api.archive=archive
    col.api.responses[reading.QUERY]={"total_count":2,"workflow_runs":[current,old]}
    col.api.responses[f"actions/runs/{rid}"]=current
    col.api.responses[f"actions/runs/{rid}/attempts/1/jobs?per_page=100"]={"total_count":2,"jobs":[
        {**job,"id":144,"run_id":rid,"head_sha":head},
        {**job,"id":145,"run_id":rid,"head_sha":head,"status":"completed","name":"capture-tushare-relay"}]}
    col.api.responses[f"actions/runs/{rid}/artifacts?per_page=100"]={"total_count":2,"artifacts":[ctr,sup]}
    return col,base,observation,current,control,archives,ctr,sup,zipbytes


def test_real_reader_recovers_old_calendar_and_new_relay_without_new_primary_calls(tmp_path,monkeypatch):
    col,base,primary,current,*_=make_reuse(tmp_path,monkeypatch)
    result=reading.attach(col,base);sm=result["research"]["smart_money"]
    assert sm["status"]=="READY" and sm["relay_status"]=="READY"
    assert sm["capture_hash"]==primary["capture_hash"] and sm["source_cutoff"]==primary["cutoff"]
    assert sm["latest_attempt"]["id"]==current["id"]
    value=json.loads(col.files[sm["details"]["relay"]["read_path"]])
    assert value["source_capture"]["identity"]["run_id"]==primary["identity"]["run_id"]
    assert value["identity"]["run_id"]==current["id"] and value["cutoff"]==NOW
    overview=json.loads(col.files[sm["details"]["overview"]["read_path"]])
    assert overview["origins"][sm["capture_hash"]]["run"]["id"]==primary["identity"]["run_id"]
    assert result["lanes"]==base["lanes"]
    reading.m.validate_read_package(result)


def test_new_relay_wrong_calendar_source_rejects_only_supplement(tmp_path,monkeypatch):
    col,base,primary,current,control,archives,ctr,sup,zipbytes=make_reuse(tmp_path,monkeypatch)
    with zipfile.ZipFile(io.BytesIO(archives[902])) as z:saved={n:z.read(n) for n in z.namelist()}
    manifest=source.decode(saved["capture.json"]);manifest["source_capture"]["capture_hash"]="f"*64
    manifest["capture_hash"]=relay._manifest_hash(manifest);saved["capture.json"]=source.encoded(manifest)
    archives[902]=zipbytes(saved);sup.update(size_in_bytes=len(archives[902]),digest="sha256:"+sha256(archives[902]).hexdigest())
    result=reading.attach(col,base);sm=result["research"]["smart_money"]
    assert sm["status"]=="READY" and sm["capture_hash"]==primary["capture_hash"]
    assert sm["relay_status"]=="CURRENT_RELAY_READING_GAP" and "relay" not in sm["details"]


def test_retained_source_preflight_selects_only_already_accepted_original(tmp_path):
    col,base,run,job,art,obs=setup_reader(tmp_path)
    previous={"last_source_run_id":run["id"],"capture_hash":obs["capture_hash"],"cutoff":obs["cutoff"]}
    def get(path,params=None):
        if path.endswith('/artifacts'):return {"total_count":1,"artifacts":[art]}
        return run
    out=control_module()["retained_relay_source"](previous,get)
    assert out["artifact_id"]==art["id"] and out["capture_hash"]==obs["capture_hash"]
    art["expired"]=True
    with pytest.raises(ValueError,match="RELAY_PRIOR_ARTIFACT_IDENTITY"):
        control_module()["retained_relay_source"](previous,get)


def test_workflow_keeps_primary_credentials_out_of_relay_and_native_artifact_reuse():
    text=Path('.github/workflows/radar-smart-money.yml').read_text()
    first,second=text.split('  capture-tushare-relay:',1)
    assert 'relay-only:' in first and 'RELAY_ONLY: ${{ inputs.relay-only }}' in first
    assert "needs.capture-smart-money.outputs.run_relay == 'true'" in second
    assert 'artifact-ids:' in second and 'run-id:' in second and 'github-token: ${{ github.token }}' in second
    source_step=second.split('- name: Capture bounded Tushare Relay supplement',1)[1].split('- name: Retain',1)[0]
    assert 'GH_TOKEN' not in source_step and 'github-token' not in source_step
    assert 'HITHINK_FINANCE_API_KEY' not in second and 'FTSHARE_API_KEY' not in second
    assert '--control "$RUNNER_TEMP/smart-money-relay-control/control.json"' in source_step


def test_cli_replays_exact_prior_primary_but_records_current_execution_identity(tmp_path,monkeypatch):
    from test_smart_money_capture import captured as original_capture
    primary,raw=original_capture(tmp_path)
    ident={**primary["identity"],"run_id":primary["identity"]["run_id"]+1,"code_commit":"d"*40}
    env={"GITHUB_REPOSITORY":ident["repository"],"GITHUB_REF":ident["ref"],
         "GITHUB_WORKFLOW":"radar-smart-money","GITHUB_RUN_ATTEMPT":"1",
         "GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_SHA":ident["code_commit"],
         "GITHUB_RUN_ID":str(ident["run_id"])}
    for key,value in env.items():monkeypatch.setenv(key,value)
    control={"run_id":ident["run_id"],"code_commit":ident["code_commit"],
             "decision":"SKIP_RELAY_ONLY_REUSE_CAPTURE","relay_source":{
                 "run_id":primary["identity"]["run_id"],"head_sha":primary["identity"]["code_commit"],
                 "capture_hash":primary["capture_hash"]}}
    path=tmp_path/"control.json";path.write_text(json.dumps(control))
    real=relay.capture;calls=[]
    def caller(*args,**kwargs):
        calls.append(args[1]);kwargs.update(clock=lambda:NOW,
            request=lambda api,params,key,clock:response(api,params,clock))
        return real(*args,**kwargs)
    monkeypatch.setattr(relay,"capture",caller)
    monkeypatch.setattr(relay.relay,"now",lambda:NOW)
    assert relay.main(["--source-capture",str(tmp_path/"capture"),"--control",str(path),
                       "--output",str(tmp_path/"cli-result")])==0
    manifest=source.decode((tmp_path/"cli-result"/"capture.json").read_bytes())
    assert calls==[ident] and manifest["identity"]==ident
    assert manifest["source_capture"]["identity"]==primary["identity"]
    assert manifest["source_capture"]["capture_hash"]==primary["capture_hash"]
    control["relay_source"]["capture_hash"]="f"*64;path.write_text(json.dumps(control))
    with pytest.raises(ValueError,match="RELAY_PRIOR_CAPTURE_BINDING"):
        relay.main(["--source-capture",str(tmp_path/"capture"),"--control",str(path),
                    "--output",str(tmp_path/"wrong")])
    assert len(calls)==1 and not (tmp_path/"wrong").exists()


@pytest.mark.parametrize("started,allowed",[(0,True),(2,True),(3,False)])
def test_actual_preflight_relay_only_does_not_reset_or_reacquire_primary(tmp_path,monkeypatch,started,allowed):
    import base64
    from datetime import datetime
    col,base,old,job,art,obs=setup_reader(tmp_path)
    primary_package=reading.attach(col,base)
    rootraw=col.files["current-state.json"]
    state_ref=primary_package["research"]["smart_money"]["details"]["state"]
    state_raw=col.files[state_ref["read_path"]]
    rid=old["id"]+10;head="d"*40
    current={**old,"id":rid,"head_sha":head,"created_at":"2026-09-26T03:50:00Z"}
    peers=[{**old,"id":old["id"]-i-1,"head_sha":str(i+1)*40} for i in range(started)]
    namespace=control_module()["main"].__globals__
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return cls.fromisoformat("2026-09-26T04:00:00+00:00").astimezone(tz)
    monkeypatch.setitem(namespace,"datetime",Clock)
    seen=[]
    def get(path,params=None):
        seen.append(path)
        if path=="actions/workflows/ci.yml/runs":
            return {"workflow_runs":[{"id":10,"created_at":"2026-09-26T03:00:00Z","head_sha":head,
                "head_branch":"main","path":".github/workflows/ci.yml","run_attempt":1,
                "status":"completed","conclusion":"success"}]}
        if path=="git/matching-refs/heads/read-model/current-state":
            return [{"ref":"refs/heads/read-model/current-state","object":{"sha":"b"*40}}]
        if path=="contents/current-state.json":
            assert params=={"ref":"b"*40}
            return {"content":base64.b64encode(rootraw).decode(),"sha":reading.m.blob_sha(rootraw)}
        if path=="git/blobs/"+state_ref["git_blob"]:
            return {"content":base64.b64encode(state_raw).decode()}
        if path=="actions/workflows/radar-smart-money.yml/runs":
            return {"total_count":2+len(peers),"workflow_runs":[current,old,*peers]}
        if path=="git/ref/heads/main":return {"object":{"sha":head}}
        if path==f"actions/runs/{old['id']}/attempts/1/jobs":return {"total_count":1,"jobs":[job]}
        for peer in peers:
            if path==f"actions/runs/{peer['id']}/attempts/1/jobs":
                return {"total_count":1,"jobs":[{**job,"name":"capture-tushare-relay", "run_id":peer['id'],
                    "head_sha":peer["head_sha"],"status":"completed","started_at":peer["created_at"]}]}
        if path==f"actions/runs/{old['id']}":return old
        if path==f"actions/runs/{old['id']}/artifacts":return {"total_count":1,"artifacts":[art]}
        raise AssertionError("unexpected preflight access "+path)
    monkeypatch.setitem(namespace,"get",get)
    env={"GITHUB_REPOSITORY":"auguspp/decision-kernel","GITHUB_REF":"refs/heads/main",
         "GITHUB_WORKFLOW":"radar-smart-money","GITHUB_RUN_ATTEMPT":"1",
         "GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_SHA":head,"GITHUB_RUN_ID":str(rid),
         "EXPECTED_CODE":head,"RELAY_ONLY":"true","REPAIR_PENDING":"false",
         "RUNNER_TEMP":str(tmp_path),"GITHUB_OUTPUT":str(tmp_path/"out.txt")}
    for key,value in env.items():monkeypatch.setenv(key,value)
    namespace["main"]()
    output=dict(x.split('=',1) for x in (tmp_path/"out.txt").read_text().splitlines())
    assert output["run_capture"]=="false" and output["run_relay"]==str(allowed).lower()
    saved=json.loads((tmp_path/"smart-money-control"/"control.json").read_bytes())
    assert saved["relay_jobs_started_today"]==started
    assert saved["today_invocations"]==2+started
    assert saved["hithink_activity"]=="NOT_CHECKED_NO_CAPTURE"
    if allowed:
        assert output["relay_source_artifact_id"]==str(art["id"])
        assert saved["relay_source"]["capture_hash"]==obs["capture_hash"]
    else:
        assert saved["decision"]=="SKIP_RELAY_DAILY_ATTEMPT_BOUND"
        assert f"actions/runs/{old['id']}/artifacts" not in seen


def test_rehashed_manifest_cannot_authorize_calls_after_an_explicit_service_refusal(tmp_path):
    def request(api,params,key,clock):
        result=response(api,params,clock,status="AUTH_OR_ENTITLEMENT")
        result["attempts"][0]["http_status"]=403
        return result
    capture(tmp_path,request)
    saved=files(tmp_path);manifest=source.decode(saved["capture.json"])
    original=deepcopy(manifest["records"][0])
    original.update(index=1,spec=manifest["records"][1]["spec"])
    manifest["records"][1]=original
    manifest["capture_hash"]=relay._manifest_hash(manifest)
    saved["capture.json"]=source.encoded(manifest)
    with pytest.raises(ValueError,match="RELAY_REQUEST_AFTER_SERVICE_STOP"):
        relay.replay(saved,identity=IDENT,cutoff=NOW)
