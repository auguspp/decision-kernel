"""Offline regressions for the isolated fixed-PDF experiment, no live requests."""
import importlib.util
from pathlib import Path
import socket

import pytest
import requests

MODULE = Path(__file__).resolve().parents[1] / 'eval' / 'cninfo_pdf_transport_probe.py'
spec = importlib.util.spec_from_file_location('pdf_probe_eval', MODULE)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BODY = b'%PDF-1.7\nsynthetic transport fixture, not a company PDF\n'


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline test attempted external networking')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(p, 'SAMPLES', (*p.SAMPLES[:2], (*p.SAMPLES[2][:3], p._sha(BODY))))


class Response:
    def __init__(self, status=200, body=BODY, headers=None):
        self.status_code = status
        self.body = body
        self.headers = {'Content-Length': str(len(body))} if headers is None else headers
        self.body_reads = 0
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_content(self, **kwargs):
        self.body_reads += 1
        if self.status_code != 200 or self.headers.get('Content-Encoding') == 'gzip':
            raise AssertionError('rejected response body was read')
        yield self.body


def factory(response=None, error=None):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            if error: raise error('SECRET_REMOTE_MESSAGE')
            return response if response is not None else Response()
    return Session, calls


def test_six_slots_retain_bytes_and_use_original_shapes(tmp_path):
    session, calls = factory()
    output = tmp_path / 'capture'
    result = p.run_probe(output, {'mode': 'SYNTHETIC_TEST_ONLY'}, session_factory=session)
    assert len(calls) == result['attempted_requests'] == 6
    assert all(r['status'] == 'PDF_BYTES_RETAINED_NOT_QUALIFIED' for r in result['records'])
    assert p.verify(output) == 'RETAINED_PROBE_INTEGRITY_CHECKED_NOT_REMOTE_CAUSE_PROVEN'
    assert calls[0][1] == {'headers': p.BASE, 'timeout': (10, 45), 'stream': True, 'allow_redirects': False}
    assert calls[1][1]['headers'] == p.VARIANTS[1][1]
    assert all(u.startswith('https://static.cninfo.com.cn/finalpage/') for u, _ in calls)
    assert result['production_qualification'] == 'NOT_ESTABLISHED'
    assert result['remote_failure_cause'] == result['historical_http_status'] == 'UNKNOWN'


@pytest.mark.parametrize('status', [301, 403, 404, 500, True, '403'])
def test_original_guard_rejects_status_without_reading_body(tmp_path, status):
    response = Response(status=status)
    session, calls = factory(response)
    result = p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 6 and response.body_reads == 0
    assert all(r['status'] == 'REJECTED' for r in result['records'])
    assert result['received_bytes'] == 0
    assert result['records'][0]['http_status'] == (status if type(status) is int else None)


def test_429_stops_without_second_shape_or_retry(tmp_path):
    response = Response(status=429)
    session, calls = factory(response)
    result = p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 1 and response.body_reads == 0
    assert result['stop_reason'] == 'HTTP_429_STOP'
    assert all(r['status'] == 'NOT_ATTEMPTED' for r in result['records'][1:])


@pytest.mark.parametrize('error,reason', [(requests.ConnectionError, 'CONNECTION_FAILED'),
                                         (requests.Timeout, 'REQUEST_TIMEOUT')])
def test_transport_failure_stops_and_never_leaks_exception(tmp_path, error, reason):
    session, calls = factory(error=error)
    output = tmp_path / 'capture'
    result = p.run_probe(output, {}, session_factory=session)
    assert len(calls) == 1 and result['stop_reason'] == reason
    assert result['received_bytes'] == 0
    assert 'SECRET' not in (output / 'result.json').read_text()
    assert all(r['status'] == 'NOT_ATTEMPTED' for r in result['records'][1:])


@pytest.mark.parametrize('headers,reason', [({'Content-Encoding': 'gzip'}, 'UNEXPECTED_CONTENT_ENCODING'),
                                           ({'Content-Length': 'bad'}, 'INVALID_CONTENT_LENGTH'),
                                           ({'Content-Length': '999'}, 'RESPONSE_LENGTH_MISMATCH')])
def test_original_response_guard_and_stream_fail_closed(tmp_path, headers, reason):
    session, calls = factory(Response(headers=headers))
    result = p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 6
    assert all(r['reason'] == reason and r['pdf_file'] is None for r in result['records'])


def test_total_byte_cap_stops_before_unbounded_body(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'MAX_TOTAL_BYTES', 1)
    response = Response()
    session, calls = factory(response)
    result = p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 1 and response.body_reads == 0
    assert result['stop_reason'] == 'TOTAL_BYTE_LIMIT'


def test_control_mismatch_is_not_success_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'SAMPLES', (*p.SAMPLES[:2], (*p.SAMPLES[2][:3], 'a' * 64)))
    session, calls = factory()
    result = p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 5 and result['stop_reason'] == 'CONTROL_HASH_MISMATCH'
    assert result['records'][4]['status'] == 'CONTROL_HASH_MISMATCH'
    assert result['records'][5]['status'] == 'NOT_ATTEMPTED'


def test_corrupt_retained_pdf_fails_verification(tmp_path):
    session, _ = factory()
    output = tmp_path / 'capture'
    p.run_probe(output, {}, session_factory=session)
    next(output.glob('*.pdf')).write_bytes(b'changed')
    with pytest.raises(ValueError, match='RETAINED_PDF_HASH_MISMATCH'):
        p.verify(output)


def test_existing_capture_is_not_overwritten(tmp_path):
    session, calls = factory()
    p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    with pytest.raises(FileExistsError):
        p.run_probe(tmp_path / 'capture', {}, session_factory=session)
    assert len(calls) == 6


def test_native_entry_rejects_second_attempt_and_unknown_head(monkeypatch):
    env = {'GITHUB_REPOSITORY': 'auguspp/decision-kernel', 'GITHUB_REF': 'refs/heads/main',
           'GITHUB_SHA': 'a' * 40, 'EXPECTED_CODE_SHA': 'a' * 40, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
           'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '123'}
    monkeypatch.setattr(p, 'version', lambda _: '2.34.2')
    assert p.native_identity(env)['GITHUB_RUN_ID'] == '123'
    for changes in ({'GITHUB_RUN_ATTEMPT': '2'}, {'EXPECTED_CODE_SHA': 'b' * 40},
                    {'GITHUB_REF': 'refs/heads/other'}, {'GITHUB_EVENT_NAME': 'push'},
                    {'GITHUB_REPOSITORY': 'other/repo'}, {'GITHUB_RUN_ID': ''}):
        with pytest.raises(ValueError): p.native_identity({**env, **changes})
    monkeypatch.setattr(p, 'version', lambda _: '2.32.5')
    with pytest.raises(ValueError, match='REQUESTS_PIN'): p.native_identity(env)


def test_existing_session_disables_env_auth_and_retries():
    with p._session() as session:
        assert session.trust_env is False
        assert len(session.cookies) == 0
        assert session.get_adapter('https://static.cninfo.com.cn/').max_retries.total == 0
