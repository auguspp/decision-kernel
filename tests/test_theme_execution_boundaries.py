"""Negative execution cases use fake credentials and synthetic transport only."""
from __future__ import annotations

import copy
import json
from datetime import timedelta

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_plan_execution as execute
from decision_kernel.runtime import theme_radar_probe as probe
from test_sector_radar_audit import prohibit_network
from test_theme_plan_execution import prepared
from test_theme_radar_probe import fixture
from test_radar_feed_consumer import AS_OF, contents


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a, **k: pytest.fail('no feed fetch'))


def lookup():
    _, supplied = fixture()
    return {(row['path'], canonical_json(row['params'])): row['response']
            for row in supplied['captures'].values()}


@pytest.mark.parametrize('form', ['escaped-value', 'nested-value', 'escaped-key', 'sensitive-key', 'deep-json'])
def test_response_safety_is_checked_before_retention_and_before_next_request(tmp_path, form):
    _, output, _, pauses, run = prepared(tmp_path)
    bodies, calls = lookup(), []
    secret = 'fake-unit-test-credential-not-a-real-key'
    encoded = ''.join('\\u%04x' % ord(char) for char in secret)
    poisoned = []

    def transport(path, params):
        calls.append((path, params))
        body = copy.deepcopy(bodies[(path, canonical_json(params))])
        if len(calls) == 1:
            if form == 'escaped-value':
                body['diagnostic'] = secret
            elif form == 'nested-value':
                body['diagnostic'] = [{'message': 'prefix ' + secret + ' suffix'}]
            elif form in {'escaped-key', 'sensitive-key'}:
                body['authorization'] = 'test-only-field'
            else:
                nested = 'test-only-leaf'
                for _ in range(40):
                    nested = [nested]
                body['diagnostic'] = nested
            raw = json.dumps(body, ensure_ascii=False).replace(secret, encoded)
            if form == 'escaped-key':
                raw = raw.replace('authorization', '\\u0061uthorization')
            poisoned.append(raw.encode())
            assert secret.encode() not in poisoned[-1]
            return poisoned[-1]
        return json.dumps(body, ensure_ascii=False).encode()

    report = run(transport=transport, credential=secret)
    assert report['status'] == execute.FAILED
    assert len(calls) == len(report['requests']) == 1
    assert pauses == [20]
    assert report['requests'][0]['response_file'] is None
    assert not (output / 'responses').exists()
    assert not (output / 'index.html').exists()
    assert report['failure'] == {'type': 'SectorRadarAuditError'}
    assert all(raw != poisoned[0] and secret.encode() not in raw for raw in contents(output).values())
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


@pytest.mark.parametrize('raw', [None, 'not bytes', b'', b' ' * (probe.MAX_INPUT_BYTES + 1) + b'{}'],
                         ids=['none', 'text', 'empty', 'oversized'])
def test_market_decode_applies_original_body_bound_before_json(raw):
    with pytest.raises(ValueError):
        execute._decode(raw)


def test_replay_decoder_reuses_sensitive_field_guard():
    with pytest.raises(RuntimeError, match='credential-like'):
        execute._decode(b'{"nested":[{"api\\u005fkey":"test-only"}]}')


def test_crossing_saved_day_window_during_pacing_stops_before_first_request(tmp_path):
    _, output, calls, pauses, run = prepared(tmp_path)
    sunday = (AS_OF + timedelta(days=2)).replace(hour=23, minute=59, second=50)
    after = sunday + timedelta(seconds=20)
    clock = iter([sunday, *[after + timedelta(seconds=i) for i in range(100)]])
    report = run(now=lambda: next(clock))
    assert report['status'] == execute.FAILED
    assert calls == [] and report['requests'] == [] and pauses == [20]
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


def test_window_expires_on_receipt_no_more_requests_are_sent(tmp_path):
    _, output, calls, pauses, run = prepared(tmp_path)
    sunday = (AS_OF + timedelta(days=2)).replace(hour=23, minute=59, second=30)
    request = sunday + timedelta(seconds=20)
    received = sunday + timedelta(seconds=40)
    clock = iter([sunday, request, received, *[received + timedelta(seconds=i + 1) for i in range(100)]])
    report = run(now=lambda: next(clock))
    assert report['status'] == execute.FAILED
    assert len(calls) == len(report['requests']) == 1 and pauses == [20]
    assert report['requests'][0]['received_at'] == received.isoformat()
    assert not (output / 'index.html').exists()
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


def test_clock_reversal_is_rejected_before_transport(tmp_path):
    _, output, calls, _, run = prepared(tmp_path)
    clock = iter([AS_OF, AS_OF - timedelta(seconds=1),
                  *[AS_OF + timedelta(seconds=i + 1) for i in range(100)]])
    report = run(now=lambda: next(clock))
    assert report['status'] == execute.FAILED
    assert calls == [] and report['requests'] == []
    assert execute.verify_execution(output)['market_stage_succeeded'] is False


def test_response_clock_reversal_stops_following_requests(tmp_path):
    _, output, calls, _, run = prepared(tmp_path)
    clock = iter([AS_OF, AS_OF + timedelta(seconds=2), AS_OF + timedelta(seconds=1),
                  *[AS_OF + timedelta(seconds=i + 3) for i in range(100)]])
    report = run(now=lambda: next(clock))
    assert report['status'] == execute.FAILED and len(calls) == 1
    assert report['requests'][0]['response_file'] is None
    # Preserve the invalid raw clock claim; do not "repair" it to create a receipt.
    with pytest.raises(ValueError, match='request clocks'):
        execute.verify_execution(output)


def test_last_valid_weekend_seconds_remain_usable(tmp_path, monkeypatch):
    _, output, calls, _, run = prepared(tmp_path)
    failures = []

    def inspected(check):
        def wrapped(*args, **kwargs):
            try:
                return check(*args, **kwargs)
            except ValueError as exc:
                failures.append((check.__name__, str(exc)))
                raise
        return wrapped

    # Diagnostics are confined to this synthetic positive case, never production.
    monkeypatch.setattr(probe, '_window', inspected(probe._window))
    monkeypatch.setattr(execute, '_decode', inspected(execute._decode))
    start = (AS_OF + timedelta(days=2)).replace(hour=23, minute=59, second=0)
    clock = iter(start + timedelta(seconds=i) for i in range(60))
    report = run(now=lambda: next(clock))
    assert report['status'] == execute.COMPLETE, (report['failure'], failures, report['requests'])
    assert len(calls) == 7
    assert execute.verify_execution(output)['market_stage_succeeded'] is True
