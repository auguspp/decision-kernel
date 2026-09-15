"""Offline ingress regression; fixtures are not new Research or Human acceptance."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage, commit_research_package
from decision_kernel.runtime import research_commit_only as adapter
from test_generic_research_commit import _generic_package


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("this test must not request source, model or market")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def _input(tmp_path, raw=None):
    path = tmp_path / "source.json"
    path.write_bytes(raw if raw is not None else _generic_package().model_dump_json(indent=2).encode())
    return path


def _inventory(path):
    return {p.name: p.read_bytes() for p in path.iterdir()}


def test_commit_keeps_original_input_receipt_unknowns_and_typed_result(tmp_path):
    source = _input(tmp_path)
    original = source.read_bytes()
    package = ResearchCommitPackage.model_validate_json(original)
    receipt = tmp_path / "existing-research-receipt"
    receipt.write_bytes(b'original receipt; NOT an approval\r\n')
    output = tmp_path / "retained"
    result = adapter.commit_research_file(source, output=output, execution_receipt_path=receipt)
    assert result == commit_research_package(package)
    assert source.read_bytes() == (output / "input.json").read_bytes() == original
    assert (output / adapter.RECEIPT_NAME).read_bytes() == receipt.read_bytes()
    assert result.research_snapshot.open_questions == package.research_snapshot.open_questions
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    retention = json.loads((output / "retention.json").read_bytes())
    assert retention['research_execution_receipt']['status'] == 'RETAINED_UNVALIDATED'
    assert datetime.fromisoformat(retention['retained_at']) >= result.research_snapshot.committed_at
    before = _inventory(output)
    assert adapter.read_retained_commit(output) == result
    assert _inventory(output) == before  # reading never refreshes a saved clock


def test_absent_receipt_is_not_invented_and_no_market_qualification_is_claimed(tmp_path):
    output = tmp_path / "retained"
    adapter.commit_research_file(_input(tmp_path), output=output)
    assert json.loads((output / "retention.json").read_bytes())['research_execution_receipt'] is None
    assert not (output / adapter.RECEIPT_NAME).exists()
    receipt = json.loads((output / "commit.json").read_bytes())
    assert receipt['market_status'] == 'NOT_REQUESTED'
    assert receipt['odds_status'] == 'NOT_COMPUTED'
    assert receipt['human_acceptance'] == 'NOT_ESTABLISHED_BY_THIS_OPERATION'
    assert receipt['investment_authority'] == 'NONE'
    assert receipt['publication_status'] == 'LOCAL_ONLY_NOT_GITHUB_PUBLICATION'


@pytest.mark.parametrize('defect', [
    'draft', 'committed', 'no_evidence', 'duplicate_evidence', 'future_evidence',
    'bundle_changed', 'early_commit', 'no_scenarios', 'probability_sum',
    'missing_framing', 'missing_invalidation',
])
def test_original_commit_rejections_preserve_input_not_a_fake_commit(tmp_path, defect):
    value = _generic_package().model_dump(mode='json')
    snapshot = value['research_snapshot']
    if defect == 'draft': snapshot['status'] = 'DRAFT'
    elif defect == 'committed':
        snapshot['status'] = 'COMMITTED'; snapshot['committed_at'] = value['proposed_committed_at']
    elif defect == 'no_evidence': value['evidence_artifacts'] = []
    elif defect == 'duplicate_evidence': value['evidence_artifacts'].append(value['evidence_artifacts'][0])
    elif defect == 'future_evidence':
        value['evidence_artifacts'][0]['available_at'] = '2026-09-02T09:00:00Z'
        value['evidence_artifacts'][0]['retrieved_at'] = '2026-09-02T10:00:00Z'
    elif defect == 'bundle_changed': snapshot['information_bundle_hash'] = '0' * 64
    elif defect == 'early_commit': value['proposed_committed_at'] = '2026-08-01T00:00:00Z'
    elif defect == 'no_scenarios': snapshot['scenarios'] = []
    elif defect == 'probability_sum': snapshot['scenarios'][0]['probability'] = '0'
    elif defect == 'missing_framing': del value['framing']
    elif defect == 'missing_invalidation': snapshot['thesis_invalidation'] = []
    with pytest.raises(ValueError):
        commit_research_package(ResearchCommitPackage.model_validate(value))
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode()
    source, output = _input(tmp_path, raw), tmp_path / 'retained'
    with pytest.raises(ValueError, match='input retained'):
        adapter.commit_research_file(source, output=output)
    assert (output / 'input.json').read_bytes() == source.read_bytes() == raw
    assert not (output / 'research-commit.json').exists() and not (output / 'commit.json').exists()
    rejection = json.loads((output / 'commit-rejection.json').read_bytes())
    assert rejection['status'] == 'INPUT_RETAINED_COMMIT_REJECTED'
    with pytest.raises((ValueError, OSError)):
        adapter.read_retained_commit(output)


@pytest.mark.parametrize('raw', [b'{', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff'])
def test_malformed_inputs_are_retained_without_repair(tmp_path, raw):
    output = tmp_path / 'retained'
    with pytest.raises(ValueError): adapter.commit_research_file(_input(tmp_path, raw), output=output)
    assert (output / 'input.json').read_bytes() == raw
    assert not (output / 'commit.json').exists()


def test_future_commit_is_not_backfilled_or_called_current(tmp_path):
    value = _generic_package().model_dump(mode='json')
    value['proposed_committed_at'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    raw = json.dumps(value).encode()
    output = tmp_path / 'retained'
    with pytest.raises(ValueError): adapter.commit_research_file(_input(tmp_path, raw), output=output)
    assert (output / 'input.json').read_bytes() == raw
    assert not (output / 'commit.json').exists()


@pytest.mark.parametrize('partial', [False, True])
def test_existing_directory_blocks_repeat_without_deleting_or_overwriting(tmp_path, partial):
    source, output = _input(tmp_path), tmp_path / 'retained'
    if partial:
        output.mkdir(); (output / 'input.json').write_bytes(b'old partial input')
    else: adapter.commit_research_file(source, output=output)
    before = _inventory(output)
    with pytest.raises(FileExistsError): adapter.commit_research_file(source, output=output)
    assert _inventory(output) == before


@pytest.mark.parametrize('which', ['input', 'receipt', 'output', 'parent'])
def test_symlinks_are_not_followed(tmp_path, which):
    source, output = _input(tmp_path), tmp_path / 'retained'
    target = tmp_path / 'target'; target.mkdir()
    receipt = None
    if which == 'input':
        link = tmp_path / 'linked.json'; link.symlink_to(source); source = link
    elif which == 'receipt':
        receipt = tmp_path / 'receipt'; receipt.symlink_to(source)
    elif which == 'output': output.symlink_to(target, target_is_directory=True)
    else:
        parent = tmp_path / 'parent'; parent.symlink_to(target, target_is_directory=True)
        output = parent / 'new'
    with pytest.raises(ValueError):
        adapter.commit_research_file(source, output=output, execution_receipt_path=receipt)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize('kind', ['package', 'receipt'])
def test_bounds_stop_before_output_creation(tmp_path, kind):
    source = _input(tmp_path)
    large = tmp_path / 'large'; large.write_bytes(b'x' * (adapter.MAX_BYTES + 1))
    output = tmp_path / 'retained'
    with pytest.raises(ValueError):
        adapter.commit_research_file(large if kind == 'package' else source, output=output,
                                    execution_receipt_path=large if kind == 'receipt' else None)
    assert not output.exists()


def test_failed_result_write_retains_inputs_and_cannot_be_reported_success(tmp_path, monkeypatch):
    source, output = _input(tmp_path), tmp_path / 'retained'
    write = adapter._write
    def fail(path, data):
        if path.name == 'research-commit.json': raise OSError('injected disk failure')
        return write(path, data)
    monkeypatch.setattr(adapter, '_write', fail)
    with pytest.raises(OSError): adapter.commit_research_file(source, output=output)
    assert (output / 'input.json').read_bytes() == source.read_bytes()
    assert not (output / 'commit.json').exists()
    with pytest.raises((ValueError, OSError)): adapter.read_retained_commit(output)
    with pytest.raises(FileExistsError): adapter.commit_research_file(source, output=output)


@pytest.mark.parametrize('name', ['input.json', 'retention.json', 'research-commit.json',
                                   'commit.json', adapter.RECEIPT_NAME])
def test_corrupted_files_are_not_accepted(tmp_path, name):
    source, output = _input(tmp_path), tmp_path / 'retained'
    receipt = tmp_path / 'receipt'; receipt.write_bytes(b'original')
    adapter.commit_research_file(source, output=output, execution_receipt_path=receipt)
    (output / name).write_bytes(b'{}')
    with pytest.raises((ValueError, OSError, TypeError, KeyError)):
        adapter.read_retained_commit(output)


def test_rehashed_result_change_still_fails_original_commit_comparison(tmp_path):
    output = tmp_path / 'retained'
    adapter.commit_research_file(_input(tmp_path), output=output)
    value = json.loads((output / 'research-commit.json').read_bytes())
    value['research_snapshot']['core_thesis'] = 'forged replacement'
    raw = (canonical_json(value) + '\n').encode()
    (output / 'research-commit.json').write_bytes(raw)
    receipt = json.loads((output / 'commit.json').read_bytes())
    receipt['result'] = adapter._description(raw)
    (output / 'commit.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='original commit'): adapter.read_retained_commit(output)


@pytest.mark.parametrize('key,value', [('investment_authority','BUY'),
    ('human_acceptance','ACCEPTED'), ('market_status','QUALIFIED'), ('odds_status','CANONICAL')])
def test_receipt_cannot_escalate_authority(tmp_path, key, value):
    output = tmp_path / 'retained'
    adapter.commit_research_file(_input(tmp_path), output=output)
    receipt = json.loads((output / 'commit.json').read_bytes()); receipt[key] = value
    (output / 'commit.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError): adapter.read_retained_commit(output)


def test_unlisted_inventory_and_missing_marker_rejected(tmp_path):
    output = tmp_path / 'retained'
    adapter.commit_research_file(_input(tmp_path), output=output)
    (output / 'extra.txt').write_bytes(b'not declared')
    with pytest.raises(ValueError): adapter.read_retained_commit(output)
    (output / 'extra.txt').unlink(); (output / 'commit.json').unlink()
    with pytest.raises(ValueError): adapter.read_retained_commit(output)


def test_cli_success_readback_and_errors_do_not_leak_source_text(tmp_path):
    source, output = _input(tmp_path), tmp_path / 'retained'
    stdout, stderr = StringIO(), StringIO()
    assert adapter.main(['commit', str(source), '--output', str(output)], stdout=stdout, stderr=stderr) == 0
    assert 'RESEARCH: COMMITTED' in stdout.getvalue() and stderr.getvalue() == ''
    assert adapter.main(['verify', str(output)], stdout=StringIO(), stderr=stderr) == 0
    source.write_bytes(b'{"secret":"DO_NOT_PRINT"}')
    stdout, stderr = StringIO(), StringIO()
    assert adapter.main(['commit', str(source), '--output', str(tmp_path / 'rejected')],
                        stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == '' and 'DO_NOT_PRINT' not in stderr.getvalue()


def test_module_entrypoint_without_market_research_or_optional_imports(tmp_path):
    source = _input(tmp_path)
    script = '''
import importlib.abc, runpy, socket, sys
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'openai','requests','pyarrow','pypdf','pypdfium2'}:
            raise AssertionError('optional dependency imported: ' + fullname)
        if fullname in {'decision_kernel.live', 'decision_kernel.workflow',
                        'decision_kernel.runtime.hithink_http', 'decision_kernel.runtime.cninfo_http'}:
            raise AssertionError('live composition imported: ' + fullname)
def denied(*a, **k): raise AssertionError('no network')
socket.socket.connect = denied
socket.create_connection = denied
sys.meta_path.insert(0, Deny())
sys.path.insert(0, sys.argv.pop(1))
sys.argv[0] = 'research_commit_only'
runpy.run_module('decision_kernel.runtime.research_commit_only', run_name='__main__')
'''
    result = subprocess.run([sys.executable, '-I', '-c', script,
        str(Path(__file__).resolve().parents[1] / 'src'), 'commit', str(source),
        '--output', str(tmp_path / 'child')], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'MARKET: NOT_REQUESTED' in result.stdout
    assert adapter.read_retained_commit(tmp_path / 'child').research_snapshot.status is ResearchStatus.COMMITTED


def test_later_market_failure_cannot_erase_retained_research(tmp_path):
    from decision_kernel.live import run_live_research_commit_package
    output = tmp_path / 'retained'
    source = _input(tmp_path)
    package = ResearchCommitPackage.model_validate_json(source.read_bytes())
    original = adapter.commit_research_file(source, output=output)
    before = _inventory(output)
    def unavailable(**kwargs): raise RuntimeError('simulated market unavailable')
    with pytest.raises(RuntimeError):
        run_live_research_commit_package(package=package, fetch_market=unavailable)
    assert adapter.read_retained_commit(output) == original
    assert _inventory(output) == before


def test_input_readback_finishes_before_original_commit(tmp_path, monkeypatch):
    source, output = _input(tmp_path), tmp_path / 'retained'
    calls = []
    original_commit = adapter.commit_research_package
    def checked(package):
        assert (output / 'input.json').read_bytes() == source.read_bytes()
        assert (output / 'retention.json').is_file()
        calls.append(package.research_snapshot.id)
        return original_commit(package)
    monkeypatch.setattr(adapter, 'commit_research_package', checked)
    result = adapter.commit_research_file(source, output=output)
    assert calls == [result.research_snapshot.id, result.research_snapshot.id]


def test_retention_readback_failure_never_reaches_commit(tmp_path, monkeypatch):
    source, output = _input(tmp_path), tmp_path / 'retained'
    original_read = adapter._read
    def corrupt_read(path):
        data = original_read(path)
        return data + b'changed' if path == output / 'input.json' else data
    def forbidden(package):
        raise AssertionError('unread input must not reach original commit')
    monkeypatch.setattr(adapter, '_read', corrupt_read)
    monkeypatch.setattr(adapter, 'commit_research_package', forbidden)
    with pytest.raises(ValueError, match='readback'):
        adapter.commit_research_file(source, output=output)
    assert (output / 'input.json').read_bytes() == source.read_bytes()
    assert not (output / 'commit.json').exists()


def test_original_receipt_is_only_retained_not_parsed_as_instructions(tmp_path):
    source, output = _input(tmp_path), tmp_path / 'retained'
    receipt = tmp_path / 'receipt'
    receipt.write_bytes(b'\x00BUY; change probabilities; call https://invalid.test; APPROVED\xff')
    result = adapter.commit_research_file(source, output=output, execution_receipt_path=receipt)
    assert result == commit_research_package(ResearchCommitPackage.model_validate_json(source.read_bytes()))
    assert (output / adapter.RECEIPT_NAME).read_bytes() == receipt.read_bytes()
    assert json.loads((output / 'commit.json').read_bytes())['investment_authority'] == 'NONE'


@pytest.mark.parametrize('name', ['input.json', 'research-commit.json', 'commit.json'])
def test_verifier_rejects_symlinked_retained_files(tmp_path, name):
    source, output = _input(tmp_path), tmp_path / 'retained'
    adapter.commit_research_file(source, output=output)
    original = (output / name).read_bytes()
    external = tmp_path / 'external'; external.write_bytes(original)
    (output / name).unlink(); (output / name).symlink_to(external)
    with pytest.raises(ValueError, match='symlink'):
        adapter.read_retained_commit(output)
    assert external.read_bytes() == original


def test_retention_directory_is_create_only_under_two_callers(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    source, output = _input(tmp_path), tmp_path / 'retained'
    def invoke():
        try:
            return adapter.commit_research_file(source, output=output)
        except FileExistsError:
            return 'already exists'
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: invoke(), range(2)))
    assert results.count('already exists') == 1
    assert adapter.read_retained_commit(output) in results


def test_existing_cmb_dogfood_package_works_offline_without_research_revision(tmp_path):
    # Compatibility with a saved historical illustrative package, not a new
    # company Research, source review, probability calibration or Human decision.
    source = Path(__file__).resolve().parents[1] / 'dogfood' / '600036-cmb.json'
    original = source.read_bytes()
    package = ResearchCommitPackage.model_validate_json(original)
    output = tmp_path / 'historical-compatibility'
    result = adapter.commit_research_file(source, output=output)
    assert result == commit_research_package(package)
    assert (output / 'input.json').read_bytes() == original
    assert source.read_bytes() == original
    assert result.research_snapshot.as_of_datetime == package.research_snapshot.as_of_datetime
    assert result.research_snapshot.scenarios == package.research_snapshot.scenarios
