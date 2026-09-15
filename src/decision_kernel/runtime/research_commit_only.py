"""Retain an existing generic Research package, then commit without Market/Odds.

This is an offline Harness adapter, not another Research validator or Git store.
The optional original researcher receipt is retained verbatim, never certified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from typing import TextIO

from ..identity import canonical_hash, canonical_json
from ..research_commit import (
    ResearchCommitPackage, ResearchCommitResult, commit_research_package,
)

FORMAT = "research-commit-only-v0"
MAX_BYTES = 512 * 1024
RECEIPT_NAME = "research-execution-receipt.bin"


def _json(raw: bytes) -> dict:
    # The existing external-research parser imports the live Funnel/workflow.
    # Reuse stdlib hooks here instead of importing that unrelated composition.
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite JSON number")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                       parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def _safe_path(path: Path) -> None:
    if any(part.is_symlink() for part in (path, *path.absolute().parents)):
        raise ValueError("symlink paths are not supported")


def _read(path: Path) -> bytes:
    _safe_path(path)
    if not path.is_file():
        raise ValueError("a regular retained file is required")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("retained file exceeds the 512 KiB adapter bound")
    return data


def _write(path: Path, data: bytes) -> None:
    if len(data) > MAX_BYTES:
        raise ValueError("retained file exceeds the 512 KiB adapter bound")
    _safe_path(path)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if _read(path) != data:
        raise ValueError("retained bytes failed readback")


def _raw(value) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _description(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": sha256(data).hexdigest()}


def _commit_receipt(result: ResearchCommitResult, result_raw: bytes,
                    retention_raw: bytes) -> dict:
    return {
        "format": FORMAT,
        "semantics": "COMMIT_OPERATION_NOT_RESEARCH_EXECUTION_OR_HUMAN_ACCEPTANCE",
        "research_status": "COMMITTED",
        "package_hash": result.package_hash,
        "information_bundle_hash": result.information_bundle_hash,
        "research_snapshot_id": str(result.research_snapshot.id),
        "result": _description(result_raw),
        "retention": _description(retention_raw),
        "market_status": "NOT_REQUESTED",
        "odds_status": "NOT_COMPUTED",
        "human_acceptance": "NOT_ESTABLISHED_BY_THIS_OPERATION",
        "investment_authority": "NONE",
        "publication_status": "LOCAL_ONLY_NOT_GITHUB_PUBLICATION",
    }


def read_retained_commit(output: Path) -> ResearchCommitResult:
    """Read exact saved files and reapply the original deterministic commit checks.

    Byte binding is not source truth, a signature, a historical execution receipt,
    or permission to promote an old/challenged package as current Research.
    """
    _safe_path(output)
    retention_raw = _read(output / "retention.json")
    retention = _json(retention_raw)
    if set(retention) != {"format", "retained_at", "input", "research_execution_receipt"}:
        raise ValueError("retention fields differ")
    at = datetime.fromisoformat(retention["retained_at"])
    if retention["format"] != FORMAT or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("retention format or clock differs")
    input_raw = _read(output / "input.json")
    if retention["input"] != _description(input_raw):
        raise ValueError("retained input binding differs")
    expected_names = {"input.json", "retention.json", "research-commit.json", "commit.json"}
    original_receipt = retention["research_execution_receipt"]
    if original_receipt is not None:
        expected_names.add(RECEIPT_NAME)
        if original_receipt != {**_description(_read(output / RECEIPT_NAME)),
                                "status": "RETAINED_UNVALIDATED"}:
            raise ValueError("original researcher receipt binding differs")
    if {p.name for p in output.iterdir()} != expected_names:
        raise ValueError("retained commit inventory differs or is incomplete")
    package = ResearchCommitPackage.model_validate(_json(input_raw))
    if package.proposed_committed_at > at:
        raise ValueError("proposed commit follows the recorded retention operation")
    expected = commit_research_package(package)
    result_raw = _read(output / "research-commit.json")
    result = ResearchCommitResult.model_validate(_json(result_raw))
    if canonical_hash(result) != canonical_hash(expected):
        raise ValueError("saved result differs from original commit validation")
    if _json(_read(output / "commit.json")) != _commit_receipt(result, result_raw, retention_raw):
        raise ValueError("commit operation receipt differs")
    return result


def commit_research_file(package_path: Path, *, output: Path,
                         execution_receipt_path: Path | None = None) -> ResearchCommitResult:
    """Retain supplied inputs before validation; never overwrite or erase failure.

    The caller owns eligibility/review and Git publication. No receipt is invented
    when the prior researcher supplied none. Original proposed commit time is
    preserved; retention time is a separate actual filesystem-operation clock.
    """
    _safe_path(output)
    input_raw = _read(package_path)
    receipt_raw = _read(execution_receipt_path) if execution_receipt_path is not None else None
    output.mkdir(parents=True, exist_ok=False)
    _write(output / "input.json", input_raw)
    if receipt_raw is not None:
        _write(output / RECEIPT_NAME, receipt_raw)
    retained_at = datetime.now(timezone.utc)
    retention_raw = _raw({
        "format": FORMAT,
        "retained_at": retained_at,
        "input": _description(input_raw),
        "research_execution_receipt": (
            {**_description(receipt_raw), "status": "RETAINED_UNVALIDATED"}
            if receipt_raw is not None else None
        ),
    })
    _write(output / "retention.json", retention_raw)
    try:
        package = ResearchCommitPackage.model_validate(_json(input_raw))
        if package.proposed_committed_at > retained_at:
            raise ValueError("future commit is not an observed commit")
        result = commit_research_package(package)
    except (ValueError, RuntimeError) as exc:
        # Never print untrusted source text, Pydantic input values or secrets.
        _write(output / "commit-rejection.json", _raw({
            "format": FORMAT, "status": "INPUT_RETAINED_COMMIT_REJECTED",
            "error_type": type(exc).__name__, "retention": _description(retention_raw),
            "investment_authority": "NONE",
        }))
        raise ValueError("input retained; original Research commit rejected") from None
    result_raw = _raw(result)
    _write(output / "research-commit.json", result_raw)
    _write(output / "commit.json", _raw(_commit_receipt(result, result_raw, retention_raw)))
    return read_retained_commit(output)


def main(argv=None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Research commit/retention; no Market or Odds.")
    commands = parser.add_subparsers(dest="command", required=True)
    commit = commands.add_parser("commit")
    commit.add_argument("package", type=Path)
    commit.add_argument("--output", type=Path, required=True)
    commit.add_argument("--execution-receipt", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = (commit_research_file(args.package, output=args.output,
                                      execution_receipt_path=args.execution_receipt)
                  if args.command == "commit" else read_retained_commit(args.output))
    except (OSError, ValueError, RuntimeError, TypeError, KeyError):
        print("RESEARCH COMMIT NOT VERIFIED; inspect retained files; no overwrite/retry.",
              file=stderr or sys.stderr)
        return 2
    print(f"RESEARCH: {result.research_snapshot.status.value}", file=stdout or sys.stdout)
    print("MARKET: NOT_REQUESTED; ODDS: NOT_COMPUTED; INVESTMENT AUTHORITY: NONE",
          file=stdout or sys.stdout)
    print("RETENTION: LOCAL_ONLY; GitHub publication requires separate exact readback.",
          file=stdout or sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
