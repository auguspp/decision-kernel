"""Bounded native GitHub day gate for the existing dated stock input job.

Preserves the current cron; a Sector completion is only a backup clock,
not a price source, research gate, or new provider subscription.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time, timezone
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

REPOSITORY = "auguspp/decision-kernel"
WORKFLOW = "stock-reading-after-sector.yml"
SOURCE_TITLE = "stock-market-inputs"
SECTOR_PATH = ".github/workflows/sector-radar-shadow.yml"
ZONE = ZoneInfo("Asia/Shanghai")


def validate_trigger(env, event):
    if env.get("GITHUB_REPOSITORY") != REPOSITORY or env.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("SOURCE_REPOSITORY_REF")
    if env.get("GITHUB_RUN_ATTEMPT") != "1" or not env.get("GITHUB_RUN_ID", "").isdigit():
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


def should_capture(env, event, now, api_get):
    kind = validate_trigger(env, event)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("CLOCK_ZONE")
    local = now.astimezone(ZONE)
    if kind != "workflow_dispatch" and (
            local.weekday() >= 5 or local.time() < time(15, 30)):
        return False, "OUTSIDE_AUTHORIZED_AFTER_CLOSE_WINDOW", None
    cutoff = datetime.combine(local.date(), time(15, 30), ZONE).astimezone(timezone.utc)
    run_info = api_get(f"repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?branch=main&per_page=100")
    runs = run_info.get("workflow_runs")
    if not isinstance(runs, list) or len(runs) > 100:
        raise ValueError("RUN_QUERY_SHAPE")
    parsed = sorted(runs, key=lambda x: (x["created_at"], x["id"]), reverse=True)
    if len(parsed) >= 100 and datetime.fromisoformat(
            parsed[-1]["created_at"].replace("Z", "+00:00")) >= cutoff:
        return False, "RUN_QUERY_SCOPE_INCOMPLETE", None
    for old in parsed:
        if str(old.get("id")) == env["GITHUB_RUN_ID"] or old.get("display_title") != SOURCE_TITLE:
            continue
        stamp = datetime.fromisoformat(old["created_at"].replace("Z", "+00:00"))
        if stamp < cutoff:
            break
        if old.get("head_branch") != "main":
            continue
        if old.get("status") != "completed":
            return False, "OTHER_SOURCE_ATTEMPT_UNCERTAIN", old["id"]
        found = api_get(f"repos/{REPOSITORY}/actions/runs/{old['id']}/artifacts?per_page=100")
        artifacts = found.get("artifacts")
        if not isinstance(artifacts, list):
            raise ValueError("ARTIFACT_QUERY_SHAPE")
        if any(item.get("name") == f"stock-market-inputs-{old['id']}-1"
               and not item.get("expired", False) for item in artifacts):
            return False, "SOURCE_ALREADY_RETAINED_THIS_CLOSE_DATE", old["id"]
        # The prior workflow may have attempted source I/O before upload failed,
        # or may itself be a qualified no-source skip. Neither authorizes a retry.
        return False, "OTHER_SOURCE_ATTEMPT_UNCERTAIN", old["id"]
    return True, "FIRST_QUALIFIED_SOURCE_ATTEMPT", None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    def api_get(path):
        response = subprocess.run(["gh", "api", path], check=True, text=True,
                                  capture_output=True, timeout=30)
        return json.loads(response.stdout)
    now = datetime.now(timezone.utc)
    allowed, reason, prior = should_capture(os.environ, event, now, api_get)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fp:
        fp.write(f"capture={'true' if allowed else 'false'}\n")
    if not allowed:
        root = Path(args.output)
        root.mkdir(parents=True, exist_ok=False)
        marker = {"version": "daily-stock-native-skip-v1", "repository": REPOSITORY,
                  "run_id": int(os.environ["GITHUB_RUN_ID"]),
                  "head_sha": os.environ["GITHUB_SHA"],
                  "reason": reason, "prior_run_id": prior,
                  "source_requests": 0, "recorded_at": now.isoformat()}
        (root/"skip.json").write_text(json.dumps(marker, sort_keys=True)+"\n",
                                      encoding="utf-8")
    print("source_capture_gate="+("ALLOW" if allowed else reason))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
