"""Real verifier seams with synthetic historical maps, no source/producer dispatch."""
from concurrent.futures import ThreadPoolExecutor
import json
import socket
import subprocess

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_detail_capture as detail
from decision_kernel.runtime import concept_detail_compat as compat
from decision_kernel.runtime import concept_radar_capture as primary
from test_concept_detail_supplement import base, execute, raw, START


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('saved reading may not call a source or subprocess')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(subprocess, 'run', deny)


def inventory(path):
    return {p.name: p.read_bytes() for p in path.iterdir()}


def seal(path, receipt):
    receipt['capture_hash'] = canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
    (path / 'capture.json').write_bytes(raw(receipt))


def historical_pair(tmp_path, monkeypatch):
    # Construct a coherent SYNTHETIC old primary ZIP and old detail, including
    # the nested base_capture_hash, plans, source metadata and verification.
    with monkeypatch.context() as m:
        m.setattr(primary, '_implementation', lambda: dict(compat.PRIMARY_BEFORE_SECTOR))
        m.setattr(detail, '_implementation', lambda: dict(compat.HISTORICAL_IMPLEMENTATION))
        out, receipt, _, inputs, metadata = execute(tmp_path)
        expected = detail.verify(out)
        primary_expected = primary.verify(tmp_path / 'original')
    return out, receipt, inputs, metadata, expected, primary_expected


def test_reviewed_primary_maps_are_exact_immutable_projections():
    assert len(compat.PRIMARY_FILES) == len(set(compat.PRIMARY_FILES)) == 13
    assert primary._implementation() == compat.PRIMARY_AFTER_QUIET_STOCK_INPUTS
    assert {k for k in compat.PRIMARY_FILES
            if compat.PRIMARY_BEFORE_SECTOR[k] != compat.PRIMARY_AFTER_SECTOR[k]} == {
                'runtime/hithink_sector_breadth_http.py', 'runtime/sector_radar_audit.py'}
    with pytest.raises(TypeError):
        compat.PRIMARY_BEFORE_SECTOR['new'] = '0' * 64


def test_current_primary_still_calls_original_verifier(tmp_path, monkeypatch):
    base(tmp_path)
    root = tmp_path / 'original'
    expected = primary.verify(root)
    before = inventory(root)
    original = primary.verify
    calls = []
    def observe(path):
        calls.append(path)
        return original(path)
    monkeypatch.setattr(primary, 'verify', observe)
    assert compat.verify_primary(root) == (expected, compat.CURRENT)
    assert calls == [root] and inventory(root) == before


def test_nested_historical_source_uses_both_guards_without_mutation(tmp_path, monkeypatch):
    out, _, inputs, metadata, expected, primary_expected = historical_pair(tmp_path, monkeypatch)
    before = inventory(out), inventory(tmp_path / 'original')
    original_functions = primary.verify, primary._implementation, detail.verify, detail.load_base
    with pytest.raises(ValueError, match='CAPTURE_IDENTITY_REJECTED'):
        primary.verify(tmp_path / 'original')
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        detail.verify(out)
    assert compat.verify_primary(tmp_path / 'original') == (primary_expected, compat.PRIMARY_SECTOR_EQUIVALENCE)
    assert compat.verify(out) == (expected, compat.HISTORICAL)
    # Shared load_base is also used by prepare/capture: it must remain strict.
    with pytest.raises(ValueError, match='CAPTURE_IDENTITY_REJECTED'):
        detail.load_base((inputs / 'base.zip').read_bytes(), metadata, at=START)
    assert original_functions == (primary.verify, primary._implementation, detail.verify, detail.load_base)
    assert before == (inventory(out), inventory(tmp_path / 'original'))


