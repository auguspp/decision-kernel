from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from .external_research_execution import ExternalResearchInputPacket
    from .single_quick_contract import SingleQuickCandidate

from ..deep_research import DeepResearchPackage
from ..live import run_live_deep_research_package, run_live_research_commit_package
from ..research_commit import ResearchCommitPackage
from ..research_workflow_v1 import ResearchFunnelResult, ResearchFunnelTerminalState
from ..workflow import DecisionSpineResult
from . import hithink_http
from .inbox import (
    _currency_prefix,
    _format_money,
    render_decision_inbox_html,
    render_decision_inbox_markdown,
)


@dataclass(frozen=True)
class ResearchAttentionHandoff:
    """Presentation wrapper for explicit legacy or single-Quick results.

    The original versioned validators own identity/lineage and route shape.
    This wrapper grants no admission, semantic acceptance or investment power;
    registration still checks the exact saved execution and source bytes.
    """

    research_funnel: ResearchFunnelResult | None = None
    company_name: str | None = None
    single_quick_input: ExternalResearchInputPacket | None = None
    single_quick_candidate: SingleQuickCandidate | None = None

    def __post_init__(self):
        from .single_quick_contract import validate_single_quick
        single = self.single_quick_input is not None or self.single_quick_candidate is not None
        if single:
            if self.research_funnel is not None or self.single_quick_input is None or self.single_quick_candidate is None:
                raise ValueError("Mixed or incomplete Research attention versions")
            checked = validate_single_quick(packet=self.single_quick_input, candidate=self.single_quick_candidate)
            if checked.status != "VALIDATED_QUICK_RESULT":
                raise ValueError("Execution gap is not a business attention handoff")
        elif self.research_funnel is None:
            raise ValueError("Research attention result missing")

    @property
    def discovery(self):
        return self.single_quick_candidate.discovery if self.single_quick_candidate is not None else self.research_funnel.discovery

    @property
    def terminal_state(self):
        if self.single_quick_candidate is None:
            return self.research_funnel.terminal_state
        from .single_quick_contract import validate_single_quick
        return validate_single_quick(packet=self.single_quick_input, candidate=self.single_quick_candidate).terminal_state

    @property
    def terminal_reason(self):
        return self.single_quick_candidate.assessment.route_reason if self.single_quick_candidate is not None else self.research_funnel.terminal_reason

    @property
    def explanation(self):
        return self.single_quick_candidate.assessment.explanation if self.single_quick_candidate is not None else self.terminal_reason

    @property
    def largest_unknown(self):
        if self.single_quick_candidate is not None:
            return "；".join(self.single_quick_candidate.assessment.unknowns) or "本次未列出；不证明所有未知均已解决"
        return self.research_funnel.pre_research.largest_unknown

    @property
    def next_discriminating_search(self):
        if self.single_quick_candidate is not None:
            a = self.single_quick_candidate.assessment
            return a.investigation.available_work if a.investigation else (a.wait_trigger or a.route_reason)
        return self.research_funnel.pre_research.next_discriminating_search

    @property
    def identity_material(self):
        if self.single_quick_candidate is None:
            return self.research_funnel.model_dump(mode="json")
        return {"input": self.single_quick_input.model_dump(mode="json"),
                "candidate": self.single_quick_candidate.model_dump(mode="json")}

    @property
    def ticker(self) -> str:
        ticker = self.discovery.ticker
        if ticker is None or not ticker.strip():
            raise ValueError("ticker-centric Research attention requires discovery.ticker")
        return ticker.strip()


