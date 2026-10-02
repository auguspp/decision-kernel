"""Offline synthetic retained-format controls; no source request or role acceptance."""
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


def seal(root, manifest):
    manifest['capture_hash'] = m.canonical_hash({k:v for k,v in manifest.items() if k != 'capture_hash'})
    (root/'capture.json').write_bytes(m.encoded(manifest))


def replace_body(root, manifest, index, body):
    attempt = manifest['records'][index]['attempts'][0]
    raw = m.encoded(body)
    (root/attempt['body']).write_bytes(raw)
    attempt.update(bytes=len(raw), sha256=m.saved.sha256(raw))
    seal(root, manifest)


def stop_after(root, manifest, index):
    for record in manifest['records'][index+1:]:
        for attempt in record['attempts']:
            if attempt['body']:
                (root/attempt['body']).unlink()
        record.update(status='NOT_ATTEMPTED_STOP', attempts=[])
    seal(root, manifest)


@pytest.fixture
def retained(tmp_path, monkeypatch):
    # Construct a known saved format, not the retired network writer or a mock service run.
    monkeypatch.setattr(m, 'inputs', lambda root: base())
    def forbidden(*args, **kwargs):
        pytest.fail('offline reader attempted source access')
    monkeypatch.setattr(m.relay, 'request', forbidden)
    monkeypatch.setattr(m.own, 'request_json', forbidden)
    for name in ('input-pins.json', 'member-source.zip', 'price-source.zip'):
        (tmp_path/name).write_bytes(b'{}')
    specs = m.plan(base())
    records = []
    for i, spec in enumerate(specs):
        if spec['source'] == 'RELAY':
            api, params = spec['api'], spec['params']
            rows = [[m.BOARD, params['trade_date'], '分散染料', '概念板块', 20]] if api == 'tdx_index' else [
                [m.BOARD, params['trade_date'], c, 'synthetic'] for c in CODES]
            body = {'code':0, 'data':{'fields':list(m.member.FIELDS[api]), 'items':rows}, 'count':len(rows)}
        else:
            body = payload(spec['code'], spec['kind'])
        raw = m.encoded(body); name = f'raw-{i:02d}-1.json'
        (tmp_path/name).write_bytes(raw)
        attempt = {'attempt':1, 'classification':'SUCCESS', 'http_status':200,
            'body':name, 'bytes':len(raw), 'sha256':m.saved.sha256(raw),
            'requested_at':(START+timedelta(seconds=60*i+1)).isoformat(),
            'received_at':(START+timedelta(seconds=60*i+2)).isoformat(),
            'headers':{}, 'business_code':0, 'business_error':None, 'business_msg':None}
        records.append({'index':i, 'spec':spec, 'status':'SUCCESS', 'attempts':[attempt]})
    manifest = {'pilot':m.PILOT, 'workflow':m.WORKFLOW, 'identity':ID,
        'authority':m.joined.AUTHORITY, 'started_at':START.isoformat(),
        'finished_at':(START+timedelta(hours=1)).isoformat(), 'complete':True,
        'plan':specs, 'records':records}
    seal(tmp_path, manifest)
    return tmp_path, manifest


def test_historical_plan_is_not_new_authority():
    p = m.plan(base())
    assert len(p) == 46 and sum(x['source'] == 'RELAY' for x in p) == 8
    assert {x['params']['trade_date'] for x in p if x['source']=='RELAY'} == {'20260922','20260923','20260924','20260928'}
    assert all(x.get('code') != '301190.SZ' for x in p)
    assert all(x['path'] != m.own.SNAPSHOT for x in p if x['source']=='HITHINK')


def test_original_pilot_wrapper_still_rejects_new_date():
    s = m.plan(base())[0]
    with pytest.raises(ValueError, match='TDX_REQUEST_SCOPE'):
        m.member.qualify(b'{}', {'api':s['api'], 'params':s['params']}, START.isoformat())


def test_complete_synthetic_saved_format_is_not_historical_role_acceptance(retained):
    root, _ = retained
    r = m.rebuild(root, ID)
    assert r == m.rebuild(root, ID)
    assert r['status'] == 'FIVE_SESSION_COHORT_INPUTS_COMPLETE'
    assert r['logical_queries'] == r['http_attempts'] == 46
    ws = r['groups'][0]['windows']
    assert ws[0]['date_labeled_member_and_price_complete'] and ws[0]['price_counts']=={'RAW_COMPARABLE':20}
    assert not ws[1]['date_labeled_member_and_price_complete'] and not ws[2]['date_labeled_member_and_price_complete']
    assert len(ws[1]['missing_member_observation_dates']) == 15
    assert len(ws[2]['missing_member_observation_dates']) == 55
    assert r['rank_or_role_computed'] is False and r['historical_pit_knowledge']=='NOT_ESTABLISHED'
    assert r['production_admission'] is False and r['source_calls_during_replay'] == 0


@pytest.mark.parametrize('http,classification,error', [(403,'AUTH_OR_ENTITLEMENT','forbidden'), (429,'RATE_LIMIT','rate_limited')])
def test_saved_service_refusal_requires_stop(retained, http, classification, error):
    root, manifest = retained
    record = manifest['records'][0]; a = record['attempts'][0]
    a.update(http_status=http, classification=classification, business_code=1, business_error=error)
    record['status'] = classification
    replace_body(root, manifest, 0, {'code':1, 'error':error})
    with pytest.raises(ValueError, match='stop was ignored'):
        m.rebuild(root, ID)
    stop_after(root, manifest, 0)
    r = m.rebuild(root, ID)
    assert r['logical_queries'] == 1 and r['status'] == 'WINDOW_INPUTS_WITH_EXPLICIT_GAPS'


