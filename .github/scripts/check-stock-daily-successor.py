#!/usr/bin/env python3
"""Validate one natural Sector successor and reuse the shared-Key activity check.

This adapter never reads the market credential, dispatches a workflow, polls,
retries, or writes production state.  It only validates the exact workflow_run
identity and performs the existing bounded GitHub metadata observation with the
four workflows known to share the repository HiThink key.
"""
from __future__ import annotations

import os
import re
import runpy
from pathlib import Path
from typing import Mapping

REPOSITORY = "auguspp/decision-kernel"
SUCCESSOR_WORKFLOW = "stock-reading-after-sector"
SECTOR_WORKFLOW = "sector-radar-shadow"
SECTOR_PATH = ".github/workflows/sector-radar-shadow.yml"
KEY_USERS = frozenset({
    ".github/workflows/sector-radar-shadow.yml",
    ".github/workflows/hithink-stock-dump-trial.yml",
    ".github/workflows/decision-inbox.yml",
    ".github/workflows/live-dogfood.yml",
})
POSITIVE = re.compile(r"[1-9][0-9]{0,19}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
ACTIVITY_SCRIPT = Path(__file__).with_name("check-sector-scheduled-activity.py")


class SuccessorCheckError(RuntimeError):
    """One fixed diagnostic for a successor that must fail closed."""


def activity_module() -> dict:
    return runpy.run_path(str(ACTIVITY_SCRIPT), run_name="stock_daily_activity_reuse")


def validate_successor(env: Mapping[str, str]) -> int:
    """Admit only a fresh same-code successor of a natural successful Sector run."""
    if (
        env.get("GITHUB_REPOSITORY") != REPOSITORY
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_WORKFLOW") != SUCCESSOR_WORKFLOW
        or env.get("GITHUB_EVENT_NAME") != "workflow_run"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
        or SHA.fullmatch(env.get("GITHUB_SHA", "")) is None
        or POSITIVE.fullmatch(env.get("GITHUB_RUN_ID", "")) is None
    ):
        raise SuccessorCheckError("FRESH_MAIN_SUCCESSOR_REQUIRED")
    if (
        env.get("UPSTREAM_NAME") != SECTOR_WORKFLOW
        or env.get("UPSTREAM_PATH") != SECTOR_PATH
        or env.get("UPSTREAM_EVENT") != "schedule"
        or env.get("UPSTREAM_STATUS") != "completed"
        or env.get("UPSTREAM_CONCLUSION") != "success"
        or env.get("UPSTREAM_RUN_ATTEMPT") != "1"
        or env.get("UPSTREAM_HEAD_BRANCH") != "main"
        or env.get("UPSTREAM_HEAD_REPOSITORY") != REPOSITORY
        or SHA.fullmatch(env.get("UPSTREAM_HEAD_SHA", "")) is None
        or env.get("UPSTREAM_HEAD_SHA") != env.get("GITHUB_SHA")
        or POSITIVE.fullmatch(env.get("UPSTREAM_RUN_ID", "")) is None
    ):
        raise SuccessorCheckError("NATURAL_SECTOR_SUCCESS_IDENTITY_REQUIRED")
    if env["UPSTREAM_RUN_ID"] == env["GITHUB_RUN_ID"]:
        raise SuccessorCheckError("UPSTREAM_RUN_CANNOT_BE_SUCCESSOR_RUN")
    return int(env["UPSTREAM_RUN_ID"])


def shared_key_blockers(read) -> list[int]:
    """Reuse the existing at-most-five-GET activity observation with Stock peers."""
    return activity_module()["check_activity"](read, peers=KEY_USERS)


def main() -> int:
    checker = activity_module()
    market_run_id = None
    try:
        market_run_id = validate_successor(os.environ)
        blockers = checker["check_activity"](
            checker["request_reader"](os.environ.get("GITHUB_TOKEN", "")),
            peers=KEY_USERS,
        )
        if blockers:
            raise SuccessorCheckError(
                "BLOCKED_SHARED_KEY_ACTIVITY run_ids=" + ",".join(map(str, blockers))
            )
        message, code = "NO_VISIBLE_PEER_ACTIVITY_NOT_A_GLOBAL_LOCK", 0
    except (SuccessorCheckError, checker["CheckError"]) as exc:
        message, code = str(exc), 2

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"dispatch_allowed={'true' if code == 0 else 'false'}\n")
            if code == 0:
                stream.write(f"market_run_id={market_run_id}\n")
    text = (
        "### Stock daily successor preflight\n\n"
        + message
        + "\n\nNo market request, workflow dispatch, polling or retry occurred in this step.\n\n"
        "This is a bounded non-atomic repository observation, not provider quota proof or a global Key lock.\n"
    )
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
