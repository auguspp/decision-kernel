"""Synthetic source-capture checks, not live CNINFO/date acceptance."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest
import requests
from decision_kernel.runtime import tushare_relay as relay

ROOT = Path(__file__).resolve().parents[1]
b2 = runpy.run_path(str(ROOT / '.github/scripts/b2-disclosure-appointments.py'))
NOW = '2099-01-01T00:00:00+00:00'
IDENTITY = {'test_only': 'SYNTHETIC_NOT_A_GITHUB_RUN'}


def body(code):
    # Fields deliberately stay raw; no positional mapping, date fill or certification.
    return json.dumps({'prbookinfos': [{'code': code, 'first': '2099-02-01',
        'actual': None, 'change1': None, 'change2': 'raw revision'}]}, ensure_ascii=False).encode()


def client(factory=body, *, http=200, complete=True, error=None):
    calls = []
    def request(params, *, clock):
        calls.append(deepcopy(params))
        return {'http_status': http, 'headers': {}, 'raw': factory(params['stockCode']),
                'body_complete': complete, 'error_type': error,
                'requested_at': clock(), 'received_at': clock()}
    return request, calls


def run(tmp_path, request):
    return b2['capture'](tmp_path / 'out', IDENTITY, request=request, clock=lambda: NOW)


def test_six_public_requests_retain_raw_without_certifying_dates(tmp_path):
    request, calls = client()
    result = run(tmp_path, request)
    assert [p['stockCode'] for p in calls] == [c[0][:6] for c in b2['COMPANIES']]
    assert calls[0]['stockCode'] == '603986'
    assert all(p['sectionTime'] == '2026-09-30' and p['pagesize'] == '100'
               and p['pagenum'] == '1' for p in calls)
    assert result['status'] == 'CAPTURED_REQUIRES_SOURCE_REVIEW'
    assert result['official_appointment_qualified'] is False
    for o in result['outcomes']:
        d = tmp_path / 'out' / o['code']
        receipt = json.loads((d / 'receipt.json').read_bytes())
        original = (d / 'response.body').read_bytes()
        assert original == body(o['code'][:6])
        assert receipt['response']['sha256'] == sha256(original).hexdigest()
        assert receipt['date_qualification'] == 'NOT_PERFORMED'
        assert receipt['official_appointment_qualified'] is False
        assert receipt['row_count'] == 1
    with pytest.raises(FileExistsError):
        run(tmp_path, request)
    assert len(calls) == 6


def test_empty_does_not_prove_no_appointment(tmp_path):
    request, calls = client(lambda _: b'{"prbookinfos":[]}')
    result = run(tmp_path, request)
    assert len(calls) == 6
    assert all(o['status'] == 'EMPTY_RESPONSE_NOT_NO_APPOINTMENT' for o in result['outcomes'])


@pytest.mark.parametrize('http', [302, 401, 403, 429, 503])
def test_non_success_retains_raw_and_stops_no_fallback(tmp_path, http):
    request, calls = client(lambda _: b'{"error":"synthetic"}', http=http)
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
    assert all(o['status'] == 'NOT_QUERIED_AFTER_STOP' and o['receipt'] is None
               for o in result['outcomes'][1:])
    assert (tmp_path / 'out' / '603986.SH' / 'response.body').read_bytes() == b'{"error":"synthetic"}'


@pytest.mark.parametrize('raw', [b'{"prbookinfos":[],"prbookinfos":[]}',
    b'{"prbookinfos":null}', b'{"prbookinfos":[42]}',
    json.dumps({'prbookinfos': [{}] * 100}).encode()])
def test_schema_or_coverage_gap_keeps_bytes(tmp_path, raw):
    request, calls = client(lambda _: raw)
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['outcomes'][0]['status'] == 'RESPONSE_GAP_RAW_RETAINED'
    assert (tmp_path / 'out' / '603986.SH' / 'response.body').read_bytes() == raw


def test_partial_stream_and_missing_body_are_not_complete(tmp_path):
    request, calls = client(lambda _: b'{"partial":', complete=False, error='ChunkedEncodingError')
    result = run(tmp_path, request)
    assert len(calls) == 1 and result['status'] == 'STOPPED_WITH_GAPS'
    receipt = json.loads((tmp_path / 'out' / '603986.SH' / 'receipt.json').read_bytes())
    assert receipt['response']['body_complete'] is False
    assert (tmp_path / 'out' / '603986.SH' / 'response.body').read_bytes() == b'{"partial":'


def test_changed_scope_stops_before_effects(tmp_path, monkeypatch):
    monkeypatch.setitem(b2['SCOPE'], 'sha256', '0' * 64)
    request, calls = client()
    with pytest.raises(relay.RelayError, match='B2_SCOPE_BYTES'):
        run(tmp_path, request)
    assert calls == [] and not (tmp_path / 'out').exists()


def test_exception_message_not_retained(tmp_path):
    def request(*args, **kwargs):
        raise RuntimeError('sensitive-url-not-to-be-serialized')
    result = run(tmp_path, request)
    assert result['status'] == 'STOPPED_WITH_GAPS'
    assert all(b'sensitive-url' not in p.read_bytes() for p in (tmp_path/'out').rglob('*') if p.is_file())


def test_transport_has_no_credentials_retry_redirect_or_cross_object_session():
    calls = []
    class Response:
        status_code = 503
        headers = {'Content-Type': 'application/json'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size): yield b'{"error":"synthetic"}'
    class Session:
        trust_env = True
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            assert self.trust_env is False and url == b2['URL']
            assert kwargs['allow_redirects'] is False and kwargs['stream'] is True
            assert kwargs['timeout'] == (5, 15)
            assert kwargs['headers'] == {'Accept': 'application/json', 'Accept-Encoding': 'identity'}
            assert 'auth' not in kwargs and 'cookies' not in kwargs
            calls.append(kwargs)
            return Response()
    result = b2['public_request']({'stockCode': '603986'}, clock=lambda: NOW, session_factory=Session)
    assert len(calls) == 1 and result['http_status'] == 503
    assert result['raw'] == b'{"error":"synthetic"}' and result['body_complete'] is True
    with requests.Session() as original:
        assert original.get_adapter('https://').max_retries.total == 0


def test_stream_failure_preserves_prefix_without_exception_text():
    class Response:
        status_code = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_content(self, chunk_size):
            yield b'{"prefix":'
            raise requests.ConnectionError('not-for-serialization')
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response()
    result = b2['public_request']({}, clock=lambda: NOW, session_factory=Session)
    assert result['raw'] == b'{"prefix":' and result['body_complete'] is False
    assert result['error_type'] == 'ConnectionError' and 'not-for-serialization' not in str(result)


def test_reflected_credential_cannot_be_archived(tmp_path, monkeypatch):
    monkeypatch.setenv(relay.SECRET_ENV, 'synthetic-sensitive-value')
    with pytest.raises(ValueError, match='B2_CREDENTIAL_REFLECTION'):
        b2['save'](tmp_path / 'receipt.json', b'synthetic-sensitive-value')
    assert not (tmp_path / 'receipt.json').exists()


def test_manual_workflow_keeps_main_gates_without_business_secrets():
    source = (ROOT / '.github/workflows/b2-disclosure-appointments.yml').read_text()
    assert 'workflow_dispatch:' in source and 'schedule:' not in source
    assert 'contents: write' not in source and 'actions: write' not in source
    assert "github.run_attempt == 1" in source and "github.actor == 'auguspp'" in source
    assert 'persist-credentials: false' in source and 'cancel-in-progress: false' in source
    assert 'head_sha=$EXPECTED_CODE' in source and "r['conclusion'] == 'success'" in source
    assert 'secrets.' not in source and 'TUSHARE_PROXY_API_KEY' not in source
    assert 'continue-on-error' not in source and 'current-state-read-entry' not in source
