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
