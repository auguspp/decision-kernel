"""Synthetic saved results and coupled Git recovery, never company acceptance."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import socket
import subprocess
import sys
from uuid import uuid4

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.market import ObservedMarket
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.provisional_odds import HumanPriceContext, build_provisional_odds, recompute_canonical_odds
from decision_kernel.runtime import odds_retention as odds, research_archive as archive
from decision_kernel.runtime import research_commit_only as retained, current_state as model
from test_generic_research_commit import AS_OF, _generic_package
from test_research_only_commit_v2 import v2_package
from test_research_archive import API, R, A, PREFIX, RECORD


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('retention cannot request market/model/source network')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


def make_result(tmp_path, kind='PROVISIONAL', *, research_only=False):
    package = v2_package() if research_only else _generic_package()
    p = tmp_path / 'research-input.json'; p.write_bytes(retained._raw(package))
    directory = tmp_path / 'research'
    research = retained.commit_research_file(p, output=directory)
    s = research.research_snapshot
    convention = 'RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE'
    context = HumanPriceContext(ticker=s.ticker, exchange=s.exchange, currency=s.currency,
        price='10', price_timestamp=AS_OF + timedelta(hours=2), utc_offset_minutes=480,
        supplied_at=AS_OF + timedelta(hours=3), price_convention=convention,
        source_reference='SYNTHETIC Human context, not an actual company request')
    result = build_provisional_odds(research_snapshot=s, price_context=context,
        artifact_id=uuid4(), created_at=AS_OF + timedelta(hours=4))
    if kind == 'SAME_RESEARCH_COMPARISON':
        market = ObservedMarket(market_price='8', market_timestamp=AS_OF + timedelta(hours=3),
            market_utc_offset_minutes=480, currency=s.currency, price_convention=convention,
            market_data_source='SYNTHETIC separately supplied observation, no live qualification')
        result = recompute_canonical_odds(provisional=result, research_snapshot=s, observed_market=market,
            market_ticker=s.ticker, market_exchange=s.exchange, artifact_id=uuid4(),
            created_at=AS_OF + timedelta(hours=5), policy=load_live_odds_v0_1())
    raw = (result.model_dump_json(indent=2) + '\n\n').encode()
    source = tmp_path / 'original-odds.json'; source.write_bytes(raw)
    return directory, canonical_hash(s), result, source


def save(source, directory, digest, output, kind='PROVISIONAL'):
    return odds.retain_odds_file(source, result_kind=kind, research_directory=directory,
                                 expected_research_hash=digest, output=output)


def read(output, directory, digest):
    return odds.read_retained_odds(output, research_directory=directory, expected_research_hash=digest)


@pytest.mark.parametrize('kind,research_only', [('PROVISIONAL', False), ('PROVISIONAL', True),
                                               ('SAME_RESEARCH_COMPARISON', False)])
def test_exact_bytes_clocks_and_research_remain_after_retention_and_readback(tmp_path, kind, research_only):
    directory, digest, result, source = make_result(tmp_path, kind, research_only=research_only)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    output = tmp_path / 'saved'
    assert save(source, directory, digest, output, kind) == result
    assert (output / 'result.json').read_bytes() == source.read_bytes()
    saved = {p.name: p.read_bytes() for p in output.iterdir()}
    assert set(saved) == odds.FILES and read(output, directory, digest) == result
    assert {p.name: p.read_bytes() for p in output.iterdir()} == saved
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    metadata = retained._json(saved['retention.json'])
    assert metadata['research_snapshot_hash'] == digest
    assert metadata['market_qualification'] == 'NOT_ESTABLISHED_BY_RETENTION'
    assert metadata['human_acceptance'] == 'NOT_ESTABLISHED_BY_RETENTION'
    assert metadata['investment_authority'] == 'NONE'
    if research_only:
        assert result.artifact.calculation_status == 'NO_CALCULATION'
        assert result.artifact.world_results == ()
        assert result.artifact.ordinal_status == 'ORDINAL_NOT_ESTABLISHED'


@pytest.mark.parametrize('damage', ['wrong-pin', 'changed-research', 'duplicate-key', 'wrong-kind',
                                     'probability-edit', 'payoff-edit'])
def test_rejected_result_keeps_original_bytes_without_success_receipt(tmp_path, damage):
    kind = 'SAME_RESEARCH_COMPARISON' if damage == 'probability-edit' else 'PROVISIONAL'
    directory, digest, result, source = make_result(tmp_path, kind)
    if damage == 'wrong-pin': digest = 'f' * 64
    elif damage == 'changed-research':
        raw = (directory / 'input.json').read_bytes().replace(b'Sample Co', b'Other Co')
        (directory / 'input.json').write_bytes(raw)
    elif damage == 'duplicate-key': source.write_bytes(b'{"secret":"do-not-echo","secret":"value"}')
    elif damage == 'wrong-kind': kind = 'SAME_RESEARCH_COMPARISON'
    else:
        data = json.loads(source.read_bytes())
        target = data['canonical'] if damage == 'probability-edit' else data
        artifact = target['artifact']
        if damage == 'probability-edit': artifact['calculation']['scenario_results'][0]['probability'] = '0.123'
        else: artifact['world_results'][0]['total_payoff_per_share'] = '999'
        target['artifact_hash'] = canonical_hash(artifact)
        source.write_bytes(retained._raw(data))
    raw = source.read_bytes()
    output = tmp_path / 'rejected'
    with pytest.raises(ValueError, match='preserve files'):
        save(source, directory, digest, output, kind)
    assert (output / 'result.json').read_bytes() == raw
    assert not (output / 'retention.json').exists()
    assert (output / 'rejection.json').exists()
    assert b'do-not-echo' not in (output / 'rejection.json').read_bytes()
    with pytest.raises(ValueError): read(output, directory, digest)
    with pytest.raises(FileExistsError): save(source, directory, digest, output, kind)


@pytest.mark.parametrize('damage', ['append-space', 'extra-file', 'missing-result', 'receipt-authority',
    'receipt-hash', 'snapshot-hash', 'package-hash', 'naive-clock', 'future-clock', 'early-clock',
    'duplicate-receipt', 'wrong-byte-type', 'unknown-field', 'rehashed-payoff'])
def test_saved_bundle_is_not_accepted_by_checksum_alone(tmp_path, damage):
    directory, digest, result, source = make_result(tmp_path)
    output = tmp_path / 'saved'; save(source, directory, digest, output)
    p = output / 'retention.json'; metadata = retained._json(p.read_bytes())
    if damage == 'append-space': (output / 'result.json').write_bytes(source.read_bytes() + b' ')
    elif damage == 'extra-file': (output / 'unexpected.py').write_bytes(b'raise RuntimeError()')
    elif damage == 'missing-result': (output / 'result.json').unlink()
    elif damage == 'receipt-authority': metadata['investment_authority'] = 'BUY'
    elif damage == 'receipt-hash': metadata['result_hash'] = 'f' * 64
    elif damage == 'snapshot-hash': metadata['research_snapshot_hash'] = 'f' * 64
    elif damage == 'package-hash': metadata['research_package_hash'] = 'f' * 64
    elif damage == 'naive-clock': metadata['retained_at'] = '2026-09-01T12:00:00'
    elif damage == 'future-clock': metadata['retained_at'] = '9999-01-01T00:00:00+00:00'
    elif damage == 'early-clock': metadata['retained_at'] = AS_OF.isoformat()
    elif damage == 'wrong-byte-type': metadata['result']['bytes'] = True
    elif damage == 'unknown-field': metadata['automatic_action'] = True
    elif damage == 'rehashed-payoff':
        data = json.loads((output / 'result.json').read_bytes())
        data['artifact']['world_results'][0]['total_payoff_per_share'] = '999'
        data['artifact_hash'] = canonical_hash(data['artifact'])
        raw = retained._raw(data); (output / 'result.json').write_bytes(raw)
        metadata['result'] = retained._description(raw); metadata['result_hash'] = canonical_hash(data)
    if damage == 'duplicate-receipt':
        p.write_bytes(b'{"format":"odds-result-retention-v0","format":"x"}')
    else: p.write_bytes(retained._raw(metadata))
    with pytest.raises((ValueError, OSError)): read(output, directory, digest)


@pytest.mark.parametrize('damage', ['existing', 'symlink-input', 'symlink-output', 'oversize'])
def test_exclusive_bounded_io_is_reused(tmp_path, damage):
    directory, digest, _, source = make_result(tmp_path)
    output = tmp_path / 'saved'
    if damage == 'existing': output.mkdir(); (output / 'old').write_bytes(b'keep')
    elif damage == 'symlink-input':
        link = tmp_path / 'link.json'; link.symlink_to(source); source = link
    elif damage == 'symlink-output': output.symlink_to(directory, target_is_directory=True)
    else: source.write_bytes(b'x' * (retained.MAX_BYTES + 1))
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises((ValueError, FileExistsError)): save(source, directory, digest, output)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    if damage == 'existing': assert (output / 'old').read_bytes() == b'keep'


def test_actual_write_failure_keeps_partial_directory_and_is_not_retried(tmp_path, monkeypatch):
    directory, digest, _, source = make_result(tmp_path)
    original = retained._write; calls = []
    def write(path, data):
        calls.append(path.name)
        if path.name == 'retention.json': raise OSError('disk full; private detail')
        return original(path, data)
    monkeypatch.setattr(retained, '_write', write)
    with pytest.raises(ValueError): save(source, directory, digest, tmp_path / 'saved')
    assert calls.count('retention.json') == 1
    assert (tmp_path / 'saved' / 'result.json').read_bytes() == source.read_bytes()
    assert b'private detail' not in (tmp_path / 'saved' / 'rejection.json').read_bytes()


class CoupledAPI(API):
    """Reuse the existing pinned-reading fixture, adding one exact dependency."""
    def __init__(self, files, research_files, digest, snapshot_id, kind='PROVISIONAL'):
        super().__init__(files, {'format': 'ODDS_RESULT', 'result_kind': kind,
            'research_record_id': 'synthetic-research', 'research_snapshot_hash': digest}, 'retention.json')
        self.research_files = research_files
        self.dependency = {'id': 'synthetic-research', 'case': 'SYNTHETIC',
            'use': 'SYNTHETIC_RESEARCH_ARCHIVE', 'purpose_note': 'Synthetic no investment authority',
            'source': {'path': 'docs/readings/synthetic-research/commit.json', 'ref': A,
                       'git_blob': model.blob_sha(research_files['commit.json'])},
            'archive': {'format': 'RESEARCH_COMMIT', 'snapshot_id': snapshot_id}}
        self.registry['references'].append(self.dependency)
        self.tree['tree'].extend({'path': 'docs/readings/synthetic-research/' + name,
            'mode': '100644', 'type': 'blob', 'sha': model.blob_sha(raw), 'size': len(raw)}
            for name, raw in research_files.items())
        self.blobs.update({model.blob_sha(b): {'sha': model.blob_sha(b), 'size': len(b),
            'encoding': 'base64', 'content': base64.b64encode(b).decode()} for b in research_files.values()})
        self.refresh()

    def refresh(self):
        super().refresh()
        if not hasattr(self, 'dependency'): return
        d = self.dependency; raw = self.research_files['commit.json']
        visible = {k: deepcopy(d[k]) for k in ('id', 'case', 'use', 'purpose_note')}
        visible['source'] = {**d['source'], 'repository': model.REPOSITORY,
            'bytes': len(raw), 'sha256': model.sha256(raw),
            'read_path': 'sources/git/' + model.blob_sha(raw) + '/commit.json'}
        visible['qualification'] = 'EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION'
        self.reading['research']['records'].append(visible)
        self.reseal()


def coupled(tmp_path, kind='PROVISIONAL', research_only=False):
    directory, digest, result, source = make_result(tmp_path, kind, research_only=research_only)
    saved = tmp_path / 'saved'; save(source, directory, digest, saved, kind)
    research = retained.read_retained_commit(directory)
    api = CoupledAPI({p.name: p.read_bytes() for p in saved.iterdir()},
        {p.name: p.read_bytes() for p in directory.iterdir()}, digest,
        str(research.research_snapshot.id), kind)
    return api, digest, result


@pytest.mark.parametrize('kind,only', [('PROVISIONAL', False), ('SAME_RESEARCH_COMPARISON', False),
                                     ('PROVISIONAL', True)])
def test_same_pinned_reading_recovers_both_archives_and_rebuilds_original_result(tmp_path, kind, only):
    api, digest, result = coupled(tmp_path, kind, only)
    output = tmp_path / 'recovered'
    receipt = archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=output)
    assert receipt['qualification'] == 'ODDS_RESULT_REVALIDATED_NOT_CURRENT_QUALIFICATION'
    assert receipt['result_kind'] == kind and receipt['result_hash'] == canonical_hash(result)
    assert receipt['research_record_id'] == 'synthetic-research'
    assert receipt['research_snapshot_hash'] == digest and receipt['remote_write'] is False
    assert receipt['odds_status'] == 'SAVED_RESULT_REBUILT_FOR_VERIFICATION_NOT_NEW_PRICE_ANALYSIS'
    assert receipt['market_qualification'] == 'NOT_ESTABLISHED_BY_RECOVERY'
    assert read(output / 'bundle', output / 'research' / 'bundle', digest) == result
    for name, raw in api.files.items(): assert (output / 'bundle' / name).read_bytes() == raw
    for name, raw in api.research_files.items(): assert (output / 'research' / 'bundle' / name).read_bytes() == raw
    assert len(api.calls) <= archive.MAX_API_CALLS
    assert all(call[2] == R for call in api.calls if call[0] == 'file')


@pytest.mark.parametrize('damage', ['missing-dependency', 'duplicate-dependency', 'invisible-dependency',
    'self-reference', 'cycle', 'non-commit', 'different-case', 'different-snapshot',
    'wrong-hash', 'wrong-kind', 'extra-config', 'unknown-kind', 'mutable-source', 'extra-result-file',
    'extra-research-files'])
def test_archive_dependency_is_explicit_typed_and_bounded(tmp_path, damage):
    api, digest, result = coupled(tmp_path)
    cfg = api.record['archive']
    if damage == 'missing-dependency': api.registry['references'] = [api.record]
    elif damage == 'duplicate-dependency': api.registry['references'].append(deepcopy(api.dependency))
    elif damage == 'self-reference': cfg['research_record_id'] = RECORD
    elif damage == 'cycle': api.dependency['archive'] = {**cfg, 'research_record_id': RECORD}
    elif damage == 'non-commit': api.dependency['archive'] = {'format': 'RETAINED_FILES'}
    elif damage == 'different-case': api.dependency['case'] = 'OTHER'
    elif damage == 'different-snapshot': api.dependency['archive']['snapshot_id'] = str(uuid4())
    elif damage == 'wrong-hash': cfg['research_snapshot_hash'] = 'f' * 64
    elif damage == 'wrong-kind': cfg['result_kind'] = 'SAME_RESEARCH_COMPARISON'
    elif damage == 'extra-config': cfg['resume'] = True
    elif damage == 'unknown-kind': cfg['result_kind'] = 'LIVE_ODDS'
    elif damage == 'mutable-source': api.dependency['source']['ref'] = 'main'
    elif damage == 'extra-result-file':
        api.tree['tree'].append({**api.tree['tree'][0], 'path': PREFIX + '/extra.json'})
    elif damage == 'extra-research-files':
        api.tree['tree'].extend({**api.tree['tree'][0], 'path': 'docs/readings/synthetic-research/e%d.json' % n}
                               for n in range(2))
    api.refresh()
    if damage == 'invisible-dependency':
        api.reading['research']['records'] = [api.visible]; api.reseal()
    output = tmp_path / 'recovered'
    with pytest.raises(ValueError):
        archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=output)
    assert not (output / 'readback.json').exists() and (output / 'failure.json').exists()
    assert len(api.calls) <= archive.MAX_API_CALLS
    if damage in {'cycle', 'non-commit'}:
        assert sum(call == ('get', 'git/commits/' + A) for call in api.calls) == 1


def test_dependency_failure_preserves_result_prefix_without_retry(tmp_path):
    api, _, _ = coupled(tmp_path)
    broken = model.blob_sha(api.research_files['input.json'])
    api.blobs[broken]['content'] = base64.b64encode(b'tampered').decode()
    output = tmp_path / 'recovered'
    with pytest.raises(ValueError): archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=output)
    assert (output / 'bundle' / 'result.json').read_bytes() == api.files['result.json']
    assert (output / 'research' / 'failure.json').exists()
    assert sum(call == ('get', 'git/blobs/' + broken) for call in api.calls) == 1
    assert not (output / 'readback.json').exists()


@pytest.mark.parametrize('command', ['retain', 'verify'])
def test_actual_fresh_process_cli_is_offline_and_does_not_import_provider(tmp_path, command):
    directory, digest, result, source = make_result(tmp_path)
    output = tmp_path / 'saved'
    if command == 'verify': save(source, directory, digest, output)
    script = '''
import sys, socket, builtins
sys.path.insert(0, sys.argv[1])
def denied(*a, **k): raise AssertionError("no network")
socket.create_connection = denied
socket.socket.connect = denied
original = builtins.__import__
def guarded(name, *a, **k):
    if name.split('.')[0] in {'openai', 'requests'} or name.startswith((
        'decision_kernel.live', 'decision_kernel.runtime.hithink_http')):
        raise AssertionError('unexpected provider/model import')
    return original(name, *a, **k)
builtins.__import__ = guarded
from decision_kernel.runtime.odds_retention import main
raise SystemExit(main(sys.argv[2:]))
'''
    args = [sys.executable, '-I', '-c', script, str(Path(__file__).resolve().parents[1] / 'src'), command,
            '--research-directory', str(directory), '--expected-research-hash', digest, '--output', str(output)]
    if command == 'retain': args.extend(['--input', str(source), '--kind', 'PROVISIONAL'])
    proc = subprocess.run(args, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0, proc.stderr
    assert 'INVESTMENT AUTHORITY: NONE' in proc.stdout
    assert read(output, directory, digest) == result


def test_dependency_cannot_return_a_different_reading_under_the_same_ref(tmp_path):
    api, _, _ = coupled(tmp_path)
    original = api.file; count = 0
    def file(path, ref):
        nonlocal count
        raw = original(path, ref)
        if path == 'current-state.json':
            count += 1
            if count == 2:
                data = retained._json(raw)
                data['research']['gaps'].append('SYNTHETIC different reading body')
                data.pop('reading_hash'); data['reading_hash'] = canonical_hash(data)
                return model.json_bytes(data)
        return raw
    api.file = file
    output = tmp_path / 'recovered'
    with pytest.raises(ValueError): archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=output)
    assert not (output / 'readback.json').exists()
    assert (output / 'failure.json').exists()


@pytest.mark.parametrize('digest', [None, True, '', 'main', 'f'*63, 'G'*64])
def test_external_snapshot_pin_must_be_explicit_hash_before_retention(tmp_path, digest):
    directory, _, _, source = make_result(tmp_path)
    output = tmp_path / 'saved'
    with pytest.raises(ValueError): save(source, directory, digest, output)
    assert not output.exists()


def test_cli_failure_never_echoes_untrusted_input_or_returns_quiet_success(tmp_path, capsys):
    directory, digest, _, source = make_result(tmp_path)
    source.write_bytes(b'{"unsafe":"do-not-echo-private-source"}')
    result = odds.main(['retain', '--input', str(source), '--kind', 'PROVISIONAL',
        '--research-directory', str(directory), '--expected-research-hash', digest,
        '--output', str(tmp_path / 'saved')])
    captured = capsys.readouterr()
    assert result == 2 and not captured.out
    assert 'do-not-echo' not in captured.err and 'NOT VERIFIED' in captured.err
