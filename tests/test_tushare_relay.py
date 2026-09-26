import json
import pytest

from decision_kernel.runtime import tushare_relay as r

def body(*, code=0, error=None, msg="ok", fields=None, items=None):
    values = [[1]] if items is None else items
    value={"code":code,"msg":msg,"data":{"fields":fields or ["a"],"items":values},"count":len(values)}
    if error is not None:
        value["error"]=error
    return json.dumps(value,separators=(",",":")).encode()

def transport_result(status, raw, clock):
    return {"http_status":status,"raw":raw,"requested_at":clock(),"received_at":clock(),
            "headers":{"X-Request-ID":"x"}}

def test_queue_waits_exactly_thirty_seconds_once_then_succeeds():
    calls=[]; sleeps=[]
    times=iter([f"2026-09-26T01:00:0{i}+00:00" for i in range(6)])
    clock=lambda:next(times)
    def transport(api,params,key,clock):
        calls.append((api,params,key))
        if len(calls)==1:
            return transport_result(503,body(code=1,error="upstream_pool_exhausted",msg="busy"),clock)
        return transport_result(200,body(items=[[2]]),clock)
    out=r.request("hm_detail",{"trade_date":"20260924","limit":5},key="abcdefgh",
                  transport=transport,sleep=sleeps.append,clock=clock)
    assert out["status"]=="SUCCESS" and len(out["attempts"])==2
    assert sleeps==[30] and len(calls)==2
    assert r.rows(r.successful_body(out))==[{"a":2}]

def test_business_timeout_is_same_bounded_queue_class():
    calls=[]; sleeps=[]
    def clock(): return "2026-09-26T01:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        raw=body(code=1,msg="timeout") if len(calls)==1 else body(items=[])
        return transport_result(200,raw,clock)
    out=r.request("report_rc",{"report_date":"20260924"},key="abcdefgh",
                  transport=transport,sleep=sleeps.append,clock=clock)
    assert out["status"]=="SUCCESS" and sleeps==[30] and len(calls)==2
    assert r.rows(r.successful_body(out))==[]

def test_source_unavailable_does_not_retry():
    calls=[]; sleeps=[]
    def clock(): return "2026-09-26T01:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(503,body(code=1,error="data_source_unavailable",msg="disabled"),clock)
    out=r.request("hm_detail",{"trade_date":"20260924"},key="abcdefgh",
                  transport=transport,sleep=sleeps.append,clock=clock)
    assert out["status"]=="SOURCE_UNAVAILABLE" and len(calls)==1 and not sleeps

def test_rate_limit_does_not_retry_or_change_host():
    calls=[]
    def clock(): return "2026-09-26T01:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append((api,params))
        return transport_result(429,body(code=1,error="rate_limited",msg="wait"),clock)
    out=r.request("report_rc",{"report_date":"20260924"},key="abcdefgh",transport=transport,
                  sleep=lambda _:pytest.fail("no sleep"),clock=clock)
    assert out["status"]=="RATE_LIMIT" and len(calls)==1
    assert r.PRO=="https://pcd.mobcvb.cn/tushare/pro"

def test_malformed_json_is_retained_as_source_gap_not_retry():
    def clock(): return "2026-09-26T01:00:00+00:00"
    out=r.request("report_rc",{"report_date":"20260924"},key="abcdefgh",
        transport=lambda api,params,key,clock: transport_result(200,b"not-json",clock),
        sleep=lambda _:pytest.fail("no retry"),clock=clock)
    assert out["status"]=="MALFORMED_RESPONSE"
    assert out["attempts"][0]["business_error"]=="JSON_INVALID"

@pytest.mark.parametrize("api,params",[("unknown",{}),("hm_list",{"__probe":1})])
def test_unreviewed_api_or_probe_never_reaches_transport(api,params):
    with pytest.raises(ValueError):
        r.request(api,params,key="abcdefgh",transport=lambda *a,**k:pytest.fail("network"))

def test_rows_preserve_relay_fields_without_inventing_source():
    value={"code":0,"data":{"fields":["ts_code","source","value"],
           "items":[["000001.SZ","relay-x",1]]},"count":1}
    assert r.rows(value)==[{"ts_code":"000001.SZ","source":"relay-x","value":1}]

def test_duplicate_json_keys_rejected():
    with pytest.raises(ValueError):
        r.decode(b'{"code":0,"code":1}')
