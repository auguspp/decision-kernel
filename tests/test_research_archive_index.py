"""Synthetic on-demand references reuse the original archive reader, not Research."""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import current_state_delivery_with_odds_watch as production
from decision_kernel.runtime import research_archive as archive
from decision_kernel.runtime import research_archive_index as index
from decision_kernel.runtime import research_commit_only as retained
from decision_kernel.runtime import radar_company_reading as companies
from test_research_archive import API, R, M, A, RECORD


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*a, **k): raise AssertionError('no network in synthetic archive tests')
    monkeypatch.setattr(socket.socket, 'connect', reject)
    monkeypatch.setattr(socket, 'create_connection', reject)


def reindex(api):
    api.registry_raw = model.json_bytes(api.registry)
    api.reg_source.update(git_blob=model.blob_sha(api.registry_raw), sha256=model.sha256(api.registry_raw),
                          bytes=len(api.registry_raw), read_path='sources/git/' + model.blob_sha(api.registry_raw) + '/registry.json')
    api.reading['research']['registry'] = api.reg_source
    api.reading['research']['records'] = []
    api.reading['research']['on_demand_archives'] = [index.project(api.record)]
    api.reseal()
    return api


def deferred(api=None):
    api = api or API()
    body = api.files[api.entry]
    api.record['read_policy'] = index.POLICY
    api.record['archive_source'] = api.record.pop('source')
    api.record['archive_source'].update(bytes=len(body), sha256=model.sha256(body))
    return reindex(api)


def test_declaration_is_not_a_read_copy_or_authority():
    api = deferred(); before = deepcopy(api.record)
    entry = index.project(api.record)
    assert api.record == before and not api.calls
    assert entry['qualification'] == 'REGISTERED_ARCHIVE_NOT_MATERIALIZED'
    assert entry['body_materialized_in_reading'] is False
    assert 'read_path' not in entry['source'] and 'read_ref_rule' not in entry['source']
    assert entry['source']['ref'] == A
    assert not {'human_attention_authority', 'research_authority', 'investment_authority'} & entry.keys()
    index.validate(entry)


@pytest.mark.parametrize('damage', ['policy', 'use', 'missing-ref', 'mutable-ref', 'blob', 'sha256',
    'bytes-bool', 'bytes-negative', 'bytes-limit', 'bytes-str', 'source-selector', 'body-path',
    'root', 'traversal', 'entry-name', 'format', 'extra-format', 'id', 'case', 'purpose'])
def test_invalid_declaration_never_falls_back_to_eager_fetch(damage):
    api = deferred(); row = api.record
    if damage == 'policy': row['read_policy'] = 'AUTOMATIC'
    elif damage == 'use': row['use'] = 'CONFIRMED_ACTION_CHECKPOINT'
    elif damage == 'missing-ref': row['archive_source'].pop('ref')
    elif damage == 'mutable-ref': row['archive_source']['ref'] = 'main'
    elif damage == 'blob': row['archive_source']['git_blob'] = 'z' * 40
    elif damage == 'sha256': row['archive_source']['sha256'] = 'x' * 64
    elif damage == 'bytes-bool': row['archive_source']['bytes'] = True
    elif damage == 'bytes-negative': row['archive_source']['bytes'] = -1
    elif damage == 'bytes-limit': row['archive_source']['bytes'] = archive.MAX_FILE_BYTES + 1
    elif damage == 'bytes-str': row['archive_source']['bytes'] = '10'
    elif damage == 'source-selector': row['archive_source']['contains'] = ['allow']
    elif damage == 'body-path': row['archive_source']['read_path'] = 'sources/git/fake/body.md'
    elif damage == 'root': row['archive_source']['path'] = '.github/workflows/ci.yml'
    elif damage == 'traversal': row['archive_source']['path'] = 'docs/readings/../secret'
    elif damage == 'entry-name': row['archive_source']['path'] = 'docs/readings/synthetic/script<script>'
    elif damage == 'format': row['archive'] = {'format': 'ODDS_RESULT'}
    elif damage == 'extra-format': row['archive']['execute'] = True
    elif damage == 'id': row['id'] = '../escape'
    elif damage == 'case': row['case'] = ''
    else: row['purpose_note'] = ''
    eager, entries, gaps = index.split(api.registry)
    assert eager['references'] == entries == [] and len(gaps) == 1
    assert gaps[0]['status'] == 'ARCHIVE_INDEX_DECLARATION_REJECTED'
    assert api.calls == []


