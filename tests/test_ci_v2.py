"""V2 domain wiring; retire with this lane, not with the retained research."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import textwrap
import tomllib
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARGS = '.github/ci-v2-research.txt'
WORKFLOW = ROOT / '.github/workflows/ci-contracts-v2.yml'


def test_domain_targets_are_current_unique_files_not_hidden_selection_rules():
    # A retired/renamed module must update the same native pytest argument file.
    paths = (ROOT / ARGS).read_text().splitlines()
    assert paths and len(paths) == len(set(paths))
    for path in paths:
        assert path.startswith('tests/test_') and path.endswith('.py')
        assert '..' not in Path(path).parts and (ROOT / path).is_file()
        assert not (ROOT / path).is_symlink()
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
    extra = project['optional-dependencies']
    assert extra['ci-contracts'] == [d for d in extra['dev'] if d.startswith('pytest==')]
    # Every v2 policy edit must invalidate legacy main-merge reuse as well.
    policy = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))['POLICY']
    assert {ARGS, str(WORKFLOW.relative_to(ROOT)), 'tests/test_ci_v2.py'} <= set(policy)


@pytest.mark.parametrize('outcome', ['pass', 'fail', 'missing'])
def test_actual_native_argument_file_command_propagates_outcome(tmp_path, outcome):
    workflow = WORKFLOW.read_text()
    step = workflow.split('      - name: Test research continuity contracts\n', 1)[1].split('      - name:', 1)[0]
    script = textwrap.dedent(step.split('        run: |\n', 1)[1])
    (tmp_path / '.github').mkdir()
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'pytest.ini').write_text('[pytest]\n')
    (tmp_path / ARGS).write_text('tests/test_contract.py\n')
    if outcome != 'missing':
        (tmp_path / 'tests/test_contract.py').write_text('def test_current_contract():\n    assert ' + str(outcome == 'pass') + '\n')
    # Deliberately outside this domain: a green domain is not a full-suite proof.
    (tmp_path / 'tests/test_other_domain.py').write_text('def test_other():\n    assert False\n')
    out = tmp_path / 'reports'; out.mkdir()
    env = {**os.environ, 'V2_REPORT_DIR': str(out), 'PYTEST_ADDOPTS': '',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
    result = subprocess.run(['bash', '-c', script], cwd=tmp_path, env=env,
                            capture_output=True, timeout=30)
    assert result.returncode == {'pass': 0, 'fail': 1, 'missing': 4}[outcome], result.stdout + result.stderr
    assert (out / 'domain.log').is_file()
    assert not (out / 'pytest.xml').exists() and not (out / 'collection.txt').exists()
    if outcome != 'missing':
        cases = ET.parse(out / 'domain.xml').getroot().findall('.//testcase')
        assert len(cases) == 1 and cases[0].get('name') == 'test_current_contract'
        assert (cases[0].find('failure') is not None) == (outcome == 'fail')


def test_shared_result_check_rejects_missing_duplicate_and_skipped_domain_tests():
    check = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))['passed_test_set']
    collection = 'tests/test_contract.py::test_one\n1 test collected\n'
    case = '<testcase classname="tests.test_contract" name="test_one"/>'
    def xml(body):
        return ('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">' + body + '</testsuite></testsuites>').encode()
    assert check(collection, xml(case)) == 1
    for body in ('', case + case, case.replace('test_one', 'test_other'),
                 case.replace('/>', '><skipped/></testcase>')):
        with pytest.raises(ValueError):
            check(collection, xml(body))
    with pytest.raises(ValueError):
        check('', xml(case))


# Formal responsibility transfer: these tests leave with partitioned execution.
def _partition_fixture():
    import hashlib
    import io
    import json
    import zipfile
    reader = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))
    identity = dict(code_sha='a' * 40, event='pull_request', run_id='123', attempt='1')
    environment = dict(tree='b' * 40, python='synthetic', machine='x86_64', platform='linux',
                       image_os='ubuntu', image_version='synthetic', runner_os='Linux',
                       runner_arch='X64', packages={'pytest': 'synthetic'})
    paths = ['tests/test_domain.py']
    collection = 'tests/test_domain.py::test_one\ntests/test_other.py::test_two\n'
    def xml(module, name):
        return (f'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0" time="1">'
                f'<testcase classname="tests.{module}" name="{name}"/></testsuite></testsuites>').encode()
    files = {'identity.txt': ''.join(k + '=' + v + '\n' for k, v in identity.items()) + 'scope=research-continuity-v2\n',
             'environment.json': json.dumps(environment),
             'domain-result.json': json.dumps(dict(scope='research-continuity-v2', complete_domain='PASS',
                 code_sha=identity['code_sha'], merge_eligible=False, full_suite='NOT_RUN_DOMAIN_ONLY', test_count=1)),
             'domain-collection.txt': collection.splitlines()[0] + '\n',
             'domain.xml': xml('test_domain', 'test_one')}
    def pack(files):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, body in files.items(): z.writestr(name, body)
        raw = out.getvalue()
        return raw, dict(id=9, name='kernel-ci-v2-123-1', expired=False, size_in_bytes=len(raw),
            digest='sha256:' + hashlib.sha256(raw).hexdigest(), workflow_run={'id': 123, 'head_sha': 'a' * 40})
    return reader, identity, environment, paths, collection, files, xml('test_other', 'test_two'), pack


def test_full_union_is_disjoint_same_run_and_preserves_reader_qualification():
    import json
    from copy import deepcopy
    reader, identity, environment, paths, collection, files, remaining, pack = _partition_fixture()
    raw, artifact = pack(files)
    combine = reader['partition_junit']
    merged = combine(collection, paths, remaining, raw, artifact, identity, environment)
    assert reader['passed_test_set'](collection, merged) == 2
    assert len(ET.fromstring(merged).findall('testsuite')) == 2
    assert files['domain.xml'] != merged  # Domain alone never becomes a full report.
    # Smaller installs are allowed; shared versions and actual runtime identity are not guessed.
    larger = deepcopy(environment); larger['packages']['unused-in-domain'] = '1'
    assert combine(collection, paths, remaining, raw, artifact, identity, larger) == merged
    for field in ('code_sha', 'event', 'run_id', 'attempt'):
        damaged = {**files, 'identity.txt': files['identity.txt'].replace(identity[field], 'wrong')}
        r, a = pack(damaged)
        with pytest.raises(ValueError): combine(collection, paths, remaining, r, a, identity, environment)
    for field in ('tree', 'python', 'image_version', 'packages'):
        wrong = deepcopy(environment); wrong[field] = {'pytest': 'wrong'} if field == 'packages' else 'wrong'
        r, a = pack({**files, 'environment.json': json.dumps(wrong)})
        with pytest.raises(ValueError): combine(collection, paths, remaining, r, a, identity, environment)
    for update in ({'test_count': True}, {'complete_domain': 'FAIL'}, {'merge_eligible': True}, {'scope': 'full'}):
        wrong = {**json.loads(files['domain-result.json']), **update}
        r, a = pack({**files, 'domain-result.json': json.dumps(wrong)})
        with pytest.raises(ValueError): combine(collection, paths, remaining, r, a, identity, environment)
    for bad_paths in ([], paths * 2, ['tests/test_deleted.py'], ['../tests/test_domain.py']):
        with pytest.raises(ValueError): combine(collection, bad_paths, remaining, raw, artifact, identity, environment)
    for bad_remaining in (files['domain.xml'], remaining.replace(b'/>', b'><failure/></testcase>', 1)):
        with pytest.raises(ValueError): combine(collection, paths, bad_remaining, raw, artifact, identity, environment)
    for update in ({'expired': True}, {'id': False}, {'name': 'kernel-ci-v2-122-1'}, {'digest': 'sha256:bad'}):
        with pytest.raises(ValueError): combine(collection, paths, remaining, raw, {**artifact, **update}, identity, environment)
    outer = {'identity.txt': ''.join(k + '=' + v + '\n' for k, v in identity.items()),
        'environment.json': json.dumps(environment),
        'scope.json': json.dumps(dict(scope='full', code_sha='a' * 40, event='pull_request', full_suite='EXECUTED_PARTITIONED_V2')),
        'merge-reuse.json': json.dumps(dict(reuse=False, reason='PR_ALWAYS_FULL')),
        'partition.json': json.dumps(dict(paths=paths, artifact=artifact)),
        'collection.txt': collection, 'remaining.xml': remaining, 'domain-source.zip': raw, 'pytest.xml': merged}
    r, a = pack(outer)
    assert reader['full_evidence'](r, a, dict(id=123, head_sha='a' * 40), environment) == 2
    for key in ('partition.json', 'domain-source.zip', 'remaining.xml'):
        damaged = dict(outer); del damaged[key]; r, a = pack(damaged)
        with pytest.raises((ValueError, KeyError)):
            reader['full_evidence'](r, a, dict(id=123, head_sha='a' * 40), environment)
    for damaged in ({**outer, 'pytest.xml': merged + b' '},
                    {**outer, 'domain-source.zip': raw + b'changed'}):
        r, a = pack(damaged)
        with pytest.raises(ValueError): reader['full_evidence'](r, a, dict(id=123, head_sha='a' * 40), environment)


def test_native_remaining_execution_keeps_tests_outside_the_domain_and_their_failures(tmp_path):
    # Actual pytest consumes --ignore arguments, but the full collection still owns both files.
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'pytest.ini').write_text('[pytest]\n')
    (tmp_path / 'tests/test_domain.py').write_text('def test_one():\n    assert True\n')
    (tmp_path / 'tests/test_other.py').write_text('def test_two():\n    assert False\n')
    (tmp_path / 'remaining.txt').write_text('--ignore=tests/test_domain.py\n')
    env = {**os.environ, 'PYTEST_ADDOPTS': '', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
    collected = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30)
    assert collected.returncode == 0
    check = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))
    domain, remaining = check['partition_nodes'](collected.stdout, ['tests/test_domain.py'])
    assert domain == ['tests/test_domain.py::test_one'] and remaining == ['tests/test_other.py::test_two']
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '@remaining.txt', '--junitxml=remaining.xml'],
        cwd=tmp_path, env=env, capture_output=True, timeout=30)
    assert result.returncode == 1
    cases = ET.parse(tmp_path / 'remaining.xml').getroot().findall('.//testcase')
    assert len(cases) == 1 and cases[0].get('name') == 'test_two' and cases[0].find('failure') is not None