@pytest.mark.parametrize('case', ['date', 'count'])
def test_bad_saved_members_do_not_complete_window(retained, case):
    root, manifest = retained
    body = json.loads((root/'raw-00-1.json').read_bytes())
    body['data']['items'][0][1 if case=='date' else -1] = '20260930' if case=='date' else 21
    replace_body(root, manifest, 0, body)
    stop_after(root, manifest, 0 if case=='date' else 1)
    r = m.rebuild(root, ID)
    assert not r['groups'][0]['windows'][0]['date_labeled_member_and_price_complete']
    assert r['outcomes'][0 if case=='date' else 1]['status'] == 'SOURCE_INPUT_UNQUALIFIED'


def test_saved_price_gap_keeps_complete_denominator(retained):
    root, manifest = retained
    body = json.loads((root/'raw-08-1.json').read_bytes())
    for k in ('open_price','high_price','low_price','close_price'):
        body['data']['item'][-1][k] = '101'
    replace_body(root, manifest, 8, body)
    r = m.rebuild(root, ID); five = r['groups'][0]['windows'][0]
    assert five['terminal_member_count'] == 20
    assert five['price_counts'] == {'RAW_COMPARABLE':19,'RETAINED_INPUT_GAP':1}
    assert r['status'] == 'WINDOW_INPUTS_WITH_EXPLICIT_GAPS'


def test_saved_action_does_not_produce_zero_return(retained):
    root, manifest = retained
    body = json.loads((root/'raw-09-1.json').read_bytes())
    body['data']['item'] = [{'ticker':CODES[0][:6], 'ex_date_ms':millis(m.DATES[-2]),
                            'dividend_per_share':'0.1', 'per_share_bonus':'0'}]
    replace_body(root, manifest, 9, body)
    r = m.rebuild(root, ID)
    row = next(x for x in r['groups'][0]['windows'][0]['rows'] if x['code']==CODES[0])
    assert row['raw_return'] is None and row['price_status'] == 'RETAINED_INPUT_GAP'


def test_saved_receipt_uncertainty_not_zero_calls(retained):
    root, manifest = retained
    (root/'raw-08-1.json').unlink()
    manifest['records'][8].update(status='REQUEST_RECEIPT_UNAVAILABLE', attempts=[])
    stop_after(root, manifest, 8)
    r = m.rebuild(root, ID)
    assert r['logical_queries'] == 9 and r['logical_queries_with_receipts'] == 8
    assert r['unknown_request_receipts'] == 1


@pytest.mark.parametrize('case', ['raw','identity','scope','extra'])
def test_tamper_refused(retained, case):
    root, manifest = retained
    if case == 'raw': (root/'raw-00-1.json').write_bytes(b'{}')
    elif case == 'extra': (root/'unexpected.json').write_bytes(b'{}')
    elif case == 'scope':
        manifest['plan'][0]['params']['trade_date'] = '20260101'
        seal(root, manifest)
    with pytest.raises(ValueError):
        m.rebuild(root, {**ID,'GITHUB_RUN_ID':'124'} if case=='identity' else ID)


@pytest.mark.parametrize('business_code', [3002, None, False, '0'])
def test_saved_action_failure_preserves_body_and_stops(retained, business_code):
    root, manifest = retained
    body = json.loads((root/'raw-09-1.json').read_bytes()); body['code'] = business_code
    manifest['records'][9]['attempts'][0]['business_code'] = business_code
    replace_body(root, manifest, 9, body)
    with pytest.raises(ValueError, match='stop was ignored'):
        m.rebuild(root, ID)
    stop_after(root, manifest, 9)
    r = m.rebuild(root, ID)
    assert r['outcomes'][9]['status'] == 'SOURCE_INPUT_UNQUALIFIED'
    assert r['logical_queries'] == 10 and r['groups'][0]['windows'][0]['terminal_member_count'] == 20
    assert json.loads((root/'raw-09-1.json').read_bytes())['code'] == business_code


def test_active_capture_and_workflow_are_retired():
    assert not hasattr(m, 'capture') and not (ROOT/m.WORKFLOW).exists()
    for mode in ('capture','prepare'):
        with pytest.raises(SystemExit) as exc:
            m.main([mode,'--root','unused','--run-id','123','--code-commit','a'*40])
        assert exc.value.code == 2


def test_verify_is_repeatably_read_only_without_credentials(retained, monkeypatch):
    root, _ = retained
    monkeypatch.delenv(m.relay.SECRET_ENV, raising=False)
    monkeypatch.delenv('HITHINK_FINANCE_API_KEY', raising=False)
    r = m.rebuild(root, ID); (root/'result').mkdir()
    (root/'result/join.json').write_bytes(m.encoded(r))
    (root/'result/join.md').write_bytes(m.render(r).encode())
    def snapshot():
        return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    before = snapshot()
    args = ['verify','--root',str(root),'--run-id','123','--code-commit','a'*40]
    assert m.main(args) == m.main(args) == 0
    assert snapshot() == before and not (root/'verification.json').exists()
    (root/'result/join.md').write_text('changed')
    with pytest.raises(ValueError, match='offline reconstruction differs'):
        m.main(args)
