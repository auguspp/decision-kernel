from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import tdx_concept_reading as reading
from decision_kernel.runtime import tdx_concept_snapshot as tdx
from test_radar_company_reading import collector, baseline
from test_tdx_concept_snapshot import DAY, SHA, WF, fake_source

CUTOFF = "2026-09-25T05:00:00Z"
RUN_ID = 123456


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("unexpected network")
    monkeypatch.setattr(socket, "create_connection", denied)


def captured(tmp_path):
    root = tmp_path / "tdx"
    ticks = iter([
        datetime(2026, 9, 25, 4, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 25, 4, 0, 1, tzinfo=timezone.utc),
    ])
    tdx.capture(
        root,
        market_session=DAY,
        workflow=WF,
        expected_code=SHA,
        source_fn=fake_source,
        now=lambda: next(ticks),
    )
    files = {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }
    return files


def run(*, run_id=RUN_ID, conclusion="success"):
    return {
        "id": run_id,
        "head_sha": SHA,
        "head_branch": "main",
        "path": reading.WORKFLOW,
        "repository": {"full_name": m.REPOSITORY},
        "head_repository": {"full_name": m.REPOSITORY},
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": conclusion,
        "created_at": "2026-09-25T03:59:00Z",
        "updated_at": "2026-09-25T04:01:00Z",
        "run_started_at": "2026-09-25T03:59:05Z",
        "html_url": f"https://github.com/{m.REPOSITORY}/actions/runs/{run_id}",
    }


class API:
    def __init__(self):
        self.calls = 0
        self.max_calls = 252
        self.reads = []
        self.responses = {}
        self.raw = None

    def get(self, path):
        self.calls += 1
        self.reads.append(path)
        return deepcopy(self.responses[path])

    def archive(self, artifact):
        self.calls += 1
        self.reads.append("ARCHIVE")
        return self.raw


