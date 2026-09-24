"""Reuse one exact PR's full CI after a clean main merge; otherwise run full CI.

This is an Actions-only read adapter, not a test cache or a history scanner.
Downloaded diagnostics are parsed as data, never extracted or executed.
"""
from __future__ import annotations

from contextlib import contextmanager
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
          'tests/test_ci_merge_reuse.py', 'pyproject.toml',
          '.github/workflows/ci-contracts-v2.yml', '.github/ci-v2-research.txt',
          'tests/test_ci_v2.py')
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


def api(root: Path, path: str) -> dict | list:
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


def passed_test_set(collection_text: str, junit_xml: bytes) -> int:
    """Check only set completeness and failures, not scope/provenance/authority.

    Both legacy full evidence and a v2 domain reuse this same existing check.
    A complete domain is NOT a full repository proof.
    """
    collection = [line for line in collection_text.splitlines()
                  if line.startswith('tests/') and '::' in line]
    expected = set()
    # Reuse the installed pytest writer's address conversion: params may contain '::'.
    from _pytest.junitxml import mangle_test_address
    for node in collection:
        names = mangle_test_address(node)
        expected.add(('.'.join(names[:-1]), names[-1]))
    require(bool(expected) and len(expected) == len(collection), 'COLLECTION_IDENTITY')
    root = ET.fromstring(junit_xml)
    suites = root.findall('.//testsuite')
    cases = root.findall('.//testcase')
    require(bool(suites) and all(int(s.get(k, '-1')) == 0 for s in suites
            for k in ('errors', 'failures', 'skipped')), 'FULL_SUITE_NOT_PASSED')
    require(all(root.find('.//' + tag) is None for tag in ('failure', 'error', 'skipped')),
            'TESTCASE_NOT_PASSED')
    actual = {(c.attrib['classname'], c.attrib['name']) for c in cases}
    require(len(actual) == len(cases) and actual == expected, 'COLLECTION_JUNIT_MISMATCH')
    return len(actual)


@contextmanager
def verified_archive(raw: bytes, artifact: dict):
    """Reuse the same bounded, digest-checked ZIP reader; never extract code."""
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
        yield archive


def full_evidence(raw: bytes, artifact: dict, run: dict, current: dict) -> int:
    with verified_archive(raw, artifact) as archive:
        identity = dict(line.split('=', 1) for line in archive.read('identity.txt').decode().splitlines())
        require(identity['code_sha'] == run['head_sha'] and identity['event'] == 'pull_request'
                and identity['run_id'] == str(run['id']) and identity['attempt'] == '1', 'PR_IDENTITY')
        scope = json.loads(archive.read('scope.json'))
        require(scope['scope'] == 'full' and scope['code_sha'] == run['head_sha']
                and scope['event'] == 'pull_request', 'NOT_FULL_PR_SCOPE')
        proof = json.loads(archive.read('merge-reuse.json'))
        require(proof['reuse'] is False and proof['reason'] == 'PR_ALWAYS_FULL', 'INHERITED_RESULT')
        require(json.loads(archive.read('environment.json')) == current, 'ENVIRONMENT_CHANGED')
        collection, xml = archive.read('collection.txt').decode(), archive.read('pytest.xml')
        partitioned = scope.get('full_suite') == 'EXECUTED_PARTITIONED_V2'
        require(('partition.json' in archive.namelist()) == partitioned, 'PARTITION_MARKER')
        if partitioned:
            plan = json.loads(archive.read('partition.json'))
            rebuilt = partition_junit(collection, plan['paths'], archive.read('remaining.xml'),
                archive.read('domain-source.zip'), plan['artifact'], identity, current)
            require(rebuilt == xml, 'PARTITION_RESULT_CHANGED')
        return passed_test_set(collection, xml)


def partition_nodes(collection: str, paths: list[str]) -> tuple[list[str], list[str]]:
    """Partition a full collection by explicit migrated files, not inferred impact."""
    require(isinstance(paths, list) and bool(paths) and len(paths) == len(set(paths)), 'DOMAIN_PATHS')
    require(all(isinstance(p, str) and re.fullmatch(r'tests/(?:[A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py', p)
                for p in paths), 'DOMAIN_PATHS')
    nodes = [n for n in collection.splitlines() if n.startswith('tests/') and '::' in n]
    require(bool(nodes) and len(nodes) == len(set(nodes)), 'COLLECTION_IDENTITY')
    domain = [n for n in nodes if n.split('::', 1)[0] in paths]
    remaining = [n for n in nodes if n.split('::', 1)[0] not in paths]
    require({n.split('::', 1)[0] for n in domain} == set(paths), 'DOMAIN_PATH_HAS_NO_TESTS')
    require(bool(remaining), 'NO_REMAINING_TESTS')
    return domain, remaining


