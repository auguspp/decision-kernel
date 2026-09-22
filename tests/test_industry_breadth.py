"""Offline breadth/source/reading contracts, not new live industry evidence."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import current_state as m, industry_breadth as s
from decision_kernel.runtime import industry_breadth_reading as r
from decision_kernel.runtime import external_radar_reading as previous
from test_external_radar_reading import setup, pack

TIME = '2026-09-20T04:00:00+00:00'
IDENTITY = {'repository': m.REPOSITORY, 'workflow': s.WORKFLOW, 'ref': 'refs/heads/main',
            'event': 'workflow_dispatch', 'code_commit': 'b'*40, 'run_id': 901,
            'attempt': 1, 'trigger_run_id': None}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('industry unit test attempted networking')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


def row(code='ALZL.SHF', spot='spot-a'):
    return {'thscode': code, 'ticker': code.split('.')[0], 'variety_name': '原名称<script>x</script>',
        'spot_indicator_id': spot, 'reference_site': '原报价地', 'default_value': 'Y',
        'spot_publish_date': '2026-09-18', 'updated_at': '2026.09.18 19:00:00',
        'converted_spot_price': 100, 'close_price': 99, 'close_basis': 1,
        'close_basis_rate': 1, 'settle_price': None}


def body(rows=None):
    return json.dumps({'code': 0, 'data': {'timestamp': int(datetime.fromisoformat(TIME).timestamp()*1000),
        'item': [row(), row(spot='spot-b'), row('IFZL.CFE')] if rows is None else rows}}, ensure_ascii=False).encode()


def receipt(raw):
    return {'path': s.ENDPOINT, 'params': {}, 'requested_at': TIME, 'received_at': TIME,
        'representation': 'DECODED_JSON_TOOL_RETURN_NOT_WIRE_BYTES', 'status': 'CAPTURED_DECODED_RESPONSE',
        'response_bytes': len(raw), 'response_sha256': m.sha256(raw)}


def captured(tmp_path, request=None, credential='test-credential'):
    root = tmp_path/'new'
    value = s.capture(root, deepcopy(IDENTITY), credential=credential,
        request=request or (lambda key: body()), clock=lambda: TIME)
    return {p.name: p.read_bytes() for p in root.iterdir()}, value


def test_breadth_is_not_three_symbols_or_one_spot_per_series():
    raw = body(); report = s.normalize(raw, receipt(raw), cutoff=TIME)['projection']
    assert report['coverage']['source_rows'] == 3 and report['coverage']['distinct_series'] == 2
    assert report['coverage']['financial_series'] == 1
    assert len(report['series'][0]['default_rows']) == 2
    assert all(v['spot_selection'].startswith('NOT_SELECTED') for v in report['series'])
    assert report['coverage']['provider_universe_complete'] == 'NOT_ESTABLISHED'
    assert all(v['question_status'] == 'NOT_FORMED' for v in report['observations'])
    assert report['units_and_ratio_scale'].startswith('RAW_PROVIDER')
    assert report['research_executions'] == report['new_attention_events'] == report['model_calls'] == 0


@pytest.mark.parametrize('problem', ['unknown-code', 'no-date', 'future-date', 'bad-number', 'missing-number', 'duplicate'])
def test_row_gaps_or_duplicate_content_do_not_erase_other_rows(problem):
    a, b = row(), row('CUZL.SHF')
    if problem == 'unknown-code': a['thscode'] = None
    elif problem == 'no-date': a['spot_publish_date'] = None
    elif problem == 'future-date': a['spot_publish_date'] = '2027-01-01'
    elif problem == 'bad-number': a['close_price'] = 'not-a-number'
    elif problem == 'missing-number': a['close_price'] = None
    else: b = deepcopy(a)
    raw = body([a,b]); p=s.normalize(raw,receipt(raw),cutoff=TIME)['projection']
    assert p['coverage']['source_rows'] == 2
    if problem == 'unknown-code': assert len(p['invalid_rows']) == 1 and len(p['observations']) == 1
    elif problem == 'future-date': assert p['observations'][0]['source_date_status'] == 'FUTURE_SOURCE_DATE'
    elif problem == 'no-date': assert p['observations'][0]['spot_age_days_at_capture'] is None
    elif problem == 'bad-number': assert 'close_price' in p['observations'][0]['invalid_numeric_fields']
    elif problem == 'missing-number': assert 'close_price' in p['observations'][0]['missing_fields']
    else: assert p['coverage']['duplicate_content_rows'] == 1


def test_empty_and_repeated_snapshots_preserve_their_meaning():
    raw=body([]); p=s.normalize(raw,receipt(raw),cutoff=TIME)['projection']
    assert p['status']=='EMPTY_SOURCE_SNAPSHOT_NOT_NO_INDUSTRY_CHANGE'
    raw=body(); first=s.normalize(raw,receipt(raw),cutoff=TIME)
    later={**receipt(raw),'received_at':'2026-09-21T04:00:00Z'}
    second=s.normalize(raw,later,cutoff=later['received_at'])
    ids=lambda p:[x['version_id'] for x in p['projection']['observations']]
    assert ids(first)==ids(second) and first!=second


@pytest.mark.parametrize('damage', ['bytes', 'hash', 'path', 'params', 'representation', 'future', 'rows'])
def test_bad_source_binding_is_rejected(damage):
    raw=body(); rec=receipt(raw)
    if damage=='bytes': rec['response_bytes']+=1
    elif damage=='hash': rec['response_sha256']='a'*64
    elif damage=='path': rec['path']='/other'
    elif damage=='params': rec['params']={'code':'LC'}
    elif damage=='representation': rec['representation']='RETAINED_HTTP_BODY'
    elif damage=='future': rec['received_at']='2027-01-01T00:00:00Z'
    else: raw=body([row()]* (s.MAX_ROWS+1));rec=receipt(raw)
    with pytest.raises(ValueError): s.normalize(raw,rec,cutoff=TIME)


def test_native_capture_is_one_call_create_only_and_replayable(tmp_path):
    calls=[]
    files,value=captured(tmp_path, lambda key:(calls.append(key),body())[1])
    assert len(calls)==1 and value['attempted_requests']==1
    run={'id':901,'head_sha':'b'*40,'event':'workflow_dispatch','run_attempt':1,
         'created_at':'2026-09-20T03:55:00Z','updated_at':'2026-09-20T04:10:00Z'}
    result=s.replay(files,run,cutoff=run['updated_at'])
    assert result['status']=='SAVED_NATIVE_SNAPSHOT'
    assert result['snapshot']['projection']['source']['representation']=='RETAINED_HTTP_BODY'
    with pytest.raises(ValueError): s.capture(tmp_path/'new',IDENTITY,credential='x',request=lambda _:calls.append('bad'))
    assert len(calls)==1
    files['basis.json']+=b' '
    with pytest.raises(ValueError): s.replay(files,run,cutoff=run['updated_at'])


@pytest.mark.parametrize('problem', ['no-key', 'timeout', 'credential', 'escaped-credential', 'oversize'])
def test_source_unavailable_never_becomes_an_empty_success(tmp_path, problem):
    calls=[]
    def request(key):
        calls.append(key)
        if problem=='timeout': raise TimeoutError('do not retain exception secrets')
        if problem=='credential': return b'{"value":"test-credential"}'
        if problem=='escaped-credential': return b'{"value":"test-credentia\\u006c"}'
        return b'x'*(s.MAX_BODY+1)
    files,value=captured(tmp_path,request,credential='' if problem=='no-key' else 'test-credential')
    assert value['receipt']['status']=='SOURCE_UNAVAILABLE' and 'basis.json' not in files
    assert len(calls)==(0 if problem=='no-key' else 1)
    assert b'test-credential' not in b''.join(files.values())


def prepared(tmp_path, monkeypatch):
    col,b,_=setup(monkeypatch); baseline=previous.attach(col,b)
    files,_=captured(tmp_path)
    run={'id':901,'head_sha':'b'*40,'head_branch':'main','path':s.WORKFLOW,
        'repository':{'full_name':m.REPOSITORY},'head_repository':{'full_name':m.REPOSITORY},
        'event':'workflow_dispatch','run_attempt':1,'status':'completed','conclusion':'success',
        'created_at':'2026-09-20T03:55:00Z','updated_at':'2026-09-20T04:10:00Z'}
    col.api.responses[r.QUERY]={'total_count':1,'workflow_runs':[run]}
    col.api.responses['actions/runs/901']=run
    raw=pack(files); art={'id':991,'name':'industry-breadth-901-1','expired':False,
        'size_in_bytes':len(raw),'digest':'sha256:'+m.sha256(raw),
        'workflow_run':{'id':901,'head_sha':'b'*40}}
    col.api.responses['actions/runs/901/artifacts?per_page=100']={'total_count':1,'artifacts':[art]}
    col.api.archives[991]=raw
    return col,baseline,run,art


def test_reading_keeps_both_dates_and_all_original_lanes(tmp_path,monkeypatch):
    col,b,_,_=prepared(tmp_path,monkeypatch); before=deepcopy(b);files=dict(col.files);calls=col.api.calls
    p=r.attach(col,b);m.validate_read_package(p)
    assert p['research']['industry_breadth']['native_status']=='SAVED_NATIVE_SNAPSHOT'
    assert p['research']['industry_breadth']['historical_status']=='HISTORICAL_BREADTH_NOT_TODAY'
    assert p['research']['external_radar']==before['research']['external_radar'] and b==before
    assert p['lanes']==b['lanes'] and col.api.calls-calls==4
    assert '<script>' not in col.files[r.DETAIL].decode()
    for name,raw in files.items():
        if name not in {'README.md','current-state.json'}: assert col.files[name]==raw


@pytest.mark.parametrize('problem',['no-run','failed','expired','wrong-code','future','rerun'])
def test_native_gaps_do_not_fall_back_or_erase_history(tmp_path,monkeypatch,problem):
    col,b,run,art=prepared(tmp_path,monkeypatch)
    if problem=='no-run': col.api.responses[r.QUERY]={'total_count':0,'workflow_runs':[]}
    elif problem=='failed': run['conclusion']='failure'
    elif problem=='expired': art['expired']=True
    elif problem=='wrong-code': run['head_sha']='f'*40
    elif problem=='future': run['updated_at']='2027-01-01T00:00:00Z'
    else: run['run_attempt']=2
    p=r.attach(col,b)
    assert p['research']['industry_breadth']['native_status']!='SAVED_NATIVE_SNAPSHOT'
    detail=json.loads(col.files[r.REPORT])['projection']['sections']
    assert detail['native']['snapshot'] is None
    assert detail['historical']['status']=='HISTORICAL_BREADTH_NOT_TODAY'


def test_workflow_and_publisher_use_existing_clock_not_price_gate():
    root=Path(__file__).resolve().parents[1]
    workflow=(root/s.WORKFLOW).read_text();publisher=(root/'.github/workflows/current-state-read-entry.yml').read_text()
    entry=(root/'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'workflows: [sector-radar-shadow]' in workflow and 'types: [completed]' in workflow
    assert 'schedule:' not in workflow and '\n  push:' not in workflow
    assert 'github.event.workflow_run.conclusion' not in workflow
    assert 'persist-credentials: false' in workflow and 'contents: write' not in workflow
    assert 'head_sha="$GITHUB_SHA"' in workflow and "r['conclusion']=='success'" in workflow
    assert 'radar-industry-breadth' in publisher and '--include-industry-breadth' in publisher
    assert 'getattr(self, "include_industry_breadth", False)' in entry
    assert 'parser.add_argument("--include-industry-breadth", action="store_true")' in entry


@pytest.mark.parametrize('field,value', [('repository','other/repo'),('workflow','.github/workflows/other.yml'),
    ('event','push'),('attempt',2),('attempt',True),('code_commit','x'*40),('trigger_run_id',99)])
def test_bad_workflow_identity_stops_before_request_or_output(tmp_path,field,value):
    calls=[];identity={**IDENTITY,field:value}
    with pytest.raises(ValueError):
        s.capture(tmp_path/'capture',identity,credential='test-credential',request=lambda k:calls.append(k))
    assert calls==[] and not (tmp_path/'capture').exists()


@pytest.mark.parametrize('damage',['redirect','http','encoding','length','oversize','truncated'])
def test_fixed_native_http_reuses_safe_streaming_policy(monkeypatch,damage):
    calls=[]
    class Response:
        status_code=403 if damage=='http' else 200
        url='https://untrusted.test/' if damage=='redirect' else s.HITHINK_BASE_URL+s.ENDPOINT
        headers=({'Content-Encoding':'gzip'} if damage=='encoding' else
                 {'Content-Length':str(s.MAX_BODY+1)} if damage=='length' else
                 {'Content-Length':'100'} if damage=='truncated' else {})
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def iter_content(self,chunk_size):
            assert chunk_size==65536
            yield b'x'*(s.MAX_BODY+1) if damage=='oversize' else b'{}'
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def get(self,url,**kwargs):
            calls.append(url)
            assert url==s.HITHINK_BASE_URL+s.ENDPOINT and kwargs['params']=={}
            assert kwargs['allow_redirects'] is False and kwargs['stream'] is True
            assert kwargs['timeout']==(10,20) and kwargs['headers']['X-api-key']=='test-credential'
            return Response()
    monkeypatch.setattr(s,'_session',Session)
    with pytest.raises(ValueError): s.request_raw('test-credential')
    assert len(calls)==1


def test_native_failure_does_not_read_older_success_and_budget_is_not_reset(tmp_path,monkeypatch):
    col,b,run,_=prepared(tmp_path,monkeypatch)
    newer={**deepcopy(run),'id':902,'conclusion':'failure',
        'created_at':'2026-09-20T04:20:00Z','updated_at':'2026-09-20T04:25:00Z'}
    col.api.responses[r.QUERY]={'total_count':2,'workflow_runs':[newer,run]}
    col.api.responses['actions/runs/902']=newer;col.api.reads=[]
    p=r.attach(col,b)
    assert p['research']['industry_breadth']['native_status'].startswith('LATEST_ATTEMPT_NOT_SUCCESSFUL')
    assert 'actions/runs/901' not in col.api.reads and ('archive',991) not in col.api.reads
    col,b,_,_=prepared(tmp_path/'budget',monkeypatch)
    col.api.calls=col.api.max_calls;col.api.reads=[]
    with pytest.raises(ValueError): r.attach(col,b)
    assert col.api.calls==col.api.max_calls and col.api.reads==[]
