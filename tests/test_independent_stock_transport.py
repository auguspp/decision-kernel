"""Only the existing bounded Decimal-safe HTTP transport gains this exact route."""
import pytest
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import hithink_dump_trial as transport


class Response:
    status_code=200
    def __init__(self,raw):
        self.raw=raw;self.headers={'Content-Type':'application/json','Content-Length':str(len(raw))}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_content(self,chunk_size):yield self.raw


class Session:
    def __init__(self,raw,calls):self.raw,self.calls=raw,calls
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def get(self,url,**kwargs):self.calls.append((url,kwargs));return Response(self.raw)


@pytest.mark.parametrize('params',[{'limit':'500','offset':'0'},{'limit':'500','offset':'6500'}, {'thscodes':'600000.SH'}])
def test_exact_route_reuses_existing_transport_preserves_decimal_lexeme_and_no_retry(monkeypatch,params):
    calls=[]
    monkeypatch.setattr(transport,'_session',lambda:Session(b'{"code":0,"data":{"value":0.12345678901234567890123456789}}',calls))
    value=own.request_json(own.SNAPSHOT,params,api_key='synthetic')
    assert value['data']['value']=='0.12345678901234567890123456789'
    assert len(calls)==1 and calls[0][1]['params']==params
    assert calls[0][1]['allow_redirects'] is False and calls[0][1]['timeout']==(10,20)


@pytest.mark.parametrize('params',[{'limit':'501','offset':'0'},{'limit':'500','offset':'7000'},
    {'limit':'500','offset':'1'},{'limit':'500','offset':'00'}, {'limit':'500','offset':'-500'},
    {'limit':500,'offset':'0'},{'limit':'500','offset':False}, {'limit':'500','offset':'0','thscodes':'600000.SH'},
    {'thscodes':'600000.SH,600001.SH'}, {'offset':'0'}])
def test_no_generic_snapshot_client_or_out_of_budget_page_route(monkeypatch,params):
    def denied():raise AssertionError('invalid request reached transport')
    monkeypatch.setattr(transport,'_session',denied)
    with pytest.raises(ValueError):own.request_json(own.SNAPSHOT,params,api_key='synthetic')
