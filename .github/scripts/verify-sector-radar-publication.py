"""Bind the existing offline replay to the files this workflow will upload.

This is a read-only publication precheck, not a producer, recovery tool, or new
replay engine. Remote artifact/cache success must still be checked separately.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.sector_radar_audit import (
    AUTHORITY,
    LIVE_PROVENANCE,
    MAX_FILE_BYTES,
    replay_sector_radar_input_audit,
    validate_sector_radar_input_audit,
)

STATE_FILES = {"market-state.json", "candidate-events.json", "manifest.json"}
RECEIPT_NAME = "publication-verification.json"


def read_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("publication input must be a bounded regular file")
    return path.read_bytes()


def verify_publication(run_directory: Path, state_directory: Path, expected_context: dict) -> dict:
    for directory in (run_directory, state_directory):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("publication input directory is missing or symbolic")
        if any(path.is_symlink() for path in directory.rglob("*")):
            raise ValueError("publication input tree contains a symbolic link")
    if (run_directory / RECEIPT_NAME).exists():
        raise ValueError("publication verification receipt already exists; do not overwrite")
    audit_root = run_directory / "input-audit"
    manifest = validate_sector_radar_input_audit(audit_root)
    if manifest["provenance"] != LIVE_PROVENANCE or manifest["status"] != "SUCCEEDED":
        raise ValueError("only a successful live calculation may pass the publication precheck")
    context = json.loads(read_file(audit_root / "inputs/context.json"))
    if set(expected_context) != {"repository", "workflow_path", "run_id", "run_attempt", "commit_sha"}:
        raise ValueError("complete expected workflow identity is required")
    if any(context.get(key) != value for key, value in expected_context.items()):
        raise ValueError("audit identity differs from the current workflow run")

    replay = replay_sector_radar_input_audit(audit_root)
    if (replay["status"] != "MATCHED_SUCCEEDED" or replay["provenance"] != LIVE_PROVENANCE
            or replay["audit_hash"] != manifest["audit_hash"]
            or replay["network_calls"] != 0 or replay["production_state_writes"] != 0):
        raise ValueError("offline replay did not prove a matching successful calculation")

    if {path.name for path in state_directory.iterdir()} != STATE_FILES:
        raise ValueError("upload state inventory differs from the complete bundle")
    output_names = {name.removeprefix("expected/output/") for name in manifest["files"]
                    if name.startswith("expected/output/")}
    if not {"operations.json", "operations.md"} <= output_names:
        raise ValueError("successful audit lacks operations records")
    # The context renderer runs after this precheck. At this point, every ordinary
    # output must be part of the sealed/replayed output inventory.
    if {path.name for path in run_directory.iterdir()} != output_names | {"input-audit"}:
        raise ValueError("upload run inventory differs from the sealed calculation")
    files = {}
    for category, directory, names in (
        ("state", state_directory, STATE_FILES), ("output", run_directory, output_names),
    ):
        for name in sorted(names):
            actual = read_file(directory / name)
            expected = read_file(audit_root / "expected" / category / name)
            if actual != expected:
                raise ValueError(f"upload file differs from the replayed calculation: {category}/{name}")
            files[f"{category}/{name}"] = {"bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest()}
    operations = json.loads(read_file(run_directory / "operations.json"))
    result = {
        "schema_version": 1, "status": "REPLAY_AND_UPLOAD_FILES_MATCHED",
        "semantics": "LOCAL_PREPUBLICATION_CHECK_NOT_REMOTE_ARTIFACT_OR_CACHE_SUCCESS",
        "workflow_identity": expected_context, "audit_hash": manifest["audit_hash"],
        "market_session": operations["latest_completed_session"],
        "state_update_status": operations["state_update_status"],
        "market_state_hash": operations["output_market_state_hash"],
        "event_ledger_hash": operations["output_event_ledger_hash"],
        "verified_files": files, "offline_replay": replay, **AUTHORITY,
    }
    result["verification_hash"] = canonical_hash(result)
    return result


def main() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_EVENT_NAME") not in {"workflow_dispatch", "schedule"}:
        raise ValueError("publication precheck requires a fresh main workflow_dispatch or schedule")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("publication precheck requires attempt 1")
    if os.environ.get("HITHINK_FINANCE_API_KEY"):
        raise ValueError("publication precheck must not receive the market credential")
    identity = {
        "repository": os.environ["GITHUB_REPOSITORY"],
        "workflow_path": ".github/workflows/sector-radar-shadow.yml",
        "run_id": int(os.environ["GITHUB_RUN_ID"]), "run_attempt": 1,
        "commit_sha": os.environ["GITHUB_SHA"],
    }
    root = Path("sector-radar-run")
    result = verify_publication(root, Path("decision-state/sector-radar"), identity)
    with (root / RECEIPT_NAME).open("x", encoding="utf-8") as output:
        output.write(canonical_json(result) + "\n")
    print("Offline replay and upload files match; remote publication has not yet been proved.")


if __name__ == "__main__":
    main()