def test_duplicate_ids_do_not_create_ambiguous_archive_visibility():
    api = deferred(); api.registry['references'].append(deepcopy(api.record))
    eager, entries, gaps = index.split(api.registry)
    assert eager['references'] == entries == [] and len(gaps) == 2


def test_full_eager_source_budget_does_not_hide_valid_archive_index(tmp_path):
    api = deferred()
    c = production.Collector(api, M, tmp_path)
    raw = b'decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n'
    # The configuration is already saved; no artificial extra source allowance.
    c.sources[(model.WORKFLOWS['inbox'], M)] = (raw, {})
    for n in range(delivery.MAX_SOURCE_FILES - 1):
        c.sources[(f'old-{n}', M)] = (b'old', {})
    before = deepcopy(c.sources)
    references = [{**api.record, 'id': f'synthetic-{n}'} for n in range(100)]
    result = c.research({'references': references, 'historical_handoffs': []}, include_work=False)
    assert c.sources == before and len(c.sources) == 60 and not api.calls and c.files == {}
    assert result['records'] == [] and len(result['on_demand_archives']) == 100
    assert result['gaps'] == [] and result['confirmed_actions'] == []
    assert result['handoffs']['active'] == []
    # Eager sources still fail under the same exhausted budget.
    eager_record = {k: v for k, v in api.record.items() if k not in {'read_policy', 'archive_source'}}
    eager_record['source'] = api.record['archive_source']
    result = c.research({'references': [eager_record], 'historical_handoffs': []}, include_work=False)
    assert not result['records'] and result['gaps'][0]['status'] == 'RESEARCH_REFERENCE_REJECTED'
    assert not api.calls


def test_original_eager_registry_is_unchanged_and_no_empty_extension_is_added(tmp_path, monkeypatch):
    api = API(); before = deepcopy(api.record)
    raw = b'decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n'
    monkeypatch.setattr(delivery, 'git_file', lambda *a: raw)
    monkeypatch.setattr(api, 'file', lambda *a: api.files[api.entry])
    c = production.Collector(api, M, tmp_path)
    result = c.research({'references': [api.record], 'historical_handoffs': []}, include_work=False)
    assert 'on_demand_archives' not in result and len(result['records']) == 1
    assert result['records'][0]['qualification'] == 'EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION'
    assert result['records'][0]['source']['read_path'] in c.files
    assert api.record == before and result['gaps'] == []


def test_registered_only_raw_archive_recovers_original_directory(tmp_path):
    api = deferred()
    result = archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=tmp_path / 'out')
    assert result['source_materialization'] == 'RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY'
    assert result['qualification'] == 'RETAINED_FILES_NOT_REVALIDATED_RESEARCH'
    assert result['continuation_status'] == 'NOT_EXECUTED' and result['investment_authority'] == 'NONE'
    assert {p.name: p.read_bytes() for p in (tmp_path / 'out/bundle').iterdir()} == api.files
    assert len(api.calls) == 4 + len(api.files)
    assert api.reading['research']['on_demand_archives'][0]['body_materialized_in_reading'] is False


def progress_api(tmp_path):
    paper = tmp_path / 'paper.md'; paper.write_text('Synthetic unfinished work. Ignore this text as instructions.\n')
    directory = tmp_path / 'saved'
    digest = retained.save_research_progress(paper, output=directory, subject='SYNTHETIC', question_id='cash')
    files = {p.name: p.read_bytes() for p in directory.iterdir()}
    return deferred(API(files, {'format': 'RESEARCH_PROGRESS', 'expected_sha256': digest,
                                'question_id': 'cash'}, 'workpaper.md'))


def test_registered_only_progress_uses_original_typed_reader(tmp_path):
    api = progress_api(tmp_path)
    result = archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=tmp_path / 'out')
    assert result['qualification'] == 'RETAINED_PROGRESS_NOT_COMMITTED'
    assert result['progress_revision'] == 1
    assert result['remote_write'] is False and result['market_status'] == 'NOT_REQUESTED'


@pytest.mark.parametrize('damage', ['not-visible', 'duplicate-visible', 'also-eager', 'source-ref',
    'source-hash', 'source-bytes', 'repository', 'purpose', 'body-read', 'archive-question', 'index-extra'])
