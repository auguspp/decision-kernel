"""Replay this case with the unchanged repository evaluator; no network or writes to inputs.

Review the script before running. Supply the seven original ZIPs and trusted source
modules named in source-index.json. An incomplete full ledger exits 2 with its report.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import socket
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_zip(root: Path, row: dict) -> ZipFile:
    path = root / row['file']
    require(path.parent == root and path.is_file() and not path.is_symlink(), 'source path')
    raw = path.read_bytes()
    require(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'source ZIP identity')
    z = ZipFile(path)
    require(z.testzip() is None, 'source ZIP CRC')
    return z


def run(args) -> int:
    here = Path(__file__).resolve().parent
    index = json.loads((here / 'source-index.json').read_bytes())
    expected = json.loads((here / 'cohort.json').read_bytes())
    require(not args.output.exists(), 'output must be new')
    for path, blob in index['modules'].items():
        raw = (args.code_root / path.removeprefix('src/')).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(actual == blob, 'trusted source module differs: ' + path)
    sys.path.insert(0, str(args.code_root.resolve()))
    def offline(*a, **k):
        raise RuntimeError('this retained replay makes no network request')
    socket.socket.connect = offline
    socket.create_connection = offline
    from decision_kernel.identity import canonical_hash, canonical_json
    from decision_kernel.adapters.hithink import normalize_hithink_calendar
    from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle
    from decision_kernel.runtime.sector_radar_outcomes import evaluate_sector_radar_outcomes, render_sector_radar_outcomes
    bundles = []
    with TemporaryDirectory() as temp:
        for row in index['state_bundles']:
            dest = Path(temp) / row['session']
            dest.mkdir()
            with read_zip(args.sources, row) as z:
                names = {'manifest.json', 'market-state.json', 'candidate-events.json'}
                require(len(z.namelist()) == 3 and set(z.namelist()) == names, 'bundle inventory')
                for name in sorted(names):
                    (dest / name).write_bytes(z.read(name))
            b = load_sector_radar_persistent_bundle(dest, expected_repository=index['repository'],
                expected_workflow=index['workflow'], expected_parent_hint_mapping_hash=index['parent_hint_mapping_hash'])
            m = b.manifest
            require((m.source_run_id, m.source_commit_sha, m.source_run_attempt, m.manifest_hash,
                     m.market_session.isoformat(), b.market_state.state_hash) ==
                    (row['run_id'], row['source_head'], 1, row['manifest_hash'], row['session'], row['state_hash']),
                    'bundle and observed original run identity disagree')
            bundles.append(b)
    row = index['calendar_audit']
    with read_zip(args.sources, row) as z:
        audit = json.loads(z.read('input-audit/manifest.json'))
        require(audit['audit_hash'] == canonical_hash({k:v for k,v in audit.items() if k != 'audit_hash'}), 'audit hash')
        for name, descriptor in audit['files'].items():
            raw = z.read('input-audit/' + name)
            require(len(raw) == descriptor['bytes'] and sha(raw) == descriptor['sha256'], 'audit inventory')
        raw = z.read(row['member'])
        require(len(raw) == row['calendar_bytes'] and sha(raw) == row['calendar_sha256'], 'calendar bytes')
        calendar = normalize_hithink_calendar(json.loads(raw))
    result = evaluate_sector_radar_outcomes(ledger=bundles[-1].event_ledger,
        states=[b.market_state for b in bundles], trading_sessions=calendar,
        as_of_session=date.fromisoformat(expected['as_of_session']),
        generated_at=datetime.fromisoformat(index['evaluation_generated_at']))
    require(result['evaluation_hash'] == index['evaluation_hash'] == expected['original_evaluation_hash'], 'evaluation differs')
    raw = (canonical_json(result) + '\n').encode()
    require(sha(raw) == index['native_output_sha256'], 'full native output differs')
    p = result['evaluation']
    require(p['status_counts'] == expected['status_counts'], 'coverage differs')
    require(p['event_count'] == expected['original_ledger_event_count'], 'ledger denominator differs')
    events = {e.event_id:e for e in bundles[-1].event_ledger.events}
    original = {e.event_id:e.event_hash for e in bundles[0].event_ledger.events}
    rows = []
    for r in p['rows']:
        if r['status'] != 'EVALUATED':
            continue
        require(original[r['event_id']] == r['event_hash'], 'later ledger changed original cohort event')
        o, m = r['outcome'], r['outcome']['metrics']
        rows.append([r['thscode'], r['name'], r['event_id'], r['event_hash'], r['first_group_hash'],
            events[r['event_id']].first_recorded_at.isoformat().replace('+00:00', 'Z'),
            *[m[k] for k in expected['columns'][6:15]], o['path'][0]['rank_20d'], o['path'][-1]['rank_20d'], o['outcome_hash']])
    require(rows == expected['rows'], 'compact cohort projection differs')
    coverage = Counter((r['signal_session'], r['horizon_sessions'], r['status']) for r in p['rows'])
    require([list(k) + [v] for k,v in sorted(coverage.items())] == expected['coverage_rows'], 'compact coverage differs')
    page = render_sector_radar_outcomes(result)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'outcomes.json').write_bytes(raw)
    (args.output / 'index.html').write_text(page, encoding='utf-8')
    print('REPLAY_MATCH; full ledger coverage:', p['status_counts'])
    print('Original capture times retained; no investment or method-quality acceptance.')
    return 2 if p['status_counts']['INPUTS_INCOMPLETE'] else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--code-root', type=Path, required=True, help='Trusted checkout src/ or supplied partial code directory')
    parser.add_argument('--output', type=Path, required=True)
    try:
        raise SystemExit(run(parser.parse_args()))
    except (ValueError, KeyError, OSError) as exc:
        print('REPLAY_NOT_COMPLETED: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
