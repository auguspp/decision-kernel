"""Bounded native GitHub day gate for the existing dated stock input job.

The existing job concurrency group supplies exclusion. Native job/step evidence
separates queued or skipped source work from a consumed/uncertain source attempt.
No source endpoint, new cron, credential, or durable coordination store is added.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time as elapsed_time
from zoneinfo import ZoneInfo

REPOSITORY = "auguspp/decision-kernel"
WORKFLOW = "stock-reading-after-sector.yml"
SOURCE_TITLE = "stock-market-inputs"
SOURCE_JOB = "daily-market-inputs"
CAPTURE_STEP = "Capture current dated stock inputs"
SECTOR_PATH = ".github/workflows/sector-radar-shadow.yml"
ZONE = ZoneInfo("Asia/Shanghai")
MAX_PRIOR_CHECKS = 6


def _clock(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("CLOCK_ZONE")
    return parsed.astimezone(timezone.utc)


def _collection(payload, key):
    rows, total = payload.get(key), payload.get("total_count")
    if (not isinstance(rows, list) or type(total) is not int
            or total < len(rows) or len(rows) > 100):
        raise ValueError("GITHUB_COLLECTION_SHAPE")
    return rows, total


def validate_trigger(env, event):
    if env.get("GITHUB_REPOSITORY") != REPOSITORY or env.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("SOURCE_REPOSITORY_REF")
    if (env.get("GITHUB_RUN_ATTEMPT") != "1"
            or re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")) is None
            or env.get("GITHUB_JOB") != SOURCE_JOB
            or env.get("GITHUB_WORKFLOW_REF") != REPOSITORY+"/.github/workflows/"+WORKFLOW+"@refs/heads/main"
            or re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", "")) is None):
        raise ValueError("SOURCE_ATTEMPT_IDENTITY")
    kind = env.get("GITHUB_EVENT_NAME")
    if kind == "workflow_run":
        parent = event.get("workflow_run") or {}
        if not (parent.get("path") == SECTOR_PATH and parent.get("head_branch") == "main"
                and (parent.get("head_repository") or {}).get("full_name") == REPOSITORY
                and parent.get("run_attempt") == 1 and parent.get("status") == "completed"):
            raise ValueError("UPSTREAM_EVENT_IDENTITY")
    elif kind == "schedule":
        if event.get("schedule") != "35 10 * * 1-5":
            raise ValueError("SCHEDULE_IDENTITY")
    elif kind == "workflow_dispatch":
        if (event.get("inputs") or {}).get("mode") != "market-inputs":
            raise ValueError("DISPATCH_MODE_IDENTITY")
    else:
        raise ValueError("SOURCE_EVENT_IDENTITY")
    return kind


def _prior_source_state(api_get, run):
    """Only native evidence of unstarted/skipped capture can release a date."""
    if (run.get("path") != ".github/workflows/"+WORKFLOW or run.get("run_attempt") != 1
            or run.get("head_branch") != "main"
            or (run.get("repository") or {}).get("full_name") != REPOSITORY
            or (run.get("head_repository") or {}).get("full_name") != REPOSITORY):
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    root = f"repos/{REPOSITORY}/actions/runs/{run['id']}"
    artifacts, total = _collection(api_get(root+"/artifacts?per_page=100"), "artifacts")
    # Even an expired or unverified source artifact means an attempt may have
    # consumed the source budget. Its name is NOT data qualification.
    if any(a.get("name") == f"stock-market-inputs-{run['id']}-1" for a in artifacts):
        return "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE"
    if total != len(artifacts):
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    jobs, total = _collection(api_get(root+"/jobs?filter=latest&per_page=100"), "jobs")
    source_jobs = [job for job in jobs if job.get("name") == SOURCE_JOB]
    if total != len(jobs) or len(source_jobs) != 1:
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    job = source_jobs[0]
    if job.get("run_id") != run['id']:
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    steps = job.get("steps")
    if not isinstance(steps, list):
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    capture = [step for step in steps if step.get("name") == CAPTURE_STEP]
    if len(capture) > 1:
        return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"
    if job.get("status") in ("queued", "waiting", "pending"):
        if not capture or (capture[0].get("status") in ("queued", "pending")
                           and not capture[0].get("started_at")):
            return "NO_SOURCE_STARTED"
    if (job.get("status") == "completed" and len(capture) == 1
            and capture[0].get("status") == "completed"
            and capture[0].get("conclusion") == "skipped"):
        return "NO_SOURCE_STARTED"
    return "OTHER_SOURCE_ATTEMPT_UNCERTAIN"


def should_capture(env, event, now, api_get):
    kind = validate_trigger(env, event)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("CLOCK_ZONE")
    local = now.astimezone(ZONE)
    if kind != "workflow_dispatch" and (local.weekday() >= 5 or local.time() < time(15, 30)):
        return False, "OUTSIDE_AUTHORIZED_AFTER_CLOSE_WINDOW", None
    cutoff = datetime.combine(local.date(), time(15, 30), ZONE).astimezone(timezone.utc)
    runs, total = _collection(api_get(
        f"repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?branch=main&per_page=100"),
        "workflow_runs")
    parsed = sorted(runs, key=lambda x: (_clock(x["created_at"]), x["id"]), reverse=True)
    if total > len(parsed) and (not parsed or _clock(parsed[-1]["created_at"]) >= cutoff):
        return False, "RUN_QUERY_SCOPE_INCOMPLETE", None
    checked = 0
    for old in parsed:
        if str(old.get("id")) == env["GITHUB_RUN_ID"] or old.get("display_title") != SOURCE_TITLE:
            continue
        if _clock(old["created_at"]) < cutoff:
            break
        if checked == MAX_PRIOR_CHECKS:
            return False, "RUN_QUERY_SCOPE_INCOMPLETE", None
        checked += 1
        state = _prior_source_state(api_get, old)
        if state != "NO_SOURCE_STARTED":
            return False, state, old["id"]
    return True, "FIRST_QUALIFIED_SOURCE_ATTEMPT", None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    deadline = elapsed_time.monotonic() + 45
    def api_get(path):
        remaining = deadline - elapsed_time.monotonic()
        if remaining <= 0:
            raise ValueError("GITHUB_READ_BUDGET_EXHAUSTED")
        response = subprocess.run(["gh", "api", path], check=True, text=True,
                                  capture_output=True, timeout=min(10, remaining))
        return json.loads(response.stdout)
    now = datetime.now(timezone.utc)
    allowed, reason, prior = should_capture(os.environ, event, now, api_get)
    # Complete the zero-source receipt BEFORE exporting false to the workflow.
    # A write failure remains a gate failure, never a success without evidence.
    if not allowed:
        root = Path(args.output)
        root.mkdir(parents=True, exist_ok=False)
        marker = {"version": "daily-stock-native-skip-v1", "repository": REPOSITORY,
                  "run_id": int(os.environ["GITHUB_RUN_ID"]), "head_sha": os.environ["GITHUB_SHA"],
                  "reason": reason, "prior_run_id": prior, "source_requests": 0,
                  "recorded_at": now.isoformat()}
        (root/"skip.json").write_text(json.dumps(marker, sort_keys=True)+"\n", encoding="utf-8")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fp:
        fp.write(f"capture={'true' if allowed else 'false'}\n")
    print("source_capture_gate="+("ALLOW" if allowed else reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
