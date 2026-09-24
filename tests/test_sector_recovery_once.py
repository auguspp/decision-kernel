"""Synthetic recovery inputs only; these tests cannot contact HiThink."""
import copy
import importlib.util
import json
import socket
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_events import create_sector_radar_candidate_event_ledger
from decision_kernel.runtime.sector_radar_persistence import write_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_state import SectorRadarStateSourceLineage, create_sector_radar_market_state

spec = importlib.util.spec_from_file_location('recovery_once', '.github/scripts/capture-sector-recovery.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail('Network forbidden in synthetic recovery tests')
    monkeypatch.setattr(socket, 'create_connection', refused)
    monkeypatch.setattr(r.http, 'urlopen', refused)


def fixture(root, full=False):
    old_day = date(2026, 9, 9)
    sessions = sorted(old_day - timedelta(days=i) for i in range(200) if (old_day - timedelta(days=i)).weekday() < 5)[-127:]
    codes = [('000300.SH', 'Synthetic benchmark')]
    codes += [(f'881{100+i:03}.TI', f'Synthetic broad {i}') for i in range(90 if full else 1)]
    codes += [(f'884{i:03}.TI', f'Synthetic granular {i}') for i in range(230 if full else 1)]
    catalog = {'code': 0, 'data': {'timestamp': 1789000000000, 'item': [{'thscode': c, 'name': n} for c, n in codes[1:]]}}
    series = [SectorPriceSeries(c, n, tuple(SectorPricePoint(d, Decimal(100+i), Decimal(1000+i)) for i, d in enumerate(sessions))) for c, n in codes]
    stamp = datetime(2026, 9, 9, 8, tzinfo=timezone.utc)
    state = create_sector_radar_market_state(catalog=normalize_hithink_industry_catalog(catalog),
        benchmark=series[0], broad_series=series[1:91] if full else series[1:2],
        granular_series=series[91:] if full else series[2:], created_at=stamp, source='SYNTHETIC_TEST_ONLY',
        source_lineage=[SectorRadarStateSourceLineage('SYNTHETIC', 1, 1, 'sha256:'+'a'*64, None)])
    ledger = create_sector_radar_candidate_event_ledger(created_at=stamp, source='SYNTHETIC_TEST_ONLY')
    bundle = write_sector_radar_persistent_bundle(root/'input', market_state=state, event_ledger=ledger,
        created_at=stamp, updated_at=stamp, source_repository=r.REPO, source_workflow=r.PARENT_WORKFLOW,
        source_run_id=34364727989, source_run_attempt=1, source_commit_sha='a'*40,
        parent_hint_mapping_hash='d'*64, last_result_hash=None, last_operation_status='SYNTHETIC_TEST_ONLY')
    plan = copy.deepcopy(r.load(r.REQUEST_FILE))
    plan['parent'].update(commit='a'*40, state_hash=state.state_hash, parent_hint_mapping_hash='d'*64)
    env = {'GITHUB_REPOSITORY':r.REPO, 'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch',
           'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_WORKFLOW_REF':r.REPO+'/'+r.WORKFLOW+'@refs/heads/main',
           'GITHUB_SHA':'b'*40, 'GITHUB_RUN_ID':'34364727990', 'RECOVERY_LAUNCH_SHA':'c'*40}
    parent = plan['parent']
    run = {'id':parent['run_id'], 'head_sha':parent['commit'], 'path':r.PARENT_WORKFLOW, 'head_branch':'main',
           'status':'completed', 'conclusion':'success', 'run_attempt':1, 'event':'schedule',
           'repository':{'full_name':r.REPO}, 'head_repository':{'full_name':r.REPO}}
    artifact = {'name':'sector-radar-state-bundle', 'id':parent['artifact_id'], 'digest':parent['artifact_digest'],
                'size_in_bytes':parent['artifact_bytes'], 'expired':False,
                'workflow_run':{'id':parent['run_id'], 'head_sha':parent['commit']}}
    launch = {'sha':'c'*40, 'tag':r.REQUEST, 'object':{'type':'commit','sha':'b'*40},
              'message':json.dumps({'request_id':r.REQUEST,'run_id':env['GITHUB_RUN_ID'],'authorization_comment_id':5628923881})}
    meta = {'run.json':run, 'artifacts.json':{'total_count':1,'artifacts':[artifact]},
            'newest.json':{'total_count':1,'workflow_runs':[run]}, 'launch.json':launch,
            'launch-ref.json':{'ref':r.LAUNCH_REF,'object':{'type':'tag','sha':'c'*40}}}
    for n, v in meta.items():r.save(root/'metadata'/n,v)
    bundle, binding = r.prepare(root, plan, env)
    days = sessions+[date(2026,9,10), date(2026,9,11)]
    calls = []
    def request(path, params):
        calls.append((path, params))
        if path == r.http.HITHINK_CALENDAR_PATH:
            return {'code':0,'data':{'item':[{'date':d.strftime('%Y%m%d')} for d in days]}}
        if path == r.index.HITHINK_INDEX_CATALOG_PATH:return copy.deepcopy(catalog)
        assert path == r.index.HITHINK_INDEX_HISTORY_PATH
        assert set(params) == {'thscode','interval','start','end'} and params['interval'] == '1d'
        end = datetime.fromtimestamp(int(params['end'])/1000,r.SHANGHAI_TZ)
        assert end.time().isoformat() == '23:59:59.999000'
        chosen = [d for d in days if int(params['start']) <= int(datetime.combine(d,datetime.min.time(),r.SHANGHAI_TZ).timestamp()*1000) <= int(params['end'])]
        items = [{'date_ms':int(datetime.combine(d,datetime.min.time(),r.SHANGHAI_TZ).timestamp()*1000),
                  'close_price':str(100+days.index(d)), 'turnover':str(1000+days.index(d)), 'volume':'1'} for d in chosen]
        return {'code':0,'data':{'thscode':params['thscode'],'interval':'1d','adjust':None,'timestamp':items[-1]['date_ms'],'item':items}}
    return bundle, binding, env, request, calls


def run(root, f, observed=None, request=None, monotonic=None):
    bundle, binding, _, transport, _ = f
    return r.collect(root,bundle,binding,provenance=r.SYNTHETIC,request=request or transport,
                     now=lambda:observed or datetime(2026,9,11,4,30,tzinfo=timezone.utc),monotonic=monotonic or (lambda:0))


@pytest.mark.parametrize('full,two_days', [(False,False),(False,True),(True,True)])
def test_original_rebuild_and_preserved_state(tmp_path, full, two_days):
    # pytest fixtures are explicit below through tmp_path; no source data is real.
    f = fixture(tmp_path, full)
    before = {n:(tmp_path/'input'/n).read_bytes() for n in r.INPUTS}
    observed = datetime(2026,9,11,8 if two_days else 4,30,tzinfo=timezone.utc)
    report = run(tmp_path,f,observed)
    assert len(f[-1]) == (323 if full else 5)
    assert report['unobserved_event_sessions'] == ['2026-09-10']+(['2026-09-11'] if two_days else [])
    assert report['production_state_writes'] == report['events_created'] == report['technical_retries'] == 0
    assert r.verify(tmp_path)['network_calls'] == 0
    assert {n:(tmp_path/'input'/n).read_bytes() for n in r.INPUTS} == before
    assert (tmp_path/'capture/candidate-events.json').read_bytes() == before['candidate-events.json']
    with pytest.raises(FileExistsError):run(tmp_path,f,observed)


@pytest.mark.parametrize('kind', ['timeout','http429','bad_json','unicode','catalog','overlap','missing','future','credential','deadline','budget'])
def test_failure_stops_and_retains_partial(tmp_path,kind):
    f = fixture(tmp_path)
    bundle,binding,_,transport,calls = f
    hit = [0]
    def request(path, params):
        hit[0] += 1
        if hit[0] == 3 and kind in {'timeout','http429','bad_json','unicode'}:
            if kind=='timeout':raise TimeoutError('synthetic')
            if kind=='http429':raise r.http.HithinkRuntimeError('failure_kind=HTTP_429; status 429')
            if kind=='unicode':raise UnicodeDecodeError('utf8',b'\xff',0,1,'synthetic')
            raise json.JSONDecodeError('synthetic','{',1)
        value = transport(path,params)
        if kind=='catalog' and hit[0]==2:value['data']['item'][0]['name']='changed'
        if hit[0]==3:
            if kind=='overlap':value['data']['item'][0]['turnover']='0'
            if kind=='missing':value['data']['item'].pop(1)
            if kind=='future':value['data']['item'][-1]['date_ms'] += 86400000
            if kind=='credential':value['secret']='synthetic-secret'
        return value
    if kind=='budget':binding['request']['max_hithink_requests']=2
    monotonic = iter([0, 100000]).__next__ if kind=='deadline' else lambda:0
    if kind=='deadline':monotonic = lambda:100000 if hit[0] else 0  # First request succeeds; next exceeds budget.
    with pytest.raises(Exception):run(tmp_path,f,request=request,monotonic=monotonic)
    saved = r.load(tmp_path/'capture/report.json')
    assert saved['status']=='FAILED_CLOSED' and saved['technical_retries']==0
    assert saved['candidate_state_hash'] is None and not (tmp_path/'capture/candidate-state.json').exists()
    assert hit[0] <= 3 and len(saved['files']) >= 1
    with pytest.raises(ValueError,match='CAPTURE_NOT_COMPLETE'):r.verify(tmp_path)


@pytest.mark.parametrize('tamper', ['repo','attempt','ref','parent','artifact','launch','latest','budget'])
def test_preflight_rejects_before_transport(tmp_path,tamper):
    bundle,binding,env,_,calls = fixture(tmp_path)
    plan = copy.deepcopy(binding['request'])
    if tamper=='repo':env['GITHUB_REPOSITORY']='other/repo'
    elif tamper=='attempt':env['GITHUB_RUN_ATTEMPT']='2'
    elif tamper=='ref':env['GITHUB_REF']='refs/heads/other'
    elif tamper=='budget':plan['max_hithink_requests']=324
    else:
        name = {'parent':'run.json','artifact':'artifacts.json','launch':'launch.json','latest':'newest.json'}[tamper]
        p=tmp_path/'metadata'/name; value=r.load(p)
        if tamper=='parent':value['head_sha']='f'*40
        if tamper=='artifact':value['artifacts'][0]['expired']=True
        if tamper=='launch':value['message']=value['message'].replace(env['GITHUB_RUN_ID'],'999')
        if tamper=='latest':value['workflow_runs'][0]['id']+=2
        r.save(p,value)
    with pytest.raises((ValueError,KeyError,RuntimeError)):r.prepare(tmp_path,plan,env)
    assert not calls


@pytest.mark.parametrize('what',['response','candidate','ledger','extra','clock','authority','input'])
def test_offline_verification_rejects_tampering(tmp_path,what):
    f=fixture(tmp_path);run(tmp_path,f)
    if what in {'response','candidate','ledger','extra','input'}:
        path={'response':'capture/responses/0002.json','candidate':'capture/candidate-state.json',
              'ledger':'capture/candidate-events.json','extra':'capture/extra.json','input':'input/market-state.json'}[what]
        with (tmp_path/path).open('ab') as file:file.write(b' ')
    else:
        p=tmp_path/'capture/report.json';data=r.load(p);data.pop('report_hash')
        if what=='clock':data['requests'][2]['started_at']='2026-09-08T00:00:00+00:00'
        else:data['production_state_writes']=1
        r.save(p,{**data,'report_hash':canonical_hash(data)})
    with pytest.raises((ValueError,KeyError,RuntimeError)):r.verify(tmp_path)


def test_injected_transport_cannot_claim_live(tmp_path):
    f=fixture(tmp_path)
    with pytest.raises(ValueError,match='INJECTED_TRANSPORT_NOT_LIVE'):
        r.collect(tmp_path,f[0],f[1],provenance=r.LIVE,request=f[3],api_key='synthetic')
    assert not f[-1]


def test_existing_activity_checker_accepts_explicit_extra_peers():
    import runpy
    from urllib.parse import parse_qs,urlsplit
    c=runpy.run_path('.github/scripts/check-sector-scheduled-activity.py')
    path='.github/workflows/sector-member-reading.yml';calls=[]
    def read(url):
        calls.append(url); status=parse_qs(urlsplit(url).query)['status'][0]
        rows=[{'id':1,'path':path,'status':status}] if status=='in_progress' else []
        return {'total_count':len(rows),'workflow_runs':rows}
    assert c['check_activity'](read)==[] and len(calls)==5
    assert c['check_activity'](read,peers=c['PEERS']|{path})==[1] and len(calls)==10


def test_consumed_recovery_has_no_launcher_and_normal_budget_is_unchanged():
    assert not Path('.github/workflows/sector-recovery-once.yml').exists()
    for path in Path('.github/workflows').glob('*.yml'):
        assert 'capture-sector-recovery.py' not in path.read_text()
    from decision_kernel.runtime.sector_radar_audit import MAX_REQUESTS
    assert MAX_REQUESTS==128


@pytest.mark.parametrize("clock", ["now", "monotonic"])
def test_live_capture_refuses_clock_injection(tmp_path, clock):
    with pytest.raises(ValueError, match="LIVE_CLOCK_OVERRIDE_REJECTED"):
        r.collect(tmp_path, None, {}, api_key="synthetic-private", **{clock: lambda: 1})
