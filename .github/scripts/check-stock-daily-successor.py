#!/usr/bin/env python3
"""Validate one eligible Sector successor and reuse the shared-Key activity check.

This adapter never reads the market credential, dispatches a workflow, polls,
retries, or writes production state. It validates the exact workflow_run identity,
classifies an explicit workflow_dispatch from the already-recorded upstream job
steps, proves the exact saved Sector result required by Stock when requested, and
performs the existing bounded GitHub metadata observation with the four workflows
known to share the repository HiThink key.
"""
from __future__ import annotations

import hashlib
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
HASH = re.compile(r"[0-9a-f]{64}\Z")
ACTIVITY_SCRIPT = Path(__file__).with_name("check-sector-scheduled-activity.py")
MAX_JOBS_BYTES = 2 * 1024 * 1024
MAX_AUDIT_JSON_BYTES = 8 * 1024 * 1024
PRODUCER_STEP = "Run independent Sector Radar shadow producer"
REPLAY_STEP = "Verify exact offline replay before publication"
STATE_UPLOAD_STEP = "Upload authoritative state bundle"
MISSED_ADOPT_STEP = "Adopt exact 2026-09-14 missed-session checkpoint"
MISSED_VERIFY_STEP = "Verify 2026-09-14 missed-session adoption exact offline match"
RECOVERY_ADOPT_STEP = "Adopt exact recovery checkpoint into original Sector lineage"
RECOVERY_VERIFY_STEP = "Verify recovery adoption exact offline match"
ELIGIBLE_ORIGINS = frozenset({"GITHUB_SCHEDULE", "WORKFLOW_DISPATCH_PRODUCE"})
RESULT_STATUSES = frozenset({
    "APPENDED_COMPLETED_SESSION_QUIET",
    "APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES",
})
IDEMPOTENT_STATUS = "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"
IDEMPOTENT_UPDATE = "ALREADY_CURRENT_IDEMPOTENT"


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


def _plain_json(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _plain_json(value[key]) for key in sorted(value)}
    raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_JSON_TYPE_INVALID")


def _sealed(value: dict, field: str) -> bool:
    if not isinstance(value, dict) or HASH.fullmatch(str(value.get(field, ""))) is None:
        return False
    body = {key: value[key] for key in value if key != field}
    raw = json.dumps(_plain_json(body), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest() == value[field]


def _audit_json(path: Path, *, required: bool) -> dict | None:
    if path.is_symlink():
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_PATH_UNSAFE")
    if not path.exists():
        if required:
            raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_FILE_REQUIRED")
        return None
    if not path.is_file():
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_PATH_UNSAFE")
    try:
        size = path.stat().st_size
        if not 0 < size <= MAX_AUDIT_JSON_BYTES:
            raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_FILE_SIZE_INVALID")
        raw = path.read_bytes()
    except OSError:
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_UNREADABLE") from None
    try:
        value = json.loads(raw, object_pairs_hook=_object)
    except (ValueError, TypeError):
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_JSON_INVALID") from None
    if not isinstance(value, dict):
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_JSON_INVALID")
    _plain_json(value)
    return value


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


def validate_stock_input(path: str, env: Mapping[str, str]) -> bool:
    """Prove whether this exact successful Sector run has the result Stock requires."""
    root = Path(path)
    if not path or root.is_symlink() or not root.is_dir():
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_DIRECTORY_REQUIRED")
    operations = _audit_json(root / "operations.json", required=True)
    if not _sealed(operations, "operations_hash"):
        raise SuccessorCheckError("UPSTREAM_SECTOR_OPERATIONS_HASH_MISMATCH")
    expected = {
        "repository": REPOSITORY,
        "workflow_path": SECTOR_PATH,
        "run_id": int(env["UPSTREAM_RUN_ID"]),
        "run_attempt": 1,
        "commit_sha": env["UPSTREAM_HEAD_SHA"],
    }
    if any(operations.get(key) != value for key, value in expected.items()):
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_IDENTITY_DIFFERS")

    result_path = root / "result.json"
    if result_path.is_symlink():
        raise SuccessorCheckError("UPSTREAM_SECTOR_AUDIT_PATH_UNSAFE")
    result = _audit_json(result_path, required=False)
    if result is not None:
        if operations.get("status") not in RESULT_STATUSES:
            raise SuccessorCheckError("UPSTREAM_SECTOR_RESULT_STATUS_INVALID")
        if operations.get("state_update_status") != "APPENDED_NEW_COMPLETED_SESSION":
            raise SuccessorCheckError("UPSTREAM_SECTOR_RESULT_STATE_UPDATE_INVALID")
        if not _sealed(result, "result_hash"):
            raise SuccessorCheckError("UPSTREAM_SECTOR_RESULT_HASH_MISMATCH")
        if operations.get("result_hash") != result.get("result_hash"):
            raise SuccessorCheckError("UPSTREAM_SECTOR_RESULT_OPERATIONS_MISMATCH")
        return True

    if (
        operations.get("status") == IDEMPOTENT_STATUS
        and operations.get("state_update_status") == IDEMPOTENT_UPDATE
        and operations.get("result_hash") is None
        and operations.get("candidate_count") == 0
    ):
        return False
    raise SuccessorCheckError("UPSTREAM_SECTOR_RESULT_REQUIRED_FOR_STOCK")


def shared_key_blockers(read) -> list[int]:
    """Reuse the existing at-most-five-GET activity observation with Stock peers."""
    return activity_module()["check_activity"](read, peers=KEY_USERS)


def _write_output(values: dict[str, str]) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")


def _stock_input_main() -> int:
    market_run_id = None
    sector_origin = None
    ready = False
    try:
        market_run_id, sector_origin = validate_successor(os.environ)
        if not handoff_allowed(sector_origin):
            raise SuccessorCheckError("INELIGIBLE_SECTOR_ORIGIN_FOR_STOCK_INPUT")
        ready = validate_stock_input(os.environ.get("UPSTREAM_RUN_AUDIT", ""), os.environ)
        message, code = (
            ("EXACT_RESULT_BEARING_SECTOR_INPUT_READY", 0)
            if ready
            else ("ALREADY_CURRENT_NO_PROSPECTIVE_RESULT_NO_STOCK_HANDOFF", 0)
        )
    except SuccessorCheckError as exc:
        message, code = str(exc), 2
    _write_output({"stock_input_ready": "true" if ready else "false"})
    origin_text = f"\n\nSector origin: `{sector_origin}`." if sector_origin else ""
    text = (
        "### Stock input result gate\n\n"
        + message
        + origin_text
        + "\n\nOnly the exact retained Sector run artifact was inspected; no market request, fallback, latest lookup, retry or dispatch occurred.\n"
    )
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(text)
    return code


def _preflight_main() -> int:
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

    values = {"dispatch_allowed": "true" if dispatch_allowed else "false"}
    if dispatch_allowed:
        values.update(market_run_id=str(market_run_id), sector_origin=str(sector_origin))
    _write_output(values)
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


def main() -> int:
    mode = os.environ.get("SUCCESSOR_CHECK_MODE", "preflight")
    if mode == "preflight":
        return _preflight_main()
    if mode == "stock-input":
        return _stock_input_main()
    print("UNKNOWN_SUCCESSOR_CHECK_MODE")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
