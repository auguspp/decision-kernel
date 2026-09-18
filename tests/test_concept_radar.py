from __future__ import annotations

import json
import socket
from datetime import datetime, time, timedelta
from decimal import Decimal, localcontext, Context
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import concept_radar as radar
from decision_kernel.runtime import concept_radar_capture as capture

TZ = radar.SHANGHAI_TZ
AT = datetime(2026, 9, 18, 16, tzinfo=TZ)
DAY = AT.date().isoformat()
SHA = 'a' * 40
WF = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_WORKFLOW': 'radar-concept-source',
      'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
      'GITHUB_RUN_ID': '123456', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': SHA}
ROOT = Path(__file__).resolve().parents[1]


def raw(value):
    return (canonical_json(value) + '\n').encode()


def ms(value):
    return int(value.timestamp() * 1000)


class Fixture:
    """Explicit synthetic exchange calendar, companies and prices; no live claim."""
    def __init__(self, count=4):
        days = [AT.date() - timedelta(days=i) for i in range(200, -1, -1)]
        self.days = [d for d in days if d.weekday() < 5][-126:]
        self.codes = [f'{886000+i:06d}.TI' for i in range(count)]
        self.called = []
        self.change = lambda path, params, value: value

    def envelope(self, rows, **extra):
        return {'code': 0, 'data': {'timestamp': ms(AT), 'item': rows, **extra}}

    def rate(self, code):
        if code == radar.BENCHMARK:
            return Decimal('.02')
        return (Decimal('-.2'), Decimal('.1'), Decimal('.05'), Decimal('.001'))[self.codes.index(code) % 4]

    def bars(self, code):
        rate = self.rate(code)
        return [{'date_ms': ms(datetime.combine(d, time(), tzinfo=TZ)),
                 'close_price': str(Decimal(100) + rate*i), 'volume': '1000', 'turnover': '2000'}
                for i, d in enumerate(self.days)]

    def snapshot(self, code):
        rate = self.rate(code)
        current, prior = Decimal(100) + rate*125, Decimal(100) + rate*124
        return {'thscode': code, 'ticker': code[:6], 'last_price': str(current), 'prev_price': str(prior),
                'price_change': str(current-prior), 'price_change_ratio_pct': str((current/prior-1)*100),
                'open_price': str(current), 'high_price': str(max(current, prior)+1),
                'low_price': str(min(current, prior)-1), 'volume': '1000', 'turnover': '2000'}

    def body(self, path, params):
        self.called.append((path, dict(params)))
        if path == radar.HITHINK_CALENDAR_PATH:
            value = self.envelope([{'date': d.strftime('%Y%m%d')} for d in self.days])
        elif path == radar.probe.CATALOG:
            rows = ([{'thscode': c, 'name': 'Synthetic concept ' + c} for c in self.codes]
                    if params == {'tag': 'cn_concept'} else [{'thscode': '881101.TI', 'name': 'Synthetic industry'}])
            value = self.envelope(rows)
        elif path == radar.probe.SNAPSHOT:
            rows = [self.snapshot(c) for c in params['thscodes'].split(',')]
            value = self.envelope(rows, total=len(rows))
        elif path == radar.probe.HISTORY:
            value = self.envelope(self.bars(params['thscode']), thscode=params['thscode'], interval='1d', adjust=None)
        else:
            assert path == radar.probe.MEMBERS
            value = self.envelope([{'thscode': '000001.SZ', 'ticker': '000001', 'name': 'Synthetic common'},
                {'thscode': f'60000{self.codes.index(params["thscode"])}.SH',
                 'ticker': f'60000{self.codes.index(params["thscode"])}', 'name': 'Synthetic member'}])
        return self.change(path, params, value)

    def request(self, path, params):
        at = AT + timedelta(seconds=2 * len(self.called))
        return raw(self.body(path, params)), at, at + timedelta(seconds=1)

    def run(self, **kw):
        return radar.observe(self.request, market_session=DAY, started_at=AT, **kw)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No network allowed in synthetic tests')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


