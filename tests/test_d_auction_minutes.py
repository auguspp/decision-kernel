"""Synthetic transport, original auction replay, exact minute fields and saved reader.

Git I/O and shared publication reservation are fixtures in reader tests. Nothing
here is a real minute-price response, market-timeliness or trade demonstration.
"""
from copy import deepcopy
from datetime import datetime
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
import zipfile

import pytest
import re

from decision_kernel.runtime import d_auction_minutes as m
from decision_kernel.runtime import d_auction_minute_reading as reading
from decision_kernel.runtime import d_auction_probe as p
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import ftshare_market_inputs as ft
from decision_kernel.runtime import tushare_relay as relay
from test_d_auction_probe import AT, IDENTITY, TARGET, fake_request, sources, pool_row, offline

WHEN = '2026-10-08T09:42:00+08:00'
MINUTE_IDENTITY = {**IDENTITY, 'GITHUB_JOB': m.JOB, 'GITHUB_RUN_ID': '456'}


def archive(files):
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items(): z.writestr(name, body)
    return buf.getvalue()


def seed(tmp_path, monkeypatch, count=3, live=False):
    names = [f'{600000+i:06}.SH' for i in range(count)]
    data = sources(prior_rows=[pool_row(s, turnover='20' if i % 2 else '5') for i, s in enumerate(names)],
                   auction_rows=[[s, '20261008', '10.5', '10'] for s in names])
    request = fake_request(data)
    monkeypatch.setattr(relay, 'request', lambda api, params, **kw: request(api, params))
    root = tmp_path/'auction'
    report = p.capture(root, market_session=TARGET, observed_at=AT, workflow=IDENTITY,
                       request=None if live else request, clock=AT.isoformat)
    files = {x.relative_to(root).as_posix(): x.read_bytes() for x in root.rglob('*') if x.is_file()}
    raw = archive(files)
    description = {'sha256': model.sha256(raw), 'git_blob': model.blob_sha(raw), 'bytes': len(raw),
                   'expires_at': '2027-01-01T00:00:00Z', 'origin_run': {'id': 123, 'head_sha': 'a'*40}}
    plan = m.plan_for(report, description, 'b'*40)
    out = tmp_path/'minutes'; out.mkdir(); (out/'auction-source.zip').write_bytes(raw)
    (out/'plan.json').write_bytes(m.encode(plan))
    return out, plan, report


def payload(plan, parameters, *, change=None):
    row = {'close': '10.1000', 'ts_millis': plan['target_end_ms'], 'ts_millis_open': plan['target_open_ms']}
    data = [{'symbol': s, 'total': 1, 'items': [dict(row)]} for s in parameters['symbols']]
    if change: change(data)
    return m.encode({'code': 200, 'data': data})


def run_capture(out, plan, *, change=None):
    calls = []
    def fetch(route, parameters):
        calls.append(parameters); assert route == m.ROUTE
        return 200, payload(plan, parameters, change=change)
    result = m.capture(out, fetch=fetch, clock=lambda: WHEN)
    return result, calls


def test_full_original_cohort_in_three_batches_and_replay(tmp_path, monkeypatch):
    out, plan, old = seed(tmp_path, monkeypatch, 57)
    before = (out/'auction-source.zip').read_bytes()
    report, calls = run_capture(out, plan)
    assert [len(c['symbols']) for c in calls] == [20, 20, 17]
    assert report['cohort_denominator'] == report['observed_0940'] == 57
    assert [r['symbol'] for r in report['rows']] == [r['symbol'] for r in p.row_dicts(old)]
    assert sum(g['denominator'] for g in report['groups'].values()) == 57
    assert m.verify(out) == report and (out/'auction-source.zip').read_bytes() == before
    assert report['rows'][0]['minute']['close_0940'] == '10.1000'
    assert report['provenance'] == 'SYNTHETIC_TEST_ONLY'
    assert report['cross_provider_return'] == 'NOT_COMPUTED'
    assert report['capture_timing'] == 'HISTORICAL_OR_LATE_NOT_0940_DISCOVERY'
    with pytest.raises(ValueError, match='already attempted'): run_capture(out, plan)


