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


@pytest.fixture
def gap_original(tmp_path, monkeypatch):
    """All prices/factors and clocks are synthetic; no provider or secret access."""
    import io, zipfile
    days = [(datetime(2026, 1, 1)+timedelta(days=i)).date().isoformat() for i in range(61)]
    codes = [f'{i:06d}.SZ' for i in range(1, 17)]
    value = {'observations': {'selected_observations': [{'thscode': x} for x in codes],
        'inventory': {'columns': ['thscode', 'last_price'], 'rows': [[x, '20'] for x in codes]},
        'selection': {'selection_hash': 'a'*64}, 'context': {'sessions': days}}}
    raw = (canonical_json(value)+'\n').encode()
    monkeypatch.setattr(c, 'DETAIL_SHA256', sha256(raw).hexdigest())
    dates = tuple(days[i].replace('-', '') for i in (-1, 0, 6, 30, 50))
    monkeypatch.setattr(c, 'GAP_DATES', dates)
    ref = c.reference(raw); tick = Tick()
    def request(api, params):
        obj = payload(api, params, ref)
        if api == 'adj_factor':
            obj['data']['items'] = [r for r in obj['data']['items'] if r[1] not in dates[1:]]
        body = json.dumps(obj).encode()
        attempt = {'attempt': 1, 'http_status': 200, 'raw': body, 'classification': 'SUCCESS',
                   'requested_at': tick(), 'received_at': tick(), 'headers': {}}
        return {'api': api, 'params': params, 'attempts': [attempt], 'status': 'SUCCESS'}
    original_identity = {**identity(), 'GITHUB_SHA': c.BASE_COMMIT, 'GITHUB_RUN_ID': str(c.BASE_RUN)}
    original = tmp_path/'original'; c.capture(original, raw, identity=original_identity, request=request, now=tick)
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in original.rglob('*'):
            if f.is_file(): z.writestr(f.relative_to(original).as_posix(), f.read_bytes())
    archive = out.getvalue()
    monkeypatch.setattr(c, 'BASE_BYTES', len(archive))
    monkeypatch.setattr(c, 'BASE_ZIP_SHA256', sha256(archive).hexdigest())
    return archive, ref, tick


def gap_attempt(tmp_path, sample, *, mutate=None, fail=None, retry=False):
    archive, ref, tick = sample; seen = []
    def request(api, params):
        i = len(seen); seen.append((api, params))
        obj = payload(api, params, ref)
        if mutate: mutate(i, obj)
        http = 200
        if i == fail:
            obj = {'error': 'forbidden', 'code': 403}; http = 403
        body = json.dumps(obj).encode()
        attempts = []
        if i == 0 and retry:
            attempts.append({'attempt': 1, 'http_status': 503, 'raw': b'{"error":"upstream_pool_exhausted"}',
                'classification': 'TEMPORARY_QUEUE', 'requested_at': tick(), 'received_at': tick(), 'headers': {}})
            tick.value += timedelta(seconds=30)
        status = c.relay.classify(http, obj)
        attempts.append({'attempt': len(attempts)+1, 'http_status': http, 'raw': body,
            'classification': status, 'requested_at': tick(), 'received_at': tick(), 'headers': {}})
        return {'api': api, 'params': params, 'attempts': attempts, 'status': status}
    env = {**identity(), 'TRIAL_PURPOSE': c.GAP_MODE}
    root = tmp_path/'gaps'
    receipt, report = c.capture_gaps(root, archive, identity=env, request=request, now=tick)
    return root, receipt, report, seen, env


def test_five_date_gap_requests_reuse_original_and_replay(tmp_path, gap_original):
    root, receipt, report, calls, env = gap_attempt(tmp_path, gap_original)
    assert len(calls) == 5 and all(api == 'adj_factor' and 'ts_code' not in p for api, p in calls)
    assert receipt['max_logical_requests'] == 5 and receipt['max_http_attempts'] == 10
    assert report['qualified_windows'] == {'5': 16, '20': 16, '60': 16}
    assert report['factor_repair']['filled_key_count'] == report['factor_repair']['target_keys'] == 64
    assert report['factor_repair']['original_qualified_windows'] == {'5': 16, '20': 0, '60': 0}
    before = (root/'original.zip').read_bytes()
    assert c.verify_gaps(root, expected_identity=env)['network_calls'] == 0
    assert (root/'original.zip').read_bytes() == before == gap_original[0]
    with pytest.raises(ValueError): c.verify(root)


@pytest.mark.parametrize('bad', ['anchor-missing', 'factor-conflict', 'root-source', 'data-source',
    'bad-date', 'bad-factor', 'duplicate', 'pagination'])
