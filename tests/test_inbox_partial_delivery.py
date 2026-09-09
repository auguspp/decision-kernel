"""Synthetic GitHub transport, real collector/archive/reading functions; no network."""
import copy
import io
import zipfile

import pytest

from decision_kernel.runtime import current_state as model
from decision_kernel.runtime.current_state_delivery import Collector

SHA = "a" * 40
NOW = "2026-09-09T15:00:00Z"


def run(number=10, conclusion="failure", day=9, **updates):
    value = {"id": number, "repository": {"full_name": model.REPOSITORY},
             "head_repository": {"full_name": model.REPOSITORY},
             "path": model.WORKFLOWS["inbox"], "head_branch": "main", "head_sha": SHA,
             "event": "schedule", "run_attempt": 1, "status": "completed", "conclusion": conclusion,
             "created_at": f"2026-09-{day:02}T13:00:00Z", "updated_at": f"2026-09-{day:02}T13:10:00Z"}
    return dict(value, **updates)


def jobs(value, inbox="success", disclosures="failure"):
    rows = []
    for index, (name, conclusion) in enumerate((("inbox", inbox), ("disclosures", disclosures))):
        rows.append({"id": value["id"] * 10 + index, "name": name, "run_id": value["id"],
                     "head_sha": value["head_sha"], "status": "completed", "conclusion": conclusion,
                     "started_at": value["created_at"], "completed_at": value["updated_at"],
                     "steps": [{"name": step, "status": "completed", "conclusion": "success"}
                               for step in ("Build Attention Inbox", "Upload mobile HTML snapshot")]})
    return {"total_count": 2, "jobs": rows}


class API:
    def __init__(self, values, job_data=None, broken=None):
        self.values, self.reads, self.downloads = values, [], []
        self.jobs = job_data or {v["id"]: jobs(v) for v in values}
        self.broken = broken
        self.raw = {}
        self.metadata = {}
        for v in values:
            memory = io.BytesIO()
            with zipfile.ZipFile(memory, "w") as archive:
                archive.writestr("summary.md", "Synthetic saved delivery; not fresh Odds")
                archive.writestr("index.html", "<p>Stored source text only</p>")
            raw = memory.getvalue()
            self.raw[v["id"]] = raw
            self.metadata[v["id"]] = {"id": v["id"], "name": "decision-inbox", "expired": False,
                "size_in_bytes": len(raw), "digest": "sha256:" + model.sha256(raw),
                "workflow_run": {"id": v["id"], "head_sha": v["head_sha"]}}

    def get(self, endpoint):
        self.reads.append(endpoint)
        if endpoint.startswith("actions/workflows/"):
            return {"total_count": len(self.values), "workflow_runs": copy.deepcopy(self.values)}
        number = int(endpoint.split("/")[2])
        if "/attempts/1/jobs?" in endpoint:
            result = self.jobs[number]
            if isinstance(result, Exception):
                raise result
            return copy.deepcopy(result)
        assert endpoint.endswith("/artifacts?per_page=100")
        item = dict(self.metadata[number])
        if self.broken == "expired":
            item["expired"] = True
        elif self.broken == "digest":
            item["digest"] = "sha256:" + "0" * 64
        elif self.broken == "foreign-artifact":
            item["workflow_run"] = {"id": 999, "head_sha": SHA}
        return {"total_count": 1, "artifacts": [item]}

    def archive(self, artifact):
        self.downloads.append(artifact["id"])
        return self.raw[artifact["id"]]


def collect(tmp_path, api, previous=None):
    reader = Collector(api, SHA, tmp_path, previous=previous, now=lambda: NOW)
    return reader, reader.lane("inbox")


def test_valid_inbox_survives_disclosure_failure_without_greenwashing(tmp_path):
    current, old = run(), run(9, "success", 8)
    api = API([old, current])
    reader, lane = collect(tmp_path, api)
    assert lane["latest_attempt"]["conclusion"] == "failure"
    assert lane["health"] == "LATEST_ATTEMPT_FAILED"
    saved = lane["last_qualified_result"]
    assert saved["run"]["id"] == 10 and saved["run"]["conclusion"] == "failure"
    assert saved["status"] == "SAVED_INBOX_DELIVERY_ONLY"
    assert saved["numeric_result_validation"] == "NOT_AVAILABLE_IN_EXISTING_ARTIFACT"
    assert saved["odds_recomputed"] is False and saved["market_session"] is None
    proof = saved["job_qualification"]
    assert proof["inbox_conclusion"] == "success"
    assert proof["sibling_jobs"][0]["name"] == "disclosures"
    assert proof["sibling_jobs"][0]["conclusion"] == "failure"
    retained = reader.files[proof["source"]["read_path"]]
    assert model.sha256(retained) == proof["source"]["sha256"]
    assert api.downloads == [10]
    assert sum("/attempts/1/jobs?" in entry for entry in api.reads) == 1
    assert "INBOX_HAS_NO_TYPED_RESULT_NOT_REVALIDATED_ODDS" in lane["gaps"]
    assert "LATEST_ATTEMPT_IS_NOT_A_NEW_QUALIFIED_DELIVERY" not in lane["gaps"]