@pytest.mark.parametrize('case,status', [
    ('missing', 'TARGET_MINUTE_NOT_RETURNED'), ('wrong_open', 'TARGET_MINUTE_TIME_UNQUALIFIED'),
    ('next_minute', 'TARGET_MINUTE_NOT_RETURNED'), ('yesterday', 'TARGET_MINUTE_NOT_RETURNED'),
    ('conflicting', 'TARGET_MINUTE_AMBIGUOUS'), ('negative', 'TARGET_CLOSE_INVALID'),
    ('null', 'TARGET_CLOSE_INVALID'), ('bool', 'TARGET_CLOSE_INVALID'), ('missing_symbol', 'SYMBOL_NOT_RETURNED'),
    ('duplicate_symbol', 'SYMBOL_AMBIGUOUS')])
def test_per_security_gap_does_not_cancel_other_rows(tmp_path, monkeypatch, case, status):
    out, plan, _ = seed(tmp_path, monkeypatch)
    def damage(data):
        row = data[0]['items'][0]
        if case == 'missing': data[0]['items'] = []
        elif case == 'wrong_open': row['ts_millis_open'] -= 60000
        elif case == 'next_minute': row['ts_millis'] += 60000
        elif case == 'yesterday': row['ts_millis'] -= 86400000; row['ts_millis_open'] -= 86400000
        elif case == 'conflicting': data[0]['items'].append({**row, 'close': '10.2'})
        elif case == 'negative': row['close'] = '-1'
        elif case == 'null': row['close'] = None
        elif case == 'bool': row['close'] = True
        elif case == 'missing_symbol': data.pop(0)
        elif case == 'duplicate_symbol': data.append(deepcopy(data[0]))
    report, _ = run_capture(out, plan, change=damage)
    assert report['cohort_denominator'] == 3 and report['observed_0940'] == 2
    assert report['rows'][0]['minute']['status'] == status
    assert m.verify(out) == report


def test_unused_ohlc_volume_internal_gaps_and_total_do_not_block_exact_close(tmp_path, monkeypatch):
    out, plan, _ = seed(tmp_path, monkeypatch)
    def change(data):
        for item in data:
            item['total'] = 20
            item['items'][0].update(open=None, high='invalid', low=-1, volume=None)
            item['items'].append({'ts_millis': plan['target_end_ms']-120000, 'close': None})
    report, _ = run_capture(out, plan, change=change)
    assert report['observed_0940'] == 3
    assert not report['rows'][0]['minute']['return_count_consistent']


@pytest.mark.parametrize('http,body,status', [
    (403, b'{"code":403}', 'ENTITLEMENT_DENIED'), (200, b'{"code":403}', 'ENTITLEMENT_DENIED'),
    (401, b'{}', 'AUTHENTICATION_FAILED'), (429, b'{}', 'RATE_LIMITED'),
    (500, b'{}', 'HTTP_REJECTED'), (200, b'{bad', 'PARSE_FAILURE')])
def test_source_stops_not_retry_or_fabricated_empty(tmp_path, monkeypatch, http, body, status):
    out, plan, _ = seed(tmp_path, monkeypatch, 57)
    calls = []
    def fetch(route, parameters):
        calls.append(parameters)
        return (200, payload(plan, parameters)) if len(calls) == 1 else (http, body)
    report = m.capture(out, fetch=fetch, clock=lambda: WHEN)
    assert len(calls) == 2 and report['observed_0940'] == 20 and report['cohort_denominator'] == 57
    assert report['source_stop'] == status
    assert report['rows'][20]['minute']['status'] == status
    assert report['rows'][40]['minute']['status'] == 'NOT_REQUESTED_AFTER_SOURCE_STOP'
    assert m.verify(out) == report


def test_transport_failure_is_not_permission_denial(tmp_path, monkeypatch):
    out, _, _ = seed(tmp_path, monkeypatch)
    def failed(*args): raise URLError('synthetic connection failure')
    report = m.capture(out, fetch=failed, clock=lambda: WHEN)
    assert report['source_stop'] == 'TRANSPORT_FAILURE' and report['source_request_count'] == 1
    assert m.verify(out) == report


