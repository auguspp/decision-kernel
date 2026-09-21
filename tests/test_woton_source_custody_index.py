"""The source-preparation note reuses on-demand reading, not eager capacity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import research_archive_index as index


def test_woton_source_note_is_exact_on_demand_without_eager_budget_growth():
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / 'current_state/registry.json').read_text())
    eager, deferred, gaps = index.split(registry)
    record_id = 'p0-000920-h1-original-pdf-custody-20260921'
    assert not gaps
    assert record_id not in {r['id'] for r in eager['references']}
    rows = [r for r in deferred if r['id'] == record_id]
    assert len(rows) == 1
    row = rows[0]
    index.validate(row)
    assert row['case'] == '000920.SZ'
    assert row['archive'] == {'format': 'RETAINED_FILES'}
    assert row['body_materialized_in_reading'] is False
    assert row['qualification'] == index.QUALIFICATION
    assert row['source'] == {
        'repository': 'auguspp/decision-kernel',
        'path': 'docs/readings/woton-original-source-custody-20260921/README.md',
        'ref': 'e9d116bd4f20f6f9a3ed6f2e299fe2a97f9c577b',
        'git_blob': 'f1d709062517854e3eec300cd12541066a7cf2dc',
        'bytes': 6507,
        'sha256': '48e3287c7c366f313933d720999b8f0e7defd589bbf41a894dd76ad2da8022ae',
    }
    note = (root / row['source']['path']).read_bytes()
    assert len(note) == row['source']['bytes']
    assert hashlib.sha256(note).hexdigest() == row['source']['sha256']
    assert hashlib.sha1(b'blob ' + str(len(note)).encode() + b'\0' + note).hexdigest() == row['source']['git_blob']
    assert note == (root / 'docs/woton-report-representation-repair-v1.md').read_bytes()
    assert b'75f3b7e88037d1eb8c2558b9a981ccb25d4dd17a' in note
    assert 'does not materialize' in note.decode()
    assert 'does not materialize' in row['purpose_note']
    assert len(eager['references']) == 49
    specs = {(r['source'].get('ref', 'a' * 40), r['source']['path']) for r in eager['references']}
    assert len(specs) + 13 <= delivery.MAX_SOURCE_FILES == 60
    assert len(eager['references']) + len(deferred) == len(registry['references'])
