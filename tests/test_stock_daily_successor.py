from __future__ import annotations

import ast
import json
import runpy
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/stock-reading-after-sector.yml"
HELPER = ROOT / ".github/scripts/check-stock-daily-successor.py"
SECTOR_WORKFLOW = ROOT / ".github/workflows/sector-radar-shadow.yml"
STOCK_WORKFLOW = ROOT / ".github/workflows/hithink-stock-dump-trial.yml"
TDX_WORKFLOW = ROOT / ".github/workflows/tdx-concept-snapshot.yml"
RESEARCH_WORKFLOW = ROOT / ".github/workflows/stock-business-research.yml"
CURRENT_STATE_WORKFLOW = ROOT / ".github/workflows/current-state-read-entry.yml"
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
        "UPSTREAM_JOBS_JSON": "",
    }
    values.update(changes)
    return values


def write_dispatch_jobs(path: Path, profile: str) -> Path:
    outcomes = {
        "Run independent Sector Radar shadow producer": "skipped",
        "Verify exact offline replay before publication": "skipped",
        "Upload authoritative state bundle": "success",
        "Adopt exact 2026-09-14 missed-session checkpoint": "skipped",
        "Verify 2026-09-14 missed-session adoption exact offline match": "skipped",
        "Adopt exact recovery checkpoint into original Sector lineage": "skipped",
        "Verify recovery adoption exact offline match": "skipped",
        "Bind 2026-09-24 exchange closure evidence": "skipped",
    }
    if profile == "produce":
        outcomes["Run independent Sector Radar shadow producer"] = "success"
        outcomes["Verify exact offline replay before publication"] = "success"
    elif profile == "backfill":
        outcomes["Run independent Sector Radar shadow producer"] = "success"
        outcomes["Verify exact offline replay before publication"] = "success"
        outcomes["Bind 2026-09-24 exchange closure evidence"] = "success"
    elif profile == "missed-adoption":
        outcomes["Adopt exact 2026-09-14 missed-session checkpoint"] = "success"
        outcomes["Verify 2026-09-14 missed-session adoption exact offline match"] = "success"
    elif profile == "recovery-adoption":
        outcomes["Adopt exact recovery checkpoint into original Sector lineage"] = "success"
        outcomes["Verify recovery adoption exact offline match"] = "success"
    elif profile == "ambiguous":
        outcomes["Run independent Sector Radar shadow producer"] = "success"
        outcomes["Verify exact offline replay before publication"] = "success"
        outcomes["Adopt exact recovery checkpoint into original Sector lineage"] = "success"
        outcomes["Verify recovery adoption exact offline match"] = "success"
    elif profile != "unknown":
        raise AssertionError(profile)
    payload = {
        "total_count": 1,
        "jobs": [{
            "name": "producer",
            "status": "completed",
            "conclusion": "success",
            "steps": [
                {"name": name, "status": "completed", "conclusion": conclusion}
                for name, conclusion in outcomes.items()
            ],
        }],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_successor_reuses_one_daily_sector_clock_for_stock_and_tdx_without_new_schedule():
    raw = WORKFLOW.read_text(encoding="utf-8")
    trigger = raw.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_run:" in trigger
    assert "workflows: [sector-radar-shadow]" in trigger
    assert "types: [completed]" in trigger and "branches: [main]" in trigger
    assert "schedule:" not in trigger and "workflow_dispatch:" not in trigger and "push:" not in trigger
    for required in (
        "github.event.workflow_run.event == 'schedule'",
        "github.event.workflow_run.event == 'workflow_dispatch'",
        "github.event.workflow_run.status == 'completed'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.run_attempt == 1",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
        "github.run_attempt == 1",
    ):
        assert required in raw
    assert "github.event.workflow_run.head_sha == github.sha" not in raw
    assert "contents: read" in raw and "actions: read" in raw and "actions: write" not in raw
    assert "persist-credentials: false" in raw
    assert "cancel-in-progress: false" in raw and "timeout-minutes: 5" in raw
    assert raw.count("hithink-stock-dump-trial.yml/dispatches") == 1
    assert raw.count("tdx-concept-snapshot.yml/dispatches") == 1
    assert raw.count("gh api --method POST") == 2
    assert "actions/runs/$UPSTREAM_RUN_ID/jobs?per_page=100&page=1" in raw
    assert "UPSTREAM_JOBS_JSON" in raw
    assert '"trial-purpose": "stock-reading"' in raw
    assert '"stock-market-run-id": os.environ["MARKET_RUN_ID"]' in raw
    assert "steps.preflight.outputs.market_run_id" in raw
    assert "steps.preflight.outputs.sector_origin" in raw
    assert "steps.tdx-origin.outputs.sector_run_id" in raw
    assert "steps.tdx-origin.outputs.sector_origin" in raw
    assert "'market-session': os.environ['MARKET_SESSION']" in raw
    assert "'code-sha': os.environ['CODE_SHA']" in raw
    dispatch = raw.split("- name: Dispatch existing bounded Stock reading once", 1)[1].split("\n  dispatch-tdx-concept:", 1)[0]
    assert "GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}" in dispatch
    assert raw.count("GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}") == 2
    assert "GH_TOKEN: ${{ github.token }}" not in dispatch
    assert 'Missing repository secret DAILY_CHAIN_DISPATCH_TOKEN' in dispatch
    assert 'do not fall back to GITHUB_TOKEN' in dispatch
    assert "stock-business-research.yml/dispatches" not in raw
    assert "gh run watch" not in raw
    assert "HITHINK_FINANCE_API_KEY" not in raw and "secrets.HITHINK_FINANCE_API_KEY" not in raw
    assert "/rerun" not in raw and "sleep(" not in raw and "while " not in raw



def test_tdx_daily_handoff_reuses_exact_sector_result_and_existing_capture_contract():
    successor = WORKFLOW.read_text(encoding="utf-8")
    tdx = TDX_WORKFLOW.read_text(encoding="utf-8")
    block = successor.split("  dispatch-tdx-concept:\n", 1)[1]

    assert "needs: dispatch-stock-reading" not in block
    assert "SUCCESSOR_CHECK_MODE: stock-input" in block
    assert "check-stock-daily-successor.py" in block
    assert '"sector-radar-run-$UPSTREAM_RUN_ID"' in block
    assert "latest_completed_session" in block
    assert "direct_next_session" in block
    assert "APPENDED_NEW_COMPLETED_SESSION" in block
    assert "Require successor code is still current main" in block
    assert "GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}" in block
    assert "HITHINK_FINANCE_API_KEY" not in block
    assert "secrets.HITHINK_FINANCE_API_KEY" not in block
    assert "schedule:" not in block

    trigger = tdx.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in trigger
    assert "schedule:" not in trigger and "workflow_run:" not in trigger
    assert "market-session:" in trigger and "code-sha:" in trigger
    assert 'test "$EXPECTED_CODE" = "$GITHUB_SHA"' in tdx
    assert "actions/workflows/ci.yml/runs" in tdx
    assert "include-hidden-files: true" in tdx


def test_exact_successor_identity_accepts_native_schedule_and_separate_code_sha():
    mod = module()
    assert mod["validate_successor"](environment()) == (499, "GITHUB_SCHEDULE")
    assert mod["handoff_allowed"]("GITHUB_SCHEDULE") is True
    # A long Sector run may finish after main has legitimately advanced.
    # The existing Stock contract binds the immutable upstream artifact separately.
    assert mod["validate_successor"](environment(GITHUB_SHA="b" * 40)) == (499, "GITHUB_SCHEDULE")
    assert mod["validate_successor"](environment(UPSTREAM_HEAD_SHA="b" * 40)) == (499, "GITHUB_SCHEDULE")
    invalid = (
        ("GITHUB_REPOSITORY", "other/repo"),
        ("GITHUB_REF", "refs/heads/other"),
        ("GITHUB_WORKFLOW", "other-workflow"),
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_RUN_ATTEMPT", "2"),
        ("GITHUB_SHA", "not-a-sha"),
        ("UPSTREAM_NAME", "other"),
        ("UPSTREAM_PATH", ".github/workflows/other.yml"),
        ("UPSTREAM_EVENT", "push"),
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


def test_workflow_dispatch_requires_exact_successful_produce_step_evidence(tmp_path):
    mod = module()
    produce = write_dispatch_jobs(tmp_path / "produce.json", "produce")
    assert mod["validate_successor"](environment(
        UPSTREAM_EVENT="workflow_dispatch",
        UPSTREAM_JOBS_JSON=str(produce),
    )) == (499, "WORKFLOW_DISPATCH_PRODUCE")
    assert mod["handoff_allowed"]("WORKFLOW_DISPATCH_PRODUCE") is True

    backfill = write_dispatch_jobs(tmp_path / "backfill.json", "backfill")
    assert mod["validate_successor"](environment(
        UPSTREAM_EVENT="workflow_dispatch",
        UPSTREAM_JOBS_JSON=str(backfill),
    )) == (499, "WORKFLOW_DISPATCH_BACKFILL")
    assert mod["handoff_allowed"]("WORKFLOW_DISPATCH_BACKFILL") is True

    for profile in ("missed-adoption", "recovery-adoption"):
        recovery = write_dispatch_jobs(tmp_path / f"{profile}.json", profile)
        assert mod["validate_successor"](environment(
            UPSTREAM_EVENT="workflow_dispatch",
            UPSTREAM_JOBS_JSON=str(recovery),
        )) == (499, "WORKFLOW_DISPATCH_RECOVERY")
        assert mod["handoff_allowed"]("WORKFLOW_DISPATCH_RECOVERY") is False

    for profile in ("unknown", "ambiguous"):
        bad = write_dispatch_jobs(tmp_path / f"{profile}.json", profile)
        with pytest.raises(mod["SuccessorCheckError"]):
            mod["validate_successor"](environment(
                UPSTREAM_EVENT="workflow_dispatch",
                UPSTREAM_JOBS_JSON=str(bad),
            ))
    with pytest.raises(mod["SuccessorCheckError"]):
        mod["validate_successor"](environment(UPSTREAM_EVENT="workflow_dispatch"))


def test_dispatch_classifier_is_pinned_to_existing_sector_step_contract():
    mod = module()
    sector = SECTOR_WORKFLOW.read_text(encoding="utf-8")
    for key in (
        "PRODUCER_STEP",
        "REPLAY_STEP",
        "STATE_UPLOAD_STEP",
        "MISSED_ADOPT_STEP",
        "MISSED_VERIFY_STEP",
        "RECOVERY_ADOPT_STEP",
        "RECOVERY_VERIFY_STEP",
        "BACKFILL_REFERENCE_STEP",
    ):
        assert f"- name: {mod[key]}" in sector


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


def test_successor_preflight_has_no_market_dispatch_or_polling_authority_itself():
    raw = HELPER.read_text(encoding="utf-8")
    assert "HITHINK_FINANCE_API_KEY" not in raw
    assert "/dispatches" not in raw and "gh api" not in raw
    assert "sleep(" not in raw
    tree = ast.parse(raw)
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    assert "check-sector-scheduled-activity.py" in raw


def test_non_github_token_stock_origin_publishes_before_any_manual_research():
    successor = WORKFLOW.read_text(encoding="utf-8")
    research = RESEARCH_WORKFLOW.read_text(encoding="utf-8")
    publisher = CURRENT_STATE_WORKFLOW.read_text(encoding="utf-8")
    assert "GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}" in successor
    trigger = research.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "workflow_dispatch:" in trigger and "workflow_run:" not in trigger
    assert "source-stock-run-id:" in research
    assert "github.event.workflow_run" not in research
    assert "python -m decision_kernel.runtime.stock_research_host" in research
    assert "stock-business-research" in publisher
    assert "hithink-stock-dump-trial" in publisher
    assert "workflow_run:" in publisher


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
