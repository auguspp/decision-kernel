from __future__ import annotations

import copy
import hashlib
import json
import runpy
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_company_context as company
from decision_kernel.runtime import economic_market_context as market
from decision_kernel.runtime import sector_radar_context as context
from test_economic_market_context import links_for
from test_sector_radar_publication_gate import make_case, identity, inventory, script as publication_script

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/scripts/build-sector-radar-reading.py'
WORKFLOW = ROOT / '.github/workflows/sector-radar-shadow.yml'
NOW = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)


def case(tmp_path, monkeypatch, mode='candidates'):
    # Actual calculation/replay, with mocked transport in the existing LIVE-branch
    # fixture. This is NOT real acquisition or an artifact for the production chain.
    run, state, outcome, observed = make_case(tmp_path / 'producer', monkeypatch, mode)
    gate = publication_script()
    receipt = gate['verify_publication'](run, state, identity())
    (run / 'publication-verification.json').write_text(canonical_json(receipt) + '\n')
    class Clock:
        @staticmethod
        def now(tz=None): return NOW + timedelta(seconds=1)
    monkeypatch.setattr(context, 'datetime', Clock)
    monkeypatch.setattr(market, 'datetime', Clock)
    assert context.main(['--bundle', str(state), '--parent-hints', str(run / 'input-audit/inputs/parent-hints.json'),
                         '--output', str(run / 'context')]) == 0
    glue = runpy.run_path(str(SCRIPT), run_name='joint_delivery_test')
    root = tmp_path / 'sources'; root.mkdir()
    spec = json.loads((ROOT / glue['COMPANIES']).read_text())
    names = {glue['SEED'], glue['LINKS'], glue['COMPANIES']}
    names.update(c['source_path'] for n in spec['nodes'] for c in n['companies'])
    for name in names:
        p = root / name; p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, p)
    (root / glue['HINTS']).write_bytes((run / 'input-audit/inputs/parent-hints.json').read_bytes())
    (root / glue['LINKS']).write_text(canonical_json(links_for(outcome.persistent_bundle.market_state)))
    (root / glue['REVIEWS']).mkdir()
    (root / glue['REVIEWS'] / '.gitkeep').touch()
    temp = tmp_path / 'staging'; temp.mkdir()
    def build():
        return glue['build_delivery'](root, run, state, temp, identity=identity(), as_of=NOW)
    return glue, build, root, run, state, temp, outcome


@pytest.mark.parametrize('mode', ['same-session', 'quiet', 'candidates'])
def test_existing_joint_cli_packages_exact_inputs_and_never_mutates_producer(tmp_path, monkeypatch, mode):
    glue, build, root, run, state, temp, outcome = case(tmp_path, monkeypatch, mode)
    originals = inventory(root), inventory(state), inventory(run)
    result = build(); target = run / 'economic-company'
    assert inventory(root) == originals[0] and inventory(state) == originals[1]
    assert {k: v for k, v in inventory(run).items() if not k.startswith('economic-company/')} == originals[2]
    assert not list(temp.iterdir()) and not list(run.glob('.reading-publish-*'))
    assert {p.name for p in target.iterdir()} == glue['PAGE_FILES'] | {'inputs.zip', 'README.txt', 'delivery.json'}
    assert result['delivery_hash'] == canonical_hash({k: v for k, v in result.items() if k != 'delivery_hash'})
    assert result['market_state_hash'] == outcome.persistent_bundle.market_state.state_hash
    assert result['event_ledger_hash'] == outcome.persistent_bundle.event_ledger.ledger_hash
    assert result['workflow_identity'] == identity()
    assert result['original_pdfs_reverified'] is result['remote_upload_verified'] is False
    assert result['source_commit_membership_verified'] is False
    assert result['market_event_writes'] == 0 and result['company_benefit_established'] is False
    for name, digest in result['files'].items():
        raw = (target / name).read_bytes()
        assert digest == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    with zipfile.ZipFile(target / 'inputs.zip') as archive:
        assert set(archive.namelist()) == set(result['source_files']) | {d + '/' for d in result['source_directories']}
        for name, digest in result['source_files'].items():
            raw = archive.read(name)
            assert digest == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        assert archive.read(glue['REVIEWS'] + '/.gitkeep') == b''
        assert archive.read('state/candidate-events.json') == (state / 'candidate-events.json').read_bytes()
    association = json.loads((target / 'association.json').read_text())
    event_ids = {i for p in association['projection']['panels'] for m in p['markets']
                 for i in m['saved_market']['recorded_event_ids_latest_session']}
    assert event_ids == {e.event_id for e in outcome.persistent_bundle.event_ledger.events}
    assert len(event_ids) == (2 if mode == 'candidates' else 0)
    soup = BeautifulSoup((target / 'index.html').read_text(), 'html.parser')
    assert '牧原' in soup.get_text() and '圆通' in soup.get_text()
    assert len(soup.select('#company-evidence')) == 1
    assert soup.find('script') is soup.find('iframe') is None


