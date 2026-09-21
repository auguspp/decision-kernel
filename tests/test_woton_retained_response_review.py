"""Actual invalid provider output stays invalid; storage does not authorize a retry."""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil
import socket

import pytest

ROOT = Path('docs/readings/000920-continuation-review-2026-09-21')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('Retained response review must remain offline')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)


def test_exact_real_response_rejects_all_three_unknown_claim_kinds_without_repair():
    before = {p.name: p.read_bytes() for p in ROOT.iterdir() if p.is_file()}
    verify = runpy.run_path(str(ROOT / 'verify.py'))['verify']
    result = verify(ROOT)
    assert result['status'] == 'ORIGINAL_REJECTION_REPRODUCED_NOT_REPAIRED'
    assert len(result['errors']) == 3 and result['originals_checked'] == 5
    assert not result['research_execution_allowed'] and result['new_model_calls'] == 0
    assert {p.name: p.read_bytes() for p in ROOT.iterdir() if p.is_file()} == before


@pytest.mark.parametrize('name', ['pre-model-output.txt','host-receipt.json','input.json','candidate.json','validation.json'])
def test_changed_originals_cannot_masquerade_as_the_saved_rejection(tmp_path, name):
    root = tmp_path / 'review'
    shutil.copytree(ROOT, root)
    (root/name).write_bytes((root/name).read_bytes() + b' ')
    verify = runpy.run_path(str(root/'verify.py'))['verify']
    with pytest.raises(ValueError, match='Retained original identity differs'):
        verify(root)


def test_review_registration_is_on_demand_and_does_not_promote_the_failed_candidate():
    registry = json.loads(Path('current_state/registry.json').read_bytes())
    rows = [r for r in registry['references'] if r['id'] == 'p0-000920-continuation-failure-review-20260921']
    assert len(rows) == 1
    row = rows[0]
    assert row['read_policy'] == 'ON_DEMAND_ARCHIVE' and row['archive']['format'] == 'RETAINED_FILES'
    assert row['case'] == '000920.SZ' and 'source' not in row
    raw = (ROOT/'README.md').read_bytes()
    assert row['archive_source']['path'] == str(ROOT/'README.md')
    assert row['archive_source']['bytes'] == len(raw)
    assert row['archive_source']['sha256'] == sha256(raw).hexdigest()
    assert 'EXECUTION_GAP' in row['purpose_note']
