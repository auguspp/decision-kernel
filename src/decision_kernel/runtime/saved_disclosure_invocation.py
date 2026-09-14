"""A first-addition request adapter for the EXISTING saved-disclosure host.

This checks an invocation, not Research admission or permission semantics. The
original host owns sources, permission, work deduplication, Pre/Quick and writes.
No model/source transport, new execution identity, retry or generic dispatcher.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from . import current_state as read
from .external_research_identity import _json
from .incremental_disclosure import WORK_REF
from .incremental_disclosure_intake import mutable_ref

DIRECTORY = ".github/saved-disclosure-invocations/"
CONTINUATION_PATH = "research_runs/disclosure-continuation-request.json"
PROFILE = "SAVED_DISCLOSURE_MAIN_REQUEST_V1"
FIELDS = {"schema_version", "profile", "approved_parent", "source_run_id",
          "reading_commit", "work_commit", "continuation_sha256", "expires_at"}


def git_read(*args: str) -> bytes:
    result = subprocess.run(["git", *args], capture_output=True, timeout=30, check=False)
    read.check(result.returncode == 0, "invocation Git read failed")
    return result.stdout


def resolve(*, api, env: dict, git=git_read, checked_at: str) -> dict:
    """Check one request-only commit; return only the original bounded CLI inputs."""
    read.check(env.get("GITHUB_REPOSITORY") == read.REPOSITORY
               and env.get("GITHUB_REF") == "refs/heads/main"
               and env.get("GITHUB_EVENT_NAME") == "push"
               and env.get("GITHUB_RUN_ATTEMPT") == "1", "unsupported invocation event")
    before, head = env.get("SOURCE_BASE", ""), env.get("GITHUB_SHA", "")
    read.check(isinstance(before, str) and isinstance(head, str)
               and read.SHA.fullmatch(before) and read.SHA.fullmatch(head)
               and before != "0" * 40 and head != before, "invalid invocation commits")
    read.check(git("rev-parse", "HEAD").decode().strip() == head
               and git("show", "-s", "--format=%P", head).decode().split() == [before],
               "invocation must have the exact single reviewed parent")
    changed = git("diff", "--no-renames", "--name-status", "-z", before, head).split(b"\0")
    read.check(len(changed) == 3 and changed[0] == b"A" and changed[-1] == b"",
               "activation commit must add exactly one request and nothing else")
    path = changed[1].decode("utf-8")
    read.check(re.fullmatch(re.escape(DIRECTORY) + r"(?:scan-[1-9][0-9]*|continue-[0-9a-f]{64})\.json", path),
               "unsupported invocation path")
    # Check the committed mode, not a potentially substituted worktree file.
    entry = git("ls-tree", head, "--", path).decode().rstrip("\n").split("\t")
    read.check(len(entry) == 2 and entry[1] == path
               and entry[0].startswith("100644 blob "), "invocation is not a regular Git blob")
    # A deleted old request may not be re-added under the same stable name.
    prior = api.get("commits?sha=" + before + "&path=" + quote(path, safe="/") + "&per_page=1")
    read.check(prior == [], "invocation request already has history")
    raw = git("show", head + ":" + path)
    read.check(len(raw) <= 4096 and read.blob_sha(raw) == entry[0].split()[2], "invocation byte identity differs")
    request = _json(raw)  # Original duplicate-key and bounded JSON checks.
    read.check(set(request) == FIELDS and type(request["schema_version"]) is int
               and request["schema_version"] == 1 and request["profile"] == PROFILE
               and request["approved_parent"] == before, "unsupported invocation request")
    source = request["source_run_id"]
    read.check(type(source) is int and 0 < source < 10**20, "invalid invocation source run")
    for key in ("reading_commit", "work_commit"):
        read.check(isinstance(request[key], str) and read.SHA.fullmatch(request[key]), "invocation ref not pinned")
    continuation = request["continuation_sha256"]
    read.check(continuation is None or isinstance(continuation, str)
               and re.fullmatch(r"[0-9a-f]{64}", continuation), "invalid continuation digest")
    expected_name = "scan-" + str(source) if continuation is None else "continue-" + continuation
    read.check(path == DIRECTORY + expected_name + ".json", "invocation name differs from its stable identity")
    if continuation is not None:
        # Original continuation.check still decides admissibility and genuine permission.
        read.check(read.sha256(git("show", head + ":" + CONTINUATION_PATH)) == continuation,
                   "original continuation request differs")
    read.check(mutable_ref(api, "main") == head, "invocation main moved")
    read.check(mutable_ref(api, read.READ_REF) == request["reading_commit"], "invocation reading moved")
    read.check(mutable_ref(api, WORK_REF) == request["work_commit"], "invocation work moved")
    reading_raw = api.file("current-state.json", request["reading_commit"])
    read.check(len(reading_raw) <= read.MAX_ARCHIVE, "reading input exceeds original bound")
    reading = json.loads(reading_raw)
    read.validate_read_package(reading)  # Existing identity/clock/authority contract.
    read.check(reading["code_commit"] == before, "reading does not bind the reviewed parent")
    read.check(read.clock(reading["checks"]["finished_at"]) <= read.clock(checked_at)
               < read.clock(request["expires_at"]) <= read.clock(reading["checks"]["recheck_after"]),
               "invocation clock outside checked reading window")
    return {"status": "REQUEST_CHECKED_NOT_RESEARCH", "profile": PROFILE,
            "request_path": path, "request_git_blob": read.blob_sha(raw),
            "request_sha256": read.sha256(raw), "approved_parent": before,
            "code_commit": head, "checked_at": checked_at, "source_run_id": source,
            "reading_commit": request["reading_commit"], "work_commit": request["work_commit"],
            "continuation_sha256": continuation, "automatic_retry": False,
            "meaning": "INVOCATION_ONLY_ORIGINAL_HOST_ADMISSION_PERMISSION_AND_DEDUP_STILL_REQUIRED",
            **read.AUTHORITY}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    read.check(not any(p.is_symlink() for p in (args.output, *args.output.parents)), "unsafe invocation output")
    args.output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "INVOCATION_REJECTED_NOT_RESEARCH", "automatic_retry": False, **read.AUTHORITY}
    api = None
    try:
        from .current_state_delivery import GitHubAPI
        api = GitHubAPI(os.environ["GH_TOKEN"])
        receipt = resolve(api=api, env=os.environ, checked_at=datetime.now(timezone.utc).isoformat())
        (args.output / "request.json").write_bytes(git_read("show", receipt["code_commit"] + ":" + receipt["request_path"]))
        # Values are checked decimal / boolean / SHA tokens, never shell fragments.
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write(f"source_run_id={receipt['source_run_id']}\n")
            stream.write("continuation=" + str(receipt["continuation_sha256"] is not None).lower() + "\n")
            stream.write("reading_commit=" + receipt["reading_commit"] + "\n")
            stream.write("work_commit=" + receipt["work_commit"] + "\n")
    except Exception as exc:
        receipt["status"] = "INVOCATION_REJECTED_NOT_RESEARCH"
        receipt["error_type"] = type(exc).__name__
        print(receipt["status"])
        return 2
    finally:
        (args.output / "invocation.json").write_bytes(read.json_bytes(receipt))
        if api is not None:
            api.session.close()
    print(receipt["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
