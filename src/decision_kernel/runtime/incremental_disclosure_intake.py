"""Move one selected SAVED packet with GitHub's native create-only API.

No source fetch, model, Research, admission, Funnel, retry or registry mutation.
The existing read client stays read-scoped; two fixed-path writes use `gh api`.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import current_state as read
from . import incremental_disclosure as work
from .current_state_delivery import GitHubAPI
from .external_research_identity import _json

REQUEST_PATH = "research_runs/disclosure-intake-request.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def native_create(path: str, raw: bytes) -> dict:
    """Exactly one CLI call, never supply an existing SHA or follow a source URL."""
    prefix, name = path.rsplit("/", 1)
    key = prefix.removeprefix(work.WORK_PREFIX)
    read.check(prefix + "/packet.json" == work.request_path(key)
               and name in {"packet.json", "intake-plan.json"}, "write outside intake paths")
    payload = {"branch": work.WORK_REF, "content": base64.b64encode(raw).decode("ascii"),
               "message": "Retain selected disclosure " + key + ": " + name}
    result = subprocess.run(
        ["gh", "api", "--hostname", "github.com", "--method", "PUT",
         "repos/" + read.REPOSITORY + "/contents/" + path, "--input", "-"],
        input=json.dumps(payload).encode(), capture_output=True, timeout=60, check=False,
    )
    if result.returncode:
        # Write may have reached GitHub. Caller retains the attempt, never retries.
        raise RuntimeError("NATIVE_CREATE_FAILED_OR_UNCERTAIN_READBACK_REQUIRED")
    return _json(result.stdout)


def mutable_ref(api, name: str) -> str:
    value = api._call("GET", "git/ref/heads/" + name).json()["object"]
    read.check(value["type"] == "commit" and read.SHA.fullmatch(value["sha"]), "invalid ref")
    return value["sha"]


def work_inventory(api, commit: str) -> tuple[dict, dict[str, bytes]]:
    tree = api.get("git/trees/" + commit + "?recursive=1")
    rows = tree["tree"]
    read.check(tree.get("truncated") is False and len(rows) <= 2048, "work tree incomplete")
    names = [r["path"] for r in rows]
    read.check(len(names) == len(set(names)), "duplicate work tree path")
    files = {}
    for row in rows:
        path = read.safe_path(row["path"])
        if row["type"] == "tree":
            continue
        read.check(row["type"] == "blob" and row["mode"] == "100644"
                   and (path == "README.md" or path.startswith(work.WORK_PREFIX)), "unsafe work tree")
        read.check(type(row["size"]) is int and 0 <= row["size"] <= read.MAX_ARCHIVE, "work file size")
        # Original _history inspects all paths, but needs bytes only for packets.
        # Auxiliary records are inventoried, not falsely claimed to be body-read.
        files[path] = b""
        if path.endswith("/packet.json"):
            raw = api.file(path, commit)
            read.check(read.blob_sha(raw) == row["sha"] and len(raw) == row["size"], "work blob mismatch")
            files[path] = raw
    read.check("README.md" in files and sum(map(len, files.values())) <= read.MAX_EXPANDED, "work inventory bound")
    work._history(files)
    return tree, files


def intake(*, api, request: dict, code_commit: str, output: Path,
           create=native_create, now=utc_now) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        with (output / name).open("xb") as f:
            f.write(value if isinstance(value, bytes) else read.json_bytes(value))
    receipt = {"schema_version": 1, "started_at": now(), "code_commit": code_commit,
               "status": "INTAKE_INCOMPLETE", "phase": "request", "formal_research_executed": False,
               "automatic_retry": False, **read.AUTHORITY}
    try:
        read.check(read.SHA.fullmatch(code_commit) is not None, "code must be pinned")
        read.check(set(request) == {"schema_version", "source_run_id", "artifact_id", "expected_work_commit",
                    "expected_key", "expected_packet_sha256", "expires_at"}
                    and request["schema_version"] == 1, "invalid intake request")
        read.check(all(type(request[k]) is int and request[k] > 0 for k in ("source_run_id", "artifact_id")), "invalid ids")
        path = work.request_path(request["expected_key"])
        read.check(read.SHA.fullmatch(request["expected_work_commit"]) is not None
                   and re.fullmatch(r"[0-9a-f]{64}", request["expected_packet_sha256"]), "invalid binding")
        save("request.json", request)
        read.check(mutable_ref(api, "main") == code_commit, "trusted main moved")
        receipt["phase"] = "work_inventory"
        before = mutable_ref(api, work.WORK_REF)
        tree, files = work_inventory(api, before)
        save("work-inventory.json", tree)
        receipt["work_commit_before"] = before
        if path in files:
            read.check(read.sha256(files[path]) == request["expected_packet_sha256"], "retained packet differs")
            receipt["status"] = "ALREADY_RESERVED_NO_EXECUTION"
            return receipt
        read.check(before == request["expected_work_commit"], "work inventory moved before reservation")
        read.check(read.clock(now()) <= read.clock(request["expires_at"]), "intake request expired")
        receipt["phase"] = "source_archive"
        run = api.get("actions/runs/" + str(request["source_run_id"]))
        read.run_identity(run, "inbox", success=True)
        read.check(run["id"] == request["source_run_id"], "wrong source run")
        data = api.get(f"actions/runs/{run['id']}/artifacts?per_page=100")
        read.check(data["total_count"] == len(data["artifacts"]) <= 100, "artifact enumeration incomplete")
        chosen = [a for a in data["artifacts"] if a["name"] == "official-disclosure-scan"]
        read.check(len(chosen) == 1 and chosen[0]["id"] == request["artifact_id"], "scan artifact differs")
        artifact = chosen[0]
        save("source-run.json", run); save("source-artifact.json", artifact)
        raw = api.archive(artifact)
        save("source.zip", raw)
        plan = work.plan_one(archive_raw=raw, artifact=artifact, run=run, work_files=files,
                             work_commit=before, selected_at=now())
        save("plan.json", plan)
        read.check(plan["selected"] is not None
                   and plan["selected"]["assessment_input_hash"] == request["expected_key"], "FIFO selection changed")
        path, packet = work.reservation(plan, raw, artifact, run)
        read.check(read.sha256(packet) == request["expected_packet_sha256"], "selected bytes differ")
        save("packet.json", packet)
        read.check(mutable_ref(api, "main") == code_commit
                   and mutable_ref(api, work.WORK_REF) == before, "main or work moved before write")
        read.check(read.clock(now()) <= read.clock(request["expires_at"]), "intake request expired")
        receipt["phase"] = "create_packet"
        response = create(path, packet)
        committed = response["commit"]["sha"]
        read.check(read.SHA.fullmatch(committed) is not None
                   and response["content"]["sha"] == read.blob_sha(packet), "create response differs")
        receipt.update(reservation_commit=committed, packet_path=path,
                       packet_blob=read.blob_sha(packet), packet_sha256=read.sha256(packet))
        receipt["phase"] = "packet_readback"
        read.check(api.file(path, committed) == packet, "exact packet readback failed")
        receipt["phase"] = "create_plan"
        plan_path = path.rsplit("/", 1)[0] + "/intake-plan.json"
        plan_raw = read.json_bytes({"plan": plan, "intake_code_commit": code_commit,
                                   "reservation_commit": committed, "research_execution": "NOT_EXECUTED"})
        response = create(plan_path, plan_raw)
        plan_commit = response["commit"]["sha"]
        read.check(read.SHA.fullmatch(plan_commit) is not None
                   and response["content"]["sha"] == read.blob_sha(plan_raw)
                   and api.file(plan_path, plan_commit) == plan_raw, "exact plan readback failed")
        receipt.update(status="RESERVED_EXACT_BYTES_NOT_RESEARCH", phase="complete",
                       plan_commit=plan_commit, plan_hash=plan["plan_hash"], packet_count=plan["packet_count"])
        return receipt
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        receipt["error_type"] = type(exc).__name__
        # No second write, source fetch, repair or new key is attempted here.
        raise
    finally:
        receipt["finished_at"] = now()
        save("receipt.json", receipt)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--code-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        read.check(os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "rerun intake rejected")
        api = GitHubAPI(os.environ["GH_TOKEN"])
        request = _json(Path(REQUEST_PATH).read_bytes())
        result = intake(api=api, request=request, code_commit=args.code_commit, output=args.output)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("INTAKE_INCOMPLETE: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
