"""Keep full CI coverage/failure semantics while reusing pytest-xdist.

The subprocess cases run the actual workflow Test script against one synthetic
local test. They never import project runtime or contact a provider.
"""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import textwrap
import tomllib
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ci.yml"


def _test_job() -> str:
    return WORKFLOW.read_text(encoding="utf-8").split("  test:\n", 1)[1].split("  judgment-timeline:", 1)[0]


def _test_script() -> str:
    step = _test_job().split("      - name: Test\n", 1)[1].split("      - name:", 1)[0]
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


def test_ci_keeps_complete_union_without_worker_retries():
    command = " ".join(_test_script().replace("\\\n", " ").splitlines()[1:]).split("2>&1", 1)[0]
    assert shlex.split(command) == [
        "python", "-m", "pytest", "-q", "-n", "4", "--dist=loadfile", "--max-worker-restart=0",
        "@$CI_REPORT_DIR/remaining-args.txt",
        "-o", "faulthandler_timeout=60", "-o", "faulthandler_exit_on_timeout=true",
        "--durations=100", "--durations-min=1.0", "--junitxml=$CI_REPORT_DIR/remaining.xml",
    ]
    job = _test_job()
    assert "python -m pytest --collect-only -q" in job
    assert "--operation partition" in job and "--operation assemble" in job
    assert "continue-on-error" not in job
    assert "set -euo pipefail" in _test_script()
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert config["tool"]["pytest"]["ini_options"]["addopts"] == "-ra"


def test_ci_verifies_the_checked_out_code_not_just_event_metadata():
    job = _test_job()
    assert "ref: ${{ github.event.pull_request.head.sha || github.sha }}" in job
    assert 'test "$(git rev-parse HEAD)" = "$CI_CODE_SHA"' in job
    assert "persist-credentials: false" in job
    assert "permissions:\n  contents: read\n" in WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in job
    assert "code_sha=%s" in job and "event_sha=%s" in job
    # Runner context is not available in job-level env; export it at runtime.
    assert "runner." not in job.split("    steps:", 1)[0]
    assert 'CI_REPORT_DIR="$RUNNER_TEMP/kernel-ci"' in job
    assert '"$CI_REPORT_DIR" >> "$GITHUB_ENV"' in job


def test_parallel_dependency_is_dev_only_and_local_default_stays_serial():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    xdist = [d for d in project["optional-dependencies"]["dev"] if d.startswith("pytest-xdist==")]
    assert len(xdist) == 1 and xdist[0].split("==")[1]
    for group, deps in project["optional-dependencies"].items():
        if group != "dev":
            assert not any("xdist" in dep or "execnet" in dep for dep in deps)
    assert not any("xdist" in dep or "execnet" in dep for dep in project["dependencies"])
    assert "-n" not in shlex.split(config["tool"]["pytest"]["ini_options"]["addopts"])


def test_ci_diagnostics_are_retained_on_failure_and_do_not_replace_the_test_result():
    job = _test_job()
    upload = job.split("      - name: Upload CI diagnostics\n", 1)[1]
    assert "if: always()" in upload
    assert "actions/upload-artifact@" in upload
    assert "kernel-ci-${{ github.run_id }}-${{ github.run_attempt }}" in upload
    assert 'tee "$CI_REPORT_DIR/pytest.log"' in _test_script()
    assert '"$CI_REPORT_DIR/collection.txt"' in job
    assert "faulthandler_timeout=60" in _test_script()
    assert "faulthandler_exit_on_timeout=true" in _test_script()
    assert "continue-on-error" not in upload


@pytest.mark.parametrize("outcome", ["pass", "fail", "crash"])
def test_actual_ci_command_propagates_test_and_worker_failure(tmp_path, outcome):
    report = tmp_path / "reports"
    report.mkdir()
    (report / "remaining-args.txt").write_text("")
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    body = {
        "pass": "    assert True\n",
        "fail": "    assert False, 'SYNTHETIC_CI_FAILURE'\n",
        "crash": "    import os\n    os._exit(7)\n",
    }[outcome]
    (tmp_path / "test_synthetic_ci.py").write_text("def test_outcome():\n" + body, encoding="utf-8")
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["CI_REPORT_DIR"] = str(report)
    completed = subprocess.run(
        ["bash", "-c", _test_script()], cwd=tmp_path, env=env,
        text=True, capture_output=True, timeout=90, check=False,
    )
    assert completed.returncode == (0 if outcome == "pass" else 1), completed.stdout + completed.stderr
    assert (report / "pytest.log").is_file()
    suites = ET.parse(report / "remaining.xml").getroot().findall("testsuite")
    assert sum(int(s.attrib["tests"]) for s in suites) == 1
    assert sum(int(s.attrib["skipped"]) for s in suites) == 0
    failures = sum(int(s.attrib["failures"]) + int(s.attrib["errors"]) for s in suites)
    assert failures == (0 if outcome == "pass" else 1)


