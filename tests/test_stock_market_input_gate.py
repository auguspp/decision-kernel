from copy import deepcopy
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json

import pytest

path = Path(__file__).resolve().parents[1] / '.github/scripts/stock-market-input-gate.py'
spec = spec_from_file_location("stock_market_input_gate", path)
gate = module_from_spec(spec)
spec.loader.exec_module(gate)
NOW = datetime(2026, 10, 9, 10, 25, tzinfo=timezone.utc)
ENV = {"GITHUB_REPOSITORY": gate.REPOSITORY, "GITHUB_REF": "refs/heads/main",
       "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": "124", "GITHUB_EVENT_NAME": "workflow_run",
       "GITHUB_JOB": gate.SOURCE_JOB, "GITHUB_SHA": "a"*40,
       "GITHUB_WORKFLOW_REF": gate.REPOSITORY+"/.github/workflows/"+gate.WORKFLOW+"@refs/heads/main"}
EVENT = {"workflow_run": {"path": gate.SECTOR_PATH, "head_branch": "main",
          "head_repository": {"full_name": gate.REPOSITORY}, "run_attempt": 1,
          "status": "completed", "conclusion": "failure"}}


def api(runs, artifacts=None, jobs=None, total=None):
    artifacts, jobs = artifacts or {}, jobs or {}
    def get(path):
        if path.endswith("runs?branch=main&per_page=100"):
            return {"workflow_runs": runs, "total_count": len(runs) if total is None else total}
        run_id = int(path.split("/runs/")[1].split("/")[0])
        if "/jobs?" in path:
            rows = jobs.get(run_id, [])
            return {"jobs": rows, "total_count": len(rows)}
        rows = artifacts.get(run_id, [])
        return {"artifacts": rows, "total_count": len(rows)}
    return get


def prev(id=120, status="completed", at="2026-10-09T10:00:00Z"):
    return {"id": id, "display_title": gate.SOURCE_TITLE, "created_at": at,
            "head_branch": "main", "status": status, "run_attempt": 1,
            "path": ".github/workflows/"+gate.WORKFLOW,
            "repository": {"full_name": gate.REPOSITORY},
            "head_repository": {"full_name": gate.REPOSITORY}}


def source_job(id=120, status="completed", capture="skipped"):
    return {"run_id": id, "name": gate.SOURCE_JOB, "status": status,
            "steps": [] if status == "queued" else [
                {"name": gate.CAPTURE_STEP, "status": "completed", "conclusion": capture}]}


def test_sector_completion_even_on_failure_allows_independent_dated_input():
    assert gate.should_capture(ENV, EVENT, NOW, api([])) == (
        True, "FIRST_QUALIFIED_SOURCE_ATTEMPT", None)


def test_previous_actual_source_artifact_for_today_blocks_all_duplicate_source():
    saved = {"name": "stock-market-inputs-120-1", "expired": False}
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], {120: [saved]})) == (
        False, "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE", 120)


def test_prior_no_source_or_uncertain_run_fails_closed():
    for status in ("completed", "in_progress"):
        assert gate.should_capture(ENV, EVENT, NOW, api([prev(status=status)])) == (
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


def test_queued_sibling_cannot_deadlock_the_running_source_job():
    queued = prev(125, "in_progress", "2026-10-09T10:24:00Z")
    assert gate.should_capture(ENV, EVENT, NOW,
        api([queued], jobs={125: [source_job(125, "queued")]}))[0] is True
    # Once this job has retained an input, the later-running sibling is blocked.
    saved = {"name": "stock-market-inputs-124-1", "expired": False}
    assert gate.should_capture({**ENV, "GITHUB_RUN_ID": "125"}, EVENT, NOW,
        api([prev(124)], {124: [saved]})) == (
        False, "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE", 124)


def test_skipped_capture_is_zero_source_but_does_not_hide_older_attempt():
    recent = prev(123)
    jobs = {123: [source_job(123)]}
    assert gate.should_capture(ENV, EVENT, NOW, api([recent], jobs=jobs))[0] is True
    saved = {"name": "stock-market-inputs-120-1", "expired": False}
    assert gate.should_capture(ENV, EVENT, NOW,
        api([recent, prev(120)], {120: [saved]}, jobs)) == (
        False, "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE", 120)


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled", "timed_out"])
def test_started_capture_without_artifact_never_authorizes_source_retry(outcome):
    assert gate.should_capture(ENV, EVENT, NOW,
        api([prev()], jobs={120: [source_job(capture=outcome)]})) == (
        False, "OTHER_SOURCE_ATTEMPT_UNCERTAIN", 120)


def test_expired_source_artifact_still_counts_as_a_consumed_attempt():
    saved = {"name": "stock-market-inputs-120-1", "expired": True}
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], {120: [saved]}))[0] is False


def test_incomplete_history_and_six_candidate_bound_do_not_call_source():
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], total=101))[1] == (
        "RUN_QUERY_SCOPE_INCOMPLETE")
    runs = [prev(id) for id in range(110, 117)]
    jobs = {run['id']: [source_job(run['id'])] for run in runs}
    assert gate.should_capture(ENV, EVENT, NOW, api(runs, jobs=jobs))[1] == (
        "RUN_QUERY_SCOPE_INCOMPLETE")


def test_skip_artifact_name_alone_does_not_prove_no_source_request():
    marker = {"name": "stock-market-inputs-skip-120-1", "expired": False}
    assert gate.should_capture(ENV, EVENT, NOW, api([prev()], {120: [marker]}))[1] == (
        "OTHER_SOURCE_ATTEMPT_UNCERTAIN")


@pytest.mark.parametrize("fault", ["job_identity", "wrong_workflow", "rerun", "capture_started"])
def test_untrusted_native_source_state_is_not_a_zero_request_claim(fault):
    old, job = prev(), source_job(status="queued")
    if fault == "job_identity":
        job['run_id'] = 999
    elif fault == "wrong_workflow":
        old['path'] = '.github/workflows/foreign.yml'
    elif fault == "rerun":
        old['run_attempt'] = 2
    else:
        job['steps'] = [{"name": gate.CAPTURE_STEP, "status": "in_progress",
                         "started_at": NOW.isoformat()}]
    assert gate.should_capture(ENV, EVENT, NOW,
        api([old], jobs={120: [job]}))[1] == "OTHER_SOURCE_ATTEMPT_UNCERTAIN"


def test_native_api_failure_is_not_swallowed_as_permission_to_capture():
    with pytest.raises(RuntimeError, match="denied"):
        gate.should_capture(ENV, EVENT, NOW, lambda _: (_ for _ in ()).throw(RuntimeError("denied")))


def test_create_only_skip_receipt_is_written_before_workflow_output(tmp_path, monkeypatch):
    event = tmp_path/'event.json'
    event.write_text(json.dumps(EVENT))
    output, marker = tmp_path/'output.txt', tmp_path/'skip'
    for key, value in {**ENV, 'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output)}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(gate, 'should_capture', lambda *_: (
        False, 'SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE', 120))
    monkeypatch.setattr('sys.argv', ['gate', '--output', str(marker)])
    assert gate.main() == 0
    assert json.loads((marker/'skip.json').read_text())['source_requests'] == 0
    assert output.read_text() == 'capture=false\n'
    output.unlink()
    with pytest.raises(FileExistsError):
        gate.main()
    assert not output.exists()
