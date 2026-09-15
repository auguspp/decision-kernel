"""Synthetic contract tests; real provider bytes are evaluated separately."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import hashlib
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import sector_missed_session as missed
from decision_kernel.runtime import sector_radar_audit as audit
from decision_kernel.runtime.sector_radar_producer import (
    SECTOR_RADAR_WORKFLOW_PATH, SectorRadarProducerContext,
)
from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state
from test_sector_radar_audit import (
    MONDAY, TUESDAY, OBSERVED, TZ, REPOSITORY,
    SyntheticProvider, resolution, hints_json, ms,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("historical reconstruction must not contact a provider")
    monkeypatch.setattr(socket, "create_connection", reject)
    monkeypatch.setattr(socket.socket, "connect", reject)


def capture(tmp_path, *, preopen=False):
    restored = resolution()
    observed = datetime.combine(TUESDAY, time(0, 10), tzinfo=TZ) if preopen else OBSERVED
    context = SectorRadarProducerContext(
        repository=REPOSITORY, workflow_path=SECTOR_RADAR_WORKFLOW_PATH,
        run_id=101, run_attempt=1, commit_sha="a" * 40, observed_at=observed,
    )
    root = tmp_path / 'input-audit'
    clock = iter(observed + timedelta(seconds=i) for i in range(4))
    recorder = audit._Recorder(root, provenance=audit.SYNTHETIC_PROVENANCE,
        credential=None, capture_now=lambda: next(clock))
    audit._save_inputs(recorder, restored, hints_json(), context)
    provider = SyntheticProvider(restored)
    codes = ','.join(s.thscode for s in restored.market_state.series)
    def response(path, params):
        result = provider(path, params)
        if preopen:
            if path == missed.HITHINK_CALENDAR_PATH:
                result['data']['item'].append({'date': TUESDAY.strftime('%Y%m%d')})
            if path == missed.HITHINK_INDEX_SNAPSHOT_PATH:
                result['data']['timestamp'] = int(observed.timestamp() * 1000)
        return result
    request = recorder.request(response)
    request(missed.HITHINK_CALENDAR_PATH, {})
    request(missed.HITHINK_INDEX_CATALOG_PATH, {'tag': 'industry'})
    request(missed.HITHINK_INDEX_SNAPSHOT_PATH, {'thscodes': codes})
    request(missed.HITHINK_INDEX_HISTORY_PATH, {
        'thscode': restored.market_state.benchmark_thscode, 'interval': '1d',
        'start': str(ms(restored.market_state.sessions[-1], 0, 0)),
        'end': str(ms(TUESDAY, 0, 0)),  # Retain the old inclusive end; do not rewrite it.
    })
    # Synthetic historical implementation. This does not simulate a successful
    # original producer; it explicitly seals a rejected pre-enrichment prefix.
    recorder.manifest['implementation'].pop('runtime/stock_radar_reading.py')
    recorder.manifest['implementation']['runtime/sector_radar_audit.py'] = 'f' * 64
    recorder.manifest.update(status='REJECTED', error_type='HithinkIndexAdapterError')
    recorder.flush()
    args = dict(expected_audit_hash=json.loads((root/'manifest.json').read_text())['audit_hash'],
        origin_run_id=101, origin_commit='a'*40, market_session=MONDAY,
        reconstruction_commit='b'*40, reconstructed_at=observed+timedelta(days=1))
    return root, args


def reseal(root, args, *, file=None, edit=None, edit_manifest=None):
    """Only synthetic fixtures: independently change their expected input hash."""
    path = root/'manifest.json'
    m = json.loads(path.read_text())
    if file:
        value = json.loads((root/file).read_text())
        edit(value)
        raw = audit._json_bytes(value)
        (root/file).write_bytes(raw)
        m['files'][file] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if edit_manifest:
        edit_manifest(m)
    m.pop('audit_hash')
    m['audit_hash'] = canonical_hash(m)
    path.write_text(canonical_json(m))
    args['expected_audit_hash'] = m['audit_hash']


def test_partial_reconstruction_is_deterministic_and_preserves_originals(tmp_path):
    root, args = capture(tmp_path)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    first = missed.reconstruct_sector_prefix(root, **args)
    assert first == missed.reconstruct_sector_prefix(root, **args)
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    r = json.loads(first['reconstruction.json'])
    assert r['status'] == missed.STATUS
    assert r['original']['status'] == 'REJECTED'
    assert r['calculation']['stock']['candidate_codes'] is None
    assert r['calculation']['stock']['status'] == 'NOT_RECONSTRUCTED'
    assert not r['natural_acceptance'] and not r['production_restore_authority']
    assert not r['event_ledger_modified'] and r['market_provider_requests'] == 0
    assert r['input_provenance'] == 'SYNTHETIC_TEST_ONLY'
    assert all(r[key] == 'NONE' for key in audit.AUTHORITY)
    assert first['unchanged-event-ledger.json'] == (root/'inputs/candidate-events.json').read_bytes()
    state = parse_sector_radar_market_state(first['reconstructed-market-state.json'].decode())
    assert state.sessions[-1] == MONDAY
    assert state.state_hash == r['calculation']['reconstructed_market_state_hash']
    assert len(r['calculation']['entries']) > 0
    assert 'manifest.json' not in first and 'result.json' not in first
    digest = r.pop('reconstruction_hash')
    assert canonical_hash(r) == digest
    assert canonical_hash(r['calculation']) == r['calculation_hash']
    assert canonical_hash(r['implementation']) == r['calculation']['calculation_implementation_hash']
    for name, desc in r['files'].items():
        assert desc == {'bytes': len(first[name]), 'sha256': hashlib.sha256(first[name]).hexdigest()}


def test_old_implementation_can_be_read_but_not_ordinary_replayed(tmp_path):
    root, args = capture(tmp_path)
    audit.validate_sector_radar_input_audit_integrity(root)
    with pytest.raises(audit.SectorRadarAuditError, match='exact recorded implementation'):
        audit.validate_sector_radar_input_audit(root)
    with pytest.raises(audit.SectorRadarAuditError, match='exact recorded implementation'):
        audit.replay_sector_radar_input_audit(root)
    assert missed.reconstruct_sector_prefix(root, **args)


def test_current_implementation_still_passes_original_validator(tmp_path):
    root, args = capture(tmp_path)
    reseal(root, args, edit_manifest=lambda m: m.update(implementation=audit._implementation()))
    assert audit.validate_sector_radar_input_audit(root)['audit_hash'] == args['expected_audit_hash']


@pytest.mark.parametrize('preopen', [False, True])
def test_reconstruction_does_not_use_todays_execution_clock_for_old_prices(tmp_path, preopen):
    root, args = capture(tmp_path, preopen=preopen)
    first = json.loads(missed.reconstruct_sector_prefix(root, **args)['reconstruction.json'])
    args['reconstructed_at'] += timedelta(days=7)
    later = json.loads(missed.reconstruct_sector_prefix(root, **args)['reconstruction.json'])
    assert first['calculation_hash'] == later['calculation_hash']
    assert first['reconstruction_hash'] != later['reconstruction_hash']
    assert first['calculation']['market_session'] == MONDAY.isoformat()
    expiry = first['calculation']['original_preopen_qualification_expires_at']
    assert bool(expiry) == preopen
    assert first['current_live_market_qualification'] == 'NOT_ESTABLISHED'


@pytest.mark.parametrize(('field', 'value'), [
    ('expected_audit_hash', '0'*64), ('origin_run_id', 102), ('origin_run_id', True),
    ('origin_commit', 'c'*40), ('origin_commit', 'not-a-sha'),
    ('reconstruction_commit', 'main'), ('market_session', TUESDAY),
    ('reconstructed_at', OBSERVED-timedelta(days=1)),
    ('reconstructed_at', datetime(2026,9,8)),
])
def test_identity_and_time_mismatch_rejected(tmp_path, field, value):
    root, args = capture(tmp_path)
    args[field] = value
    with pytest.raises((ValueError, audit.SectorRadarAuditError)):
        missed.reconstruct_sector_prefix(root, **args)


def test_original_bytes_tampering_is_rejected(tmp_path):
    root, args = capture(tmp_path)
    (root/'responses/0002.json').write_bytes(b'{}')
    with pytest.raises(audit.SectorRadarAuditError, match='byte size mismatch'):
        missed.reconstruct_sector_prefix(root, **args)


def test_rehashed_new_snapshot_does_not_match_independent_origin_binding(tmp_path):
    root, args = capture(tmp_path)
    old_hash = args['expected_audit_hash']
    reseal(root, args, file='responses/0002.json', edit=lambda x: x['data'].update(timestamp=ms(TUESDAY)))
    args['expected_audit_hash'] = old_hash
    with pytest.raises(ValueError, match='independently bound audit'):
        missed.reconstruct_sector_prefix(root, **args)


@pytest.mark.parametrize('case', ['malformed', 'future_ready', 'reverse_clock', 'request', 'code_map', 'future_bar', 'window', 'intraday'])
def test_resealed_synthetic_invalid_contracts_still_fail_closed(tmp_path, case):
    root, args = capture(tmp_path, preopen=case=='intraday')
    if case == 'malformed':
        reseal(root, args, file='responses/0002.json', edit=lambda x: x.update(data=[]))
    elif case == 'future_ready':
        reseal(root, args, file='responses/0002.json', edit=lambda x: x['data'].update(timestamp=ms(TUESDAY)))
    elif case == 'reverse_clock':
        reseal(root, args, edit_manifest=lambda m: m['requests'][2].update(captured_at=(OBSERVED-timedelta(seconds=1)).isoformat()))
    elif case == 'request':
        reseal(root, args, edit_manifest=lambda m: m['requests'][1]['params'].update(tag='cn_concept'))
    elif case == 'code_map':
        reseal(root, args, edit_manifest=lambda m: m['implementation'].update(extra='c'*64))
    elif case == 'future_bar':
        reseal(root, args, file='responses/0003.json', edit=lambda x: x['data']['item'][-1].update(date_ms=ms(TUESDAY,0,0)))
    elif case == 'window':
        reseal(root, args, edit_manifest=lambda m: m['requests'][3]['params'].update(end='1'))
    else:
        # Later trading-day snapshot cannot be carried through opening auction.
        observed = datetime.combine(TUESDAY,time(10),tzinfo=TZ)
        reseal(root, args, file='responses/0002.json', edit=lambda x: x['data'].update(timestamp=int(observed.timestamp()*1000)))
        reseal(root, args, edit_manifest=lambda m: [r.update(captured_at=(observed+timedelta(seconds=i)).isoformat()) for i,r in enumerate(m['requests'])])
    with pytest.raises((ValueError, audit.SectorRadarAuditError)):
        missed.reconstruct_sector_prefix(root, **args)


def test_no_expansion_into_more_requests_or_provider_error(tmp_path):
    root, args = capture(tmp_path)
    reseal(root, args, edit_manifest=lambda m: m['requests'].pop())
    with pytest.raises(audit.SectorRadarAuditError):
        missed.reconstruct_sector_prefix(root, **args)


def test_cli_is_create_only_and_never_overwrites_input(tmp_path):
    root, args = capture(tmp_path)
    # Fixed synthetic past capture; the CLI records its real execution clock.
    argv = ['--audit-root', str(root), '--expected-audit-hash', args['expected_audit_hash'],
            '--origin-run-id', '101', '--origin-commit', 'a'*40,
            '--reconstruction-commit', 'b'*40, '--market-session', MONDAY.isoformat(),
            '--output', str(tmp_path/'new-reading')]
    assert missed.main(argv) == 0
    report = (tmp_path/'new-reading/reconstruction.json').read_bytes()
    assert missed.main(argv) == 2
    assert (tmp_path/'new-reading/reconstruction.json').read_bytes() == report
    argv[-1] = str(root)
    assert missed.main(argv) == 2