@pytest.mark.parametrize('side', ['historical', 'installed'])
@pytest.mark.parametrize('mutation', ['missing', 'extra', 'changed'])
def test_primary_pair_rejects_every_unreviewed_mapping(tmp_path, monkeypatch, side, mutation):
    historical_pair(tmp_path, monkeypatch)
    root = tmp_path / 'original'
    value = dict(compat.PRIMARY_BEFORE_SECTOR if side == 'historical' else compat.PRIMARY_AFTER_SECTOR)
    key = 'runtime/concept_radar_capture.py'
    if mutation == 'missing': del value[key]
    elif mutation == 'extra': value['arbitrary.py'] = '0' * 64
    else: value[key] = '0' * 64
    if side == 'historical':
        receipt = json.loads((root / 'capture.json').read_bytes())
        receipt['implementation'] = value
        seal(root, receipt)
    else:
        monkeypatch.setattr(primary, '_implementation', lambda: value)
    with pytest.raises(ValueError, match='CONCEPT_HISTORICAL_IMPLEMENTATION_REJECTED'):
        compat.verify_primary(root)


def test_primary_reverse_transition_is_not_admitted(tmp_path, monkeypatch):
    base(tmp_path)
    monkeypatch.setattr(primary, '_implementation', lambda: dict(compat.PRIMARY_BEFORE_SECTOR))
    with pytest.raises(ValueError, match='CONCEPT_HISTORICAL_IMPLEMENTATION_REJECTED'):
        compat.verify_primary(tmp_path / 'original')


@pytest.mark.parametrize('filename', ['plan.json', 'observation.json', 'request-1.json', 'response-1.json'])
def test_legacy_primary_replay_checks_original_bytes_after_resealing(tmp_path, monkeypatch, filename):
    historical_pair(tmp_path, monkeypatch)
    root = tmp_path / 'original'
    receipt = json.loads((root / 'capture.json').read_bytes())
    value = json.loads((root / filename).read_bytes())
    value['not_original'] = True
    (root / filename).write_bytes(raw(value))
    receipt['files'] = primary._inventory(root)
    seal(root, receipt)
    with pytest.raises(ValueError):
        compat.verify_primary(root)


def test_unreviewed_nested_base_is_not_laundered_by_outer_map(tmp_path, monkeypatch):
    out, *_ = historical_pair(tmp_path, monkeypatch)
    old = primary._implementation
    monkeypatch.setattr(primary, '_implementation', lambda: {**old(), 'extra': '0' * 64})
    # Keep the separate outer installed guard at the reviewed map, so rejection
    # here proves the NESTED guard rather than failing only the outer detail.
    monkeypatch.setattr(detail, '_implementation', lambda: dict(compat.POST_STOCK_READING_IMPLEMENTATION))
    with pytest.raises(ValueError, match='CONCEPT_HISTORICAL_IMPLEMENTATION_REJECTED'):
        compat.verify(out)


def test_parallel_current_and_historical_calls_leave_both_modules_strict(tmp_path, monkeypatch):
    left = tmp_path / 'left'; right = tmp_path / 'right'
    left.mkdir(); right.mkdir()
    old, _, _, _, old_expected, _ = historical_pair(left, monkeypatch)
    new, *_ = execute(right)
    new_expected = detail.verify(new)
    bindings = primary._implementation, detail._implementation, detail.load_base
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(compat.verify, old)
        two = pool.submit(compat.verify, new)
        assert one.result() == (old_expected, compat.HISTORICAL)
        assert two.result() == (new_expected, compat.CURRENT)
    assert bindings == (primary._implementation, detail._implementation, detail.load_base)
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        detail.verify(old)


def test_normal_primary_reader_uses_reviewed_legacy_verifier(tmp_path, monkeypatch):
    from test_concept_company_reading import inputs
    from decision_kernel.runtime import concept_radar_reading as reader
    from decision_kernel.runtime.radar_company_reading import retained_bytes
    with monkeypatch.context() as m:
        m.setattr(primary, '_implementation', lambda: dict(compat.PRIMARY_BEFORE_SECTOR))
        col, _, _, _, files, _ = inputs(tmp_path)
    report, reference, status = reader.read(col, col.now())
    assert status['status'] == 'VERIFIED_SAVED_CONCEPT_SOURCE'
    assert status['replay_mode'] == compat.PRIMARY_SECTOR_EQUIVALENCE
    assert status['replay'] == json.loads(files['verification.json'])
    for name, body in files.items():
        if name.startswith('payload/'):
            assert retained_bytes(col.files, status['details'][name[8:]]) == body
    assert retained_bytes(col.files, reference) == files['payload/observation.json']