def test_full_catalog_and_deferred_history_are_not_three_theme_universe():
    f = Fixture()
    p = f.run()['projection']
    assert p['catalog_count'] == p['snapshot_count'] == 4
    assert p['detail_selected_codes'] == f.codes[:3]
    assert p['coverage']['detail_deferred'] == 1
    assert p['concepts'][-1]['detail_acquisition'] == 'DEFERRED_NOT_ACQUIRED'
    assert p['policy']['detail_order_meaning'].endswith('NOT_RESEARCH_PRIORITY')
    assert len(f.called) == 11 and p['coverage']['full_concept_trend_radar'] is False
    assert p['coverage']['atomic_snapshot'] is False
    assert all(p[k] == v for k, v in radar.AUTHORITY.items())


def test_negative_mover_and_current_member_overlap_preserved():
    p = Fixture().run()['projection']
    assert Decimal(p['concepts'][0]['daily_return']) < 0
    assert p['coverage']['member_occurrences'] == 6 and p['coverage']['member_union'] == 4
    company = next(c for c in p['companies'] if c['thscode'] == '000001.SZ')
    assert len(company['origins']) == 3 and company['business_linkage'] == 'NOT_ESTABLISHED'
    assert all(c['pre_quick_execution'] == 'NOT_EXECUTED_BY_THIS_SOURCE' for c in p['companies'])
    assert len(p['overlaps']) == 3
    assert all(o['intersection_members'] == ['000001.SZ'] for o in p['overlaps'])


def test_original_path_math_reused_and_no_small_subset_multiday_rank():
    f = Fixture()
    p = f.run()['projection']
    b = radar.normalize_hithink_completed_index_history(f.envelope(f.bars(radar.BENCHMARK),
        thscode=radar.BENCHMARK, interval='1d', adjust=None), thscode=radar.BENCHMARK,
        sessions=tuple(f.days), observed_at=AT)
    for detail in p['details']:
        code = detail['thscode']
        series = radar.normalize_hithink_completed_index_history(f.envelope(f.bars(code), thscode=code,
            interval='1d', adjust=None), thscode=code, sessions=tuple(f.days), observed_at=AT)
        with localcontext(Context(prec=28)):
            expected = radar.probe._path_observation(code, series.points, tuple(x.close for x in b.points), tuple(f.days))
        assert canonical_json(detail['path']) == canonical_json(expected)
        assert detail['path']['cross_sectional_rank'] is None
        assert detail['path']['rating'] is None


@pytest.mark.parametrize('mutation', ['missing', 'intraday', 'other_code', 'price', 'volume'])
def test_bad_theme_history_is_explicit_partial_not_no_trend(mutation):
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.HISTORY and params['thscode'] == f.codes[0]:
            if mutation == 'missing': value['data']['item'].pop(3)
            elif mutation == 'intraday': value['data']['item'][3]['date_ms'] += 1000
            elif mutation == 'other_code': value['data']['thscode'] = f.codes[1]
            elif mutation == 'price': value['data']['item'][-1]['close_price'] = '123'
            else: value['data']['item'][-1]['volume'] = '1001'
        return value
    f.change = change
    p = f.run()['projection']
    assert p['details'][0]['path'] is None and p['coverage']['history_checked'] == 2
    assert p['coverage']['memberships_checked'] == 3 and p['coverage']['detail_gaps'] == 1
    assert p['details'][0]['history_status'] == 'DATA_QUALIFICATION_REJECTED'
    assert '没有趋势' in radar.render({'projection': p, 'projection_hash': canonical_hash(p)})


