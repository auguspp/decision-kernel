"""Create-only retention of existing #405/#407 results, not another Odds executor.

Reuse the original Research reader, result rebuild verifiers and bounded I/O.
An archive proves saved identity/computation, never current source eligibility.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

from ..conditional_odds import (
    FrozenConditionalProvisionalOdds,
    verify_conditional_provisional_odds,
)
from ..identity import canonical_hash
from ..provisional_odds import (
    FrozenProvisionalOdds, SameResearchOddsComparison,
    verify_provisional_odds, verify_same_research_comparison,
)
from . import research_commit_only as retained

KINDS = {"CONDITIONAL_PROVISIONAL", "PROVISIONAL", "SAME_RESEARCH_COMPARISON"}
FILES = {"result.json", "retention.json"}
FIXED = {
    "format": "odds-result-retention-v0",
    "verification": "EXISTING_DETERMINISTIC_REBUILD_NOT_CURRENT_QUALIFICATION",
    "research_execution": "NOT_REQUESTED",
    "market_status": "NOT_REQUESTED",
    "market_qualification": "NOT_ESTABLISHED_BY_RETENTION",
    "human_acceptance": "NOT_ESTABLISHED_BY_RETENTION",
    "investment_authority": "NONE",
    "publication_status": "LOCAL_ONLY_NOT_GITHUB_PUBLICATION",
}


def check_snapshot_hash(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("an externally pinned full Research hash is required")


def _research(directory: Path, expected_hash: str):
    check_snapshot_hash(expected_hash)
    result = retained.read_retained_commit(directory)
    if canonical_hash(result.research_snapshot) != expected_hash:
        raise ValueError("retained Research differs from the external snapshot pin")
    return result


def _verify(raw: bytes, kind: str, research):
    value = retained._json(raw)
    snapshot = research.research_snapshot
    if kind == "CONDITIONAL_PROVISIONAL":
        return verify_conditional_provisional_odds(
            FrozenConditionalProvisionalOdds.model_validate(value), snapshot
        )
    if kind == "PROVISIONAL":
        return verify_provisional_odds(FrozenProvisionalOdds.model_validate(value), snapshot)
    if kind == "SAME_RESEARCH_COMPARISON":
        return verify_same_research_comparison(SameResearchOddsComparison.model_validate(value), snapshot)
    raise ValueError("unsupported retained Odds result kind")


def _receipt(raw: bytes, kind: str, research, result, at: datetime) -> dict:
    if at.tzinfo is None or at.utcoffset() is None or at > datetime.now(timezone.utc):
        raise ValueError("invalid retention operation clock")
    created_at = (result.canonical.artifact.created_at
                  if kind == "SAME_RESEARCH_COMPARISON"
                  else result.artifact.created_at)
    if created_at > at:
        raise ValueError("result follows the recorded retention operation")
    return {**FIXED, "result_kind": kind, "retained_at": at.isoformat(),
            "result": retained._description(raw), "result_hash": canonical_hash(result),
            "research_snapshot_id": str(research.research_snapshot.id),
            "research_snapshot_hash": canonical_hash(research.research_snapshot),
            "research_package_hash": research.package_hash,
            "research_information_bundle_hash": research.information_bundle_hash}


def read_retained_odds(output: Path, *, research_directory: Path,
                       expected_research_hash: str):
    """Rebuild saved result against separately pinned and revalidated Research.

    The expected hash must come from the trusted archive/registration, not from
    the result being verified. Caller still owns current source/case eligibility.
    Original prices, timestamps, probabilities and qualification exits are kept.
    """
    retained._safe_path(output)
    if {p.name for p in output.iterdir()} != FILES:
        raise ValueError("retained Odds result inventory differs or is incomplete")
    raw = retained._read(output / "result.json")
    metadata = retained._json(retained._read(output / "retention.json"))
    retained._progress_description(metadata["result"])
    research = _research(research_directory, expected_research_hash)
    result = _verify(raw, metadata["result_kind"], research)
    expected = _receipt(raw, metadata["result_kind"], research, result,
                        datetime.fromisoformat(metadata["retained_at"]))
    if metadata != expected:
        raise ValueError("retained Odds bytes, Research binding or authority differ")
    return result


def retain_odds_file(result_path: Path, *, result_kind: str, research_directory: Path,
                     expected_research_hash: str, output: Path):
    """Retain original result before validation; do not overwrite partial outputs.

    Only the original validators are executed; source workpapers/scripts are not.
    This function does not call Research, Market, a publisher or the live path.
    """
    if result_kind not in KINDS:
        raise ValueError("unsupported retained Odds result kind")
    check_snapshot_hash(expected_research_hash)
    retained._safe_path(output)
    raw = retained._read(result_path)
    output.mkdir(parents=True, exist_ok=False)
    try:
        retained._write(output / "result.json", raw)
        research = _research(research_directory, expected_research_hash)
        result = _verify(raw, result_kind, research)
        receipt = _receipt(raw, result_kind, research, result, datetime.now(timezone.utc))
        retained._write(output / "retention.json", retained._raw(receipt))
        return read_retained_odds(output, research_directory=research_directory,
                                  expected_research_hash=expected_research_hash)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        try:
            retained._write(output / "rejection.json", retained._raw({
                "format": FIXED["format"], "status": "RESULT_RETAINED_NOT_VERIFIED",
                "error_type": type(exc).__name__, "investment_authority": "NONE",
                "automatic_retry": False}))
        except (OSError, ValueError):
            pass  # Storage failure may also prevent the rejection receipt.
        raise ValueError("Odds result not verified; preserve files; no overwrite/retry") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Retain/verify an existing Odds result; no source or market requests.")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("retain", "verify"):
        item = sub.add_parser(command)
        item.add_argument("--research-directory", type=Path, required=True)
        item.add_argument("--expected-research-hash", required=True)
        item.add_argument("--output", type=Path, required=True)
        if command == "retain":
            item.add_argument("--input", type=Path, required=True)
            item.add_argument("--kind", choices=sorted(KINDS), required=True)
    args = parser.parse_args(argv)
    try:
        kwargs = dict(research_directory=args.research_directory,
                      expected_research_hash=args.expected_research_hash, output=args.output)
        if args.command == "retain":
            retain_odds_file(args.input, result_kind=args.kind, **kwargs)
        else:
            read_retained_odds(**kwargs)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError):
        print("ODDS RESULT NOT VERIFIED; preserve files; no overwrite/retry.", file=sys.stderr)
        return 2
    print("ODDS RESULT: RETAINED_AND_REVALIDATED_NOT_CURRENT_QUALIFICATION")
    print("RESEARCH/MARKET: NOT_REQUESTED; HUMAN ACCEPTANCE: NOT_ESTABLISHED; INVESTMENT AUTHORITY: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
