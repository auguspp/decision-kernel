"""Synthetic directory fixtures only; never request or certify broker reports."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('c1_locators', ROOT/'.github/scripts/c1-report-locators.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ENV = {'GITHUB_REPOSITORY':m.saved.REPOSITORY, 'GITHUB_SHA':'a'*40, 'GITHUB_RUN_ID':'123',
       'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch'}


def payload(spec):
    day = spec['params']['trade_date']
    row = [day, 'synthetic', m.TARGETS[day], '个股研报', 'synthetic author', '光迅科技',
           '002281.SZ', '长江证券', 'synthetic', 'https://example.invalid/report.pdf']
    return {'code':0, 'data':{'fields':list(m.FIELDS), 'items':[row]}, 'count':1}


def clock():
    value = datetime(2026, 10, 2, tzinfo=timezone.utc)
    def now():
        nonlocal value
        value += timedelta(seconds=31)
        return value.isoformat()
    return now


def request(api, params, *, clock):
    raw = m.common.encoded(payload({'params':params}))
    return {'status':'SUCCESS', 'attempts':[{'attempt':1, 'classification':'SUCCESS',
        'http_status':200, 'raw':raw, 'requested_at':clock(), 'received_at':clock(),
        'headers':{}, 'business_code':0, 'business_error':None, 'business_msg':None}]}


def test_plan_is_two_exact_queries_not_all_market():
    p = m.plan()
    assert len(p) == 2 and {x['params']['trade_date'] for x in p} == {'20260430','20260910'}
    assert all(x['api']=='research_report' and x['params']['ts_code']=='002281.SZ' for x in p)
    assert all(x['params']['inst_csname']=='长江证券' for x in p)


def test_source_and_replay_do_not_fetch_locators(tmp_path, monkeypatch):
    monkeypatch.setenv(m.relay.SECRET_ENV,'synthetic-key')
    root=tmp_path/'out'; r=m.capture(root,ENV,request=request,now=clock())
    assert r==m.rebuild(root,ENV) and r['http_receipts']==2
    assert all(x['status']=='LOCATOR_ONLY_NOT_FETCHED' for x in r['outcomes'])
    assert r['pdf_acquired'] is False and r['full_model_qualified'] is False
    with pytest.raises(FileExistsError):m.capture(root,ENV,request=request,now=clock())


@pytest.mark.parametrize('field,value',[('trade_date','20260930'),('ts_code','600000.SH'),
                                      ('inst_csname','另一券商'),('report_type','行业研报')])
def test_foreign_directory_not_accepted(field,value):
    spec=m.plan()[0]; b=payload(spec); b['data']['items'][0][m.FIELDS.index(field)]=value
    with pytest.raises(ValueError):m.inspect(m.common.encoded(b),spec)


@pytest.mark.parametrize('bad',[False,None,'0',3002])
def test_business_status_requires_integer_zero(bad):
    spec=m.plan()[0]; b=payload(spec); b['code']=bad
    with pytest.raises(ValueError):m.inspect(m.common.encoded(b),spec)


def test_failure_stops_second_query(tmp_path,monkeypatch):
    monkeypatch.setenv(m.relay.SECRET_ENV,'synthetic-key'); calls=[]
    def bad(api,params,clock):
        calls.append(params)
        r=request(api,params,clock=clock)
        a=r['attempts'][0]
        a.update(raw=m.common.encoded({'code':1,'error':'forbidden'}),http_status=403,
                 classification='AUTH_OR_ENTITLEMENT',business_code=1,business_error='forbidden')
        r['status']='AUTH_OR_ENTITLEMENT';return r
    r=m.capture(tmp_path/'out',ENV,request=bad,now=clock())
    assert len(calls)==1 and r['outcomes'][1]['status']=='NOT_ATTEMPTED_STOP'


def test_invalid_directory_stops_and_retains_original(tmp_path,monkeypatch):
    monkeypatch.setenv(m.relay.SECRET_ENV,'synthetic-key'); calls=[]
    def bad(api,params,clock):
        calls.append(params);r=request(api,params,clock=clock)
        b=payload({'params':params});b['data']['items'][0][6]='600000.SH'
        r['attempts'][0]['raw']=m.common.encoded(b);return r
    r=m.capture(tmp_path/'out',ENV,request=bad,now=clock())
    assert len(calls)==1 and r['outcomes'][0]['status']=='DIRECTORY_UNQUALIFIED'
    assert b'600000.SH' in (tmp_path/'out/raw-0-1.json').read_bytes()


def test_empty_or_ambiguous_is_not_a_model():
    spec=m.plan()[0];b=payload(spec);b['data']['items']=[];b['count']=0
    assert m.inspect(m.common.encoded(b),spec)['status']=='TARGET_NOT_IN_RETURNED_PAGE'
    b=payload(spec);b['data']['items']*=2;b['count']=2
    assert m.inspect(m.common.encoded(b),spec)['status']=='TARGET_AMBIGUOUS'


def test_url_credentials_never_qualify():
    spec=m.plan()[0];b=payload(spec);b['data']['items'][0][-1]='https://user:secret@example.invalid/file.pdf'
    assert m.inspect(m.common.encoded(b),spec)['status']=='URL_UNQUALIFIED'


def test_tampered_raw_refused(tmp_path,monkeypatch):
    monkeypatch.setenv(m.relay.SECRET_ENV,'synthetic-key');root=tmp_path/'out'
    m.capture(root,ENV,request=request,now=clock())
    (root/'raw-0-1.json').write_bytes(b'{}')
    with pytest.raises(ValueError):m.rebuild(root,ENV)


def test_missing_key_makes_no_request(tmp_path,monkeypatch):
    monkeypatch.delenv(m.relay.SECRET_ENV,raising=False)
    r=m.capture(tmp_path/'out',ENV,request=lambda *a,**k:pytest.fail('network'),now=clock())
    assert r['http_receipts']==r['logical_queries_attempted']==0
    assert r['outcomes'][0]['status']=='CREDENTIAL_UNAVAILABLE'


def test_manual_carrier_keeps_c2_and_other_sources_out():
    text=(ROOT/m.WORKFLOW).read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text
    assert 'github.run_attempt == 1' in text and 'assert not prior' in text
    assert text.count('secrets.TUSHARE_PROXY_API_KEY')==1
    assert 'HITHINK' not in text and 'c2-dated-window' not in text
    assert 'contents: write' not in text and 'actions: write' not in text
