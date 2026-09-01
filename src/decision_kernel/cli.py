from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from .adapters.hithink import HITHINK_API_KEY_ENV
from .deep_research import DeepResearchPackage
from .live import run_live_deep_research_package
from .workflow import DeepenedDecisionResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision-kernel",
        description="Run one accepted Deep Research package through live Odds and Human gating.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser(
        "run",
        help="Run a DeepResearchPackage with the latest qualified HiThink completed close.",
    )
    run.add_argument(
        "package",
        type=Path,
        help="Path to one DeepResearchPackage JSON file.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    if args.command != "run":
        raise AssertionError(f"unsupported command: {args.command}")

    try:
        package = DeepResearchPackage.model_validate_json(
            args.package.read_text(encoding="utf-8")
        )
        result = run_live_deep_research_package(
            package=package,
            api_key=os.environ.get(HITHINK_API_KEY_ENV),
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2

    _print_result(result, stdout=stdout)
    return 0


def _print_result(result: DeepenedDecisionResult, *, stdout: TextIO) -> None:
    decision = result.decision
    surface = decision.human_surface
    brief = surface.brief
    market = decision.odds.artifact.observed_market

    print("DECISION KERNEL", file=stdout)
    print(f"STATE: {decision.terminal_state.value}", file=stdout)
    print(f"SECURITY: {brief.ticker} {brief.company_name}", file=stdout)
    print(
        "PRICE: "
        f"{market.market_price} {market.currency} @ {market.market_timestamp.isoformat()}",
        file=stdout,
    )
    print(f"ODDS: {brief.odds.participation_zone.value}", file=stdout)
    print(
        "HUMAN ATTENTION: " + ("YES" if surface.attention_eligible else "NO"),
        file=stdout,
    )
    print(f"INVESTMENT AUTHORITY: {surface.investment_authority}", file=stdout)

    if not surface.attention_eligible:
        print(f"QUIET REASON: {surface.eligibility_reason}", file=stdout)
        return

    print(f"WHY NOW: {brief.why_now}", file=stdout)
    print(f"CURRENT BELIEF: {brief.current_belief}", file=stdout)
    print(f"MARKET EXPECTATION: {brief.market_expectation}", file=stdout)
    print("OPEN QUESTIONS:", file=stdout)
    for item in brief.open_questions:
        print(f"- {item}", file=stdout)
    print("INVALIDATION:", file=stdout)
    for item in brief.invalidation:
        print(f"- {item}", file=stdout)
    print("MONITORING TRIGGERS:", file=stdout)
    for item in brief.monitoring_triggers:
        print(f"- {item}", file=stdout)


if __name__ == "__main__":
    raise SystemExit(main())
