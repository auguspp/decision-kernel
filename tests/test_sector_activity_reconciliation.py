"""Offline transport-level replay of the real 2026-09-25 1/0 count drift.

No market source, live API, scheduler or skipped source qualification.
"""
import json
import runpy
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/scripts/check-sector-scheduled-activity.py'


def module():
    return runpy.run_path(str(SCRIPT))


def empty():
    return {'total_count': 0, 'workflow_runs': []}


def row(identifier, path, status='queued'):
    return {'id': identifier, 'path': path, 'status': status}


class Response:
    status = 200

    def __init__(self, payload, link=''):
        self.raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.headers = {'Link': link}

    def read(self, size):
        return self.raw[:size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def transport(monkeypatch, mod, respond):
    calls, observations = [], []

    class Opener:
        def open(self, request, timeout):
            assert request.get_method() == 'GET' and timeout == 10
            assert request.get_header('Authorization') == 'Bearer PRIVATE-CANARY'
            calls.append(request.full_url)
            return respond(request.full_url)

    monkeypatch.setitem(mod['request_reader'].__globals__, 'build_opener', lambda *args: Opener())
    read = mod['request_reader']('PRIVATE-CANARY', observations=observations)
    return read, calls, observations


@pytest.mark.parametrize('blocker_status', [None, 'queued', 'in_progress', 'waiting', 'pending', 'requested'])
def test_real_count_drift_requires_all_scoped_statuses(monkeypatch, blocker_status):
    mod = module()
    target = '.github/workflows/live-dogfood.yml'

    def respond(url):
        path, query = urlsplit(url).path, parse_qs(urlsplit(url).query)
        status = query['status'][0]
        if path.endswith('/actions/runs'):
            # Exact real diagnostic body; do not assert an unproved race cause.
            return Response(b'{"total_count":1,"workflow_runs":[]}' if status == 'queued' else empty())
        if path.endswith('/live-dogfood.yml/runs') and status == blocker_status:
            return Response({'total_count': 1, 'workflow_runs': [row(901, target+'@refs/heads/main', status)]})
        return Response(empty())

    read, calls, observations = transport(monkeypatch, mod, respond)
    assert mod['check_activity'](read) == ([] if blocker_status is None else [901])
    assert len(calls) == 2 + len(mod['PEERS'])*len(mod['ACTIVE'])
    assert len(set(calls)) == len(calls)  # no broad-query retry/poll
    assert observations[1]['total_count'] == 1 and observations[1]['returned_rows'] == 0
    assert observations[1]['body_sha256'] == '134d1a5f88fc6e48e9e6689b031e057d67c1fff70cbbba5c0e4fa98e8804795c'
    for peer in mod['PEERS']:
        assert {parse_qs(urlsplit(u).query)['status'][0] for u in calls if '/'+peer.split('/')[-1]+'/runs?' in u} == set(mod['ACTIVE'])
    assert 'PRIVATE-CANARY' not in json.dumps(observations)


def test_complete_normal_path_still_uses_only_five_queries(monkeypatch):
    mod = module()
    read, calls, notes = transport(monkeypatch, mod, lambda url: Response(empty()))
    assert mod['check_activity'](read) == []
    assert len(calls) == len(notes) == 5
    assert all('/actions/runs?' in url for url in calls)


def test_observed_blocker_is_not_discarded_during_reconciliation(monkeypatch):
    mod = module()
    def respond(url):
        if '/actions/runs?' in url:
            return Response({'total_count': 2, 'workflow_runs': [row(903, '.github/workflows/decision-inbox.yml')]})
        return Response(empty())
    read, calls, _ = transport(monkeypatch, mod, respond)
    assert mod['check_activity'](read) == [903]
    assert len(calls) == 16


@pytest.mark.parametrize('kind', ['mismatch', 'pagination', 'identity', 'completed', 'duplicate'])
def test_incomplete_or_invalid_scoped_response_never_passes(monkeypatch, kind):
    mod = module()
    target = sorted(mod['PEERS'])[0]
    def respond(url):
        if '/actions/runs?' in url:
            return Response({'total_count': 1, 'workflow_runs': []})
        if kind == 'mismatch':
            return Response({'total_count': 1, 'workflow_runs': []})
        if kind == 'pagination':
            return Response(empty(), '<https://api.github.com/unused?page=2>; rel="next"')
        path = '.github/workflows/unrelated.yml' if kind == 'identity' else target
        one = row(903, path, 'completed' if kind == 'completed' else 'queued')
        rows = [one, one] if kind == 'duplicate' else [one]
        return Response({'total_count': len(rows), 'workflow_runs': rows})
    read, calls, _ = transport(monkeypatch, mod, respond)
    with pytest.raises(mod['CheckError']):
        mod['check_activity'](read)
    assert len(calls) == 2


def test_repository_pagination_is_reconciled_not_ignored(monkeypatch):
    mod = module()
    def respond(url):
        return Response(empty(), '<https://api.github.com/unused?page=2>; rel=next' if '/actions/runs?' in url else '')
    read, calls, _ = transport(monkeypatch, mod, respond)
    assert mod['check_activity'](read) == []
    assert len(calls) == 16
    assert not any('page=2' in url for url in calls)


@pytest.mark.parametrize('kind', ['http401', 'http403', 'http429', 'http500', 'timeout', 'json', 'duplicate_keys', 'oversized'])
def test_transport_or_malformed_errors_do_not_trigger_reconciliation(monkeypatch, kind):
    mod = module()
    def respond(url):
        if kind.startswith('http'):
            raise HTTPError(url, int(kind[4:]), 'PRIVATE-CANARY', {}, None)
        if kind == 'timeout':
            raise URLError(TimeoutError('PRIVATE-CANARY'))
        raw = {'json': b'PRIVATE-CANARY', 'duplicate_keys': b'{"total_count":0,"total_count":0,"workflow_runs":[]}',
               'oversized': b'x'*(mod['MAX_BYTES']+1)}[kind]
        return Response(raw)
    read, calls, notes = transport(monkeypatch, mod, respond)
    with pytest.raises(mod['CheckError']) as error:
        mod['check_activity'](read)
    assert len(calls) == len(notes) == 1
    assert 'PRIVATE-CANARY' not in str(error.value)+json.dumps(notes)


@pytest.mark.parametrize('url', [
    'https://evil.invalid/repos/auguspp/decision-kernel/actions/runs?status=queued&per_page=100&page=1',
    'https://api.github.com/repos/other/repo/actions/runs?status=queued&per_page=100&page=1',
    'https://api.github.com/repos/auguspp/decision-kernel/actions/workflows/../secrets/runs?status=queued&per_page=100&page=1',
    'https://api.github.com/repos/auguspp/decision-kernel/actions/runs?status=queued&per_page=100&page=2',
    'https://api.github.com/repos/auguspp/decision-kernel/actions/runs?status=queued&per_page=100&page=1#fragment',
])
def test_scoped_reader_does_not_expand_to_arbitrary_urls(monkeypatch, url):
    mod = module()
    read, calls, _ = transport(monkeypatch, mod, lambda url: Response(empty()))
    with pytest.raises(mod['CheckError'], match='GITHUB_URL_NOT_ALLOWED'):
        read(url)
    assert calls == []


def test_extra_key_user_is_included_in_scoped_reconciliation(monkeypatch):
    mod = module()
    extra = '.github/workflows/sector-member-reading.yml'
    def respond(url):
        if '/actions/runs?' in url:
            return Response({'total_count': 1, 'workflow_runs': []})
        status = parse_qs(urlsplit(url).query)['status'][0]
        rows = [row(906, extra, status)] if '/sector-member-reading.yml/runs?' in url else []
        return Response({'total_count': len(rows), 'workflow_runs': rows})
    read, calls, _ = transport(monkeypatch, mod, respond)
    assert mod['check_activity'](read, peers=mod['PEERS']|{extra}) == [906]
    assert len(calls) == 21


def test_failure_receipt_survives_before_market_output(monkeypatch, tmp_path, capsys):
    mod = module()
    def respond(url):
        return Response({'total_count': 1, 'workflow_runs': []})
    _, calls, _ = transport(monkeypatch, mod, respond)
    for k,v in {'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
                'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_RUN_ATTEMPT':'1',
                'GITHUB_TOKEN':'PRIVATE-CANARY','GITHUB_STEP_SUMMARY':str(tmp_path/'summary.md')}.items():
        monkeypatch.setenv(k,v)
    assert mod['main']() == 2
    text = capsys.readouterr().out
    assert 'GITHUB_SCOPED_ACTIVITY_RESPONSE_INCOMPLETE' in text
    assert '"total_count": 1' in text and '"returned_rows": 0' in text
    assert text == (tmp_path/'summary.md').read_text()+'\n'
    assert 'PRIVATE-CANARY' not in text
    assert len(calls) == 2
