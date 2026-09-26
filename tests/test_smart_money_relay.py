import json

from decision_kernel.runtime import smart_money_relay as m
from decision_kernel.runtime import tushare_relay as relay

IDENT={"repository":"auguspp/decision-kernel","workflow":".github/workflows/radar-smart-money.yml",
       "ref":"refs/heads/main","event":"workflow_dispatch","code_commit":"a"*40,"run_id":123,"attempt":1}

def response(api,params,clock,*,status="SUCCESS",rows=None,error=None):
    values=[[api,1]] if rows is None else rows
    raw=json.dumps({"code":0 if status=="SUCCESS" else 1,
                    "error":error,"msg":"ok" if status=="SUCCESS" else "busy",
                    "data":{"fields":["api","value"],"items":values},"count":len(values)},
                   separators=(",",":")).encode()
    return {"api":api,"params":{k:str(v) for k,v in params.items()},"status":status,"attempts":[
        {"attempt":1,"http_status":200 if status=="SUCCESS" else 503,"raw":raw,
         "requested_at":clock(),"received_at":clock(),"headers":{"X-Request-ID":"r"},
         "classification":status,"business_code":0 if status=="SUCCESS" else 1,
         "business_error":None if status=="SUCCESS" else error,
         "business_msg":"ok" if status=="SUCCESS" else "busy"}]}

def test_capture_replay_retains_independent_relay_rows(tmp_path,monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    times=iter([f"2026-09-26T01:00:{i:02d}+00:00" for i in range(40)])
    clock=lambda:next(times)
    def request(api,params,key,clock):
        return response(api,params,clock)
    out=tmp_path/"relay"
    result=m.capture(out,IDENT,"2026-09-24",request=request,clock=clock)
    assert result["status"]=="READY" and result["market_session"]=="2026-09-24"
    assert set(result["families"])==set(m.APIS)
    assert all(v["row_count"]==1 for v in result["families"].values())
    files={p.name:p.read_bytes() for p in out.iterdir() if p.is_file()}
    replay=m.replay(files,identity=IDENT,cutoff="2026-09-26T02:00:00+00:00")
    assert replay["capture_hash"]==result["capture_hash"]
    assert replay["source_role"].startswith("SECONDARY_")

def test_one_queue_gap_does_not_erase_other_sources(tmp_path,monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    def clock(): return "2026-09-26T01:00:00+00:00"
    def request(api,params,key,clock):
        if api=="hm_detail":
            return response(api,params,clock,status="TEMPORARY_QUEUE",rows=[],
                            error="upstream_pool_exhausted")
        return response(api,params,clock)
    result=m.capture(tmp_path/"relay",IDENT,"2026-09-24",request=request,clock=clock)
    assert result["status"]=="PARTIAL_WITH_EXPLICIT_GAPS"
    assert result["families"]["hm_detail"]["row_count"]==0
    assert result["families"]["hm_list"]["row_count"]==1
    assert result["unresolved"]==[{"api":"hm_detail","status":"TEMPORARY_QUEUE",
                                  "business_error":"upstream_pool_exhausted"}]

def test_report_rc_qualified_empty_is_not_a_gap(tmp_path,monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    def clock(): return "2026-09-26T01:00:00+00:00"
    def request(api,params,key,clock):
        return response(api,params,clock,rows=[] if api=="report_rc" else None)
    result=m.capture(tmp_path/"relay",IDENT,"2026-09-24",request=request,clock=clock)
    assert result["families"]["report_rc"]["status"]=="SUCCESS"
    assert result["families"]["report_rc"]["row_count"]==0
    assert not result["unresolved"]

def test_no_completed_primary_session_stays_explicit(tmp_path,monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    def clock(): return "2026-09-26T01:00:00+00:00"
    result=m.capture(tmp_path/"relay",IDENT,None,request=lambda *a,**k:None,clock=clock)
    assert result["status"]=="NO_COMPLETED_SESSION" and result["families"]=={}

def test_missing_secret_is_retained_not_fake_empty(tmp_path,monkeypatch):
    monkeypatch.delenv(relay.SECRET_ENV,raising=False)
    def clock(): return "2026-09-26T01:00:00+00:00"
    result=m.capture(tmp_path/"relay",IDENT,"2026-09-24",request=lambda *a,**k:None,clock=clock)
    assert result["status"]=="UNAVAILABLE_NOT_QUIET"
    assert all(v["status"]=="CREDENTIAL_UNAVAILABLE" for v in result["families"].values())

def test_plan_uses_primary_session_and_never_probe_sample():
    plan=m.plan("2026-09-24")
    assert plan[0]["api"]=="hm_list" and plan[0]["params"]["__probe"]=="0"
    for item in plan[1:]:
        assert item["params"].get("trade_date",item["params"].get("report_date"))=="20260924"
