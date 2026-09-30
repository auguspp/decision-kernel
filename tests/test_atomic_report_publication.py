"""Create-only report pairs, including interruption of real retained-input CLIs."""
from concurrent.futures import ThreadPoolExecutor
import errno
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.runtime import current_state as state
from decision_kernel.runtime import research_commit_only as retention


ROOT = Path(__file__).resolve().parents[1]
PAIR = {'report.json': b'{"status":"retained"}\n', 'report.md': b'# Retained\n'}
QUALIFIED_HOST = sys.platform.startswith('linux') or sys.platform == 'win32'
requires_publication = pytest.mark.skipif(
    not QUALIFIED_HOST, reason='atomic no-replace publication is not qualified on this host')


def contents(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def assert_no_staging(parent):
    assert not list(parent.glob('.kernel-report-*'))


@requires_publication
def test_publish_exposes_only_complete_readback_verified_pair(tmp_path, monkeypatch):
    output = tmp_path / 'report'
    original_rename = retention._rename_new_directory
    original_fsync = retention.os.fsync
    written, synced, renamed = [], [], []

    def fsync(fd):
        original_fsync(fd)
        synced.append(fd)

    def write(path, raw):
        assert not output.exists()
        assert path.parent.parent.parent == output.parent
        retention._write(path, raw)
        written.append(path)

    def rename(source, destination):
        assert destination == output
        assert contents(source) == PAIR
        assert not output.exists()
        assert len(synced) == len(written) == 2
        original_rename(source, destination)
        renamed.append(destination)

    monkeypatch.setattr(retention.os, 'fsync', fsync)
    monkeypatch.setattr(retention, '_rename_new_directory', rename)
    retention._publish_report_files(output, PAIR, write_file=write)
    assert contents(output) == PAIR
    assert renamed == [output]
    assert_no_staging(tmp_path)


@requires_publication
@pytest.mark.parametrize('fail_on', [1, 2])
@pytest.mark.parametrize('failure_point', ['before', 'partial', 'after'])
def test_first_or_second_write_failure_leaves_no_output_and_retry_works(
        tmp_path, fail_on, failure_point):
    output = tmp_path / 'report'
    calls = []

    def failing_write(path, raw):
        calls.append(path.name)
        if len(calls) == fail_on:
            if failure_point == 'partial':
                path.write_bytes(raw[:1])
            elif failure_point == 'after':
                retention._write(path, raw)
            raise OSError(errno.ENOSPC, 'injected report write failure')
        retention._write(path, raw)

    with pytest.raises(OSError, match='injected report write failure'):
        retention._publish_report_files(output, PAIR, write_file=failing_write)
    assert len(calls) == fail_on
    assert not output.exists()
    assert_no_staging(tmp_path)
    retention._publish_report_files(output, PAIR)
    assert contents(output) == PAIR
    assert_no_staging(tmp_path)


@requires_publication
@pytest.mark.parametrize('corrupted_name', list(PAIR))
def test_corruption_after_writer_readback_is_caught_before_publication(
        tmp_path, corrupted_name):
    output = tmp_path / 'report'

    def corrupting_write(path, raw):
        retention._write(path, raw)
        if path.name == 'report.md':
            (path.parent / corrupted_name).write_bytes(b'corrupted after original readback')

    with pytest.raises(ValueError, match='staged report bytes failed readback'):
        retention._publish_report_files(output, PAIR, write_file=corrupting_write)
    assert not output.exists()
    assert_no_staging(tmp_path)
    retention._publish_report_files(output, PAIR)
    assert contents(output) == PAIR


def test_original_write_readback_failure_cannot_publish(tmp_path, monkeypatch):
    output = tmp_path / 'report'
    original_read = retention._read

    def corrupt_read(path):
        raw = original_read(path)
        return raw + b'wrong' if path.name == 'report.md' else raw

    monkeypatch.setattr(retention, '_read', corrupt_read)
    with pytest.raises(ValueError, match='retained bytes failed readback'):
        retention._publish_report_files(output, PAIR)
    assert not output.exists()
    assert_no_staging(tmp_path)


def make_target(output, kind):
    if kind == 'empty-directory':
        output.mkdir()
    elif kind == 'nonempty-directory':
        output.mkdir()
        (output / 'existing.txt').write_bytes(b'original retained result')
    elif kind == 'file':
        output.write_bytes(b'original retained file')
    else:
        destination = output.parent / 'symlink-destination'
        if kind == 'symlink':
            destination.mkdir()
            (destination / 'original.txt').write_bytes(b'original symlink referent')
        output.symlink_to(destination, target_is_directory=True)


def target_snapshot(output):
    stat = output.lstat()
    if output.is_symlink():
        raw = contents(output) if output.exists() else None
        return stat.st_ino, os.readlink(output), raw
    return stat.st_ino, contents(output) if output.is_dir() else output.read_bytes()


TARGET_KINDS = ['empty-directory', 'nonempty-directory', 'file', 'symlink', 'dangling-symlink']


@pytest.mark.parametrize('kind', TARGET_KINDS)
def test_existing_target_is_never_changed_or_staged(tmp_path, kind):
    output = tmp_path / 'report'
    make_target(output, kind)
    before = target_snapshot(output)

    def unexpected_write(*args):
        pytest.fail('existing target must be rejected before staging writes')

    with pytest.raises((FileExistsError, ValueError)):
        retention._publish_report_files(output, PAIR, write_file=unexpected_write)
    assert target_snapshot(output) == before
    assert_no_staging(tmp_path)


@requires_publication
@pytest.mark.parametrize('kind', TARGET_KINDS)
def test_competitor_target_created_immediately_before_rename_is_preserved(
        tmp_path, monkeypatch, kind):
    output = tmp_path / 'report'
    original_rename = retention._rename_new_directory
    before = []

    def compete(source, destination):
        assert contents(source) == PAIR
        make_target(destination, kind)
        before.append(target_snapshot(destination))
        original_rename(source, destination)

    monkeypatch.setattr(retention, '_rename_new_directory', compete)
    with pytest.raises(OSError):
        retention._publish_report_files(output, PAIR)
    assert target_snapshot(output) == before[0]
    assert_no_staging(tmp_path)


@requires_publication
def test_two_publishers_race_with_exactly_one_complete_winner(tmp_path, monkeypatch):
    output = tmp_path / 'report'
    barrier = threading.Barrier(2, timeout=10)
    original_rename = retention._rename_new_directory
    pairs = [{name: raw + str(index).encode() for name, raw in PAIR.items()}
             for index in range(2)]

    def synchronized_rename(source, destination):
        assert set(contents(source)) == set(PAIR)
        barrier.wait()
        original_rename(source, destination)

    def publish(index):
        try:
            retention._publish_report_files(output, pairs[index])
            return index, 'published'
        except FileExistsError:
            return index, 'already-exists'

    monkeypatch.setattr(retention, '_rename_new_directory', synchronized_rename)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(publish, range(2)))
    winners = [index for index, status in outcomes if status == 'published']
    assert len(winners) == 1
    assert sum(status == 'already-exists' for _, status in outcomes) == 1
    assert contents(output) == pairs[winners[0]]
    assert_no_staging(tmp_path)


