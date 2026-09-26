import json
import socket
import pytest

from decision_kernel.runtime import smart_money_relay_contract as contract
from decision_kernel.runtime import smart_money_sources as s

from decision_kernel.runtime import smart_money_relay as m
from decision_kernel.runtime import tushare_relay as relay

IDENT={"repository":"auguspp/decision-kernel","workflow":".github/workflows/radar-smart-money.yml",
       "ref":"refs/heads/main","event":"workflow_dispatch","code_commit":"a"*40,"run_id":123,"attempt":1}

def sample_body(api, params, rows=None):
    day = params.get("trade_date", params.get("report_date", "20260924"))
    examples = {
        "hm_list": {"name": "sample-label", "orgs": "sample-seat"},
        "hm_detail": {"trade_date": day, "ts_code": "600000.SH", "hm_name": "sample-label",
                      "hm_orgs": "sample-seat", "net_amount": 1},
        "report_rc": {"report_date": day, "ts_code": "600000.SH", "org_name": "sample-broker",
                      "quarter": "2027Q4", "eps": 1},
        "top_list": {"trade_date": day, "ts_code": "600000.SH", "reason": "sample-reason"},
        "top_inst": {"trade_date": day, "ts_code": "600000.SH", "exalter": "sample-seat",
                     "side": "0", "reason": "sample-reason"},
    }
    example = examples[api]
    values = [list(example.values())] if rows is None else rows
    return {"code": 0, "msg": "ok", "data": {"fields": list(example), "items": values},
            "count": len(values)}

def response(api,params,clock,*,status="SUCCESS",rows=None,error=None):
    body = sample_body(api, params, rows)
    body.update(code=0 if status=="SUCCESS" else 1, error=error,
                msg="ok" if status=="SUCCESS" else "busy")
    raw=json.dumps(body,separators=(",",":")).encode()
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


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("unexpected source request")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def qualified(api="hm_detail", change=None):
    spec = next(x for x in m.plan("2026-09-24") if x["api"] == api)
    body = sample_body(api, spec["params"])
    if change:
        change(body)
    return contract.qualify(s.decode(json.dumps(body).encode()), spec,
                            received_at="2026-09-26T00:00:00Z")


@pytest.mark.parametrize("api", m.APIS)
def test_actual_interface_shape_qualifies_without_claiming_market_completeness(api):
    result = qualified(api)
    assert result["qualified_row_indexes"] == [0] and not result["issues"]
    assert not result["coverage"]["complete_market"]
    assert result["qualification"] == "BOUNDED_PAGE_QUALIFIED"


@pytest.mark.parametrize("value", [None, False, True, "0", 0.0])
def test_business_success_is_not_truthiness_or_missing_code(value):
    with pytest.raises(s.SourceError, match="RELAY_BUSINESS_NOT_SUCCESS"):
        qualified(change=lambda body: body.update(code=value))


@pytest.mark.parametrize("extra", [{"ok":False}, {"ok":1}, {"error":"upstream_error"}])
def test_business_error_cannot_hide_behind_code_zero(extra):
    with pytest.raises(s.SourceError, match="RELAY_BUSINESS_NOT_SUCCESS"):
        qualified(change=lambda body: body.update(extra))


def test_duplicate_column_cannot_silently_replace_security():
    def damage(body):
        body["data"]["fields"].append("ts_code")
        body["data"]["items"][0].append("000001.SZ")
    with pytest.raises(s.SourceError, match="RELAY_DUPLICATE_FIELDS"):
        qualified(change=damage)


def test_decimal_and_provider_metadata_are_preserved_without_a_new_identity():
    spec = m.plan("2026-09-24")[1]
    body = sample_body("hm_detail", spec["params"])
    body.update(provider="relay-envelope-provider")
    body["data"]["source"] = {"name": "upstream-claim"}
    body["data"]["fields"] += ["source", "future_extra"]
    body["data"]["items"][0] += ["row-origin", None]
    raw=json.dumps(body,separators=(",",":")).encode().replace(
        b',1,"row-origin"', b',1234567890123.1234567890123456789,"row-origin"')
    assert b"1234567890123.1234567890123456789" in raw
    exact=s.decode(raw)
    result=contract.qualify(exact,spec,received_at="2026-09-26T00:00:00Z")
    assert result["rows"][0]["net_amount"]=="1234567890123.1234567890123456789"
    assert result["rows"][0]["source"]=="row-origin" and result["rows"][0]["future_extra"] is None
    assert result["source_claims"][1]["value"]=={"name":"upstream-claim"}
    assert result["source_fields_present"]==["source"]
    assert "VENDOR_LABELS" in result["identity_limit"]


