#!/usr/bin/env python3
"""Build and independently re-build the 2026-09-10 Sector recovery checkpoint offline.

This consumes only frozen GitHub artifacts whose source identities already passed the
bounded overlap gates. It performs zero market/provider requests and does not install
production/current-state/cache/events or grant Research/Odds/Action authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

B = runpy.run_path(".github/scripts/capture-sector-ths-v4-final-continuation.py")
compose = B["compose"]
load_json = B["load_json"]
save_json = B["save_json"]
require = B["require"]
AUTHORITY = B["AUTHORITY"]
_atomic_bytes = B["_atomic_bytes"]

SOURCE_RUN = 34593139374
SOURCE_ARTIFACT = 10196462869
SOURCE_DIGEST = "9602d99827fc82187346786ea568fe1ff6da6a0df511e2610dca8e5df5bb6797"
SOURCE_STATUS = "SOURCE_COVERAGE_EXACT_COMPLETE"
SOURCE_SEMANTICS = "FROZEN_SECTOR_RECOVERY_THS_V4_SOURCE_COMPLETION_ONLY"
EXPECTED_TOTAL = 321
EXPECTED_PUBLIC = 211
EXPECTED_HITHINK = 110
EXPECTED_V4 = 120
EXPECTED_V6 = 76
EXPECTED_V2 = 15
TARGET = "2026-09-10"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_manifest(complete: Path) -> tuple[dict[str, str], str]:
    rows: dict[str, str] = {}
    for dirname in ("raw-v4", "raw-v6", "raw-v2"):
        root = complete / dirname
        require(root.is_dir() and not root.is_symlink(), f"source raw dir missing {dirname}")
        for path in sorted(root.glob("*.js")):
            require(path.is_file() and not path.is_symlink(), f"invalid raw path {path}")
            rel = f"{dirname}/{path.name}"
            require(rel not in rows, f"duplicate raw path {rel}")
            rows[rel] = sha256_bytes(path.read_bytes())
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return rows, sha256_bytes(canonical)


def validate_complete(complete: Path) -> dict[str, Any]:
    receipt_path = complete / "receipt.json"
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    require(receipt.get("status") == SOURCE_STATUS, "source completion status changed")
    require(receipt.get("semantics") == SOURCE_SEMANTICS, "source completion semantics changed")
    require(receipt.get("final_exact_coverage") == EXPECTED_TOTAL, "source exact coverage changed")
    require(receipt.get("final_public_exact_coverage") == EXPECTED_PUBLIC, "source public coverage changed")
    require(receipt.get("final_v4_count") == EXPECTED_V4, "source v4 count changed")
    require(receipt.get("final_v6_count") == EXPECTED_V6, "source v6 count changed")
    require(receipt.get("final_v2_count") == EXPECTED_V2, "source v2 count changed")
    require(receipt.get("network_calls") == 22, "source completion request count changed")
    require(receipt.get("retry_count") == 0, "source completion retry count changed")
    require(receipt.get("new_identity_count") == 22, "source completion admitted count changed")
    require(receipt.get("hithink_new_requests") == 0, "source completion made HiThink request")
    require(receipt.get("production_state_writes") == 0, "source completion wrote production state")
    require(receipt.get("events_created") == 0, "source completion created event")
    require(receipt.get("restore_authority") == "NONE", "source completion restore authority changed")
    require(receipt.get("research_authority") == "NONE", "source completion research authority changed")
    require(receipt.get("investment_authority") == "NONE", "source completion investment authority changed")
    require(receipt.get("error") is None, "source completion has error")
    attempts = receipt.get("http_attempts")
    require(isinstance(attempts, list) and len(attempts) == 22, "source completion attempts changed")
    require(all(isinstance(row, dict) and row.get("http_status") == 200 for row in attempts), "source completion HTTP not all 200")
    checks = receipt.get("overlap_checks")
    require(isinstance(checks, list) and len(checks) == 66, "source completion overlap count changed")
    require(all(isinstance(row, dict) and row.get("exact") is True for row in checks), "source completion overlap not exact")

    rows, manifest_sha = raw_manifest(complete)
    counts = {
        "v4": sum(1 for key in rows if key.startswith("raw-v4/")),
        "v6": sum(1 for key in rows if key.startswith("raw-v6/")),
        "v2": sum(1 for key in rows if key.startswith("raw-v2/")),
    }
    require(counts == {"v4": EXPECTED_V4, "v6": EXPECTED_V6, "v2": EXPECTED_V2}, "source raw counts changed")
    require(sum(counts.values()) == EXPECTED_PUBLIC, "source public raw total changed")
    return {
        "receipt_sha256": sha256_bytes(receipt_bytes),
        "raw_manifest_sha256": manifest_sha,
        "raw_file_count": len(rows),
        "raw_counts": counts,
    }


def candidate_checks(candidate_bytes: bytes) -> dict[str, Any]:
    payload = json.loads(candidate_bytes)
    sessions = payload.get("sessions")
    series = payload.get("series")
    require(isinstance(sessions, list) and sessions and sessions[-1] == TARGET, "candidate target session changed")
    require(isinstance(series, list) and len(series) == EXPECTED_TOTAL, "candidate identity count changed")
    identities = [str(row.get("thscode")) for row in series if isinstance(row, dict)]
    require(len(identities) == EXPECTED_TOTAL and len(set(identities)) == EXPECTED_TOTAL, "candidate identities not unique")
    return {
        "target_session": sessions[-1],
        "session_count": len(sessions),
        "identity_count": len(series),
        "state_hash": payload.get("state_hash"),
        "source": payload.get("source"),
    }


def build(source: Path, complete: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    try:
        source_binding = validate_complete(complete)
        candidate_bytes, event_bytes, rebuilt = compose(source, complete, False)
        require(rebuilt.get("status") == "RECOVERY_CANDIDATE_REVIEW_REQUIRED", "candidate compose status changed")
        require(rebuilt.get("hithink_new_requests") == 0, "offline compose made HiThink request")
        require(rebuilt.get("production_state_writes") == 0, "offline compose wrote production state")
        require(rebuilt.get("events_created") == 0, "offline compose created events")
        require(rebuilt.get("restore_authority") == "NONE", "offline compose restore authority changed")
        require(rebuilt.get("research_authority") == "NONE", "offline compose research authority changed")
        require(rebuilt.get("investment_authority") == "NONE", "offline compose investment authority changed")
        checks = candidate_checks(candidate_bytes)
        require(checks["state_hash"] == rebuilt.get("candidate_state_hash"), "candidate state hash binding changed")
        candidate_sha = sha256_bytes(candidate_bytes)
        event_sha = sha256_bytes(event_bytes)
        require(candidate_sha == rebuilt.get("candidate_state_sha256"), "candidate byte hash binding changed")
        require(event_sha == rebuilt.get("event_ledger_sha256"), "event ledger hash binding changed")

        _atomic_bytes(out / "candidate-state.json", candidate_bytes)
        _atomic_bytes(out / "candidate-events.json", event_bytes)
        receipt = {
            "schema_version": 1,
            "status": "RECOVERY_CHECKPOINT_CANDIDATE_REVIEW_REQUIRED",
            "semantics": "OFFLINE_SOURCE_COMPLETE_RECOVERY_CHECKPOINT_NOT_PRODUCTION",
            "source_coverage": {
                "run_id": SOURCE_RUN,
                "artifact_id": SOURCE_ARTIFACT,
                "digest": SOURCE_DIGEST,
                **source_binding,
            },
            "candidate_state_hash": rebuilt["candidate_state_hash"],
            "candidate_state_sha256": candidate_sha,
            "candidate_event_ledger_sha256": event_sha,
            "target_session": checks["target_session"],
            "session_count": checks["session_count"],
            "identity_count": checks["identity_count"],
            "candidate_source": checks["source"],
            "network_calls": 0,
            "hithink_new_requests": 0,
            **AUTHORITY,
            "error": None,
        }
        save_json(out / "checkpoint-receipt.json", receipt)
        print(receipt["status"], receipt["candidate_state_hash"], receipt["candidate_state_sha256"])
        return 0
    except Exception as exc:
        save_json(
            out / "checkpoint-receipt.json",
            {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "semantics": "OFFLINE_SOURCE_COMPLETE_RECOVERY_CHECKPOINT_NOT_PRODUCTION",
                "network_calls": 0,
                "hithink_new_requests": 0,
                **AUTHORITY,
                "error": {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]},
            },
        )
        print(f"FAILED_CLOSED: {type(exc).__name__}: {exc}")
        return 2


def verify(source: Path, complete: Path, checkpoint: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=False)
    try:
        source_binding = validate_complete(complete)
        saved = load_json(checkpoint / "checkpoint-receipt.json")
        require(saved.get("status") == "RECOVERY_CHECKPOINT_CANDIDATE_REVIEW_REQUIRED", "saved checkpoint incomplete")
        require(saved.get("source_coverage", {}).get("receipt_sha256") == source_binding["receipt_sha256"], "source receipt binding changed")
        require(saved.get("source_coverage", {}).get("raw_manifest_sha256") == source_binding["raw_manifest_sha256"], "source raw manifest binding changed")
        candidate_bytes, event_bytes, rebuilt = compose(source, complete, False)
        require(candidate_bytes == (checkpoint / "candidate-state.json").read_bytes(), "candidate bytes differ")
        require(event_bytes == (checkpoint / "candidate-events.json").read_bytes(), "candidate event bytes differ")
        require(rebuilt.get("candidate_state_hash") == saved.get("candidate_state_hash"), "candidate state hash differs")
        require(sha256_bytes(candidate_bytes) == saved.get("candidate_state_sha256"), "candidate sha differs")
        require(sha256_bytes(event_bytes) == saved.get("candidate_event_ledger_sha256"), "event ledger sha differs")
        result = {
            "schema_version": 1,
            "status": "OFFLINE_REBUILD_EXACT_MATCH",
            "semantics": "RECOVERY_CHECKPOINT_REPRODUCIBILITY_ONLY_NOT_PRODUCTION",
            "source_coverage_run_id": SOURCE_RUN,
            "source_coverage_artifact_id": SOURCE_ARTIFACT,
            "source_coverage_digest": SOURCE_DIGEST,
            "source_receipt_sha256": source_binding["receipt_sha256"],
            "source_raw_manifest_sha256": source_binding["raw_manifest_sha256"],
            "candidate_state_hash": rebuilt["candidate_state_hash"],
            "candidate_state_sha256": sha256_bytes(candidate_bytes),
            "candidate_event_ledger_sha256": sha256_bytes(event_bytes),
            "network_calls": 0,
            "hithink_new_requests": 0,
            **AUTHORITY,
            "error": None,
        }
        save_json(out / "verification.json", result)
        print(result["status"], result["candidate_state_hash"])
        return 0
    except Exception as exc:
        save_json(
            out / "verification.json",
            {
                "schema_version": 1,
                "status": "FAILED_CLOSED",
                "semantics": "RECOVERY_CHECKPOINT_REPRODUCIBILITY_ONLY_NOT_PRODUCTION",
                "network_calls": 0,
                "hithink_new_requests": 0,
                **AUTHORITY,
                "error": {"type": type(exc).__name__, "message": " ".join(str(exc).split())[:1000]},
            },
        )
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--source", type=Path, required=True)
    b.add_argument("--complete", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--source", type=Path, required=True)
    v.add_argument("--complete", type=Path, required=True)
    v.add_argument("--checkpoint", type=Path, required=True)
    v.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "build":
        return build(args.source, args.complete, args.output)
    return verify(args.source, args.complete, args.checkpoint, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