@pytest.mark.parametrize('damage', ['raw', 'report', 'plan', 'extra', 'clock', 'workflow'])
def test_byte_identity_replay_and_clock_tampering_rejected(tmp_path, monkeypatch, damage):
    out, plan, _ = seed(tmp_path, monkeypatch); run_capture(out, plan)
    if damage == 'raw': (out/'raw/01.json').write_bytes(b'{}')
    elif damage == 'extra': (out/'extra.py').write_text('not executable')
    else:
        path = out/('receipt.json' if damage in ('clock', 'workflow') else damage+'.json')
        value = json.loads(path.read_bytes())
        if damage == 'clock': value['calls'][0]['received_at'] = '2026-10-07T01:00:00Z'
        elif damage == 'workflow': value['workflow'] = MINUTE_IDENTITY
        elif damage == 'plan': value['target_end_ms'] += 60000
        else: value['observed_0940'] += 1
        path.write_bytes(m.encode(value))
    with pytest.raises((ValueError, KeyError)): m.verify(out)


def test_request_uses_official_repeated_symbols_and_no_adjustment_conversion(tmp_path, monkeypatch):
    _, plan, _ = seed(tmp_path, monkeypatch)
    urls = []
    class Response:
        headers = {}
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def geturl(self): return urls[-1]
        def read(self, n): return b'{"code":200,"data":[]}'
    def open_request(req, timeout): urls.append(req.full_url); return Response()
    monkeypatch.setenv('FTSHARE_API_KEY', 'synthetic-not-a-real-key')
    monkeypatch.setattr(ft, 'build_opener', lambda *a: SimpleNamespace(open=open_request))
    status, raw = ft.request(m.ROUTE, plan['batches'][0])
    query = parse_qs(urlsplit(urls[0]).query)
    assert query['symbols'] == plan['batches'][0]['symbols']
    assert query['interval_value'] == ['1'] and 'adjust_kind' not in query
    assert urlsplit(urls[0]).path == '/gateway/api/v2/market/data/stock_minutes/batch'
    assert status == 200 and raw == b'{"code":200,"data":[]}'


def reader_fixture(tmp_path, monkeypatch):
    out, plan, _ = seed(tmp_path, monkeypatch, live=True)
    monkeypatch.setattr(ft, 'request', lambda route, params: (200, payload(plan, params)))
    report = m.capture(out, clock=lambda: WHEN, workflow=MINUTE_IDENTITY)
    files = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
    raw = archive(files)
    run = {'id':456, 'display_title':m.TITLE, 'path':m.WORKFLOW, 'head_branch':'main',
           'event':'workflow_dispatch', 'run_attempt':1, 'head_sha':'a'*40, 'status':'completed', 'conclusion':'success',
           'created_at':WHEN, 'updated_at':WHEN, 'run_started_at':WHEN,
           'repository':{'full_name':model.REPOSITORY}, 'head_repository':{'full_name':model.REPOSITORY}}
    artifact = {'id':789, 'name':m.TITLE+'-456-1', 'expired':False, 'expires_at':'2027-01-01T00:00:00Z',
                'digest':'sha256:'+model.sha256(raw), 'size_in_bytes':len(raw),
                'workflow_run': {'id':456, 'head_sha':'a'*40}}
    def forbidden(*a): raise AssertionError('second query or source access')
    collector = SimpleNamespace(api=SimpleNamespace(calls=0, max_calls=1000, get=forbidden),
        files={'README.md': b'original reading', 'old.json': b'original'}, archive_cache={}, previous=None, previous_commit=None)
    collector.artifacts = lambda r: [artifact]
    collector.archive = lambda a, r: (model.unpack_archive(raw, a, r), {'sha256':model.sha256(raw), 'bytes':len(raw)})
    def retain(path, value):
        collector.files[path] = value
        return {'read_path':path, 'bytes':len(value), 'sha256':model.sha256(value), 'git_blob':model.blob_sha(value)}
    collector.retain = retain
    monkeypatch.setattr(reading, '_reserve', lambda *a, **kw: None)  # Existing shared quota has separate tests.
    return collector, {'checks':{'finished_at':WHEN}}, {'workflow_runs':[run], 'total_count':1}, report


