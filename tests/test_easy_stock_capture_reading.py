"""Offline actual capture -> ZIP -> Collector tests, never live source claims."""
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import re
import socket
import zipfile

import pytest
import requests

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import easy_stock_capture as s, easy_stock_context as c, easy_stock_reading as r
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError
from test_easy_stock_context import market_body, csv_body, DAY, NOW
from test_radar_company_reading import collector, baseline

WF = {'repository': m.REPOSITORY, 'workflow': s.WORKFLOW, 'ref': 'refs/heads/main',
      'event': 'workflow_dispatch', 'code_commit': 'a'*40, 'run_id': 901, 'attempt': 1, 'trigger_run_id': None}
CUTOFF = '2026-09-22T10:05:00Z'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('unexpected network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def body(spec):
    return csv_body(spec['id'][6:]) if spec['provider'] == 'CFFEX' else market_body(spec['id'])


def captured(tmp_path, transport=None, monotonic=lambda: 0):
    times = iter((c.clock(NOW) + timedelta(seconds=i)).isoformat() for i in range(40))
    root = tmp_path/'public'
    value = s.capture(root, deepcopy(WF), transport=transport or (lambda spec, _: body(spec)),
                      clock=lambda: next(times), monotonic=monotonic)
    return {p.name: p.read_bytes() for p in root.iterdir()}, value


def run():
    return {'id': 901, 'head_sha': WF['code_commit'], 'head_branch': 'main', 'path': s.WORKFLOW,
        'repository': {'full_name': m.REPOSITORY}, 'head_repository': {'full_name': m.REPOSITORY},
        'event': 'workflow_dispatch', 'run_attempt': 1, 'status': 'completed', 'conclusion': 'success',
        'created_at': '2026-09-22T09:59:00Z', 'updated_at': '2026-09-22T10:02:00Z'}


def test_exact_eight_capture_and_replay_does_not_execute_artifact_code(tmp_path):
    files, value = captured(tmp_path)
    p = s.replay(files, run(), cutoff=CUTOFF)
    assert value['attempted_requests'] == 8 and len(files) == 10
    assert len(p['sections']) == 8 and all(x['result'] is not None for x in p['sections'])
    assert p['source_calls_during_replay'] == p['research_executions'] == 0
    assert p['target_date'] == DAY
    with pytest.raises(ValueError): s.replay({**files, 'code.py': b'raise Exception()'}, run(), cutoff=CUTOFF)
    with pytest.raises(ValueError): s.capture(tmp_path/'public', WF)


def test_429_stops_same_provider_without_stopping_independent_sources(tmp_path):
    calls=[]
    def transport(spec, _):
        calls.append(spec['id'])
        if spec['id'] == 'eastmoney-industry':
            raise DumpTrialError('HTTP_REJECTED', http_status=429)
        return body(spec)
    files, value = captured(tmp_path, transport)
    p = s.replay(files, run(), cutoff=CUTOFF)
    assert calls == ['tencent-industry', 'eastmoney-industry', 'cffex-IF', 'cffex-IH', 'cffex-IC', 'cffex-IM']
    assert value['attempted_requests'] == 6
    assert [x['status'] for x in p['sections'][2:4]] == ['NOT_ATTEMPTED_PROVIDER_RATE_LIMIT']*2
    assert p['sections'][1]['receipt']['http_status'] == 429


@pytest.mark.parametrize('kind', ['timeout', 'unsafe', 'malformed', 'business'])
def test_transport_body_and_contract_failures_remain_distinct(tmp_path, kind):
    def transport(spec, _):
        if spec['id'] == 'tencent-industry':
            if kind == 'timeout': raise requests.Timeout('do not publish this private diagnostic')
            if kind == 'unsafe': return b'{"api_key":"secret-like-value"}'
            if kind == 'malformed': return b'not-json'
            return b'{"code":1,"data":[]}'
        return body(spec)
    files, _ = captured(tmp_path, transport)
    p = s.replay(files, run(), cutoff=CUTOFF)
    first = p['sections'][0]
    expected = {'timeout': 'SOURCE_UNAVAILABLE', 'unsafe': 'BODY_NOT_RETAINED',
                'malformed': 'BODY_NOT_RETAINED', 'business': 'RETAINED_BODY_CONTRACT_REJECTED'}
    assert first['status'] == expected[kind] and first['result'] is None
    assert all(x['result'] is not None for x in p['sections'][1:])
    assert b'private diagnostic' not in files['capture.json']
    assert ('tencent-industry.body' in files) == (kind == 'business')


def test_time_budget_stops_without_fake_network_calls(tmp_path):
    ticks=iter([0]+[181]*8)
    files, value = captured(tmp_path, monotonic=lambda: next(ticks))
    assert value['attempted_requests'] == 0
    assert all(x['status'] == 'NOT_ATTEMPTED_TIME_BUDGET' for x in s.replay(files, run(), cutoff=CUTOFF)['sections'])


@pytest.mark.parametrize('damage', ['hash', 'run', 'retry', 'future', 'target', 'request', 'clock', 'count', 'skip', 'body'])
def test_rehashed_forgery_does_not_pass_original_replay(tmp_path, damage):
    files, value = captured(tmp_path)
    if damage == 'hash': value['capture_hash'] = '0'*64
    elif damage == 'run': value['workflow']['run_id'] = 902
    elif damage == 'retry': value['retry_count'] = 1
    elif damage == 'future': value['finished_at'] = '2027-01-01T00:00:00Z'
    elif damage == 'target': value['target_date'] = '2026-09-21'
    elif damage == 'request': value['records'][0]['request']['params']['p'] = '2'
    elif damage == 'clock': value['records'][0]['received_at'] = '2026-09-21T00:00:00Z'
    elif damage == 'count': value['attempted_requests'] = 7
    elif damage == 'skip': value['records'][0]['elapsed_ms_before_request'] = 181000
    else: files['tencent-industry.body'] += b' '
    if damage != 'hash': value['capture_hash'] = canonical_hash({k: v for k, v in value.items() if k != 'capture_hash'})
    files['capture.json'] = s.encoded(value)
    with pytest.raises((ValueError, KeyError)): s.replay(files, run(), cutoff=CUTOFF)


@pytest.mark.parametrize('field,value', [('event','push'),('attempt',2),('attempt',True),('repository','other/repo'),('ref','refs/heads/other')])
def test_workflow_boundary_precedes_output_or_source(tmp_path,field,value):
    calls=[]
    with pytest.raises(ValueError):
        s.capture(tmp_path/'x', {**WF, field:value}, transport=lambda *a: calls.append(a))
    assert calls == [] and not (tmp_path/'x').exists()


def test_fixed_http_never_forwards_credentials_and_checks_response(monkeypatch):
    spec = c.requests_for(DAY)[0]; calls=[]
    class Response:
        status_code=200
        url=requests.Request('GET', spec['url'], params=spec['params']).prepare().url
        headers={}
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def iter_content(self,chunk_size): yield market_body()
    class Session:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def get(self,url,**kw):
            calls.append(url)
            assert url==spec['url'] and kw['params']==spec['params']
            assert kw['allow_redirects'] is False and kw['stream'] is True
            assert kw['timeout']==(10,20)
            assert 'Authorization' not in kw['headers'] and 'X-api-key' not in kw['headers']
            return Response()
    monkeypatch.setattr(s,'_session',Session)
    assert s.request_raw(spec, DAY) == market_body()
    Response.url='https://evil.invalid/'
    with pytest.raises(ValueError): s.request_raw(spec, DAY)
    with pytest.raises(ValueError): s.request_raw({**spec,'url':'https://evil.invalid/'},DAY)
    assert len(calls)==2


class API:
    def __init__(self):
        self.calls=0;self.max_calls=252;self.reads=[];self.responses={};self.raw=None
    def get(self,path):
        self.calls+=1;self.reads.append(path);return deepcopy(self.responses[path])
    def archive(self,artifact):
        self.calls+=1;self.reads.append('ARCHIVE');return self.raw


def setup(tmp_path):
    files,_=captured(tmp_path)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in files.items(): z.writestr(name,raw)
    api=API();api.raw=stream.getvalue();rr=run()
    job={'id':44,'name':r.JOB,'run_id':901,'head_sha':WF['code_commit'],
        'status':'completed','conclusion':'success', 'started_at':'2026-09-22T09:59:20Z',
        'completed_at':'2026-09-22T10:01:00Z',
        'steps':[{'name':n,'status':'completed','conclusion':'success'} for n in (r.GUARD,r.CAPTURE,r.UPLOAD)]}
    art={'id':991,'name':s.ARTIFACT_PREFIX+'901-1','expired':False,'size_in_bytes':len(api.raw),
         'digest':'sha256:'+m.sha256(api.raw),'workflow_run':{'id':901,'head_sha':rr['head_sha']}}
    api.responses={r.QUERY:{'total_count':1,'workflow_runs':[rr]},'actions/runs/901':rr,
        'actions/runs/901/attempts/1/jobs?per_page=100':{'total_count':1,'jobs':[job]},
        'actions/runs/901/artifacts?per_page=100':{'total_count':1,'artifacts':[art]}}
    col=collector(api,tmp_path);col.now=lambda:CUTOFF
    b,_,_=baseline(col)
    col.files['README.md']+=b'\nORIGINAL_NAV\n'
    return col,b,rr,job,art


def test_real_zip_collector_keeps_sibling_failure_and_old_reading(tmp_path):
    col,b,rr,_,_=setup(tmp_path);before=deepcopy(b)
    rr['conclusion']='failure'
    result=r.attach(col,b);m.validate_read_package(result)
    assert result['lanes']==before['lanes'] and b==before and result['pending']==before['pending']
    p=json.loads(col.files[r.PREFIX+'.json'])['projection']['section']
    assert p['whole_workflow_failure_preserved'] and p['whole_workflow_conclusion']=='failure'
    assert p['normalized_source_count']==8 and p['result']['source_calls_during_replay']==0
    assert col.files[p['archive']['read_path']]==col.api.raw and b'ORIGINAL_NAV' in col.files['README.md']
    assert col.api.calls==5 and result['research']['easy_stock_context']['investment_authority']=='NONE'


@pytest.mark.parametrize('damage',['job_failure','step_failure','wrong_job_head','wrong_job_time','expired','digest','future','rerun','foreign','missing_job','duplicate_run'])
def test_newest_failure_never_reads_older_success_or_erases_other_lanes(tmp_path,damage):
    col,b,rr,job,art=setup(tmp_path)
    old={**deepcopy(rr),'id':900,'created_at':'2026-09-21T09:00:00Z'}
    col.api.responses[r.QUERY]={'total_count':2,'workflow_runs':[rr,old]}
    if damage=='job_failure':job['conclusion']='failure'
    elif damage=='step_failure':job['steps'][0]['conclusion']='failure'
    elif damage=='wrong_job_head':job['head_sha']='b'*40
    elif damage=='wrong_job_time':job['completed_at']='2026-09-22T10:00:00Z'
    elif damage=='expired':art['expired']=True
    elif damage=='digest':art['digest']='sha256:'+'0'*64
    elif damage=='future':rr['updated_at']='2027-01-01T00:00:00Z'
    elif damage=='rerun':rr['run_attempt']=2
    elif damage=='foreign':rr['head_repository']['full_name']='other/repo'
    elif damage=='missing_job':job['name']='capture'
    else:col.api.responses[r.QUERY]['workflow_runs']=[rr,rr]
    result=r.attach(col,b)
    assert result['lanes']==b['lanes']
    p=json.loads(col.files[r.PREFIX+'.json'])['projection']['section']
    assert p['result'] is None and not any('/900' in str(v) for v in col.api.reads)


def test_no_run_budget_and_html_are_explicit(tmp_path):
    col,b,_,_,_=setup(tmp_path)
    col.api.responses[r.QUERY]={'total_count':0,'workflow_runs':[]}
    value=r.attach(col,b)
    assert value['research']['easy_stock_context']['status']=='NOT_RUN_NOT_NO_ACTIVITY'
    assert col.api.calls==1
    col.api.calls=col.api.max_calls;col.api.reads=[]
    with pytest.raises(ValueError):r.attach(col,value)
    assert col.api.calls==252 and col.api.reads==[]
    assert '<script>' not in r.render({'status':'<script>unsafe</script>', 'result':None})


@pytest.mark.parametrize('job_name,module', [('public-context','easy_stock_capture'),
                                            ('industrial-fundamentals','industry_fundamentals')])
def test_public_job_reuses_original_clock_and_has_no_source_secrets(job_name,module):
    path=Path('.github/workflows/radar-industry-breadth.yml')
    text=path.read_text()
    # Select exactly this job, not all later sibling jobs' CI preflights.
    tail=text.split('\n  '+job_name+':\n',1)[1]
    job=re.split(r'\n  [a-z][a-z0-9-]*:\n',tail,maxsplit=1)[0]
    assert 'workflow_run:' in text and 'workflows: [sector-radar-shadow]' in text
    assert 'cron:' not in text and '\n  push:' not in text
    assert 'secrets.' not in job and 'HITHINK' not in job and 'contents: write' not in text
    assert 'persist-credentials: false' in job and 'head_sha="$GITHUB_SHA"' in job
    assert 'python -m decision_kernel.runtime.'+module in job
    assert 'GH_TOKEN:' in job.split('- name: Install',1)[0]
    assert 'GH_TOKEN:' not in job.split('- name: Install',1)[1]
    pub=Path('.github/workflows/current-state-read-entry.yml').read_text()
    assert '--include-easy-stock-context' in pub and 'easy-stock-context' not in pub.split('jobs:',1)[0]