def zip_bytes(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return stream.getvalue()


def setup(tmp_path, *, files=None):
    files = files or captured(tmp_path)
    api = API()
    api.raw = zip_bytes(files)
    selected = run()
    artifact = {
        "id": 990,
        "name": f"tdx-concept-{RUN_ID}-1",
        "expired": False,
        "size_in_bytes": len(api.raw),
        "digest": "sha256:" + m.sha256(api.raw),
        "workflow_run": {"id": RUN_ID, "head_sha": SHA},
    }
    api.responses = {
        reading.QUERY: {"total_count": 1, "workflow_runs": [selected]},
        f"actions/runs/{RUN_ID}": selected,
        f"actions/runs/{RUN_ID}/artifacts?per_page=100": {
            "total_count": 1,
            "artifacts": [artifact],
        },
    }
    col = collector(api, tmp_path)
    col.now = lambda: CUTOFF
    base, _, _ = baseline(col)
    col.files["README.md"] += b"\nORIGINAL_NAV\n"
    return col, base, selected, artifact


def test_exact_artifact_replays_into_pinned_reading_without_new_source(tmp_path):
    col, base, _, _ = setup(tmp_path)
    result = reading.attach(col, base)
    m.validate_read_package(result)

    section = result["research"]["tdx_concept_context"]
    assert section["status"] == "VERIFIED_SAVED_TDX_CONCEPT_SOURCE"
    assert section["result"]["market_session"] == DAY.isoformat()
    assert section["result"]["catalog_count"] == 2
    assert section["result"]["coverage"]["eastmoney_required"] is False
    assert section["source_calls_during_replay"] == 0
    assert section["investment_authority"] == "NONE"
    assert col.files[section["archive"]["read_path"]] == col.api.raw
    assert json.loads(col.files[section["details"]["observation"]["read_path"]])["projection"]["catalog_count"] == 2
    assert b"ORIGINAL_NAV" in col.files["README.md"]
    assert "TDX 概念市场横截面".encode() in col.files["README.md"]


def test_newest_failed_attempt_never_falls_back_to_older_success(tmp_path):
    col, base, latest, _ = setup(tmp_path)
    latest["conclusion"] = "failure"
    old = {
        **run(run_id=RUN_ID - 1),
        "created_at": "2026-09-24T03:59:00Z",
        "updated_at": "2026-09-24T04:01:00Z",
    }
    col.api.responses[reading.QUERY] = {
        "total_count": 2,
        "workflow_runs": [latest, old],
    }
    col.api.responses[f"actions/runs/{RUN_ID}"] = latest

    result = reading.attach(col, base)
    section = result["research"]["tdx_concept_context"]
    assert section["status"] == "LATEST_ATTEMPT_NOT_SUCCESSFUL"
    assert section["result"] is None
    assert "ARCHIVE" not in col.api.reads
    assert not any(str(RUN_ID - 1) in path for path in col.api.reads)
    assert result["lanes"] == base["lanes"]


def test_no_run_is_explicit_not_zero_activity(tmp_path):
    col, base, _, _ = setup(tmp_path)
    col.api.responses[reading.QUERY] = {"total_count": 0, "workflow_runs": []}
    result = reading.attach(col, base)
    section = result["research"]["tdx_concept_context"]
    assert section["status"] == "NOT_RUN_NOT_NO_ACTIVITY"
    assert section["result"] is None
    assert result["lanes"] == base["lanes"]


@pytest.mark.parametrize("damage", ["hidden_missing", "expired", "digest", "rerun", "foreign", "future"])
def test_artifact_or_run_identity_failure_is_visible_and_does_not_search_older(tmp_path, damage):
    files = captured(tmp_path)
    if damage == "hidden_missing":
        files.pop("source-files/.eltdx_board_cache.json")
    col, base, selected, artifact = setup(tmp_path, files=files)
    old = {
        **run(run_id=RUN_ID - 1),
        "created_at": "2026-09-24T03:59:00Z",
        "updated_at": "2026-09-24T04:01:00Z",
    }
    col.api.responses[reading.QUERY] = {
        "total_count": 2,
        "workflow_runs": [selected, old],
    }

    if damage == "expired":
        artifact["expired"] = True
    elif damage == "digest":
        artifact["digest"] = "sha256:" + "0" * 64
    elif damage == "rerun":
        selected["run_attempt"] = 2
        col.api.responses[f"actions/runs/{RUN_ID}"]["run_attempt"] = 2
    elif damage == "foreign":
        selected["head_repository"]["full_name"] = "other/repo"
        col.api.responses[f"actions/runs/{RUN_ID}"]["head_repository"]["full_name"] = "other/repo"
    elif damage == "future":
        selected["updated_at"] = "2027-01-01T00:00:00Z"
        col.api.responses[f"actions/runs/{RUN_ID}"]["updated_at"] = "2027-01-01T00:00:00Z"

    # Keep artifact metadata internally consistent for the hidden-file case so
    # the reader reaches the exact required file-set gate.
    col.api.responses[f"actions/runs/{RUN_ID}/artifacts?per_page=100"]["artifacts"][0] = artifact

    result = reading.attach(col, base)
    section = result["research"]["tdx_concept_context"]
    assert section["status"] == "UNAVAILABLE_OR_REJECTED_NOT_QUIET"
    assert section["result"] is None
    assert not any(str(RUN_ID - 1) in path for path in col.api.reads)
    assert result["lanes"] == base["lanes"]


def test_workflows_retain_hidden_source_file_and_publish_tdx_reading():
    tdx_workflow = Path(".github/workflows/tdx-concept-snapshot.yml").read_text()
    assert "include-hidden-files: true" in tdx_workflow
    assert "schedule:" not in tdx_workflow and "secrets." not in tdx_workflow

    publisher = Path(".github/workflows/current-state-read-entry.yml").read_text()
    assert "tdx-concept-snapshot" in publisher
    assert "--include-tdx-concept-context" in publisher
    assert "schedule:" not in publisher