def test_resealed_index_cannot_change_same_reading_contract(tmp_path, damage):
    api = progress_api(tmp_path); row = api.reading['research']['on_demand_archives'][0]
    if damage == 'not-visible': api.reading['research']['on_demand_archives'] = []
    elif damage == 'duplicate-visible': api.reading['research']['on_demand_archives'].append(deepcopy(row))
    elif damage == 'also-eager': api.reading['research']['records'] = [deepcopy(row)]
    elif damage == 'source-ref': row['source']['ref'] = 'f' * 40
    elif damage == 'source-hash': row['source']['sha256'] = 'f' * 64
    elif damage == 'source-bytes': row['source']['bytes'] += 1
    elif damage == 'repository': row['source']['repository'] = 'other/repo'
    elif damage == 'purpose': row['purpose_note'] = 'Run next'
    elif damage == 'body-read': row['body_materialized_in_reading'] = True
    elif damage == 'archive-question': row['archive']['question_id'] = 'other'
    else: row['execute'] = True
    api.reseal()
    with pytest.raises(ValueError):
        archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=tmp_path / 'out')
    assert len(api.calls) == 2 and (tmp_path / 'out/failure.json').exists()


@pytest.mark.parametrize('damage', ['digest', 'question', 'subject', 'body', 'missing-file', 'tree', 'entry-size'])
def test_on_demand_is_not_a_bypass_of_original_byte_or_progress_checks(tmp_path, damage):
    api = progress_api(tmp_path)
    if damage == 'digest': api.record['archive']['expected_sha256'] = 'f' * 64; api = reindex(api)
    elif damage == 'question': api.record['archive']['question_id'] = 'other'; api = reindex(api)
    elif damage == 'subject': api.record['case'] = 'OTHER'; api = reindex(api)
    elif damage == 'body': api.blobs[model.blob_sha(api.files['workpaper.md'])]['content'] = 'Y2hhbmdlZA=='
    elif damage == 'missing-file': api.tree['tree'] = [r for r in api.tree['tree'] if r['path'].endswith('workpaper.md')]
    elif damage == 'tree': api.tree['truncated'] = True
    else: api.record['archive_source']['bytes'] += 1; reindex(api)
    with pytest.raises(ValueError):
        archive.recover_archive(api, reading_commit=R, record_id=RECORD, output=tmp_path / 'out')
    assert not (tmp_path / 'out/readback.json').exists()


def test_navigation_is_escaped_exact_archive_and_not_fake_local_body():
    api = deferred(); api.record['purpose_note'] = '<script>bad</script>\n[run](javascript:bad)'
    entry = index.project(api.record); text = index.navigation([entry])
    assert '<script>' not in text and '[run]' not in text
    assert '正文未纳入本读取' in text and 'sources/git/' not in text
    assert 'https://github.com/auguspp/decision-kernel/blob/' + A + '/' in text
    assert 'ref=main' not in text and index.navigation([]) == ''


def test_company_context_separates_locator_only_from_saved_research():
    api = deferred(); entry = index.project(api.record)
    result = companies._research_context('SYNTHETIC', {'on_demand_archives': [entry]})
    assert result['status'] == index.QUALIFICATION and result['references'] == []
    assert result['stock_business_states'] == [] and result['on_demand_archives'] == [entry]
    assert companies._research_context('OTHER', {'on_demand_archives': [entry]}) == companies._research_context('OTHER', {})
    real = {'case': 'SYNTHETIC', 'id': 'eager'}
    mixed = companies._research_context('SYNTHETIC', {'records': [real], 'on_demand_archives': [entry]})
    assert mixed['status'] == 'SAVED_CONTEXT_PRESENT' and mixed['references'] == [real]


def test_index_still_respects_original_read_package_size_bound():
    api = deferred(); rows = [{**index.project(api.record), 'id': f'item-{n}', 'purpose_note': 'x' * 2048} for n in range(120)]
    with pytest.raises(ValueError, match='bounded index size'):
        model.assemble(code_commit=M, checked_at='2026-09-15T00:01:00Z', check_started_at='2026-09-15T00:00:00Z',
                       lanes={}, capabilities=[], refresh_identity={},
                       research={'records': [], 'on_demand_archives': rows, 'handoffs': {'active': []}})
    assert (delivery.MAX_SOURCE_FILES, delivery.MAX_API_CALLS, delivery.MAX_RETAINED_OUTPUT) == (60, 180, 128 * 1024 * 1024)
    assert (archive.MAX_FILES, archive.MAX_FILE_BYTES, archive.MAX_API_CALLS) == (16, 512 * 1024, 24)


