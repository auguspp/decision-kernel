"""Compose saved research price checks and the existing read-only Odds Watch.

Explicit source failures are retained as coverage gaps, not a quiet result.
No provider fallback, new retry policy, or research/decision authority is added.
"""
from __future__ import annotations

import argparse
from html import escape
import os
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO
from urllib.error import HTTPError

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


def coverage_text(planned: int, completed: int, gaps: list[str], report: dict) -> str:
    watch = report["watch"]
    active = watch["active_case_count"]
    unknown = watch["price_gap_count"]
    triggered = watch["attention_case_count"]
    checked = active - unknown
    text = (f"原有研究包价格复核：完成 {completed}/{planned}，无法判断 {len(gaps)}。"
            f"Watch：已启用 {active}，已完成判断 {checked}；"
            f"确认触界 {triggered}，未触界 {checked - triggered}，无法判断 {unknown}。")
    if gaps or unknown:
        text += " 本次为部分可用交付；缺口不等于未触界，也不要求你手工核价。"
    return text


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
        config = odds_watch.load_json(args.odds_watch_config)
        registry = odds_watch.load_json(args.odds_watch_registry)
        odds_watch.validate_config(config, registry)
        cache: dict[str, object] = {}
        failures: dict[str, hithink_http.HithinkRuntimeError] = {}
        shared_failure = None
        requested_ticker = None

        def fetch_market(*, thscode: str, observed_at):
            nonlocal shared_failure, requested_ticker
            key = thscode.strip().upper()
            requested_ticker = key
            if key in failures:
                raise failures[key]
            if key not in cache:
                if shared_failure is not None:
                    raise shared_failure
                try:
                    cache[key] = hithink_http.fetch_latest_hithink_observed_market(
                        thscode=key, observed_at=observed_at, api_key=api_key,
                    )
                except hithink_http.HithinkRuntimeError as exc:
                    failures[key] = exc
                    # Do not let another ticker repeat account-wide rejection.
                    # Calendar exhaustion already uses the original batch latch.
                    cause = exc.__cause__
                    if isinstance(cause, HTTPError) and cause.code in {401, 403, 429}:
                        shared_failure = exc
                    raise
            return cache[key]

        decisions = []
        gaps = []
        for path in args.packages:
            requested_ticker = None
            try:
                decisions.append(attention_inbox._run_research_package(
                    path.read_text(encoding="utf-8"), fetch_market=fetch_market,
                    observed_at=generated_at,
                ))
            except hithink_http.HithinkRuntimeError:
                if requested_ticker is None:
                    raise  # Not an identified market acquisition failure.
                gaps.append(f"{path.name} / {requested_ticker}")
        handoffs = tuple(
            attention_inbox.parse_research_attention_handoff(path.read_text(encoding="utf-8"))
            for path in args.research_attention
        )
        report = odds_watch.build_watch(
            config=config, registry=registry, observed_at=generated_at,
            fetch_market=fetch_market,
        )
        odds_watch.validate_report(report)
        # Configuration, package integrity and unexpected exceptions still fail
        # before any delivery is written. Only typed source gaps are composable.
        summary = attention_inbox.render_attention_inbox_markdown(
            decisions, handoffs, generated_at=generated_at,
        )
        page = attention_inbox.render_attention_inbox_html(
            decisions, handoffs, generated_at=generated_at,
        )
        coverage = coverage_text(len(args.packages), len(decisions), gaps, report)
        degraded = bool(gaps or report["watch"]["price_gap_count"])
        # These are presentation-only legacy empty-state phrases, not decisions.
        # Scope their assertions even when all requested prices were available.
        for before, after in (
            ("今天没有需要你关注的东西。", "已完成的原有研究包复核未产生新的关注项；Watch与日常Quick分别查看。"),
            ("今天没有 case 需要人工复核。", "已完成读取的原有研究包中，未发现待人工复核项。"),
            ("后台监控和低成本研究继续运行。", "这不是当天Hosted Quick结果或全市场无变化的结论。"),
            ("后台监控继续运行；没有新的 Human attention requirement。", "本结论只覆盖上方已完成的读取范围。"),
        ):
            summary = summary.replace(before, after)
            page = page.replace(before, after)
        if degraded:
            page = re.sub(r'<article class="card empty">.*?</article>', '', page,
                          count=1, flags=re.DOTALL)
        gap_text = "\n".join(f"- {item}：PRICE_UNAVAILABLE_NOT_QUIET" for item in gaps)
        summary = "# 本次读取覆盖\n\n" + coverage + "\n\n" + gap_text + "\n\n" + summary
        block = '<aside><h2>本次读取覆盖</h2><p>' + escape(coverage) + '</p>'
        block += ''.join('<p>' + escape(item) + '：PRICE_UNAVAILABLE_NOT_QUIET</p>' for item in gaps)
        block += '</aside>'
        if "</header>" not in page:
            raise ValueError("INBOX_HEADER_REQUIRED")
        page = page.replace("</header>", "</header>" + block, 1)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(page, encoding="utf-8")
        args.summary.write_text(summary, encoding="utf-8")
        odds_watch.write_watch(report=report, output_dir=args.odds_watch_output)
        research_attention = sum(
            item.terminal_state is attention_inbox.ResearchFunnelTerminalState.DEEPEN_REQUIRED
            for item in handoffs
        )
        decision_wake = sum(item.human_surface.attention_eligible for item in decisions)
        print("ATTENTION INBOX: "
              f"{research_attention} research attention / {decision_wake} decision wake / "
              f"{len(handoffs)} research handoffs / {len(decisions)} researched cases", file=stdout)
        print("ODDS WATCH: "
              f"{report['watch']['attention_case_count']} review / "
              f"{report['watch']['price_gap_count']} price gaps / "
              f"{report['watch']['active_case_count']} active cases", file=stdout)
        print("DELIVERY=" + ("DEGRADED_SOURCE_GAPS" if degraded else "COMPLETE_REQUESTED_SCOPE"), file=stdout)
        print(coverage, file=stdout)
        print(f"HTML: {args.output}\nSUMMARY: {args.summary}\nWATCH: {args.odds_watch_output / 'watch.json'}", file=stdout)
        return 0  # Delivery succeeded, not a claim that source acquisition did.
    except (OSError, ValueError, hithink_http.HithinkRuntimeError) as exc:
        print(f"Attention Inbox + Odds Watch failed: {type(exc).__name__}", file=stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
