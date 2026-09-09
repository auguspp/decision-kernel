"""Synthetic GitHub responses, real original scan/packet/FIFO/archive functions."""
import base64
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import incremental_disclosure_intake as intake
from test_incremental_disclosure import packet, scan, SHA, NOW

W = "b" * 40


class API:
    def __init__(self, raws, history=None):
        self.raw, self.artifact, self.run = scan(raws)
        self.tip, self.code = W, SHA
        self.history = {"README.md": b"data only", **(history or {})}
        self.snapshots = {W: copy.deepcopy(self.history)}
        self.reads, self.writes, self.downloads = [], [], 0
        self.defect, self.fail_write = None, None

    def _call(self, method, endpoint):
        assert method == "GET"
        self.reads.append(endpoint)
        value = self.code if endpoint == "git/ref/heads/main" else self.tip
        return SimpleNamespace(json=lambda: {"object": {"type": "commit", "sha": value}})

    def get(self, endpoint):
        self.reads.append(endpoint)
        if endpoint.startswith("git/trees/"):
            rows = [{"path": p, "type": "blob", "mode": "100644", "size": len(b), "sha": read.blob_sha(b)}
                    for p, b in self.history.items()]
            if self.defect == "symlink": rows[0]["mode"] = "120000"
            if self.defect == "wrong-blob": rows[-1]["sha"] = "d" * 40
            return {"tree": rows, "truncated": self.defect == "truncated"}
        if endpoint == "actions/runs/10": return copy.deepcopy(self.run)
        assert endpoint == "actions/runs/10/artifacts?per_page=100"
        rows = [copy.deepcopy(self.artifact)]
        if self.defect == "duplicate-artifact": rows.append(copy.deepcopy(rows[0]))
        return {"artifacts": rows, "total_count": len(rows) + (1 if self.defect == "partial-artifacts" else 0)}

    def archive(self, artifact):
        self.downloads += 1
        return self.raw

    def file(self, path, ref):
        self.reads.append((path, ref))
        raw = self.snapshots[ref][path]
        return raw + b"bad" if self.defect == "readback" and ref != W else raw

    def create(self, path, raw):
        self.writes.append((path, raw))
        assert path not in self.history  # Simulated native create-only constraint.
        if self.fail_write == "before": raise RuntimeError("write response lost")
        self.history[path] = raw
        self.tip = f"{len(self.writes):040x}"
        self.snapshots[self.tip] = copy.deepcopy(self.history)
        if self.fail_write == "after": raise RuntimeError("write response lost after server commit")
        return {"commit": {"sha": self.tip}, "content": {"sha": read.blob_sha(raw)}}


def request(raw):
    return {"schema_version": 1, "source_run_id": 10, "artifact_id": 100,
            "expected_work_commit": W, "expected_key": work._packet(raw).assessment_input_hash,
            "expected_packet_sha256": read.sha256(raw), "expires_at": "2026-09-10T00:00:00Z"}


def execute(tmp_path, api, req, name="out"):
    return intake.intake(api=api, request=req, code_commit=SHA, output=tmp_path/name,
                         create=api.create, now=lambda: NOW)


def test_intake_preserves_exact_unicode_and_original_fifo(tmp_path):
    earlier = packet(day=5)
    selected = packet(code="300750", day=8, title="保存原字节\n𠮷与吉不相同")
    later = packet(code="600036", day=8)
    history = {work.request_path(work._packet(earlier).assessment_input_hash): earlier}
    api = API([later, selected, earlier], history)
    result = execute(tmp_path, api, request(selected))
    assert result["status"] == "RESERVED_EXACT_BYTES_NOT_RESEARCH"
    assert api.writes[0][1] == selected and len(api.writes) == 2 and api.downloads == 1
    assert result["packet_sha256"] == read.sha256(selected)
    plan = json.loads((tmp_path/"out"/"plan.json").read_bytes())
    assert plan["packet_count"] == 3 and plan["reserved_count"] == 1
    assert not result["formal_research_executed"] and not result["automatic_retry"]
    assert all(result[key] == "NONE" for key in read.AUTHORITY)
    assert api.history[next(iter(history))] == earlier


def test_existing_reservation_never_selects_replacement_or_reads_archive(tmp_path):
    raw = packet(); path = work.request_path(work._packet(raw).assessment_input_hash)
    api = API([raw, packet(day=8)], {path: raw, path.replace("packet.json", "failure.json"): b"{}"})
    api.tip = "c" * 40; api.snapshots[api.tip] = dict(api.history)
    result = execute(tmp_path, api, request(raw))
    assert result["status"] == "ALREADY_RESERVED_NO_EXECUTION"
    assert not api.writes and api.downloads == 0


