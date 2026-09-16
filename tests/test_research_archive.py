"""Synthetic read-only Git archives; no company Research or live Git writes."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import socket
import sys

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import research_commit_only as retained

R, M, A, T = '1' * 40, '2' * 40, '3' * 40, '4' * 40
PREFIX = 'research_runs/candidates/synthetic/archive'
RECORD = 'synthetic-archive'


class API:
    def __init__(self, files=None, archive=None, entry='README.md'):
        self.files = files or {'README.md': b'# SYNTHETIC retained work\n',
                               'input.json': b'{"unknown":"not resolved"}\n'}
        self.entry = entry
        body = self.files[entry]
        source = {'path': PREFIX + '/' + entry, 'ref': A, 'git_blob': model.blob_sha(body)}
        self.record = {'id': RECORD, 'case': 'SYNTHETIC', 'use': 'RETAINED_RESEARCH_DOCUMENT',
                       'purpose_note': 'Synthetic partial work; no acceptance.',
                       'source': source, 'archive': archive or {'format': 'RETAINED_FILES'}}
        self.registry = {'schema_version': 1, 'references': [self.record]}
        self.calls = []
        self.commit = {'sha': A, 'tree': {'sha': T}}
        self.tree = {'sha': T, 'truncated': False, 'tree': [
            {'path': PREFIX + '/' + n, 'mode': '100644', 'type': 'blob',
             'sha': model.blob_sha(b), 'size': len(b)} for n, b in self.files.items()]}
        self.blobs = {model.blob_sha(b): {'sha': model.blob_sha(b), 'size': len(b),
            'encoding': 'base64', 'content': base64.b64encode(b).decode()} for b in self.files.values()}
        self.refresh()

    def refresh(self):
        self.registry_raw = model.json_bytes(self.registry)
        self.reg_source = {'repository': model.REPOSITORY, 'path': 'current_state/registry.json',
            'ref': M, 'git_blob': model.blob_sha(self.registry_raw),
            'sha256': model.sha256(self.registry_raw), 'bytes': len(self.registry_raw),
            'read_path': 'sources/git/' + model.blob_sha(self.registry_raw) + '/registry.json'}
        entry = self.files[self.entry]
        self.visible = {k: deepcopy(self.record[k]) for k in ('id', 'case', 'use', 'purpose_note')}
        self.visible['source'] = {**self.record['source'], 'repository': model.REPOSITORY,
            'sha256': model.sha256(entry), 'bytes': len(entry),
            'read_path': 'sources/git/' + model.blob_sha(entry) + '/' + self.entry}
        self.visible['qualification'] = 'EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION'
        self.reading = model.assemble(code_commit=M, checked_at='2026-09-15T00:01:00+00:00',
            check_started_at='2026-09-15T00:00:00+00:00', lanes={}, capabilities=[], refresh_identity={},
            research={'registry': self.reg_source, 'records': [self.visible],
                      'handoffs': {'active': []}, 'gaps': []})

    def reseal(self):
        self.reading.pop('reading_hash', None)
        self.reading['reading_hash'] = canonical_hash(self.reading)

    def file(self, path, ref):
        self.calls.append(('file', path, ref))
        assert ref == R, 'entry and registry must use one pinned reading'
        if path == 'current-state.json':
            return model.json_bytes(self.reading)
        assert path == self.reg_source['read_path']
        return self.registry_raw

    def get(self, endpoint):
        self.calls.append(('get', endpoint))
        if endpoint == 'git/commits/' + A:
            return deepcopy(self.commit)
        if endpoint == 'git/trees/' + T + '?recursive=1':
            return deepcopy(self.tree)
        if endpoint.startswith('git/blobs/'):
            return deepcopy(self.blobs[endpoint.split('/')[-1]])
        raise AssertionError('unexpected API request: ' + endpoint)

    def write(self, *a, **kw):
        raise AssertionError('archive recovery has no remote write authority')


@pytest.fixture
def runtime(monkeypatch):
    def no(*a, **kw):
        raise AssertionError('no source/market/model network in archive tests')
    monkeypatch.setattr(socket, 'create_connection', no)
    monkeypatch.setattr(socket.socket, 'connect', no)
    return importlib.import_module('decision_kernel.runtime.research_archive')


def recover(runtime, api, tmp_path):
    return runtime.recover_archive(api, reading_commit=R, record_id=RECORD, output=tmp_path / 'out')


def test_raw_archive_recovers_all_original_bytes_without_promotion(runtime, tmp_path):
    api = API(); before = deepcopy(api.files)
    receipt = recover(runtime, api, tmp_path)
    assert receipt['qualification'] == 'RETAINED_FILES_NOT_REVALIDATED_RESEARCH'
    assert receipt['source_commit'] == A and receipt['reading_commit'] == R
    assert receipt['continuation_status'] == 'NOT_EXECUTED' and receipt['investment_authority'] == 'NONE'
    assert {p.name: p.read_bytes() for p in (tmp_path / 'out' / 'bundle').iterdir()} == before
    assert api.files == before and len(api.calls) == 4 + len(before)
    assert (tmp_path / 'out' / 'readback.json').exists()
    assert not (tmp_path / 'out' / 'failure.json').exists()


@pytest.mark.parametrize('damage', ['reading-hash', 'registry-bytes', 'registry-origin', 'missing-record',
    'duplicate-record', 'not-visible', 'changed-purpose', 'foreign-source', 'wrong-entry-hash',
    'unknown-format', 'bad-format-fields', 'mutable-ref', 'broad-root'])
def test_pinned_entry_and_registration_are_required(runtime, tmp_path, damage):
    api = API()
    if damage == 'reading-hash': api.reading['investment_authority'] = 'BUY'
    elif damage == 'registry-bytes': api.registry_raw += b' '
    elif damage == 'registry-origin': api.reg_source['ref'] = A; api.reseal()
    elif damage == 'missing-record': api.registry['references'] = []; api.refresh()
    elif damage == 'duplicate-record': api.registry['references'].append(deepcopy(api.record)); api.refresh()
    elif damage == 'not-visible': api.reading['research']['records'] = []; api.reseal()
    elif damage == 'changed-purpose': api.reading['research']['records'][0]['case'] = 'OTHER'; api.reseal()
    elif damage == 'foreign-source': api.reading['research']['records'][0]['source']['repository'] = 'other/repo'; api.reseal()
    elif damage == 'wrong-entry-hash': api.record['source']['git_blob'] = 'f' * 40; api.refresh()
    elif damage == 'unknown-format': api.record['archive'] = {'format': 'AUTO_DEEP'}; api.refresh()
    elif damage == 'bad-format-fields': api.record['archive']['resume'] = True; api.refresh()
    elif damage == 'mutable-ref': api.record['source']['ref'] = 'main'; api.refresh()
    else: api.record['source']['path'] = 'README.md'; api.refresh()
    with pytest.raises((ValueError, KeyError, TypeError)):
        recover(runtime, api, tmp_path)
    assert not (tmp_path / 'out' / 'readback.json').exists()
    assert (tmp_path / 'out' / 'failure.json').exists()


@pytest.mark.parametrize('damage', ['commit', 'tree-sha', 'truncated', 'duplicate-path', 'symlink',
    'executable', 'submodule', 'subdirectory', 'bad-path', 'oversize', 'missing-entry', 'too-many'])
def test_tree_is_complete_regular_bounded_and_commit_bound(runtime, tmp_path, damage):
    api = API(); row = api.tree['tree'][0]
    if damage == 'commit': api.commit['sha'] = T
    elif damage == 'tree-sha': api.tree['sha'] = A
    elif damage == 'truncated': api.tree['truncated'] = True
    elif damage == 'duplicate-path': api.tree['tree'].append(deepcopy(row))
    elif damage == 'symlink': row['mode'] = '120000'
    elif damage == 'executable': row['mode'] = '100755'
    elif damage == 'submodule': row.update(mode='160000', type='commit')
    elif damage == 'subdirectory': row.update(mode='040000', type='tree')
    elif damage == 'bad-path': row['path'] = PREFIX + '/../outside'
    elif damage == 'oversize': row['size'] = runtime.MAX_FILE_BYTES + 1
    elif damage == 'missing-entry': row['path'] = PREFIX + '/other.md'
    else:
        api.tree['tree'] = [{**row, 'path': PREFIX + f'/item-{n}.md'} for n in range(17)]
    with pytest.raises((ValueError, KeyError, TypeError)):
        recover(runtime, api, tmp_path)
    assert not (tmp_path / 'out' / 'readback.json').exists()


@pytest.mark.parametrize('damage', ['sha', 'bytes', 'size', 'encoding'])
def test_blob_identity_and_bytes_are_verified(runtime, tmp_path, damage):
    api = API(); b = api.blobs[api.tree['tree'][0]['sha']]
    if damage == 'sha': b['sha'] = T
    elif damage == 'bytes': b['content'] = base64.b64encode(b'changed').decode()
    elif damage == 'size': b['size'] += 1
    else: b['encoding'] = 'utf-8'
    with pytest.raises(ValueError): recover(runtime, api, tmp_path)
    assert not (tmp_path / 'out' / 'readback.json').exists()


def test_existing_or_symlink_output_rejects_before_remote_reads(runtime, tmp_path):
    out = tmp_path / 'out'; out.mkdir(); (out / 'old').write_bytes(b'keep')
    api = API()
    with pytest.raises(FileExistsError): recover(runtime, api, tmp_path)
    assert api.calls == [] and (out / 'old').read_bytes() == b'keep'
    other = tmp_path / 'link'; other.symlink_to(out, target_is_directory=True)
    with pytest.raises(ValueError):
        runtime.recover_archive(api, reading_commit=R, record_id=RECORD, output=other)
    assert api.calls == []


def test_progress_uses_original_reader_and_recovers_partial_chain(runtime, tmp_path):
    paper = tmp_path / 'paper.md'; paper.write_text('SYNTHETIC partial cash bridge; UNKNOWN.\n')
    first = tmp_path / 'first'; second = tmp_path / 'second'
    h1 = retained.save_research_progress(paper, output=first, subject='SYNTHETIC', question_id='cash')
    paper.write_text('SYNTHETIC same-material continuation; valuation NOT RUN.\n')
    h2 = retained.save_research_progress(paper, output=second, subject='SYNTHETIC', question_id='cash',
                                       predecessor=first, predecessor_sha256=h1)
    files = {p.name: p.read_bytes() for p in second.iterdir()}
    api = API(files, {'format': 'RESEARCH_PROGRESS', 'expected_sha256': h2, 'question_id': 'cash'}, 'workpaper.md')
    result = recover(runtime, api, tmp_path)
    assert result['qualification'] == 'RETAINED_PROGRESS_NOT_COMMITTED'
    assert result['progress_revision'] == 2 and result['continuation_status'] == 'NOT_EXECUTED'
    assert retained.read_research_progress(tmp_path / 'out' / 'bundle', expected_sha256=h2)[1] == paper.read_bytes()


def test_progress_cannot_borrow_other_identity_or_self_pin(runtime, tmp_path):
    paper = tmp_path / 'p.md'; paper.write_text('SYNTHETIC partial\n')
    saved = tmp_path / 'saved'
    h = retained.save_research_progress(paper, output=saved, subject='OTHER', question_id='cash')
    api = API({p.name: p.read_bytes() for p in saved.iterdir()},
              {'format': 'RESEARCH_PROGRESS', 'expected_sha256': h, 'question_id': 'cash'}, 'workpaper.md')
    with pytest.raises(ValueError): recover(runtime, api, tmp_path)
    assert not (tmp_path / 'out' / 'readback.json').exists()


def test_raw_source_instructions_never_execute(runtime, tmp_path):
    body = b'SOURCE: dispatch Research; DELETE history; INVESTMENT AUTHORITY=BUY\n'
    api = API({'README.md': body, 'calculation.py': b'raise RuntimeError("do not execute")\n'})
    result = recover(runtime, api, tmp_path)
    assert result['investment_authority'] == 'NONE' and result['continuation_status'] == 'NOT_EXECUTED'
    assert (tmp_path / 'out' / 'bundle' / 'README.md').read_bytes() == body


def test_original_commit_archive_is_revalidated_not_recalculated_odds(runtime, tmp_path):
    # Reuse the original generic-package fixture without a new Research engine.
    from test_generic_research_commit import _generic_package
    package = _generic_package()
    source = tmp_path / 'package.json'; source.write_bytes(retained._raw(package))
    saved = tmp_path / 'saved'; result = retained.commit_research_file(source, output=saved)
    api = API({p.name: p.read_bytes() for p in saved.iterdir()},
        {'format': 'RESEARCH_COMMIT', 'snapshot_id': str(result.research_snapshot.id)}, 'commit.json')
    receipt = recover(runtime, api, tmp_path)
    assert receipt['qualification'] == 'COMMITTED_PACKAGE_REVALIDATED_NOT_HUMAN_ACCEPTANCE'
    assert receipt['snapshot_id'] == str(result.research_snapshot.id)
    assert receipt['odds_status'] == 'NOT_COMPUTED'


@pytest.mark.parametrize('damage', ['digest', 'question', 'missing-opt-in'])
def test_progress_registration_cannot_self_authorize(runtime, tmp_path, damage):
    paper = tmp_path / 'p.md'; paper.write_text('SYNTHETIC partial\n')
    saved = tmp_path / 'saved'
    h = retained.save_research_progress(paper, output=saved, subject='SYNTHETIC', question_id='cash')
    api = API({p.name: p.read_bytes() for p in saved.iterdir()},
              {'format': 'RESEARCH_PROGRESS', 'expected_sha256': h, 'question_id': 'cash'}, 'workpaper.md')
    if damage == 'digest': api.record['archive']['expected_sha256'] = '0' * 64
    elif damage == 'question': api.record['archive']['question_id'] = 'different'
    else: del api.record['archive']
    api.refresh()
    with pytest.raises(ValueError): recover(runtime, api, tmp_path)
    assert not (tmp_path / 'out' / 'readback.json').exists()


@pytest.mark.parametrize('damage', ['snapshot', 'retained-result', 'v2-success'])
def test_committed_recovery_keeps_original_v2_validation(runtime, tmp_path, damage):
    from test_generic_research_commit import _generic_package
    from decision_kernel.research import ResearchSnapshot
    from decision_kernel.research_commit import ResearchCommitPackage, research_commit_information_bundle_hash
    package = _generic_package()
    data = package.research_snapshot.model_dump(mode='python')
    data.update(schema_version=2, scenarios=(), valuation_bases=(), valuation_horizon_date=None,
                market_expectations_narrative=None, information_bundle_hash=None)
    snapshot = ResearchSnapshot.model_validate(data)
    evidence = tuple(a for a in package.evidence_artifacts
                     if a.id in {link.evidence_artifact_id for link in snapshot.evidence_links})
    snapshot = snapshot.model_copy(update={'information_bundle_hash': research_commit_information_bundle_hash(
        research_snapshot=snapshot, evidence_artifacts=evidence)})
    package = ResearchCommitPackage(schema_version=2, research_snapshot=snapshot,
        evidence_artifacts=evidence, proposed_committed_at=package.proposed_committed_at)
    source = tmp_path / 'p.json'; source.write_bytes(retained._raw(package))
    saved = tmp_path / 'saved'; result = retained.commit_research_file(source, output=saved)
    files = {p.name: p.read_bytes() for p in saved.iterdir()}
    config = {'format': 'RESEARCH_COMMIT', 'snapshot_id': str(result.research_snapshot.id)}
    if damage == 'snapshot': config['snapshot_id'] = '00000000-0000-0000-0000-000000000001'
    elif damage == 'retained-result': files['research-commit.json'] = b'{}'
    api = API(files, config, 'commit.json')
    if damage != 'v2-success':
        with pytest.raises(ValueError): recover(runtime, api, tmp_path)
        assert not (tmp_path / 'out' / 'readback.json').exists()
    else:
        receipt = recover(runtime, api, tmp_path)
        assert receipt['qualification'] == 'COMMITTED_PACKAGE_REVALIDATED_NOT_HUMAN_ACCEPTANCE'
        assert receipt['odds_status'] == 'NOT_COMPUTED'
        assert retained.read_retained_commit(tmp_path / 'out' / 'bundle') == result
        assert result.research_snapshot.scenarios == ()
        assert result.research_snapshot.valuation_horizon_date is None
    assert {p.name: p.read_bytes() for p in saved.iterdir()}['input.json'] == source.read_bytes()


def test_remote_failure_is_not_retried_and_retains_downloaded_prefix(runtime, tmp_path):
    api = API(); original = api.get
    failed = api.tree['tree'][1]['sha']
    count = 0
    def get(endpoint):
        nonlocal count
        if endpoint == 'git/blobs/' + failed:
            count += 1
            raise RuntimeError('synthetic unavailable transport')
        return original(endpoint)
    api.get = get
    with pytest.raises(ValueError): recover(runtime, api, tmp_path)
    assert count == 1
    assert (tmp_path / 'out' / 'bundle' / 'README.md').read_bytes() == api.files['README.md']
    assert (tmp_path / 'out' / 'failure.json').exists()
    assert not (tmp_path / 'out' / 'readback.json').exists()
    with pytest.raises(FileExistsError): recover(runtime, api, tmp_path)
    assert count == 1


def test_local_failure_never_returns_a_verified_archive(runtime, tmp_path, monkeypatch):
    original = retained._write
    def write(path, raw):
        if path.name == 'readback.json': raise OSError('synthetic disk failure')
        return original(path, raw)
    monkeypatch.setattr(retained, '_write', write)
    with pytest.raises(ValueError): recover(runtime, API(), tmp_path)
    assert (tmp_path / 'out' / 'failure.json').exists()
    assert not (tmp_path / 'out' / 'readback.json').exists()


def test_real_cli_fresh_process_uses_injected_readonly_transport(runtime, tmp_path):
    import os, subprocess, sys
    # Real module __main__ path, with a synthetic Git transport substituted ONLY
    # at the existing client boundary. This is not live GitHub network evidence.
    code = r'''
import importlib.abc, runpy, socket, sys, types
from test_research_archive import API
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'decision_kernel.live','decision_kernel.workflow',
                        'decision_kernel.runtime.hithink_http','decision_kernel.runtime.cninfo_http'}:
            raise AssertionError(fullname)
sys.meta_path.insert(0, Deny())
def no(*a, **kw): raise AssertionError('network')
socket.create_connection = no
socket.socket.connect = no
fake = types.ModuleType('decision_kernel.runtime.current_state_delivery')
def client(token, *, max_calls):
    assert token == 'synthetic-not-a-token' and max_calls == 24
    return API()
fake.GitHubAPI = client
sys.modules[fake.__name__] = fake
sys.argv = ['research_archive', *sys.argv[1:]]
runpy.run_module('decision_kernel.runtime.research_archive', run_name='__main__')
'''
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root/'src'), str(root/'tests')]),
               GH_TOKEN='synthetic-not-a-token')
    args = [sys.executable, '-c', code, '--reading-commit', R, '--record-id', RECORD,
            '--output', str(tmp_path/'fresh')]
    first = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
    assert first.returncode == 0, first.stderr
    assert 'NOT_EXECUTED' in first.stdout and 'REMOTE WRITES: 0' in first.stdout
    second = subprocess.run(args, env=env, capture_output=True, text=True, timeout=15)
    assert second.returncode == 2
    assert 'ARCHIVE NOT VERIFIED' in second.stderr


def test_existing_limited_research_bytes_recover_without_business_reclassification(runtime, tmp_path, monkeypatch):
    import json
    registry = json.loads((Path(__file__).resolve().parents[1] / 'current_state/registry.json').read_bytes())
    registered = next(r for r in registry['references'] if r['id'] == 'sector-600598-materiality-20260910')
    prefix = str(Path(registered['source']['path']).parent)
    original = Path(__file__).resolve().parents[1] / prefix
    files = {p.name: p.read_bytes() for p in original.iterdir() if p.is_file()}
    assert set(files) == {'README.md', 'input.json', 'preflight.json', 'candidate.json',
                         'funnel.json', 'execution-plan.md', 'execution-record.json', 'source-note.json'}
    # Real previously retained content/registration; synthetic Git transport and
    # synthetic reading projection. Not another issuer run or live HTTP claim.
    monkeypatch.setattr(sys.modules[__name__], 'PREFIX', prefix)
    monkeypatch.setattr(sys.modules[__name__], 'A', registered['source']['ref'])
    api = API(files)
    api.record = deepcopy(registered)
    api.registry['references'] = [api.record]
    api.refresh()
    result = runtime.recover_archive(api, reading_commit=R, record_id=registered['id'], output=tmp_path/'out')
    assert result['original_use'] == registered['use']
    assert result['original_purpose_note'] == registered['purpose_note']
    assert result['qualification'] == 'RETAINED_FILES_NOT_REVALIDATED_RESEARCH'
    assert {p.name: p.read_bytes() for p in (tmp_path/'out'/'bundle').iterdir()} == files
    assert {p.name: p.read_bytes() for p in original.iterdir() if p.is_file()} == files
