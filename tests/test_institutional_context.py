"""Source-window, no-authority, retained-byte and comparison-boundary contracts."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
import requests

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import institutional_context as s

EX = {'repository':'auguspp/decision-kernel','workflow':s.WORKFLOW,'ref':'refs/heads/main',
      'event':'workflow_dispatch','code_commit':'a'*40,'run_id':123,'attempt':1}
SCOPE = s.scope('002436.SZ','2026-08-11','2026-09-24')
NOW = '2026-09-25T03:00:00+00:00'
ACTIVITY = {'SECUCODE':'002436.SZ','SECURITY_CODE':'002436','NOTICE_DATE':'2026-09-01 00:00:00',
    'RECEIVE_START_DATE':'2026-08-30 00:00:00','RECEIVE_OBJECT':'机构甲、机构乙','INVESTIGATORS':'张、李',
    'RECEIVE_WAY_EXPLAIN':'特定对象调研'}
REPORT = {'stockCode':'002436','infoCode':'AP20260831abc','publishDate':'2026-08-31 00:00:00',
    'orgSName':'机构甲','orgCode':'A','title':'报告 | <script>not executed</script>',
    'predictThisYearEps':'0.25','predictNextYearEps':None,'predictNextTwoYearEps':'0'}


def envelope(family, rows):
    return s.encoded({'success':True,'result':{'data':rows,'count':len(rows),'pages':1}} if family=='activity'
        else {'data':rows,'hits':len(rows),'TotalPage':1})


def run(tmp_path, fetch=None):
    calls=[]
    def transport(spec, selected):
        assert selected == SCOPE; calls.append(spec)
        return fetch(spec) if fetch else (200, envelope(spec['family'],[ACTIVITY] if spec['family']=='activity' else [REPORT]))
    root=tmp_path/'capture'
    result=s.capture(root,SCOPE,EX,transport=transport,clock=lambda:NOW)
    assert result == s.replay(root,EX)
    return root,result['projection'],calls


def test_two_bounded_sources_and_source_dates_not_retrieval_year(tmp_path):
    _,p,calls=run(tmp_path)
    assert len(calls)==2 and all(c['params'].get('pageSize')=='50' for c in calls)
    assert 'push2' not in str(calls)
    assert p['investment_authority']=='NONE' and p['model_calls']==0 and p['source_calls_during_replay']==0
    a=p['families']['activity']['records'][0]
    assert a['event_date']=='2026-08-30' and a['publication_date']=='2026-09-01'
    assert a['available_at']==NOW and a['historical_available_at']=='NOT_ESTABLISHED'
    assert a['counts']=={'events':None,'distinct_institutions':None,'participants':None}
    r=p['families']['reports']['records'][0]
    assert r['target_period']=='NOT_ESTABLISHED' and r['forecast_revision']=='NOT_COMPARABLE'
    assert r['forecast_slots']['predictNextYearEps'] is None
    assert r['forecast_slots']['predictNextTwoYearEps']=='0'


def test_exact_duplicate_rows_collapsed_but_variants_kept(tmp_path):
    changed={**REPORT,'predictThisYearEps':'0.27'}
    def fetch(spec):
        rows=[ACTIVITY,ACTIVITY] if spec['family']=='activity' else [REPORT,REPORT,changed]
        return 200,envelope(spec['family'],rows)
    _,p,_=run(tmp_path,fetch)
    assert p['families']['activity']['unique_record_versions']==1
    r=p['families']['reports']
    assert r['duplicates_collapsed']==1 and r['unique_record_versions']==2
    assert len(r['records'][0]['source_locations'])==2
    assert all(x['forecast_revision']=='NOT_COMPARABLE' for x in r['records'])


def test_single_page_limit_does_not_claim_window_complete(tmp_path):
    def fetch(spec):
        if spec['family']=='activity':
            return 200,s.encoded({'success':True,'result':{'data':[ACTIVITY],'count':77,'pages':2}})
        return 200,s.encoded({'data':[REPORT]})
    _,p,_=run(tmp_path,fetch)
    assert all(not x['matched_reported_scope'] for x in p['families'].values())


@pytest.mark.parametrize('status',[401,403,429])
def test_policy_stop_does_not_try_other_host_or_source(tmp_path,status):
    root,p,calls=run(tmp_path,lambda spec:(status,b'refused'))
    assert len(calls)==1 and p['families']['reports']['status']=='NOT_ATTEMPTED_POLICY_STOP'
    assert (root/'activity.body').read_bytes()==b'refused'


def test_502_is_retained_and_different_endpoint_still_gets_one_attempt(tmp_path):
    def fetch(spec):
        return (502,b'gateway failure') if spec['family']=='activity' else (200,envelope('reports',[REPORT]))
    root,p,calls=run(tmp_path,fetch)
    assert len(calls)==2 and p['families']['activity']['http_status']==502
    assert p['families']['reports']['status']=='CONTEXT_READY'
    assert (root/'activity.body').read_bytes()==b'gateway failure'


def test_transport_failure_remains_unknown_without_fake_body(tmp_path):
    def fetch(spec): raise requests.Timeout()
    root,p,calls=run(tmp_path,fetch)
    assert len(calls)==2 and not list(root.glob('*.body'))
    assert all(v['status']=='TRANSPORT_UNAVAILABLE' for v in p['families'].values())


@pytest.mark.parametrize('bad',[
    {'SECURITY_CODE':'600276'}, {'SECUCODE':'002436.SH'}, {'NOTICE_DATE':'2026-07-01'},
    {'RECEIVE_START_DATE':'2026-09-02'}, {'NOTICE_DATE':'2026-09-01T00:00:00+08:00'},
])
def test_identity_date_or_unreviewed_time_shape_is_not_admitted(tmp_path,bad):
    def fetch(spec):
        return 200,envelope(spec['family'],[{**ACTIVITY,**bad}] if spec['family']=='activity' else [REPORT])
    _,p,_=run(tmp_path,fetch)
    assert p['families']['activity']['status']=='RETAINED_BODY_NOT_QUALIFIED'
    assert p['families']['reports']['status']=='CONTEXT_READY'


def test_empty_and_invalid_json_are_not_no_activity(tmp_path):
    def fetch(spec):
        return (200,envelope('activity',[])) if spec['family']=='activity' else (200,b'{"data":[],"data":[]}')
    _,p,_=run(tmp_path,fetch)
    assert p['families']['activity']['status']=='EMPTY_RETURN_NOT_PROOF_OF_NO_ACTIVITY'
    assert p['families']['reports']['status']=='RETAINED_BODY_NOT_QUALIFIED'


@pytest.mark.parametrize('mutation',['raw','request','run','authority','clock','derived','extra'])
def test_custody_mutations_rejected_even_after_capture_rehash(tmp_path,mutation):
    root,p,_=run(tmp_path)
    if mutation=='raw': (root/'reports.body').write_bytes(b'{}')
    elif mutation=='derived': (root/'context.json').write_bytes(b'{}')
    elif mutation=='extra': (root/'extra').write_bytes(b'no')
    else:
        saved=json.loads((root/'capture.json').read_bytes())
        if mutation=='request': saved['records'][0]['request']['params']['pageNumber']='2'
        if mutation=='run': saved['execution']['run_id']=124
        if mutation=='authority': saved['authority']['investment_authority']='YES'
        if mutation=='clock': saved['records'][0]['received_at']='2026-09-24T00:00:00Z'
        saved['capture_hash']=canonical_hash({k:v for k,v in saved.items() if k!='capture_hash'})
        (root/'capture.json').write_bytes(s.encoded(saved))
    with pytest.raises((ValueError,KeyError)):
        s.replay(root,EX)


def test_output_is_create_only_and_symlink_rejected(tmp_path):
    root,p,_=run(tmp_path)
    with pytest.raises(ValueError,match='OUTPUT_CREATE_ONLY'):
        s.capture(root,SCOPE,EX)
    link=tmp_path/'link'; link.symlink_to(root,target_is_directory=True)
    with pytest.raises(ValueError): s.replay(link,EX)


def test_transport_bound_to_reviewed_scope_and_no_redirect_or_auth(monkeypatch):
    spec=s.specs(SCOPE)[0]; payload=envelope('activity',[ACTIVITY]); seen=[]
    expected=requests.Request('GET',spec['url'],params=spec['params']).prepare().url
    class Response:
        status_code=200; headers={'Content-Length':str(len(payload))}; url=expected
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def iter_content(self,chunk_size): yield payload
    class Session:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def get(self,url,**kwargs):
            seen.append(kwargs)
            assert kwargs['allow_redirects'] is False and kwargs['timeout']==(10,20)
            assert not any('token' in k.lower() or 'key' in k.lower() for k in kwargs['headers'])
            return Response()
    monkeypatch.setattr(s,'_session',Session)
    assert s.request_raw(spec,SCOPE)==(200,payload)
    bad=deepcopy(spec); bad['url']='https://elsewhere/'
    with pytest.raises(ValueError): s.request_raw(bad,SCOPE)
    assert len(seen)==1


def test_bad_execution_and_scope_fail_before_network(tmp_path):
    with pytest.raises(ValueError): s.capture(tmp_path/'x',SCOPE,{**EX,'attempt':2})
    with pytest.raises(ValueError): s.scope('002436.SH','2026-08-11','2026-09-24')
    with pytest.raises(ValueError): s.scope('002436.SZ','2025-01-01','2026-09-24')