@pytest.mark.parametrize("defect", ["truncated", "symlink", "wrong-blob", "missing-packet"])
def test_bad_work_history_blocks_before_source_or_write(tmp_path, defect):
    old = packet(day=5); selected = packet(day=8)
    path = work.request_path(work._packet(old).assessment_input_hash)
    api = API([selected], {path: old}); api.defect = defect
    if defect == "missing-packet":
        api.history = {"README.md": b"data", path.replace("packet.json", "failure.json"): b"{}"}
    with pytest.raises(ValueError): execute(tmp_path, api, request(selected))
    assert api.downloads == 0 and not api.writes
    assert json.loads((tmp_path/"out"/"receipt.json").read_bytes())["status"] == "INTAKE_INCOMPLETE"


@pytest.mark.parametrize("defect", ["expired", "wrong-key", "work-moved", "main-moved", "digest", "rerun", "duplicate-artifact", "partial-artifacts"])
def test_identity_boundaries_and_fifo_are_not_relaxed(tmp_path, defect):
    raw = packet(); api = API([raw]); req = request(raw)
    api.defect = defect
    if defect == "expired": req["expires_at"] = "2026-09-08T00:00:00Z"
    if defect == "wrong-key": req["expected_key"] = "c" * 64
    if defect == "work-moved": req["expected_work_commit"] = "d" * 40
    if defect == "main-moved": api.code = "e" * 40
    if defect == "digest": api.artifact["digest"] = "sha256:" + "0" * 64
    if defect == "rerun": api.run["run_attempt"] = 2
    with pytest.raises(ValueError): execute(tmp_path, api, req)
    assert not api.writes


@pytest.mark.parametrize("stage", ["before", "after"])
def test_uncertain_write_is_not_repeated(tmp_path, stage):
    raw = packet(); api = API([raw]); api.fail_write = stage
    with pytest.raises(RuntimeError): execute(tmp_path, api, request(raw))
    assert len(api.writes) == 1
    saved = json.loads((tmp_path/"out"/"receipt.json").read_bytes())
    assert saved["phase"] == "create_packet" and saved["status"] == "INTAKE_INCOMPLETE"
    if stage == "after":
        api.fail_write = None
        assert execute(tmp_path, api, request(raw), "later")["status"] == "ALREADY_RESERVED_NO_EXECUTION"
        assert len(api.writes) == 1  # No invented repair or second launch.


def test_failed_readback_keeps_reservation_without_plan_or_repair(tmp_path):
    raw = packet(); api = API([raw]); api.defect = "readback"
    with pytest.raises(ValueError): execute(tmp_path, api, request(raw))
    assert len(api.writes) == 1 and api.writes[0][0] in api.history
    result = json.loads((tmp_path/"out"/"receipt.json").read_bytes())
    assert result["phase"] == "packet_readback" and not result["formal_research_executed"]


def test_native_cli_uses_fixed_repo_no_shell_and_no_overwrite_sha(monkeypatch):
    key = "a" * 64; raw = "原字节𠮷\n".encode(); calls = []
    def run(args, **kw):
        calls.append((args, kw)); return SimpleNamespace(returncode=0, stdout=b'{"created":true}')
    monkeypatch.setattr(intake.subprocess, "run", run)
    assert intake.native_create(work.request_path(key), raw) == {"created": True}
    args, kw = calls[0]; body = json.loads(kw["input"])
    assert args[:5] == ["gh", "api", "--hostname", "github.com", "--method"]
    assert body["branch"] == work.WORK_REF and "sha" not in body
    assert base64.b64decode(body["content"]) == raw and kw.get("shell", False) is False
    with pytest.raises(ValueError): intake.native_create("src/packet.json", raw)
    assert len(calls) == 1


def test_workflow_reacts_only_to_changed_explicit_request_and_successful_main_ci():
    raw = Path(".github/workflows/incremental-disclosure-intake.yml").read_text()
    assert "workflow_run:" in raw and "event == 'push'" in raw and "conclusion == 'success'" in raw
    assert "run_attempt == 1" in raw and "fetch-depth: 2" in raw
    assert "git diff --quiet HEAD^1 HEAD -- research_runs/disclosure-intake-request.json" in raw
    assert "persist-credentials: false" in raw and "cancel-in-progress: false" in raw
    assert "secrets." not in raw and "workflow_dispatch:" not in raw and "schedule:" not in raw
    assert "actions: read" in raw and "actions: write" not in raw