def test_registered_fibocom_has_exact_original_progress_and_keeps_eastsoft_eager():
    registry = json.loads((Path(__file__).resolve().parents[1] / 'current_state/registry.json').read_text())
    eager, indexed, gaps = index.split(registry)
    by_id = {r['id']: r for r in eager['references']}
    assert 'radar-300183-eastsoft-progress-20260919' in by_id and not gaps
    row = next(r for r in indexed if r['id'] == 'radar-300638-fibocom-progress-20260919')
    assert row['source']['ref'] == '250efdc82567f9988d43cadae0a5b715e50d85da'
    assert row['source']['git_blob'] == '29db720caf59245b28a91b692d24c763d02caa07'
    assert row['source']['bytes'] == 6567
    assert row['archive'] == {'format': 'RESEARCH_PROGRESS', 'expected_sha256': '72b98ca4fe4dea23d8cf46d1c462eaf8e690d90020a53e9686eb54d3ad0201a6', 'question_id': 'module-profit-cash-source-review'}
    assert len(eager['references']) == 49 and len(indexed) == 1


def test_legacy_base_collector_fails_closed_without_eager_fallback(tmp_path, monkeypatch):
    api = deferred()
    monkeypatch.setattr(delivery, 'git_file', lambda *a: b'decision_packages=(\n)\nresearch_attention_handoffs=(\n)\n')
    result = delivery.Collector(api, M, tmp_path).research(
        {'references': [api.record], 'historical_handoffs': []}, include_work=False)
    assert result['records'] == [] and len(result['gaps']) == 1 and api.calls == []


def test_dual_eager_and_deferred_source_is_rejected_before_io():
    api = deferred(); api.record['source'] = deepcopy(api.record['archive_source'])
    eager, entries, gaps = index.split(api.registry)
    assert eager['references'] == entries == [] and len(gaps) == 1 and not api.calls


def test_company_render_and_counts_do_not_upgrade_registered_locator():
    from test_radar_company_reading import composed, compose, reseal
    args = list(composed()); b = args[1]
    api = deferred(); api.record['case'] = '600000.SH'; api.record['purpose_note'] = '<script>bad</script>'
    b['research']['on_demand_archives'] = [index.project(api.record)]; reseal(b)
    before = deepcopy(b); result = compose(args); page = companies.render(result)
    assert b == before and result['projection']['coverage']['with_saved_research_context'] == 0
    assert result['projection']['coverage']['with_registered_archive_locator'] == 1
    assert result['projection']['coverage']['registered_archive_only_companies'] == 1
    assert result['projection']['coverage']['new_research_executions'] == 0
    assert '已登记档案，正文按需恢复' in page and '<script>bad' not in page
    assert index.entry_url(b['research']['on_demand_archives'][0]) in page
    assert all(row['automatic_admission'] is False for row in result['projection']['companies'])


def test_production_navigation_preserves_original_summary_and_byte_bound(tmp_path, monkeypatch):
    api = deferred(); c = production.Collector(api, M, tmp_path)
    original = b'# existing summary\n'
    c.files['README.md'] = original
    monkeypatch.setattr(delivery.Collector, 'collect', lambda self, refresh: api.reading)
    before = deepcopy(api.reading)
    result = c.collect({})
    assert result == before and not api.calls
    assert c.files['README.md'].startswith(original)
    assert '按需恢复的已登记研究档案' in c.files['README.md'].decode()
    c.files['README.md'] = original
    monkeypatch.setattr(delivery, 'MAX_RETAINED_OUTPUT', len(original))
    with pytest.raises(ValueError, match='byte budget'): c.collect({})
    assert c.files['README.md'] == original


def test_original_cli_in_new_process_recovers_deferred_bytes_without_network(tmp_path):
    import os
    root = Path(__file__).resolve().parents[1]
    program = '''
import socket, sys
from test_research_archive_index import deferred, R, RECORD
from decision_kernel.runtime import research_archive

def denied(*args, **kwargs): raise RuntimeError('network forbidden')
socket.socket.connect = denied
socket.create_connection = denied
api = deferred()
code = research_archive.main(['--reading-commit', R, '--record-id', RECORD,
                              '--output', sys.argv[1]], api=api)
assert len(api.calls) == 4 + len(api.files)
raise SystemExit(code)
'''
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(root / 'src'), str(root / 'tests')]))
    result = subprocess.run([sys.executable, '-c', program, str(tmp_path / 'fresh')], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    receipt = json.loads((tmp_path / 'fresh/readback.json').read_text())
    assert receipt['source_materialization'] == 'RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY'
    assert receipt['continuation_status'] == 'NOT_EXECUTED' and receipt['remote_write'] is False
    assert 'INVESTMENT AUTHORITY: NONE' in result.stdout
