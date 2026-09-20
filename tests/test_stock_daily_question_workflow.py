"""Exercise the actual daily dispatch guard without invoking Research or a provider."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import textwrap

import pytest


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/stock-business-research.yml"
DAILY_STEP = "Daily reviewed question through saved policy and original admission"
INCOMPATIBLE_INPUTS = (
    "reviewed-question", "reviewed-question-continuation", "recover-sources",
    "prepare-sources", "source-successor", "source-successor-continuation",
    "deepseek-compat",
)
INCOMPATIBLE_ENV = (
    "REVIEWED_QUESTION", "REVIEWED_QUESTION_CONTINUATION", "RECOVER_SOURCES",
    "PREPARE_SOURCES", "SOURCE_SUCCESSOR", "SOURCE_SUCCESSOR_CONTINUATION",
    "DEEPSEEK_COMPAT",
)
CODE = "a" * 40


def daily_step():
    return WORKFLOW.read_text().split(f"      - name: {DAILY_STEP}\n", 1)[1].split(
        "      - name:", 1)[0]


def test_daily_dispatch_reuses_existing_job_and_concurrency_with_only_deepseek_credentials():
    workflow = WORKFLOW.read_text()
    trigger = workflow.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    daily = trigger.split("      daily-reviewed-question:\n", 1)[1].split("      reviewed-question-continuation:", 1)[0]
    assert "type: boolean" in daily and "default: false" in daily
    assert "schedule:" not in trigger and "workflow_run:" not in trigger
    assert "group: stock-business-first-v0\n  cancel-in-progress: false" in workflow
    assert re.findall(r"^  ([a-z-]+):$", workflow.split("jobs:\n", 1)[1], re.M) == [
        "research-stock-business", "deepseek-compatibility", "prepare-stock-sources",
    ]
    step = daily_step()
    assert "GH_TOKEN: ${{ github.token }}" in step
    assert re.findall(r"secrets\.([A-Z_]+)", step) == ["DEEPSEEK_API_KEY"]
    assert "SUB2API" not in step and "stock_question_continuation" not in step
    assert "continue-on-error" not in workflow
    retained = workflow.split("      - name: Preserve original sources, model outputs and partial failures\n", 1)[1]
    assert "if: always()" in retained and "path: run-output/" in retained


def test_daily_dispatch_cannot_select_existing_modes():
    workflow = WORKFLOW.read_text()
    research = workflow.split("  research-stock-business:\n", 1)[1].split("    runs-on:", 1)[0]
    assert "!inputs.daily-reviewed-question ||" in research
    assert "inputs.code-sha == github.sha" in research
    assert "!inputs.source-stock-run-id" in research
    for name in INCOMPATIBLE_INPUTS:
        assert f"!inputs.{name}" in research
    for job in ("deepseek-compatibility", "prepare-stock-sources"):
        condition = workflow.split(f"  {job}:\n", 1)[1].split("    runs-on:", 1)[0]
        assert "!inputs.daily-reviewed-question" in condition
    original_steps = workflow.split(f"      - name: {DAILY_STEP}\n", 1)[0]
    conditions = re.findall(r"^        if: (.+)$", original_steps, re.M)
    assert len(conditions) == 3
    assert all("!inputs.daily-reviewed-question" in condition for condition in conditions)


def run_daily_script(tmp_path, override):
    marker = tmp_path / "invoked.txt"
    environment = {
        "PATH": os.environ["PATH"], "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "auguspp/decision-kernel", "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": CODE, "EXPECTED_CODE_SHA": CODE,
        "SOURCE_STOCK_RUN": "", "DEEPSEEK_API_KEY": "synthetic-test-only",
        "TEST_CHECKOUT_SHA": CODE, "TEST_INVOKED": str(marker),
        **{name: "false" for name in INCOMPATIBLE_ENV}, **override,
    }
    # Shell stand-ins record the host command; no actual Git or Python runs.
    prelude = """git() { printf '%s\\n' "$TEST_CHECKOUT_SHA"; }
python() { printf '%s\\n' "$@" > "$TEST_INVOKED"; }
"""
    script = textwrap.dedent(daily_step().split("        run: |\n", 1)[1])
    result = subprocess.run(
        ["bash", "-c", prelude + script], cwd=tmp_path, env=environment,
        text=True, capture_output=True, timeout=10, check=False,
    )
    return result, marker


def test_actual_daily_script_invokes_only_daily_host_mode(tmp_path):
    result, marker = run_daily_script(tmp_path, {})
    assert result.returncode == 0, result.stderr
    assert marker.read_text().splitlines() == [
        "-m", "decision_kernel.runtime.stock_question_host", "--daily-reviewed-question",
        "--code-commit", CODE, "--output", "run-output",
    ]


@pytest.mark.parametrize("override", [
    *({name: "true"} for name in INCOMPATIBLE_ENV),
    {"GITHUB_EVENT_NAME": "schedule"},
    {"GITHUB_REPOSITORY": "other/decision-kernel"},
    {"GITHUB_REF": "refs/heads/topic"},
    {"GITHUB_RUN_ATTEMPT": "2"},
    {"EXPECTED_CODE_SHA": ""},
    {"EXPECTED_CODE_SHA": "main"},
    {"GITHUB_SHA": "b" * 40},
    {"TEST_CHECKOUT_SHA": "b" * 40},
    {"SOURCE_STOCK_RUN": "123"},
    {"DEEPSEEK_API_KEY": ""},
], ids=lambda value: next(iter(value)))
def test_actual_daily_script_rejects_conflict_or_unbound_identity_before_host(tmp_path, override):
    result, marker = run_daily_script(tmp_path, override)
    assert result.returncode != 0
    assert not marker.exists()