def test_saved_reader_replays_real_code_and_keeps_other_inputs(tmp_path, monkeypatch):
    collector, baseline, query, report = reader_fixture(tmp_path, monkeypatch)
    before = dict(collector.files)
    result = reading.read_saved(collector, baseline, run_query=query, retained_limit=16*1024*1024)
    assert result['observed_0940'] == 3 and result['new_source_requests'] == 0
    assert collector.files[m.PATH] == m.encode(report)
    assert all(collector.files[k] == v for k, v in before.items())
    assert m.PATH in result['summary']


@pytest.mark.parametrize('failure', ['query', 'pending', 'artifact', 'budget'])
def test_reading_failure_never_erases_original_prices_or_research(tmp_path, monkeypatch, failure):
    collector, baseline, query, _ = reader_fixture(tmp_path, monkeypatch)
    if failure == 'query': query = {}
    elif failure == 'pending': query['workflow_runs'][0]['status'] = 'in_progress'
    elif failure == 'artifact': collector.artifacts = lambda r: []
    before = dict(collector.files)
    result = reading.read_saved(collector, baseline, run_query=query,
        retained_limit=1 if failure == 'budget' else 16*1024*1024)
    assert 'file' not in result and collector.files == before
    assert result['new_source_requests'] == 0 and result['status'] in ('MINUTE_READING_GAP_NOT_QUIET', 'MINUTE_CAPTURE_PENDING')


def test_same_query_composes_auction_close_and_minutes(monkeypatch):
    from decision_kernel.runtime import stock_market_input_reading as r
    from decision_kernel.runtime import d_auction_reading as ar, d_auction_follow_through as fr
    query = {'workflow_runs': [], 'total_count': 0}; calls = []
    monkeypatch.setattr(r, '_read_current_prices', lambda *a: {'_run_query':query, 'summary':'daily'})
    def read_auction(*a, run_query): assert run_query is query; return {'summary':'auction'}
    def read_minutes(*a, run_query, retained_limit):
        assert run_query is query; calls.append('minutes'); return {'summary':'minutes'}
    monkeypatch.setattr(ar, 'read_saved', read_auction)
    monkeypatch.setattr(fr, 'read_saved', lambda *a, **kw: {'summary':'close'})
    monkeypatch.setattr(reading, 'read_saved', read_minutes)
    result = r.read_current(None, {})
    assert result['summary'] == 'dailyauctioncloseminutes' and calls == ['minutes']


def test_manual_existing_workflow_only_and_existing_publisher_trigger():
    root = Path(__file__).resolve().parents[1]
    workflow = (root/'.github/workflows/stock-reading-after-sector.yml').read_text()
    assert re.findall(r"- cron: '([^']+)'", workflow) == ['35 10 * * 1-5', '5 11,13 * * 1-5']
    job = workflow.split('  auction-minutes:', 1)[1]
    assert "github.event_name == 'workflow_dispatch'" in job and "inputs.mode == 'auction-minutes'" in job
    assert "inputs.mode != 'auction-minutes'" in workflow.split('  dispatch-tdx-concept:', 1)[0]
    capture = job.split('      - name: Capture finite', 1)[1].split('      - name:', 1)[0]
    assert 'FTSHARE_API_KEY: ${{ secrets.FTSHARE_API_KEY }}' in capture and 'GH_TOKEN' not in capture
    assert 'continue-on-error' not in job
    pub = (root/'.github/workflows/current-state-read-entry.yml').read_text()
    assert "github.event.workflow_run.display_title == 'd-auction-minutes'" in pub


def test_unreadable_prior_locator_cannot_block_new_qualified_minutes(tmp_path, monkeypatch):
    collector, baseline, query, _ = reader_fixture(tmp_path, monkeypatch)
    def failed(*a): raise ValueError('synthetic previous file unavailable')
    monkeypatch.setattr(reading, 'previous_reference', failed)
    out = reading.read_saved(collector, baseline, run_query=query, retained_limit=16*1024*1024)
    assert out['observed_0940'] == 3 and out['previous_result_gap'] == 'ValueError'


def test_wrong_envelope_stops_but_mixed_member_gaps_do_not():
    assert m.response_status(200, b'{"code":200,"data":[{"different_contract":true}]}') == 'PARSE_FAILURE'
    assert m.response_status(200, b'{"code":200,"data":[{"symbol":"600000.SH","items":[]},null]}') == 'RESPONSE_SAVED'
