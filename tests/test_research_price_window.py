"""Bounded window and custody checks, explicitly synthetic, not market evidence."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import research_price_window as w

NOW = datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)
CODES = ['600276.SH', '002050.SZ']


def envelope(api, fields, rows, **extra):
    return w.dumps({'code': 0, 'api_name': api, 'data': {'fields': fields, 'items': rows}, **extra})


def fake_request():
    elapsed = 0
    def request(api, params):
        nonlocal elapsed
        elapsed += 1
        if api == 'trade_cal':
            rows = [[params['exchange'], '20260928', 1], [params['exchange'], '20260929', 1],
                    [params['exchange'], '20260930', 1]]
        elif api == 'daily':
            rows = [[params['ts_code'], d, '10', '11', '9', '10.5', '10']
                    for d in ('20260928', '20260929', '20260930')]
        else:
            rows = [[params['ts_code'], d, '1'] for d in ('20260928', '20260929', '20260930')]
        return {'api': api, 'params': params, 'status': 'SUCCESS', 'attempts': [{
            'attempt': 1, 'http_status': 200, 'classification': 'SUCCESS',
            'requested_at': (NOW+timedelta(seconds=elapsed*2)).isoformat(),
            'received_at': (NOW+timedelta(seconds=elapsed*2+1)).isoformat(),
            'headers': {}, 'raw': envelope(api, w.FIELDS[api].split(','), rows)}]}
    return request


def captured(tmp_path, request=None):
    root = tmp_path/'result'
    report = w.capture(root, codes=CODES, start='20260928', end='20260930', observed_at=NOW,
        workflow={'synthetic': True}, request=request or fake_request(),
        clock=lambda: (NOW+timedelta(minutes=1)).isoformat())
    return root, report


def test_roundtrip_and_authority(tmp_path):
    root, result = captured(tmp_path)
    assert w.verify(root) == result
    assert result['status'] == 'COMPLETE_PROVIDER_DAILY_WINDOWS'
    assert result['source_requests'] == 6 and len(result['securities']) == 2
    assert result['provenance'] == 'SYNTHETIC_TEST_ONLY'
    assert result['investment_authority'] == 'NONE'
    assert not result['current_state_updated'] and not result['research_executed'] and not result['watch_registered']
    assert 'NOT_TOTAL_RETURN' in result['price_semantics']
    assert result['historical_acquisition'] == 'NOT_ESTABLISHED_BY_LATER_RETRIEVAL'
    assert result['company_action_details'] == 'NOT_OBTAINED'
    assert result['securities'][0]['prices']['20260928']['open'] == '10'
    with pytest.raises(ValueError, match='CREATE_ONLY'):
        w.capture(root, codes=CODES, start='20260928', end='20260930', observed_at=NOW,
                  workflow={}, request=fake_request())


@pytest.mark.parametrize('codes,start,end', [
    ([], '20260928', '20260930'), (['600276.SH']*2, '20260928', '20260930'),
    (['920344.BJ'], '20260928', '20260930'), (['600276.SH;echo secret'], '20260928', '20260930'),
    ([f'{i:06}.SH' for i in range(6)], '20260928', '20260930'),
    (CODES, '20260931', '20260930'), (CODES, '20260930', '20260928'),
    (CODES, '20260830', '20260930'), (CODES, '20261007', '20261007'),
    (CODES, '2026-09-28', '20260930'), (CODES, '20260928', '20261008'),
])
def test_reject_scope_before_requests(codes, start, end, tmp_path):
    def forbidden(*a, **k):
        raise AssertionError('source must not run')
    with pytest.raises(ValueError):
        w.capture(tmp_path/'bad', codes=codes, start=start, end=end, observed_at=NOW,
                  workflow={}, request=forbidden)
    assert not (tmp_path/'bad').exists()


def test_maximum_plan_and_clock():
    p = w.plan(['600276.SH', '002674.SZ', '600598.SH', '002050.SZ', '603986.SH'],
               '20260901', '20260930', NOW)
    assert len(p) == 12
    assert [q['api'] for q in p[:2]] == ['trade_cal']*2
    assert all(q['params']['limit'] == '1000' for q in p)
    with pytest.raises(ValueError, match='CLOCK_ZONE'):
        w.plan(CODES, '20260928', '20260930', NOW.replace(tzinfo=None))


@pytest.mark.parametrize('status,http', [('AUTH_OR_ENTITLEMENT',403), ('RATE_LIMIT',429),
                                         ('REQUEST_BUDGET_EXHAUSTED',None)])
def test_stop_does_not_request_other_objects(tmp_path, status, http):
    calls = []
    def failed(api, params):
        calls.append(api)
        return {'api': api, 'params': params, 'status': status,
                'attempts': [] if http is None else [{'attempt':1, 'http_status':http,
                'classification':status, 'requested_at':NOW.isoformat(), 'received_at':NOW.isoformat(),
                'headers': {}, 'raw':b'{"code":-1,"msg":"synthetic denied"}'}]}
    root, report = captured(tmp_path, failed)
    assert len(calls) == 1 and report['source_requests'] == 1
    assert report['status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert all(s['status'] == 'NOT_REQUESTED' for s in report['source_statuses'][1:])
    assert w.verify(root) == report


@pytest.mark.parametrize('mutator', [
    lambda body: body['data']['items'].append(body['data']['items'][0]),
    lambda body: body['data']['items'][0].__setitem__(0, '600000.SH'),
    lambda body: body['data']['items'][0].__setitem__(1, '20260927'),
    lambda body: body['data']['items'][0].__setitem__(2, '0'),
    lambda body: body['data']['items'][0].__setitem__(3, '8'),
    lambda body: body['data']['items'][0].__setitem__(4, '12'),
    lambda body: body['data']['fields'].append('close'),
    lambda body: body.__setitem__('has_more', True),
    lambda body: body.__setitem__('total', 10),
    lambda body: body.__setitem__('code', 403),
])
def test_invalid_daily_rows_stay_unqualified(tmp_path, mutator):
    original = fake_request()
    def changed(api, params):
        r = original(api, params)
        if api == 'daily' and params['ts_code'] == CODES[0]:
            b = json.loads(r['attempts'][0]['raw']); mutator(b)
            r['attempts'][0]['raw'] = w.dumps(b)
        return r
    root, report = captured(tmp_path, changed)
    assert report['securities'][0]['status'] == 'WINDOW_GAPS'
    assert report['securities'][1]['status'] == 'COMPLETE_PROVIDER_DAILY_WINDOW'
    assert w.verify(root) == report


@pytest.mark.parametrize('api', ['daily', 'adj_factor', 'trade_cal'])
def test_missing_rows_are_not_filled(tmp_path, api):
    original = fake_request()
    def missing(name, params):
        r = original(name, params)
        if name == api:
            b = json.loads(r['attempts'][0]['raw']); b['data']['items'].pop()
            r['attempts'][0]['raw'] = w.dumps(b)
        return r
    root, report = captured(tmp_path, missing)
    assert report['status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert w.verify(root) == report


@pytest.mark.parametrize('file', ['raw/01-1.json', 'report.json', 'summary.md'])
def test_tamper_rejects(tmp_path, file):
    root, _ = captured(tmp_path)
    with (root/file).open('ab') as f:
        f.write(b' ')
    with pytest.raises(ValueError):
        w.verify(root)


def test_wrong_request_and_hash_reject(tmp_path):
    root, _ = captured(tmp_path)
    r = json.loads((root/'receipt.json').read_bytes())
    r['calls'][2]['params']['ts_code'] = '600000.SH'
    (root/'receipt.json').write_bytes(w.dumps(r))
    with pytest.raises(ValueError, match='REQUEST_IDENTITY'):
        w.verify(root)


def test_symlink_and_extra_raw_reject(tmp_path):
    root, _ = captured(tmp_path)
    (root/'raw'/'extra.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='RAW_INVENTORY'):
        w.verify(root)
    (root/'raw'/'extra.json').unlink()
    target = root/'raw'/'01-1.json'; saved = target.read_bytes(); target.unlink()
    (tmp_path/'source.json').write_bytes(saved); target.symlink_to(tmp_path/'source.json')
    with pytest.raises(ValueError, match='SYMLINK'):
        w.verify(root)


def test_live_identity_fails_before_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv('TUSHARE_PROXY_API_KEY', raising=False)
    with pytest.raises(ValueError, match='EXECUTION_IDENTITY'):
        w.capture(tmp_path/'bad', codes=CODES, start='20260928', end='20260930',
                  observed_at=NOW, workflow={})
    assert not (tmp_path/'bad').exists()


def test_workflow_manual_read_only_and_secret_isolation():
    text = (Path(__file__).parents[1]/'.github/workflows/research-price-window.yml').read_text()
    assert '  workflow_dispatch:' in text
    assert all(x not in text for x in ('  schedule:', '  push:', '  workflow_run:'))
    assert 'permissions:\n  contents: read\n  actions: read' in text
    assert 'github.run_attempt == 1' in text and "github.ref == 'refs/heads/main'" in text
    assert text.count('secrets.') == 1
    capture = text.split('- name: Capture the explicit research window', 1)[1].split('- name: Verify', 1)[0]
    assert 'TUSHARE_PROXY_API_KEY:' in capture and 'GH_TOKEN' not in capture
    verify = text.split('- name: Verify saved replies', 1)[1].split('- name: Retain', 1)[0]
    assert 'secrets.' not in verify and 'GH_TOKEN' not in verify
    assert 'current-state' not in text and 'ci.yml/runs?head_sha=' in text
    assert 'persist-credentials: false' in text
    assert '--codes "$WINDOW_CODES"' in text


def test_inclusive_31_day_boundary():
    assert w.plan(['600276.SH'], '20260831', '20260930', NOW)


def test_byte_budget_stops_source_and_preserves_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(w, 'MAX_BODY', 16)
    root, report = captured(tmp_path)
    receipt = json.loads((root/'receipt.json').read_bytes())
    assert len(receipt['calls']) == 1 and receipt['calls'][0]['status'] == 'BYTE_BUDGET'
    assert report['status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert w.verify(root) == report


def test_empty_and_closed_day_rows_are_not_complete(tmp_path):
    original = fake_request()
    def with_closed_day(api, params):
        result = original(api, params)
        if api == 'trade_cal':
            body = json.loads(result['attempts'][0]['raw'])
            body['data']['items'][1][2] = 0
            result['attempts'][0]['raw'] = w.dumps(body)
        return result
    root, report = captured(tmp_path, with_closed_day)
    assert report['status'] == 'PARTIAL_OR_UNAVAILABLE'
    assert report['securities'][0]['rows_outside_open_sessions'] == ['20260929']
    assert w.verify(root) == report


def test_retry_after_denial_is_rejected(tmp_path):
    root, _ = captured(tmp_path)
    receipt = json.loads((root/'receipt.json').read_bytes())
    receipt['calls'][0]['status'] = 'AUTH_OR_ENTITLEMENT'
    (root/'receipt.json').write_bytes(w.dumps(receipt))
    with pytest.raises(ValueError, match='AFTER_STOP'):
        w.verify(root)
