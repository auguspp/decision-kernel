#!/usr/bin/env python3
"""Adopt one exact offline Sector recovery checkpoint into the original producer lineage.

Case-bounded P0 recovery only. No provider/network access, no retrospective events,
no Research/Odds/Action authority. The remote state artifact/cache publication remains
the workflow's responsibility after this script has built and revalidated the bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json
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
OPERATION = "adopt-recovery-2026-09-10"
ADOPTION_STATUS = "RECOVERY_CHECKPOINT_ADOPTED_NO_RETROACTIVE_EVENT"

PARENT_RUN_ID = 34364727989
PARENT_ARTIFACT_ID = 10109790767
PARENT_HEAD_SHA = "381f4d1f826a6d98844d27d626129211218ca332"
PARENT_STATE_HASH = "fbfbf132dd11fd0d5be686db855b9f037aca7fc3055d2cb8dbac794494b95e05"
PARENT_ARTIFACT_DIGEST = "sha256:1f5f6ffa1795c8ccfdb457425d7a116e150fe5a504efac92b23294d891eb4324"
PARENT_HINT_HASH = "0b0b73e17da9019e4ce15af263394f0aafc5c49442c99babefbf43d15b6c6f38"
PARENT_EVENT_FILE_SHA256 = "4a6801bad15a1c93fadcd233f294d93f34fa1446fecc6d86a475ca9a2689340e"
PARENT_EVENT_LEDGER_HASH = "e7a059e28467213f83651a7c1b8dfb1d500a285e389552eb7322558130afdcf2"
PARENT_LAST_RESULT_HASH = "65a95dbd975d9acf555bea0e9bd1c1e6492a01b37f7363394fb76029ea00bbe4"

CHECKPOINT_RUN_ID = 34593517648
CHECKPOINT_ARTIFACT_ID = 10196584150
CHECKPOINT_ARTIFACT_DIGEST = "sha256:08ca629f718dccf8ca2d779651cef69529df0f3e3ed7a04d7f324cdec345fa02"
CHECKPOINT_RECEIPT_SHA256 = "7066a71571b286ac5e1e448c5a785ec8098b9e15d940e5b0c9de6abfc4e1f26a"
CHECKPOINT_VERIFY_SHA256 = "167110b70dc21ee8767a584261f911375f2eeb1256658014c60b4c991c46daeb"
CANDIDATE_STATE_HASH = "98c1f4425cf087a15a72c03af4a34ab7be43bdefea4d2467d20757b73d0ecd10"
CANDIDATE_STATE_SHA256 = "ff76904ee48aa8613095e91392b469989801080f5befec672225203985e391bf"
CANDIDATE_EVENT_SHA256 = PARENT_EVENT_FILE_SHA256
CANDIDATE_SOURCE = "RECOVERY_CANDIDATE_RETAINED_HITHINK_THS_MIXED_PUBLIC_NOT_RESTORE_AUTHORITY"
SOURCE_COVERAGE_RUN_ID = 34593139374
SOURCE_COVERAGE_ARTIFACT_ID = 10196462869
SOURCE_COVERAGE_DIGEST = "9602d99827fc82187346786ea568fe1ff6da6a0df511e2610dca8e5df5bb6797"
SOURCE_RECEIPT_SHA256 = "b8394cb8456b70465d9294cbbff31df7a7028230c64155c41957431abd7fe739"
SOURCE_RAW_MANIFEST_SHA256 = "87dad620ec3fd13d3be667837ebb426208b99d009062bab924cab7827aca6b16"

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
    require(env.get("GITHUB_REF") == "refs/heads/main", "recovery adoption requires main")
    require(env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "recovery adoption must be manual")
    require(env.get("GITHUB_RUN_ATTEMPT") == "1", "recovery adoption must use attempt 1")
    require(env.get("RECOVERY_OPERATION") == OPERATION, "recovery adoption operation changed")
    require(not env.get("HITHINK_FINANCE_API_KEY"), "recovery adoption must not receive market credential")
    run_id = env.get("GITHUB_RUN_ID", "")
    commit_sha = env.get("GITHUB_SHA", "")
    require(run_id.isdigit() and int(run_id) > 0, "invalid workflow run id")
    require(re.fullmatch(r"[0-9a-f]{40}", commit_sha) is not None, "invalid workflow commit")
    return {"run_id": int(run_id), "run_attempt": 1, "commit_sha": commit_sha}


def validate_parent(
    parent_dir: Path,
    *,
    discovered_run_id: int,
    discovered_artifact_id: int,
    discovered_head_sha: str,
):
    require(discovered_run_id == PARENT_RUN_ID, "latest successful Sector run changed")
    require(discovered_artifact_id == PARENT_ARTIFACT_ID, "latest successful Sector artifact changed")
    require(discovered_head_sha == PARENT_HEAD_SHA, "latest successful Sector commit changed")
    bundle = load_sector_radar_persistent_bundle(
        parent_dir,
        expected_repository=REPO,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )
    manifest = bundle.manifest
    require(manifest.source_run_id == PARENT_RUN_ID, "parent bundle run changed")
    require(manifest.source_run_attempt == 1, "parent bundle attempt changed")
    require(manifest.source_commit_sha == PARENT_HEAD_SHA, "parent bundle commit changed")
    require(manifest.market_state_hash == PARENT_STATE_HASH, "parent state hash changed")
    require(manifest.event_ledger_file_sha256 == PARENT_EVENT_FILE_SHA256, "parent event file changed")
    require(manifest.event_ledger_hash == PARENT_EVENT_LEDGER_HASH, "parent event ledger changed")
    require(manifest.last_result_hash == PARENT_LAST_RESULT_HASH, "parent result hash changed")
    require(manifest.market_session == date(2026, 9, 9), "parent market session changed")
    return bundle


def validate_checkpoint(checkpoint_root: Path):
    state_path = checkpoint_root / "checkpoint" / "candidate-state.json"
    event_path = checkpoint_root / "checkpoint" / "candidate-events.json"
    receipt_path = checkpoint_root / "checkpoint" / "checkpoint-receipt.json"
    verify_path = checkpoint_root / "checkpoint-verify" / "verification.json"
    for path in (state_path, event_path, receipt_path, verify_path):
        require(path.is_file() and not path.is_symlink(), f"checkpoint file missing: {path}")
    state_bytes = state_path.read_bytes()
    event_bytes = event_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    verify_bytes = verify_path.read_bytes()
    require(sha256(state_bytes) == CANDIDATE_STATE_SHA256, "candidate-state bytes changed")
    require(sha256(event_bytes) == CANDIDATE_EVENT_SHA256, "candidate event bytes changed")
    require(sha256(receipt_bytes) == CHECKPOINT_RECEIPT_SHA256, "checkpoint receipt bytes changed")
    require(sha256(verify_bytes) == CHECKPOINT_VERIFY_SHA256, "checkpoint verification bytes changed")

    receipt = read_json(receipt_path)
    verify = read_json(verify_path)
    require(receipt.get("status") == "RECOVERY_CHECKPOINT_CANDIDATE_REVIEW_REQUIRED", "checkpoint status changed")
    require(receipt.get("semantics") == "OFFLINE_SOURCE_COMPLETE_RECOVERY_CHECKPOINT_NOT_PRODUCTION", "checkpoint semantics changed")
    require(receipt.get("candidate_state_hash") == CANDIDATE_STATE_HASH, "checkpoint state hash changed")
    require(receipt.get("candidate_state_sha256") == CANDIDATE_STATE_SHA256, "checkpoint state sha changed")
    require(receipt.get("candidate_event_ledger_sha256") == CANDIDATE_EVENT_SHA256, "checkpoint event sha changed")
    require(receipt.get("candidate_source") == CANDIDATE_SOURCE, "checkpoint candidate source changed")
    require(receipt.get("target_session") == "2026-09-10", "checkpoint target changed")
    require(receipt.get("session_count") == 127 and receipt.get("identity_count") == 321, "checkpoint dimensions changed")
    require(receipt.get("network_calls") == receipt.get("hithink_new_requests") == 0, "checkpoint was not offline")
    require(receipt.get("production_state_writes") == receipt.get("events_created") == 0, "checkpoint mutated production")
    require(all(receipt.get(key) == "NONE" for key in ("restore_authority", "research_authority", "human_attention_authority", "investment_authority")), "checkpoint authority changed")
    coverage = receipt.get("source_coverage") or {}
    require(
        coverage.get("run_id") == SOURCE_COVERAGE_RUN_ID
        and coverage.get("artifact_id") == SOURCE_COVERAGE_ARTIFACT_ID
        and coverage.get("digest") == SOURCE_COVERAGE_DIGEST
        and coverage.get("receipt_sha256") == SOURCE_RECEIPT_SHA256
        and coverage.get("raw_manifest_sha256") == SOURCE_RAW_MANIFEST_SHA256
        and coverage.get("raw_file_count") == 211,
        "source-complete binding changed",
    )

    require(verify.get("status") == "OFFLINE_REBUILD_EXACT_MATCH", "checkpoint rebuild proof changed")
    require(verify.get("candidate_state_hash") == CANDIDATE_STATE_HASH, "rebuild state hash changed")
    require(verify.get("candidate_state_sha256") == CANDIDATE_STATE_SHA256, "rebuild state sha changed")
    require(verify.get("candidate_event_ledger_sha256") == CANDIDATE_EVENT_SHA256, "rebuild event sha changed")
    require(verify.get("network_calls") == verify.get("hithink_new_requests") == 0, "rebuild proof was not offline")
    require(verify.get("production_state_writes") == verify.get("events_created") == 0, "rebuild proof mutated production")

    state = parse_sector_radar_market_state(state_bytes.decode("utf-8"))
    ledger = parse_sector_radar_candidate_event_ledger(event_bytes.decode("utf-8"))
    require(serialize_sector_radar_market_state(state).encode("utf-8") == state_bytes, "candidate state is not byte-canonical")
    require(serialize_sector_radar_candidate_event_ledger(ledger).encode("utf-8") == event_bytes, "candidate ledger is not byte-canonical")
    require(state.state_hash == CANDIDATE_STATE_HASH, "parsed candidate state hash changed")
    require(state.sessions[-1] == date(2026, 9, 10) and len(state.sessions) == 127, "candidate session boundary changed")
    require(len(state.series) == 321, "candidate identity count changed")
    require(state.source == CANDIDATE_SOURCE, "candidate source changed")
    require(state.catalog_hash == "367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360", "candidate catalog changed")
    last_lineage = state.source_lineage[-1]
    require(
        last_lineage.role == "RECOVERY_PARENT_STATE"
        and last_lineage.workflow_run_id == PARENT_RUN_ID
        and last_lineage.artifact_id == PARENT_ARTIFACT_ID
        and last_lineage.artifact_digest == PARENT_ARTIFACT_DIGEST
        and last_lineage.result_hash == PARENT_LAST_RESULT_HASH,
        "candidate parent lineage changed",
    )
    require(ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "candidate ledger hash changed")
    return state, ledger, state_bytes, event_bytes


def adopt(args: argparse.Namespace) -> int:
    identity = invocation()
    parent = validate_parent(
        args.parent,
        discovered_run_id=args.discovered_run_id,
        discovered_artifact_id=args.discovered_artifact_id,
        discovered_head_sha=args.discovered_head_sha,
    )
    state, ledger, state_bytes, event_bytes = validate_checkpoint(args.checkpoint)
    require(event_bytes == (args.parent / "candidate-events.json").read_bytes(), "checkpoint event ledger differs from production parent")
    require(state.catalog_hash == parent.market_state.catalog_hash, "checkpoint catalog differs from parent")
    require(state.sessions[:-1] == parent.market_state.sessions, "checkpoint does not extend parent by exactly one session")
    require(state.series[0].thscode == parent.market_state.series[0].thscode, "checkpoint benchmark identity changed")

    completed_at = datetime.now(timezone.utc)
    args.output.mkdir(parents=True, exist_ok=False)
    output = write_sector_radar_persistent_bundle(
        args.state_dir,
        market_state=state,
        event_ledger=ledger,
        created_at=parent.manifest.created_at,
        updated_at=completed_at,
        source_repository=REPO,
        source_workflow=WORKFLOW,
        source_run_id=identity["run_id"],
        source_run_attempt=identity["run_attempt"],
        source_commit_sha=identity["commit_sha"],
        parent_hint_mapping_hash=PARENT_HINT_HASH,
        last_result_hash=PARENT_LAST_RESULT_HASH,
        last_operation_status=ADOPTION_STATUS,
    )
    require((args.state_dir / "market-state.json").read_bytes() == state_bytes, "adopted state bytes changed")
    require((args.state_dir / "candidate-events.json").read_bytes() == event_bytes, "adopted event bytes changed")
    require(output.market_state.state_hash == CANDIDATE_STATE_HASH, "adopted state hash changed")
    require(output.event_ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "adopted event ledger hash changed")

    receipt = {
        "schema_version": 1,
        "status": "RECOVERY_ADOPTION_BUNDLE_READY_FOR_REMOTE_AUTHORITY",
        "semantics": "EXACT_CHECKPOINT_ADOPTION_IN_ORIGINAL_SECTOR_WORKFLOW_NO_RETROACTIVE_EVENT",
        "operation": OPERATION,
        "human_authorization_comment_id": 5628923881,
        "workflow_run_id": identity["run_id"],
        "workflow_run_attempt": 1,
        "workflow_commit_sha": identity["commit_sha"],
        "parent_run_id": PARENT_RUN_ID,
        "parent_artifact_id": PARENT_ARTIFACT_ID,
        "parent_state_hash": PARENT_STATE_HASH,
        "checkpoint_run_id": CHECKPOINT_RUN_ID,
        "checkpoint_artifact_id": CHECKPOINT_ARTIFACT_ID,
        "checkpoint_artifact_digest": CHECKPOINT_ARTIFACT_DIGEST,
        "candidate_state_hash": CANDIDATE_STATE_HASH,
        "candidate_state_sha256": CANDIDATE_STATE_SHA256,
        "event_ledger_sha256": CANDIDATE_EVENT_SHA256,
        "event_ledger_hash": PARENT_EVENT_LEDGER_HASH,
        "output_manifest_hash": output.manifest.manifest_hash,
        "output_market_session": output.manifest.market_session.isoformat(),
        "last_result_hash_preserved": PARENT_LAST_RESULT_HASH,
        "market_provider_network_calls": 0,
        "hithink_calls": 0,
        "events_created": 0,
        "production_state_writes": 1,
        "remote_state_artifact_authority": "NOT_ESTABLISHED_BY_LOCAL_RECEIPT",
        "cache_authority": "NONE_CACHE_IS_ACCELERATION_ONLY",
        **AUTHORITY,
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    save_json(args.output / "recovery-adoption.json", receipt)
    return 0


def verify(args: argparse.Namespace) -> int:
    identity = invocation()
    _, _, state_bytes, event_bytes = validate_checkpoint(args.checkpoint)
    bundle = load_sector_radar_persistent_bundle(
        args.state_dir,
        expected_repository=REPO,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )
    require(bundle.manifest.source_run_id == identity["run_id"], "adopted bundle run id changed")
    require(bundle.manifest.source_run_attempt == 1, "adopted bundle attempt changed")
    require(bundle.manifest.source_commit_sha == identity["commit_sha"], "adopted bundle commit changed")
    require(bundle.manifest.last_operation_status == ADOPTION_STATUS, "adopted operation status changed")
    require(bundle.manifest.last_result_hash == PARENT_LAST_RESULT_HASH, "adopted result hash changed")
    require(bundle.market_state.state_hash == CANDIDATE_STATE_HASH, "adopted state hash changed")
    require(bundle.event_ledger.ledger_hash == PARENT_EVENT_LEDGER_HASH, "adopted event hash changed")
    require((args.state_dir / "market-state.json").read_bytes() == state_bytes, "adopted state bytes differ from checkpoint")
    require((args.state_dir / "candidate-events.json").read_bytes() == event_bytes, "adopted event bytes differ from checkpoint")

    receipt = read_json(args.output / "recovery-adoption.json")
    claimed = receipt.pop("receipt_hash", None)
    require(claimed == canonical_hash(receipt), "adoption receipt hash changed")
    require(receipt.get("status") == "RECOVERY_ADOPTION_BUNDLE_READY_FOR_REMOTE_AUTHORITY", "adoption receipt status changed")
    require(receipt.get("output_manifest_hash") == bundle.manifest.manifest_hash, "adoption manifest binding changed")
    verification = {
        "schema_version": 1,
        "status": "RECOVERY_ADOPTION_OFFLINE_EXACT_MATCH",
        "workflow_run_id": identity["run_id"],
        "candidate_state_hash": CANDIDATE_STATE_HASH,
        "candidate_state_sha256": CANDIDATE_STATE_SHA256,
        "event_ledger_sha256": CANDIDATE_EVENT_SHA256,
        "event_ledger_hash": PARENT_EVENT_LEDGER_HASH,
        "output_manifest_hash": bundle.manifest.manifest_hash,
        "market_provider_network_calls": 0,
        "hithink_calls": 0,
        "events_created": 0,
        "production_state_writes": 0,
        **AUTHORITY,
    }
    verification["verification_hash"] = canonical_hash(verification)
    save_json(args.output / "recovery-adoption-verification.json", verification)
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    adopt_p = sub.add_parser("adopt")
    adopt_p.add_argument("--parent", type=Path, required=True)
    adopt_p.add_argument("--checkpoint", type=Path, required=True)
    adopt_p.add_argument("--state-dir", type=Path, required=True)
    adopt_p.add_argument("--output", type=Path, required=True)
    adopt_p.add_argument("--discovered-run-id", type=int, required=True)
    adopt_p.add_argument("--discovered-artifact-id", type=int, required=True)
    adopt_p.add_argument("--discovered-head-sha", required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--checkpoint", type=Path, required=True)
    verify_p.add_argument("--state-dir", type=Path, required=True)
    verify_p.add_argument("--output", type=Path, required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "adopt":
        return adopt(args)
    return verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
