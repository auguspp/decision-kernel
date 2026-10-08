from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1] / '.github/scripts/stock-market-input-gate.py'
spec = spec_from_file_location("stock_market_input_gate", path)
gate = module_from_spec(spec)
spec.loader.exec_module(gate)

NOW = datetime(2026, 10, 9, 10, 25, tzinfo=timezone.utc)
ENV = {"GITHUB_REPOSITORY": gate.REPOSITORY, "GITHUB_REF": "refs/heads/main",
       "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "124", "GITHUB_EVENT_NAME": "workflow_run"}
EVENT = {"workflow_run": {"path": gate.SECTOR_PATH, "head_branch": "main",
          "head_repository": {"full_name": gate.REPOSITORY}, "run_attempt": 1,
          "status": "completed", "conclusion": "failure"}}


def api(runs, artifacts=None):
    artifacts = artifacts or {}
    def get(path):
        if path.endswith("runs?branch=main&per_page=100"):
            return {"workflow_runs": runs}
        return {"artifacts": artifacts.get(int(path.split("/runs/")[1].split("/")[0]), [])}
    return get


def prev(id=120, status="completed", at="2026-10-09T10:00:00Z"):
    return {"id": id, "display_title": gate.SOURCE_TITLE, "created_at": at,
            "head_branch": "main", "status": status}


def test_sector_completion_even_on_failure_allows_independent_dated_input():
    assert gate.should_capture(ENV, EVENT, NOW, api([])) == (
        True, "FIRST_QUALIFIED_SOURCE_ATTEMPT", None)


def test_previous_actual_source_artifact_for_today_blocks_all_duplicate_source():
    saved = {"name": "stock-market-inputs-120-1", "expired": False}
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], {120: [saved]})) == (
        False, "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE", 120)


def test_prior_no_source_or_uncertain_run_fails_closed():
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], {120: []})) == (
        False, "OTHER_SOURCE_ATTEMPT_UNCERTAIN", 120)
    assert gate.should_capture(ENV, EVENT, NOW, api([prev(status="in_progress")])) == (
        False, "OTHER_SOURCE_ATTEMPT_UNCERTAIN", 120)


def test_different_prior_shanghai_calendar_day_is_not_duplicate():
    assert gate.should_capture(ENV, EVENT, NOW,
        api([prev(at="2026-10-08T10:00:00Z")])) == (
        True, "FIRST_QUALIFIED_SOURCE_ATTEMPT", None)


def test_wrong_upstream_event_fails_before_github_api_read():
    invalid = {"workflow_run": {**EVENT["workflow_run"], "path": ".github/workflows/decision-inbox.yml"}}
    with pytest.raises(ValueError, match="UPSTREAM_EVENT_IDENTITY"):
        gate.should_capture(ENV, invalid, NOW, lambda _: 1 / 0)


def test_preclose_is_suppressed_and_wrong_schedule_refused():
    before = datetime(2026, 10, 9, 6, 30, tzinfo=timezone.utc)
    assert gate.should_capture(ENV, EVENT, before, lambda _: 1 / 0)[1] == (
        "OUTSIDE_AUTHORIZED_AFTER_CLOSE_WINDOW")
    with pytest.raises(ValueError, match="SCHEDULE_IDENTITY"):
        gate.should_capture({**ENV, "GITHUB_EVENT_NAME": "schedule"},
                            {"schedule": "35 12 * * 1-5"}, NOW, api([]))
