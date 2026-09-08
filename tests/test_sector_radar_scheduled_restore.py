"""Both producer triggers maintain one newest-success state lineage.

These are synthetic GitHub responses that honor the requested event filter,
not a natural schedule run or market/state publication acceptance.
"""
from urllib.parse import parse_qs, urlsplit

import pytest

from decision_kernel.runtime.sector_radar_persistence import (
    SECTOR_RADAR_STATE_ARTIFACT_NAME,
)
from decision_kernel.runtime.sector_radar_producer import (
    SECTOR_RADAR_WORKFLOW_FILE,
    discover_previous_sector_radar_artifact,
)


def response_reader(events, *, newest_artifact="available"):
    calls = []
    rows = [
        {"id": run_id, "event": event, "head_branch": "main",
         "conclusion": "success", "run_attempt": 1, "head_sha": "a" * 40}
        for run_id, event in zip((102, 99), events, strict=True)
    ]

    def read(url):
        calls.append(url)
        parsed = urlsplit(url)
        if "/workflows/" in parsed.path:
            query = parse_qs(parsed.query)
            assert query["branch"] == ["main"]
            assert query["status"] == ["success"]
            assert query["per_page"] == ["2"]
            # Model GitHub's actual filtering: the former manual-only query
            # would silently hide the newer scheduled success.
            selected = [row for row in rows
                        if "event" not in query or row["event"] in query["event"]]
            return {"total_count": len(selected), "workflow_runs": selected}
        assert parsed.path.endswith("/artifacts")
        run_id = int(parsed.path.split("/")[-2])
        assert run_id in (102, 99)
        if run_id == 102 and newest_artifact == "missing":
            return {"total_count": 0, "artifacts": []}
        return {"total_count": 1, "artifacts": [{
            "id": 500 + run_id, "name": SECTOR_RADAR_STATE_ARTIFACT_NAME,
            "expired": run_id == 102 and newest_artifact == "expired",
            "size_in_bytes": 123,
        }]}

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
    assert "event" not in parse_qs(urlsplit(calls[0]).query)
    assert len(calls) == 2
    assert "/runs/102/artifacts" in calls[1]
    assert not any("/runs/99/artifacts" in url for url in calls)


@pytest.mark.parametrize("condition", ["missing", "expired"])
def test_newest_scheduled_artifact_failure_never_falls_back_to_manual(condition):
    read, calls = response_reader(("schedule", "workflow_dispatch"),
                                  newest_artifact=condition)
    result = discover(read)
    assert result.prior_success_found and not result.artifact_available
    assert result.prior_run_id == 102
    assert result.artifact_expired == (True if condition == "expired" else None)
    assert result.artifact_id == (602 if condition == "expired" else None)
    assert len(calls) == 2
    assert "/runs/102/artifacts" in calls[1]
    assert not any("/runs/99/artifacts" in url for url in calls)
