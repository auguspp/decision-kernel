"""Publisher clock regression, not a new native/market-data experiment.

The saved-source seam and root assembly are real. Only the native result and
shared Git quota are fixtures, to control elapsed time without sleeping.
"""
from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_price_structure as d
from decision_kernel.runtime import d_price_structure_reading as r
from test_d_price_structure import AT, offline
from test_d_price_structure_reading import seeded, LIMIT

COMPUTED = '2026-10-04T12:00:10+00:00'
FINISHED = '2026-10-04T12:00:20+00:00'


def clock_only_worker(source):
    """No structure assertion: empty native geometry is a clock-test fixture."""
    bars = source['bars']
    return {
        'version': d.VERSION, 'algorithm': d.ALGORITHM, 'parameters': d.PARAMETERS,
        'subject': source['subject'], 'computed_at': COMPUTED,
        'market_session': bars[-1]['session'], 'bar_count': len(bars),
        'input_hash': canonical_hash(bars),
        'input_members': [{'session': b['session'], 'hash': canonical_hash(b)} for b in bars],
        'state': {'bi_list': [], 'finished_keys': [], 'zs_list': []},
        'stroke_lifecycles': [],
    }


@pytest.mark.parametrize('failure', [False, True])
def test_structure_closes_reading_clock_after_computation_or_failure(monkeypatch, failure):
    collector, baseline = seeded(monkeypatch)
    original = deepcopy(baseline)
    collector.now = lambda: FINISHED
    def worker(source):
        if failure:
            raise RuntimeError('synthetic failed worker after baseline cutoff')
        return clock_only_worker(source)
    monkeypatch.setattr(r, 'run_native', worker)
    payload = r.attach(collector, baseline, retained_limit=LIMIT)
    model.validate_read_package(payload)
    assert payload['checks']['finished_at'] == payload['generated_at'] == FINISHED
    assert payload['checks']['started_at'] == baseline['checks']['started_at']
    assert payload['checks']['recheck_after'] == '2026-10-05T12:00:20+00:00'
    assert baseline == original
    assert payload['lanes'] == baseline['lanes']
    assert {k:v for k,v in payload['research'].items() if k != r.KEY} == baseline['research']
    assert collector.files['details/prices.json'] == b'original price input'
    if failure:
        assert payload['research'][r.KEY]['status'] == 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED'
        assert r.PATH not in collector.files
    else:
        saved = json.loads(collector.files[r.PATH])
        assert saved['checked_at'] == FINISHED
        assert model.clock(saved['computed_at']) <= model.clock(payload['generated_at'])
        r._bound(collector.files[r.PATH], payload['research'][r.KEY])


def test_same_input_preserves_computation_but_advances_completed_check(monkeypatch):
    first, baseline = seeded(monkeypatch)
    first.now = lambda: FINISHED
    monkeypatch.setattr(r, 'run_native', clock_only_worker)
    previous = r.attach(first, baseline, retained_limit=LIMIT)
    old_bytes = first.files[r.PATH]
    current, base2 = seeded(monkeypatch)
    current.previous = previous
    current.previous_commit = 'b' * 40
    current.api.file = lambda path, ref: old_bytes
    current.now = lambda: '2026-10-04T12:00:30+00:00'
    def forbidden(*a):
        raise AssertionError('same source cannot rerun native')
    monkeypatch.setattr(r, 'run_native', forbidden)
    result = r.attach(current, base2, retained_limit=LIMIT)
    saved = json.loads(current.files[r.PATH])
    assert saved['reading_status'] == 'SAME_INPUT_REUSED'
    assert saved['computed_at'] == COMPUTED
    assert saved['checked_at'] == result['checks']['finished_at'] == current.now()
    assert first.files[r.PATH] == old_bytes


@pytest.mark.parametrize('bad_clock', ['worker_future', 'reader_backwards'])
def test_unreconciled_clock_does_not_publish_structure(monkeypatch, bad_clock):
    collector, baseline = seeded(monkeypatch)
    before = dict(collector.files)
    collector.now = lambda: FINISHED if bad_clock == 'worker_future' else '2026-10-04T11:59:59+00:00'
    def worker(source):
        value = clock_only_worker(source)
        if bad_clock == 'worker_future':
            value['computed_at'] = '2026-10-04T12:00:30+00:00'
        return value
    monkeypatch.setattr(r, 'run_native', worker)
    result = r.attach(collector, baseline, retained_limit=LIMIT)
    model.validate_read_package(result)
    assert r.PATH not in collector.files
    assert collector.files['details/prices.json'] == before['details/prices.json']
    assert result['lanes'] == baseline['lanes']
    if bad_clock == 'reader_backwards':
        assert result is baseline
        assert collector.files == before
