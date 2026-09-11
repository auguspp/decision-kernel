"""Synthetic bounded recovery tests. No provider, model or GitHub calls."""
from __future__ import annotations

import copy
import importlib.util
import json
import socket
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_events import create_sector_radar_candidate_event_ledger
from decision_kernel.runtime.sector_radar_persistence import write_sector_radar_persistent_bundle
from decision_kernel.runtime.sector_radar_state import SectorRadarStateSourceLineage, create_sector_radar_market_state

spec = importlib.util.spec_from_file_location('sector_recovery_once_test', '.github/scripts/capture-sector-recovery.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **k: pytest.fail('real network forbidden'))


def setup_case(root, *, count=3, target=date(2026, 9, 10)):
    last = date(2026, 9, 9)
    sessions = sorted(last - timedelta(days=n) for n in range(200) if (last - timedelta(days=n)).weekday() < 5)[-127:]
    now = datetime.combine(target, time(17), tzinfo=m.SHANGHAI_TZ)
    prior = datetime.combine(last, time(16), tzinfo=m.SHANGHAI_TZ)
    millis = lambda d: int(datetime.combine(d, time(), tzinfo=m.SHANGHAI_TZ).timestamp() * 1000)
    identities = [('000300.SH', 'Synthetic benchmark')]
    identities += [(f'881{i:03d}.TI', f'Synthetic broad{i}') for i in range(1, 91 if count == 321 else 2)]
    identities += [(f'884{i:03d}.TI', f'Synthetic granular{i}') for i in range(1, 231 if count == 321 else 2)]
    catalogue = {'code': 0, 'data': {'timestamp': millis(last), 'item': [dict(thscode=c, name=n) for c, n in identities[1:]]}}
    catalog = normalize_hithink_industry_catalog(catalogue)
    histories = [SectorPriceSeries(c, n, tuple(SectorPricePoint(d, Decimal(100 + i), Decimal(1000 + i))
                 for i, d in enumerate(sessions))) for c, n in identities]
    state = create_sector_radar_market_state(catalog=catalog, benchmark=histories[0],
        broad_series=histories[1:91 if count == 321 else 2], granular_series=histories[91 if count == 321 else 2:],
        created_at=prior, source=m.SYNTHETIC,
        source_lineage=[SectorRadarStateSourceLineage('SYNTHETIC', 1, 1, 'sha256:' + 'a' * 64, None)])
    bundle = write_sector_radar_persistent_bundle(root / 'input', market_state=state,
        event_ledger=create_sector_radar_candidate_event_ledger(created_at=prior, source=m.SYNTHETIC),
        created_at=prior, updated_at=prior, source_repository=m.REPO, source_workflow=m.PARENT_WORKFLOW,
        source_run_id=1, source_run_attempt=1, source_commit_sha='a'*40, parent_hint_mapping_hash='b'*64,
        last_result_hash=None, last_operation_status='SYNTHETIC_TEST_ONLY')
    plan = copy.deepcopy(m.load(m.REQUEST_FILE))
    plan['parent'].update(run_id=1, commit='a'*40, artifact_id=2, artifact_digest='sha256:'+'a'*64,
                         state_hash=state.state_hash, parent_hint_mapping_hash='b'*64)
    env = dict(GITHUB_REPOSITORY=m.REPO, GITHUB_REF='refs/heads/main', GITHUB_EVENT_NAME='workflow_dispatch',
        GITHUB_RUN_ATTEMPT='1', GITHUB_WORKFLOW_REF=m.REPO+'/'+m.WORKFLOW+'@refs/heads/main',
        GITHUB_SHA='c'*40, GITHUB_RUN_ID='3')
    md = root/'metadata'; md.mkdir()
    run = dict(id=1, head_sha='a'*40, path=m.PARENT_WORKFLOW, head_branch='main', status='completed',
               conclusion='success', run_attempt=1, event='schedule',
               repository={'full_name':m.REPO}, head_repository={'full_name':m.REPO})
    artifact = dict(id=2, name='sector-radar-state-bundle', digest='sha256:'+'a'*64,
                    size_in_bytes=plan['parent']['artifact_bytes'], expired=False,
                    workflow_run={'id':1,'head_sha':'a'*40})
    for name, data in {'run.json':run, 'newest.json':{'workflow_runs':[run]},
        'artifacts.json':{'total_count':1,'artifacts':[artifact]},
        'launch.json':{'tag':m.REQUEST,'object':{'type':'commit','sha':'c'*40},
                      'message':json.dumps(dict(request_id=m.REQUEST,run_id='3',authorization_comment_id=5628923881))}}.items():
        m.save(md/name, data)
    m.prepare(root, plan, env)
    days = [last + timedelta(days=i) for i in range(1, (target-last).days+1)]
    calendar = sessions + days + [target + timedelta(days=1)]
    calls = []
    def read(path, params):
        calls.append((path, params))
        if path == m.http.HITHINK_CALENDAR_PATH:
            return {'code':0,'data':{'item':[{'date':d.strftime('%Y%m%d')} for d in calendar]}}
        if path == m.index.HITHINK_INDEX_CATALOG_PATH:
            return copy.deepcopy(catalogue)
        assert path == m.index.HITHINK_INDEX_HISTORY_PATH
        assert int(params['end']) < millis(target+timedelta(days=1))
        return {'code':0, 'data':dict(thscode=params['thscode'], interval='1d', adjust=None,
            timestamp=millis(target), item=[dict(date_ms=millis(d), close_price=str(100+i),
                volume='100', turnover=str(1000+i)) for i,d in enumerate(sessions+days) if d >= sessions[-3]])}
    return bundle, plan, env, now, read, calls


@pytest.mark.parametrize('count,target', [(3,date(2026,9,10)),(3,date(2026,9,11)),(321,date(2026,9,11))])
def test_real_original_composition_and_offline_rebuild(tmp_path, count, target):
    b,p,e,now,read,calls = setup_case(tmp_path,count=count,target=target)
    original = (tmp_path/'input/candidate-events.json').read_bytes()
    report = m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:now)
    assert len(calls) == count + 2 <= 323
    proof = m.verify(tmp_path)
    assert proof['network_calls'] == 0 and proof['restore_authority'] is False
    assert proof['provenance'] == m.SYNTHETIC
    state = m.parse_sector_radar_market_state((tmp_path/'capture/candidate-state.json').read_text())
    assert len(state.sessions) == 127 and state.sessions[-1] == target
    assert state.series[0].closes[-1] == Decimal(226+(target-date(2026,9,9)).days)
    assert (tmp_path/'input/candidate-events.json').read_bytes() == original
    assert (tmp_path/'capture/candidate-events.json').read_bytes() == original
    assert report['unobserved_event_sessions'][0] == '2026-09-10' and report['events_created'] == 0
    assert not (tmp_path/'capture/manifest.json').exists()  # not a production bundle
    with pytest.raises(FileExistsError):
        m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:now)
    assert len(calls) == count + 2


