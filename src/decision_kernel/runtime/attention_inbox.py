from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import TextIO

from ..deep_research import DeepResearchPackage
from ..live import run_live_deep_research_package, run_live_research_commit_package
from ..research_commit import ResearchCommitPackage
from ..research_workflow_v1 import ResearchFunnelResult, ResearchFunnelTerminalState
from ..workflow import DecisionSpineResult
from . import hithink_http
from .inbox import (
    _currency_prefix,
    _format_money,
    _format_percent,
    _quiet_odds_context,
    _scenario_summary,
)


@dataclass(frozen=True)
class ResearchAttentionHandoff:
    """Harness-only display wrapper around an already-validated Research Funnel result.

    `company_name` is presentation metadata only. The Research route, PIT lineage and authority
    remain owned by the embedded `ResearchFunnelResult`; this wrapper is deliberately not a
    KernelModel and adds no new schema/state-machine semantics.
    """

    research_funnel: ResearchFunnelResult
    company_name: str | None = None

    @property
    def ticker(self) -> str:
        ticker = self.research_funnel.discovery.ticker
        if ticker is None or not ticker.strip():
            raise ValueError("ticker-centric Research attention requires discovery.ticker")
        return ticker.strip()


def parse_research_attention_handoff(raw: str) -> ResearchAttentionHandoff:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Research attention handoff must be a JSON object")

    if "research_funnel" not in payload:
        return ResearchAttentionHandoff(
            research_funnel=ResearchFunnelResult.model_validate(payload),
        )

    unexpected = set(payload) - {"company_name", "research_funnel"}
    if unexpected:
        raise ValueError(
            "Research attention wrapper contains unsupported keys: "
            + ", ".join(sorted(unexpected))
        )
    company_name = payload.get("company_name")
    if company_name is not None:
        if not isinstance(company_name, str) or not company_name.strip():
            raise ValueError("Research attention company_name must be non-empty when supplied")
        company_name = company_name.strip()

    return ResearchAttentionHandoff(
        research_funnel=ResearchFunnelResult.model_validate(payload["research_funnel"]),
        company_name=company_name,
    )


def serialize_research_attention_handoff(handoff: ResearchAttentionHandoff) -> str:
    payload: dict[str, object] = {
        "research_funnel": handoff.research_funnel.model_dump(mode="json"),
    }
    if handoff.company_name is not None:
        payload["company_name"] = handoff.company_name
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _ticker_key(value: str) -> str:
    normalized = value.strip().upper()
    return normalized.split(".", 1)[0]


def _decision_by_ticker(
    decisions: Sequence[DecisionSpineResult],
) -> dict[str, DecisionSpineResult]:
    indexed: dict[str, DecisionSpineResult] = {}
    for decision in decisions:
        key = _ticker_key(decision.human_surface.brief.ticker)
        if key in indexed:
            raise ValueError(f"Attention Inbox received duplicate current Research for {key}")
        indexed[key] = decision
    return indexed


def _group_actionable_research(
    handoffs: Sequence[ResearchAttentionHandoff],
) -> tuple[tuple[str, tuple[ResearchAttentionHandoff, ...]], ...]:
    grouped: dict[str, list[ResearchAttentionHandoff]] = {}
    for handoff in handoffs:
        if handoff.research_funnel.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED:
            continue
        key = _ticker_key(handoff.ticker)
        grouped.setdefault(key, []).append(handoff)
    return tuple((key, tuple(items)) for key, items in grouped.items())


def _company_name(
    ticker_key: str,
    handoffs: Sequence[ResearchAttentionHandoff],
    decision: DecisionSpineResult | None,
) -> str:
    if decision is not None:
        return decision.human_surface.brief.company_name
    for handoff in handoffs:
        if handoff.company_name:
            return handoff.company_name
    return ticker_key


def _research_state_line(decision: DecisionSpineResult | None) -> str:
    if decision is None:
        return "尚未建立 frozen Research · Odds 未生成"
    brief = decision.human_surface.brief
    prefix = _currency_prefix(brief.currency)
    return (
        "Research 已存在 · "
        f"{brief.odds.participation_zone.value} · "
        f"{prefix}{_format_money(brief.current_price)}"
    )


def _research_reasons(handoffs: Sequence[ResearchAttentionHandoff]) -> tuple[str, ...]:
    reasons: list[str] = []
    for handoff in handoffs:
        reason = handoff.research_funnel.terminal_reason.strip()
        if reason not in reasons:
            reasons.append(reason)
    return tuple(reasons)


