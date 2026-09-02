from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from .deep_research import DeepResearchPackage
from .live import run_live_deep_research_package, run_live_research_commit_package
from .research_commit import ResearchCommitPackage
from .runtime import hithink_http
from .runtime.inbox import render_decision_inbox_html, render_decision_inbox_markdown
from .workflow import DecisionSpineResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision-kernel",
        description="Run reviewed research through live Odds and Human gating.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser(
        "run",
        help="Run a Decision OS Research Method v1 DeepResearchPackage.",
    )
    run.add_argument(
        "package",
        type=Path,
        help="Path to one DeepResearchPackage JSON file.",
    )
    generic = subparsers.add_parser(
        "run-research",
        help="Run a method-agnostic ResearchCommitPackage.",
    )
    generic.add_argument(
        "package",
        type=Path,
        help="Path to one ResearchCommitPackage JSON file.",
    )
    inbox = subparsers.add_parser(
        "build-inbox",
        help="Run reviewed research packages and render one Human Decision Inbox.",
    )
    inbox.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="ResearchCommitPackage or DeepResearchPackage JSON files to include.",
    )
    inbox.add_argument(
        "--output",
        type=Path,
        default=Path("decision-inbox/index.html"),
        help="HTML output path.",
    )
    inbox.add_argument(
        "--summary",
        type=Path,
        default=Path("decision-inbox/summary.md"),
        help="Markdown summary output path.",
    )
    return parser


def _run_inbox_package(
    raw_package: str,
    *,
    fetch_market,
    observed_at: datetime,
) -> DecisionSpineResult:
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("inbox research package must be a JSON object")

    if "deep_research" in payload and "discovery" in payload:
        package = DeepResearchPackage.model_validate(payload)
        return run_live_deep_research_package(
            package=package,
            fetch_market=fetch_market,
            observed_at=observed_at,
        ).decision

    package = ResearchCommitPackage.model_validate(payload)
    return run_live_research_commit_package(
        package=package,
        fetch_market=fetch_market,
        observed_at=observed_at,
    ).decision


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    try:
        api_key = os.environ.get(hithink_http.HITHINK_API_KEY_ENV)

        def fetch_market(*, thscode: str, observed_at):
            return hithink_http.fetch_latest_hithink_observed_market(
                thscode=thscode,
                observed_at=observed_at,
                api_key=api_key,
            )

        if args.command == "build-inbox":
            generated_at = datetime.now(timezone.utc)
            decisions = [
                _run_inbox_package(
                    package_path.read_text(encoding="utf-8"),
                    fetch_market=fetch_market,
                    observed_at=generated_at,
                )
                for package_path in args.packages
            ]

            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                render_decision_inbox_html(decisions, generated_at=generated_at),
                encoding="utf-8",
            )
            args.summary.write_text(
                render_decision_inbox_markdown(decisions, generated_at=generated_at),
                encoding="utf-8",
            )
            attention = sum(
                decision.human_surface.attention_eligible for decision in decisions
            )
            print(
                f"DECISION INBOX: {attention} attention / {len(decisions)} total",
                file=stdout,
            )
            print(f"HTML: {args.output}", file=stdout)
            print(f"SUMMARY: {args.summary}", file=stdout)
            return 0

        raw_package = args.package.read_text(encoding="utf-8")
        if args.command == "run":
            package = DeepResearchPackage.model_validate_json(raw_package)
            decision = run_live_deep_research_package(
                package=package,
                fetch_market=fetch_market,
            ).decision
        elif args.command == "run-research":
            package = ResearchCommitPackage.model_validate_json(raw_package)
            decision = run_live_research_commit_package(
                package=package,
                fetch_market=fetch_market,
            ).decision
        else:
            raise AssertionError(f"unsupported command: {args.command}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2

    _print_decision(decision, stdout=stdout)
    return 0


def _print_decision(decision: DecisionSpineResult, *, stdout: TextIO) -> None:
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
