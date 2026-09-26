"""Synthetic optional-reader faults; no network or market acceptance."""
from copy import deepcopy
import socket
import pytest
import io
import json
import zipfile
from hashlib import sha256

from decision_kernel.runtime import smart_money_reading as reading
from decision_kernel.runtime import smart_money_relay as relay_capture
from decision_kernel.runtime import tushare_relay as relay
from test_smart_money_capture import setup_reader
from test_smart_money_reading import preserve_as_previous
from test_smart_money_relay import sample_body

def relay_result(api,params,clock):
    raw=json.dumps(sample_body(api,params),separators=(",",":")).encode()
    return {"api":api,"params":{k:str(v) for k,v in params.items()},"status":"SUCCESS","attempts":[
        {"attempt":1,"http_status":200,"raw":raw,"requested_at":clock(),"received_at":clock(),
         "headers":{"X-Request-ID":"r"},"classification":"SUCCESS","business_code":0,
         "business_error":None,"business_msg":"ok"}]}

def with_relay(tmp_path,monkeypatch):
    col,base,run,job,artifact,primary=setup_reader(tmp_path)
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    run["updated_at"]="2026-09-26T02:11:00Z"
    out=tmp_path/"relay-source"
    times=iter([f"2026-09-26T02:10:{i:02d}+00:00" for i in range(40)])
    relay_capture.capture(out,primary["identity"],"2026-09-24",
                          request=lambda api,params,key,clock:relay_result(api,params,clock),
                          clock=lambda:next(times))
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            if p.is_file():
                z.writestr(p.name,p.read_bytes())
    relay_raw=stream.getvalue()
    relay_art={"id":901,"name":f"smart-money-relay-{run['id']}-1",
               "size_in_bytes":len(relay_raw),"digest":"sha256:"+sha256(relay_raw).hexdigest(),
               "expired":False,"workflow_run":{"id":run["id"],"head_sha":run["head_sha"]}}
    jobs_key=f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100"
    relay_job={"name":"capture-tushare-relay","id":43,"head_sha":run["head_sha"],
               "run_id":run["id"],"run_attempt":1,"status":"completed","conclusion":"success"}
    col.api.responses[jobs_key]["jobs"].append(relay_job)
    col.api.responses[jobs_key]["total_count"]+=1
    key=f"actions/runs/{run['id']}/artifacts?per_page=100"
    col.api.responses[key]["artifacts"].append(relay_art)
    col.api.responses[key]["total_count"]+=1
    original=col.api.raw_archive
    def archive(selected):
        col.api.calls+=1
        col.api.reads.append("ARCHIVE")
        return relay_raw if selected["id"]==901 else original
    col.api.archive=archive
    return col,base,run,job,artifact,primary,relay_job,relay_art

def test_normal_reading_retains_relay_supplement_without_replacing_primary(tmp_path,monkeypatch):
    col,base,run,job,artifact,primary,*_=with_relay(tmp_path,monkeypatch)
    result=reading.attach(col,base)
    sm=result["research"]["smart_money"]
    assert sm["status"]=="READY" and sm["relay_status"]=="READY"
    assert sm["relay_retained_status"]=="READY"
    assert "relay" in sm["details"]
    saved=json.loads(col.files["details/radar/smart-money/relay.json"])
    assert saved["reading_relation"]=="CURRENT_SOURCE_RUN"
    assert saved["families"]["hm_list"]["row_count"]==1
    text=col.files["details/radar/smart-money.md"].decode()
    assert "Tushare Relay 补充来源" in text
    assert primary["capture_hash"]==sm["capture_hash"]

def test_legacy_capture_without_relay_remains_readable(tmp_path):
    col,base,*_=setup_reader(tmp_path)
    result=reading.attach(col,base)
    sm=result["research"]["smart_money"]
    assert sm["status"]=="READY"
    assert sm["relay_status"]=="NOT_PRESENT_LEGACY_OR_NOT_RUN"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args,**kwargs):
        raise AssertionError("unexpected network in synthetic optional-reader test")
    monkeypatch.setattr(socket.socket,"connect",reject)
    monkeypatch.setattr(socket,"getaddrinfo",reject)