@pytest.mark.parametrize('endpoint', [radar.probe.HISTORY, radar.probe.MEMBERS])
@pytest.mark.parametrize('code', [3001, 3002, 3004])
def test_explicit_detail_unavailable_is_not_batch_auth_failure(endpoint, code):
    f = Fixture()
    f.change = lambda path, params, value: {'code': code, 'message': 'provider data unavailable'} if (
        path == endpoint and params.get('thscode') == f.codes[0]) else value
    p = f.run()['projection']
    assert p['coverage']['detail_gaps'] == 1 and len(f.called) == 11
    assert p['details'][0]['history_status' if endpoint == radar.probe.HISTORY else 'membership_status'] == 'SOURCE_UNAVAILABLE'


@pytest.mark.parametrize('code', [1001, 1002, 2001, 429, 9999])
def test_auth_rate_unknown_business_failure_remains_fatal(code):
    f = Fixture()
    f.change = lambda path, params, value: {'code': code} if path == radar.probe.MEMBERS else value
    with pytest.raises(ValueError, match='PROVIDER_BUSINESS_REJECTED'):
        f.run()
    assert len([x for x in f.called if x[0] == radar.probe.MEMBERS]) == 1


@pytest.mark.parametrize('kind', ['missing_snapshot', 'duplicate_snapshot', 'wrong_total', 'catalog_overlap', 'future_ready', 'bad_calendar'])
def test_shared_identity_or_clock_failure_does_not_create_partial_success(kind):
    f = Fixture()
    def change(path, params, value):
        d = value['data']
        if path == radar.probe.SNAPSHOT:
            if kind == 'missing_snapshot': d['item'].pop(); d['total'] -= 1
            if kind == 'duplicate_snapshot': d['item'][-1] = d['item'][0]
            if kind == 'wrong_total': d['total'] += 1
            if kind == 'future_ready': d['timestamp'] = ms(AT + timedelta(days=1))
        if kind == 'catalog_overlap' and path == radar.probe.CATALOG and params['tag'] == 'cn_concept':
            d['item'][0]['thscode'] = '881101.TI'
        if kind == 'bad_calendar' and path == radar.HITHINK_CALENDAR_PATH:
            d['item'].pop()
        return value
    f.change = change
    with pytest.raises(ValueError):
        f.run()
    assert not any(path == radar.probe.MEMBERS for path, _ in f.called)


@pytest.mark.parametrize('at', [AT.replace(hour=15, minute=29), AT-timedelta(days=1), AT+timedelta(days=1)])
def test_intraday_or_wrong_target_day_has_zero_requests(at):
    f = Fixture()
    with pytest.raises(ValueError, match='SAME_DAY_COMPLETED_WINDOW_REQUIRED'):
        radar.observe(f.request, market_session=DAY, started_at=at)
    assert not f.called


def test_catalog_not_certified_by_prefix_and_exact_4096_bound():
    f = Fixture(4097)
    with pytest.raises(ValueError, match='CATALOG_SCOPE_REJECTED'): f.run()
    assert len(f.called) == 2
    f = Fixture(4096)
    p = f.run()['projection']
    assert p['catalog_count'] == 4096 and len(f.called) == radar.MAX_REQUESTS == 15
    assert len([c for c in f.called if c[0] == radar.probe.SNAPSHOT]) == 5
    assert all(len(params['thscodes'].split(',')) <= 1024 for path, params in f.called if path == radar.probe.SNAPSHOT)


def test_source_labels_html_escaped_not_instructions():
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.CATALOG and params['tag'] == 'cn_concept':
            value['data']['item'][0]['name'] = '<script>alert(1)</script>'
        return value
    f.change = change
    html = radar.render(f.run())
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'historical_first_vintage' in html and '多日趋势' in html


def make_capture(tmp_path, *, mutate=None, fail=False, secret=''):
    f = Fixture()
    if mutate:
        f.change = mutate
    stamp = AT
    def now():
        nonlocal stamp
        stamp += timedelta(seconds=1)
        return stamp
    def transport(path, params):
        if fail: raise OSError('remote ' + secret)
        return raw(f.body(path, params))
    out = tmp_path / 'capture'
    r = capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA, transport=transport,
                        now=now, pause=lambda seconds: None, credential=secret)
    return out, r, f


