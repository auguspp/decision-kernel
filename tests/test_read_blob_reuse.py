"""Original Git publisher with a proved immutable-object cache; no real network."""
import base64
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as d
from decision_kernel.runtime import institutional_radar_reading as r
from decision_kernel.runtime.read_blob_reuse import GitHubReadReuseAPI, pending_blob_writes
from test_concept_radar import no_network
from test_concept_company_reading import inputs, reading

PRIOR, TREE, NEW = 'd'*40, 'e'*40, 'c'*40


def api_fixture(previous, current, *, used=0):
    api = GitHubReadReuseAPI('SYNTHETIC', max_calls=252)
    api.calls = used
    rows = [{'path': p, 'mode': '100644', 'type': 'blob', 'sha': m.blob_sha(b), 'size': len(b)}
            for p, b in previous.items()]
    responses = {
        'git/commits/'+PRIOR: {'sha': PRIOR, 'tree': {'sha': TREE}},
        'git/trees/'+TREE+'?recursive=1': {'sha': TREE, 'truncated': False, 'tree': rows},
        'contents/current-state.json?ref='+NEW: {'type': 'file', 'encoding': 'base64',
            'sha': m.blob_sha(current['current-state.json']),
            'content': base64.b64encode(current['current-state.json']).decode()},
    }
    wire = []
    def call(method, endpoint, body=None):
        api.calls += 1
        assert api.calls <= api.max_calls
        wire.append((method, endpoint, deepcopy(body)))
        if method == 'GET': value = responses[endpoint]
        elif endpoint == 'git/blobs': value = {'sha': m.blob_sha(base64.b64decode(body['content']))}
        elif endpoint == 'git/trees': value = {'sha': 'b'*40}
        elif endpoint == 'git/commits': value = {'sha': NEW}
        else: value = {'ref': body.get('ref')}
        return SimpleNamespace(content=json.dumps(value).encode(), json=lambda: deepcopy(value))
    api._call = call  # Mock the wire, NOT native get/write/publish logic.
    return api, responses, wire


def test_original_publisher_reuses_only_exact_proved_blobs_and_keeps_ref_readback():
    previous = {'current-state.json': b'old-index', 'details/a': b'kept', 'details/b': b'same'}
    current = {'current-state.json': b'new-index', 'details/a': b'kept',
               'details/renamed': b'same', 'details/new': b'new-body'}
    api, _, wire = api_fixture(previous, current)
    api.prime_previous_reading(PRIOR)
    assert api.calls == 2 and pending_blob_writes(api, current) == 2
    result = d.publish(api, current, PRIOR, 'a'*40, 'f'*64)
    assert result == NEW and api.blob_reuse_hits == 2
    posts = [x for x in wire if x[1] == 'git/blobs']
    assert len(posts) == 2
    assert {base64.b64decode(x[2]['content']) for x in posts} == {b'new-index', b'new-body'}
    tree = next(x[2] for x in wire if x[1] == 'git/trees')
    assert tree['base_tree'] == TREE
    assert {x['path']: x['sha'] for x in tree['tree']} == {p: m.blob_sha(b) for p,b in current.items()}
    assert wire[-2][1] == 'contents/current-state.json?ref='+NEW
    assert wire[-1] == ('PATCH', 'git/refs/heads/'+m.READ_REF, {'sha': NEW, 'force': False})
    assert api.calls == 8  # 2 proof reads +2 uploads +tree/commit/readback/ref; cached commit read costs0.


def test_unprimed_cache_preserves_original_all_blob_posts():
    files = {'current-state.json': b'index', 'a': b'kept'}
    api, _, wire = api_fixture(files, files)
    assert pending_blob_writes(api, files) == 2
    d.publish(api, files, PRIOR, 'a'*40, 'f'*64)
    assert len([x for x in wire if x[1] == 'git/blobs']) == 2 and api.blob_reuse_hits == 0


@pytest.mark.parametrize('kind', ['wrong_commit', 'wrong_tree', 'truncated', 'missing_truncated',
    'duplicate_path', 'bad_blob', 'unsafe_path', 'symlink', 'missing_size', 'bool_size'])
