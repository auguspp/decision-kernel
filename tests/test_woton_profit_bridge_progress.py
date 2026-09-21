"""Check retained financial progress identity, not issuer truth or execution."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from decision_kernel.runtime import research_archive_index as index
from decision_kernel.runtime.research_commit_only import read_research_progress


def test_woton_profit_bridge_is_same_question_r3_on_demand_and_not_execution():
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root / 'current_state/registry.json').read_text())
    records = {r['id']: r for r in registry['references']}
    record = records['p0-000920-reports-only-profit-bridge-20260921']
    old = records['p0-000920-reports-only-working-capital-20260920']
    entry = index.project(record)
    index.validate(entry)
    assert entry['body_materialized_in_reading'] is False
    assert record['archive']['question_id'] == old['archive']['question_id']
    assert record['archive']['expected_sha256'] == 'fbc34d8edd768a4fd499225dc76894bceca098062d9ae393bf1d350a775822f4'
    source = record['archive_source']
    assert source['ref'] == '69305a766eb2cc4b09a6b1a6d4008625e54b8a3d'
    path = root / source['path']
    progress, paper = read_research_progress(path.parent, expected_sha256=record['archive']['expected_sha256'])
    assert {p.name for p in path.parent.iterdir()} == {'workpaper.md', 'progress.json', 'predecessor.json'}
    assert progress['revision'] == 3 and progress['subject'] == '000920.SZ'
    assert progress['question_id'] == record['archive']['question_id']
    assert progress['predecessor']['sha256'] == old['archive']['expected_sha256']
    assert progress['research_status'] == 'RETAINED_PROGRESS_NOT_COMMITTED'
    assert progress['human_acceptance'] == 'NOT_ESTABLISHED_BY_RETENTION'
    assert progress['continuation_status'] == 'NOT_EXECUTED'
    assert progress['investment_authority'] == 'NONE'
    assert len(paper) == source['bytes'] == 14279
    assert hashlib.sha256(paper).hexdigest() == source['sha256']
    assert hashlib.sha1(b'blob ' + str(len(paper)).encode() + b'\0' + paper).hexdigest() == source['git_blob']
    assert '551,260.96' in paper.decode() and 'UNKNOWN' in paper.decode()
    eager, deferred, gaps = index.split(registry)
    assert not gaps and record['id'] not in {r['id'] for r in eager['references']}
    assert entry in deferred