@pytest.mark.parametrize('fault', ['timeout','429','overlap','missing','wrong_code','catalog','secret'])
def test_failure_stops_and_retains_prior_responses(tmp_path, fault):
    b,p,e,now,read,calls = setup_case(tmp_path)
    def broken(path, params):
        value = read(path, params)
        if path == m.index.HITHINK_INDEX_HISTORY_PATH:
            if fault == 'timeout': raise m.http.HithinkRuntimeError('failure_kind=TIMEOUT; elapsed_ms=10000')
            if fault == '429': raise m.http.HithinkRuntimeError('failure_kind=HTTP_429; elapsed_ms=10000')
            if fault == 'overlap': value['data']['item'][0]['close_price']='999'
            if fault == 'missing': value['data']['item'].pop()
            if fault == 'wrong_code': value['data']['thscode']='999999.SH'
            if fault == 'secret': value['secret_key']='canary-not-retained'
        if path == m.index.HITHINK_INDEX_CATALOG_PATH and fault == 'catalog':
            value['data']['item'][0]['name']='Different catalog'
        return value
    with pytest.raises((ValueError, RuntimeError)):
        m.collect(tmp_path,b,p,request=broken,provenance=m.SYNTHETIC,now=lambda:now)
    assert len(calls) <= 3
    report=m.load(tmp_path/'capture/report.json')
    assert report['status']=='FAILED_CLOSED' and report['candidate_state_hash'] is None
    assert (tmp_path/'capture/responses/0000.json').is_file()
    assert not (tmp_path/'capture/candidate-state.json').exists()
    assert 'canary-not-retained' not in '\n'.join(f.read_text() for f in (tmp_path/'capture').rglob('*.json'))
    with pytest.raises(ValueError,match='CAPTURE_NOT_COMPLETE'): m.verify(tmp_path)