def test_gap_conflict_stops_before_remaining_dates(tmp_path, gap_original, bad):
    def change(i, obj):
        if i != 0: return
        if bad == 'anchor-missing': obj['data']['items'].pop()
        if bad == 'factor-conflict': obj['data']['items'][0][-1] = '2'
        if bad == 'root-source': obj['source'] = 'different'
        if bad == 'data-source': obj['data']['source'] = 'different'
        if bad == 'bad-date': obj['data']['items'][0][1] = '20270101'
        if bad == 'bad-factor': obj['data']['items'][0][-1] = '0'
        if bad == 'duplicate': obj['data']['items'].append(obj['data']['items'][0])
        if bad == 'pagination': obj['data']['has_more'] = True
    root, receipt, report, calls, env = gap_attempt(tmp_path, gap_original, mutate=change)
    assert len(calls) == 1 and receipt['stopped'] == 'INPUT_SCHEMA_OR_SCOPE_REJECTED'
    assert report['factor_repair']['filled_key_count'] == 0
    assert report['qualified_windows'] == {'5': 16, '20': 0, '60': 0}
    c.verify_gaps(root, expected_identity=env)


def test_gap_denial_keeps_all_original_prices_and_full_denominator(tmp_path, gap_original):
    root, receipt, report, calls, env = gap_attempt(tmp_path, gap_original, fail=1)
    assert len(calls) == 2 and receipt['stopped'] == 'AUTH_OR_ENTITLEMENT'
    assert report['cohort_denominator'] == 16 and report['factor_repair']['filled_key_count'] == 0
    assert report['request_dispositions'][2:] == ['NOT_REQUESTED_AFTER_SOURCE_STOP']*3
    c.verify_gaps(root, expected_identity=env)


def test_missing_factor_row_is_not_forward_filled(tmp_path, gap_original):
    def change(i, obj):
        if i == 1: obj['data']['items'].pop()
    root, _, report, _, _ = gap_attempt(tmp_path, gap_original, mutate=change)
    assert report['qualified_windows'] == {'5': 16, '20': 16, '60': 15}
    assert report['factor_repair']['filled_key_count'] == 63
    c.verify_gaps(root)


def test_gap_retry_keeps_original_queue_contract(tmp_path, gap_original):
    root, receipt, _, _, _ = gap_attempt(tmp_path, gap_original, retry=True)
    assert receipt['recorded_http_attempts'] == 6
    c.verify_gaps(root)


def test_gap_tampered_original_or_external_identity_rejected(tmp_path, gap_original):
    root, _, _, _, env = gap_attempt(tmp_path, gap_original)
    with pytest.raises(ValueError, match='EXTERNAL_EXECUTION_IDENTITY'):
        c.verify_gaps(root, expected_identity={**env, 'GITHUB_RUN_ID': '2345'})
    (root/'original.zip').write_bytes(gap_original[0]+b'x')
    with pytest.raises(ValueError, match='ORIGINAL_ARCHIVE_PIN'): c.verify_gaps(root)


def test_original_authorization_not_reopened_by_gap_mode():
    original = {'id': 1, 'display_title': c.TITLE, 'run_attempt': 1, 'event': 'workflow_dispatch', 'head_branch': 'main'}
    gap = {**original, 'id': 2, 'display_title': c.GAP_TITLE}
    c.one_shot_scope([original, gap], 2, 2, mode=c.GAP_MODE)
    with pytest.raises(ValueError): c.one_shot_scope([original, gap], 2, 2)
    with pytest.raises(ValueError): c.one_shot_scope([original, gap, {**gap, 'id': 3}], 3, 3, mode=c.GAP_MODE)