# These checks retire with the native draft feedback path, not with business data.
def _draft_case(tmp_path, outcome='pass'):
    import json
    import runpy
    scope = runpy.run_path(str(ROOT / '.github/scripts/ci-content-scope.py'))
    def put(path, text):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
    def git(*args):
        return subprocess.check_output(['git', '-c', 'user.name=Synthetic CI', '-c',
            'user.email=ci@example.invalid', *args], cwd=tmp_path, stderr=subprocess.PIPE).decode().strip()
    git('init', '-q')
    put('.github/scripts/ci-content-scope.py', (ROOT / '.github/scripts/ci-content-scope.py').read_text())
    for path in scope['DRAFT_SMOKE']:
        put(path, 'def test_core():\n    assert True\n')
    put('src/behavior.py', 'value = 1\n')
    put('tests/test_changed.py', 'def test_change():\n    assert True\n')
    put('tests/test_unselected.py', 'def test_not_covered_by_feedback():\n    assert False\n')
    git('add', '.'); git('commit', '-qm', 'synthetic baseline')
    base = git('rev-parse', 'HEAD')
    put('src/behavior.py', 'value = (\n' if outcome == 'syntax' else 'value = 2\n')
    put('tests/test_changed.py', 'def test_change():\n    assert '+str(outcome != 'fail')+'\n# changed\n')
    git('add', '.'); git('commit', '-qm', 'synthetic edit')
    head = git('rev-parse', 'HEAD')
    payload = dict(action='synchronize', pull_request=dict(draft=True,
        head=dict(sha=head, repo=dict(full_name=scope['REPO'])),
        base=dict(sha=base, ref='main', repo=dict(full_name=scope['REPO']))))
    report = scope['select'](tmp_path, 'pull_request', base, head,
                            read_runs=lambda *_: pytest.fail('no remote lookup for code edits'))
    report_dir = tmp_path / '.git/reports'; report_dir.mkdir()
    (report_dir / 'event.json').write_text(json.dumps(payload))
    return scope, report, payload, report_dir


def test_draft_feedback_requires_explicit_owned_draft_and_safe_diff(tmp_path):
    from copy import deepcopy
    scope, report, payload, _ = _draft_case(tmp_path)
    choose = scope['draft_feedback_scope']
    assert choose(report, payload)['scope'] == 'draft_feedback'
    assert report['scope'] == 'full'  # Classification never mutates the original.
    for draft in (False, None, 1, 'true'):
        bad = deepcopy(payload); bad['pull_request']['draft'] = draft
        assert choose(report, bad)['scope'] == 'full'
    for action in ('ready_for_review', 'edited', 'unknown'):
        bad = deepcopy(payload); bad['action'] = action
        assert choose(report, bad)['scope'] == 'full'
    for side in ('head', 'base'):
        bad = deepcopy(payload); bad['pull_request'][side]['repo']['full_name'] = 'other/repo'
        assert choose(report, bad)['scope'] == 'full'
        bad = deepcopy(payload); bad['pull_request'][side]['sha'] = 'e'*40
        assert choose(report, bad)['scope'] == 'full'
    for bad in ({}, None, {'pull_request': None}):
        assert choose(report, bad)['scope'] == 'full'
    for event in ('push', 'workflow_dispatch'):
        assert choose({**report, 'event': event}, payload)['scope'] == 'full'
    for reason in ('SCOPE_READ_UNAVAILABLE_OSError', 'NO_TRUSTED_SUCCESSFUL_BASE_CI'):
        assert choose({**report, 'reason': reason}, payload)['scope'] == 'full'
    assert choose({**report, 'changes': []}, payload)['scope'] == 'full'
    for path in ('.github/workflows/ci.yml', '.github/scripts/ci-content-scope.py',
                 'tests/test_ci_contract.py', 'tests/conftest.py', 'pyproject.toml',
                 'requirements-dev.txt', 'src/../run.py', '/run.py', 'src/a\nb.py'):
        rows = [dict(report['changes'][0], path=path)]
        assert choose({**report, 'changes': rows}, payload)['scope'] == 'full', path
    for change in ({'status': 'D'}, {'status': 'R100'}, {'new_mode': '120000'}, {'new_mode': '100755'}):
        rows = [{**report['changes'][0], **change}]
        assert choose({**report, 'changes': rows}, payload)['scope'] == 'full'


