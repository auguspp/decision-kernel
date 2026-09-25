"""Retain the newest TDX Concept source in the normal pinned read-model.

This reader never acquires market data. It selects only the newest main
workflow attempt, verifies the exact saved artifact with trusted installed
Kernel code, and retains a compact reading plus the exact source ZIP. A failed
or rejected newest attempt never falls back to an older success.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import zipfile

from . import current_state as model
from . import current_state_delivery as delivery
from . import tdx_concept_snapshot as tdx
from .institutional_radar_reading import ERRORS, _reserve, _run

WORKFLOW = ".github/workflows/tdx-concept-snapshot.yml"
QUERY = "actions/workflows/tdx-concept-snapshot.yml/runs?branch=main&per_page=20"
PREFIX = "details/radar/tdx-concept"


def native(collector):
    """Read/replay only the newest retained TDX main attempt."""
    collector.tdx_concept_read_attempt = None
    collector.tdx_concept_read_stage = "BUDGET_PREFLIGHT"
    _reserve(collector, calls=4, files=8)

    collector.tdx_concept_read_stage = "RUN_DISCOVERY"
    listing = collector.api.get(QUERY)
    runs = listing["workflow_runs"]
    model.check(
        isinstance(runs, list)
        and len(runs) <= 20
        and type(listing["total_count"]) is int
        and listing["total_count"] >= len(runs)
        and (runs or listing["total_count"] == 0),
        "TDX Concept run query incomplete",
    )
    model.check(len({run["id"] for run in runs}) == len(runs), "Duplicate TDX Concept run")
    if not runs:
        return {
            "status": "NOT_RUN_NOT_NO_ACTIVITY",
            "result": None,
            "meaning": "NO_RETAINED_TDX_RUN_NOT_ZERO_CONCEPT_ACTIVITY",
            **tdx.AUTHORITY,
        }

    selected = max(runs, key=lambda run: (model.clock(run["created_at"]), run["id"]))
    collector.tdx_concept_read_stage = "RUN_IDENTITY"
    _run(selected, cutoff=collector.now(), workflow=WORKFLOW)
    collector.tdx_concept_read_attempt = model.concise_run(selected)

    run = collector.api.get(f"actions/runs/{selected['id']}")
    _run(run, cutoff=collector.now(), workflow=WORKFLOW)
    model.check(
        all(run[key] == selected[key] for key in ("id", "head_sha", "created_at", "event", "run_attempt")),
        "TDX Concept selected run identity changed",
    )
    state = {
        "status": "LATEST_ATTEMPT_NOT_SUCCESSFUL",
        "latest_attempt": model.concise_run(run),
        "result": None,
        "query_scope": "NEWEST_TWENTY_MAIN_INVOCATIONS_NOT_ALL_HISTORY",
        "meaning": "NO_OLDER_SUCCESS_FALLBACK; NOT_ZERO_CONCEPT_ACTIVITY",
        **tdx.AUTHORITY,
    }
    if run["status"] != "completed" or run["conclusion"] != "success":
        return state
    _run(run, cutoff=collector.now(), completed=True, workflow=WORKFLOW)

    collector.tdx_concept_read_stage = "ARCHIVE_FETCH"
    artifact = model.select_artifact(
        collector.artifacts(run), f"tdx-concept-{run['id']}-1"
    )
    files, archive = collector.archive(artifact, run)
    expected = {
        "capture.json",
        "plan.json",
        "source.json",
        "observation.json",
        "summary.md",
        "source-files/.eltdx_board_cache.json",
        "source-files/infoharbor_block.dat",
        "source-files/tdxhy.cfg",
        "source-files/security_list.json",
    }
    model.check(set(files) == expected, "TDX Concept artifact file scope differs")

    collector.tdx_concept_read_stage = "PAYLOAD_REPLAY"
    receipt = json.loads(files["capture.json"])
    workflow = tdx.workflow_identity(receipt["workflow"], run["head_sha"])
    model.check(
        workflow["GITHUB_RUN_ID"] == str(run["id"])
        and receipt["status"] == "CAPTURED_TDX_CONCEPT_SNAPSHOT"
        and model.clock(run["created_at"])
        <= model.clock(receipt["started_at"])
        <= model.clock(receipt["finished_at"])
        <= model.clock(run["updated_at"]),
        "TDX Concept capture identity or clock differs",
    )

    # Never execute artifact code. Trusted installed Kernel code rebuilds the
    # observation from the exact retained source models/files.
    with tempfile.TemporaryDirectory(prefix="tdx-concept-read-") as directory:
        root = Path(directory)
        for name, raw in files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        replay = tdx.replay(root, expected_execution=workflow)

    report = json.loads(files["observation.json"])
    model.check(report == replay, "TDX Concept retained observation differs from replay")
    projection = report["projection"]

    collector.tdx_concept_read_stage = "READ_RETENTION"
    _reserve(collector, files=4)
    details = {
        "observation": collector.retain(PREFIX + "/observation.json", files["observation.json"]),
        "summary": collector.retain(PREFIX + "/summary.md", files["summary.md"]),
        "capture": collector.retain(PREFIX + "/capture.json", files["capture.json"]),
        "run": collector.retain(PREFIX + "/run.json", model.json_bytes(run)),
    }
    return {
        **state,
        "status": "VERIFIED_SAVED_TDX_CONCEPT_SOURCE",
        "result": {
            "market_session": projection["market_session"],
            "catalog_count": projection["catalog_count"],
            "coverage": projection["coverage"],
            "taxonomy": projection["taxonomy"],
            "period_basis": projection["period_basis"],
            "package_version": projection["package_version"],
            "wheel_sha256": projection["wheel_sha256"],
            "chosen_host": projection["chosen_host"],
            "projection_hash": report["projection_hash"],
        },
        "archive": archive,
        "details": details,
        "source_calls_during_replay": projection["source_calls_during_replay"],
        "meaning": (
            "READ_ONLY_COMPLETED_SESSION_MARKET_EXPRESSION; "
            "EXACT_ARCHIVE_REPLAYED_WITH_TRUSTED_CODE; "
            "NOT_RESEARCH_ODDS_OR_DECISION"
        ),
    }


def _attach_section(collector, baseline):
    before_files = dict(collector.files)
    before_cache = dict(collector.archive_cache)
    try:
        return native(collector)
    except ERRORS as exc:
        collector.files = before_files
        collector.archive_cache = before_cache
        return {
            "status": "UNAVAILABLE_OR_REJECTED_NOT_QUIET",
            "error_type": type(exc).__name__,
            "failed_stage": getattr(collector, "tdx_concept_read_stage", "UNKNOWN"),
            "latest_attempt": getattr(collector, "tdx_concept_read_attempt", None),
            "result": None,
            "meaning": (
                "TDX_CONCEPT_READ_GAP_NOT_ZERO_ACTIVITY; "
                "NO_OLDER_SUCCESS_FALLBACK; BASELINE_PRESERVED"
            ),
            **tdx.AUTHORITY,
        }


def attach(collector, baseline):
    """Compose one compact TDX source status into the existing read package."""
    model.validate_read_package(baseline)
    section = _attach_section(collector, baseline)
    research = deepcopy(baseline["research"])
    research["tdx_concept_context"] = section

    payload = model.assemble(
        code_commit=collector.code_commit,
        checked_at=collector.now(),
        check_started_at=baseline["checks"]["started_at"],
        lanes=baseline["lanes"],
        research=research,
        capabilities=baseline["capability_gaps"],
        refresh_identity=baseline["refresh"],
    )

    old_summary = model.render_summary(baseline).encode()
    root = collector.files["README.md"]
    model.check(root.startswith(old_summary), "TDX Concept original navigation differs")
    tail = root[len(old_summary):]

    line = (
        "\n[TDX 概念市场横截面](" + PREFIX + "/summary.md)"
        "；completed-session 1/5/10 Market Expression，不是 Research/Odds/Decision。\n"
        if section.get("details")
        else "\nTDX 概念市场横截面："
             + str(section["status"])
             + "；读取缺口不等于零概念变化。\n"
    )
    if line not in tail:
        tail += line.encode()

    replacements = {
        "current-state.json": model.read_package_bytes(payload),
        "README.md": model.render_summary(payload).encode() + tail,
    }
    model.check(
        sum(len(value) for key, value in collector.files.items() if key not in replacements)
        + sum(map(len, replacements.values()))
        <= delivery.MAX_RETAINED_OUTPUT,
        "TDX Concept retained byte budget",
    )
    _reserve(collector, replacements=replacements)
    collector.files.update(replacements)
    return payload
