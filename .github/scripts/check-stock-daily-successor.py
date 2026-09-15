#!/usr/bin/env python3
"""Validate one eligible Sector successor and reuse the shared-Key activity check.

This adapter never reads the market credential, dispatches a workflow, polls,
retries, or writes production state. It validates the exact workflow_run identity,
classifies an explicit workflow_dispatch from the already-recorded upstream job
steps, and performs the existing bounded GitHub metadata observation with the four
workflows known to share the repository HiThink key.
"""
from __future__ import annotations

import json
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
MAX_JOBS_BYTES = 2 * 1024 * 1024
PRODUCER_STEP = "Run independent Sector Radar shadow producer"
REPLAY_STEP = "Verify exact offline replay before publication"
STATE_UPLOAD_STEP = "Upload authoritative state bundle"
MISSED_ADOPT_STEP = "Adopt exact 2026-09-14 missed-session checkpoint"
MISSED_VERIFY_STEP = "Verify 2026-09-14 missed-session adoption exact offline match"
RECOVERY_ADOPT_STEP = "Adopt exact recovery checkpoint into original Sector lineage"
RECOVERY_VERIFY_STEP = "Verify recovery adoption exact offline match"
ELIGIBLE_ORIGINS = frozenset({"GITHUB_SCHEDULE", "WORKFLOW_DISPATCH_PRODUCE"})


class SuccessorCheckError(RuntimeError):
    """One fixed diagnostic for a successor that must fail closed."""


def activity_module() -> dict:
    return runpy.run_path(str(ACTIVITY_SCRIPT), run_name="stock_daily_activity_reuse")


def _object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SuccessorCheckError("UPSTREAM_JOBS_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def classify_workflow_dispatch(path: str) -> str:
    """Classify one successful Sector workflow_dispatch from its exact job steps."""
    if not path:
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_REQUIRED")
    try:
        raw = Path(path).read_bytes()
    except OSError:
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_UNREADABLE") from None
    if not raw or len(raw) > MAX_JOBS_BYTES:
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_SIZE_INVALID")
    try:
        payload = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, TypeError):
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_JSON_INVALID") from None
    if not isinstance(payload, dict):
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_INVALID")
    jobs, count = payload.get("jobs"), payload.get("total_count")
    if (
        not isinstance(jobs, list)
        or type(count) is not int
        or not 1 <= count <= 100
        or len(jobs) != count
    ):
        raise SuccessorCheckError("UPSTREAM_DISPATCH_JOBS_INCOMPLETE")
    producers = [job for job in jobs if isinstance(job, dict) and job.get("name") == "producer"]
    if len(producers) != 1:
        raise SuccessorCheckError("UPSTREAM_DISPATCH_PRODUCER_JOB_REQUIRED")
    job = producers[0]
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        raise SuccessorCheckError("UPSTREAM_DISPATCH_PRODUCER_JOB_NOT_SUCCESS")
    steps = job.get("steps")
    if not isinstance(steps, list) or not steps:
        raise SuccessorCheckError("UPSTREAM_DISPATCH_STEPS_REQUIRED")
    outcomes = {}
    for step in steps:
        if not isinstance(step, dict):
            raise SuccessorCheckError("UPSTREAM_DISPATCH_STEP_INVALID")
        name, status, conclusion = step.get("name"), step.get("status"), step.get("conclusion")
        if not isinstance(name, str) or not name or name in outcomes or status != "completed":
            raise SuccessorCheckError("UPSTREAM_DISPATCH_STEP_INVALID")
        if conclusion not in {"success", "failure", "cancelled", "skipped"}:
            raise SuccessorCheckError("UPSTREAM_DISPATCH_STEP_INVALID")
        outcomes[name] = conclusion

    produce_ok = all(
        outcomes.get(name) == "success"
        for name in (PRODUCER_STEP, REPLAY_STEP, STATE_UPLOAD_STEP)
    )
    adoption_success = [
        outcomes.get(MISSED_ADOPT_STEP) == "success" and outcomes.get(MISSED_VERIFY_STEP) == "success",
        outcomes.get(RECOVERY_ADOPT_STEP) == "success" and outcomes.get(RECOVERY_VERIFY_STEP) == "success",
    ]
    if produce_ok:
        if any(adoption_success):
            raise SuccessorCheckError("UPSTREAM_DISPATCH_OPERATION_AMBIGUOUS")
        return "WORKFLOW_DISPATCH_PRODUCE"
    if sum(adoption_success) == 1:
        if (
            outcomes.get(PRODUCER_STEP) != "skipped"
            or outcomes.get(REPLAY_STEP) != "skipped"
            or outcomes.get(STATE_UPLOAD_STEP) != "success"
        ):
            raise SuccessorCheckError("UPSTREAM_DISPATCH_RECOVERY_SHAPE_INVALID")
        return "WORKFLOW_DISPATCH_RECOVERY"
    raise SuccessorCheckError("UPSTREAM_DISPATCH_OPERATION_UNPROVEN")


