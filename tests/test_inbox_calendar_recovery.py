"""#513: faithful urllib TLS timeout injection, never a live source call."""
from datetime import datetime, timedelta
from hashlib import sha256
import io
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from decision_kernel.runtime import hithink_http as h, attention_inbox_with_odds_watch as app, odds_watch
from decision_kernel.adapters.hithink import HithinkAdapterError
from test_hithink_history_window import _sessions, _calendar_envelope, _history_envelope, SHANGHAI

ROOT = Path(__file__).resolve().parents[1]
OBSERVED = datetime(2026, 8, 28, 16, 30, tzinfo=SHANGHAI)
SECRET = 'fixture-secret-not-for-logs'


class Response:
    def __init__(self, body):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    h._request_hithink_calendar.cache_clear()
    monkeypatch.delenv(h.HITHINK_SECTOR_PACING_ENV, raising=False)
    # Deterministic elapsed budget; no sleeping and no network in the regression.
    ticks = [0.0]
    monkeypatch.setattr(h.time, 'monotonic', lambda: ticks[0])
    monkeypatch.setattr(h.time, 'sleep', lambda seconds: ticks.__setitem__(0, ticks[0] + seconds))
    yield ticks
    h._request_hithink_calendar.cache_clear()
    assert h._calendar_recovery.get() is None


def calendar():
    return h.fetch_hithink_trading_calendar(observed_at=OBSERVED, api_key=SECRET)


def logs(capsys):
    return [json.loads(line.split(' ', 1)[1]) for line in capsys.readouterr().err.splitlines()
            if line.startswith('HITHINK_CALENDAR_ATTEMPT ')]


@pytest.mark.parametrize('transport', ['tls', 'direct_timeout', 'body_timeout'])
def test_one_transient_timeout_recovers_original_qualified_market(monkeypatch, capsys, isolated, transport):
    calls = []
    class ReadTimeout(Response):
        def read(self): raise TimeoutError('untrusted ' + SECRET)
    def open_(request, timeout):
        path = urlsplit(request.full_url).path
        calls.append((path, timeout))
        if len(calls) == 1:
            if transport == 'tls': raise URLError(TimeoutError('TLS ' + SECRET))
            if transport == 'direct_timeout': raise TimeoutError(SECRET)
            return ReadTimeout(b'')
        if path == h.HITHINK_CALENDAR_PATH: return Response(_calendar_envelope(_sessions()))
        return Response(_history_envelope(_sessions()))
    monkeypatch.setattr(h, 'urlopen', open_)
    with h.inbox_calendar_timeout_recovery():
        market = h.fetch_latest_hithink_observed_market(thscode='600000.SH', observed_at=OBSERVED, api_key=SECRET)
        assert calendar() == _sessions()  # Exact original cache, no extra network.
    assert [p for p, _ in calls] == [h.HITHINK_CALENDAR_PATH] * 2 + [h.HITHINK_HISTORY_PATH]
    assert market.market_timestamp.date() == OBSERVED.date()
    assert market.market_price == 14
    assert isolated[0] == 1
    records = logs(capsys)
    assert len(records) == 4 and records[1]['status'] == 'TIMEOUT' and records[1]['retry_scheduled']
    assert records[3]['status'] == 'NORMALIZED_CALENDAR_NOT_PRICE_QUALIFICATION'
    assert records[3]['normalized_sessions_sha256'] == sha256('\n'.join(d.isoformat() for d in _sessions()).encode()).hexdigest()
    assert SECRET not in json.dumps(records)
    for record in records:
        assert record['fallback_provider'] is None and record['max_attempts'] == 2
        assert datetime.fromisoformat(record['requested_at']).utcoffset() is not None
        assert record['requested_shanghai_date'] == '2026-08-28'


@pytest.mark.parametrize('failure', ['429', '401', '403', '500', '502', 'certificate', 'dns', 'text_timeout',
                                    'bad_json', 'unicode', 'non_object', 'business', 'empty', 'duplicate', 'bad_date'])
