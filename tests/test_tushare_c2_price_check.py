"""Synthetic source/negative controls; no live Relay, source secrets or trading claim."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import tushare_c2_price_check as c
from decision_kernel.identity import canonical_json


@pytest.fixture
def sample(monkeypatch):
    days = [(datetime(2026, 1, 1) + timedelta(days=i)).date().isoformat() for i in range(61)]
    codes = ['000001.SZ', '600000.SH']
    value = {'observations': {'selected_observations': [{'thscode': x} for x in codes],
        'inventory': {'columns': ['thscode', 'last_price'], 'rows': [[x, '20'] for x in codes]},
        'selection': {'selection_hash': 'a'*64}, 'context': {'sessions': days}}}
    raw = (canonical_json(value)+'\n').encode()
    monkeypatch.setattr(c, 'DETAIL_SHA256', sha256(raw).hexdigest())
    return raw, c.reference(raw)


def identity():
    return {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_JOB': c.MODE,
        'TRIAL_PURPOSE': c.MODE, 'GITHUB_SHA': 'b'*40, 'GITHUB_RUN_ID': '1234'}


class Tick:
    def __init__(self):
        self.value = datetime(2026, 10, 3, tzinfo=timezone.utc)
    def __call__(self):
        self.value += timedelta(seconds=1)
        return self.value.isoformat()


def payload(api, params, ref):
    fields = (c.FACTOR_FIELDS if api == 'adj_factor' else c.DAILY_FIELDS).split(',')
    codes = [params['ts_code']] if 'ts_code' in params else ref['symbols']
    days = [params['trade_date']] if 'trade_date' in params else [x.replace('-', '') for x in ref['sessions']]
    rows = []
    for code in codes:
        for day in reversed(days):
            price = '20' if day == ref['sessions'][-1].replace('-', '') else '10'
            row = {'ts_code': code, 'trade_date': day, 'open': price, 'high': price, 'low': price,
                'close': price, 'pre_close': '10', 'vol': '100', 'amount': '200', 'ah_vol': None,
                'ah_amount': None, 'adj_factor': '1'}
            rows.append([row[f] for f in fields])
    return {'code': 0, 'data': {'fields': fields, 'items': rows}}


def run_capture(tmp_path, sample, *, change=None, fail_at=None, status=403, retry=False):
    raw, ref = sample
    tick, seen = Tick(), []
    def request(api, params):
        i = len(seen); seen.append((api, params))
        obj = payload(api, params, ref)
        if change:
            change(i, obj)
        http = 200
        if i == fail_at:
            obj = {'ok': False, 'error': 'forbidden' if status == 403 else 'rate_limited'}
            http = status
        body = json.dumps(obj, separators=(',', ':')).encode()
        def attempt(number, code, b):
            return {'attempt': number, 'http_status': code, 'raw': b,
                'classification': c.relay.classify(code, c.relay.decode(b)),
                'requested_at': tick(), 'received_at': tick(), 'headers': {'X-Request-ID': 'synthetic'}}
        attempts = []
        if retry and i == 0:
            attempts.append(attempt(1, 503, b'{"error":"upstream_pool_exhausted"}'))
            tick.value += timedelta(seconds=30)
        attempts.append(attempt(len(attempts)+1, http, body))
        return {'api': api, 'params': params, 'status': attempts[-1]['classification'], 'attempts': attempts}
    root = tmp_path/'result'
    receipt, report = c.capture(root, raw, identity=identity(), request=request, now=tick)
    return root, receipt, report, seen


def test_full_same_provider_price_comparison_and_replay(tmp_path, sample):
    root, receipt, report, seen = run_capture(tmp_path, sample)
    assert len(seen) == 5
    assert report['cohort_denominator'] == 2
    assert report['qualified_windows'] == {'5': 2, '20': 2, '60': 2}
    assert report['observations'][0]['windows']['60']['price_change'] == '1'
    assert report['snapshot']['scope'] == 'RETURNED_DAILY_TRADING_ROWS_NOT_ALL_LISTED_SECURITIES'
    assert not report['daily_admission'] and not report['new_selection']
    assert c.verify(root, expected_identity=identity())['network_calls'] == 0
    before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    c.verify(root)
    assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
    with pytest.raises(ValueError, match='OUTPUT_EXISTS'):
        c.capture(root, sample[0], identity=identity(), request=lambda *_: pytest.fail('network'))


def test_provider_factor_is_used_not_substituted_for_action_history(tmp_path, sample):
    def change(i, obj):
        if i == 2:
            obj['data']['items'][0][-1] = '2'
    root, _, report, _ = run_capture(tmp_path, sample, change=change)
    row = report['observations'][0]
    assert row['windows']['5']['price_change'] == '3'
    assert row['corporate_action_details'] == 'NOT_OBTAINED_NOT_INFERRED_FROM_FACTORS'
    c.verify(root)


@pytest.mark.parametrize('api_index', [1, 2])
def test_older_gap_does_not_erase_shorter_window(tmp_path, sample, api_index):
    def change(i, obj):
        if i == api_index:
            obj['data']['items'].pop()
    root, _, report, _ = run_capture(tmp_path, sample, change=change)
    row = report['observations'][0]
    assert row['windows']['5']['price_change'] == '1'
    assert row['windows']['20']['price_change'] == '1'
    assert row['windows']['60']['price_change'] is None
    assert len(row['windows']['60']['missing_price_dates' if api_index == 1 else 'missing_factor_dates']) == 1
    assert report['cohort_denominator'] == 2
    c.verify(root)


def test_new_listing_missing_history_not_backfilled(tmp_path, sample):
    def change(i, obj):
        if i == 1:
            obj['data']['items'] = obj['data']['items'][:1]
    root, _, report, seen = run_capture(tmp_path, sample, change=change)
    assert len(seen) == 5 and report['qualified_windows'] == {'5': 1, '20': 1, '60': 1}
    assert all(w['price_change'] is None for w in report['observations'][0]['windows'].values())
    c.verify(root)


@pytest.mark.parametrize('bad', ['foreign-code', 'foreign-date', 'duplicate-row', 'duplicate-field', 'count', 'more', 'business-bool'])
def test_malformed_scope_stops_without_next_request(tmp_path, sample, bad):
    def change(i, obj):
        if i != 1:
            return
        d = obj['data']
        if bad == 'foreign-code': d['items'][0][0] = '999999.SH'
        if bad == 'foreign-date': d['items'][0][1] = '20270101'
        if bad == 'duplicate-row': d['items'].append(d['items'][0])
        if bad == 'duplicate-field': d['fields'][-1] = 'close'
        if bad == 'count': obj['count'] = 70
        if bad == 'more': d['has_more'] = True
        if bad == 'business-bool': obj['code'] = False
    root, receipt, report, seen = run_capture(tmp_path, sample, change=change)
    assert len(seen) == 2 and receipt['stopped'] == 'INPUT_SCHEMA_OR_SCOPE_REJECTED'
    assert report['request_dispositions'][2] == 'NOT_REQUESTED_AFTER_SOURCE_STOP'
    c.verify(root)


@pytest.mark.parametrize('status', [401, 403, 429])
def test_denial_stops_and_keeps_failure_raw(tmp_path, sample, status):
    root, receipt, report, seen = run_capture(tmp_path, sample, fail_at=2, status=status)
    assert len(seen) == 3
    assert report['qualified_windows'] == {'5': 0, '20': 0, '60': 0}
    assert report['observations'][1]['history_status'] == 'NOT_REQUESTED_AFTER_SOURCE_STOP'
    assert (root/'raw/02-1.json').is_file()
    c.verify(root)


def test_honest_one_queue_retry(tmp_path, sample):
    root, receipt, _, seen = run_capture(tmp_path, sample, retry=True)
    assert receipt['recorded_http_attempts'] == len(seen)+1
    assert c.verify(root)['recorded_http_attempts'] == 6
    receipt['calls'][0]['attempts'][1]['requested_at'] = receipt['calls'][0]['attempts'][0]['received_at']
    c.write(root, 'receipt.json', receipt)
    with pytest.raises(ValueError, match='RETRY_SCOPE'):
        c.verify(root)


@pytest.mark.parametrize('field,value', [('close', '21'), ('high', '1'), ('vol', '0'), ('amount', '-1')])
def test_values_never_become_qualified_by_field_rename(tmp_path, sample, field, value):
    def change(i, obj):
        if i == 1:
            obj['data']['items'][0][obj['data']['fields'].index(field)] = value
    root, _, report, _ = run_capture(tmp_path, sample, change=change)
    assert report['qualified_windows']['5'] == 1
    assert report['observations'][0]['windows']['5']['price_change'] is None
    c.verify(root)


def test_tamper_report_and_identity_rejected(tmp_path, sample):
    root, _, report, _ = run_capture(tmp_path, sample)
    with pytest.raises(ValueError, match='EXTERNAL_EXECUTION_IDENTITY'):
        c.verify(root, expected_identity={**identity(), 'GITHUB_RUN_ID': '5678'})
    report['daily_admission'] = True; c.write(root, 'report.json', report)
    with pytest.raises(ValueError, match='REPORT_REBUILD'):
        c.verify(root)


def test_raw_tamper_and_symlink_rejected(tmp_path, sample):
    root, _, _, _ = run_capture(tmp_path, sample)
    path = root/'raw/00-1.json'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='RAW_INTEGRITY'):
        c.verify(root)
    (root/'extra').symlink_to(path)
    with pytest.raises(ValueError, match='SYMLINK'):
        c.verify(root)


def test_after_denial_replay_rejected_even_with_updated_counts(tmp_path, sample):
    root, receipt, _, _ = run_capture(tmp_path, sample, fail_at=1)
    fake = deepcopy(receipt['calls'][-1]); fake.update(c.request_plan(sample[1])[2])
    receipt['calls'].append(fake); receipt['logical_requests_started'] += 1
    c.write(root, 'receipt.json', receipt)
    with pytest.raises(ValueError, match='REQUEST_AFTER_SOURCE_STOP'):
        c.verify(root)


def test_unexplained_incomplete_success_is_not_accepted(tmp_path, sample):
    root, receipt, _, _ = run_capture(tmp_path, sample)
    receipt['stopped'] = 'RAW_CUSTODY_BUDGET'; c.write(root, 'receipt.json', receipt)
    with pytest.raises(ValueError, match='STOP_IDENTITY'):
        c.verify(root)


def test_consumed_pilot_and_incomplete_inventory_refused():
    r = {'id': 1, 'display_title': c.TITLE, 'run_attempt': 1, 'event': 'workflow_dispatch', 'head_branch': 'main'}
    c.one_shot_scope([r], 1, 1)
    with pytest.raises(ValueError): c.one_shot_scope([r], 2, 1)
    with pytest.raises(ValueError): c.one_shot_scope([r, {**r, 'id': 2}], 2, 2)
    with pytest.raises(ValueError): c.one_shot_scope([{**r, 'run_attempt': 2}], 1, 1)


def test_fixed_reference_pin_and_execution_refused(sample):
    with pytest.raises(ValueError, match='REFERENCE_PIN'): c.reference(sample[0]+b' ')
    with pytest.raises(ValueError, match='EXECUTION_IDENTITY'): c.workflow_identity({**identity(), 'GITHUB_REF': 'refs/heads/draft'})
    with pytest.raises(ValueError, match='EXECUTION_IDENTITY'): c.workflow_identity({**identity(), 'GITHUB_EVENT_NAME': 'schedule'})


def test_exact_decimal_lexeme_and_no_duplicate_keys():
    assert c.raw_json(b'{"x":1.234567890123456789}')['x'] == Decimal('1.234567890123456789')
    with pytest.raises(ValueError): c.raw_json(b'{"x":1,"x":2}')
    with pytest.raises(ValueError): c.raw_json(b'{"x":NaN}')


def test_isolated_purpose_and_existing_recovery_short_circuit(monkeypatch):
    import runpy
    run = {'path': '.github/workflows/hithink-stock-dump-trial.yml',
        'event': 'workflow_dispatch', 'display_title': c.TITLE}
    assert c.is_source_check_run(run)
    assert not c.is_source_check_run({**run, 'event': 'schedule'})
    assert not c.is_source_check_run({**run, 'display_title': 'stock-reading | sector=123 | page=base | recovery=none'})
    root = Path(__file__).resolve().parents[1]
    control = runpy.run_path(str(root/'.github/scripts/reconcile-radar-delivery.py'))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_run')
    monkeypatch.setenv('UPSTREAM_PATH', run['path'])
    monkeypatch.setenv('UPSTREAM_DISPLAY_TITLE', c.TITLE)
    assert control['independent_stock_upstream'](None) is True
    flow = (root/'.github/workflows/hithink-stock-dump-trial.yml').read_text()
    job = flow.split('  tushare-c2-price-check:\n', 1)[1].split('  inspect:\n', 1)[0]
    assert 'TUSHARE_PROXY_API_KEY:' in job and 'HITHINK_FINANCE_API_KEY:' not in job and 'FTSHARE_API_KEY:' not in job
    assert 'one_shot_scope(rows' in job and 'steps.relay-capture.outcome' in job
    assert c.TITLE in (root/'.github/workflows/current-state-read-entry.yml').read_text()
    assert "tushare-c2-price-check |" in (root/'.github/workflows/stock-reading-after-sector.yml').read_text()
