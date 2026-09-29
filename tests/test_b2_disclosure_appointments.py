"""Synthetic-only tests for the six-object caller, not live appointment acceptance."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest
from decision_kernel.runtime import tushare_relay as relay

ROOT = Path(__file__).resolve().parents[1]
b2 = runpy.run_path(str(ROOT / '.github/scripts/b2-disclosure-appointments.py'))
NOW = '2099-01-01T00:00:00+00:00'
IDENTITY = {'test_only': 'SYNTHETIC_NOT_A_GITHUB_RUN'}


def body(code, *, rows=None, fields=None):
    fields = list(b2['FIELDS']) if fields is None else fields
    row = {'ts_code': code, 'ann_date': '20990101', 'end_date': b2['PERIOD'],
           'pre_date': '20990201', 'actual_date': None, 'modify_date': 'raw revision; not a clock'}
    values = [[row.get(f) for f in fields]] if rows is None else rows
    return json.dumps({'code': 0, 'provider': 'synthetic-only',
                       'data': {'fields': fields, 'items': values}}, ensure_ascii=False).encode()


def client(raw_factory, *, http=200):
    calls, waits = [], []
    def request(api, params):
        calls.append((api, deepcopy(params)))
        def transport(a, p, k, *, clock):
            return {'http_status': http, 'raw': raw_factory(p['ts_code']),
                    'requested_at': NOW, 'received_at': NOW, 'headers': {'X-Request-ID': 'synthetic'}}
        return relay.request(api, params, key='synthetic-b2-test-only',
                             transport=transport, sleep=waits.append, clock=lambda: NOW)
    return request, calls, waits


def run(tmp_path, request):
    return b2['capture'](tmp_path / 'out', IDENTITY, request=request, clock=lambda: NOW)


def test_six_explicit_requests_retain_originals_and_nulls(tmp_path):
    request, calls, waits = client(body)
    result = run(tmp_path, request)
    assert len(calls) == 6 and waits == []
    assert [p['ts_code'] for _, p in calls] == [c[0] for c in b2['COMPANIES']]
    assert all(a == 'disclosure_date' and p['end_date'] == '20260930'
               and p['fields'] == ','.join(b2['FIELDS']) for a, p in calls)
    assert result['status'] == 'CAPTURED_REQUIRES_SOURCE_REVIEW'
    assert result['official_appointment_qualified'] is False
    for item in result['outcomes']:
        d = tmp_path / 'out' / item['code']
        receipt = json.loads((d / 'receipt.json').read_bytes())
        row = receipt['table']['rows'][0]
        assert row['actual_date'] is None and row['modify_date'] == 'raw revision; not a clock'
        assert receipt['table']['date_qualification'] == 'NOT_PERFORMED'
        original = (d / 'attempt-1.body').read_bytes()
        assert original == body(item['code'])
        attempt = receipt['client_result']['attempts'][0]
        assert attempt['sha256'] == sha256(original).hexdigest() and attempt['bytes'] == len(original)
        assert attempt['headers']['X-Request-ID'] == 'synthetic'
    with pytest.raises(FileExistsError):
        run(tmp_path, request)
    assert len(calls) == 6


def test_empty_response_is_not_absence_of_appointments(tmp_path):
    request, calls, _ = client(lambda code: body(code, rows=[]))
    result = run(tmp_path, request)
    assert len(calls) == 6
    assert all(o['status'] == 'EMPTY_RESPONSE_NOT_NO_APPOINTMENT' for o in result['outcomes'])
    assert result['official_appointment_qualified'] is False


def test_columns_use_names_and_revisions_are_not_deduplicated():
    code = b2['COMPANIES'][0][0]
    reversed_fields = list(reversed(b2['FIELDS']))
    normal = b2['inspect_body'](body(code), code)
    reversed_result = b2['inspect_body'](body(code, fields=reversed_fields), code)
    assert normal == reversed_result
    data = json.loads(body(code)); data['data']['items'] *= 2
    result = b2['inspect_body'](json.dumps(data).encode(), code)
    assert len(result['rows']) == 2 and result['matching_row_indexes'] == [0, 1]


@pytest.mark.parametrize('http', [403, 429, 503])
def test_failure_stops_remaining_company_requests(tmp_path, http):
    def raw(code):
        return b'{"code":1,"error":"upstream_timeout"}' if http == 503 else b'{"code":-1}'
    request, calls, waits = client(raw, http=http)
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
    assert waits == ([30] if http == 503 else [])
    assert all(o['status'] == 'NOT_QUERIED_AFTER_STOP' and o['receipt'] is None
               for o in result['outcomes'][1:])
    assert (tmp_path / 'out' / b2['COMPANIES'][0][0] / 'attempt-1.body').exists()


@pytest.mark.parametrize('bad', ['duplicate', 'wrong-api', 'business-error'])
def test_bad_envelope_preserves_raw_without_qualifying(tmp_path, bad):
    def raw(code):
        data = json.loads(body(code))
        if bad == 'duplicate':
            data['data']['fields'][-1] = data['data']['fields'][0]
        elif bad == 'wrong-api':
            data['api_name'] = 'daily'
        else:
            data['error'] = 'unauthorized'
        return json.dumps(data).encode()
    request, calls, _ = client(raw)
    result = run(tmp_path, request)
    assert len(calls) == 1
    assert result['outcomes'][0]['status'] == 'RESPONSE_REJECTED_RAW_RETAINED'
    assert (tmp_path / 'out' / b2['COMPANIES'][0][0] / 'attempt-1.body').read_bytes() == raw(b2['COMPANIES'][0][0])


@pytest.mark.parametrize('gap', ['missing-modify', 'wrong-security', 'wrong-period', 'truncated'])
def test_field_and_scope_gaps_are_not_silently_filled(tmp_path, gap):
    def raw(code):
        data = json.loads(body(code))
        if gap == 'missing-modify':
            data['data']['fields'].pop(); data['data']['items'][0].pop()
        elif gap == 'wrong-security':
            data['data']['items'][0][0] = '999999.SZ'
        elif gap == 'wrong-period':
            data['data']['items'][0][2] = '20260630'
        else:
            data['count'] = 101
        return json.dumps(data).encode()
    request, calls, _ = client(raw)
    result = run(tmp_path, request)
    assert len(calls) == 1
    assert result['outcomes'][0]['status'] == 'FIELD_OR_COVERAGE_GAP_RAW_RETAINED'
    receipt = json.loads((tmp_path / 'out' / b2['COMPANIES'][0][0] / 'receipt.json').read_bytes())
    assert receipt['table']['issues'] and len(receipt['table']['rows']) == 1


def test_exception_is_retained_without_leaking_its_text(tmp_path):
    def request(*args):
        raise RuntimeError('sensitive-url-not-to-be-serialized')
    result = run(tmp_path, request)
    assert result['outcomes'][0]['status'] == 'CLIENT_EXCEPTION'
    for p in (tmp_path / 'out').rglob('*'):
        if p.is_file():
            assert b'sensitive-url' not in p.read_bytes()


def test_absent_credential_is_not_a_vendor_refusal(tmp_path, monkeypatch):
    monkeypatch.delenv(relay.SECRET_ENV, raising=False)
    result = run(tmp_path, relay.request)
    assert result['outcomes'][0]['status'] == 'CREDENTIAL_UNAVAILABLE'
    assert not list((tmp_path / 'out').rglob('*.body'))


def test_manual_source_only_workflow_boundary():
    source = (ROOT / '.github/workflows/b2-disclosure-appointments.yml').read_text()
    assert 'workflow_dispatch:' in source and 'schedule:' not in source
    assert 'contents: write' not in source and 'actions: write' not in source
    assert "github.run_attempt == 1" in source and "github.actor == 'auguspp'" in source
    assert 'persist-credentials: false' in source and 'cancel-in-progress: false' in source
    assert b2['CLIENT_BLOB'] in source and 'head_sha=$EXPECTED_CODE' in source
    assert "r['event'] == 'push'" in source and "r['conclusion'] == 'success'" in source
    assert source.count('secrets.') == 1 and 'secrets.TUSHARE_PROXY_API_KEY' in source
    assert 'current-state-read-entry' not in source and 'continue-on-error' not in source


def test_reflected_credential_cannot_be_archived(tmp_path, monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV, 'synthetic-sensitive-value')
    with pytest.raises(ValueError, match='B2_CREDENTIAL_REFLECTION'):
        b2['save'](tmp_path / 'receipt.json', b'{"header":"synthetic-sensitive-value"}')
    assert not (tmp_path / 'receipt.json').exists()