def test_packaged_inputs_rebuild_existing_cli_without_original_source_directory(tmp_path, monkeypatch):
    glue, build, root, run, state, temp, _ = case(tmp_path, monkeypatch)
    receipt = build(); target = run / 'economic-company'
    copied = tmp_path / 'downloaded-inputs'
    with zipfile.ZipFile(target / 'inputs.zip') as archive:
        archive.extractall(copied)  # Trusted locally generated, bounded fixture archive.
    shutil.rmtree(root)
    output = tmp_path / 'rebuilt'
    assert company.main([
        '--source-root', str(copied), '--seed', str(copied / glue['SEED']),
        '--reviews-dir', str(copied / glue['REVIEWS']), '--bundle', str(copied / 'state'),
        '--parent-hints', str(copied / glue['HINTS']), '--links', str(copied / glue['LINKS']),
        '--company-links', glue['COMPANIES'], '--as-of', receipt['input_cutoff'], '--output', str(output),
    ]) == 0
    for name in glue['PAGE_FILES']:
        assert (output / name).read_bytes() == (target / name).read_bytes()


@pytest.mark.parametrize('change', ['receipt', 'other_run', 'rejected', 'missing', 'state', 'operations', 'context', 'hints'])
def test_wrong_precheck_or_changed_producer_bytes_never_publish_a_reading(tmp_path, monkeypatch, change):
    glue, build, root, run, state, temp, _ = case(tmp_path, monkeypatch)
    path = run / 'publication-verification.json'
    receipt = json.loads(path.read_text())
    if change == 'receipt': receipt['verification_hash'] = '0' * 64
    if change == 'other_run': receipt['workflow_identity']['run_id'] += 1
    if change == 'rejected': receipt['offline_replay']['status'] = 'MATCHED_REJECTED'
    if change in {'other_run', 'rejected'}:
        receipt['verification_hash'] = canonical_hash({k: v for k, v in receipt.items() if k != 'verification_hash'})
    if change in {'receipt', 'other_run', 'rejected'}: path.write_text(canonical_json(receipt))
    if change == 'missing': path.unlink()
    if change == 'state': (state / 'market-state.json').write_bytes((state / 'market-state.json').read_bytes() + b'\n')
    if change == 'operations': (run / 'operations.md').write_text('old output')
    if change == 'context': (run / 'context/context.json').write_text('{}')
    if change == 'hints': (root / glue['HINTS']).write_bytes((root / glue['HINTS']).read_bytes() + b'\n')
    before = inventory(root), inventory(state), inventory(run)
    with pytest.raises((ValueError, OSError, KeyError, RuntimeError)): build()
    assert before == (inventory(root), inventory(state), inventory(run))
    assert not list(temp.iterdir())


@pytest.mark.parametrize('change', ['missing_reviews', 'draft', 'company_drift', 'symlink', 'budget'])
def test_missing_or_unaccepted_economic_company_inputs_are_not_empty_success(tmp_path, monkeypatch, change):
    glue, build, root, run, state, temp, _ = case(tmp_path, monkeypatch)
    reviews = root / glue['REVIEWS']
    if change == 'missing_reviews': shutil.rmtree(reviews)
    if change == 'draft': (reviews / 'draft.json').write_text('{"status":"PENDING_REVIEW"}')
    if change == 'company_drift':
        p = next((root / 'radar_inputs/company-evidence').glob('*.json'))
        p.write_bytes(p.read_bytes() + b'\n')
    if change == 'symlink':
        p = root / glue['SEED']; p.unlink(); p.symlink_to(ROOT / glue['SEED'])
    if change == 'budget': glue['build_delivery'].__globals__['MAX_FILES'] = 3
    before = inventory(root), inventory(state), inventory(run)
    with pytest.raises((ValueError, OSError, KeyError, RuntimeError)): build()
    assert before == (inventory(root), inventory(state), inventory(run))
    assert not list(temp.iterdir())


