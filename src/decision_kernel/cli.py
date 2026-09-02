from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from .deep_research import DeepResearchPackage
from .live import run_live_deep_research_package, run_live_research_commit_package
from .research_commit import ResearchCommitPackage
from .runtime import cninfo_http, hithink_http
from .runtime.disclosure_radar import (
    filter_research_uncovered_disclosure_batches,
    group_disclosures_by_publication_date,
)
from .runtime.inbox import render_decision_inbox_html, render_decision_inbox_markdown
from .workflow import DecisionSpineResult


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


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
    disclosure_scan = subparsers.add_parser(
        "scan-disclosures",
        help=(
            "One-shot scan for official CNINFO disclosure batches newer than frozen Research."
        ),
    )
    disclosure_scan.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="One current ResearchCommitPackage or DeepResearchPackage per A-share security.",
    )
    disclosure_scan.add_argument(
        "--through",
        type=date.fromisoformat,
        required=True,
        help="Inclusive CNINFO scan end date in YYYY-MM-DD form.",
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


def _research_snapshot_from_raw_package(raw_package: str):
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("disclosure scan research package must be a JSON object")
    if "deep_research" in payload and "discovery" in payload:
        return DeepResearchPackage.model_validate(payload).research_snapshot
    return ResearchCommitPackage.model_validate(payload).research_snapshot


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

        if args.command == "scan-disclosures":
            research_as_of_by_stock: dict[str, datetime] = {}
            company_by_stock: dict[str, str] = {}
            scan_inputs: list[tuple[str, date]] = []

            for package_path in args.packages:
                snapshot = _research_snapshot_from_raw_package(
                    package_path.read_text(encoding="utf-8")
                )
                ticker = snapshot.ticker.strip()
                if ticker in research_as_of_by_stock:
                    raise ValueError(
                        f"disclosure scan received more than one current Research package for {ticker}"
                    )
                start_date = snapshot.as_of_datetime.astimezone(SHANGHAI_TZ).date()
                if start_date > args.through:
                    raise ValueError(
                        f"disclosure scan end date precedes frozen Research for {ticker}"
                    )

                research_as_of_by_stock[ticker] = snapshot.as_of_datetime
                company_by_stock[ticker] = snapshot.company_name
                scan_inputs.append((ticker, start_date))

            announcements = []
            for ticker, start_date in scan_inputs:
                batch = cninfo_http.fetch_cninfo_disclosures(
                    stock_code=ticker,
                    start_date=start_date,
                    end_date=args.through,
                )
                announcements.extend(batch.announcements)

            batches = group_disclosures_by_publication_date(announcements)
            uncovered = filter_research_uncovered_disclosure_batches(
                batches,
                research_as_of_by_stock=research_as_of_by_stock,
            )

            print(
                "OFFICIAL DISCLOSURE SCAN: "
                f"{len(uncovered)} research-uncovered / "
                f"{len(batches)} dated batches / "
                f"{len(announcements)} announcements / "
                f"{len(research_as_of_by_stock)} research cases",
                file=stdout,
            )
            if not uncovered:
                print("NO RESEARCH-UNCOVERED OFFICIAL DISCLOSURES", file=stdout)
            for batch in uncovered:
                print(
                    "UNCOVERED: "
                    f"{batch.stock_code} {company_by_stock[batch.stock_code]} | "
                    f"research_as_of={research_as_of_by_stock[batch.stock_code].isoformat()} | "
                    f"publication_date={batch.publication_date.isoformat()} | "
                    f"announcements={len(batch.announcements)}",
                    file=stdout,
                )
                for item in batch.announcements:
                    print(
                        f"- {item.announcement_id} | {item.title} | {item.source_locator}",
                        file=stdout,
                    )
            print("RESEARCH STATUS: UNASSESSED", file=stdout)
            print("INVESTMENT AUTHORITY: NONE", file=stdout)
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