@pytest.mark.parametrize('unsupported', ['host', 'libc-symbol', 'ENOSYS', 'EOPNOTSUPP'])
def test_unsupported_atomic_primitive_fails_closed_without_rename_fallback(
        tmp_path, monkeypatch, unsupported):
    output = tmp_path / 'report'

    def forbidden_rename(*args, **kwargs):
        pytest.fail('an unsupported atomic primitive must not fall back to os.rename')

    monkeypatch.setattr(retention.os, 'rename', forbidden_rename)
    if unsupported == 'host':
        monkeypatch.setattr(retention.sys, 'platform', 'darwin')
        expected = NotImplementedError
    else:
        monkeypatch.setattr(retention.sys, 'platform', 'linux')
        if unsupported == 'libc-symbol':
            library = SimpleNamespace()
            expected = NotImplementedError
        else:
            def unavailable_rename(*args):
                retention.ctypes.set_errno(getattr(errno, unsupported))
                return -1
            library = SimpleNamespace(renameat2=unavailable_rename)
            expected = OSError
        monkeypatch.setattr(retention.ctypes, 'CDLL', lambda *a, **k: library)
    with pytest.raises(expected):
        retention._publish_report_files(output, PAIR)
    assert not output.exists()
    assert_no_staging(tmp_path)


@pytest.mark.parametrize('mutation', ['extra-file', 'missing-file'])
def test_staging_inventory_mismatch_is_not_published(tmp_path, mutation):
    output = tmp_path / 'report'

    def wrong_inventory(path, raw):
        retention._write(path, raw)
        if path.name == 'report.md':
            if mutation == 'extra-file':
                (path.parent / 'unexpected.txt').write_bytes(b'extra')
            else:
                (path.parent / 'report.json').unlink()

    with pytest.raises(ValueError, match='inventory differs|regular retained file'):
        retention._publish_report_files(output, PAIR, write_file=wrong_inventory)
    assert not output.exists()
    assert_no_staging(tmp_path)


REAL_CASES = ['census-provider-failure', 'census-ir-reference',
              'comparison-accelink', 'comparison-xingsen']


