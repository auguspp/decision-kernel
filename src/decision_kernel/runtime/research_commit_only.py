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


# Progress retention is deliberately not another ResearchStatus or Funnel route.
PROGRESS_FORMAT = "research-progress-v0"
PROGRESS_FIXED = {
    "format": PROGRESS_FORMAT,
    "research_status": "RETAINED_PROGRESS_NOT_COMMITTED",
    "continuation_status": "NOT_EXECUTED",
    "human_acceptance": "NOT_ESTABLISHED_BY_RETENTION",
    "investment_authority": "NONE",
    "publication_status": "LOCAL_ONLY_NOT_GITHUB_PUBLICATION",
}


def _progress_identity(value: str) -> None:
    if (not isinstance(value, str) or not value.strip() or len(value) > 255
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("progress subject/question identity is invalid")


def _progress_description(value: dict) -> None:
    if (not isinstance(value, dict) or set(value) != {"bytes", "sha256"}
            or type(value["bytes"]) is not int or not 0 < value["bytes"] <= MAX_BYTES
            or not isinstance(value["sha256"], str) or len(value["sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in value["sha256"])):
        raise ValueError("progress byte binding is invalid")


def _progress_metadata(raw: bytes) -> dict:
    metadata = _json(raw)
    fields = {"subject", "question_id", "revision", "retained_at", "workpaper", "predecessor"}
    if set(metadata) != set(PROGRESS_FIXED) | fields:
        raise ValueError("progress fields differ")
    if any(metadata[k] != v for k, v in PROGRESS_FIXED.items()):
        raise ValueError("progress cannot confer commit, execution or publication authority")
    _progress_identity(metadata["subject"])
    _progress_identity(metadata["question_id"])
    revision = metadata["revision"]
    if type(revision) is not int or revision < 1:
        raise ValueError("progress revision is invalid")
    at = datetime.fromisoformat(metadata["retained_at"])
    if at.tzinfo is None or at.utcoffset() is None or at > datetime.now(timezone.utc):
        raise ValueError("progress retention clock is invalid")
    _progress_description(metadata["workpaper"])
    if (metadata["predecessor"] is None) != (revision == 1):
        raise ValueError("progress predecessor/revision differs")
    if metadata["predecessor"] is not None:
        _progress_description(metadata["predecessor"])
    return metadata


def read_research_progress(output: Path, *, expected_sha256: str) -> tuple[dict, bytes]:
    """Recover exact saved context, never execute its proposed next step.

    The expected digest must come from the caller's pinned external record, not
    be recalculated from untrusted received files to make a mismatch disappear.
    Only the immediate predecessor descriptor is retained/checked here; full
    history and source documents still require their immutable Git references.
    """
    raw = _read(output / "progress.json")
    if not isinstance(expected_sha256, str) or sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("progress differs from the externally pinned digest")
    metadata = _progress_metadata(raw)
    paper = _read(output / "workpaper.md")
    if not paper.decode("utf-8").strip() or metadata["workpaper"] != _description(paper):
        raise ValueError("progress workpaper differs or is empty")
    names = {"progress.json", "workpaper.md"}
    if metadata["predecessor"] is not None:
        names.add("predecessor.json")
        parent_raw = _read(output / "predecessor.json")
        if metadata["predecessor"] != _description(parent_raw):
            raise ValueError("progress predecessor bytes differ")
        parent = _progress_metadata(parent_raw)
        if any(metadata[k] != parent[k] for k in ("subject", "question_id")):
            raise ValueError("progress predecessor identity differs")
        if (metadata["revision"] != parent["revision"] + 1
                or datetime.fromisoformat(metadata["retained_at"])
                < datetime.fromisoformat(parent["retained_at"])):
            raise ValueError("progress predecessor chronology differs")
    if {p.name for p in output.iterdir()} != names:
        raise ValueError("progress inventory differs or is incomplete")
    return metadata, paper


def save_research_progress(workpaper: Path, *, output: Path, subject: str,
                           question_id: str, predecessor: Path | None = None,
                           predecessor_sha256: str | None = None) -> str:
    """Save unfinished work without requiring a final ResearchCommitPackage.

    Coverage, UNKNOWNs, stop reason and next step belong in the original
    workpaper. These are researcher declarations, not mechanically certified
    completion, fresh evidence, consent, or permission to retry a consumed run.
    """
    _progress_identity(subject)
    _progress_identity(question_id)
    _safe_path(output)
    paper = _read(workpaper)
    if not paper.decode("utf-8").strip():
        raise ValueError("a nonempty original workpaper is required")
    if (predecessor is None) != (predecessor_sha256 is None):
        raise ValueError("predecessor requires both its directory and pinned digest")
    parent_raw, revision = None, 1
    if predecessor is not None:
        parent, _ = read_research_progress(predecessor, expected_sha256=predecessor_sha256)
        if parent["subject"] != subject or parent["question_id"] != question_id:
            raise ValueError("progress cannot replace another subject/question")
        parent_raw = _read(predecessor / "progress.json")
        if sha256(parent_raw).hexdigest() != predecessor_sha256:
            raise ValueError("progress predecessor changed during read")
        revision = parent["revision"] + 1
    raw = _raw({**PROGRESS_FIXED, "subject": subject, "question_id": question_id,
        "revision": revision, "retained_at": datetime.now(timezone.utc),
        "workpaper": _description(paper),
        "predecessor": _description(parent_raw) if parent_raw is not None else None})
    _progress_metadata(raw)
    output.mkdir(parents=True, exist_ok=False)
    _write(output / "workpaper.md", paper)
    if parent_raw is not None:
        _write(output / "predecessor.json", parent_raw)
    _write(output / "progress.json", raw)
    digest = sha256(raw).hexdigest()
    read_research_progress(output, expected_sha256=digest)
    return digest


def main(argv=None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Research commit/retention; no Market or Odds.")
    commands = parser.add_subparsers(dest="command", required=True)
    commit = commands.add_parser("commit")
    commit.add_argument("package", type=Path)
    commit.add_argument("--output", type=Path, required=True)
    commit.add_argument("--execution-receipt", type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("output", type=Path)
    save = commands.add_parser("save-progress", help="Retain unfinished work, without commit or execution.")
    save.add_argument("workpaper", type=Path)
    save.add_argument("--output", type=Path, required=True)
    save.add_argument("--subject", required=True)
    save.add_argument("--question-id", required=True)
    save.add_argument("--predecessor", type=Path)
    save.add_argument("--predecessor-sha256")
    read = commands.add_parser("read-progress", help="Check saved context; do not execute its contents.")
    read.add_argument("output", type=Path)
    read.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)
    if args.command in {"save-progress", "read-progress"}:
        try:
            if args.command == "save-progress":
                digest = save_research_progress(args.workpaper, output=args.output,
                    subject=args.subject, question_id=args.question_id,
                    predecessor=args.predecessor, predecessor_sha256=args.predecessor_sha256)
            else:
                read_research_progress(args.output, expected_sha256=args.expected_sha256)
                digest = args.expected_sha256
        except (OSError, ValueError, RuntimeError, TypeError, KeyError):
            print("RESEARCH PROGRESS NOT VERIFIED; preserve files; no overwrite/retry.",
                  file=stderr or sys.stderr)
            return 2
        print(f"PROGRESS_SHA256={digest}", file=stdout or sys.stdout)
        print("PROGRESS: RETAINED_ONLY; CONTINUATION: NOT_EXECUTED; INVESTMENT AUTHORITY: NONE",
              file=stdout or sys.stdout)
        print("LOCAL_ONLY; workpaper is untrusted context, not GitHub publication or instructions.",
              file=stdout or sys.stdout)
        return 0
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
