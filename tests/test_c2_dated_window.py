"""Synthetic source controls only; no service request or economic-role acceptance."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('window', ROOT/'.github/scripts/c2-dated-window.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CODES = [f'{600000+i:06d}.SH' for i in range(19)] + ['301190.SZ']
# Explicit synthetic calendar; no fixture is a market calendar or source response.
DAYS = [(date(2026,7,1)+timedelta(days=i)).isoformat() for i in range(55)] + m.DATES
ID = {'GITHUB_REPOSITORY':m.saved.REPOSITORY, 'GITHUB_SHA':'a'*40, 'GITHUB_RUN_ID':'123',
      'GITHUB_RUN_ATTEMPT':'1','GITHUB_REF':'refs/heads/main','GITHUB_EVENT_NAME':'workflow_dispatch'}
START = datetime(2026,10,2,3,tzinfo=timezone.utc)


def millis(day):
    return int(datetime.combine(date.fromisoformat(day),time(),m.own.TZ).timestamp()*1000)


def payload(code, kind):
    if kind == 'actions': return {'code':0,'data':{'thscode':code,'ticker':code[:6],'item':[]}}
    bars = [{'date_ms':millis(d),'open_price':'100','high_price':'100','low_price':'100',
             'close_price':'100','volume':'10000','turnover':'1000000'} for d in DAYS]
    return {'code':0,'data':{'timestamp':int(START.timestamp()*1000), 'thscode':code, 'interval':'1d','adjust':'none','item':bars}}


def base():
    qs = {c:{'quote':{'code':0,'data':{'timestamp':None,'item':[{'thscode':c,'ticker':c[:6],
        'last_price':'100','prev_price':'100','open_price':'100','high_price':'100','low_price':'100',
        'volume':'10000','turnover':'1000000'}]}},'received_at':'2026-10-01T00:00:00+00:00'} for c in CODES}
    prices = {'301190.SZ':m.raw_windows(payload('301190.SZ','history'),payload('301190.SZ','actions'),qs['301190.SZ'],DAYS,START.isoformat())}
    return ({d:{m.BOARD:list(CODES)} for d in m.DATES[-2:]},DAYS,set(CODES),prices,qs,
            {'source_pins':{'synthetic':True},'report_hash':'b'*64,'price_source':{'unavailable_samples':['001246.SZ','920202.BJ']}})


def ticking():
    value = START
    def now():
        nonlocal value
        value += timedelta(seconds=31)
        return value.isoformat()
    return now


def relay(api, params, key, clock):
    rows = [[m.BOARD,params['trade_date'],'分散染料','概念板块',20]] if api=='tdx_index' else [
        [m.BOARD,params['trade_date'],c,'synthetic'] for c in CODES]
    raw=m.common.encoded({'code':0,'data':{'fields':list(m.member.FIELDS[api]),'items':rows},'count':len(rows)})
    return {'api':api,'params':params,'attempts':[{'attempt':1,'classification':'SUCCESS','http_status':200,
        'raw':raw,'requested_at':clock(),'received_at':clock(),'headers':{},'business_code':0,
        'business_error':None,'business_msg':None}]}


def stock(path, params, api_key):
    return payload(params['thscode'], 'history' if path==m.own.HISTORY else 'actions')


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'inputs', lambda root:base())
    monkeypatch.setenv(m.relay.SECRET_ENV, 'synthetic-relay-key')
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY','synthetic-hithink-key')
    for n in ('input-pins.json','member-source.zip','price-source.zip'): (tmp_path/n).write_bytes(b'{}')
    return tmp_path


def run(root, **kwargs):
    return m.capture(root,ID,relay_request=kwargs.pop('relay_request',relay),
                     stock_request=kwargs.pop('stock_request',stock),now=ticking(),pause=lambda n:None,**kwargs)


def test_fixed_missing_days_and_request_budget():
    p=m.plan(base())
    assert len(p)==46 and sum(x['source']=='RELAY' for x in p)==8
    assert {x['params']['trade_date'] for x in p if x['source']=='RELAY'} == {'20260922','20260923','20260924','20260928'}
    assert all(x.get('code')!='301190.SZ' for x in p)
    assert all(x['path']!=m.own.SNAPSHOT for x in p if x['source']=='HITHINK')


def test_original_pilot_wrapper_still_rejects_new_date():
    s=m.plan(base())[0]
    with pytest.raises(ValueError,match='TDX_REQUEST_SCOPE'):
        m.member.qualify(b'{}',{'api':s['api'],'params':s['params']},START.isoformat())


def test_complete_control_replays_all_twenty_with_only_five_day_membership(setup):
    r=run(setup)
    assert r['status']=='FIVE_SESSION_COHORT_INPUTS_COMPLETE'
    assert r['logical_queries']==r['http_attempts']==46
    assert r==m.rebuild(setup,ID)
    ws=r['groups'][0]['windows']
    assert ws[0]['date_labeled_member_and_price_complete'] and ws[0]['price_counts']=={'RAW_COMPARABLE':20}
    assert not ws[1]['date_labeled_member_and_price_complete'] and not ws[2]['date_labeled_member_and_price_complete']
    assert len(ws[1]['missing_member_observation_dates'])==15
    assert len(ws[2]['missing_member_observation_dates'])==55
    assert '没有新采集' not in m.render(r) and '只保留两日' not in m.render(r)
    assert r['rank_or_role_computed'] is False and r['historical_pit_knowledge']=='NOT_ESTABLISHED'
    with pytest.raises(ValueError): run(setup)


@pytest.mark.parametrize('http,classification,error',[(403,'AUTH_OR_ENTITLEMENT','forbidden'),(429,'RATE_LIMIT','rate_limited')])
def test_service_refusal_stops_other_source_too(setup,http,classification,error):
    def denied(api,params,key,clock):
        x=relay(api,params,key,clock);a=x['attempts'][0]
        a.update(http_status=http,classification=classification,raw=m.common.encoded({'code':1,'error':error}),business_code=1)
        return x
    r=run(setup,relay_request=denied,stock_request=lambda *a,**k:pytest.fail('source call'))
    assert r['logical_queries']==1 and r['status']=='WINDOW_INPUTS_WITH_EXPLICIT_GAPS'


def test_bad_member_date_stops_before_stock(setup):
    def wrong(api,params,key,clock):
        x=relay(api,params,key,clock); b=json.loads(x['attempts'][0]['raw']); b['data']['items'][0][1]='20260930'
        x['attempts'][0]['raw']=m.common.encoded(b);return x
    r=run(setup,relay_request=wrong,stock_request=lambda *a,**k:pytest.fail('source'))
    assert r['logical_queries']==1 and r['outcomes'][0]['status']=='SOURCE_INPUT_UNQUALIFIED'


def test_catalog_count_mismatch_keeps_missing_day(setup):
    def wrong(api,params,key,clock):
        x=relay(api,params,key,clock)
        if api=='tdx_index':
            b=json.loads(x['attempts'][0]['raw']);b['data']['items'][0][-1]=21;x['attempts'][0]['raw']=m.common.encoded(b)
        return x
    r=run(setup,relay_request=wrong)
    assert r['logical_queries']==2 and not r['groups'][0]['windows'][0]['date_labeled_member_and_price_complete']


def test_stock_price_gap_not_removed_and_other_planned_stocks_retained(setup):
    def bad(path,params,api_key):
        value=stock(path,params,api_key)
        if params['thscode']==CODES[0] and path==m.own.HISTORY:
            for k in ('open_price','high_price','low_price','close_price'):value['data']['item'][-1][k]='101'
        return value
    r=run(setup,stock_request=bad)
    assert r['logical_queries']==46 and r['groups'][0]['windows'][0]['terminal_member_count']==20
    assert r['groups'][0]['windows'][0]['price_counts']=={'RAW_COMPARABLE':19,'RETAINED_INPUT_GAP':1}
    assert r['status']=='WINDOW_INPUTS_WITH_EXPLICIT_GAPS'


def test_action_exclusion_does_not_produce_zero_return(setup):
    def action(path,params,api_key):
        x=stock(path,params,api_key)
        if path==m.own.ACTIONS and params['thscode']==CODES[0]:
            x['data']['item']=[{'ticker':CODES[0][:6],'ex_date_ms':millis(m.DATES[-2]),'dividend_per_share':'0.1','per_share_bonus':'0'}]
        return x
    r=run(setup,stock_request=action)
    row=next(x for x in r['groups'][0]['windows'][0]['rows'] if x['code']==CODES[0])
    assert row['raw_return'] is None and row['price_status']=='RETAINED_INPUT_GAP'


def test_own_transport_exception_retains_uncertainty_no_retry(setup):
    r=run(setup,stock_request=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('private')))
    assert r['logical_queries']==9 and r['logical_queries_with_receipts']==8 and r['unknown_request_receipts']==1
    assert r['outcomes'][8]['status']=='REQUEST_RECEIPT_UNAVAILABLE'
    assert b'private' not in (setup/'capture.json').read_bytes()


def test_no_credentials_no_source_access(setup,monkeypatch):
    monkeypatch.delenv(m.relay.SECRET_ENV)
    r=run(setup,relay_request=lambda *a,**k:pytest.fail('network'))
    assert r['logical_queries']==0


@pytest.mark.parametrize('case',['raw','identity','scope','extra'])
def test_tamper_refused(setup,case):
    run(setup)
    if case=='raw':(setup/'raw-00-1.json').write_bytes(b'{}')
    elif case=='extra':(setup/'unexpected.json').write_bytes(b'{}')
    elif case=='scope':
        c=json.loads((setup/'capture.json').read_bytes());c['plan'][0]['params']['trade_date']='20260101'
        c['capture_hash']=m.canonical_hash({k:v for k,v in c.items() if k!='capture_hash'});(setup/'capture.json').write_bytes(m.encoded(c))
    with pytest.raises(ValueError):m.rebuild(setup,{**ID,'GITHUB_RUN_ID':'124'} if case=='identity' else ID)


def test_manual_carrier_keeps_ci_single_use_secrets_and_both_concurrency_groups():
    text=(ROOT/'.github/workflows/c2-dated-window.yml').read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text and '\n  push:' not in text
    assert 'radar-global-market-relay' in text and 'hithink-stock-dump-qualification' in text
    assert 'assert not prior' in text and 'github.run_attempt == 1' in text and 'head_sha=$EXPECTED_CODE' in text
    assert 'contents: write' not in text and 'actions: write' not in text
    assert text.count('secrets.TUSHARE_PROXY_API_KEY')==text.count('secrets.HITHINK_FINANCE_API_KEY')==1
    assert 'secrets.' not in text.split('- name: Rebuild saved')[1]
