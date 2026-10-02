from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import tdx_member_source_check as m
from decision_kernel.runtime import tushare_relay as relay

IDENTITY = {"repository": "auguspp/decision-kernel", "code_commit": "a" * 40,
            "run_id": "123456", "run_attempt": 1, "workflow": m.WORKFLOW}
NOW = "2026-10-02T01:00:00+00:00"
KEY = "synthetic-tdx-test-key"


def response(spec, *, members=None):
    day = spec['params']['trade_date']
    if spec['api'] == 'tdx_index':
        rows = [[b, day, n, '概念板块', 1] for b, n in m.BOARDS.items()]
    else:
        rows = [[spec['params']['ts_code'], day, s, '测试公司'] for s in (members or ['600000.SH'])]
    return {'code': 0, 'api_name': spec['api'], 'provider': 'relay-declared-upstream',
            'data': {'fields': list(m.FIELDS[spec['api']]), 'items': rows}, 'count': len(rows)}


def raw(spec):
    return m.encoded(response(spec))


def native(_):
    return {d: {'origin': {'reading_ref': ref, 'reading_hash': h},
                'boards': {b: {'name': n, 'members': ['600000.SH']} for b, n in m.BOARDS.items()}}
            for d, (ref, h) in m.NATIVE.items()}


def ticking():
    t = datetime(2026, 10, 2, 1, tzinfo=timezone.utc)
    def clock():
        nonlocal t
        t += timedelta(seconds=31)
        return t.isoformat()
    return clock


def request(api, params, key, clock):
    assert key == KEY
    spec = {'api': api, 'params': params}
    return {'api': api, 'params': params, 'status': 'SUCCESS', 'attempts': [{
        'attempt': 1, 'classification': 'SUCCESS', 'http_status': 200, 'raw': raw(spec),
        'requested_at': clock(), 'received_at': clock(), 'headers': {'X-Request-ID': 'test'},
        'business_code': 0, 'business_error': None, 'business_msg': 'ok'}]}


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV, KEY)
    monkeypatch.setattr(m, 'native_inputs', native)


def test_plan_is_six_logical_queries_with_explicit_fields_not_live_call():
    specs = m.plan()
    assert len(specs) == 6
    assert [s['api'] for s in specs].count('tdx_member') == 4
    assert [s['api'] for s in specs].count('tdx_index') == 2
    assert all(s['params']['trade_date'] in m.NATIVE for s in specs)
    assert all('fields' in s['params'] for s in specs)
    assert set(m.BOARDS) == {'880550.TDX', '880706.TDX'}


@pytest.mark.parametrize('spec', m.plan())
def test_both_endpoints_have_pure_qualified_control(spec):
    out = m.qualify(raw(spec), spec, NOW)
    assert out['status'] == 'DATED_PAGE_QUALIFIED'
    assert out['source_claims'][0]['value'] == 'relay-declared-upstream'


@pytest.mark.parametrize('case', ['wrong_date', 'wrong_board', 'duplicate_identity', 'wrong_api',
                                  'missing_column', 'duplicate_column', 'count_mismatch', 'empty',
                                  'code_bool', 'bad_security', 'null_name', 'at_cap', 'invalid_day'])
def test_member_page_fail_closed(case):
    spec = m.plan()[1]
    b = response(spec)
    rows, fields = b['data']['items'], b['data']['fields']
    if case == 'wrong_date': rows[0][1] = '20260930'
    elif case == 'invalid_day': rows[0][1] = '20260931'
    elif case == 'wrong_board': rows[0][0] = '880706.TDX'
    elif case == 'duplicate_identity': rows.append(rows[0][:]); b['count'] = 2
    elif case == 'wrong_api': b['api_name'] = 'ths_member'
    elif case == 'missing_column': fields[-1] = 'other'
    elif case == 'duplicate_column': fields[-1] = fields[0]
    elif case == 'count_mismatch': b['count'] = 2
    elif case == 'empty': rows.clear(); b['count'] = 0
    elif case == 'code_bool': b['code'] = False
    elif case == 'bad_security': rows[0][2] = '600000'
    elif case == 'null_name': rows[0][3] = None
    elif case == 'at_cap': b['data']['items'] = rows * 3000; b['count'] = 3000
    with pytest.raises((ValueError, TypeError)):
        m.qualify(m.encoded(b), spec, NOW)


