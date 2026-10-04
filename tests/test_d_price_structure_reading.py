"""Synthetic Collector seam: real archive/hash/native/reading logic, no Git I/O.

Shared publication quota enforcement already has its own tests. Only that
external reservation boundary is stubbed here; detail/root size checks are real.
"""
from copy import deepcopy
from io import BytesIO
import json
from types import SimpleNamespace
import zipfile

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import d_price_structure as d
from decision_kernel.runtime import d_price_structure_reading as r
from test_d_price_structure import archive_fixture, AT, offline

LIMIT = 128 * 1024 * 1024
M, R = 'a' * 40, 'b' * 40


def seeded(monkeypatch, source=None):
    files, _ = archive_fixture() if source is None else source
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in files.items(): z.writestr(name, raw)
    raw = stream.getvalue(); path = 'sources/artifacts/' + model.sha256(raw) + '.zip'
    ref = {'artifact_id': 123, 'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw),
           'git_blob': model.blob_sha(raw), 'expires_at': '2099-01-01T00:00:00Z',
           'origin_run': {'id': 456, 'head_sha': M}}
    api = SimpleNamespace(calls=0, max_calls=10000)
    def forbidden(*args): raise AssertionError('unexpected external Git I/O')
    api.file = forbidden
    collector = SimpleNamespace(code_commit=M, previous=None, previous_commit=None, api=api,
                                archive_cache={123: (files, ref)})
    baseline = model.assemble(code_commit=M, checked_at=AT, check_started_at=AT,
        lanes={'sector': {'last_qualified_result': {'archive': ref}, 'latest_attempt': {}, 'gaps': []}},
        research={'handoffs': {'active': []}, 'records': [{'id': 'old-research'}]}, capabilities=[], refresh_identity={})
    collector.files = {path: raw, 'current-state.json': model.read_package_bytes(baseline),
                       'README.md': b'original reading\n', 'details/prices.json': b'original price input'}
    def retain(path, raw):
        if path in collector.files: assert collector.files[path] == raw
        collector.files[path] = raw
        return {'read_path': path, 'bytes': len(raw), 'sha256': model.sha256(raw), 'git_blob': model.blob_sha(raw),
                'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
    collector.retain = retain
    monkeypatch.setattr(r, '_reserve', lambda *a, **k: None)
    return collector, baseline


def test_real_native_worker_reaches_root_and_readme(monkeypatch):
    collector, baseline = seeded(monkeypatch)
    before = deepcopy(baseline)
    payload = r.attach(collector, baseline, retained_limit=LIMIT)
    assert baseline == before
    model.validate_read_package(payload)
    descriptor = payload['research'][r.KEY]
    report_raw = collector.files[descriptor['read_path']]; r._bound(report_raw, descriptor)
    report = json.loads(report_raw)
    assert report['reading_status'] == 'SAVED_SOURCE_COMPUTED'
    assert report['observed_delta']['status'] == 'FIRST_RECORDED_READING'
    assert report['subject'] == '000300.SH' and report['bar_count'] == 20
    assert report['market_session'] == '2026-01-30'
    assert report['report_hash'] == canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
    assert payload['research']['records'] == baseline['research']['records']
    assert collector.files['details/prices.json'] == b'original price input'
    assert r.PATH.encode() in collector.files['README.md']
    r._bound(collector.files[r.INPUT_PATH], report['normalized_input_file'])


def test_same_source_reuses_saved_result_without_native_reinstallation(monkeypatch):
    first, baseline = seeded(monkeypatch)
    prior = r.attach(first, baseline, retained_limit=LIMIT)
    prior_bytes = first.files[r.PATH]
    second, current = seeded(monkeypatch)
    second.previous = prior; second.previous_commit = R
    second.api.file = lambda path, ref: prior_bytes if (path, ref) == (r.PATH, R) else None
    def forbidden(*a, **k): raise AssertionError('unchanged source must not run native again')
    monkeypatch.setattr(r, 'run_native', forbidden)
    output = r.attach(second, current, retained_limit=LIMIT)
    saved = json.loads(second.files[r.PATH]); old = json.loads(prior_bytes)
    assert saved['reading_status'] == 'SAME_INPUT_REUSED'
    assert saved['observed_delta']['status'] == 'UNCHANGED_INPUT_NOT_NEW_MARKET_EVENT'
    assert saved['computed_at'] == old['computed_at'] and saved['observed_strokes'] == old['observed_strokes']
    assert first.files[r.PATH] == prior_bytes
    assert output['research']['records'] == prior['research']['records']


@pytest.mark.parametrize('failure', ['native', 'archive', 'quota', 'capacity'])
def test_optional_failure_cannot_delete_prices_or_research(monkeypatch, failure):
    collector, baseline = seeded(monkeypatch); old = dict(collector.files)
    if failure == 'native':
        def failed(*a): raise RuntimeError('synthetic native process failure')
        monkeypatch.setattr(r, 'run_native', failed)
    elif failure == 'archive': collector.archive_cache.clear()
    elif failure == 'quota':
        def failed(*a, **k): raise ValueError('synthetic publication reserve failure')
        monkeypatch.setattr(r, '_reserve', failed)
    limit = sum(map(len, collector.files.values())) + 1024 if failure == 'capacity' else LIMIT
    output = r.attach(collector, baseline, retained_limit=limit)
    for path, raw in old.items():
        if path not in ('README.md', 'current-state.json'): assert collector.files[path] == raw
    assert r.PATH not in collector.files and r.INPUT_PATH not in collector.files
    assert output['research']['records'] == baseline['research']['records']
    assert output['research'].get(r.KEY, {}).get('status') == 'STRUCTURE_UNAVAILABLE_OTHER_INPUTS_PRESERVED'
    model.validate_read_package(output)


def test_worker_receives_no_credentials_or_original_environment(monkeypatch):
    source = __import__('test_d_price_structure').synthetic(3)
    monkeypatch.setenv('GH_TOKEN', 'SYNTHETIC_NOT_A_TOKEN')
    def inspect_command(cmd, **kw):
        assert 'GH_TOKEN' not in kw['env'] and 'TUSHARE_PROXY_API_KEY' not in kw['env']
        assert kw['timeout'] == 45 and kw['capture_output'] is True
        assert cmd[1:3] == ['-m', 'decision_kernel.runtime.d_price_structure']
        return SimpleNamespace(returncode=9)
    monkeypatch.setattr(r.subprocess, 'run', inspect_command)
    with pytest.raises(ValueError): r.run_native(source)


def test_delivery_configuration_keeps_existing_cadence_and_real_native_tests():
    import ast
    from pathlib import Path
    import tomllib
    import yaml
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / 'pyproject.toml').read_text())
    extras = project['project']['optional-dependencies']
    assert 'czsc==1.0.1' in extras['price-structure'] and 'czsc==1.0.1' in extras['dev']
    assert not any('czsc' in d for d in project['project']['dependencies'])
    wf = yaml.safe_load((root / '.github/workflows/current-state-read-entry.yml').read_text())
    steps = [step for job in wf['jobs'].values() for step in job.get('steps', [])]
    install = next(s for s in steps if s.get('name') == 'Install optional saved-price structure engine')
    assert '--only-binary=:all:' in install['run'] and 'GITHUB_STEP_SUMMARY' in install['run']
    assert any(s.get('env', {}).get('INCLUDE_PRICE_STRUCTURE') == '1' for s in steps)
    module = ast.parse((root / 'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text())
    # This is a wiring check, not an invocation of the entire production collector.
    imports = [n.module for n in ast.walk(module) if isinstance(n, ast.ImportFrom)]
    assert 'd_price_structure_reading' in imports
    registry = json.loads((root / 'current_state/registry.json').read_text())
    entry = next(r for r in registry['references'] if r['id'] == 'd331-czsc-retained-20261004')
    assert entry['use'] == 'NAVIGATION_ONLY' and entry['read_policy'] == 'ON_DEMAND_ARCHIVE'
    assert 'source' not in entry and entry['archive']['format'] == 'RETAINED_FILES'
    assert entry['archive_source']['ref'] == '019aa648eb7fcc9cefcfe2e41853bae28848c594'


def test_even_failure_note_must_not_overflow_original_root(monkeypatch):
    collector, baseline = seeded(monkeypatch); before = dict(collector.files)
    def unavailable(*a): raise RuntimeError('synthetic engine unavailable')
    def root_full(*a): raise ValueError('synthetic root capacity')
    monkeypatch.setattr(r, 'run_native', unavailable)
    monkeypatch.setattr(model, 'read_package_bytes', root_full)
    assert r.attach(collector, baseline, retained_limit=LIMIT) is baseline
    assert collector.files == before