def primary_intact(col,base,result,primary):
    sm=result["research"]["smart_money"]
    assert sm["status"]=="READY"
    assert sm["capture_hash"]==primary["capture_hash"]
    assert result["lanes"]==base["lanes"]
    for key in ("history","state","overview","browser","markdown"):
        ref=sm["details"][key]
        assert reading.m.blob_sha(col.files[ref["read_path"]])==ref["git_blob"]
    reading.m.validate_read_package(result)
    assert json.loads(col.files["current-state.json"])==result
    return sm


@pytest.mark.parametrize("damage",["digest","expired","job_head","job_attempt","duplicate_job",
                                   "duplicate_artifact","no_job","wrong_calendar","late_capture"])
def test_bad_current_supplement_never_suppresses_primary(tmp_path,monkeypatch,damage):
    col,base,run,job,art,primary,rjob,rart=with_relay(tmp_path,monkeypatch)
    jobs=col.api.responses[f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100"]
    arts=col.api.responses[f"actions/runs/{run['id']}/artifacts?per_page=100"]
    if damage=="digest":rart["digest"]="sha256:"+"0"*64
    elif damage=="expired":rart["expired"]=True
    elif damage=="job_head":rjob["head_sha"]="f"*40
    elif damage=="job_attempt":rjob["run_attempt"]=2
    elif damage=="duplicate_job":jobs["jobs"].append(deepcopy(rjob));jobs["total_count"]+=1
    elif damage=="duplicate_artifact":arts["artifacts"].append(deepcopy(rart));arts["total_count"]+=1
    elif damage=="no_job":jobs["jobs"].remove(rjob);jobs["total_count"]-=1
    elif damage=="late_capture":run["updated_at"]="2026-09-26T02:05:00Z"
    else:
        real=reading.read_relay
        def wrong(*a,**kw):
            result=real(*a,**kw);result["result"]["market_session"]="2026-09-23";return result
        monkeypatch.setattr(reading,"read_relay",wrong)
    result=reading.attach(col,base)
    sm=primary_intact(col,base,result,primary)
    assert sm["relay_status"]=="CURRENT_RELAY_READING_GAP"
    assert "relay" not in sm["details"]
    assert 900 in col.archive_cache and 901 not in col.archive_cache


def test_primary_retained_before_optional_archive_and_counters_not_rolled_back(tmp_path,monkeypatch):
    col,base,run,job,art,primary,rjob,rart=with_relay(tmp_path,monkeypatch)
    real=col.api.archive;seen=[]
    def archive(selected):
        seen.append(selected["id"])
        if selected["id"]==901:
            saved=json.loads(col.files["current-state.json"])["research"]["smart_money"]
            assert saved["capture_hash"]==primary["capture_hash"]
            assert "details" in saved
            col.api.calls+=1
            col.files["sources/artifacts/partial.zip"]=b"uncommitted"
            raise OSError("synthetic archive failure")
        return real(selected)
    col.api.archive=archive
    used=col.api.calls
    sm=primary_intact(col,base,reading.attach(col,base),primary)
    assert seen==[900,901] and col.api.calls>used
    assert "sources/artifacts/partial.zip" not in col.files
    assert sm["relay_status"]=="CURRENT_RELAY_READING_GAP"


@pytest.mark.parametrize("damage",["missing","hash","shape","future","authority"])
def test_broken_prior_supplement_does_not_destroy_primary_history(tmp_path,monkeypatch,damage):
    col,base,run,job,art,primary,*_=with_relay(tmp_path,monkeypatch)
    first=reading.attach(col,base);preserve_as_previous(col,first)
    col.previous=deepcopy(first)
    refs=col.previous["research"]["smart_money"]["details"]
    key="git/blobs/"+refs["relay"]["git_blob"]
    if damage=="missing":del col.api.responses[key]
    elif damage=="hash":col.api.responses[key]["content"]="Y29ycnVwdA=="
    else:
        import base64
        value=json.loads(base64.b64decode(col.api.responses[key]["content"]))
        if damage=="shape":value["families"]=None
        elif damage=="future":value["cutoff"]="2027-01-01T00:00:00Z"
        else:value["automatic_full"]=True
        raw=reading.m.json_bytes(value);sha=reading.m.blob_sha(raw)
        refs["relay"].update(git_blob=sha,bytes=len(raw),sha256=reading.m.sha256(raw))
        col.api.responses["git/blobs/"+sha]={"sha":sha,"encoding":"base64","content":base64.b64encode(raw).decode()}
    col.previous["reading_hash"]=reading.canonical_hash({k:v for k,v in col.previous.items() if k!="reading_hash"})
    col.api.responses[reading.QUERY]={"total_count":0,"workflow_runs":[]}
    result=reading.attach(col,first);sm=result["research"]["smart_money"]
    assert sm["status"]=="NOT_RUN" and sm["uses_prior_observation"]
    assert sm["capture_hash"]==primary["capture_hash"] and "history" in sm["details"]
    assert sm["relay_previous_status"]=="PREVIOUS_RELAY_READING_GAP"
    assert sm["relay_status"]=="PREVIOUS_RELAY_READING_GAP"
    assert sm["relay_prior_retained_entry"]=={"commit":"b"*40,"reference":refs["relay"]}
    overview=json.loads(col.files[sm["details"]["overview"]["read_path"]])
    assert "relay_supplement" not in overview
    assert "relay" not in sm["details"]
    reading.m.validate_read_package(result)


def test_new_current_supplement_does_not_read_or_inherit_broken_prior(tmp_path,monkeypatch):
    col,base,run,job,art,primary,*_=with_relay(tmp_path,monkeypatch)
    first=reading.attach(col,base);refs=preserve_as_previous(col,first)
    key="git/blobs/"+refs["relay"]["git_blob"];del col.api.responses[key]
    col.api.reads.clear()
    result=reading.attach(col,first);sm=primary_intact(col,first,result,primary)
    assert sm["relay_status"]=="READY" and key not in col.api.reads
    assert sm["relay_prior_retained_entry"] is None
    assert sm["relay_reading_diagnostics"]=={}


def test_current_failure_keeps_previous_supplement_with_original_cutoff(tmp_path,monkeypatch):
    col,base,run,job,art,primary,rjob,rart=with_relay(tmp_path,monkeypatch)
    first=reading.attach(col,base)
    old=json.loads(col.files[first["research"]["smart_money"]["details"]["relay"]["read_path"]])
    preserve_as_previous(col,first);rart["digest"]="sha256:"+"0"*64
    result=reading.attach(col,first);sm=primary_intact(col,first,result,primary)
    assert sm["relay_status"]=="CURRENT_RELAY_READING_GAP" and sm["relay_retained_status"]=="READY"
    saved=json.loads(col.files[sm["details"]["relay"]["read_path"]])
    assert saved["cutoff"]==old["cutoff"] and saved["capture_hash"]==old["capture_hash"]
    assert saved["reading_relation"]=="PRIOR_RETAINED_NO_CURRENT_SUPPLEMENT"
    assert saved["current_run_status"]=="CURRENT_RELAY_READING_GAP"


def test_prior_relay_locator_survives_more_than_one_missing_publication(tmp_path,monkeypatch):
    col,base,run,job,art,primary,*_=with_relay(tmp_path,monkeypatch)
    first=reading.attach(col,base);refs=preserve_as_previous(col,first)
    key="git/blobs/"+refs["relay"]["git_blob"];original=col.api.responses.pop(key)
    col.api.responses[reading.QUERY]={"total_count":0,"workflow_runs":[]}
    second=reading.attach(col,first);locator=second["research"]["smart_money"]["relay_prior_retained_entry"]
    preserve_as_previous(col,second);col.previous_commit="c"*40
    third=reading.attach(col,second)
    assert third["research"]["smart_money"]["relay_prior_retained_entry"]==locator
    preserve_as_previous(col,third);col.previous_commit="d"*40
    col.api.responses[key]=original
    fourth=reading.attach(col,third)["research"]["smart_money"]
    assert fourth["relay_previous_status"]=="EXACT_PREVIOUS_SUPPLEMENT"
    assert fourth["relay_retained_status"]=="READY" and fourth["relay_prior_retained_entry"] is None


@pytest.mark.parametrize("conclusion",["failure","cancelled","timed_out"])
def test_failed_supplement_checkpoint_not_promoted_to_success(tmp_path,monkeypatch,conclusion):
    col,base,run,job,art,primary,rjob,rart=with_relay(tmp_path,monkeypatch)
    rjob["conclusion"]=conclusion;run["conclusion"]=conclusion
    result=reading.attach(col,base);sm=primary_intact(col,base,result,primary)
    assert sm["relay_status"]=="PARTIAL_FAILED_EXECUTION"
    value=json.loads(col.files[sm["details"]["relay"]["read_path"]])
    assert any(x["api"]=="execution" for x in value["unresolved"])


@pytest.mark.parametrize("fault",["render","retain","bytes","api_budget"])
def test_optional_publication_failures_preserve_fully_valid_primary(tmp_path,monkeypatch,fault):
    col,base,run,job,art,primary,*_=with_relay(tmp_path,monkeypatch)
    if fault=="render":
        def reject(*a,**k):raise ValueError("synthetic rendering failure")
        monkeypatch.setattr(relay_capture,"render",reject)
    elif fault=="retain":
        real=col.retain
        def retain(path,raw):
            if path.endswith("relay.json"):raise ValueError("synthetic optional retention failure")
            return real(path,raw)
        monkeypatch.setattr(col,"retain",retain)
    elif fault=="bytes":
        real=col.api.archive
        def archive(selected):
            if selected["id"]==901:
                monkeypatch.setattr(reading.delivery,"MAX_RETAINED_OUTPUT",sum(map(len,col.files.values()))+1000)
            return real(selected)
        col.api.archive=archive
    else:
        real=reading.current_relay
        def budget(*a,**k):
            from decision_kernel.runtime.read_blob_reuse import pending_blob_writes
            col.api.max_calls=col.api.calls+pending_blob_writes(col.api,col.files)+5
            return real(*a,**k)
        monkeypatch.setattr(reading,"current_relay",budget)
    result=reading.attach(col,base);sm=primary_intact(col,base,result,primary)
    assert sm["relay_status"] in {"CURRENT_RELAY_READING_GAP","OPTIONAL_RELAY_PUBLICATION_GAP"}
    assert "relay" not in sm["details"] and 901 not in col.archive_cache


def test_no_room_even_for_optional_diagnostic_still_preserves_valid_primary(tmp_path,monkeypatch):
    col,base,run,job,art,primary,*_=with_relay(tmp_path,monkeypatch)
    real=col.api.archive
    def archive(selected):
        if selected["id"]==901:
            monkeypatch.setattr(reading.delivery,"MAX_RETAINED_OUTPUT",sum(map(len,col.files.values())))
        return real(selected)
    col.api.archive=archive
    result=reading.attach(col,base);sm=primary_intact(col,base,result,primary)
    assert sm["relay_status"]=="OPTIONAL_RELAY_NOT_CHECKED" and "relay" not in sm["details"]
    assert 901 not in col.archive_cache


@pytest.mark.parametrize("conclusion,expected",[("success","JOB_SUCCEEDED_ARTIFACT_MISSING"),
    ("skipped","NOT_RUN_WITHOUT_PRIMARY_CAPTURE"),("failure","JOB_FAILURE")])
def test_no_optional_artifact_remains_explicit_not_zero_activity(tmp_path,monkeypatch,conclusion,expected):
    col,base,run,job,art,primary,rjob,rart=with_relay(tmp_path,monkeypatch)
    arts=col.api.responses[f"actions/runs/{run['id']}/artifacts?per_page=100"]
    arts["artifacts"].remove(rart);arts["total_count"]-=1;rjob["conclusion"]=conclusion
    sm=primary_intact(col,base,reading.attach(col,base),primary)
    assert sm["relay_status"]==expected and "relay" not in sm["details"]