@pytest.mark.parametrize('case', ['taxonomy', 'name', 'missing_target', 'count_bool'])
def test_catalog_is_not_a_silent_cross_taxonomy_mapping(case):
    spec = m.plan()[0]; b = response(spec); rows = b['data']['items']
    if case == 'taxonomy': rows[0][3] = '行业板块'
    elif case == 'name': rows[0][2] = '相似但不同的名称'
    elif case == 'missing_target': rows.pop(); b['count'] = len(rows)
    else: rows[0][4] = True
    with pytest.raises(ValueError): m.qualify(m.encoded(b), spec, NOW)


def test_unknown_columns_kept_in_raw_and_no_source_identity_upgrade():
    spec = m.plan()[1]; b = response(spec)
    b['data']['fields'].append('extra'); b['data']['items'][0].append(1.23)
    r = m.qualify(m.encoded(b), spec, NOW)
    assert r['extra_columns_retained_in_raw'] == ['extra']
    assert b['data']['items'][0][-1] == 1.23


def test_capture_replay_and_repeated_output_refusal(setup, tmp_path):
    root = tmp_path / 'out'
    out = m.capture(root, {}, IDENTITY, request=request, now=ticking())
    assert out['status'] == 'FOUR_DATED_GROUPS_MATCH_NATIVE'
    assert out['http_attempts_recorded'] == out['logical_queries_attempted'] == 6
    assert m.replay(m.load_files(root), IDENTITY) == out
    assert out['continuous_membership'] == out['historical_pit_knowledge'] == 'NOT_ESTABLISHED'
    assert not out['independent_economic_evidence'] and out['multi_horizon_roles'] == 'NOT_COMPUTED'
    with pytest.raises(ValueError): m.capture(root, {}, IDENTITY, request=request, now=ticking())


@pytest.mark.parametrize('status,http', [('AUTH_OR_ENTITLEMENT', 403), ('RATE_LIMIT', 429),
                                        ('SOURCE_UNAVAILABLE', 503)])
def test_service_denial_stops_remaining_queries(setup, tmp_path, status, http):
    seen = []
    def denied(api, params, key, clock):
        seen.append(api); r = request(api, params, key, clock)
        error = {'AUTH_OR_ENTITLEMENT': 'forbidden', 'RATE_LIMIT': 'rate_limited',
                 'SOURCE_UNAVAILABLE': 'data_source_unavailable'}[status]
        a = r['attempts'][0]; a.update(classification=status, http_status=http,
            raw=m.encoded({'code': 1, 'error': error}), business_code=1, business_error=error)
        r['status'] = status
        return r
    out = m.capture(tmp_path / status, {}, IDENTITY, request=denied, now=ticking())
    assert len(seen) == 1 and out['status'] == 'SOURCE_QUALIFICATION_GAP'
    assert all(o['status'] == 'NOT_ATTEMPTED_STOP' for o in out['outcomes'][1:])


def test_table_failure_stops_without_requery(setup, tmp_path):
    seen = []
    def wrong(api, params, key, clock):
        seen.append(api); r = request(api, params, key, clock)
        b = response({'api': api, 'params': params}); b['data']['items'][0][1] = '20261001'
        r['attempts'][0]['raw'] = m.encoded(b)
        return r
    out = m.capture(tmp_path / 'bad', {}, IDENTITY, request=wrong, now=ticking())
    assert len(seen) == 1 and out['outcomes'][0]['status'] == 'TABLE_UNQUALIFIED'


