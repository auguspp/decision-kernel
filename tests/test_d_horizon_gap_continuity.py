"""Synthetic interrupted-reading regression; not natural session acceptance.

Use the existing full attach fixture for integration. Its Git/registry/quota
seams are synthetic; the native root assembler and horizon implementation run.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_horizon_follow_up as h
from decision_kernel.runtime import stock_market_inputs as p

AT = '2026-12-01T10:00:00+00:00'
LATER = '2026-12-01T10:05:00+00:00'
OLD = 'a' * 40
GAP = 'b' * 40
LIMIT = 20 * 1024 * 1024


def previous():
    body = {'version': h.VERSION, 'checked_at': AT, 'cases': []}
    body['report_hash'] = canonical_hash(body)
    raw = p.dumps(body)
    descriptor = {'read_path': h.PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
                  'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    calls = []
    def file(path, ref):
        calls.append((path, ref))
        assert (path, ref) == (h.PATH, OLD)
        return raw
    collector = SimpleNamespace(previous={'research': {h.KEY: descriptor},
        'checks': {'finished_at': AT}}, previous_commit=OLD, api=SimpleNamespace(file=file))
    return collector, body, calls


def as_gap(collector):
    reference, _ = h._previous_reference(collector)
    collector.previous = {'research': {h.KEY: {
        'status': 'HORIZON_FOLLOW_UP_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
        'previous_saved_reading': reference}}, 'checks': {'finished_at': LATER}}
    collector.previous_commit = GAP
    return reference


def test_single_explicit_locator_survives_gap_without_history_query():
    c, body, calls = previous()
    reference = as_gap(c)
    snapshot = deepcopy(c.previous)
    ref, interrupted = h._previous_reference(c)
    assert interrupted and ref == reference
    assert h._previous(c) == body
    assert calls == [(h.PATH, OLD)] and c.previous == snapshot


def test_legacy_gap_without_locator_remains_unknown_without_read():
    c, _, calls = previous()
    as_gap(c)
    del c.previous['research'][h.KEY]['previous_saved_reading']
    assert h._previous_reference(c) == (None, True)
    assert h._previous(c) is None and calls == []


@pytest.mark.parametrize('field,value', [
    ('read_path', 'different/report.json'), ('read_ref_rule', 'USE_MAIN'),
    ('bytes', True), ('bytes', 0), ('bytes', 10 ** 9),
    ('sha256', 'g' * 64), ('git_blob', 'main'),
])
def test_invalid_locator_refused_before_io(field, value):
    c, _, calls = previous()
    reference = as_gap(c)
    reference['file'][field] = value
    with pytest.raises(ValueError): h._previous(c)
    assert calls == []


def test_gap_self_reference_is_not_a_history_walk():
    c, _, calls = previous()
    ref = as_gap(c); ref['commit'] = GAP
    with pytest.raises(ValueError, match='self reference'): h._previous(c)
    assert calls == []


def test_bytes_failure_does_not_retry_other_refs():
    c, _, calls = previous(); as_gap(c)
    original = c.api.file
    c.api.file = lambda path, ref: original(path, ref) + b' '
    with pytest.raises(ValueError, match='retained bytes'): h._previous(c)
    assert calls == [(h.PATH, OLD)]


def test_hashed_report_cannot_claim_a_clock_after_containing_reading():
    c, _, calls = previous()
    c.previous['checks']['finished_at'] = '2026-12-01T09:59:59+00:00'
    with pytest.raises(ValueError, match='report clock'): h._previous(c)
    assert calls == [(h.PATH, OLD)]


def sequence(monkeypatch):
    from test_d_horizon_follow_up import seeded
    first, base = seeded(monkeypatch)
    valid = h.attach(first, base, retained_limit=LIMIT)
    raw = first.files[h.PATH]
    first_report = p.loads(raw)
    assert first_report['cases'][0]['checkpoints'][0]['change'] == '0.100000000000'
    return seeded, valid, raw, first_report


def fail_prices(*args, **kwargs):
    raise ValueError('synthetic unavailable current price input')


def test_two_failures_then_valid_input_keep_first_clock_and_original_provenance(monkeypatch):
    seeded, prior, raw, first = sequence(monkeypatch)
    old_snapshot = deepcopy(prior)
    calls = []
    for ref in (OLD, GAP):
        c, base = seeded(monkeypatch)
        c.previous, c.previous_commit = prior, ref
        c.now = lambda: LATER
        def file(path, commit):
            calls.append((path, commit)); assert commit == OLD
            return raw
        c.api.file = file
        monkeypatch.setattr(h, 'read_price_parts', fail_prices)
        prior = h.attach(c, base, retained_limit=LIMIT)
        model.validate_read_package(prior)
        gap = prior['research'][h.KEY]
        assert gap['status'] == 'HORIZON_FOLLOW_UP_UNAVAILABLE_OTHER_INPUTS_PRESERVED'
        assert gap['previous_saved_reading']['commit'] == OLD
        assert gap['previous_saved_reading']['file'] == old_snapshot['research'][h.KEY]
        assert h.PATH not in c.files and prior['lanes'] == base['lanes']
    c, base = seeded(monkeypatch)
    c.previous, c.previous_commit = prior, 'c' * 40
    c.now = lambda: LATER
    c.api.file = lambda path, ref: raw if (path, ref) == (h.PATH, OLD) else pytest.fail('wrong prior ref')
    result = h.attach(c, base, retained_limit=LIMIT)
    report = p.loads(c.files[h.PATH]); row = report['cases'][0]
    assert row['checkpoints'][0]['first_recorded_at'] == AT
    assert row['checkpoints'][0]['observation'] == 'UNCHANGED_ENDPOINT_RESULT'
    assert row['contract_hash'] == first['cases'][0]['contract_hash']
    assert row['anchor_session'] == first['cases'][0]['anchor_session']
    assert report['previous_reading_commit'] == OLD
    assert report['previous_reading_gap'] == 'PREVIOUS_HORIZON_READING_INTERRUPTED'
    assert '期限观察曾中断' in c.files['README.md'].decode()
    assert result['lanes'] == base['lanes'] and calls == [(h.PATH, OLD), (h.PATH, OLD)]


def test_declaration_failure_also_keeps_explicit_previous_locator(monkeypatch):
    seeded, prior, raw, _ = sequence(monkeypatch)
    c, base = seeded(monkeypatch)
    c.previous, c.previous_commit = prior, OLD
    c.api.file = lambda *args: raw
    def failed_source(spec): raise OSError('synthetic declaration read failure')
    c.source = failed_source
    result = h.attach(c, base, retained_limit=LIMIT)
    assert result['research'][h.KEY]['previous_saved_reading']['commit'] == OLD
    assert result['research'][h.KEY]['phase'] == 'DECLARATION'
    assert h.PATH not in c.files


def test_unavailable_previous_bytes_preserve_locator_but_not_old_result(monkeypatch):
    seeded, prior, raw, _ = sequence(monkeypatch)
    c, base = seeded(monkeypatch)
    c.previous, c.previous_commit = prior, OLD
    def missing(*args): raise OSError('synthetic original unavailable')
    c.api.file = missing
    monkeypatch.setattr(h, 'read_price_parts', fail_prices)
    result = h.attach(c, base, retained_limit=LIMIT)
    gap = result['research'][h.KEY]
    assert gap['previous_reading_commit'] is None
    assert gap['previous_saved_reading']['commit'] == OLD
    assert gap['previous_saved_reading']['meaning'] == 'PREVIOUS_READING_NOT_CURRENT_SUCCESS'
    assert h.PATH not in c.files
