"""News-only readback transport tests; synthetic bytes are not captured news."""
import base64
import json

import pytest
import requests

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import news_live_publication as live

R, TREE = 'c' * 40, 'd' * 40


def client(monkeypatch, *, size=64):
    raw = {live.MANIFEST: b'{"test_only":true}\n', live.HISTORY: b'x' * size}
    entries = [{'path': path, 'mode': '100644', 'type': 'blob',
                'sha': m.blob_sha(body), 'size': len(body)} for path, body in raw.items()]
    objects = {
        'git/commits/' + R: {'sha': R, 'tree': {'sha': TREE}},
        'git/trees/' + TREE: {'sha': TREE, 'truncated': False, 'tree': entries},
        **{'git/blobs/' + m.blob_sha(body): {'sha': m.blob_sha(body), 'size': len(body),
           'encoding': 'base64', 'content': base64.encodebytes(body).decode('ascii')}
           for body in raw.values()},
    }
    api = live.NewsLiveGitHubAPI('synthetic-test-token', max_calls=20)
    calls = []

    def request(method, url, **options):
        assert method == 'GET'
        assert options['allow_redirects'] is False and options['timeout'] == 45
        assert url.startswith(api.root)
        endpoint = url.removeprefix(api.root)
        calls.append(endpoint)
        value = objects[endpoint]
        response = requests.Response()
        response.status_code = value if type(value) is int else 200
        response._content = json.dumps(value).encode()
        return response

    monkeypatch.setattr(api.session, 'request', request)
    return api, objects, calls, raw


@pytest.mark.parametrize('size', [1024 * 1024 + 1, 2 * 1024 * 1024])
def test_history_above_contents_limit_uses_exact_git_objects(monkeypatch, size):
    api, objects, calls, raw = client(monkeypatch, size=size)
    # Reproduce the documented Contents representation that the original client
    # rejects. Do not weaken that historical client or its implementation hash.
    old = delivery.GitHubAPI('synthetic-test-token')
    monkeypatch.setattr(old, 'get', lambda _: {'type': 'file', 'encoding': 'none',
        'content': '', 'size': size, 'sha': m.blob_sha(raw[live.HISTORY])})
    with pytest.raises(ValueError, match='bounded text file'):
        old.file(live.HISTORY, R)
    assert api.file(live.HISTORY, R) == raw[live.HISTORY]
    assert api.file(live.MANIFEST, R) == raw[live.MANIFEST]
    assert api.file(live.HISTORY, R) == raw[live.HISTORY]
    assert calls == ['git/commits/' + R, 'git/trees/' + TREE,
        'git/blobs/' + m.blob_sha(raw[live.HISTORY]),
        'git/blobs/' + m.blob_sha(raw[live.MANIFEST])]
    assert api.calls == 4  # immutable metadata is shared, never a mutable-ref read


@pytest.mark.parametrize('path,ref', [('../history.json', R), ('other.json', R),
                                     (live.HISTORY, 'main'), (live.HISTORY, None)])
def test_live_read_scope_rejects_before_transport(monkeypatch, path, ref):
    api, _, calls, _ = client(monkeypatch)
    with pytest.raises(ValueError):
        api.file(path, ref)
    assert calls == [] and api.calls == 0


@pytest.mark.parametrize('damage', ['commit', 'tree', 'truncated', 'extra_path',
                                    'symlink', 'oversize', 'blob_sha', 'blob_size', 'body'])
def test_unbound_or_altered_git_objects_fail_closed(monkeypatch, damage):
    api, objects, calls, raw = client(monkeypatch)
    commit = objects['git/commits/' + R]
    tree = objects['git/trees/' + TREE]
    entry = next(row for row in tree['tree'] if row['path'] == live.HISTORY)
    blob = objects['git/blobs/' + m.blob_sha(raw[live.HISTORY])]
    if damage == 'commit': commit['sha'] = 'a' * 40
    elif damage == 'tree': tree['sha'] = 'a' * 40
    elif damage == 'truncated': tree['truncated'] = True
    elif damage == 'extra_path': tree['tree'].append({**entry, 'path': 'other.json'})
    elif damage == 'symlink': entry['mode'] = '120000'
    elif damage == 'oversize': entry['size'] = live.source.MAX_HISTORY_BYTES + 1
    elif damage == 'blob_sha': blob['sha'] = 'a' * 40
    elif damage == 'blob_size': blob['size'] += 1
    elif damage == 'body': blob['content'] = base64.b64encode(b'y' * 64).decode()
    with pytest.raises(ValueError):
        api.file(live.HISTORY, R)
    assert len(calls) <= 3
    if damage in {'symlink', 'oversize'}:
        assert not any(path.startswith('git/blobs/') for path in calls)


@pytest.mark.parametrize('status', [403, 503])
def test_transport_refusal_is_not_retried_or_rerouted(monkeypatch, status):
    api, objects, calls, _ = client(monkeypatch)
    objects['git/commits/' + R] = status
    with pytest.raises(delivery.GitHubReadError, match='GitHub HTTP ' + str(status)):
        api.file(live.HISTORY, R)
    assert calls == ['git/commits/' + R] and api.calls == 1
