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


def test_ci_keeps_one_full_suite_without_filtering_or_worker_retries():
    command = " ".join(_test_script().replace("\\\n", " ").splitlines()[1:]).split("2>&1", 1)[0]
    assert shlex.split(command) == [
        "python", "-m", "pytest", "-q", "-n", "2", "--dist=loadfile", "--max-worker-restart=0",
        "--durations=100", "--durations-min=1.0", "--junitxml=$CI_REPORT_DIR/pytest.xml",
    ]
    job = _test_job()
    assert "python -m pytest --collect-only -q" in job
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
    assert "continue-on-error" not in upload


@pytest.mark.parametrize("outcome", ["pass", "fail", "crash"])
def test_actual_ci_command_propagates_test_and_worker_failure(tmp_path, outcome):
    report = tmp_path / "reports"
    report.mkdir()
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
    suites = ET.parse(report / "pytest.xml").getroot().findall("testsuite")
    assert sum(int(s.attrib["tests"]) for s in suites) == 1
    assert sum(int(s.attrib["skipped"]) for s in suites) == 0
    failures = sum(int(s.attrib["failures"]) + int(s.attrib["errors"]) for s in suites)
    assert failures == (0 if outcome == "pass" else 1)
