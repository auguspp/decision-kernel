"""Synthetic acquisition envelopes; real bounded recorder and offline replay."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import hithink_independent_capture as capture
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime import independent_stock_observations as independent
from test_hithink_stock_reading import inputs


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('provider network is prohibited in synthetic acceptance')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(own, 'request_json', denied)


def provider(count=5578, *, mutation=None, closure=False):
    days, at, history, quote, actions = inputs()
    if closure:
        shift = date(2026, 9, 30) - days[-1]
        days = [d + shift for d in days]
        # Shift to an exact fixture calendar ending Sep30, omitting the closure.
        d = date(2026, 9, 30)
        days = []
        while len(days) < 61:
            if d.weekday() < 5:
                days.append(d)
            d -= timedelta(days=1)
        days.reverse()
        for row, d in zip(history['data']['item'], days):
            row['date_ms'] = int(datetime.combine(d, time(), own.TZ).timestamp()*1000)
        at = datetime(2026, 10, 1, 10, 40, tzinfo=own.TZ)
        history['data']['timestamp'] = int(at.timestamp()*1000)
    ms = int(at.timestamp()*1000)
    calendar = {'code': 0, 'data': {'item': [{'date': d.strftime('%Y%m%d')} for d in days]}}
    index_quote = {'code': 0, 'data': {'timestamp': ms, 'total': 1, 'item': [{
        'thscode': '000300.SH', 'ticker': '1B0300', 'last_price': '70', 'prev_price': '69',
        'price_change': '1', 'price_change_ratio_pct': '1.4492753623', 'open_price': '70',
        'high_price': '71', 'low_price': '69', 'volume': '100', 'turnover': '7000'}]}}
    index_history = {'code': 0, 'data': {'thscode': '000300.SH', 'interval': '1d', 'adjust': None,
        'timestamp': history['data']['item'][-1]['date_ms'], 'item': deepcopy(history['data']['item'])}}
    rows = [{'thscode': f'{600000+i:06}.SH', 'ticker': f'{600000+i:06}',
        'last_price': '10', 'prev_price': '10', 'turnover': '0'} for i in range(count)]
    for i in range(min(count, 3)):
        rows[i]['last_price'] = str(20-i)
    calls = []
    def request(path, params):
        calls.append((path, dict(params)))
        if path == independent.HITHINK_CALENDAR_PATH:
            value = deepcopy(calendar)
        elif path == independent.indices.HITHINK_INDEX_SNAPSHOT_PATH:
            value = deepcopy(index_quote)
        elif path == independent.indices.HITHINK_INDEX_HISTORY_PATH:
            value = deepcopy(index_history)
        elif path == own.SNAPSHOT and 'offset' in params:
            offset = int(params['offset'])
            value = {'code': 0, 'data': {'timestamp': ms, 'total': count, 'item': deepcopy(rows[offset:offset+500])}}
        else:
            code = params.get('thscode', params.get('thscodes'))
            if path == own.HISTORY:
                value = deepcopy(history)
            elif path == own.SNAPSHOT:
                value = deepcopy(quote)
                value['data']['item'][0].update(thscode=code, ticker=code[:6])
            else:
                value = deepcopy(actions)
                value['data'].update(thscode=code, ticker=code[:6])
        return mutation(path, params, value, len(calls)) if mutation else value
    return SimpleNamespace(days=days, at=at, request=request, calls=calls)


def run(tmp_path, *, count=5578, mutation=None, closure=False, now=None):
    p = provider(count, mutation=mutation, closure=closure)
    pauses = []
    root = tmp_path/'capture'
    source = capture.capture(root, observed_at=p.at, transport=p.request,
        workflow={'fixture': 'SYNTHETIC_TEST_ONLY'}, now=now or (lambda: p.at), pause=pauses.append,
        closure_date='2026-10-01' if closure else None)
    return root, source, p, pauses


def test_complete_5578_denominator_frozen_k3_exact_24_calls_and_replay(tmp_path):
    root, source, p, pauses = run(tmp_path)
    assert source['status'] == capture.COMPLETE, source['failure_reason']
    assert len(p.calls) == len(source['requests']) == 24
    assert pauses == [20]*23
    report = independent._load(root/'observations.json')
    assert report['coverage']['unique_identities'] == 5578
    assert report['coverage']['complete_pages'] == 12
    assert report['coverage']['independently_selected'] == report['coverage']['selected_qualified'] == 3
    assert [r['thscode'] for r in report['selection']['selected']] == ['600000.SH','600001.SH','600002.SH']
    assert not report['production_admission'] and report['research_authority'] == report['investment_authority'] == 'NONE'
    assert report['replay_controls']['rows'] == [] and 'source_audit_hash' not in report
    assert not any('sector' in name or 'state' in name or 'association' in name for name in source['files'])
    assert set(source['files']) == {'inputs/context.json','selection.json'} | {f'responses/{i:02d}.json' for i in range(1,25)}
    receipt = capture.verify(root, expected_capture_hash=source['capture_hash'])
    assert receipt['network_calls'] == 0 and receipt['request_attempts'] == 24


@pytest.mark.parametrize('count,expected,status', [(7000,26,capture.COMPLETE),(7001,4,capture.FAILED)])
def test_first_declared_total_reserves_full_k3_and_rejects_over_budget(tmp_path,count,expected,status):
    root, source, p, _ = run(tmp_path, count=count)
    assert source['status'] == status
    assert len(p.calls) == expected
    if status == capture.FAILED:
        assert source['failure_reason'] == 'FULL_MARKET_AND_FROZEN_K3_EXCEED_EXISTING_26_REQUEST_BUDGET'
        assert source['selection_hash'] is None
        assert not (root/'selection.json').exists() and not (root/'observations.json').exists()
        assert not any(path in {own.HISTORY,own.ACTIONS} for path,_ in p.calls)
    assert capture.verify(root, expected_capture_hash=source['capture_hash'])['request_attempts'] == expected


@pytest.mark.parametrize('position', [1,4,8,16,18,24])
def test_failed_transport_attempt_counts_no_retry_no_next_batch(tmp_path,position):
    def mutate(path,params,value,index):
        if index == position:
            raise OSError('do not retain credentials or provider text')
        return value
    root, source, p, pauses = run(tmp_path,mutation=mutate)
    assert source['status'] == capture.FAILED and len(p.calls) == position
    assert len(pauses) == position-1
    assert source['requests'][-1]['error_type'] == 'CaptureFailure'
    assert source['failure_reason'] == 'TRANSPORT_REQUEST_FAILED_NO_RETRY'
    assert 'do not retain' not in (root/'capture.json').read_text()
    assert not (root/'observations.json').exists()
    assert capture.verify(root,expected_capture_hash=source['capture_hash'])['status'].startswith('RETAINED_FAILED')


@pytest.mark.parametrize('kind', ['short','duplicate','changed_total','future_ready','stale_ready'])
def test_full_page_qualification_rejects_without_truncation_or_stock_fetch(tmp_path,kind):
    def mutate(path,params,value,index):
        if index == 5:
            if kind == 'short': value['data']['item'].pop()
            elif kind == 'duplicate': value['data']['item'][0]['thscode']='600000.SH'; value['data']['item'][0]['ticker']='600000'
            elif kind == 'changed_total': value['data']['total']-=1
            elif kind == 'future_ready': value['data']['timestamp']+=1000
            else: value['data']['timestamp']-=86400000
        return value
    root, source, p, _ = run(tmp_path,mutation=mutate)
    assert source['status'] == capture.FAILED and len(p.calls)==5
    assert source['selection_hash'] is None and not (root/'observations.json').exists()


def test_known_issuer_business_failure_retains_frozen_selection_and_no_replacement(tmp_path):
    def mutate(path,params,value,index):
        if path == own.HISTORY and params['thscode']=='600000.SH':
            return {'code':3002,'msg':'original failure','data':{}}
        return value
    root, source, p, _ = run(tmp_path,mutation=mutate)
    assert source['status'] == capture.COMPLETE and len(p.calls)==22
    report = independent._load(root/'observations.json')
    assert report['selection']['selected'][0]['thscode']=='600000.SH'
    assert report['selected_observations'][0]['input_failure']['provider_business_code']==3002
    assert report['coverage']['selected_qualified']==2
    assert not any(q.get('thscodes')=='600000.SH' for _,q in p.calls)
    assert capture.verify(root,expected_capture_hash=source['capture_hash'])['request_attempts']==22


def test_global_provider_failure_stops_remaining_frozen_stocks(tmp_path):
    def mutate(path,params,value,index):
        return {'code':429,'data':{}} if index==16 else value
    root, source, p, _ = run(tmp_path,mutation=mutate)
    assert source['status']==capture.FAILED and len(p.calls)==16
    assert (root/'selection.json').exists() and not (root/'observations.json').exists()


def test_oct1_explicit_reviewed_closure_keeps_real_clock_and_sep30_anchor(tmp_path):
    root, source, _, _ = run(tmp_path,closure=True)
    assert source['status']==capture.COMPLETE, source['failure_reason']
    report=independent._load(root/'observations.json')
    assert report['context']['comparison_session']=='2026-09-30'
    assert report['context']['reference']['closed_dates']==['2026-10-01']
    assert report['context']['started_at'].startswith('2026-10-01')
    assert independent._load(root/'inputs/closure-evidence.json')==capture.CLOSURE_EVIDENCE
    assert capture.verify(root,expected_capture_hash=source['capture_hash'])['network_calls']==0


def test_holiday_without_explicit_closure_is_not_weekday_inference(tmp_path):
    p=provider(closure=True)
    source=capture.capture(tmp_path/'capture',observed_at=p.at,transport=p.request,workflow={},now=lambda:p.at,pause=lambda n:None)
    assert source['status']==capture.FAILED and len(p.calls)==3


@pytest.mark.parametrize('name',['responses/01.json','responses/04.json','selection.json','observations.json','README.txt'])
def test_tampered_bytes_or_rehashed_derived_output_cannot_replace_replay(tmp_path,name):
    root,source,_,_=run(tmp_path,count=503)
    assert source['status']==capture.COMPLETE
    path=root/name
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError):capture.verify(root,expected_capture_hash=source['capture_hash'])


def environment():
    return {'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1',
        'GITHUB_SHA':'a'*40,'GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_dispatch',
        'GITHUB_WORKFLOW_REF':'auguspp/decision-kernel/.github/workflows/hithink-stock-dump-trial.yml@refs/heads/main',
        'GITHUB_JOB':capture.PURPOSE,'TRIAL_PURPOSE':capture.PURPOSE}


@pytest.mark.parametrize('key,value',[('GITHUB_RUN_ATTEMPT','2'),('GITHUB_EVENT_NAME','schedule'),
    ('GITHUB_JOB','stock-reading'),('GITHUB_REF','refs/heads/feature'),('STOCK_MARKET_RUN_ID','123'),
    ('STOCK_DISCOVERY_PAGE','hash:0'),('RECOVERY_KEY','retry'),('TRIAL_PURPOSE','stock-reading')])
def test_wrong_manual_identity_or_legacy_inputs_rejected_before_transport(key,value):
    env=environment(); assert capture.intent(env)['trial_purpose']==capture.PURPOSE
    env[key]=value
    with pytest.raises(ValueError):capture.intent(env)


def test_existing_live_stock_selector_excludes_distinct_independent_job_even_on_failure(tmp_path):
    from test_current_state_stock_query_scope import collector,stock_job
    from test_current_state import run as workflow_run
    original=workflow_run(10,lane='stock')
    for status in ('success','failure','cancelled'):
        isolated=workflow_run(11,lane='stock',conclusion=status)
        c,api=collector(tmp_path,[isolated,original],{10:stock_job(),11:{'total_count':2,'jobs':[
            {'name':'stock-reading','conclusion':'skipped'}, {'name':capture.PURPOSE,'conclusion':status}]}})
        assert c.runs('stock')==([original],True)
        assert not api.writes


def test_workflow_has_distinct_manual_only_job_no_sector_or_dispatch():
    value=Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    job=value.split('  stock-independent-observations:\n',1)[1].split('  stock-reading:\n',1)[0]
    assert "inputs.trial-purpose == 'stock-independent-observations'" in job
    assert "github.event_name == 'workflow_dispatch'" in job and 'github.run_attempt == 1' in job
    assert 'actions/download-artifact' not in job and 'gh run download' not in job and 'dispatches' not in job
    assert "name: stock-independent-observations-${{ github.run_id }}-${{ github.run_attempt }}" in job
    assert 'ci.yml/runs' in job and 'git/ref/heads/main' in job
    assert 'secrets.HITHINK_FINANCE_API_KEY' in job and 'DAILY_CHAIN_DISPATCH_TOKEN' not in job


def test_actions_3002_is_failure_not_empty_actions_and_selection_precedes_history(tmp_path):
    def mutate(path,params,value,index):
        if path==own.HISTORY:
            assert (tmp_path/'capture/selection.json').is_file()
        return {'code':3002,'data':{}} if path==own.ACTIONS and params['thscode']=='600001.SH' else value
    root,source,p,_=run(tmp_path,mutation=mutate)
    assert source['status']==capture.COMPLETE and len(p.calls)==24
    report=independent._load(root/'observations.json')
    assert report['selected_observations'][1]['input_failure']['phase']=='CORPORATE_ACTIONS'
    assert report['selected_observations'][1]['status']=='REQUEST_FAILED'
    assert report['selected_observations'][1]['stock_path'] is None
    capture.verify(root,expected_capture_hash=source['capture_hash'])


@pytest.mark.parametrize('mutation',['missing_recent','old_gap','future_history','future_quote'])
def test_reused_own_stock_qualification_and_receipts(tmp_path,mutation):
    def change(path,params,value,index):
        if params.get('thscode',params.get('thscodes'))!='600000.SH':return value
        if path==own.HISTORY and mutation=='missing_recent':value['data']['item'].pop(-2)
        elif path==own.HISTORY and mutation=='old_gap':value['data']['item'].pop(1)
        elif path==own.HISTORY and mutation=='future_history':value['data']['timestamp']+=1000
        elif path==own.SNAPSHOT and mutation=='future_quote':value['data']['timestamp']=int(provider().at.timestamp()*1000)+1000
        return value
    root,source,p,_=run(tmp_path,count=503,mutation=change)
    if mutation.startswith('future'):
        assert source['status']==capture.FAILED
        assert p.calls[-1][0]==(own.HISTORY if mutation=='future_history' else own.SNAPSHOT)
        assert not (root/'observations.json').exists()
    else:
        assert source['status']==capture.COMPLETE
        row=independent._load(root/'observations.json')['selected_observations'][0]
        if mutation=='missing_recent':assert row['status']=='DATA_INSUFFICIENT'
        else:assert row['stock_path']['returns']['60'] is None
        capture.verify(root,expected_capture_hash=source['capture_hash'])


@pytest.mark.parametrize('damage',['calendar_includes_closed','wrong_anchor','ready_before_close','evidence_changed'])
def test_closure_exception_does_not_waive_calendar_benchmark_or_receipt_contract(tmp_path,damage):
    def mutate(path,params,value,index):
        if path==independent.HITHINK_CALENDAR_PATH and damage=='calendar_includes_closed':
            value['data']['item'].append({'date':'20261001'})
        if path==independent.indices.HITHINK_INDEX_SNAPSHOT_PATH and damage=='wrong_anchor':
            value['data']['item'][0]['last_price']='71'
        if path==own.SNAPSHOT and 'offset' in params and damage=='ready_before_close':
            value['data']['timestamp']=int(datetime(2026,9,30,15,29,tzinfo=own.TZ).timestamp()*1000)
        return value
    root,source,p,_=run(tmp_path,closure=True,mutation=mutate)
    if damage=='evidence_changed':
        assert source['status']==capture.COMPLETE
        evidence=independent._load(root/'inputs/closure-evidence.json');evidence['notice_facts']['closure_start']='2026-09-29'
        (root/'inputs/closure-evidence.json').write_text(canonical_json(evidence)+'\n')
        with pytest.raises(ValueError):capture.verify(root,expected_capture_hash=source['capture_hash'])
    else:
        assert source['status']==capture.FAILED and len(p.calls)<=4


def test_one_capture_uses_decimal_28_regardless_of_ambient_context(tmp_path):
    from decimal import localcontext
    a=tmp_path/'a';b=tmp_path/'b';a.mkdir();b.mkdir()
    root,source,_,_=run(a,count=503)
    expected=independent._read(root/'observations.json')
    with localcontext() as ctx:
        ctx.prec=7
        other,changed,_,_=run(b,count=503)
        assert changed['status']==capture.COMPLETE
        assert independent._read(other/'observations.json')==expected
        capture.verify(other,expected_capture_hash=changed['capture_hash'])


def test_no_smaller_sample_fallback_and_create_only_output(tmp_path):
    root,source,p,_=run(tmp_path,count=2)
    assert source['status']==capture.FAILED and len(p.calls)==4
    assert source['selection_hash'] is None and not (root/'observations.json').exists()
    saved=(root/'capture.json').read_bytes()
    with pytest.raises(ValueError,match='CREATE_ONLY'):
        capture.capture(root,observed_at=p.at,transport=p.request,workflow={})
    assert (root/'capture.json').read_bytes()==saved


def test_expired_clock_prevents_first_request_instead_of_backdating(tmp_path):
    p=provider();root=tmp_path/'capture'
    source=capture.capture(root,observed_at=p.at,transport=p.request,workflow={},
        now=lambda:p.at+timedelta(minutes=31),pause=lambda n:None)
    assert source['status']==capture.FAILED and not p.calls and not source['requests']
    assert source['observed_at']==p.at.isoformat()
    assert capture.verify(root,expected_capture_hash=source['capture_hash'])['request_attempts']==0