def test_missing_credential_is_gap_without_request(monkeypatch, setup, tmp_path):
    monkeypatch.delenv(relay.SECRET_ENV)
    out = m.capture(tmp_path / 'no-key', {}, IDENTITY,
                    request=lambda *a, **k: pytest.fail('network'), now=ticking())
    assert out['http_attempts_recorded'] == 0
    assert out['outcomes'][0]['status'] == 'CREDENTIAL_UNAVAILABLE'


def test_native_check_precedes_any_source_access(monkeypatch, tmp_path):
    def rejected(_): raise ValueError('native hash mismatch')
    monkeypatch.setattr(m, 'native_inputs', rejected)
    with pytest.raises(ValueError):
        m.capture(tmp_path / 'out', {}, IDENTITY, request=lambda *a, **k: pytest.fail('source'))
    assert not (tmp_path / 'out').exists()


def test_tampered_body_wrong_execution_and_extra_file_refused(setup, tmp_path):
    root = tmp_path / 'out'; m.capture(root, {}, IDENTITY, request=request, now=ticking())
    files = m.load_files(root)
    changed = dict(files); changed['raw-00-1.json'] += b' '
    with pytest.raises(ValueError): m.replay(changed, IDENTITY)
    with pytest.raises(ValueError): m.replay(files, {**IDENTITY, 'run_id': '2'})
    with pytest.raises(ValueError): m.replay({**files, 'unplanned.json': b'{}'}, IDENTITY)


def test_new_admissions_use_original_request_and_temporary_queue_logic():
    seen, slept = [], []
    def transport(api, params, key, clock):
        seen.append((api, params))
        body = (m.encoded({'code': 1, 'msg': 'timeout'}) if len(seen) == 1 else raw({'api': api, 'params': params}))
        return {'raw': body, 'http_status': 200, 'requested_at': clock(), 'received_at': clock(), 'headers': {}}
    s = m.plan()[1]
    out = relay.request(s['api'], s['params'], key=KEY, transport=transport, sleep=slept.append, clock=ticking())
    assert len(seen) == 2 and slept == [30] and out['status'] == 'SUCCESS'
    assert seen[0] == seen[1]


def test_catalog_member_count_disagreement_is_not_source_pass(setup, tmp_path):
    def mismatch(api, params, key, clock):
        r = request(api, params, key, clock)
        if api == 'tdx_index':
            b = response({'api': api, 'params': params})
            b['data']['items'][0][4] = 2
            r['attempts'][0]['raw'] = m.encoded(b)
        return r
    out = m.capture(tmp_path / 'counts', {}, IDENTITY, request=mismatch, now=ticking())
    assert out['status'] == 'SOURCE_QUALIFICATION_GAP'
    assert out['comparisons'][0]['status'] == 'CATALOG_COUNT_MISMATCH'


def test_manual_carrier_isolated_and_original_b2_client_pin_reconciled():
    from hashlib import sha1
    root = Path(__file__).resolve().parents[1]
    source = (root / m.WORKFLOW).read_text()
    assert 'workflow_dispatch:' in source and 'schedule:' not in source and 'push:' not in source
    assert "github.run_attempt == 1" in source and "github.actor == 'auguspp'" in source
    assert "refs/heads/main" in source and 'persist-credentials: false' in source
    assert 'head_sha=$EXPECTED_CODE' in source and "r['conclusion'] == 'success'" in source
    assert 'Pilot already invoked' in source and '--paginate --slurp' in source
    assert 'contents: write' not in source and 'actions: write' not in source
    assert source.count('secrets.TUSHARE_PROXY_API_KEY') == 1
    verify = source.split('- name: Rebuild saved report', 1)[1]
    assert 'secrets.' not in verify and 'GH_TOKEN' not in verify
    assert 'cancel-in-progress: false' in source and 'retention-days: 90' in source
    raw = (root / 'src/decision_kernel/runtime/tushare_relay.py').read_bytes()
    digest = sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert digest in source
    assert digest in (root / '.github/workflows/b2-disclosure-appointments.yml').read_text()