def _source_lanes(handoffs: Sequence[ResearchAttentionHandoff]) -> tuple[str, ...]:
    lanes: list[str] = []
    for handoff in handoffs:
        lane = handoff.research_funnel.discovery.source_lane.strip()
        if lane not in lanes:
            lanes.append(lane)
    return tuple(lanes)


def render_attention_inbox_markdown(
    decisions: Sequence[DecisionSpineResult],
    research_handoffs: Sequence[ResearchAttentionHandoff],
    *,
    generated_at: datetime,
) -> str:
    indexed = _decision_by_ticker(decisions)
    research_groups = _group_actionable_research(research_handoffs)
    research_tickers = {ticker for ticker, _ in research_groups}
    decision_attention = tuple(
        decision
        for decision in decisions
        if decision.human_surface.attention_eligible
        and _ticker_key(decision.human_surface.brief.ticker) not in research_tickers
    )
    quiet_decisions = tuple(
        decision for decision in decisions if not decision.human_surface.attention_eligible
    )
    background_research = tuple(
        handoff
        for handoff in research_handoffs
        if handoff.research_funnel.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED
    )
    front_count = len(research_groups) + len(decision_attention)

    lines = [
        "# Attention Inbox",
        "",
        f"生成时间：{generated_at.isoformat()}",
        "",
        (
            f"**需要关注：{front_count}**　·　"
            f"后台研究处置：{len(background_research)}　·　"
            f"安静已研究：{len(quiet_decisions)}"
        ),
        "",
    ]
    if front_count == 0:
        lines.extend(
            [
                "今天没有需要你关注的东西。",
                "",
                "后台监控和低成本研究继续运行。",
                "",
            ]
        )

    for ticker, handoffs in research_groups:
        decision = indexed.get(ticker)
        name = _company_name(ticker, handoffs, decision)
        reasons = _research_reasons(handoffs)
        lanes = _source_lanes(handoffs)
        lines.extend(
            [
                f"## {name} {ticker}",
                "",
                "**为什么值得看**",
                *[f"- {reason}" for reason in reasons],
                "",
                (
                    "**当前状态：** `DEEPEN_REQUIRED` · "
                    f"{_research_state_line(decision)}"
                ),
                f"**发现来源：** {' / '.join(lanes)}",
                "",
                "<details>",
                "<summary>深入查看</summary>",
                "",
            ]
        )
        for handoff in handoffs:
            result = handoff.research_funnel
            pre = result.pre_research
            lines.extend(
                [
                    f"### {result.discovery.source_lane}",
                    "",
                    f"**触发：** {result.discovery.why_now}",
                    "",
                    "**已确认观察**",
                    *[
                        f"- {observation.statement}"
                        for observation in result.discovery.factual_observations
                    ],
                    "",
                    f"**最大疑点：** {pre.largest_unknown}",
                    "",
                    f"**下一步验证：** {pre.next_discriminating_search}",
                    "",
                ]
            )
            if result.discovery.contradiction_or_mapping_warning:
                lines.extend(
                    [
                        "**映射 / 反证警告：** "
                        + result.discovery.contradiction_or_mapping_warning,
                        "",
                    ]
                )
        if decision is not None:
            brief = decision.human_surface.brief
            lines.extend(
                [
                    "**已有 Research 状态**",
                    f"- 当前 Belief：{brief.current_belief}",
                    f"- 市场可能在定价：{brief.market_expectation}",
                    f"- Decision wake：{'YES' if decision.human_surface.attention_eligible else 'NO'}",
                    "",
                ]
            )
        lines.extend(
            [
                "_Research attention ≠ Recommendation · Investment Authority = NONE_",
                "",
                "</details>",
                "",
            ]
        )

    for decision in decision_attention:
        surface = decision.human_surface
        brief = surface.brief
        prefix = _currency_prefix(brief.currency)
        lines.extend(
            [
                f"## {brief.company_name} {brief.ticker}",
                "",
                "**为什么值得看**  ",
                brief.why_now,
                "",
                (
                    f"**当前状态：** `DECISION_WORTHY_REVIEW` · Research 已存在 · "
                    f"`{brief.odds.participation_zone.value}` · "
                    f"{prefix}{_format_money(brief.current_price)}"
                ),
                "",
                "<details>",
                "<summary>深入查看</summary>",
                "",
                f"**我们相信什么**  \n{brief.current_belief}",
                "",
                f"**市场可能在定价什么**  \n{brief.market_expectation}",
                "",
                "**关键问题**",
                *[f"- {item}" for item in brief.open_questions],
                "",
                "**失效条件**",
                *[f"- {item}" for item in brief.invalidation],
                "",
                "**监控指标**",
                *[f"- {item}" for item in brief.monitoring_triggers],
                "",
                f"系统投资权限：`{surface.investment_authority}`",
                "",
                "</details>",
                "",
            ]
        )

    if background_research:
        lines.extend(
            [
                "<details>",
                f"<summary>后台研究处置（{len(background_research)}）</summary>",
                "",
            ]
        )
        for handoff in background_research:
            result = handoff.research_funnel
            name = handoff.company_name or handoff.ticker
            lines.append(
                f"- **{name} {handoff.ticker}** — `{result.terminal_state.value}` — "
                f"{result.terminal_reason}"
            )
        lines.extend(["", "</details>", ""])

    if quiet_decisions:
        lines.extend(
            [
                "<details>",
                f"<summary>安静已研究（{len(quiet_decisions)}）</summary>",
                "",
            ]
        )
        for decision in quiet_decisions:
            brief = decision.human_surface.brief
            context = _quiet_odds_context(decision)
            prefix = _currency_prefix(brief.currency)
            lines.extend(
                [
                    (
                        f"- **{brief.company_name} {brief.ticker}** — "
                        f"{prefix}{_format_money(brief.current_price)} — "
                        f"`{brief.odds.participation_zone.value}` — "
                        "重新值得看：`ACCEPTABLE_ODDS "
                        f"{context.acceptable_operator} "
                        f"{prefix}{_format_money(context.acceptable_price)}`"
                    ),
                    (
                        "  - Frozen scenarios："
                        f"{_scenario_summary(context, currency=brief.currency)}"
                    ),
                ]
            )
        lines.extend(["", "</details>", ""])

    lines.extend(
        [
            "_Research Funnel allocates research budget; only HumanResearchSurface owns the canonical Decision wake._",
            "",
            "_Research ≠ Recommendation · Investment Authority = NONE_",
            "",
        ]
    )
    return "\n".join(lines)