def partition_junit(collection: str, paths: list[str], remaining_xml: bytes,
                    domain_raw: bytes, artifact: dict, identity: dict, current: dict) -> bytes:
    """Full proof = fresh disjoint executions in this run; no historical fallback."""
    domain, remaining = partition_nodes(collection, paths)
    passed_test_set('\n'.join(remaining), remaining_xml)
    require(type(artifact.get('id')) is int and artifact['id'] > 0
            and artifact.get('expired') is False
            and artifact['name'] == f"kernel-ci-v2-{identity['run_id']}-{identity['attempt']}"
            and str(artifact['workflow_run']['id']) == identity['run_id']
            and artifact['workflow_run']['head_sha'] == identity['code_sha'], 'DOMAIN_ARTIFACT_IDENTITY')
    with verified_archive(domain_raw, artifact) as z:
        source = dict(line.split('=', 1) for line in z.read('identity.txt').decode().splitlines())
        require(all(source.get(k) == identity[k] for k in ('code_sha', 'event', 'run_id', 'attempt'))
                and source.get('scope') == 'research-continuity-v2', 'DOMAIN_EXECUTION_IDENTITY')
        environment = json.loads(z.read('environment.json'))
        require({k: v for k, v in environment.items() if k != 'packages'} ==
                {k: v for k, v in current.items() if k != 'packages'}, 'DOMAIN_ENVIRONMENT')
        # The lighter installation may omit packages, never silently change shared versions.
        require(bool(environment['packages']) and all(current['packages'].get(k) == v
                for k, v in environment['packages'].items()), 'DOMAIN_PACKAGES')
        result = json.loads(z.read('domain-result.json'))
        require(result['scope'] == 'research-continuity-v2' and result['complete_domain'] == 'PASS'
                and result['code_sha'] == identity['code_sha'] and result['merge_eligible'] is False
                and result['full_suite'] == 'NOT_RUN_DOMAIN_ONLY'
                and type(result['test_count']) is int and result['test_count'] == len(domain), 'DOMAIN_RESULT')
        domain_xml = z.read('domain.xml')
        passed_test_set(z.read('domain-collection.txt').decode(), domain_xml)
        passed_test_set('\n'.join(domain), domain_xml)
    # Preserve original testcase IDs, failures and measured suite times. This is
    # explicitly a multi-job JUnit aggregate, never a fictitious single pytest run.
    combined = ET.Element('testsuites')
    for label, xml in (('research-continuity-v2', domain_xml), ('remaining-current-contracts', remaining_xml)):
        for suite in ET.fromstring(xml).findall('.//testsuite'):
            suite.set('name', label)
            combined.append(suite)
    combined_xml = ET.tostring(combined, encoding='utf-8')
    passed_test_set(collection, combined_xml)  # Union complete; duplicates fail.
    return combined_xml


def partition_operation(root: Path, out: Path, operation: str) -> None:
    identity = dict(line.split('=', 1) for line in (out / 'identity.txt').read_text().splitlines())
    require(git(root, 'rev-parse', 'HEAD') == identity['code_sha']
            and not command(root, 'git', 'diff', '--name-only', 'HEAD', '--'), 'CHECKOUT_CHANGED')
    paths = (root / '.github/ci-v2-research.txt').read_text().splitlines()
    collection = (out / 'collection.txt').read_text()
    partition_nodes(collection, paths)
    require(all((root / p).is_file() and not (root / p).is_symlink() for p in paths), 'DOMAIN_PATHS')
    if operation == 'partition':
        (out / 'remaining-args.txt').write_text(''.join('--ignore=' + p + '\n' for p in paths))
        return
    # Same run only. Missing, failed, truncated or foreign domain evidence fails;
    # do not rerun that domain in the old job to manufacture a green result.
    payload = api(root, f"actions/runs/{identity['run_id']}/artifacts?per_page=100")
    require(payload['total_count'] == len(payload['artifacts']), 'INCOMPLETE_ARTIFACT_LIST')
    candidates = [a for a in payload['artifacts']
                  if a['name'] == f"kernel-ci-v2-{identity['run_id']}-{identity['attempt']}"]
    require(len(candidates) == 1, 'NO_UNIQUE_DOMAIN_ARTIFACT')
    artifact = candidates[0]
    require(type(artifact.get('id')) is int and artifact['id'] > 0
            and artifact.get('expired') is False, 'DOMAIN_ARTIFACT_IDENTITY')
    raw = command(root, 'gh', 'api', f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip")
    current = json.loads((out / 'environment.json').read_text())
    xml = partition_junit(collection, paths, (out / 'remaining.xml').read_bytes(), raw, artifact, identity, current)
    (out / 'domain-source.zip').write_bytes(raw)
    (out / 'partition.json').write_text(json.dumps(dict(paths=paths, artifact=artifact), sort_keys=True, indent=2) + '\n')
    (out / 'pytest.xml').write_bytes(xml)
    scope = json.loads((out / 'scope.json').read_text())
    require(scope['scope'] == 'full' and scope['code_sha'] == identity['code_sha']
            and scope['event'] == identity['event'], 'NOT_FULL_PR_SCOPE')
    scope['full_suite'] = 'EXECUTED_PARTITIONED_V2'
    (out / 'scope.json').write_text(json.dumps(scope, sort_keys=True, indent=2) + '\n')
    print('FULL_SUITE=EXECUTED_PARTITIONED_V2 TESTS=' + str(passed_test_set(collection, xml)))


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
        # Run.pull_requests can be empty after merge. Query the exact commit's
        # native association instead; never guess from a branch or commit message.
        linked = read(root, f'commits/{head}/pulls?per_page=100')
        require(isinstance(linked, list) and len(linked) < 100, 'INCOMPLETE_PR_LIST')
        prs = [p for p in linked if p['merge_commit_sha'] == head
               and p['head']['sha'] == pr_head and p['base']['sha'] == base
               and p['base']['ref'] == 'main']
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
    parser.add_argument('--operation', choices=('select', 'partition', 'assemble'), default='select')
    args = parser.parse_args()
    root = Path.cwd()
    if args.operation != 'select':
        partition_operation(root, args.report_dir, args.operation)
        return
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