def test_repeat_delivery_never_overwrites_prior_page(tmp_path, monkeypatch):
    _, build, root, run, state, _, _ = case(tmp_path, monkeypatch)
    build(); before = inventory(run)
    with pytest.raises(ValueError, match='never replace'): build()
    assert inventory(run) == before


def test_interrupted_destination_copy_cleans_only_owned_staging(tmp_path, monkeypatch):
    _, build, root, run, state, temp, _ = case(tmp_path, monkeypatch)
    before = inventory(root), inventory(state), inventory(run)
    original = shutil.copytree
    def broken(src, dst, *a, **kw):
        if '.reading-publish-' in str(dst):
            Path(dst).mkdir(); (Path(dst) / 'partial').write_text('interrupted')
            raise OSError('synthetic copy failure')
        return original(src, dst, *a, **kw)
    monkeypatch.setattr(shutil, 'copytree', broken)
    with pytest.raises(OSError): build()
    assert before == (inventory(root), inventory(state), inventory(run))
    assert not list(temp.iterdir())


def test_input_change_after_render_is_detected_before_publication(tmp_path, monkeypatch):
    glue, build, root, run, state, temp, _ = case(tmp_path, monkeypatch)
    old = company.main
    def altered(args):
        result = old(args)
        p = root / glue['SEED']; p.write_bytes(p.read_bytes() + b'\n')
        return result
    monkeypatch.setattr(company, 'main', altered)
    before = inventory(state), inventory(run)
    with pytest.raises(ValueError, match='inputs changed'): build()
    assert before == (inventory(state), inventory(run))
    assert not list(temp.iterdir())


@pytest.mark.parametrize('key,value', [
    ('GITHUB_REF', 'refs/heads/feature'), ('GITHUB_EVENT_NAME', 'push'),
    ('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_REPOSITORY', 'other/repo'),
    ('HITHINK_FINANCE_API_KEY', 'must-not-arrive'),
])
def test_workflow_entry_refuses_wrong_identity_or_market_secret(tmp_path, monkeypatch, key, value):
    glue = runpy.run_path(str(SCRIPT), run_name='joint_delivery_entry_test')
    for k, v in {'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REPOSITORY': 'auguspp/decision-kernel',
                 'HITHINK_FINANCE_API_KEY': ''}.items(): monkeypatch.setenv(k, v)
    monkeypatch.setenv(key, value); monkeypatch.chdir(tmp_path)
    assert glue['main']() == 2 and not list(tmp_path.iterdir())


def test_workflow_reuses_existing_artifact_and_keeps_all_or_nothing_publication():
    text = WORKFLOW.read_text()
    names = ['Verify exact offline replay before publication', 'Render read-only saved-state context',
             'Package joint economic and company reading', 'Upload complete run audit',
             'Upload authoritative state bundle', 'Save cache acceleration copy']
    assert [text.index(n) for n in names] == sorted(text.index(n) for n in names)
    step = text.split('      - name: ' + names[2] + '\n')[1].split('      - name: ')[0]
    assert 'if: success()' in step and 'HITHINK_FINANCE_API_KEY: ""' in step
    assert 'python .github/scripts/build-sector-radar-reading.py' in step
    assert "pip install -e '.[discovery]'" in text
    assert 'schedule:' not in text and 'continue-on-error' not in text
    assert 'economic-company/index.html' in text and 'steps.joint-reading.outcome' in text
    assert '[ "$JOINT_OUTCOME" = "success" ] && [ -n "$RUN_AUDIT_URL" ]' in text
    assert text.count('uses: actions/upload-artifact@v7') == 2
    for name in names[-2:]:
        assert 'if: success()' in text.split('      - name: ' + name + '\n')[1].split('      - name: ')[0]
