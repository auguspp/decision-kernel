"""Gap continuity at the real reader seam; synthetic native output, not engine proof."""
from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_price_structure as d
from decision_kernel.runtime import d_price_structure_reading as r
from test_d_price_structure import AT, offline
from test_d_price_structure_reading import seeded, LIMIT, R


def fake_native(source):
    """Only a one-stroke serialized fixture. This does not run or validate CZSC."""
    bi = {'key': 'synthetic-stroke', 'sdt': '2026-01-05', 'edt': '2026-01-09',
          'direction': 'Up', 'a': {'repr': '100'}, 'b': {'repr': '104'}}
    return {'version': d.VERSION, 'algorithm': deepcopy(d.ALGORITHM),
            'parameters': deepcopy(d.PARAMETERS), 'subject': source['subject'],
            'market_session': source['bars'][-1]['session'], 'computed_at': AT,
            'input_hash': canonical_hash(source['bars']), 'bar_count': len(source['bars']),
            'input_members': [{'session': b['session'], 'hash': canonical_hash(b)} for b in source['bars']],
            'state': {'bi_list': [bi], 'finished_keys': [bi['key']], 'zs_list': []},
            'stroke_lifecycles': [{'geometry': bi, 'first_visible': {'replay_session': '2026-01-12'}}]}


@pytest.fixture
def saved(monkeypatch):
    monkeypatch.setattr(r, 'run_native', fake_native)
    collector, root = seeded(monkeypatch)
    output = r.attach(collector, root, retained_limit=LIMIT)
    return output, collector.files[r.PATH]


def successor(monkeypatch, root, body, *, failed=True, body_failure=None):
    collector, current = seeded(monkeypatch)
    collector.previous, collector.previous_commit = root, 'c' * 40
    calls = []
    def read(path, ref):
        calls.append((path, ref))
        assert (path, ref) == (r.PATH, R)
        if body_failure:
            raise body_failure('synthetic history read failure')
        return body
    collector.api.file = read
    if failed:
        # Intentionally retained metadata-only failed archive, like the real case.
        # The current failed input is NOT replaced by the available older source.
        files, archive = collector.archive_cache[123]
        archive['artifact_id'] = 456
        collector.archive_cache[456] = (files, archive)
        current['lanes']['sector']['latest_attempt'] = {
            'conclusion': 'failure', 'operation': {'source': archive}}
        # _cached identity/replay is independently tested; simulate only this
        # failure's metadata-only content while retaining real normalization.
        from decision_kernel.runtime import independent_stock_reading
        original = independent_stock_reading._cached
        def cached(c, ref, at):
            if ref['artifact_id'] == 456:
                return {'operations.json': b'{"status":"FAILED_CLOSED"}'}
            return original(c, ref, at)
        monkeypatch.setattr(independent_stock_reading, '_cached', cached)
    current = model.assemble(code_commit=current['code_commit'], checked_at=AT,
        check_started_at=AT, lanes=current['lanes'], research=current['research'],
        capabilities=[], refresh_identity={})
    return collector, current, calls


def gap_root(saved):
    root, body = saved
    root = deepcopy(root)
    root['research'][r.KEY] = {'status': 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
        'previous_saved_reading': {'commit': R, 'file': root['research'][r.KEY],
            'market_session': '2026-01-30', 'meaning': 'PREVIOUS_READING_NOT_CURRENT_SUCCESS'}}
    return root, body


def test_consecutive_failures_keep_exact_locator_without_current_substitution(monkeypatch, saved):
    root, body = gap_root(saved)
    reference = deepcopy(root['research'][r.KEY]['previous_saved_reading'])
    for _ in range(3):
        collector, current, calls = successor(monkeypatch, root, body)
        output = r.attach(collector, current, retained_limit=LIMIT)
        gap = output['research'][r.KEY]
        assert gap['status'] == 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED'
        assert gap['previous_saved_reading'] == reference
        assert gap['phase'] == 'SOURCE_GEOMETRY' and gap['new_source_requests'] == 0
        assert r.PATH not in collector.files and r.INPUT_PATH not in collector.files
        assert calls == [(r.PATH, R)]
        assert R.encode() in collector.files['README.md']
        assert '不是本次来源成功'.encode() in collector.files['README.md']
        assert output['research']['records'] == current['research']['records']
        assert collector.files['details/prices.json'] == b'original price input'
        root = output


