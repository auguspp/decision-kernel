"""Thin I/O around native matrix/needs and pytest-split. No scheduler or selector."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
R = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))
require = R['require']
FIELDS = ('code_sha', 'event', 'run_id', 'attempt')
# Restore data only to fixed report names; never extract or execute archive paths.
PLAN_FILES = ('identity.txt', 'scope.json', 'environment.json', 'packages.json',
              'collection.txt', 'remaining-args.txt', 'durations-hint.json', 'constraints.txt',
              'merge-reuse.json', 'main-smoke.xml', 'main-smoke.log', 'content-check.json',
              'content-check.log', 'content-tests.log', 'draft-feedback.json',
              'draft-feedback.xml', 'draft-feedback.log', 'python.txt', 'cpu-count.txt')


def identity() -> dict:
    return dict(code_sha=os.environ['CI_CODE_SHA'], event=os.environ['GITHUB_EVENT_NAME'],
                run_id=os.environ['GITHUB_RUN_ID'], attempt=os.environ['GITHUB_RUN_ATTEMPT'])


def json_write(path: Path, data) -> None:
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')


def artifact(raw_id: dict, name: str, rows=None) -> tuple[bytes, dict]:
    if rows is None:
        payload = R['api'](ROOT, f"actions/runs/{raw_id['run_id']}/artifacts?per_page=100")
        require(payload['total_count'] == len(payload['artifacts']), 'INCOMPLETE_ARTIFACT_LIST')
        rows = payload['artifacts']
    matches = [a for a in rows if a['name'] == name]
    require(len(matches) == 1, 'NO_UNIQUE_EXECUTION_ARTIFACT')
    a = matches[0]
    require(type(a['id']) is int and a['id'] > 0 and a['expired'] is False
            and str(a['workflow_run']['id']) == raw_id['run_id']
            and a['workflow_run']['head_sha'] == raw_id['code_sha'], 'ARTIFACT_IDENTITY')
    raw = R['command'](ROOT, 'gh', 'api', f"repos/{R['REPO']}/actions/artifacts/{a['id']}/zip")
    return raw, a


def restore(out: Path) -> dict:
    expected = identity()
    raw, a = artifact(expected, f"kernel-ci-plan-{expected['run_id']}-{expected['attempt']}")
    with R['verified_archive'](raw, a) as z:
        source = dict(line.split('=', 1) for line in z.read('identity.txt').decode().splitlines())
        require(all(source.get(k) == expected[k] for k in FIELDS), 'PREPARATION_IDENTITY')
        scope = json.loads(z.read('scope.json'))
        require(scope['code_sha'] == expected['code_sha'] and scope['event'] == expected['event'], 'PREPARATION_SCOPE')
        for name in PLAN_FILES:
            if name in z.namelist():
                (out / name).write_bytes(z.read(name))
    return scope


def durations(collection: str, xml: bytes) -> dict:
    from _pytest.junitxml import mangle_test_address
    cases = {(c.get('classname'), c.get('name')): float(c.get('time', '0'))
             for c in ET.fromstring(xml).findall('.//testcase')}
    result = {}
    for node in collection.splitlines():
        if node.startswith('tests/') and '::' in node:
            names = mangle_test_address(node)
            value = cases[('.'.join(names[:-1]), names[-1])]
            require(math.isfinite(value) and value >= 0, 'INVALID_DURATION')
            result[node] = value
    return result


def duration_hint() -> dict:
    """Optional exact-base timing data, at most one inherited PR hop; never a gate.

    Missing/expired/non-full sources just use pytest-split's equal-cost default.
    The hint never chooses whether a test runs; full union is independently checked.
    """
    try:
        scope = runpy.run_path(str(ROOT / '.github/scripts/ci-content-scope.py'))
        base = os.environ.get('CI_BASE_SHA', '')
        require(R['SHA'].fullmatch(base), 'BASE_UNKNOWN')
        run = scope['trusted_base'](scope['main_ci'](ROOT, base), base)
        require(run is not None, 'BASE_NOT_SUCCESSFUL')
        raw, meta = artifact(dict(run_id=str(run['id']), code_sha=base), f"kernel-ci-{run['id']}-1")
        for hop in range(2):
            with R['verified_archive'](raw, meta) as z:
                if 'durations.json' in z.namelist():
                    values = json.loads(z.read('durations.json'))
                    require(isinstance(values, dict) and len(values) <= 100000, 'INVALID_DURATION')
                    require(all(isinstance(k, str) and k.startswith('tests/') and '::' in k
                                and type(v) in (int, float) and math.isfinite(v) and v >= 0
                                for k, v in values.items()), 'INVALID_DURATION')
                    return values if any(values.values()) else {}
                if 'collection.txt' in z.namelist() and 'pytest.xml' in z.namelist():
                    return durations(z.read('collection.txt').decode(), z.read('pytest.xml'))
                require(hop == 0, 'NO_DURATION_SOURCE')
                source = json.loads(z.read('merge-reuse.json'))['source']
                source_id = dict(run_id=str(source['run_id']), code_sha=source['head_sha'])
            raw, meta = artifact(source_id, f"kernel-ci-{source['run_id']}-1")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, ImportError, RuntimeError,
            R['subprocess'].SubprocessError, R['zipfile'].BadZipFile, ET.ParseError):
        print('DURATION_HINT=UNAVAILABLE; all tests remain required')
    return {}


def prepare(out: Path) -> None:
    values = duration_hint()
    json_write(out / 'durations-hint.json', values)
    scope = json.loads((out / 'scope.json').read_text())['scope']
    if scope != 'full':
        return
    paths = (ROOT / '.github/ci-v2-research.txt').read_text().splitlines()
    R['partition_nodes']((out / 'collection.txt').read_text(), paths)
    require(all((ROOT / p).is_file() and not (ROOT / p).is_symlink() for p in paths), 'DOMAIN_PATHS')
    (out / 'remaining-args.txt').write_text(''.join('--ignore=' + p + '\n' for p in paths))
    packages = json.loads((out / 'environment.json').read_text())['packages']
    (out / 'constraints.txt').write_text(''.join(f'{k}=={v}\n' for k, v in sorted(packages.items())))


def shard_result(out: Path, group: int) -> None:
    require(group in (1, 2, 3, 4), 'SHARD_GROUP')
    count = R['passed_test_set']((out / 'selected-collection.txt').read_text(), (out / 'shard.xml').read_bytes())
    json_write(out / 'shard.json', dict(scope='remaining-shard-v2', group=group, splits=4,
        test_count=count, timing_sha256=hashlib.sha256((out / 'durations-hint.json').read_bytes()).hexdigest(),
        merge_eligible=False))


def check_needs(needs: dict) -> str:
    require(set(needs) == {'prepare', 'contracts-v2', 'remaining-v2'}, 'UNEXPECTED_JOBS')
    require(needs['prepare']['result'] == 'success', 'PREPARATION_FAILED')
    mode = needs['prepare']['outputs']['scope']
    require(mode in ('full', 'content', 'draft_feedback', 'merge_reuse'), 'UNKNOWN_SCOPE')
    expected = 'success' if mode == 'full' else 'skipped'
    require(all(needs[k]['result'] == expected for k in ('contracts-v2', 'remaining-v2')), 'REQUIRED_JOBS_NOT_PASSED')
    return mode


def finalize(out: Path, needs: dict) -> None:
    mode = check_needs(needs)  # A skipped/cancelled/failed prerequisite can never turn green.
    scope = restore(out)
    require(scope['scope'] == mode, 'PREPARATION_SCOPE')
    if mode != 'full':
        (out / 'durations.json').write_bytes((out / 'durations-hint.json').read_bytes())
        print('VALIDATED_SCOPE=' + mode)
        return
    expected = identity()
    current = json.loads((out / 'environment.json').read_text())
    collection = (out / 'collection.txt').read_text()
    paths = (ROOT / '.github/ci-v2-research.txt').read_text().splitlines()
    payload = R['api'](ROOT, f"actions/runs/{expected['run_id']}/artifacts?per_page=100")
    require(payload['total_count'] == len(payload['artifacts']), 'INCOMPLETE_ARTIFACT_LIST')
    suffix = f"{expected['run_id']}-{expected['attempt']}"
    sources = [artifact(expected, f'kernel-ci-shard-{g}-{suffix}', payload['artifacts']) for g in range(1, 5)]
    timing = hashlib.sha256((out / 'durations-hint.json').read_bytes()).hexdigest()
    remaining = R['matrix_remaining'](collection, paths, sources, expected, current, timing)
    domain, a = artifact(expected, f'kernel-ci-v2-{suffix}', payload['artifacts'])
    xml = R['partition_junit'](collection, paths, remaining, domain, a, expected, current)
    for group, (raw, _) in enumerate(sources, 1):
        (out / f'shard-{group}.zip').write_bytes(raw)
    (out / 'remaining.xml').write_bytes(remaining)
    (out / 'domain-source.zip').write_bytes(domain)
    json_write(out / 'partition.json', dict(paths=paths, artifact=a, shards=[a for _, a in sources], timing_sha256=timing))
    (out / 'pytest.xml').write_bytes(xml)
    json_write(out / 'durations.json', durations(collection, xml))
    scope['full_suite'] = 'EXECUTED_MATRIX_V2'
    json_write(out / 'scope.json', scope)
    print('FULL_SUITE=EXECUTED_MATRIX_V2 TESTS=' + str(R['passed_test_set'](collection, xml)))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('prepare', 'restore', 'shard-result', 'finalize'))
    p.add_argument('--report-dir', type=Path, required=True)
    p.add_argument('--group', type=int)
    args = p.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    require(R['git'](ROOT, 'rev-parse', 'HEAD') == os.environ['CI_CODE_SHA']
            and not R['command'](ROOT, 'git', 'diff', '--name-only', 'HEAD', '--'), 'CHECKOUT_CHANGED')
    if args.operation == 'prepare': prepare(args.report_dir)
    elif args.operation == 'restore': restore(args.report_dir)
    elif args.operation == 'shard-result': shard_result(args.report_dir, args.group)
    else: finalize(args.report_dir, json.loads(os.environ['CI_NEEDS']))


if __name__ == '__main__':
    main()
