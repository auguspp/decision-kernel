"""Offline capture/replay contracts; synthetic requests are not new live evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import current_state as m, news_daily as s

TIME = '2026-09-20T04:00:00+00:00'
IDENTITY = {'repository': m.REPOSITORY, 'ref': 'refs/heads/main', 'event': 'workflow_dispatch',
            'code_commit': 'b'*40, 'run_id': 901, 'attempt': 1,
            'workflow': s.WORKFLOW, 'trigger_run_id': None}
IMAGE = (json.dumps([s.IMAGE]) + ' sha256:' + 'c'*64 + '\n').encode()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('News unit test attempted external networking')
    monkeypatch.setattr(socket, 'create_connection', fail)
    monkeypatch.setattr(socket, 'getaddrinfo', fail)
    monkeypatch.setattr(socket.socket, 'connect', fail)


def body(label, *, items=None):
    host = s.news.NEWS_DOMAINS[label][0]
    return m.json_bytes({'id': label, 'status': 'success', 'items': [
        {'id': '1', 'title': '公司甲公开资料有待核对<script>x</script>',
         'url': 'https://' + host + '/detail/1'}] if items is None else items})


def captured(tmp_path, request=None, *, clock=lambda: TIME):
    root = tmp_path / 'capture'
    result = s.capture(root, deepcopy(IDENTITY), IMAGE,
                       request=request or (lambda label: (200, body(label))), clock=clock)
    return root, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}, result


def test_all_seven_sources_roundtrip_through_original_normalizers(tmp_path):
    calls = []
    def request(label):
        calls.append(label); return 200, body(label)
    root, files, report = captured(tmp_path, request)
    assert tuple(calls) == s.SOURCES
    assert s.rebuild(files, cutoff=TIME) == report
    p = report['projection']
    assert p['status'] == 'WINDOWS_CAPTURED' and p['coverage']['normalized_sources'] == 7
    assert len(p['news']['projection']['observations']) == 7
    assert all(r['qualification'] == 'CONTEXT_ONLY' and r['question_status'] == 'NOT_FORMED'
               for r in p['news']['projection']['observations'])
    assert p['upstream_request_count'] == 'UNKNOWN' and p['local_service_requests'] == 7
    assert p['research_executions'] == p['model_calls'] == p['new_attention_events'] == 0
    with pytest.raises(ValueError, match='create-only'):
        s.capture(root, IDENTITY, IMAGE, request=request, clock=lambda: TIME)
    assert len(calls) == 7


@pytest.mark.parametrize('problem', ['timeout', 'forbidden', 'empty-body', 'bad-json', 'oversize'])
def test_one_source_failure_is_visible_and_does_not_erase_six_peers(tmp_path, problem):
    def request(label):
        if label != 'cls': return 200, body(label)
        if problem == 'timeout': raise TimeoutError('Do not retain arbitrary exception text')
        if problem == 'forbidden': return 403, b'not allowed'
        if problem == 'empty-body': return 200, b''
        if problem == 'bad-json': return 200, b'not JSON'
        return 200, b'x' * (s.MAX_BODY + 1)
    _, files, report = captured(tmp_path, request)
    assert report['projection']['status'] == 'PARTIAL_NEWS_WINDOWS'
    assert report['projection']['coverage']['normalized_sources'] == 6
    assert report['projection']['source_outcomes'][0]['status'] != 'OBSERVATIONS_NORMALIZED'
    assert b'Do not retain arbitrary' not in b''.join(files.values())
    assert s.rebuild(files, cutoff=TIME) == report


def test_empty_windows_are_not_source_failure_or_complete_news_coverage(tmp_path):
    _, files, report = captured(tmp_path, lambda label: (200, body(label, items=[])))
    p = report['projection']
    assert p['status'] == 'WINDOWS_CAPTURED'
    assert p['news']['projection']['observations'] == []
    assert all(o['observations_in_window'] == 0 for o in p['source_outcomes'])
    assert p['coverage']['complete_news_coverage'] is False


def test_repeated_capture_time_does_not_create_new_article_versions(tmp_path):
    _, _, first = captured(tmp_path / 'one')
    _, _, second = captured(tmp_path / 'two', clock=lambda: '2026-09-21T04:00:00+00:00')
    ids = lambda r: sorted(x['version_id'] for x in r['projection']['news']['projection']['observations'])
    assert ids(first) == ids(second)
    assert first['projection']['captured_through'] != second['projection']['captured_through']


@pytest.mark.parametrize('field,value', [('repository', 'other/repo'), ('ref', 'refs/heads/other'),
    ('attempt', 2), ('attempt', True), ('event', 'push'), ('code_commit', 'x'*40),
    ('workflow', '.github/workflows/other.yml'), ('trigger_run_id', 999)])
def test_identity_is_rejected_before_any_request(tmp_path, field, value):
    identity = {**IDENTITY, field: value}; calls = []
    with pytest.raises((ValueError, TypeError)):
        s.capture(tmp_path/'capture', identity, IMAGE, request=lambda label: calls.append(label), clock=lambda: TIME)
    assert calls == [] and not (tmp_path/'capture').exists()


@pytest.mark.parametrize('damage', ['body', 'manifest', 'missing', 'extra', 'cutoff', 'receipt-hash'])
def test_saved_input_corruption_or_future_capture_is_rejected(tmp_path, damage):
    _, files, _ = captured(tmp_path)
    if damage == 'body': files['raw/newsnow-cls.json'] += b' '
    elif damage == 'manifest':
        val=json.loads(files['capture.json']); val['files']['plan.json']['bytes'] += 1
        files['capture.json']=m.json_bytes(val)
    elif damage == 'missing': del files['receipts/cls.json']
    elif damage == 'extra': files['untrusted.py'] = b'raise RuntimeError("must not execute")'
    elif damage == 'receipt-hash':
        path='receipts/cls.json'; val=json.loads(files[path]); val['sha256']='f'*64
        files[path]=m.json_bytes(val)
        manifest=json.loads(files['capture.json']); manifest['files'][path]={'bytes':len(files[path]),'sha256':m.sha256(files[path])}
        files['capture.json']=m.json_bytes(manifest)
    cutoff='2026-09-19T04:00:00+00:00' if damage=='cutoff' else TIME
    with pytest.raises((ValueError, KeyError)):
        s.rebuild(files, cutoff=cutoff)


def test_bad_image_pin_and_symlink_are_rejected(tmp_path):
    with pytest.raises(ValueError, match='digest'):
        s.capture(tmp_path/'bad', IDENTITY, IMAGE.replace(b'98b62', b'88b62'), clock=lambda: TIME)
    target=tmp_path/'target'; target.mkdir(); link=tmp_path/'link'; link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='create-only'):
        s.capture(link/'out', IDENTITY, IMAGE, clock=lambda: TIME)


@pytest.mark.parametrize('damage', ['url', 'encoding', 'length', 'over-read', 'truncated'])
def test_transport_uses_original_no_redirect_and_bounded_local_only_get(monkeypatch, damage):
    class Response:
        status=200
        headers={}
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def geturl(self): return 'https://other.test/' if damage=='url' else s.url('cls')
        def read(self, limit):
            assert limit==s.MAX_BODY+1
            return b'x'*(s.MAX_BODY+1) if damage=='over-read' else b'{}'
    response=Response()
    if damage=='encoding': response.headers={'Content-Encoding':'gzip'}
    elif damage=='length': response.headers={'Content-Length':str(s.MAX_BODY+1)}
    elif damage=='truncated': response.headers={'Content-Length':'100'}
    class Opener:
        def open(self, request, timeout):
            assert request.full_url==s.url('cls') and timeout==15
            assert not any(k.lower()=='authorization' for k,v in request.header_items())
            return response
    def opener(*handlers):
        assert any(isinstance(h, s._NoRedirect) for h in handlers)
        assert any(isinstance(h, s.ProxyHandler) and h.proxies=={} for h in handlers)
        return Opener()
    monkeypatch.setattr(s, 'build_opener', opener)
    with pytest.raises(ValueError): s.fetch('cls')


def test_no_future_claim_is_promoted_to_a_publication_fact(tmp_path):
    def request(label):
        val=json.loads(body(label)); val['items'][0]['pubDate']='2027-01-01T00:00:00Z'
        return 200,m.json_bytes(val)
    _, _, report=captured(tmp_path,request)
    row=report['projection']['news']['projection']['observations'][0]
    assert row['publication_claims']['pubDate']['status']=='FUTURE_CLAIM'
    assert row['qualification']=='CONTEXT_ONLY'