@pytest.mark.parametrize('outcome', ['pass', 'fail', 'syntax'])
def test_actual_draft_shell_feedback_does_not_claim_full_success(tmp_path, outcome):
    import json
    import sys
    _, report, _, report_dir = _draft_case(tmp_path, outcome)
    env = os.environ.copy()
    env.update(GITHUB_EVENT_NAME='pull_request', CI_BASE_SHA=report['base_sha'],
        CI_CODE_SHA=report['code_sha'], GITHUB_EVENT_PATH=str(report_dir/'event.json'),
        GITHUB_OUTPUT=str(report_dir/'outputs'), GITHUB_STEP_SUMMARY=str(report_dir/'summary'),
        CI_REPORT_DIR=str(report_dir), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='')
    selected = subprocess.run([sys.executable, '.github/scripts/ci-content-scope.py', 'select',
        '--report-dir', str(report_dir)], cwd=tmp_path, env=env, capture_output=True, timeout=30)
    assert selected.returncode == 0, selected.stderr
    assert json.loads((report_dir/'scope.json').read_text())['scope'] == 'draft_feedback'
    step = _test_job().split('      - name: Draft feedback only - not merge validation\n', 1)[1].split('      - name:', 1)[0]
    script = textwrap.dedent(step.split('        run: |\n', 1)[1])
    run = subprocess.run(['bash', '-c', script], cwd=tmp_path, env=env,
                         capture_output=True, timeout=60)
    assert run.returncode == (0 if outcome == 'pass' else 1), run.stdout + run.stderr
    feedback = json.loads((report_dir/'draft-feedback.json').read_text())
    assert feedback['full_suite'] == 'NOT_RUN_DRAFT_FEEDBACK'
    assert feedback['merge_eligible'] is False
    assert 'tests/test_changed.py' in feedback['test_paths']
    assert 'tests/test_unselected.py' not in feedback['test_paths']
    assert not (report_dir/'pytest.xml').exists() and not (report_dir/'collection.txt').exists()
    assert (report_dir/'draft-feedback.log').exists()
    if outcome != 'syntax':
        cases = ET.parse(report_dir/'draft-feedback.xml').getroot().findall('.//testcase')
        assert len(cases) == 5
        assert sum(c.find('failure') is not None for c in cases) == (outcome == 'fail')
        assert feedback['exit_code'] == run.returncode
        assert 'NOT_RUN_DRAFT_FEEDBACK' in (report_dir/'summary').read_text()
    else:
        assert feedback['exit_code'] is None  # Failed before pytest, not a pass.


def test_draft_feedback_rejects_changed_checkout_and_diff(tmp_path):
    scope, report, payload, report_dir = _draft_case(tmp_path)
    preview = scope['draft_feedback_scope'](report, payload)
    bad = {**preview, 'changes': preview['changes'][:-1]}
    with pytest.raises(ValueError, match='checkout or diff'):
        scope['draft_feedback'](tmp_path, bad, report_dir)
    (tmp_path/'src/behavior.py').write_text('value = 3\n')
    with pytest.raises(ValueError, match='checkout or diff'):
        scope['draft_feedback'](tmp_path, preview, report_dir)


def test_draft_scope_is_rejected_by_original_full_evidence_reader():
    import hashlib
    import io
    import json
    import runpy
    import zipfile
    reader = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))
    head = 'a'*40
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('identity.txt', f'code_sha={head}\nevent=pull_request\nrun_id=123\nattempt=1\n')
        archive.writestr('scope.json', json.dumps(dict(scope='draft_feedback', code_sha=head, event='pull_request')))
    raw = data.getvalue()
    artifact = dict(size_in_bytes=len(raw), digest='sha256:'+hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError, match='NOT_FULL_PR_SCOPE'):
        reader['full_evidence'](raw, artifact, dict(head_sha=head, id=123), {})


def test_draft_ready_transition_keeps_complete_engineering_gate():
    workflow = WORKFLOW.read_text()
    events = workflow.split('  pull_request:\n', 1)[1].split('  push:\n', 1)[0]
    for action in ('opened', 'synchronize', 'reopened', 'ready_for_review', 'converted_to_draft'):
        assert action in events
    for label in ('Verify exact PR full-suite reuse after real installation', 'Record full test collection', 'Test'):
        step = _test_job().split('      - name: '+label+'\n', 1)[1].split('      - name:', 1)[0]
        assert "steps.scope.outputs.scope != 'draft_feedback'" in step
    assert 'continue-on-error' not in workflow and 'pull_request_target' not in workflow