def test_nontransport_failures_cannot_be_laundered_by_retry(monkeypatch, capsys, failure):
    calls = []
    def open_(request, timeout):
        calls.append(request.full_url)
        if failure.isdigit():
            # Even an HTTPError whose message happens to be a TimeoutError is HTTP.
            raise HTTPError(request.full_url, int(failure), TimeoutError('timeout'), None, None)
        if failure == 'certificate': raise URLError(ssl.SSLCertVerificationError('bad certificate'))
        if failure == 'dns': raise URLError(OSError('DNS'))
        if failure == 'text_timeout': raise URLError('TLS handshake timed out')
        if failure == 'bad_json': return Response(b'{bad')
        if failure == 'unicode': return Response(b'\xff')
        if failure == 'non_object': return Response(b'[]')
        body = _calendar_envelope(_sessions())
        if failure == 'business': body['code'] = 429
        if failure == 'empty': body['data']['item'] = []
        if failure == 'duplicate': body['data']['item'].append(body['data']['item'][-1])
        if failure == 'bad_date': body['data']['item'][0]['date'] = '20260230'
        return Response(body)
    monkeypatch.setattr(h, 'urlopen', open_)
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises((h.HithinkRuntimeError, ValueError)):
            calendar()
        with h.inbox_calendar_timeout_recovery():
            with pytest.raises(h.HithinkRuntimeError, match='no further attempt'): calendar()
    assert len(calls) == 1
    records = logs(capsys)
    assert records[-1]['status'] == 'NON_RETRYABLE_FAILURE' and not records[-1]['retry_scheduled']


def test_exhausted_two_timeouts_latched_within_batch_and_no_old_result(monkeypatch, capsys):
    calls = []
    def fail(request, timeout):
        calls.append(request.full_url)
        raise URLError(TimeoutError('TLS handshake'))
    monkeypatch.setattr(h, 'urlopen', fail)
    with h.inbox_calendar_timeout_recovery():
        for _ in range(3):
            with pytest.raises(h.HithinkRuntimeError): calendar()
    assert len(calls) == 2 and h._request_hithink_calendar.cache_info().currsize == 0
    assert not logs(capsys)[-1]['retry_scheduled']


def test_no_retry_outside_inbox_scope_or_for_historical_prices(monkeypatch, capsys):
    calls = []
    def fail(request, timeout):
        calls.append(request.full_url); raise URLError(TimeoutError('TLS'))
    monkeypatch.setattr(h, 'urlopen', fail)
    with pytest.raises(h.HithinkRuntimeError): calendar()
    assert len(calls) == 1 and logs(capsys) == []
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError):
            h._request_hithink_json(api_key=SECRET, path=h.HITHINK_HISTORY_PATH, params={}, timeout_seconds=10)
    assert len(calls) == 2 and logs(capsys) == []


def test_retry_start_budget_stops_a_late_second_attempt(monkeypatch, isolated, capsys):
    calls = []
    def fail(request, timeout):
        calls.append(timeout); isolated[0] += 31
        raise URLError(TimeoutError('late OS timeout'))
    monkeypatch.setattr(h, 'urlopen', fail)
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError): calendar()
    assert len(calls) == 1 and not logs(capsys)[-1]['retry_scheduled']


def test_next_shanghai_date_never_reuses_yesterdays_calendar(monkeypatch):
    calls = []
    def open_(request, timeout):
        calls.append(request.full_url); return Response(_calendar_envelope(_sessions()))
    monkeypatch.setattr(h, 'urlopen', open_)
    with h.inbox_calendar_timeout_recovery(): calendar()
    with h.inbox_calendar_timeout_recovery():
        h.fetch_hithink_trading_calendar(observed_at=OBSERVED + timedelta(days=1), api_key=SECRET)
    assert len(calls) == 2


@pytest.mark.parametrize('timeout', [0, -1, 11, float('inf'), float('nan'), True])
def test_invalid_recovery_timeout_stops_before_transport(monkeypatch, timeout):
    monkeypatch.setattr(h, 'urlopen', lambda *a, **kw: pytest.fail('network'))
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError):
            h._request_hithink_calendar(api_key=SECRET, shanghai_date=OBSERVED.date(), timeout_seconds=timeout)


