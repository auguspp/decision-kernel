"""Synthetic compatibility cases; the unchanged real artifact is checked separately."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_detail_compat as compat
from test_concept_detail_supplement import execute, raw, no_network


def seal(root, receipt):
    receipt['capture_hash'] = canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
    (root / 'capture.json').write_bytes(raw(receipt))


def historical(root, receipt):
    # A synthetic fixture, never mutation of a retained historical artifact.
    receipt = deepcopy(receipt)
    receipt['implementation'] = dict(compat.HISTORICAL_IMPLEMENTATION)
    seal(root, receipt)
    return receipt


def inventory(root):
    return {p.name: p.read_bytes() for p in root.iterdir()}


def test_reviewed_pair_is_complete_and_only_reviewed_non_replay_files_differ():
    assert capture._implementation() == compat.POST_DELIVERY_CONTINUITY_IMPLEMENTATION
    assert len(compat.HISTORICAL_IMPLEMENTATION) == len(compat.REPLAY_IMPLEMENTATION) == 17
    assert len(compat.POST_SECTOR_BACKFILL_IMPLEMENTATION) == 17
    assert {k for k in compat.HISTORICAL_IMPLEMENTATION
            if compat.HISTORICAL_IMPLEMENTATION[k] != compat.REPLAY_IMPLEMENTATION[k]} == {
        'runtime/current_state.py', 'runtime/current_state_delivery.py'}
    assert {k for k in compat.REPLAY_IMPLEMENTATION
            if compat.REPLAY_IMPLEMENTATION[k] != compat.POST_SECTOR_BACKFILL_IMPLEMENTATION[k]} == {
        'runtime/hithink_sector_breadth_http.py', 'runtime/sector_radar_audit.py'}
    with pytest.raises(TypeError):
        compat.HISTORICAL_IMPLEMENTATION['extra'] = '0' * 64
    with pytest.raises(TypeError):
        compat.POST_SECTOR_BACKFILL_IMPLEMENTATION['extra'] = '0' * 64


def test_current_capture_still_uses_original_verifier_and_remains_unchanged(tmp_path):
    root, receipt, *_ = execute(tmp_path)
    before = inventory(root)
    assert compat.verify(root) == (capture.verify(root), compat.CURRENT)
    assert inventory(root) == before


def test_historical_rebuild_is_exact_and_original_verifier_stays_strict(tmp_path):
    root, receipt, *_ = execute(tmp_path)
    expected = capture.verify(root)
    receipt = historical(root, receipt)
    expected['capture_hash'] = receipt['capture_hash']
    before = inventory(root)
    identity_function = capture._implementation
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        capture.verify(root)
    assert compat.verify(root) == (expected, compat.HISTORICAL)
    assert inventory(root) == before
    assert capture._implementation is identity_function
    assert capture.verify.__globals__['_implementation'] is identity_function
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        capture.verify(root)


@pytest.mark.parametrize('name', sorted(compat.HISTORICAL_IMPLEMENTATION))
@pytest.mark.parametrize('mutation', ['changed', 'missing'])
def test_every_historical_fingerprint_is_required(tmp_path, name, mutation):
    root, receipt, *_ = execute(tmp_path)
    receipt = historical(root, receipt)
    if mutation == 'changed':
        receipt['implementation'][name] = '0' * 64
    else:
        del receipt['implementation'][name]
    seal(root, receipt)
    with pytest.raises(ValueError, match='DETAIL_HISTORICAL_IMPLEMENTATION_REJECTED'):
        compat.verify(root)


@pytest.mark.parametrize('side', ['historical', 'installed'])
@pytest.mark.parametrize('mutation', ['extra', 'unknown', 'missing'])
def test_unreviewed_pair_rejected_even_with_resealed_receipt(tmp_path, monkeypatch, side, mutation):
    root, receipt, *_ = execute(tmp_path)
    receipt = historical(root, receipt)
    value = dict(compat.REPLAY_IMPLEMENTATION) if side == 'installed' else receipt['implementation']
    if mutation == 'extra':
        value['runtime/extra.py'] = '0' * 64
    elif mutation == 'missing':
        del value['runtime/current_state.py']
    else:
        value['runtime/current_state.py'] = '0' * 64
    if side == 'installed':
        monkeypatch.setattr(capture, '_implementation', lambda: value)
    else:
        seal(root, receipt)
    with pytest.raises(ValueError, match='DETAIL_HISTORICAL_IMPLEMENTATION_REJECTED'):
        compat.verify(root)


@pytest.mark.parametrize('mutation', ['receipt_hash', 'inventory', 'report', 'plan', 'base', 'authority', 'clock'])
def test_full_validation_still_runs_for_historical_pair(tmp_path, mutation):
    root, receipt, *_ = execute(tmp_path)
    receipt = historical(root, receipt)
    if mutation == 'receipt_hash':
        receipt['capture_hash'] = '0' * 64
        (root / 'capture.json').write_bytes(raw(receipt))
    elif mutation == 'inventory':
        (root / 'response-1.json').write_bytes((root / 'response-1.json').read_bytes() + b' ')
    else:
        if mutation == 'report':
            value = json.loads((root / 'observation.json').read_bytes())
            value['projection']['companies'][0]['source_names'] = ['FORGED']
            value['projection_hash'] = canonical_hash(value['projection'])
            (root / 'observation.json').write_bytes(raw(value))
        elif mutation == 'plan':
            value = json.loads((root / 'plan.json').read_bytes())
            value['selection']['plan']['offset'] = 3
            (root / 'plan.json').write_bytes(raw(value))
        elif mutation == 'base':
            (root / 'base.zip').write_bytes((root / 'base.zip').read_bytes() + b'changed')
        elif mutation == 'authority':
            receipt['investment_authority'] = 'BUY'
        else:
            receipt['finished_at'] = '2000-01-01T00:00:00Z'
        receipt['files'] = capture._inventory(root)
        seal(root, receipt)
    before = inventory(root)
    with pytest.raises(ValueError):
        compat.verify(root)
    assert inventory(root) == before


def test_simultaneous_current_and_historical_replay_never_mutates_module(tmp_path):
    a = tmp_path / 'a'; b = tmp_path / 'b'; a.mkdir(); b.mkdir()
    current, *_ = execute(a)
    old, receipt, *_ = execute(b)
    expected_current = capture.verify(current)
    expected_old = capture.verify(old)
    receipt = historical(old, receipt)
    expected_old['capture_hash'] = receipt['capture_hash']
    fn = capture._implementation
    with ThreadPoolExecutor(max_workers=2) as pool:
        left = pool.submit(compat.verify, current)
        right = pool.submit(compat.verify, old)
        assert left.result() == (expected_current, compat.CURRENT)
        assert right.result() == (expected_old, compat.HISTORICAL)
    assert capture._implementation is fn
    assert capture.verify(current) == expected_current
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        capture.verify(old)