def test_unqualified_previous_tree_never_seeds_reuse(kind):
    api, responses, _ = api_fixture({'a': b'old'}, {'current-state.json': b'index'})
    tree = responses['git/trees/'+TREE+'?recursive=1']
    row = tree['tree'][0]
    if kind == 'wrong_commit': responses['git/commits/'+PRIOR]['sha'] = 'f'*40
    elif kind == 'wrong_tree': tree['sha'] = 'f'*40
    elif kind == 'truncated': tree['truncated'] = True
    elif kind == 'missing_truncated': tree.pop('truncated')
    elif kind == 'duplicate_path': tree['tree'].append(deepcopy(row))
    elif kind == 'bad_blob': row['sha'] = 'not-a-sha'
    elif kind == 'unsafe_path': row['path'] = '../bad'
    elif kind == 'symlink': row['mode'] = '120000'
    elif kind == 'missing_size': row.pop('size')
    else: row['size'] = True
    with pytest.raises(ValueError): api.prime_previous_reading(PRIOR)
    assert api.proven_read_blobs == frozenset() and api.blob_reuse_origin is None
    assert pending_blob_writes(api, {'x': b'old'}) == 1


def test_prior_commit_cannot_change_and_same_commit_does_not_requery():
    api, _, _ = api_fixture({'x': b'a'}, {'current-state.json': b'index'})
    api.prime_previous_reading(PRIOR); api.prime_previous_reading(PRIOR)
    assert api.calls == 2
    with pytest.raises(ValueError, match='identity changed'): api.prime_previous_reading('f'*40)
    assert api.calls == 2


def test_bad_readback_preserves_original_no_ref_write_gate():
    previous = {'x': b'old'}; current = {'current-state.json': b'new', 'x': b'old'}
    api, responses, wire = api_fixture(previous, current)
    api.prime_previous_reading(PRIOR)
    data = responses['contents/current-state.json?ref='+NEW]
    data.update(content=base64.b64encode(b'wrong').decode(), sha=m.blob_sha(b'wrong'))
    with pytest.raises(ValueError, match='publication readback mismatch'):
        d.publish(api, current, PRIOR, 'a'*40, 'f'*64)
    assert not any(x[0] == 'PATCH' for x in wire)


def test_final_replacement_bytes_are_reserved_even_when_old_index_is_known(tmp_path):
    api, _, _ = api_fixture({'current-state.json': b'old'}, {'current-state.json': b'new'})
    api.prime_previous_reading(PRIOR)
    col = d.Collector(api, 'a'*40, tmp_path); col.files = {'current-state.json': b'old'}
    api.calls = 247
    r._reserve(col)
    with pytest.raises(ValueError, match='publication reserve'):
        r._reserve(col, replacements={'current-state.json': b'new'})
    assert col.files['current-state.json'] == b'old' and api.calls == 247


def test_actual_source_adapter_fits_same_252_envelope_with_large_prior_reading(tmp_path):
    col, baseline, _, _, _, _ = inputs(tmp_path)
    # Explicit synthetic production-shaped footprint, not a claim about actual R usage.
    col.files.update({f'prior/{n}.txt': str(n).encode() for n in range(150)})
    old_api = col.api
    api, responses, _ = api_fixture(col.files, {'current-state.json': b'not-published-here'}, used=60)
    responses.update(old_api.responses)
    def archive(artifact):
        api.calls += 1
        return old_api.raw_archive if artifact['id'] == 200 else old_api.concept_archive
    api.archive = archive
    col.api = api; col.previous_commit = PRIOR
    before = dict(col.files)
    _, meta, view = reading(col, baseline)
    assert meta['status'] == 'READ_OK' and view['coverage']['concept_companies'] == 4
    assert api.blob_reuse_origin['commit'] == PRIOR
    assert all(col.files[k] == v for k,v in before.items() if k not in {'current-state.json','README.md'})
    assert api.calls + pending_blob_writes(api, col.files) + 5 <= 252
    assert api.calls + len(col.files) + 5 > 252  # Old repeated-POST accounting blocks this footprint.
    assert api.blob_reuse_hits == 0  # No publication/POST was actually performed by this read test.


def test_reuse_is_opt_in_and_does_not_replace_original_publication_code():
    from pathlib import Path
    entry=Path('src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'api_class = base.GitHubAPI' in entry and 'if args.include_concept_discovery:' in entry
    assert 'commit = base.publish(' in entry and 'READ_BLOB_REUSE_HITS=' in entry