def saved_consumer_fixture(tmp_path, gap_original, *, gap=None, corrupt=False):
    import io, zipfile
    from types import SimpleNamespace
    from decision_kernel.runtime import current_state as model
    from decision_kernel.runtime import independent_stock_reading as reader
    original, ref, _ = gap_original
    values = {c.BASE_RUN: original}; fetched = []
    def run(rid, mode, status='success'):
        return {'id': rid, 'head_sha': c.BASE_COMMIT if rid == c.BASE_RUN else 'b'*40,
            'head_branch': 'main', 'run_attempt': 1, 'event': 'workflow_dispatch',
            'status': 'completed', 'conclusion': status,
            'path': '.github/workflows/hithink-stock-dump-trial.yml',
            'display_title': c.TITLE if mode == c.MODE else c.GAP_TITLE,
            'created_at': '2026-10-03T01:00:00Z',
            'repository': {'full_name': model.REPOSITORY}, 'head_repository': {'full_name': model.REPOSITORY}}
    base = run(c.BASE_RUN, c.MODE); rows = [base]
    if gap is not None:
        directory, _, _, _, _ = gap
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in directory.rglob('*'):
                if f.is_file():
                    raw = f.read_bytes()
                    if corrupt and f.name == 'report.json': raw += b' '
                    z.writestr(f.relative_to(directory).as_posix(), raw)
        values[1234] = out.getvalue(); rows.insert(0, run(1234, c.GAP_MODE))
    class API:
        calls = 0
        max_calls = 1000
        def get(self, path):
            self.calls += 1
            if path.startswith('actions/workflows/'):
                return {'total_count': len(rows), 'workflow_runs': rows}
            assert path == f'actions/runs/{c.BASE_RUN}'
            return base
    class Collector:
        def __init__(self): self.api = API(); self.files = {}; self.archive_cache = {}
        def artifacts(self, selected):
            rid = selected['id']; b = values[rid]
            return [{'id': c.BASE_ARTIFACT if rid == c.BASE_RUN else 4321,
                'name': f"{c.MODE if rid == c.BASE_RUN else c.GAP_MODE}-{rid}-1",
                'expired': False, 'expires_at': '2099-01-01T00:00:00Z',
                'size_in_bytes': len(b), 'digest': 'sha256:'+sha256(b).hexdigest(),
                'workflow_run': {'id': rid, 'head_sha': selected['head_sha']}}]
        def archive(self, artifact, selected):
            fetched.append(selected['id']); b = values[selected['id']]
            return model.unpack_archive(b, artifact, selected), {'artifact_id': artifact['id'], 'sha256': sha256(b).hexdigest()}
    observations = json.loads(c.original_input(original)['files']['reference.json'])['observations']
    return reader, Collector(), observations, rows, fetched


def test_daily_reader_attaches_verified_gap_not_relabelled_hithink(tmp_path, gap_original):
    gap = gap_attempt(tmp_path, gap_original)
    reader, col, obs, _, fetched = saved_consumer_fixture(tmp_path, gap_original, gap=gap)
    before = deepcopy(obs)
    out = reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')
    assert out['qualified_windows'] == {'5': 16, '20': 16, '60': 16}
    assert obs == before and fetched == [1234]
    assert out['daily_acquisition'] == 'NOT_ESTABLISHED' and out['source'] == 'THIRD_PARTY_TUSHARE_RELAY'


def test_daily_reader_original_stays_original_when_no_gap_run(tmp_path, gap_original):
    reader, col, obs, _, fetched = saved_consumer_fixture(tmp_path, gap_original)
    out = reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')
    assert out['qualified_windows'] == {'5': 16, '20': 0, '60': 0}
    assert out['factor_repair'] is None and fetched == [c.BASE_RUN]


def test_daily_reader_does_not_hide_failed_latest_gap(tmp_path, gap_original):
    gap = gap_attempt(tmp_path, gap_original)
    reader, col, obs, rows, fetched = saved_consumer_fixture(tmp_path, gap_original, gap=gap)
    rows.insert(0, {**rows[0], 'id': 5678, 'created_at': '2026-10-03T02:00:00Z', 'conclusion': 'failure'})
    out = reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')
    assert out['latest_gap_attempt']['id'] == 5678 and out['latest_gap_attempt']['conclusion'] == 'failure'
    assert fetched == [c.BASE_RUN] and out['qualified_windows']['20'] == 0


def test_daily_reader_rejects_tampered_latest_gap_without_old_fallback(tmp_path, gap_original):
    gap = gap_attempt(tmp_path, gap_original)
    reader, col, obs, _, fetched = saved_consumer_fixture(tmp_path, gap_original, gap=gap, corrupt=True)
    with pytest.raises(ValueError, match='REPORT_REBUILD'):
        reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')
    assert fetched == [1234]


def test_daily_reader_rejects_mixed_cohort_and_budget_before_reads(tmp_path, gap_original):
    reader, col, obs, _, _ = saved_consumer_fixture(tmp_path, gap_original)
    col.api.max_calls = 1
    with pytest.raises(ValueError, match='publication reserve'):
        reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')
    assert col.api.calls == 0
    col.api.max_calls = 1000; obs['selection']['selection_hash'] = 'f'*64
    with pytest.raises(ValueError, match='cohort differs'):
        reader.saved_tushare_comparison(col, obs, '2026-10-03T05:00:00Z')


def test_gap_workflow_reuses_job_and_retains_original_isolation():
    import runpy
    flow = Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    assert 'tushare-c2-factor-gaps]' in flow and 'capture-gaps' in flow and 'verify-gaps' in flow
    assert 'original_input(raw)' in flow and 'BASE_ZIP_SHA256' in flow
    assert 'schedule:' not in flow and 'continue-on-error' not in flow
    mod = runpy.run_path('.github/scripts/reconcile-radar-delivery.py')
    assert c.GAP_MODE in mod['ISOLATED_STOCK']
    assert "tushare-c2-factor-gaps |" in Path('.github/workflows/stock-reading-after-sector.yml').read_text()
