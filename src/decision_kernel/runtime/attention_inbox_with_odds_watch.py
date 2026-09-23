"""Thin composition of the existing Attention Inbox and read-only Odds Watch.

This wrapper exists only to share the exact qualified-market fetches in one process.
It does not replace either underlying renderer or create another scheduler/provider.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from . import attention_inbox, hithink_http, odds_watch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_kernel.runtime.attention_inbox_with_odds_watch",
        description="Render the existing Attention Inbox plus a bounded typed Odds Watch artifact.",
    )
    parser.add_argument("packages", nargs="+", type=Path)
    parser.add_argument("--research-attention", action="append", default=[], type=Path)
    parser.add_argument("--output", type=Path, default=Path("decision-inbox/index.html"))
    parser.add_argument("--summary", type=Path, default=Path("decision-inbox/summary.md"))
    parser.add_argument("--odds-watch-config", required=True, type=Path)
    parser.add_argument("--odds-watch-registry", required=True, type=Path)
    parser.add_argument("--odds-watch-output", type=Path, default=Path("odds-watch"))
    return parser


@hithink_http.inbox_calendar_timeout_recovery()
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
        generated_at = datetime.now(timezone.utc)
        api_key = os.environ.get(hithink_http.HITHINK_API_KEY_ENV)
        cache: dict[str, object] = {}

        def fetch_market(*, thscode: str, observed_at):
            key = thscode.strip().upper()
            if key not in cache:
                cache[key] = hithink_http.fetch_latest_hithink_observed_market(
                    thscode=key,
                    observed_at=observed_at,
                    api_key=api_key,
                )
            return cache[key]

        decisions = tuple(
            attention_inbox._run_research_package(
                path.read_text(encoding="utf-8"),
                fetch_market=fetch_market,
                observed_at=generated_at,
            )
            for path in args.packages
        )
        handoffs = tuple(
            attention_inbox.parse_research_attention_handoff(path.read_text(encoding="utf-8"))
            for path in args.research_attention
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            attention_inbox.render_attention_inbox_html(
                decisions, handoffs, generated_at=generated_at
            ),
            encoding="utf-8",
        )
        args.summary.write_text(
            attention_inbox.render_attention_inbox_markdown(
                decisions, handoffs, generated_at=generated_at
            ),
            encoding="utf-8",
        )

        config = odds_watch.load_json(args.odds_watch_config)
        registry = odds_watch.load_json(args.odds_watch_registry)
        report = odds_watch.build_watch(
            config=config,
            registry=registry,
            observed_at=generated_at,
            fetch_market=fetch_market,
        )
        odds_watch.validate_report(report)
        odds_watch.write_watch(report=report, output_dir=args.odds_watch_output)

        research_attention = sum(
            item.terminal_state
            is attention_inbox.ResearchFunnelTerminalState.DEEPEN_REQUIRED
            for item in handoffs
        )
        decision_wake = sum(item.human_surface.attention_eligible for item in decisions)
        print(
            "ATTENTION INBOX: "
            f"{research_attention} research attention / {decision_wake} decision wake / "
            f"{len(handoffs)} research handoffs / {len(decisions)} researched cases",
            file=stdout,
        )
        print(
            "ODDS WATCH: "
            f"{report['watch']['attention_case_count']} review / "
            f"{report['watch']['price_gap_count']} price gaps / "
            f"{report['watch']['active_case_count']} active cases",
            file=stdout,
        )
        print(f"HTML: {args.output}", file=stdout)
        print(f"SUMMARY: {args.summary}", file=stdout)
        print(f"WATCH: {args.odds_watch_output / 'watch.json'}", file=stdout)
        return 0
    except (OSError, ValueError) as exc:
        print(f"Attention Inbox + Odds Watch failed: {type(exc).__name__}", file=stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
