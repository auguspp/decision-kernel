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
    envelope, archive = collector.archive(artifact, run)
    nested = "snapshot/capture.json" in envelope
    files = {k[len("snapshot/"):]: v for k, v in envelope.items() if k.startswith("snapshot/")} if nested else envelope
    long_files = {k[len("trend/"):]: v for k, v in envelope.items() if k.startswith("trend/")} if nested else {}
    if nested:
        model.check(all(k.startswith(("snapshot/", "trend/")) for k in envelope),
                    "TDX Concept envelope scope differs")
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
        long_state = {"status": "NOT_CAPTURED_LEGACY_SOURCE" if not nested else "UNAVAILABLE_OR_REJECTED",
                      "meaning": "LONG_HISTORY_GAP_NOT_NO_TREND"}
        long_outputs = {}
        if long_files:
            try:
                from . import tdx_concept_trend as trend
                model.check(set(long_files) <= trend.FILES and "capture.json" in long_files,
                            "TDX long history file scope differs")
                # Keep the old base tree unchanged: its strict inventory rejects siblings.
                with tempfile.TemporaryDirectory(prefix="tdx-trend-read-") as long_directory:
                    long_root = Path(long_directory)
                    for name, raw in long_files.items():
                        (long_root / name).write_bytes(raw)
                    cap = json.loads(long_files["capture.json"])
                    model.check(model.clock(run["created_at"]) <= model.clock(cap["started_at"])
                                <= model.clock(cap["finished_at"]) <= model.clock(run["updated_at"]),
                                "TDX long history run clock differs")
                    long_report = trend.replay(long_root, replay, receipt, json.loads(files["source.json"]))
                if "projection" in long_report:
                    lp = long_report["projection"]
                    long_state = {"status": "VERIFIED_SAVED_LONG_HISTORY",
                                  "projection_hash": long_report["projection_hash"],
                                  "catalog_count": lp["catalog_count"], "coverage": lp["coverage"]}
                    long_outputs = {k: long_files[k] for k in ("trend.json", "summary.md", "capture.json")}
                else:
                    long_state.update(long_report)
                    long_outputs = {"capture.json": long_files["capture.json"]}
            except (ImportError, *ERRORS) as exc:
                long_state["error_type"] = type(exc).__name__
                long_outputs = {}

        membership = {"status": "UNAVAILABLE_OR_REJECTED", "meaning": "MEMBERSHIP_GAP_NOT_NO_MEMBERS"}
        member_bytes = None
        try:
            from . import tdx_concept_membership as members
            member_report = members.build(root, replay, receipt)
            member_bytes = members.encoded(member_report)
            membership = {"status": "VERIFIED_SAVED_MEMBERSHIP",
                          "projection_hash": member_report["projection_hash"],
                          "catalog_count": member_report["projection"]["catalog_count"],
                          "relation_count": member_report["projection"]["relation_count"]}
        except (ImportError, *ERRORS) as exc:
            membership["error_type"] = type(exc).__name__

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
    if member_bytes is not None:
        member_files_before = dict(collector.files)
        try:
            _reserve(collector, files=1)
            membership["file"] = collector.retain(PREFIX + "/membership.json", member_bytes)
        except ERRORS as exc:
            collector.files = member_files_before
            membership = {"status": "UNAVAILABLE_OR_REJECTED", "error_type": type(exc).__name__,
                          "meaning": "MEMBERSHIP_GAP_NOT_NO_MEMBERS"}
    if long_outputs:
        before_long = dict(collector.files)
        try:
            _reserve(collector, files=len(long_outputs))
            long_state["details"] = {name: collector.retain(PREFIX + "/trend/" + name, raw)
                                     for name, raw in long_outputs.items()}
        except ERRORS as exc:
            collector.files = before_long
            long_state = {"status": "UNAVAILABLE_OR_REJECTED", "error_type": type(exc).__name__,
                          "meaning": "LONG_HISTORY_GAP_NOT_NO_TREND"}
    return {
        **state,
        "trend": long_state,
        "membership": membership,
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
    if section.get("membership", {}).get("file"):
        line += "\n[TDX 概念完整成员（同版本）](" + PREFIX + "/membership.json)；来源成员不是业务受益或持仓。\n"
    if section.get("trend", {}).get("status") == "VERIFIED_SAVED_LONG_HISTORY":
        line += "\n[概念5/20/60日相对走势与阶段](" + PREFIX + "/trend/summary.md)；同期基准、持续天数与缺口分别保留，不是投资信号。\n"
    elif section.get("details"):
        line += "\n概念20/60日相对走势尚未取得或通过校验；原短期行情与成员独立保留。\n"
    encoded_line = line.encode()
    if encoded_line not in tail:
        tail += encoded_line

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