@pytest.mark.parametrize('recovered', [True, False])
def test_original_inbox_and_typed_watch_with_real_adapters_not_mocked_decisions(monkeypatch, tmp_path, recovered):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None): return OBSERVED.astimezone(tz)
    monkeypatch.setattr(app, 'datetime', FixedDateTime)
    monkeypatch.setenv(h.HITHINK_API_KEY_ENV, SECRET)
    calls = []
    def open_(request, timeout):
        path = urlsplit(request.full_url).path; calls.append(path)
        if path == h.HITHINK_CALENDAR_PATH:
            if calls.count(path) == 1 or not recovered:
                raise URLError(TimeoutError('The handshake operation timed out'))
            return Response(_calendar_envelope(_sessions()))
        body = _history_envelope(_sessions())
        body['data']['thscode'] = parse_qs(urlsplit(request.full_url).query)['thscode'][0]
        return Response(body)
    monkeypatch.setattr(h, 'urlopen', open_)
    args = [str(ROOT/'dogfood/600519-moutai.json'),
            '--output', str(tmp_path/'inbox.html'), '--summary', str(tmp_path/'summary.md'),
            '--odds-watch-config', str(ROOT/'decision_inputs/odds-watch-v0.json'),
            '--odds-watch-registry', str(ROOT/'current_state/registry.json'),
            '--odds-watch-output', str(tmp_path/'watch')]
    old = tmp_path/'old-success.json'; old.write_bytes(b'original historical success, not today')
    if recovered:
        assert app.main(args, stdout=io.StringIO(), stderr=io.StringIO()) == 0
        assert (tmp_path/'inbox.html').is_file()
        report = odds_watch.read_and_validate(tmp_path/'watch/watch.json')
        assert report['watch']['price_gap_count'] == 0
        assert report['watch']['authority'] == odds_watch.AUTHORITY
        assert calls.count(h.HITHINK_CALENDAR_PATH) == 2
        assert calls.count(h.HITHINK_HISTORY_PATH) == 6
    else:
        with pytest.raises(h.HithinkRuntimeError): app.main(args)
        assert calls == [h.HITHINK_CALENDAR_PATH] * 2
        assert not (tmp_path/'inbox.html').exists() and not (tmp_path/'watch').exists()
    assert old.read_bytes() == b'original historical success, not today'


@pytest.mark.parametrize('terminal', ['http429', 'semantic', 'json'])
def test_second_attempt_must_still_pass_original_checks(monkeypatch, capsys, terminal):
    calls = []
    def open_(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1: raise URLError(TimeoutError('TLS'))
        if terminal == 'http429': raise HTTPError(request.full_url, 429, 'limit', None, None)
        if terminal == 'semantic': return Response({'code': 0, 'data': {'item': []}})
        return Response(b'{bad')
    monkeypatch.setattr(h, 'urlopen', open_)
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises((h.HithinkRuntimeError, ValueError)): calendar()
        with pytest.raises(h.HithinkRuntimeError, match='no further attempt'): calendar()
    assert len(calls) == 2
    records = logs(capsys)
    assert records[-1]['status'] == 'NON_RETRYABLE_FAILURE' and not records[-1]['retry_scheduled']


def test_only_native_typed_timeout_cause_qualifies_not_a_message(monkeypatch):
    calls = []
    def fake(**kwargs):
        calls.append(kwargs['path']); raise h.HithinkRuntimeError('failure_kind=TIMEOUT')
    monkeypatch.setattr(h, '_request_hithink_json', fake)
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError): calendar()
    assert len(calls) == 1


def test_recovery_scope_resets_after_failure_and_preserves_sector_policy(monkeypatch):
    calls = []
    def fail(request, timeout):
        calls.append(request.full_url); raise URLError(TimeoutError('TLS'))
    monkeypatch.setattr(h, 'urlopen', fail)
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError): calendar()
    with pytest.raises(h.HithinkRuntimeError): calendar()  # Outside scope: one request.
    assert len(calls) == 3
    monkeypatch.setenv(h.HITHINK_SECTOR_PACING_ENV, '1')
    with h.inbox_calendar_timeout_recovery():
        with pytest.raises(h.HithinkRuntimeError, match='Sector pacing'): calendar()
    assert len(calls) == 3