def render_attention_inbox_html(
    decisions: Sequence[DecisionSpineResult],
    research_handoffs: Sequence[ResearchAttentionHandoff],
    *,
    generated_at: datetime,
) -> str:
    indexed = _decision_by_ticker(decisions)
    research_groups = _group_actionable_research(research_handoffs)
    research_tickers = {ticker for ticker, _ in research_groups}
    decision_attention = tuple(
        decision
        for decision in decisions
        if decision.human_surface.attention_eligible
        and _ticker_key(decision.human_surface.brief.ticker) not in research_tickers
    )
    quiet_decisions = tuple(
        decision for decision in decisions if not decision.human_surface.attention_eligible
    )
    background_research = tuple(
        handoff
        for handoff in research_handoffs
        if handoff.research_funnel.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED
    )
    front_count = len(research_groups) + len(decision_attention)

    def text(value: object) -> str:
        return escape(str(value), quote=True)

    def bullets(items: Sequence[str]) -> str:
        return "<ul>" + "".join(f"<li>{text(item)}</li>" for item in items) + "</ul>"

    cards: list[str] = []
    for ticker, handoffs in research_groups:
        decision = indexed.get(ticker)
        name = _company_name(ticker, handoffs, decision)
        reasons = _research_reasons(handoffs)
        lanes = _source_lanes(handoffs)
        detail_parts: list[str] = []
        for handoff in handoffs:
            result = handoff.research_funnel
            pre = result.pre_research
            warning = (
                f'<p><b>映射 / 反证警告：</b>{text(result.discovery.contradiction_or_mapping_warning)}</p>'
                if result.discovery.contradiction_or_mapping_warning
                else ""
            )
            detail_parts.append(
                f"""
                <section>
                  <h3>{text(result.discovery.source_lane)}</h3>
                  <p><b>触发：</b>{text(result.discovery.why_now)}</p>
                  <h4>已确认观察</h4>
                  {bullets(tuple(item.statement for item in result.discovery.factual_observations))}
                  <p><b>最大疑点：</b>{text(pre.largest_unknown)}</p>
                  <p><b>下一步验证：</b>{text(pre.next_discriminating_search)}</p>
                  {warning}
                </section>
                """
            )
        existing = ""
        price = ""
        if decision is not None:
            brief = decision.human_surface.brief
            prefix = _currency_prefix(brief.currency)
            price = f'<div class="price">{text(prefix)}{text(_format_money(brief.current_price))}</div>'
            existing = f"""
                <section>
                  <h3>已有 Research 状态</h3>
                  <p><b>当前 Belief：</b>{text(brief.current_belief)}</p>
                  <p><b>市场可能在定价：</b>{text(brief.market_expectation)}</p>
                  <p><b>Decision wake：</b>{'YES' if decision.human_surface.attention_eligible else 'NO'}</p>
                </section>
            """
        cards.append(
            f"""
            <article class="card research-attention">
              <div class="card-head">
                <div>
                  <p class="eyebrow">值得研究</p>
                  <h2>{text(name)} <span>{text(ticker)}</span></h2>
                </div>
                {price}
              </div>
              <section class="why"><h3>为什么值得看</h3>{bullets(reasons)}</section>
              <div class="state-row">
                <span>DEEPEN_REQUIRED</span>
                <span>{text(_research_state_line(decision))}</span>
                <span>{text(' / '.join(lanes))}</span>
              </div>
              <details class="drilldown">
                <summary>深入查看</summary>
                {''.join(detail_parts)}
                {existing}
                <p class="authority">Research attention ≠ Recommendation · Investment Authority = NONE</p>
              </details>
            </article>
            """
        )

    for decision in decision_attention:
        surface = decision.human_surface
        brief = surface.brief
        prefix = _currency_prefix(brief.currency)
        cards.append(
            f"""
            <article class="card decision-attention">
              <div class="card-head">
                <div>
                  <p class="eyebrow">需要决策复核</p>
                  <h2>{text(brief.company_name)} <span>{text(brief.ticker)}</span></h2>
                </div>
                <div class="price">{text(prefix)}{text(_format_money(brief.current_price))}</div>
              </div>
              <section class="why"><h3>为什么值得看</h3><p>{text(brief.why_now)}</p></section>
              <div class="state-row">
                <span>DECISION_WORTHY_REVIEW</span>
                <span>Research 已存在</span>
                <span>{text(brief.odds.participation_zone.value)}</span>
              </div>
              <details class="drilldown">
                <summary>深入查看</summary>
                <section><h3>我们相信什么</h3><p>{text(brief.current_belief)}</p></section>
                <section><h3>市场可能在定价什么</h3><p>{text(brief.market_expectation)}</p></section>
                <section><h3>关键问题</h3>{bullets(brief.open_questions)}</section>
                <section><h3>失效条件</h3>{bullets(brief.invalidation)}</section>
                <section><h3>监控指标</h3>{bullets(brief.monitoring_triggers)}</section>
                <p class="authority">系统投资权限：{text(surface.investment_authority)}</p>
              </details>
            </article>
            """
        )

    if not cards:
        cards.append(
            '<article class="card empty"><p class="eyebrow">今天</p>'
            '<h2>没有需要你关注的东西。</h2>'
            '<p class="muted">后台监控和低成本研究继续运行。</p></article>'
        )

    background_rows = "".join(
        f"<li><strong>{text(item.company_name or item.ticker)} {text(item.ticker)}</strong> — "
        f"{text(item.research_funnel.terminal_state.value)} — "
        f"{text(item.research_funnel.terminal_reason)}</li>"
        for item in background_research
    )
    background_block = (
        f'<details class="background"><summary>后台研究处置（{len(background_research)}）</summary>'
        f'<ul>{background_rows}</ul></details>'
        if background_research
        else ""
    )

    quiet_rows: list[str] = []
    for decision in quiet_decisions:
        brief = decision.human_surface.brief
        context = _quiet_odds_context(decision)
        prefix = _currency_prefix(brief.currency)
        quiet_rows.append(
            f"""
            <li>
              <strong>{text(brief.company_name)} {text(brief.ticker)}</strong>
              <span>{text(prefix)}{text(_format_money(brief.current_price))} · {text(brief.odds.participation_zone.value)}</span>
              <div>重新值得看：ACCEPTABLE_ODDS {text(context.acceptable_operator)} {text(prefix)}{text(_format_money(context.acceptable_price))}</div>
            </li>
            """
        )
    quiet_block = (
        f'<details class="background"><summary>安静已研究（{len(quiet_decisions)}）</summary>'
        f'<ul class="quiet-list">{"".join(quiet_rows)}</ul></details>'
        if quiet_decisions
        else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Attention Inbox</title>
<style>
:root {{ color-scheme: light dark; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
body {{ margin:0; background:#f5f6f8; color:#16181d; }}
main {{ max-width:720px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ margin:0 0 6px; font-size:30px; }}
.meta,.muted,.authority {{ color:#6b7280; }}
.counts {{ font-size:17px; font-weight:650; }}
.card {{ background:#fff; border:1px solid #e5e7eb; border-radius:18px; padding:20px; margin:16px 0; box-shadow:0 3px 14px rgba(0,0,0,.04); }}
.card.research-attention,.card.decision-attention {{ border-width:2px; }}
.card-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
.eyebrow {{ margin:0 0 4px; font-size:13px; font-weight:750; letter-spacing:.04em; }}
h2 {{ margin:0; font-size:24px; }}
h2 span {{ color:#6b7280; font-size:16px; font-weight:600; }}
.price {{ font-size:24px; font-weight:750; white-space:nowrap; }}
.why {{ border-top:0; margin-top:18px; padding-top:0; }}
.state-row {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 2px; }}
.state-row span {{ background:#f0f1f3; border-radius:999px; padding:6px 10px; font-size:12px; }}
section {{ border-top:1px solid #eceef1; padding-top:14px; margin-top:14px; }}
h3 {{ margin:0 0 8px; font-size:15px; }}
h4 {{ margin:12px 0 6px; font-size:13px; }}
p,li {{ line-height:1.6; }}
ul {{ padding-left:20px; }}
details {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:14px 16px; margin-top:18px; }}
.card .drilldown {{ background:transparent; border-style:dashed; }}
summary {{ cursor:pointer; font-weight:650; }}
.quiet-list {{ list-style:none; padding:0; }}
.quiet-list li {{ border-top:1px solid #eceef1; padding:10px 0; display:grid; gap:4px; }}
footer {{ margin-top:22px; color:#6b7280; font-size:12px; line-height:1.6; }}
@media (prefers-color-scheme: dark) {{
  body {{ background:#0f1115; color:#f3f4f6; }}
  .card,details {{ background:#171a21; border-color:#2a2f39; }}
  section,.quiet-list li {{ border-color:#2a2f39; }}
  .state-row span {{ background:#252a33; }}
  .meta,.muted,.authority,h2 span,footer {{ color:#9ca3af; }}
}}
</style>
</head>
<body>
<main>
<header>
  <h1>Attention Inbox</h1>
  <p class="meta">生成时间：{text(generated_at.isoformat())}</p>
  <p class="counts">需要关注：{front_count}　·　后台研究处置：{len(background_research)}　·　安静已研究：{len(quiet_decisions)}</p>
</header>
{''.join(cards)}
{background_block}
{quiet_block}
<footer>
Research Funnel allocates research budget; only HumanResearchSurface owns the canonical Decision wake.<br>
Research ≠ Recommendation · Investment Authority = NONE
</footer>
</main>
</body>
</html>
"""


def _run_research_package(
    raw_package: str,
    *,
    fetch_market,
    observed_at: datetime,
) -> DecisionSpineResult:
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("Attention Inbox research package must be a JSON object")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_kernel.runtime.attention_inbox",
        description="Render one ticker-centric Human Attention Inbox from existing Research outputs.",
    )
    parser.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="Current ResearchCommitPackage or DeepResearchPackage files.",
    )
    parser.add_argument(
        "--research-attention",
        action="append",
        default=[],
        type=Path,
        help=(
            "Repeatable ResearchFunnelResult or Harness wrapper JSON. "
            "Only validated DEEPEN_REQUIRED results enter the front surface."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("decision-inbox/index.html"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("decision-inbox/summary.md"),
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
    try:
        generated_at = datetime.now(timezone.utc)
        api_key = os.environ.get(hithink_http.HITHINK_API_KEY_ENV)

        def fetch_market(*, thscode: str, observed_at):
            return hithink_http.fetch_latest_hithink_observed_market(
                thscode=thscode,
                observed_at=observed_at,
                api_key=api_key,
            )

        decisions = tuple(
            _run_research_package(
                path.read_text(encoding="utf-8"),
                fetch_market=fetch_market,
                observed_at=generated_at,
            )
            for path in args.packages
        )
        handoffs = tuple(
            parse_research_attention_handoff(path.read_text(encoding="utf-8"))
            for path in args.research_attention
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            render_attention_inbox_html(decisions, handoffs, generated_at=generated_at),
            encoding="utf-8",
        )
        args.summary.write_text(
            render_attention_inbox_markdown(decisions, handoffs, generated_at=generated_at),
            encoding="utf-8",
        )
        decision_wakes = sum(item.human_surface.attention_eligible for item in decisions)
        deepen = sum(
            item.research_funnel.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED
            for item in handoffs
        )
        print(
            f"ATTENTION INBOX: {deepen} research attention / {decision_wakes} decision wake / "
            f"{len(handoffs)} research handoffs / {len(decisions)} researched cases",
            file=stdout,
        )
        print(f"HTML: {args.output}", file=stdout)
        print(f"SUMMARY: {args.summary}", file=stdout)
        return 0
    except (OSError, ValueError) as exc:
        print(f"Attention Inbox failed: {exc}", file=stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