def validate_successor(env: Mapping[str, str]) -> tuple[int, str]:
    """Admit one exact successful Sector run and preserve its real trigger origin."""
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
    upstream_event = env.get("UPSTREAM_EVENT")
    if (
        env.get("UPSTREAM_NAME") != SECTOR_WORKFLOW
        or env.get("UPSTREAM_PATH") != SECTOR_PATH
        or upstream_event not in {"schedule", "workflow_dispatch"}
        or env.get("UPSTREAM_STATUS") != "completed"
        or env.get("UPSTREAM_CONCLUSION") != "success"
        or env.get("UPSTREAM_RUN_ATTEMPT") != "1"
        or env.get("UPSTREAM_HEAD_BRANCH") != "main"
        or env.get("UPSTREAM_HEAD_REPOSITORY") != REPOSITORY
        or SHA.fullmatch(env.get("UPSTREAM_HEAD_SHA", "")) is None
        or POSITIVE.fullmatch(env.get("UPSTREAM_RUN_ID", "")) is None
    ):
        raise SuccessorCheckError("ELIGIBLE_SECTOR_SUCCESS_IDENTITY_REQUIRED")
    if env["UPSTREAM_RUN_ID"] == env["GITHUB_RUN_ID"]:
        raise SuccessorCheckError("UPSTREAM_RUN_CANNOT_BE_SUCCESSOR_RUN")
    origin = (
        "GITHUB_SCHEDULE"
        if upstream_event == "schedule"
        else classify_workflow_dispatch(env.get("UPSTREAM_JOBS_JSON", ""))
    )
    return int(env["UPSTREAM_RUN_ID"]), origin


def handoff_allowed(origin: str) -> bool:
    return origin in ELIGIBLE_ORIGINS


def shared_key_blockers(read) -> list[int]:
    """Reuse the existing at-most-five-GET activity observation with Stock peers."""
    return activity_module()["check_activity"](read, peers=KEY_USERS)


def main() -> int:
    checker = activity_module()
    market_run_id = None
    sector_origin = None
    dispatch_allowed = False
    try:
        market_run_id, sector_origin = validate_successor(os.environ)
        if not handoff_allowed(sector_origin):
            message, code = "INELIGIBLE_RECOVERY_DISPATCH_NO_STOCK_HANDOFF", 0
        else:
            blockers = checker["check_activity"](
                checker["request_reader"](os.environ.get("GITHUB_TOKEN", "")),
                peers=KEY_USERS,
            )
            if blockers:
                raise SuccessorCheckError(
                    "BLOCKED_SHARED_KEY_ACTIVITY run_ids=" + ",".join(map(str, blockers))
                )
            message, code = "NO_VISIBLE_PEER_ACTIVITY_NOT_A_GLOBAL_LOCK", 0
            dispatch_allowed = True
    except (SuccessorCheckError, checker["CheckError"]) as exc:
        message, code = str(exc), 2

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"dispatch_allowed={'true' if dispatch_allowed else 'false'}\n")
            if dispatch_allowed:
                stream.write(f"market_run_id={market_run_id}\n")
                stream.write(f"sector_origin={sector_origin}\n")
    origin_text = f"\n\nSector origin: `{sector_origin}`." if sector_origin else ""
    text = (
        "### Stock daily successor preflight\n\n"
        + message
        + origin_text
        + "\n\nNo market request, workflow dispatch, polling or retry occurred in this step.\n\n"
        "A workflow_dispatch producer remains workflow_dispatch in lineage; it is not relabelled as a native schedule run.\n\n"
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