def test_original_capture_replay_zero_network_and_create_only(tmp_path):
    out, r, f = make_capture(tmp_path)
    assert r['status'] == capture.COMPLETE
    result = capture.verify(out)
    assert result['network_calls'] == 0 and result['catalog_count'] == 4 and result['company_count'] == 4
    assert len(f.called) == 11
    with pytest.raises(ValueError, match='CREATE_ONLY'):
        capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA,
                        transport=lambda *a: pytest.fail('no new call'), now=lambda: AT)


def test_partial_capture_rebuilds_without_claiming_complete_history(tmp_path):
    def mutate(path, params, value):
        if path == radar.probe.HISTORY and params['thscode'] == '886000.TI':
            value['data']['item'].pop(2)
        return value
    out, r, _ = make_capture(tmp_path, mutate=mutate)
    assert r['status'] == capture.PARTIAL
    assert capture.verify(out)['status'] == 'ORIGINAL_CONCEPT_REQUESTS_BODIES_AND_READING_REBUILT'


@pytest.mark.parametrize('name', ['observation.json', 'index.html', 'request-4.json', 'response-4.json', 'plan.json'])
def test_rehashed_tampering_rejected_by_rebuild(tmp_path, name):
    out, r, _ = make_capture(tmp_path)
    if name == 'index.html':
        (out/name).write_bytes((out/name).read_bytes()+b' changed')
    else:
        value = json.loads((out/name).read_bytes())
        if name == 'observation.json':
            value['projection']['companies'] = []
            value['projection_hash'] = canonical_hash(value['projection'])
        elif name == 'response-4.json': value['data']['item'][-1]['last_price'] = '100'
        elif name == 'request-4.json': value['params']['thscodes'] = '000300.SH'
        else: value['market_session'] = '2026-09-17'
        (out/name).write_bytes(raw(value))
    r['files'] = capture._inventory(out)
    r['capture_hash'] = canonical_hash({k: v for k, v in r.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(raw(r))
    with pytest.raises(ValueError): capture.verify(out)


def test_failed_transport_keeps_finite_receipt_without_secret(tmp_path):
    out, r, _ = make_capture(tmp_path, fail=True, secret='DO-NOT-RETAIN-12345')
    assert r['status'] == capture.FAILED and len(r['requests']) == 1
    assert all(b'DO-NOT-RETAIN-12345' not in p.read_bytes() for p in out.iterdir())
    assert capture.verify(out)['status'] == 'RETAINED_FAILED_CONCEPT_CAPTURE_REMOTE_CAUSE_NOT_REPROVEN'


def test_unsafe_body_not_archived(tmp_path):
    out, r, _ = make_capture(tmp_path, mutate=lambda *a: {'code': 0, 'token': 'secret-material'})
    assert r['status'] == capture.FAILED and not list(out.glob('response-*.json'))
    assert capture.verify(out)['network_calls'] == 0


@pytest.mark.parametrize('key,value', [('GITHUB_REF','refs/heads/draft'), ('GITHUB_RUN_ATTEMPT','2'),
    ('GITHUB_EVENT_NAME','push'), ('GITHUB_SHA','b'*40), ('GITHUB_RUN_ID','01'), ('GITHUB_WORKFLOW','other')])
def test_wrong_workflow_has_no_authority(key, value):
    env = {**WF, key: value}
    with pytest.raises(ValueError, match='WORKFLOW_IDENTITY_REJECTED'):
        capture.workflow_identity(env, SHA)


def test_symlink_capture_rejected(tmp_path):
    out, _, _ = make_capture(tmp_path)
    link = tmp_path/'link'
    link.symlink_to(out, target_is_directory=True)
    with pytest.raises(ValueError): capture.verify(link)


def test_manual_workflow_scope_and_no_research_secret():
    text = (ROOT/'.github/workflows/radar-concept-source.yml').read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text and 'workflow_run:' not in text
    assert 'contents: read' in text and 'contents: write' not in text and 'actions: write' not in text
    assert 'persist-credentials: false' in text and "github.run_attempt == 1" in text
    assert text.count('secrets.HITHINK_FINANCE_API_KEY') == 1 and 'secrets: inherit' not in text
    assert 'SUB2API' not in text and 'stock-business-research' not in text
    assert 'git rev-parse HEAD' in text and 'concept_radar_capture verify' in text


def test_benchmark_anchor_reuses_price_identity_not_new_volume_gate():
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.HISTORY and params['thscode'] == radar.BENCHMARK:
            value['data']['item'][-1]['volume'] = '1001'
        return value
    f.change = change
    assert f.run()['projection']['coverage']['history_checked'] == 3


@pytest.mark.parametrize('kind', ['reversed', 'too_late', 'day_boundary'])
def test_actual_response_clocks_not_repaired_by_later_requests(kind):
    f = Fixture()
    def request(path, params):
        raw_body, at, received = f.request(path, params)
        if len(f.called) == 4:
            if kind == 'reversed': received = at - timedelta(seconds=1)
            elif kind == 'too_late': received = AT + timedelta(minutes=31)
            else: received = AT + timedelta(days=1)
        return raw_body, at, received
    with pytest.raises(ValueError, match='RESPONSE_CLOCK_REJECTED'):
        radar.observe(request, market_session=DAY, started_at=AT)
    assert len(f.called) == 4


def test_company_name_disagreement_keeps_both_source_names():
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.MEMBERS and params['thscode'] == f.codes[1]:
            value['data']['item'][0]['name'] = 'Synthetic alternate name'
        return value
    f.change = change
    p = f.run()['projection']
    c = next(c for c in p['companies'] if c['thscode'] == '000001.SZ')
    assert len(c['source_names']) == 2 and len(c['origins']) == 3


def test_success_not_relabelled_as_partial_or_granted_authority(tmp_path):
    out, r, _ = make_capture(tmp_path)
    r['status'] = capture.PARTIAL
    r['capture_hash'] = canonical_hash({k: v for k, v in r.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(raw(r))
    with pytest.raises(ValueError, match='READING_REBUILD_DIFFERS'): capture.verify(out)
    r['investment_authority'] = 'ALLOW'
    r['capture_hash'] = canonical_hash({k: v for k, v in r.items() if k != 'capture_hash'})
    (out/'capture.json').write_bytes(raw(r))
    with pytest.raises(ValueError, match='CAPTURE_IDENTITY_REJECTED'): capture.verify(out)


def test_cli_replay_refuses_market_secret(tmp_path, monkeypatch):
    monkeypatch.setenv(capture.HITHINK_API_KEY_ENV, 'DUMMY-KEY')
    assert capture.main(['verify', '--output', str(tmp_path)]) == 2


@pytest.mark.parametrize('kind', ['expired', 'reversed'])
def test_capture_checks_next_request_clock_before_transport(tmp_path, kind):
    f = Fixture()
    clock_calls = 0
    def now():
        nonlocal clock_calls
        clock_calls += 1
        if clock_calls < 4:
            return AT + timedelta(seconds=clock_calls)
        return AT + timedelta(minutes=31) if kind == 'expired' or clock_calls > 4 else AT
    out = tmp_path/'bounded-clock'
    r = capture.capture(out, market_session=DAY, workflow=WF, expected_code=SHA,
        transport=lambda path, params: raw(f.body(path, params)), now=now, pause=lambda seconds: None)
    assert r['status'] == capture.FAILED and len(f.called) == len(r['requests']) == 1
    assert r['reason_code'] == 'REQUEST_WINDOW_EXPIRED_OR_REVERSED'
    assert capture.verify(out)['network_calls'] == 0