@pytest.mark.parametrize("api,boundary", [("hm_list",1000),("hm_detail",2000),("report_rc",3000)])
def test_official_cap_not_requested_5000_defines_truncation_warning(api,boundary):
    def change(body):
        body["data"]["items"] *= boundary
        body["count"]=boundary
    result=qualified(api,change)
    assert result["row_count"]==boundary
    assert any(x["code"]=="POSSIBLE_TRUNCATION" for x in result["issues"])


def test_larger_count_does_not_certify_saved_single_page():
    result=qualified(change=lambda b:b.update(count=2))
    assert any(x["code"]=="COUNT_EXCEEDS_SAVED_ROWS" for x in result["issues"])


@pytest.mark.parametrize("day",["20260923","20270924","202609240000","bad",None])
def test_out_of_scope_date_retains_row_but_does_not_qualify_it(day):
    result=qualified(change=lambda b:b["data"]["items"][0].__setitem__(0,day))
    assert result["rows"][0]["trade_date"]==day and result["qualified_row_count"]==0
    assert result["row_gaps"][0]["row_index"]==0


def test_forecast_target_year_is_not_disclosure_day():
    result=qualified("report_rc")
    assert result["rows"][0]["quarter"]=="2027Q4" and not result["issues"]


def test_missing_fields_and_invalid_security_keep_explicit_gaps():
    result=qualified(change=lambda b:b["data"]["fields"].__setitem__(1,"unknown_code"))
    assert result["qualified_row_count"]==0
    assert result["issues"][0]["fields"]==["ts_code"]
    result=qualified(change=lambda b:b["data"]["items"][0].__setitem__(1,"600000"))
    assert result["row_gaps"][0]["codes"]==["SECURITY_IDENTITY_UNQUALIFIED"]


def test_empty_response_is_not_absence_evidence():
    def empty(body):
        body["data"]["items"]=[];body["count"]=0
    result=qualified("report_rc",empty)
    assert result["coverage"]["status"]=="EMPTY_RESPONSE_NOT_NO_ACTIVITY"
    assert result["qualified_row_count"]==0 and not result["issues"]


def test_replay_isolates_bad_family_and_roundtrips_exact_numeric_original(tmp_path,monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    clock=lambda:"2026-09-26T01:00:00Z"
    original=[]
    def request(api,params,key,clock):
        result=response(api,params,clock)
        body=json.loads(result["attempts"][0]["raw"])
        if api=="hm_list":
            body["data"]["fields"]=["name","name"]
        raw=json.dumps(body,separators=(",",":")).encode()
        if api=="hm_detail":
            raw=raw.replace(b'"sample-seat",1]',b'"sample-seat",12.34567890123456789]')
            original.append(raw)
        result["attempts"][0]["raw"]=raw
        return result
    out=tmp_path/"source"
    result=m.capture(out,IDENT,"2026-09-24",request=request,clock=clock)
    assert result["status"]=="PARTIAL_WITH_EXPLICIT_GAPS"
    assert result["families"]["hm_list"]["interpretation_error"]=="RELAY_DUPLICATE_FIELDS"
    assert result["families"]["hm_detail"]["rows"][0]["net_amount"]=="12.34567890123456789"
    assert (out/"raw-01-1.json").read_bytes()==original[0]
    files={p.name:p.read_bytes() for p in out.iterdir()}
    assert m.replay(files,identity=IDENT,cutoff=clock())==result
    assert "全市场" in m.render(result)


@pytest.mark.parametrize("side", ["", None, "2", True])
def test_missing_side_keeps_useful_identity_date_but_never_infers_buy_side(side):
    result=qualified("top_inst",lambda b:b["data"]["items"][0].__setitem__(3,side))
    assert result["qualified_row_indexes"]==[0]
    assert result["rows"][0]["side"]==side
    assert result["field_gaps"]==[{"row_index":0,"field":"side","code":"SIDE_NOT_ESTABLISHED"}]
    assert result["qualification"]=="WITH_EXPLICIT_GAPS"


def test_wrong_api_response_is_not_a_successful_table_for_requested_api():
    with pytest.raises(s.SourceError,match="RELAY_RESPONSE_API_MISMATCH"):
        qualified(change=lambda body:body.update(api_name="daily"))


def test_tiny_raw_exponent_cannot_expand_into_unbounded_output():
    spec=m.plan("2026-09-24")[1]
    raw=json.dumps(sample_body("hm_detail",spec["params"]),separators=(",",":")).encode()
    raw=raw.replace(b'"sample-seat",1]',b'"sample-seat",1e1000000]')
    with pytest.raises(s.SourceError,match="RELAY_DECIMAL_EXPANSION_BOUND"):
        contract.qualify(s.decode(raw),spec,received_at="2026-09-26T00:00:00Z")