def test_recovery_of_identical_source_keeps_original_clocks(monkeypatch, saved):
    root, body = gap_root(saved)
    collector, current, calls = successor(monkeypatch, root, body, failed=False)
    monkeypatch.setattr(r, 'run_native', lambda *a: pytest.fail('no repeated native computation'))
    output = r.attach(collector, current, retained_limit=LIMIT)
    report = json.loads(collector.files[r.PATH]); old = json.loads(body)
    assert report['reading_status'] == 'SAME_INPUT_REUSED'
    assert report['observed_delta']['status'] == 'UNCHANGED_INPUT_NOT_NEW_MARKET_EVENT'
    assert report['previous_reading_commit'] == R
    assert report['previous_reading_gap'] == 'STRUCTURE_OBSERVATION_INTERRUPTED'
    assert report['computed_at'] == old['computed_at']
    assert report['observed_strokes'] == old['observed_strokes']
    assert '结构观察曾中断'.encode() in collector.files['README.md']
    assert calls == [(r.PATH, R)]
    r._bound(collector.files[r.PATH], output['research'][r.KEY])


@pytest.mark.parametrize('damage', ['commit', 'self', 'path', 'meaning', 'size', 'digest'])
def test_invalid_carried_locator_rejected_before_git_io(monkeypatch, saved, damage):
    root, body = gap_root(saved)
    ref = root['research'][r.KEY]['previous_saved_reading']
    if damage == 'commit': ref['commit'] = 'main'
    elif damage == 'self': ref['commit'] = 'c' * 40
    elif damage == 'path': ref['file']['read_path'] = 'another/file.json'
    elif damage == 'meaning': ref['meaning'] = 'CURRENT_SUCCESS'
    elif damage == 'size': ref['file']['bytes'] = d.MAX_BYTES + 1
    else: ref['file']['sha256'] = 'not-a-digest'
    collector, current, calls = successor(monkeypatch, root, body)
    output = r.attach(collector, current, retained_limit=LIMIT)
    assert output['research'][r.KEY]['previous_reading_gap'] == 'ValueError'
    assert calls == [] and 'previous_saved_reading' not in output['research'][r.KEY]


@pytest.mark.parametrize('damage', ['bytes', 'report_hash', 'session', 'future_clock', 'transport'])
def test_rejected_history_does_not_block_valid_current_source(monkeypatch, saved, damage):
    root, body = gap_root(saved)
    ref = root['research'][r.KEY]['previous_saved_reading']
    if damage == 'bytes': body += b'changed'
    elif damage in ('report_hash', 'future_clock'):
        old = json.loads(body)
        if damage == 'report_hash': old['report_hash'] = '0' * 64
        else:
            old['checked_at'] = '2099-01-01T00:00:00Z'
            old['report_hash'] = canonical_hash({k: v for k, v in old.items() if k != 'report_hash'})
        body = d.encode(old)
        ref['file'].update(bytes=len(body), sha256=model.sha256(body), git_blob=model.blob_sha(body))
    elif damage == 'session': ref['market_session'] = '2026-01-29'
    collector, current, calls = successor(monkeypatch, root, body, failed=False,
        body_failure=OSError if damage == 'transport' else None)
    output = r.attach(collector, current, retained_limit=LIMIT)
    report = json.loads(collector.files[r.PATH])
    assert report['reading_status'] == 'SAVED_SOURCE_COMPUTED'
    assert report['previous_reading_gap'] in ('ValueError', 'OSError')
    assert report['previous_reading_commit'] is None
    assert calls == [(r.PATH, R)]
    assert output['research']['records'] == current['research']['records']


def test_unreadable_history_still_keeps_recorded_locator_on_current_failure(monkeypatch, saved):
    root, body = gap_root(saved)
    collector, current, calls = successor(monkeypatch, root, body, body_failure=OSError)
    output = r.attach(collector, current, retained_limit=LIMIT)
    gap = output['research'][r.KEY]
    assert gap['previous_reading_gap'] == 'OSError'
    assert gap['previous_saved_reading'] == root['research'][r.KEY]['previous_saved_reading']
    assert calls == [(r.PATH, R)] and r.PATH not in collector.files


def test_already_lost_locator_is_not_reconstructed_by_history_search(monkeypatch, saved):
    root, body = gap_root(saved)
    del root['research'][r.KEY]['previous_saved_reading']
    collector, current, calls = successor(monkeypatch, root, body)
    output = r.attach(collector, current, retained_limit=LIMIT)
    assert 'previous_saved_reading' not in output['research'][r.KEY] and calls == []
