"""Synthetic dated observations and native saved-reader seam, no network/trading.

Full source capture/verify and the original archive reader run here. Only shared
Git quota is stubbed; the synthetic LIVE-shaped receipt is not source evidence.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from types import SimpleNamespace
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_auction_next_session as n
from decision_kernel.runtime import stock_market_inputs as prices
from decision_kernel.runtime import independent_stock_reading as independent
from test_d_auction_follow_through import mixed
from test_d_auction_probe import offline
from test_stock_market_inputs import make_request, NOW, body

AT = '2026-10-09T09:00:00+00:00'
CHECK = '2026-10-09T10:00:00+00:00'
M, R = 'a'*40, 'b'*40
LIMIT = 128*1024*1024


def descriptor(raw, path):
    return {'bytes': len(raw), 'sha256': model.sha256(raw), 'git_blob': model.blob_sha(raw),
            'read_path': path, 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}


def cohort(tmp_path):
    auction, _ = mixed(tmp_path)
    return n.seed(auction, {'source_archive': {'sha256': 'c'*64, 'read_path': 'auction.zip'}}, CHECK)


def source(rows, day='2026-10-09'):
    return {'source': prices.SOURCE, 'provenance': 'LIVE_TUSHARE_RELAY',
            'tables': {('daily', day.replace('-', '')): rows}, 'coverage': {},
            'received_through': AT, 'archive': {'sha256': 'd'*64, 'read_path': 'daily.zip'}}


def test_add_open_only_to_same_nine_calls_keep_legacy_replay(tmp_path):
    for include in (False, True):
        root = tmp_path/str(include)
        report = prices.capture(root, observed_at=NOW, workflow={}, request=make_request(),
                                clock=NOW.isoformat, include_open=include)
        assert prices.verify(root) == report and report['source_requests'] == 9
        receipt = prices.loads((root/'receipt.json').read_bytes())
        for call in receipt['calls'][1:]:
            fields = call['params']['fields'].split(',')
            assert ('open' in fields) == (include and call['api'] == 'daily')
        assert report['qualified_windows'] == {'5': 1, '20': 1, '60': 1}
        assert ('daily_fields_requested' in report) == include
        receipt['daily_fields'] = 'close,high'
        with pytest.raises(ValueError, match='DAILY_FIELD_SCOPE'):
            prices.build(receipt, {})


def test_target_is_explicit_next_open_not_calendar_day_or_first_success(tmp_path):
    c = cohort(tmp_path); c['market_session'] = '2026-10-09'
    values = {'2026-10-10': False, '2026-10-11': False, '2026-10-12': True, '2026-10-13': True}
    target, prefix, gap = n.target_session(c, values, '2026-10-13')
    assert target == '2026-10-12' and not gap and len(prefix) == 3
    later = source({'600001.SH': {'open': '20', 'close': '30'}}, day='2026-10-13')
    out = n.project(c, values, '2026-10-13', [later], checked_at='2026-10-13T10:00:00Z')
    assert out['target_session'] == target and all(r[2:4] == [None,None] for r in out['rows'])
    assert len(out['rows']) == 6


def test_calendar_gap_and_revision_never_move_anchor(tmp_path):
    c = cohort(tmp_path)
    out = n.project(c, {'2026-10-10': True}, '2026-10-10', [], checked_at=CHECK)
    assert out['calendar_gap'] == '2026-10-09' and out['target_session'] is None
    established = n.project(c, {'2026-10-09': True}, '2026-10-09', [], checked_at=CHECK)
    with pytest.raises(ValueError, match='calendar revised'):
        n.target_session(established, {'2026-10-09': False, '2026-10-10': True}, '2026-10-10')


def test_missing_open_factor_does_not_block_raw_close_and_all_groups_retained(tmp_path):
    c = cohort(tmp_path); before = deepcopy(c)
    out = n.project(c, {'2026-10-09': True}, '2026-10-09', [source({
        '600001.SH': {'close': '10.1000'}, '600002.SH': {'open': '11.000', 'close': '10'},
        '600003.SH': {'open': '-1', 'close': '9'}, '600004.SH': {'open': 'NaN', 'close': '8'},
        '600005.SH': {'open': '10', 'close': '7'}})], checked_at=CHECK)
    assert c == before and len(out['rows']) == 6
    assert out['rows'][0][2:] == [None, '10.1000', 'FIELD_NOT_RETURNED', 'RAW_QUOTE_OBSERVED']
    assert out['rows'][2][2] is None and out['rows'][2][-2] == 'QUOTE_VALUE_INVALID'
    assert out['rows'][-1][-1] == 'COHORT_IDENTITY_UNRESOLVED'
    assert [out['groups'][g]['denominator'] for g in n.GROUPS] == [2,1,1,1,1]
    assert sum(g['close_observed'] for g in out['groups'].values()) == 5
    assert out['price_basis'] == 'RAW_OPEN_CLOSE_ONLY_NOT_CROSS_SESSION_ADJUSTED_RETURN'


def test_whole_quote_source_only_no_row_splice(tmp_path):
    c = cohort(tmp_path)
    first = source({'600001.SH': {'open': '11','close':'10'}})
    second = source({'600002.SH': {'open': '21','close':'20'}})
    second['archive']['sha256'] = 'e'*64
    out = n.project(c, {'2026-10-09': True}, '2026-10-09', [first,second], checked_at=CHECK)
    assert out['rows'][0][2:4] == ['11','10'] and out['rows'][1][2:4] == [None,None]
    assert out['quote_source'] == first['archive']


def test_unchanged_first_clock_and_later_gap_preserve_whole_observation(tmp_path):
    c = cohort(tmp_path); sources = [source({'600001.SH': {'open':'11','close':'10'}})]
    old = n.project(c, {'2026-10-09': True}, '2026-10-09', sources, checked_at=CHECK)
    raw = prices.dumps(old)
    same = n.project(old, {'2026-10-09': True}, '2026-10-09', sources, checked_at='2026-10-10T10:00:00Z')
    assert same['result_first_recorded_at'] == CHECK and same['observation'] == 'UNCHANGED_DATED_OBSERVATIONS'
    kept = n.project(same, {'2026-10-09': True}, '2026-10-09', [], checked_at='2026-10-10T10:00:00Z')
    assert kept['rows'] == old['rows'] and kept['quote_source'] == old['quote_source']
    assert kept['current_quote_gap'] == 'TARGET_QUOTE_NOT_IN_CURRENT_SAVED_SOURCES'
    assert prices.dumps(old) == raw


@pytest.mark.parametrize('damage', ['members', 'future', 'wrong-source'])
def test_bad_identity_and_future_source_are_rejected(tmp_path, damage):
    c = cohort(tmp_path); s = source({'600001.SH': {'close':'10'}})
    if damage == 'members': c['members'][0]['symbol'] = '600006.SH'
    elif damage == 'future': s['received_through'] = '2099-01-01T00:00:00Z'
    else: s['source'] = 'FOREIGN'
    with pytest.raises(ValueError): n.project(c, {'2026-10-09': True}, '2026-10-09', [s], checked_at=CHECK)


def test_pending_cohort_is_not_replaced_by_new_auction_and_completed_archive_is_explicit(tmp_path):
    old = cohort(tmp_path); current = deepcopy(old); current['id'] = 'f'*64
    current['market_session'] = '2026-10-09'
    loc = {'reading_commit': R, 'file': {'read_path': n.PATH}}
    items, archived = n.retain_cohorts({'cohorts':[old]}, current, loc)
    assert len(items) == 2 and not archived
    assert items[0]['auction_origin']['reading_commit'] == R
    old.update(status='NEXT_SESSION_OBSERVED_WITH_GAPS', target_session='2026-10-09')
    items, archived = n.retain_cohorts({'cohorts':[old]}, current, loc)
    assert len(items) == 2 and not archived  # Keep T+1 result through that day's repeated readings.
    current['market_session'] = '2026-10-12'
    items, archived = n.retain_cohorts({'cohorts':[old]}, current, loc)
    assert len(items) == len(archived) == 1 and archived[0]['reading_commit'] == R
    items, _ = n.retain_cohorts({'cohorts':[old]}, None, loc)
    assert len(items) == 1  # A later failed auction never deletes the old result.


def fixture_collector(tmp_path, monkeypatch):
    """Source-shaped synthetic receipt passes real replay, not a live assertion."""
    auction, _ = mixed(tmp_path)
    auction['provenance'] = 'LIVE_TUSHARE_RELAY'
    at = datetime.fromisoformat(AT)
    fetch = make_request(at)
    def request(api, params):
        result = fetch(api,params)
        if api == 'daily':
            result['attempts'][0]['raw'] = body(api,['ts_code','trade_date','close','open'],
                [['600001.SH',params['trade_date'],'10.10','10.5000']])
        return result
    identity = {'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
        'GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'daily-market-inputs','GITHUB_EVENT_NAME':'workflow_dispatch',
        'GITHUB_WORKFLOW_REF':'auguspp/decision-kernel/'+prices.WORKFLOW+'@refs/heads/main',
        'GITHUB_SHA':M,'GITHUB_RUN_ID':'111'}
    root = tmp_path/'daily'; report = prices.capture(root, observed_at=at, workflow=identity, request=request, clock=at.isoformat)
    for file in ('receipt.json','report.json'):
        data = prices.loads((root/file).read_bytes()); data['provenance'] = 'LIVE_TUSHARE_RELAY'
        (root/file).write_bytes(prices.dumps(data))
    report = prices.verify(root)
    files = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    stream = BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items(): z.writestr(k,v)
    raw = stream.getvalue(); archive = {**descriptor(raw,'sources/daily.zip'), 'artifact_id':111,
        'expires_at':'2099-01-01T00:00:00Z','origin_run':{'id':111,'head_sha':M}}
    collector = SimpleNamespace(files={'README.md':b'original\n','price-original':b'original',
        'sources/daily.zip':raw}, previous=None, previous_commit=None, code_commit=M,
        now=lambda: CHECK, api=SimpleNamespace(calls=0,max_calls=10000), archive_cache={111:(files,archive)})
    def retain(path, raw):
        assert path not in collector.files
        collector.files[path] = raw
        return descriptor(raw,path)
    collector.retain = retain
    dd = {'status':report['status'],'file':retain('daily.json',prices.dumps(report)),
        'publication_verification':'REBUILT_FROM_EXACT_RETAINED_RESPONSE_BYTES',
        'market_session':report['market_session'],'source_archive':archive}
    dd['auction_probe'] = {'status':auction['status'],'file':retain('auction.json',prices.dumps(auction)),
        'publication_verification':'REBUILT_FROM_RETAINED_RESPONSE_BYTES',
        'market_session':auction['market_session'],'source_archive':{'sha256':'c'*64,'read_path':'synthetic-auction.zip'}}
    index = retain(independent.PATH,prices.dumps({'daily_market_inputs':dd}))
    baseline = model.assemble(code_commit=M, checked_at=AT, check_started_at=AT,
        lanes={}, research={independent.KEY:index,'records':[{'id':'original'}],'handoffs':{'active':[]}},capabilities=[],refresh_identity={})
    collector.files['current-state.json'] = model.read_package_bytes(baseline)
    monkeypatch.setattr(n,'_reserve',lambda *a,**kw:None)
    return collector,baseline


def test_actual_parser_archive_and_attach_with_open_and_no_extra_requests(tmp_path, monkeypatch):
    c,b = fixture_collector(tmp_path,monkeypatch); before = deepcopy((b,c.files))
    out = n.attach(c,b,retained_limit=LIMIT)
    assert 'read_path' in out['research'][n.KEY]
    report = prices.loads(c.files[n.PATH]); model.validate_read_package(out)
    assert report['cohorts'][0]['target_session'] == '2026-10-09'
    assert report['cohorts'][0]['rows'][0][2:4] == ['10.5000','10.10']
    assert report['new_source_requests'] == 0 and report['investment_authority'] == 'NONE'
    assert sum(g['denominator'] for g in report['cohorts'][0]['groups'].values()) == 6
    assert out['generated_at'] == report['checked_at'] == CHECK and b == before[0]
    assert all(c.files[k] == v for k,v in before[1].items() if k not in ('README.md','current-state.json'))
    assert n.PATH.encode() in c.files['README.md']


def test_failure_then_recovery_uses_exact_successful_predecessor(tmp_path, monkeypatch):
    c,b = fixture_collector(tmp_path,monkeypatch)
    first = n.attach(c,b,retained_limit=LIMIT); raw = c.files[n.PATH]; old = prices.loads(raw)
    prior_files = dict(c.files); c.files = {k:v for k,v in prior_files.items() if k != n.PATH}
    c.previous, c.previous_commit = first, R
    c.api.file = lambda path,ref: raw if (path,ref)==(n.PATH,R) else (_ for _ in ()).throw(AssertionError('wrong ref'))
    saved_cache = c.archive_cache; c.archive_cache = {}
    failed = n.attach(c,b,retained_limit=LIMIT)
    assert failed['research'][n.KEY]['previous_result']['reading_commit'] == R
    assert n.PATH not in c.files
    c.previous, c.previous_commit, c.archive_cache = failed, 'e'*40, saved_cache
    recovered = n.attach(c,b,retained_limit=LIMIT)
    assert 'read_path' in recovered['research'][n.KEY]
    report = prices.loads(c.files[n.PATH])
    assert report['previous_result']['reading_commit'] == R
    assert report['cohorts'][0]['first_recorded_at'] == old['cohorts'][0]['first_recorded_at']
    assert report['cohorts'][0]['result_first_recorded_at'] == old['cohorts'][0]['result_first_recorded_at']


@pytest.mark.parametrize('failure', ['raw','quota','capacity','backwards'])
def test_failures_do_not_erase_prior_reading_inputs(tmp_path,monkeypatch,failure):
    c,b = fixture_collector(tmp_path,monkeypatch); before = dict(c.files)
    if failure == 'raw': c.files['sources/daily.zip'] += b'corrupt'
    if failure == 'quota':
        def denied(*a,**k): raise ValueError('synthetic quota')
        monkeypatch.setattr(n,'_reserve',denied)
    if failure == 'backwards': c.now = lambda:'2026-10-08T10:00:00Z'
    limit = 1 if failure == 'capacity' else LIMIT
    out = n.attach(c,b,retained_limit=limit)
    assert n.PATH not in c.files and out['research']['records'] == b['research']['records']
    assert c.files['price-original'] == before['price-original']
    assert failure != 'capacity' or out is b


def test_real_delivery_wires_after_horizon_before_optional_structure():
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    module = ast.parse((root/'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text())
    collect = next(n for n in ast.walk(module) if isinstance(n, ast.FunctionDef) and n.name == 'collect')
    imports = [(n.lineno,n.module) for n in ast.walk(collect) if isinstance(n, ast.ImportFrom)]
    line = {name:i for i,name in imports}
    assert line['d_horizon_follow_up'] < line['d_auction_next_session'] < line['d_price_structure_reading']
