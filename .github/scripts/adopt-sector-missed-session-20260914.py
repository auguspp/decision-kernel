#!/usr/bin/env python3
"""Adopt one exact 2026-09-14 missed-session Sector reconstruction as restore state.

Case-bounded #375-A continuity only. Reconstructs from the exact retained failed
input audit, performs no market/provider request, preserves the 9/11 event ledger,
and publishes no retrospective 9/14 event. Remote restore authority exists only
after the original Sector workflow successfully uploads the resulting state bundle.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.sector_missed_session import (
    SEMANTICS as RECONSTRUCTION_SEMANTICS,
    STATUS as RECONSTRUCTION_STATUS,
    reconstruct_sector_prefix,
)
from decision_kernel.runtime.sector_radar_events import (
    parse_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_persistence import (
    load_sector_radar_persistent_bundle,
    write_sector_radar_persistent_bundle,
)
from decision_kernel.runtime.sector_radar_state import (
    parse_sector_radar_market_state,
    serialize_sector_radar_market_state,
)

REPO = "auguspp/decision-kernel"
WORKFLOW = ".github/workflows/sector-radar-shadow.yml"
OPERATION = "adopt-missed-session-2026-09-14"
ADOPTION_STATUS = "MISSED_SESSION_CHECKPOINT_ADOPTED_NO_RETROACTIVE_EVENT"
TARGET_SESSION = date(2026, 9, 14)
PARENT_HINT_HASH = "0b0b73e17da9019e4ce15af263394f0aafc5c49442c99babefbf43d15b6c6f38"

# Exact newest successful production parent before the missed 9/14 session.
PARENT_RUN_ID = 34610140283
PARENT_ARTIFACT_ID = 10268611038
PARENT_HEAD_SHA = "bb77bf82ef3bb5e8068cc966a7fa7b8fdf6fdd2d"
PARENT_STATE_HASH = "789f89ce5c6c795afb920494056b56fea7f8fc55cd9f6cd4fa98298c9b44183a"
PARENT_STATE_SHA256 = "3ed93f658bf87dd822ba6562b9003fe3ee504a2cdfb6b0cfaf0fd8d4ec598037"
PARENT_EVENT_SHA256 = "5eb51bb419185c3d7b461828ca6831ab7af5f87e37fafa5d13db3a17593ed25c"
PARENT_EVENT_LEDGER_HASH = "96e2c48a85b58f91f1bf635df061ee3f4ae450a19c35dac84329d0f49b55ee84"
PARENT_LAST_RESULT_HASH = "298039781fef0f8992c388bea7552428a286a4938dfd8c89a833e805c3702378"

# Exact failed natural source prefix retained from the 9/14 attempt.
SOURCE_RUN_ID = 34868170673
SOURCE_ARTIFACT_ID = 10358420687
SOURCE_HEAD_SHA = "2021f8a0999ce3eae299cea83800c803e23a44c7"
SOURCE_AUDIT_HASH = "788b8b89edd543026a6c0608ee61bfcc97c151257e44c115efe46ad30f971e69"
SOURCE_ARCHIVE_SHA256 = "00d0a785466e64de97541c47124f9540f1b0c522b724a1b0a7f8415ec5c7d3cd"

# Deterministic calculation bytes from merged #376. reconstructed_at/commit are
# intentionally outside this calculation identity and vary per recovery execution.
CANDIDATE_CALCULATION_HASH = "b661c6d16082f5b0d65505089a4682df6840b37e839acc58ba49f9630047fc9e"
CANDIDATE_STATE_HASH = "fe869bf419d4b4a75095578caf422d873082605635c84f490832358c2c6a8109"
CANDIDATE_STATE_SHA256 = "f97b5103f94d4dd47be0b913aa550d02f1c61f8b02b0a0a23a530f8ec30f44ac"
CANDIDATE_EVENT_SHA256 = PARENT_EVENT_SHA256

AUTHORITY = {
    "signal_transition_authority": "NONE",
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
}


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing regular file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def invocation() -> dict[str, Any]:
    env = os.environ
    require(env.get("GITHUB_REPOSITORY") == REPO, "repository identity changed")
    require(env.get("GITHUB_REF") == "refs/heads/main", "missed-session adoption requires main")
    require(env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "missed-session adoption must be manual")
    require(env.get("GITHUB_RUN_ATTEMPT") == "1", "missed-session adoption must use attempt 1")
    require(env.get("RECOVERY_OPERATION") == OPERATION, "missed-session adoption operation changed")
    require(not env.get("HITHINK_FINANCE_API_KEY"), "missed-session adoption must not receive market credential")
    run_id = env.get("GITHUB_RUN_ID", "")
    commit_sha = env.get("GITHUB_SHA", "")
    require(run_id.isdigit() and int(run_id) > 0, "invalid workflow run id")
    require(re.fullmatch(r"[0-9a-f]{40}", commit_sha) is not None, "invalid workflow commit")
    return {"run_id": int(run_id), "run_attempt": 1, "commit_sha": commit_sha}


def validate_parent(parent_dir: Path, *, discovered_run_id: int, discovered_artifact_id: int, discovered_head_sha: str):
    require(discovered_run_id == PARENT_RUN_ID, "latest successful Sector run changed")
    require(discovered_artifact_id == PARENT_ARTIFACT_ID, "latest successful Sector artifact changed")
    require(discovered_head_sha == PARENT_HEAD_SHA, "latest successful Sector commit changed")
    bundle = load_sector_radar_persistent_bundle(
        parent_dir,
        expected_repository=REPO,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )
    m = bundle.manifest
    require(m.source_run_id == PARENT_RUN_ID and m.source_run_attempt == 1, "parent run identity changed")
    require(m.source_commit_sha == PARENT_HEAD_SHA, "parent commit changed")
    require(m.market_session == date(2026, 9, 11), "parent session changed")
    require(m.market_state_hash == PARENT_STATE_HASH, "parent state hash changed")
    require(m.event_ledger_file_sha256 == PARENT_EVENT_SHA256, "parent event bytes changed")
    require(m.event_ledger_hash == PARENT_EVENT_LEDGER_HASH, "parent event ledger changed")
    require(m.last_result_hash == PARENT_LAST_RESULT_HASH, "parent last result changed")
    require(sha256((parent_dir / "market-state.json").read_bytes()) == PARENT_STATE_SHA256, "parent state bytes changed")
    return bundle


def reconstruct(source_audit: Path, *, reconstruction_commit: str, reconstructed_at: datetime) -> dict[str, bytes]:
    files = reconstruct_sector_prefix(
        source_audit,
        expected_audit_hash=SOURCE_AUDIT_HASH,
        origin_run_id=SOURCE_RUN_ID,
        origin_commit=SOURCE_HEAD_SHA,
        market_session=TARGET_SESSION,
        reconstruction_commit=reconstruction_commit,
        reconstructed_at=reconstructed_at,
    )
    report = json.loads(files["reconstruction.json"])
    require(report.get("status") == RECONSTRUCTION_STATUS, "reconstruction status changed")
    require(report.get("semantics") == RECONSTRUCTION_SEMANTICS, "reconstruction semantics changed")
    require(report.get("calculation_hash") == CANDIDATE_CALCULATION_HASH, "reconstruction calculation changed")
    calculation = report.get("calculation") or {}
    require(calculation.get("market_session") == TARGET_SESSION.isoformat(), "reconstruction session changed")
    require(calculation.get("reconstructed_market_state_hash") == CANDIDATE_STATE_HASH, "candidate state hash changed")
    require(calculation.get("coverage") == {"index_series": 321, "broad_entries": 2, "granular_entries": 12, "scope_complete": False}, "reconstruction coverage changed")
    stock = calculation.get("stock") or {}
    require(stock.get("status") == "NOT_RECONSTRUCTED" and stock.get("candidate_codes") is None, "historical Stock was invented")
    require(report.get("market_provider_requests") == 0 and report.get("event_ledger_modified") is False, "reconstruction authority changed")
    state_bytes = files["reconstructed-market-state.json"]
    event_bytes = files["unchanged-event-ledger.json"]
    require(sha256(state_bytes) == CANDIDATE_STATE_SHA256, "candidate state bytes changed")
    require(sha256(event_bytes) == CANDIDATE_EVENT_SHA256, "candidate event bytes changed")
    return files


def validate_candidate(parent, files: dict[str, bytes]):
    state_bytes = files["reconstructed-market-state.json"]
    event_bytes = files["unchanged-event-ledger.json"]
    state = parse_sector_radar_market_state(state_bytes.decode("utf-8"))
    ledger = parse_sector_radar_candidate_event_ledger(event_bytes.decode("utf-8"))
    require(serialize_sector_radar_market_state(state).encode("utf-8") == state_bytes, "candidate state is not canonical")
    require(serialize_sector_radar_candidate_event_ledger(ledger).encode("utf-8") == event_bytes, "candidate event ledger is not canonical")
    require(state.state_hash == CANDIDATE_STATE_HASH and state.sessions[-1] == TARGET_SESSION, "candidate state identity changed")
    require(len(state.sessions) == 127 and len(state.series) == 321, "candidate dimensions changed")
    require(ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "candidate event ledger hash changed")
    previous = parent.market_state
    require(state.catalog_hash == previous.catalog_hash, "candidate catalog changed")
    require(state.sessions[:-1] == previous.sessions[1:], "candidate did not append exactly one session")
    require(state.broad_identities == previous.broad_identities, "candidate broad identities changed")
    require(state.granular_identities == previous.granular_identities, "candidate granular identities changed")
    for old, new in zip(previous.series, state.series, strict=True):
        require((new.thscode, new.name) == (old.thscode, old.name), "candidate series identity changed")
        require(new.closes[:-1] == old.closes[1:], "candidate historical closes changed")
        require(new.turnovers[:-1] == old.turnovers[1:], "candidate historical turnovers changed")
    return state, ledger, state_bytes, event_bytes


def write_reconstruction(output: Path, files: dict[str, bytes]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    reconstruction_dir = output / "missed-session-reconstruction"
    reconstruction_dir.mkdir()
    for name, raw in files.items():
        with (reconstruction_dir / name).open("xb") as stream:
            stream.write(raw)


def adopt(args: argparse.Namespace) -> int:
    identity = invocation()
    parent = validate_parent(
        args.parent,
        discovered_run_id=args.discovered_run_id,
        discovered_artifact_id=args.discovered_artifact_id,
        discovered_head_sha=args.discovered_head_sha,
    )
    reconstructed_at = datetime.now(timezone.utc)
    files = reconstruct(args.source_audit, reconstruction_commit=identity["commit_sha"], reconstructed_at=reconstructed_at)
    # Explicit byte check against the actual latest successful production parent.
    require(files["unchanged-event-ledger.json"] == (args.parent / "candidate-events.json").read_bytes(), "candidate event ledger differs from production parent")
    state, ledger, state_bytes, event_bytes = validate_candidate(parent, files)
    write_reconstruction(args.output, files)

    completed_at = datetime.now(timezone.utc)
    bundle = write_sector_radar_persistent_bundle(
        args.state_dir,
        market_state=state,
        event_ledger=ledger,
        created_at=parent.manifest.created_at,
        updated_at=completed_at,
        source_repository=REPO,
        source_workflow=WORKFLOW,
        source_run_id=identity["run_id"],
        source_run_attempt=1,
        source_commit_sha=identity["commit_sha"],
        parent_hint_mapping_hash=PARENT_HINT_HASH,
        last_result_hash=PARENT_LAST_RESULT_HASH,
        last_operation_status=ADOPTION_STATUS,
    )
    require((args.state_dir / "market-state.json").read_bytes() == state_bytes, "adopted state bytes changed")
    require((args.state_dir / "candidate-events.json").read_bytes() == event_bytes, "adopted event bytes changed")
    require(bundle.market_state.state_hash == CANDIDATE_STATE_HASH, "adopted state hash changed")
    require(bundle.event_ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "adopted event ledger changed")
    receipt = {
        "schema_version": 1,
        "status": "MISSED_SESSION_ADOPTION_BUNDLE_READY_FOR_REMOTE_AUTHORITY",
        "semantics": "PIT_RECONSTRUCTED_SECTOR_STATE_ADOPTION_NO_RETROACTIVE_EVENT_NOT_NATURAL_DELIVERY",
        "operation": OPERATION,
        "requirement_issue": 375,
        "human_authorization_comment_id": 5675606163,
        "workflow_run_id": identity["run_id"],
        "workflow_run_attempt": 1,
        "workflow_commit_sha": identity["commit_sha"],
        "parent_run_id": PARENT_RUN_ID,
        "parent_artifact_id": PARENT_ARTIFACT_ID,
        "parent_state_hash": PARENT_STATE_HASH,
        "source_failed_run_id": SOURCE_RUN_ID,
        "source_failed_artifact_id": SOURCE_ARTIFACT_ID,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "source_audit_hash": SOURCE_AUDIT_HASH,
        "target_market_session": TARGET_SESSION,
        "reconstruction_calculation_hash": CANDIDATE_CALCULATION_HASH,
        "candidate_state_hash": CANDIDATE_STATE_HASH,
        "candidate_state_sha256": CANDIDATE_STATE_SHA256,
        "event_ledger_sha256": CANDIDATE_EVENT_SHA256,
        "event_ledger_hash": PARENT_EVENT_LEDGER_HASH,
        "output_manifest_hash": bundle.manifest.manifest_hash,
        "last_result_hash_preserved": PARENT_LAST_RESULT_HASH,
        "natural_acceptance": False,
        "historical_stock_reconstructed": False,
        "market_provider_network_calls": 0,
        "hithink_calls": 0,
        "events_created": 0,
        "production_state_writes": 1,
        "remote_state_artifact_authority": "NOT_ESTABLISHED_BY_LOCAL_RECEIPT",
        "cache_authority": "NONE_CACHE_IS_ACCELERATION_ONLY",
        **AUTHORITY,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    save_json(args.output / "missed-session-adoption.json", receipt)
    return 0


def verify(args: argparse.Namespace) -> int:
    identity = invocation()
    # Reconstruct again at a later real clock; calculation/state must be identical.
    files = reconstruct(args.source_audit, reconstruction_commit=identity["commit_sha"], reconstructed_at=datetime.now(timezone.utc))
    bundle = load_sector_radar_persistent_bundle(
        args.state_dir,
        expected_repository=REPO,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )
    require(bundle.manifest.source_run_id == identity["run_id"] and bundle.manifest.source_run_attempt == 1, "adopted run identity changed")
    require(bundle.manifest.source_commit_sha == identity["commit_sha"], "adopted commit changed")
    require(bundle.manifest.last_operation_status == ADOPTION_STATUS, "adopted operation changed")
    require(bundle.manifest.market_session == TARGET_SESSION, "adopted market session changed")
    require(bundle.manifest.last_result_hash == PARENT_LAST_RESULT_HASH, "adopted result hash changed")
    require(bundle.market_state.state_hash == CANDIDATE_STATE_HASH, "adopted state hash changed")
    require(bundle.event_ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "adopted event ledger hash changed")
    require((args.state_dir / "market-state.json").read_bytes() == files["reconstructed-market-state.json"], "adopted state differs from reconstruction")
    require((args.state_dir / "candidate-events.json").read_bytes() == files["unchanged-event-ledger.json"], "adopted event ledger differs from reconstruction")
    receipt = read_json(args.output / "missed-session-adoption.json")
    claimed = receipt.pop("receipt_hash", None)
    require(claimed == canonical_hash(receipt), "adoption receipt hash changed")
    require(receipt.get("output_manifest_hash") == bundle.manifest.manifest_hash, "manifest binding changed")
    verification = {
        "schema_version": 1,
        "status": "MISSED_SESSION_ADOPTION_OFFLINE_EXACT_MATCH",
        "workflow_run_id": identity["run_id"],
        "target_market_session": TARGET_SESSION,
        "reconstruction_calculation_hash": CANDIDATE_CALCULATION_HASH,
        "candidate_state_hash": CANDIDATE_STATE_HASH,
        "candidate_state_sha256": CANDIDATE_STATE_SHA256,
        "event_ledger_sha256": CANDIDATE_EVENT_SHA256,
        "event_ledger_hash": PARENT_EVENT_LEDGER_HASH,
        "output_manifest_hash": bundle.manifest.manifest_hash,
        "natural_acceptance": False,
        "historical_stock_reconstructed": False,
        "market_provider_network_calls": 0,
        "hithink_calls": 0,
        "events_created": 0,
        "production_state_writes": 0,
        **AUTHORITY,
    }
    verification["verification_hash"] = canonical_hash(verification)
    save_json(args.output / "missed-session-adoption-verification.json", verification)
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    a = sub.add_parser("adopt")
    a.add_argument("--parent", type=Path, required=True)
    a.add_argument("--source-audit", type=Path, required=True)
    a.add_argument("--state-dir", type=Path, required=True)
    a.add_argument("--output", type=Path, required=True)
    a.add_argument("--discovered-run-id", type=int, required=True)
    a.add_argument("--discovered-artifact-id", type=int, required=True)
    a.add_argument("--discovered-head-sha", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--source-audit", type=Path, required=True)
    v.add_argument("--state-dir", type=Path, required=True)
    v.add_argument("--output", type=Path, required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return adopt(args) if args.command == "adopt" else verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
