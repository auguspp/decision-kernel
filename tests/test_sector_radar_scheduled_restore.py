"""Native workflow frontier checks, using synthetic API pages and no remote I/O.

Both triggers retain one lineage. HTTP 200 or a sorted success-only page is not
freshness evidence. These tests do not certify live acquisition or publication.
"""
from copy import deepcopy
from urllib.parse import parse_qs, urlsplit

import pytest

from decision_kernel.runtime.sector_radar_persistence import (
    SECTOR_RADAR_STATE_ARTIFACT_NAME,
)
from decision_kernel.runtime.sector_radar_producer import (
    SECTOR_RADAR_WORKFLOW_FILE,
    SECTOR_RADAR_WORKFLOW_PATH,
    SectorRadarProducerError,
    discover_previous_sector_radar_artifact,
)


def run_row(run_id, number, *, event="workflow_dispatch", branch="main",
            status="completed", conclusion="success"):
    return {"id": run_id, "run_number": number, "workflow_id": 7,
            "path": SECTOR_RADAR_WORKFLOW_PATH, "event": event,
            "head_branch": branch, "status": status, "conclusion": conclusion,
            "run_attempt": 1, "head_sha": "a" * 40}


def page_rows(events=("schedule", "workflow_dispatch")):
    return [run_row(103, 3, status="in_progress", conclusion=None),
            run_row(102, 2, event=events[0]), run_row(99, 1, event=events[1])]


def response_reader(events=("schedule", "workflow_dispatch"), *,
                    newest_artifact="available", rows=None):
    calls = []
    rows = page_rows(events) if rows is None else deepcopy(rows)

    def read(url):
        calls.append(url)
        parsed = urlsplit(url)
        if "/workflows/" in parsed.path:
            query = parse_qs(parsed.query)
            assert query == {"per_page": ["20"]}
            return {"total_count": len(rows), "workflow_runs": deepcopy(rows)}
        assert parsed.path.endswith("/artifacts")
        run_id = int(parsed.path.split("/")[-2])
        assert run_id in (102, 99)
        if newest_artifact == "missing":
            return {"total_count": 0, "artifacts": []}
        artifact = {"id": 500 + run_id, "name": SECTOR_RADAR_STATE_ARTIFACT_NAME,
                    "expired": newest_artifact == "expired", "size_in_bytes": 123}
        artifacts = [artifact, dict(artifact)] if newest_artifact == "duplicate" else [artifact]
        return {"total_count": len(artifacts), "artifacts": artifacts}

    return read, calls


def discover(read):
    return discover_previous_sector_radar_artifact(
        repository="auguspp/decision-kernel",
        workflow_file=SECTOR_RADAR_WORKFLOW_FILE,
        current_run_id=103, token=None, request_json=read,
    )


@pytest.mark.parametrize("events", [
    ("schedule", "workflow_dispatch"),
    ("workflow_dispatch", "schedule"),
    ("schedule", "schedule"),
])
def test_newest_success_is_not_hidden_by_its_trigger(events):
    read, calls = response_reader(events)
    result = discover(read)
    assert result.prior_success_found and result.artifact_available
    assert result.prior_run_id == 102 and result.artifact_id == 602
    assert result.prior_run_attempt == 1 and result.prior_head_sha == "a" * 40
    assert len(calls) == 2 and "/runs/102/artifacts" in calls[1]
    assert not any("/runs/99/artifacts" in url for url in calls)


@pytest.mark.parametrize("condition", ["missing", "expired"])
def test_newest_scheduled_artifact_failure_never_falls_back_to_manual(condition):
    read, calls = response_reader(newest_artifact=condition)
    result = discover(read)
    assert result.prior_success_found and not result.artifact_available
    assert result.prior_run_id == 102
    assert result.artifact_expired == (True if condition == "expired" else None)
    assert result.artifact_id == (602 if condition == "expired" else None)
    assert len(calls) == 2 and "/runs/102/artifacts" in calls[1]
    assert not any("/runs/99/artifacts" in url for url in calls)