@pytest.mark.parametrize('field,value', [('GITHUB_RUN_ATTEMPT','2'),('GITHUB_EVENT_NAME','schedule'),
                                        ('GITHUB_REF','refs/heads/other'),('GITHUB_REPOSITORY','other/repo')])
def test_unauthorized_invocation(tmp_path, field, value):
    b,p,e,now,read,calls=setup_case(tmp_path); e[field]=value
    with pytest.raises(ValueError): m.prepare(tmp_path,p,e)
    assert calls==[]


@pytest.mark.parametrize('name', ['newest','artifact','launch','budget','parent'])
def test_bad_preflight_never_authorizes_capture(tmp_path,name):
    b,p,e,now,read,calls=setup_case(tmp_path)
    if name=='newest': m.save(tmp_path/'metadata/newest.json',{'workflow_runs':[{'id':4,'head_sha':'d'*40}]})
    if name=='artifact':
        x=m.load(tmp_path/'metadata/artifacts.json'); x['artifacts'][0]['expired']=True; m.save(tmp_path/'metadata/artifacts.json',x)
    if name=='launch':
        x=m.load(tmp_path/'metadata/launch.json'); x['message']='{}'; m.save(tmp_path/'metadata/launch.json',x)
    if name=='budget': p['max_hithink_requests']=324
    if name=='parent': p['parent']['state_hash']='f'*64
    with pytest.raises(ValueError): m.prepare(tmp_path,p,e)
    assert calls==[]


def test_budget_time_and_live_injection_refusal(tmp_path):
    b,p,e,now,read,calls=setup_case(tmp_path)
    with pytest.raises(ValueError,match='INJECTED_TRANSPORT_NOT_LIVE'):
        m.collect(tmp_path,b,p,request=read,provenance=m.LIVE,api_key='private')
    clock=iter([0,m.CAPTURE_SECONDS,m.CAPTURE_SECONDS])
    with pytest.raises(ValueError,match='CAPTURE_DEADLINE_REACHED'):
        m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:now,monotonic=lambda:next(clock))
    assert calls==[]


@pytest.mark.parametrize('tamper', ['response','candidate','ledger','extra','report'])
def test_offline_verification_refuses_tampering(tmp_path,tamper):
    b,p,e,now,read,calls=setup_case(tmp_path)
    m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:now)
    paths={'response':'responses/0002.json','candidate':'candidate-state.json',
           'ledger':'candidate-events.json','extra':'responses/9999.json','report':'report.json'}
    (tmp_path/'capture'/paths[tamper]).write_text('{}')
    with pytest.raises((ValueError,KeyError)): m.verify(tmp_path)
    assert len(calls)==5


def test_manual_isolated_workflow_and_unchanged_daily_budget():
    workflow=Path('.github/workflows/sector-recovery-once.yml').read_text()
    assert 'workflow_dispatch:' in workflow and '  schedule:' not in workflow and '  push:' not in workflow
    assert 'timeout-minutes: 150' in workflow and 'timeout-minutes: 140' in workflow
    assert 'group: sector-radar-prospective-state' in workflow and 'cancel-in-progress: false' in workflow
    assert 'git/refs"' in workflow and '--method PATCH' not in workflow and '--method DELETE' not in workflow
    assert 'digest-mismatch: error' in workflow and 'if: always()' in workflow
    assert 'actions/cache' not in workflow and 'SUB2API' not in workflow
    from decision_kernel.runtime.sector_radar_audit import MAX_REQUESTS
    assert MAX_REQUESTS==128


def test_new_state_creation_is_after_source_retrieval_not_backdated(tmp_path):
    b,p,e,now,read,calls=setup_case(tmp_path)
    ticks=iter(now+timedelta(seconds=i) for i in range(30))
    report=m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:next(ticks))
    assert report['candidate_created_at'] > report['requests'][-1]['completed_at'] > report['observed_at']
    assert m.verify(tmp_path)['network_calls']==0


def test_total_request_cap_stops_without_dropping_coverage(tmp_path):
    b,p,e,now,read,calls=setup_case(tmp_path)
    p['max_hithink_requests']=3  # synthetic lower ceiling, never a live override
    with pytest.raises(ValueError,match='REQUEST_LIMIT_REACHED'):
        m.collect(tmp_path,b,p,request=read,provenance=m.SYNTHETIC,now=lambda:now)
    assert len(calls)==3 and not (tmp_path/'capture/candidate-state.json').exists()
