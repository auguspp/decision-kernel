from __future__ import annotations

import runpy
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/stock-reading-after-sector.yml"
HELPER = ROOT / ".github/scripts/check-stock-daily-successor.py"
STOCK_WORKFLOW = ROOT / ".github/workflows/hithink-stock-dump-trial.yml"
STOCK_CAPTURE = ROOT / ".github/scripts/capture-stock-reading.py"
CURRENT_STATE = ROOT / "src/decision_kernel/runtime/current_state.py"


def module():
    return runpy.run_path(str(HELPER), run_name="stock_daily_successor_test")


def environment(**changes):
    values = {
        "GITHUB_REPOSITORY": "auguspp/decision-kernel",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW": "stock-reading-after-sector",
        "GITHUB_EVENT_NAME": "workflow_run",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "500",
        "GITHUB_SHA": "a" * 40,
        "UPSTREAM_NAME": "sector-radar-shadow",
        "UPSTREAM_PATH": ".github/workflows/sector-radar-shadow.yml",
        "UPSTREAM_EVENT": "schedule",
        "UPSTREAM_STATUS": "completed",
        "UPSTREAM_CONCLUSION": "success",
        "UPSTREAM_RUN_ATTEMPT": "1",
        "UPSTREAM_RUN_ID": "499",
        "UPSTREAM_HEAD_BRANCH": "main",
        "UPSTREAM_HEAD_REPOSITORY": "auguspp/decision-kernel",
        "UPSTREAM_HEAD_SHA": "a" * 40,
    }
    values.update(changes)
    return values


def test_successor_is_one_natural_sector_handoff_not_a_new_clock_or_market_reader():
    raw = WORKFLOW.read_text(encoding="utf-8")
    trigger = raw.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_run:" in trigger
    assert "workflows: [sector-radar-shadow]" in trigger
    assert "types: [completed]" in trigger and "branches: [main]" in trigger
    assert "schedule:" not in trigger and "workflow_dispatch:" not in trigger and "push:" not in trigger
    for required in (
        "github.event.workflow_run.event == 'schedule'",
        "github.event.workflow_run.status == 'completed'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.run_attempt == 1",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
        "github.run_attempt == 1",
    ):
        assert required in raw
    assert "github.event.workflow_run.head_sha == github.sha" not in raw
    assert "contents: read" in raw and "actions: write" in raw
    assert "persist-credentials: false" in raw
    assert "cancel-in-progress: false" in raw and "timeout-minutes: 5" in raw
    assert raw.count("hithink-stock-dump-trial.yml/dispatches") == 1
    assert raw.count("gh api --method POST") == 1
    assert '"trial-purpose": "stock-reading"' in raw
    assert '"stock-market-run-id": os.environ["MARKET_RUN_ID"]' in raw
    assert "steps.preflight.outputs.market_run_id" in raw
    assert "HITHINK_FINANCE_API_KEY" not in raw and "secrets.HITHINK_FINANCE_API_KEY" not in raw
    assert "/rerun" not in raw and "sleep(" not in raw and "while " not in raw


def test_exact_successor_identity_accepts_natural_sector_success_and_separate_code_sha():
    mod = module()
    assert mod["validate_successor"](environment()) == 499
    # A long natural Sector run may finish after main has legitimately advanced.
    # The existing Stock contract binds the immutable upstream artifact separately.
    assert mod["validate_successor"](environment(GITHUB_SHA="b" * 40)) == 499
    assert mod["validate_successor"](environment(UPSTREAM_HEAD_SHA="b" * 40)) == 499
    invalid = (
        ("GITHUB_REPOSITORY", "other/repo"),
        ("GITHUB_REF", "refs/heads/other"),
        ("GITHUB_WORKFLOW", "other-workflow"),
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("GITHUB_SHA", "not-a-sha"),
        ("UPSTREAM_NAME", "other"),
        ("UPSTREAM_PATH", ".github/workflows/other.yml"),
        ("UPSTREAM_EVENT", "workflow_dispatch"),
        ("UPSTREAM_STATUS", "in_progress"),
        ("UPSTREAM_CONCLUSION", "failure"),
        ("UPSTREAM_RUN_ATTEMPT", "2"),
        ("UPSTREAM_RUN_ID", "0"),
        ("UPSTREAM_HEAD_BRANCH", "feature"),
        ("UPSTREAM_HEAD_REPOSITORY", "other/repo"),
        ("UPSTREAM_HEAD_SHA", "not-a-sha"),
    )
    for key, value in invalid:
        with pytest.raises(mod["SuccessorCheckError"]):
            mod["validate_successor"](environment(**{key: value}))
    with pytest.raises(mod["SuccessorCheckError"]):
        mod["validate_successor"](environment(UPSTREAM_RUN_ID="500"))


def test_successor_reuses_existing_bounded_activity_observation_for_all_key_users():
    mod = module()
    assert mod["KEY_USERS"] == frozenset({
        ".github/workflows/sector-radar-shadow.yml",
        ".github/workflows/hithink-stock-dump-trial.yml",
        ".github/workflows/decision-inbox.yml",
        ".github/workflows/live-dogfood.yml",
    })
    calls = []

    def read(url):
        status = parse_qs(urlsplit(url).query)["status"][0]
        calls.append(status)
        rows = [
            {"id": 700 + i, "path": path + "@refs/heads/main", "status": status}
            for i, path in enumerate(sorted(mod["KEY_USERS"]))
        ]
        return {"total_count": len(rows), "workflow_runs": rows}

    assert mod["shared_key_blockers"](read) == [700, 701, 702, 703]
    assert tuple(calls) == mod["activity_module"]()["ACTIVE"]


def test_successor_preflight_has_no_market_or_dispatch_authority_itself():
    raw = HELPER.read_text(encoding="utf-8")
    assert "HITHINK_FINANCE_API_KEY" not in raw
    assert "/dispatches" not in raw and "gh api" not in raw
    assert "POST" not in raw and "PUT" not in raw
    assert "sleep(" not in raw and "while " not in raw
    assert "check-sector-scheduled-activity.py" in raw


def test_existing_stock_and_current_state_production_contracts_are_not_broadened():
    stock = STOCK_WORKFLOW.read_text(encoding="utf-8")
    stock_trigger = stock.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_run:" not in stock_trigger and "schedule:" not in stock_trigger
    assert "workflow_dispatch:" in stock_trigger
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'stock-reading'" in stock

    capture = STOCK_CAPTURE.read_text(encoding="utf-8")
    assert "stock reading requires explicit manual intent" in capture
    assert "env.get('GITHUB_EVENT_NAME')!='workflow_dispatch'" in capture

    current = CURRENT_STATE.read_text(encoding="utf-8")
    assert 'run.get("event") in {"schedule", "workflow_dispatch"}' in current
    assert 'r.get("event") in {"schedule", "workflow_dispatch"}' in current