@pytest.mark.parametrize("damage", [
    "stale", "empty", "hole", "duplicate_id", "duplicate_number", "wrong_workflow",
    "wrong_path", "missing_number", "boolean_number", "unknown_branch",
    "current_not_main", "unknown_conclusion", "unfinished_main", "oversized",
])
def test_unqualified_frontier_fails_before_artifact_or_bootstrap(damage):
    rows = page_rows()
    if damage == "stale": rows = rows[1:]
    elif damage == "empty": rows = []
    elif damage == "hole": rows.pop(1)
    elif damage == "duplicate_id": rows[2]["id"] = rows[1]["id"]
    elif damage == "duplicate_number": rows[2]["run_number"] = rows[1]["run_number"]
    elif damage == "wrong_workflow": rows[1]["workflow_id"] = 8
    elif damage == "wrong_path": rows[1]["path"] = ".github/workflows/another.yml"
    elif damage == "missing_number": del rows[1]["run_number"]
    elif damage == "boolean_number": rows[1]["run_number"] = True
    elif damage == "unknown_branch": rows[1]["head_branch"] = None
    elif damage == "current_not_main": rows[0]["head_branch"] = "candidate"
    elif damage == "unknown_conclusion": rows[1]["conclusion"] = None
    elif damage == "unfinished_main": rows[1].update(status="in_progress", conclusion=None)
    else: rows = [run_row(200 + n, n + 1) for n in range(21)]
    read, calls = response_reader(rows=rows)
    with pytest.raises(SectorRadarProducerError):
        discover(read)
    assert len(calls) == 1 and "/workflows/" in calls[0]


def test_page_order_and_newer_invocation_do_not_select_another_parent():
    rows = page_rows()
    # Deliberately oldest-first, plus a later successful invocation. Neither
    # list position nor numerically largest run_id selects the predecessor.
    rows = [rows[2], run_row(104, 4), rows[0], rows[1]]
    read, calls = response_reader(rows=rows)
    assert discover(read).prior_run_id == 102
    assert len(calls) == 2 and "/runs/102/artifacts" in calls[1]


@pytest.mark.parametrize("intervening", ["failed", "non_main"])
def test_complete_intervening_non_successes_do_not_hide_the_prior_success(intervening):
    rows = page_rows()
    if intervening == "failed": rows[1]["conclusion"] = "failure"
    else: rows[1]["head_branch"] = "candidate"
    read, calls = response_reader(rows=rows)
    assert discover(read).prior_run_id == 99
    assert len(calls) == 2 and "/runs/99/artifacts" in calls[1]


@pytest.mark.parametrize("first_run", [True, False])
def test_bootstrap_requires_observed_prefix_to_workflow_run_one(first_run):
    rows = [run_row(103, 1, status="in_progress", conclusion=None)] if first_run else page_rows()
    if not first_run:
        rows[1]["conclusion"] = rows[2]["conclusion"] = "failure"
    read, calls = response_reader(rows=rows)
    result = discover(read)
    assert not result.prior_success_found and not result.artifact_available
    assert result.prior_run_id is None and len(calls) == 1


def test_window_exhaustion_is_not_no_prior_success():
    rows = [run_row(103, 30, status="in_progress", conclusion=None)]
    rows.extend(run_row(200 + n, n, conclusion="failure") for n in range(29, 10, -1))
    read, calls = response_reader(rows=rows)
    with pytest.raises(SectorRadarProducerError, match="missing workflow run number 10"):
        discover(read)
    assert len(calls) == 1


def test_selected_artifact_ambiguity_does_not_search_older_success():
    read, calls = response_reader(newest_artifact="duplicate")
    with pytest.raises(SectorRadarProducerError, match="duplicate state artifacts"):
        discover(read)
    assert len(calls) == 2 and "/runs/102/artifacts" in calls[1]