def parse_research_attention_handoff(raw: str) -> ResearchAttentionHandoff:
    from .external_research_identity import _json
    payload = _json(raw.encode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Research attention handoff must be a JSON object")

    if payload.get("format") == "single-quick-attention-v1":
        from .single_quick_contract import read_saved_result, SingleQuickCandidate
        from .saved_research_once import raw as encode
        if set(payload) - {"format", "input", "candidate", "company_name"}:
            raise ValueError("Unsupported single Quick attention fields")
        packet, candidate, _ = read_saved_result(encode(payload["input"]), encode(payload["candidate"]))
        if not isinstance(candidate, SingleQuickCandidate):
            raise ValueError("Single Quick attention requires its explicit result version")
        name = payload.get("company_name")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("Research attention company_name must be non-empty when supplied")
        return ResearchAttentionHandoff(company_name=name.strip() if name else None,
            single_quick_input=packet, single_quick_candidate=candidate)

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
    handoff.__post_init__()
    payload: dict[str, object] = ({"research_funnel": handoff.research_funnel.model_dump(mode="json")}
        if handoff.single_quick_candidate is None else
        {"format": "single-quick-attention-v1", **handoff.identity_material})
    if handoff.company_name is not None:
        payload["company_name"] = handoff.company_name
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _ticker_key(value: str) -> str:
    return value.strip().upper().split(".", 1)[0]


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
        if handoff.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED:
            continue
        grouped.setdefault(_ticker_key(handoff.ticker), []).append(handoff)
    return tuple((ticker, tuple(items)) for ticker, items in grouped.items())


def _company_name(
    ticker: str,
    handoffs: Sequence[ResearchAttentionHandoff],
    decision: DecisionSpineResult | None,
) -> str:
    if decision is not None:
        return decision.human_surface.brief.company_name
    return next((item.company_name for item in handoffs if item.company_name), ticker)


def _research_state(decision: DecisionSpineResult | None) -> str:
    if decision is None:
        return "尚未建立 frozen Research · Odds 未生成"
    brief = decision.human_surface.brief
    prefix = _currency_prefix(brief.currency)
    return (
        "Research 已存在 · "
        f"{brief.odds.participation_zone.value} · "
        f"{prefix}{_format_money(brief.current_price)}"
    )


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return tuple(ordered)


def _markdown_text(value: object) -> str:
    text = escape(str(value), quote=True).replace("\n", " ").replace("\r", " ")
    for char in "`[]()|*_!":
        text = text.replace(char, "&#" + str(ord(char)) + ";")
    return text


def _markdown_lane(value: str) -> str:
    """Keep safe machine labels legible without allowing source Markdown."""
    if re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*", value):
        return value
    return _markdown_text(value)


def _render_research_markdown(
    ticker: str,
    handoffs: Sequence[ResearchAttentionHandoff],
    decision: DecisionSpineResult | None,
) -> str:
    name = _company_name(ticker, handoffs, decision)
    reasons = _unique(tuple(item.explanation for item in handoffs))
    lanes = _unique(tuple(item.discovery.source_lane for item in handoffs))
    lines = [
        f"## {_markdown_text(name)} {_markdown_text(ticker)}",
        "",
        "**为什么值得看**",
        *[f"- {_markdown_text(reason)}" for reason in reasons],
        "",
        f"**当前状态：** `DEEPEN_REQUIRED` · {_research_state(decision)}",
        f"**发现来源：** {' / '.join(_markdown_lane(lane) for lane in lanes)}",
        "",
        "<details>",
        "<summary>深入查看</summary>",
        "",
    ]
    for handoff in handoffs:
        result = handoff
        lines.extend(
            [
                f"### {_markdown_lane(result.discovery.source_lane)}",
                "",
                f"**触发：** {_markdown_text(result.discovery.why_now)}",
                "",
                "**已确认观察**",
                *[
                    f"- {_markdown_text(observation.statement)}"
                    for observation in result.discovery.factual_observations
                ],
                "",
                f"**最大疑点：** {_markdown_text(result.largest_unknown)}",
                "",
                f"**下一步验证：** {_markdown_text(result.next_discriminating_search)}",
                "",
            ]
        )
        if result.discovery.contradiction_or_mapping_warning:
            lines.extend(
                [
                    "**映射 / 反证警告：** "
                    + _markdown_text(result.discovery.contradiction_or_mapping_warning),
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
    return "\n".join(lines)


def _render_research_html(
    ticker: str,
    handoffs: Sequence[ResearchAttentionHandoff],
    decision: DecisionSpineResult | None,
) -> str:
    def text(value: object) -> str:
        return escape(str(value), quote=True)

    name = _company_name(ticker, handoffs, decision)
    reasons = _unique(tuple(item.explanation for item in handoffs))
    lanes = _unique(tuple(item.discovery.source_lane for item in handoffs))
    price = ""
    existing = ""
    if decision is not None:
        brief = decision.human_surface.brief
        prefix = _currency_prefix(brief.currency)
        price = f'<div class="price">{text(prefix)}{text(_format_money(brief.current_price))}</div>'
        existing = f"""
        <section><h3>已有 Research 状态</h3>
          <p><b>当前 Belief：</b>{text(brief.current_belief)}</p>
          <p><b>市场可能在定价：</b>{text(brief.market_expectation)}</p>
          <p><b>Decision wake：</b>{'YES' if decision.human_surface.attention_eligible else 'NO'}</p>
        </section>
        """

    details: list[str] = []
    for handoff in handoffs:
        result = handoff
        observations = "".join(
            f"<li>{text(item.statement)}</li>"
            for item in result.discovery.factual_observations
        )
        warning = (
            f'<p><b>映射 / 反证警告：</b>{text(result.discovery.contradiction_or_mapping_warning)}</p>'
            if result.discovery.contradiction_or_mapping_warning
            else ""
        )
        details.append(
            f"""
            <section><h3>{text(result.discovery.source_lane)}</h3>
              <p><b>触发：</b>{text(result.discovery.why_now)}</p>
              <p><b>已确认观察</b></p><ul>{observations}</ul>
              <p><b>最大疑点：</b>{text(result.largest_unknown)}</p>
              <p><b>下一步验证：</b>{text(result.next_discriminating_search)}</p>
              {warning}
            </section>
            """
        )

    reason_list = "".join(f"<li>{text(reason)}</li>" for reason in reasons)
    return f"""
    <article class="card attention research-attention">
      <div class="card-head">
        <div><p class="eyebrow">值得研究</p><h2>{text(name)} <span>{text(ticker)}</span></h2></div>
        {price}
      </div>
      <section class="why-now"><h3>为什么值得看</h3><ul>{reason_list}</ul></section>
      <div class="state-row">
        <span>DEEPEN_REQUIRED</span><span>{text(_research_state(decision))}</span>
        <span>{text(' / '.join(lanes))}</span>
      </div>
      <details class="drilldown"><summary>深入查看</summary>
        {''.join(details)}{existing}
        <p class="authority">Research attention ≠ Recommendation · Investment Authority = NONE</p>
      </details>
    </article>
    """


def _background_markdown(handoffs: Sequence[ResearchAttentionHandoff]) -> str:
    if not handoffs:
        return ""
    lines = [
        "<details>",
        f"<summary>后台研究处置（{len(handoffs)}）</summary>",
        "",
    ]
    for handoff in handoffs:
        result = handoff
        name = handoff.company_name or handoff.ticker
        lines.append(
            f"- **{_markdown_text(name)} {_markdown_text(handoff.ticker)}** — `{result.terminal_state.value}` — "
            f"{_markdown_text(result.terminal_reason)}"
        )
        if handoff.single_quick_candidate is not None:
            lines += ["  - 为什么值得看：" + _markdown_text(handoff.explanation),
                      "  - 下一步／触发：" + _markdown_text(handoff.next_discriminating_search)]
    lines.extend(["", "</details>", ""])
    return "\n".join(lines)


def _background_html(handoffs: Sequence[ResearchAttentionHandoff]) -> str:
    if not handoffs:
        return ""
    rows = "".join(
        f"<li><strong>{escape(item.company_name or item.ticker)} {escape(item.ticker)}</strong> — "
        f"{escape(item.terminal_state.value)} — "
        f"{escape(item.terminal_reason)}"
        + ("<p>为什么值得看：" + escape(item.explanation) + "</p><p>下一步／触发："
           + escape(item.next_discriminating_search) + "</p>"
           if item.single_quick_candidate is not None else "") + "</li>"
        for item in handoffs
    )
    return (
        f'<details class="background"><summary>后台研究处置（{len(handoffs)}）</summary>'
        f"<ul>{rows}</ul></details>"
    )


def render_attention_inbox_markdown(
    decisions: Sequence[DecisionSpineResult],
    research_handoffs: Sequence[ResearchAttentionHandoff],
    *,
    generated_at: datetime,
) -> str:
    indexed = _decision_by_ticker(decisions)
    research_groups = _group_actionable_research(research_handoffs)
    research_tickers = {ticker for ticker, _ in research_groups}
    filtered_decisions = tuple(
        item
        for item in decisions
        if _ticker_key(item.human_surface.brief.ticker) not in research_tickers
    )
    background = tuple(
        item
        for item in research_handoffs
        if item.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED
    )
    base = render_decision_inbox_markdown(filtered_decisions, generated_at=generated_at)
    base_lines = base.splitlines()
    base_attention = sum(item.human_surface.attention_eligible for item in filtered_decisions)
    base_quiet = len(filtered_decisions) - base_attention
    front_count = len(research_groups) + base_attention

    body = base_lines[6:]
    if research_groups and base_attention == 0 and body[:4] == [
        "今天没有 case 需要人工复核。",
        "",
        "后台监控继续运行；没有新的 Human attention requirement。",
        "",
    ]:
        body = body[4:]
    if body and body[-1] == "":
        body = body[:-1]
    if body and body[-1].startswith("_Research ≠ Recommendation"):
        body = body[:-1]

    lines = [
        "# Attention Inbox",
        "",
        f"生成时间：{generated_at.isoformat()}",
        "",
        (
            f"**需要关注：{front_count}**　·　"
            f"后台研究处置：{len(background)}　·　安静已研究：{base_quiet}"
        ),
        "",
    ]
    if front_count == 0:
        lines.extend(["今天没有需要你关注的东西。", "", "后台监控和低成本研究继续运行。", ""])
    for ticker, handoffs in research_groups:
        lines.append(_render_research_markdown(ticker, handoffs, indexed.get(ticker)))
    lines.extend(body)
    background_markdown = _background_markdown(background)
    if background_markdown:
        lines.extend(["", background_markdown])
    lines.extend(
        [
            "",
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
    filtered_decisions = tuple(
        item
        for item in decisions
        if _ticker_key(item.human_surface.brief.ticker) not in research_tickers
    )
    background = tuple(
        item
        for item in research_handoffs
        if item.terminal_state is not ResearchFunnelTerminalState.DEEPEN_REQUIRED
    )
    base_attention = sum(item.human_surface.attention_eligible for item in filtered_decisions)
    base_quiet = len(filtered_decisions) - base_attention
    front_count = len(research_groups) + base_attention

    html = render_decision_inbox_html(filtered_decisions, generated_at=generated_at)
    html = html.replace("<title>Decision Inbox</title>", "<title>Attention Inbox</title>", 1)
    html = html.replace("<h1>Decision Inbox</h1>", "<h1>Attention Inbox</h1>", 1)
    html = re.sub(
        r'<p class="counts">需要关注：\d+　·　安静：\d+</p>',
        (
            f'<p class="counts">需要关注：{front_count}　·　'
            f'后台研究处置：{len(background)}　·　安静已研究：{base_quiet}</p>'
        ),
        html,
        count=1,
    )
    if research_groups and base_attention == 0:
        html = re.sub(
            r'<article class="card empty">.*?</article>',
            "",
            html,
            count=1,
            flags=re.DOTALL,
        )
    cards = "".join(
        _render_research_html(ticker, handoffs, indexed.get(ticker))
        for ticker, handoffs in research_groups
    )
    if cards:
        html = html.replace("</header>", f"</header>\n{cards}", 1)
    background_html = _background_html(background)
    if background_html:
        html = html.replace("<footer>", f"{background_html}\n<footer>", 1)
    html = html.replace(
        "<footer>Research ≠ Recommendation · Investment Authority = NONE</footer>",
        (
            "<footer>Research Funnel allocates research budget; only HumanResearchSurface owns "
            "the canonical Decision wake.<br>Research ≠ Recommendation · Investment Authority = NONE</footer>"
        ),
        1,
    )
    return html


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
    parser.add_argument("--output", type=Path, default=Path("decision-inbox/index.html"))
    parser.add_argument("--summary", type=Path, default=Path("decision-inbox/summary.md"))
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
        print(
            "ATTENTION INBOX: "
            f"{sum(item.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED for item in handoffs)} research attention / "
            f"{sum(item.human_surface.attention_eligible for item in decisions)} decision wake / "
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
