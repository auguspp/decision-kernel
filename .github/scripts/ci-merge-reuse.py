"""Reuse one exact PR's full CI after a clean main merge; otherwise run full CI.

This is an Actions-only read adapter, not a test cache or a history scanner.
Downloaded diagnostics are parsed as data, never extracted or executed.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

REPO = 'auguspp/decision-kernel'
WORKFLOW = '.github/workflows/ci.yml'
POLICY = (WORKFLOW, '.github/scripts/ci-content-scope.py',
          '.github/scripts/ci-merge-reuse.py', 'tests/test_ci_contract.py',
          'tests/test_ci_content_scope.py', 'tests/test_ci_resource_efficiency.py',
          'tests/test_ci_merge_reuse.py', 'pyproject.toml')
SHA = re.compile(r'[0-9a-f]{40}')
MAX_ZIP = 8 * 1024 * 1024
MAX_EXPANDED = 32 * 1024 * 1024


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def command(root: Path, *args: str) -> bytes:
    return subprocess.run(args, cwd=root, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=30).stdout


def git(root: Path, *args: str) -> str:
    return command(root, 'git', *args).decode().strip()


def api(root: Path, path: str) -> dict:
    return json.loads(command(root, 'gh', 'api', f'repos/{REPO}/{path}'))


def environment(root: Path, report_dir: Path, env: dict) -> dict:
    packages = json.loads((report_dir / 'packages.json').read_text())
    inventory = {re.sub(r'[-_.]+', '-', p['name']).lower(): p['version'] for p in packages}
    require(len(inventory) == len(packages), 'DUPLICATE_PACKAGE_NAMES')
    return dict(tree=git(root, 'rev-parse', 'HEAD^{tree}'), python=sys.version,
                machine=platform.machine(), platform=sys.platform,
                image_os=env.get('ImageOS'), image_version=env.get('ImageVersion'),
                runner_os=env.get('RUNNER_OS'), runner_arch=env.get('RUNNER_ARCH'),
                packages=inventory)


def latest_pr_run(payload: dict, head: str) -> dict:
    rows = payload['workflow_runs']
    require(payload['total_count'] == len(rows), 'INCOMPLETE_RUN_LIST')
    require(bool(rows), 'NO_PR_RUN')
    # Do not filter away a newer failed, foreign, or otherwise invalid candidate.
    require(all(type(r.get('id')) is int and r['id'] > 0 for r in rows), 'INVALID_RUN_ID')
    run = max(rows, key=lambda r: r['id'])
    require(run['head_sha'] == head and run['event'] == 'pull_request'
            and run['name'] == 'kernel-tests' and run['path'] == WORKFLOW
            and run['head_repository']['full_name'] == REPO
            and type(run['run_attempt']) is int and run['run_attempt'] == 1
            and run['status'] == 'completed' and run['conclusion'] == 'success',
            'PR_RUN_NOT_OWNED_FIRST_SUCCESS')
    return run


def full_evidence(raw: bytes, artifact: dict, run: dict, current: dict) -> int:
    require(0 < len(raw) == artifact['size_in_bytes'] <= MAX_ZIP, 'ARCHIVE_SIZE')
    require('sha256:' + hashlib.sha256(raw).hexdigest() == artifact['digest'], 'ARCHIVE_DIGEST')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)) and 0 < len(names) <= 128, 'ARCHIVE_NAMES')
        require(sum(i.file_size for i in infos) <= MAX_EXPANDED, 'ARCHIVE_EXPANDED_SIZE')
        require(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                    and '\\' not in n for n in names), 'ARCHIVE_PATH')
        require(archive.testzip() is None, 'ARCHIVE_CRC')
        identity = dict(line.split('=', 1) for line in archive.read('identity.txt').decode().splitlines())
        require(identity['code_sha'] == run['head_sha'] and identity['event'] == 'pull_request'
                and identity['run_id'] == str(run['id']) and identity['attempt'] == '1', 'PR_IDENTITY')
        scope = json.loads(archive.read('scope.json'))
        require(scope['scope'] == 'full' and scope['code_sha'] == run['head_sha']
                and scope['event'] == 'pull_request', 'NOT_FULL_PR_SCOPE')
        proof = json.loads(archive.read('merge-reuse.json'))
        require(proof['reuse'] is False and proof['reason'] == 'PR_ALWAYS_FULL', 'INHERITED_RESULT')
        require(json.loads(archive.read('environment.json')) == current, 'ENVIRONMENT_CHANGED')
        collection = [line for line in archive.read('collection.txt').decode().splitlines()
                      if line.startswith('tests/') and '::' in line]
        expected = set()
        # Reuse the installed pytest writer's address conversion: params may contain '::'.
        from _pytest.junitxml import mangle_test_address
        for node in collection:
            names = mangle_test_address(node)
            expected.add(('.'.join(names[:-1]), names[-1]))
        require(bool(expected) and len(expected) == len(collection), 'COLLECTION_IDENTITY')
        root = ET.fromstring(archive.read('pytest.xml'))
        suites = root.findall('.//testsuite')
        cases = root.findall('.//testcase')
        require(bool(suites) and all(int(s.get(k, '-1')) == 0 for s in suites
                for k in ('errors', 'failures', 'skipped')), 'FULL_SUITE_NOT_PASSED')
        require(all(root.find('.//' + tag) is None for tag in ('failure', 'error', 'skipped')),
                'TESTCASE_NOT_PASSED')
        actual = {(c.attrib['classname'], c.attrib['name']) for c in cases}
        require(len(actual) == len(cases) and actual == expected, 'COLLECTION_JUNIT_MISMATCH')
        return len(actual)


def select(root: Path, report_dir: Path, env: dict, current: dict, *, read=api, download=None) -> dict:
    result = dict(reuse=False, reason='NOT_FIRST_MAIN_MERGE',
                  full_suite='PENDING_FULL_EXECUTION', source=None)
    if env.get('GITHUB_EVENT_NAME') == 'pull_request':
        result['reason'] = 'PR_ALWAYS_FULL'
        return result
    if not (env.get('GITHUB_EVENT_NAME') == 'push' and env.get('GITHUB_REF') == 'refs/heads/main'
            and env.get('GITHUB_REPOSITORY') == REPO and env.get('GITHUB_RUN_ATTEMPT') == '1'):
        return result
    try:
        head, base = env['CI_CODE_SHA'], env['CI_BASE_SHA']
        require(SHA.fullmatch(head) and SHA.fullmatch(base), 'COMMIT_IDENTITY')
        require(git(root, 'rev-parse', 'HEAD') == head, 'CHECKOUT_CHANGED')
        require(not command(root, 'git', 'diff', '--name-only', 'HEAD', '--'), 'DIRTY_CHECKOUT')
        headers = git(root, 'cat-file', '-p', head).split('\n\n', 1)[0].splitlines()
        parents = [line.split()[1] for line in headers if line.startswith('parent ')]
        require(len(parents) == 2 and parents[0] == base, 'NOT_SINGLE_CLEAN_MERGE_PUSH')
        pr_head = parents[1]
        require(git(root, 'rev-parse', pr_head + '^{tree}') == current['tree'], 'MERGE_TREE_DIFFERS')
        require(not command(root, 'git', 'diff', '--name-only', base, head, '--', *POLICY), 'CI_POLICY_CHANGED')
        require(all(current.get(k) for k in ('image_os', 'image_version', 'runner_os', 'runner_arch')),
                'ENVIRONMENT_IDENTITY_MISSING')
        query = f'actions/workflows/ci.yml/runs?head_sha={pr_head}&event=pull_request&per_page=100'
        run = latest_pr_run(read(root, query), pr_head)
        prs = [p for p in run['pull_requests'] if p['head']['sha'] == pr_head
               and p['base']['sha'] == base and p['base']['ref'] == 'main']
        require(len(prs) == 1, 'PR_MERGE_ASSOCIATION')
        pr = read(root, 'pulls/' + str(prs[0]['number']))
        require(pr['merged'] is True and pr['merge_commit_sha'] == head
                and pr['head']['sha'] == pr_head and pr['head']['repo']['full_name'] == REPO
                and pr['base']['ref'] == 'main' and pr['base']['repo']['full_name'] == REPO,
                'PR_NOT_THIS_MERGE')
        payload = read(root, f"actions/runs/{run['id']}/artifacts?per_page=100")
        require(payload['total_count'] == len(payload['artifacts']), 'INCOMPLETE_ARTIFACT_LIST')
        matches = [a for a in payload['artifacts'] if a['name'] == f"kernel-ci-{run['id']}-1"]
        require(len(matches) == 1, 'NO_UNIQUE_PR_ARTIFACT')
        artifact = matches[0]
        require(artifact['expired'] is False and type(artifact['id']) is int
                and artifact['id'] > 0 and 0 < artifact['size_in_bytes'] <= MAX_ZIP
                and artifact['workflow_run']['id'] == run['id']
                and artifact['workflow_run']['head_sha'] == pr_head, 'ARTIFACT_IDENTITY')
        raw = (download(root, artifact['id']) if download else
               command(root, 'gh', 'api', f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip"))
        count = full_evidence(raw, artifact, run, current)
        require(latest_pr_run(read(root, query), pr_head)['id'] == run['id'], 'PR_RUN_CHANGED_DURING_READ')
        result.update(reuse=True, reason='EXACT_PR_FULL_SUITE_REUSED', full_suite='REUSED_NOT_RERUN',
                      source=dict(run_id=run['id'], pr=pr['number'], head_sha=pr_head,
                                  artifact_id=artifact['id'], digest=artifact['digest'],
                                  tree=current['tree'], test_count=count))
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError,
            AttributeError, ImportError, zipfile.BadZipFile, ET.ParseError, RuntimeError) as exc:
        # External error bodies may contain private information; retain only local codes.
        code = str(exc) if type(exc) is ValueError and re.fullmatch(r'[A-Z_]+', str(exc)) else type(exc).__name__
        result['reason'] = 'FULL_REQUIRED_' + code
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    current = environment(root, args.report_dir, os.environ)
    (args.report_dir / 'environment.json').write_text(json.dumps(current, sort_keys=True, indent=2) + '\n')
    report = select(root, args.report_dir, os.environ, current)
    (args.report_dir / 'merge-reuse.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    if report['reuse']:
        scope_path = args.report_dir / 'scope.json'
        scope = json.loads(scope_path.read_text())
        scope.update(scope='merge_reuse', full_suite='REUSED_NOT_RERUN', full_suite_source=report['source'])
        scope_path.write_text(json.dumps(scope, sort_keys=True, indent=2) + '\n')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('reuse=' + str(report['reuse']).lower() + '\n')
    print('CI_MERGE_REUSE=' + str(report['reuse']).lower() + ' REASON=' + report['reason'])


if __name__ == '__main__':
    main()
