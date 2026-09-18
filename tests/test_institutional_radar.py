"""Synthetic contract tests; no claimed live institution observation."""
import copy
import hashlib
import json
import socket
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import institutional_radar as r
from decision_kernel.runtime import institutional_radar_capture as c

DAY = '2026-09-17'
NOW = datetime.fromisoformat('2026-09-18T08:40:00+08:00')


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('network is forbidden in unit/replay tests')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


def raw(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode()


def fixtures():
    dates = ['2026-09-15', '2026-09-16', DAY, '2026-09-18']
    calendar = {'code': 0, 'data': {'item': [
        {'date': d.replace('-', ''), 'date_ms': int(datetime.fromisoformat(d+'T00:00:00+08:00').timestamp())*1000}
        for d in dates]}}
    first = {'thscode': '600999.SH', 'ticker': '600999', 'name': '合成未研究公司', 'range_days': 1,
             'org_net_value': '1250000.125', 'org_buy_num': 2, 'org_sell_num': 1,
             'concept_list': [{'name': '供应商概念标签'}], 'limit_reason': '供应商解释未核验'}
    rows = [first, {**first, 'range_days': 3, 'org_net_value': '-3000000.50'},
            {**first, 'thscode': '300999.SZ', 'ticker': '300999', 'name': '另一合成公司', 'org_net_value': None}]
    board = {'code': 0, 'data': {'board_type': 'org', 'trade_date': DAY,
             'timestamp': int(datetime.fromisoformat(DAY+'T00:00:00+08:00').timestamp())*1000,
             'count': 3, 'stock_count': 2, 'stock_items': rows, 'hot_money_items': []}}
    return calendar, board


def project(calendar=None, board=None, *, request_mutator=None):
    normal_calendar, normal_board = fixtures()
    a, b = raw(calendar if calendar is not None else normal_calendar), raw(board if board is not None else normal_board)
    records = [{'path': path, 'params': params, 'requested_at': (NOW+timedelta(seconds=i*20)).isoformat(),
                'received_at': (NOW+timedelta(seconds=i*20+1)).isoformat(),
                'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
               for i, (path, params, body) in enumerate([
                   (r.HITHINK_CALENDAR_PATH, {}, a), (r.BOARD_PATH, {'board_type': 'org', 'date': DAY}, b)])]
    if request_mutator:
        request_mutator(records)
    return r.build(a, b, requests=records, market_session=DAY, generated_at=NOW+timedelta(seconds=30),
                   provenance='SYNTHETIC_TEST_ONLY')


def test_independent_entry_keeps_opposite_overlapping_windows_and_unknowns():
    p = project()['projection']
    assert p['coverage']['distinct_stocks'] == 2 and p['coverage']['returned_window_rows'] == 3
    assert [x['institution_net_cny'] for x in p['companies'][0]['observations']] == ['1250000.125', '-3000000.50']
    assert p['companies'][1]['observations'][0]['institution_net_cny'] is None
    assert p['window_aggregation'].startswith('NONE')
    assert p['companies'][0]['stock_price_qualification'] == 'NOT_EXECUTED'
    assert p['companies'][0]['research_status'] == 'NOT_EXECUTED'
    assert all(p[k] == v for k, v in r.AUTHORITY.items())
    assert 'SECTOR_PRICE_FILTER' in p['companies'][0]['entry']
    assert 'NOT_FIRST_VINTAGE_PIT' in p['clock_meaning']
    assert p['source_publication_time'] == 'UNKNOWN'


@pytest.mark.parametrize('kind', ['board', 'day', 'stamp', 'boolstamp', 'stockcount', 'negative_count',
                                  'boolcount', 'missingrows', 'mixed', 'duplicate', 'window', 'ticker', 'name'])
def test_bad_identity_and_denominators_fail_closed(kind):
    _, b = fixtures(); d = b['data']
    if kind == 'board': d['board_type'] = 'all'
    elif kind == 'day': d['trade_date'] = '2026-09-16'
    elif kind == 'stamp': d['timestamp'] += 1
    elif kind == 'boolstamp': d['timestamp'] = True
    elif kind == 'stockcount': d['stock_count'] = 3
    elif kind == 'negative_count': d['count'] = -1
    elif kind == 'boolcount': d['count'] = True
    elif kind == 'missingrows': d['stock_items'] = []
    elif kind == 'mixed': d['hot_money_items'] = [{}]
    elif kind == 'duplicate': d['stock_items'][1]['range_days'] = 1
    elif kind == 'window': d['stock_items'][0]['range_days'] = 2
    elif kind == 'ticker': d['stock_items'][0]['ticker'] = '600998'
    elif kind == 'name': d['stock_items'][1]['name'] = '冲突身份'
    with pytest.raises(ValueError): project(board=b)


@pytest.mark.parametrize('key,value', [('org_net_value', 'NaN'), ('org_net_value', True),
                                      ('org_buy_num', -1), ('org_sell_num', '0.5'), ('org_net_value', {})])
def test_invalid_institution_numbers_rejected(key, value):
    _, b = fixtures(); b['data']['stock_items'][0][key] = value
    with pytest.raises(ValueError): project(board=b)


@pytest.mark.parametrize('kind', ['path', 'params', 'hash', 'size', 'future', 'reversed', 'preclose'])
def test_exact_request_and_actual_clocks(kind):
    def mutate(rows):
        if kind == 'path': rows[1]['path'] = '/another-path'
        elif kind == 'params': rows[1]['params']['board_type'] = 'hot_money'
        elif kind == 'hash': rows[1]['sha256'] = '0'*64
        elif kind == 'size': rows[1]['bytes'] += 1
        elif kind == 'future': rows[1]['received_at'] = (NOW+timedelta(hours=1)).isoformat()
        elif kind == 'reversed': rows[1]['requested_at'] = (NOW-timedelta(seconds=10)).isoformat()
        elif kind == 'preclose':
            for row in rows:
                row['requested_at'] = '2026-09-17T14:00:00+08:00'
                row['received_at'] = '2026-09-17T14:00:00+08:00'
    with pytest.raises(ValueError): project(request_mutator=mutate)


def test_unknown_upstream_row_aggregation_is_not_invented():
    _, b = fixtures(); b['data']['count'] = 4
    p = project(board=b)['projection']
    assert p['coverage']['source_count_equals_returned_rows'] is False
    assert p['coverage']['returned_window_rows'] == 3


def test_empty_source_scope_is_not_no_market_opportunities():
    _, b = fixtures(); b['data'].update(stock_items=[], count=0, stock_count=0)
    report = project(board=b)
    assert report['projection']['companies'] == []
    assert '不代表市场没有值得研究的对象' in r.render(report)


def test_escaped_source_labels_are_not_instructions():
    _, b = fixtures()
    for row in b['data']['stock_items'][:2]: row['name'] = '<script>BUY</script>'
    b['data']['stock_items'][0]['limit_reason'] = '</pre><img src="https://bad.example/a">'
    text = r.render(project(board=b))
    assert '<script>' not in text and '<img' not in text
    assert '&lt;script&gt;' in text and '未执行' in text


def test_business_failure_and_untrusted_json_do_not_become_quiet():
    _, b = fixtures(); b['code'] = 3002
    with pytest.raises(ValueError, match='PROVIDER_BUSINESS_FAILURE'): project(board=b)
    with pytest.raises(ValueError): r.decode(b'{"code":0,"code":1}')
    with pytest.raises(ValueError): r.decode(b'{"api_key":"secret"}')
    with pytest.raises(ValueError): r.decode(b'{"name":"KNOWN_KEY"}', 'KNOWN_KEY')


def run_capture(tmp_path, *, fail=None):
    bodies = list(map(raw, fixtures())); calls = []; clock = [NOW]
    def now():
        clock[0] += timedelta(seconds=1)
        return clock[0]
    def transport(path, params):
        calls.append((path, dict(params)))
        if fail == 'transport' and len(calls) == 2: raise OSError('do-not-retain-provider-body')
        if fail == 'unsafe' and len(calls) == 2: return b'{"secret":"do-not-retain"}'
        if fail == 'business' and len(calls) == 1: return b'{"code":2001,"data":null}'
        return bodies[len(calls)-1]
    pauses = []
    root = tmp_path/'capture'
    result = c.capture(root, market_session=DAY, workflow={'origin': 'SYNTHETIC_TEST_ONLY'},
                       transport=transport, now=now, pause=pauses.append)
    return root, result, calls, pauses


def test_real_functions_capture_and_replay_exact_synthetic_bytes(tmp_path):
    root, result, calls, pauses = run_capture(tmp_path)
    assert result['status'] == c.COMPLETE and len(calls) == 2 and pauses == [20]
    assert (root/'response-2.json').read_bytes() == raw(fixtures()[1])
    verified = c.verify(root)
    assert verified['company_count'] == 2 and verified['network_calls'] == 0
    with pytest.raises(ValueError, match='CREATE_ONLY'):
        c.capture(root, market_session=DAY, workflow={}, transport=None, now=lambda: NOW)


@pytest.mark.parametrize('failure', ['transport', 'unsafe', 'business'])
def test_failed_attempt_retained_without_retry_or_quiet(tmp_path, failure):
    root, result, calls, _ = run_capture(tmp_path, fail=failure)
    assert result['status'] == c.FAILED
    assert len(calls) == (1 if failure == 'business' else 2)
    assert not (root/'observation.json').exists()
    assert c.verify(root)['status'].startswith('RETAINED_FAILED_ATTEMPT')
    assert 'do-not-retain' not in ''.join(p.read_text() for p in root.iterdir())


def test_rehashed_derived_tampering_cannot_replace_original_replay(tmp_path):
    root, _, _, _ = run_capture(tmp_path)
    path = root/'observation.json'; report = json.loads(path.read_text())
    report['projection']['companies'][0]['observations'][0]['institution_net_cny'] = '999999'
    report['projection_hash'] = canonical_hash(report['projection'])
    path.write_bytes(c._bytes(report))
    receipt = json.loads((root/'capture.json').read_text())
    receipt['files'] = c._inventory(root)
    receipt['capture_hash'] = canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
    (root/'capture.json').write_bytes(c._bytes(receipt))
    with pytest.raises(ValueError, match='ORIGINAL_INPUT_REBUILD'): c.verify(root)


@pytest.mark.parametrize('key,value', [('GITHUB_REF', 'refs/heads/other'), ('GITHUB_RUN_ATTEMPT', '2'),
                                      ('GITHUB_EVENT_NAME', 'schedule'), ('GITHUB_SHA', 'b'*40)])
def test_only_fresh_exact_main_manual_runtime_is_permitted(key, value):
    env = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_WORKFLOW': 'radar-institutional-source',
           'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_RUN_ATTEMPT': '1',
           'GITHUB_SHA': 'a'*40, 'GITHUB_RUN_ID': '123'}
    assert c.workflow_identity(env, 'a'*40)['GITHUB_RUN_ID'] == '123'
    env[key] = value
    with pytest.raises(ValueError): c.workflow_identity(env, 'a'*40)


def test_workflow_is_manual_read_only_and_has_no_secret_in_replay():
    root = Path(__file__).resolve().parents[1]
    text = (root/'.github/workflows/radar-institutional-source.yml').read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text and 'workflow_run:' not in text
    assert 'contents: write' not in text and 'persist-credentials: false' in text
    replay = text.split('- name: Replay original response bytes', 1)[1].split('- name:', 1)[0]
    assert 'secrets.' not in replay and '--output' in replay
