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

@pytest.mark.parametrize("status,raw", [(502,b""),(503,b"<html>gateway</html>"),(504,b"")])
def test_non_json_gateway_keeps_http_failure_and_existing_bounded_retry(status, raw):
    calls=[]; sleeps=[]
    def clock(): return "2026-10-03T10:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(status,raw,clock)
    out=r.request("trade_cal",{"exchange":"SSE"},key="abcdefgh",
                  transport=transport,sleep=sleeps.append,clock=clock)
    assert out["status"]=="TEMPORARY_QUEUE" and len(calls)==2 and sleeps==[30]
    assert all(a["raw"]==raw and a["http_status"]==status for a in out["attempts"])
    assert r.successful_body(out) is None

@pytest.mark.parametrize("status,expected", [(401,"AUTH_OR_ENTITLEMENT"),
    (403,"AUTH_OR_ENTITLEMENT"),(429,"RATE_LIMIT"),(400,"INVALID_PARAMS"),
    (200,"MALFORMED_RESPONSE")])
def test_empty_denial_or_invalid_success_never_retries_or_becomes_success(status, expected):
    def clock(): return "2026-10-03T10:00:00+00:00"
    out=r.request("daily",{"trade_date":"20260930"},key="abcdefgh",
        transport=lambda api,params,key,clock:transport_result(status,b"",clock),
        sleep=lambda _:pytest.fail("no retry"),clock=clock)
    assert out["status"]==expected and len(out["attempts"])==1
    assert out["attempts"][0]["raw"]==b"" and r.successful_body(out) is None


def test_real_requests_stream_timeout_uses_original_bounded_retry(monkeypatch):
    from urllib3.exceptions import ReadTimeoutError
    calls=[]; sleeps=[]; sessions=[]
    times=iter([f"2026-10-03T12:00:{i:02}+00:00" for i in range(12)])
    def clock(): return next(times)
    class Raw:
        def stream(self, *args, **kwargs):
            raise ReadTimeoutError(None, "/redacted", "sensitive text must not be saved")
            yield
    class Session:
        trust_env=True
        def __init__(self): sessions.append(self); self.closed=False
        def get(self, url, **kwargs):
            calls.append(kwargs)
            response=r.requests.Response()
            response.status_code=200
            response.url=r.requests.Request("GET",url,params=kwargs["params"]).prepare().url
            if len(calls)==1:
                response.raw=Raw()
                response.close=lambda:None
            else:
                response._content=body()
                response._content_consumed=True
            response.headers={}
            return response
        def close(self): self.closed=True
    monkeypatch.setattr(r.requests,"Session",Session)
    out=r.request("daily",{"trade_date":"20260930"},key="abcdefgh",sleep=sleeps.append,clock=clock)
    assert out["status"]=="SUCCESS" and len(calls)==2 and sleeps==[30]
    first=out["attempts"][0]
    assert first["classification"]=="TEMPORARY_QUEUE"
    assert first["transport_error_type"]=="STREAM_READ_TIMEOUT"
    assert first["raw"] is None and first["requested_at"]<first["received_at"]
    assert "sensitive" not in json.dumps(out,default=lambda value:"<bytes>")
    assert all(s.closed and s.trust_env is False for s in sessions)
    assert all(c["timeout"]==(10,30) and c["allow_redirects"] is False for c in calls)


def test_plain_connection_error_does_not_gain_timeout_retry():
    calls=[]
    times=iter(["2026-10-03T12:00:00+00:00","2026-10-03T12:00:07+00:00"])
    def transport(*args,**kwargs):
        calls.append(1)
        raise r.requests.ConnectionError("private host information")
    out=r.request("daily",{},key="abcdefgh",transport=transport,
                  sleep=lambda _:pytest.fail("no retry"),clock=lambda:next(times))
    assert len(calls)==1 and out["status"]=="TRANSPORT_CONNECTION"
    assert out["attempts"][0]["transport_error_type"]=="CONNECTION_ERROR"
    assert out["attempts"][0]["requested_at"]=="2026-10-03T12:00:00+00:00"
    assert out["attempts"][0]["received_at"]=="2026-10-03T12:00:07+00:00"
    assert "private" not in json.dumps(out)


def test_daily_opt_in_backoff_is_three_attempts_and_preserves_all_failures():
    calls=[]; sleeps=[]
    def clock():return "2026-10-03T14:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(503,body(code=1,error="upstream_pool_exhausted"),clock)
    out=r.request("daily",{},key="abcdefgh",transport=transport,sleep=sleeps.append,
                  clock=clock,retry_waits=(30,90))
    assert len(calls)==3 and sleeps==[30,90] and out["status"]=="TEMPORARY_QUEUE"
    assert len(out["attempts"])==3 and all(a["http_status"]==503 and a["raw"] for a in out["attempts"])
    assert r.successful_body(out) is None


def test_daily_backoff_can_recover_on_last_attempt_without_hiding_denial():
    calls=[]; sleeps=[]
    def clock():return "2026-10-03T14:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(503,body(code=1,error="upstream_pool_exhausted"),clock) if len(calls)<3 else transport_result(200,body(),clock)
    out=r.request("daily",{},key="abcdefgh",transport=transport,sleep=sleeps.append,
                  clock=clock,retry_waits=(30,90))
    assert out["status"]=="SUCCESS" and len(calls)==3 and sleeps==[30,90]
    assert r.rows(r.successful_body(out))==[{"a":1}]


@pytest.mark.parametrize("status,raw",[(403,body(code=1,error="forbidden")),
    (429,body(code=1,error="rate_limited")),(503,body(code=1,error="data_source_unavailable")),
    (200,b"not-json")])
def test_daily_extra_retry_does_not_apply_to_permanent_or_malformed_outcome(status,raw):
    calls=[]
    def clock():return "2026-10-03T14:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(status,raw,clock)
    out=r.request("daily",{},key="abcdefgh",transport=transport,
                  sleep=lambda _:pytest.fail("no retry"),clock=clock,retry_waits=(30,90))
    assert len(calls)==1 and out["status"]!="SUCCESS"


def test_shared_capture_deadline_refuses_late_retry_and_never_fakes_http():
    calls=[]; sleeps=[]; moments=iter([0,150])
    def clock():return "2026-10-03T14:00:00+00:00"
    def transport(api,params,key,clock):
        calls.append(1)
        return transport_result(503,body(code=1,error="upstream_pool_exhausted"),clock)
    out=r.request("daily",{},key="abcdefgh",transport=transport,sleep=sleeps.append,
                  clock=clock,retry_waits=(30,90),deadline=200,monotonic=lambda:next(moments))
    assert len(calls)==1 and sleeps==[] and out["status"]=="TEMPORARY_QUEUE"
    empty=r.request("daily",{},key="abcdefgh",transport=lambda *a,**k:pytest.fail("no request"),
                    retry_waits=(30,90),deadline=50,monotonic=lambda:0,clock=clock)
    assert empty["status"]=="REQUEST_BUDGET_EXHAUSTED" and empty["attempts"]==[]