@pytest.mark.parametrize("failure", ["expired", "digest", "foreign-artifact"])
def test_qualified_latest_delivery_bad_artifact_never_falls_back(tmp_path, failure):
    api = API([run(), run(9, "success", 8)], broken=failure)
    _, lane = collect(tmp_path, api)
    assert lane["last_qualified_result"] is None
    assert not any("runs/9/" in endpoint for endpoint in api.reads)
    assert lane["health"] == "LATEST_ATTEMPT_FAILED"


@pytest.mark.parametrize("defect", ["missing", "duplicate", "wrong-run", "wrong-sha", "partial",
    "unfinished", "no-upload", "future-clock", "reversed-clock", "transport"])
def test_job_proof_failure_is_visible_and_not_delivery(tmp_path, defect):
    current = run()
    data = jobs(current)
    first = data["jobs"][0]
    if defect == "missing":
        data = {"total_count": 1, "jobs": data["jobs"][1:]}
    elif defect == "duplicate":
        data["jobs"].append(copy.deepcopy(first)); data["total_count"] = 3
    elif defect == "wrong-run":
        first["run_id"] = 11
    elif defect == "wrong-sha":
        first["head_sha"] = "b" * 40
    elif defect == "partial":
        data["total_count"] = 101
    elif defect == "unfinished":
        first["status"] = "in_progress"
    elif defect == "no-upload":
        first["steps"].pop()
    elif defect == "future-clock":
        first["completed_at"] = "2026-09-10T00:00:00Z"
    elif defect == "reversed-clock":
        first["completed_at"] = "2026-09-09T12:00:00Z"
    else:
        data = RuntimeError("unavailable")
    api = API([current], {10: data})
    _, lane = collect(tmp_path, api)
    assert lane["last_qualified_result"] is None
    assert api.downloads == []
    assert lane["job_check_gaps"][0]["run_id"] == 10
    assert "INBOX_JOB_CHECK_INCOMPLETE_NOT_CURRENT_SUCCESS" in lane["gaps"]


def test_missing_latest_job_proof_keeps_older_success_historical_not_current(tmp_path):
    api = API([run(), run(9, "success", 8)], {10: RuntimeError("missing")})
    _, lane = collect(tmp_path, api)
    assert lane["last_qualified_result"]["run"]["id"] == 9
    assert lane["latest_attempt"]["id"] == 10 and lane["health"] == "LATEST_ATTEMPT_FAILED"
    assert "LATEST_ATTEMPT_IS_NOT_A_NEW_QUALIFIED_DELIVERY" in lane["gaps"]
    assert lane["job_check_gaps"]


@pytest.mark.parametrize("conclusion", ["failure", "skipped", "cancelled"])
def test_failed_or_skipped_inbox_is_never_rescued(tmp_path, conclusion):
    current = run()
    api = API([current], {10: jobs(current, inbox=conclusion)})
    _, lane = collect(tmp_path, api)
    assert lane["last_qualified_result"] is None and api.downloads == []
    assert lane["latest_job_check"]["inbox_conclusion"] == conclusion


@pytest.mark.parametrize("update", [{"run_attempt": 2}, {"head_sha": "invalid"},
    {"repository": {"full_name": "foreign/repo"}}, {"head_repository": {"full_name": "foreign/repo"}}])
def test_original_identity_guards_still_block(tmp_path, update):
    api = API([run(**update)])
    _, lane = collect(tmp_path, api)
    assert lane["last_qualified_result"] is None and api.downloads == []


def test_existing_whole_run_success_does_not_need_new_exception(tmp_path):
    api = API([run(conclusion="success")])
    _, lane = collect(tmp_path, api)
    assert lane["health"] == "LATEST_ATTEMPT_SUCCEEDED"
    assert "job_qualification" not in lane["last_qualified_result"]
    assert not any("/jobs?" in endpoint for endpoint in api.reads)


def test_markdown_table_remains_contiguous_and_failure_text_is_safe(tmp_path):
    api = API([run()])
    reader, inbox = collect(tmp_path, api)
    proof = inbox["last_qualified_result"]["job_qualification"]
    proof["sibling_jobs"][0]["name"] = "disclosures | [inject](url) <script>"
    blank = model.lane_reading(latest=None, qualified=None, failure="gap", checked_at=NOW, query_complete=False)
    packet = model.assemble(code_commit=SHA, checked_at=NOW, check_started_at=NOW,
        lanes={"sector": blank, "stock": blank, "inbox": inbox},
        research={"handoffs": {"active": []}}, capabilities=[], refresh_identity={})
    rendered = model.render_summary(packet)
    rows = rendered.splitlines()
    start = rows.index("|---|---|---|")
    assert all(rows[start + i].startswith("|") for i in (1, 2, 3))
    assert "日期未提供" in rows[start + 3] and "None /" not in rendered
    assert "整次 workflow：failure" in rendered and "<script>" not in rendered
    assert "[inject](url)" not in rendered
    model.validate_read_package(packet)
    assert all(packet[key] == "NONE" for key in model.AUTHORITY)