def retained_cli(case, output):
    """Use exact retained inputs/sources, never synthetic replacements or network."""
    if case.startswith('census-'):
        module = 'decision_kernel.runtime.reviewed_activity_census'
        stem = case.removeprefix('census-')
        root = ROOT / 'docs/readings/c-reviewed-activity-boundaries-2026-09-30'
        source_names = ({'capture': 'provider-capture.json',
                         'activity': 'provider-activity.body', 'reports': 'provider-reports.body'}
                        if stem == 'provider-failure' else {'ir': 'ir-reconciliation.md'})
        input_path = root / (stem + '-input.json')
        expected_json = root / (stem + '-report.json')
        expected_md = root / (stem + '-report.md')
        prefix = 'census'
    else:
        module = 'decision_kernel.runtime.research_comparison'
        stem = case.removeprefix('comparison-')
        root = ROOT / 'docs/readings' / ('c-longitudinal-' + stem + '-2026-09-30')
        input_path = root / 'input.json'
        value = json.loads(input_path.read_bytes())
        source_names = {source['id']: source['id'] + '-' + Path(source['path']).name
                        for source in value['sources']}
        expected_json, expected_md = root / 'comparison.json', root / 'comparison.md'
        prefix = 'comparison'
    raw = input_path.read_bytes()
    arguments = [str(input_path), '--sha256', state.sha256(raw), '--output', str(output)]
    snapshots = {input_path: raw}
    for source_id, name in source_names.items():
        path = root / name
        arguments += ['--source', source_id + '=' + str(path)]
        snapshots[path] = path.read_bytes()
    expected = {prefix + '.json': (canonical_json(json.loads(expected_json.read_bytes())) + '\n').encode(),
                prefix + '.md': expected_md.read_bytes()}
    return module, arguments, expected, snapshots


def subprocess_environment():
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + environment.get('PYTHONPATH', '')
    return environment


def run_cli(module, arguments):
    return subprocess.run([sys.executable, '-m', module, *arguments], cwd=ROOT,
                          env=subprocess_environment(), capture_output=True, text=True, timeout=30)


INJECTED_CLI = r'''
import errno
import importlib
from pathlib import Path
import os
import sys
import time

module_name, mode, fail_on, marker = sys.argv[1:5]
module = importlib.import_module(module_name)
original_write = module._write
count = 0

def write(path, raw):
    global count
    count += 1
    if count == int(fail_on):
        with path.open('xb') as stream:
            stream.write(raw[:max(1, len(raw) // 2)])
            stream.flush()
            os.fsync(stream.fileno())
        if mode == 'kill':
            ready = Path(marker)
            pending = ready.with_suffix('.pending')
            pending.write_text(str(path), encoding='utf-8')
            os.replace(pending, ready)
            while True:
                time.sleep(60)
        raise OSError(errno.ENOSPC, 'injected real CLI report write failure')
    original_write(path, raw)

module._write = write
sys.argv = [module_name, *sys.argv[5:]]
module.main()
'''


@requires_publication
@pytest.mark.parametrize('case', REAL_CASES)
@pytest.mark.parametrize('fail_on', [1, 2])
def test_real_retained_cli_write_failure_has_no_partial_result_and_can_retry(
        tmp_path, case, fail_on):
    output = tmp_path / 'report'
    module, arguments, expected, snapshots = retained_cli(case, output)
    failed = subprocess.run(
        [sys.executable, '-c', INJECTED_CLI, module, 'failure', str(fail_on), '-', *arguments],
        cwd=ROOT, env=subprocess_environment(), capture_output=True, text=True, timeout=30)
    assert failed.returncode != 0
    assert 'injected real CLI report write failure' in failed.stderr
    assert not output.exists()
    assert_no_staging(tmp_path)
    assert {path: path.read_bytes() for path in snapshots} == snapshots

    retried = run_cli(module, arguments)
    assert retried.returncode == 0, retried.stderr
    assert contents(output) == expected
    refused = run_cli(module, arguments)
    assert refused.returncode != 0
    assert contents(output) == expected
    assert {path: path.read_bytes() for path in snapshots} == snapshots
    assert_no_staging(tmp_path)


@requires_publication
@pytest.mark.parametrize('case', REAL_CASES)
def test_real_cli_killed_during_second_staging_write_leaves_no_target_and_retry_works(
        tmp_path, case):
    output = tmp_path / 'report'
    marker = tmp_path / 'staging-ready'
    module, arguments, expected, snapshots = retained_cli(case, output)
    process = subprocess.Popen(
        [sys.executable, '-c', INJECTED_CLI, module, 'kill', '2', str(marker), *arguments],
        cwd=ROOT, env=subprocess_environment(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True)
    try:
        deadline = time.monotonic() + 20
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists(), 'child never reached its second partial staging write'
        staged_path = Path(marker.read_text(encoding='utf-8'))
        assert staged_path.is_file()
        assert set(contents(staged_path.parent)) == set(expected)
        assert staged_path.read_bytes() != expected[staged_path.name]
        assert not output.exists()
        process.kill()
        process.communicate(timeout=10)
        assert process.returncode != 0
        if os.name == 'posix':
            assert process.returncode == -signal.SIGKILL
        assert not output.exists()
        # SIGKILL cannot run TemporaryDirectory cleanup. A retry must neither
        # consume nor remove the interrupted run's private retained staging.
        orphans = list(tmp_path.glob('.kernel-report-*'))
        assert len(orphans) == 1
        orphan_contents = contents(staged_path.parent)
        retried = run_cli(module, arguments)
        assert retried.returncode == 0, retried.stderr
        assert contents(output) == expected
        assert list(tmp_path.glob('.kernel-report-*')) == orphans
        assert contents(staged_path.parent) == orphan_contents
        assert {path: path.read_bytes() for path in snapshots} == snapshots
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
