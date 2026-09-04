from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, localcontext
from html import escape

from ..odds import ODDS_DECIMAL_CONTEXT, ParticipationZone
from ..workflow import DecisionSpineResult


MONEY_QUANTUM = Decimal("0.01")
PERCENT_QUANTUM = Decimal("0.1")


@dataclass(frozen=True)
class QuietOddsContext:
    expected_return: Decimal
    positive_probability: Decimal
    required_return: Decimal
    required_probability: Decimal
    acceptable_price: Decimal
    acceptable_operator: str
    drawdown_to_acceptable: Decimal
    scenarios: tuple[tuple[str, Decimal, Decimal], ...]


def _ordered(decisions: Sequence[DecisionSpineResult]) -> tuple[DecisionSpineResult, ...]:
    return tuple(
        sorted(
            decisions,
            key=lambda item: (
                not item.human_surface.attention_eligible,
                item.human_surface.brief.ticker,
            ),
        )
    )


def _as_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _format_percent(value: object) -> str:
    percent = (_as_decimal(value) * Decimal("100")).quantize(PERCENT_QUANTUM)
    return f"{format(percent, 'f').rstrip('0').rstrip('.')}%"


def _format_money(value: object) -> str:
    return format(_as_decimal(value).quantize(MONEY_QUANTUM), "f")


def _currency_prefix(currency: object) -> str:
    return "¥" if str(currency) == "CNY" else f"{currency} "


def _quiet_odds_context(decision: DecisionSpineResult) -> QuietOddsContext:
    brief = decision.human_surface.brief
    condition = brief.participation_condition
    if condition.threshold_basis_zone is not ParticipationZone.ACCEPTABLE_ODDS:
        raise ValueError("quiet Inbox cases must use ACCEPTABLE_ODDS as the next threshold")

    odds = decision.odds.artifact
    aggregate = odds.calculation.aggregate
    if aggregate is None:
        raise ValueError("quiet Inbox explanation requires calculated Odds")

    required_return = _as_decimal(condition.required_expected_return)
    required_probability = _as_decimal(
        condition.required_positive_return_probability
    )

    with localcontext(ODDS_DECIMAL_CONTEXT):
        expected_return_price = (
            aggregate.probability_weighted_total_payoff_per_share
            / (Decimal("1") + required_return)
        )

        probability_price: Decimal | None = None
        if required_probability > Decimal("0"):
            probability_by_payoff: dict[Decimal, Decimal] = {}
            for scenario in odds.calculation.scenario_results:
                payoff = _as_decimal(scenario.total_payoff_per_share)
                probability_by_payoff[payoff] = probability_by_payoff.get(
                    payoff, Decimal("0")
                ) + _as_decimal(scenario.probability)

            cumulative_probability = Decimal("0")
            for payoff in sorted(probability_by_payoff, reverse=True):
                cumulative_probability += probability_by_payoff[payoff]
                if cumulative_probability >= required_probability:
                    probability_price = payoff
                    break

            if probability_price is None:
                raise ValueError(
                    "positive-return probability threshold is unreachable "
                    "from the frozen scenario distribution"
                )

        if probability_price is None or expected_return_price < probability_price:
            raw_acceptable_price = expected_return_price
            acceptable_operator = "≤"
        else:
            raw_acceptable_price = probability_price
            acceptable_operator = "<"

        acceptable_price = raw_acceptable_price.quantize(
            MONEY_QUANTUM,
            rounding=ROUND_FLOOR,
        )
        current_price = _as_decimal(brief.current_price)
        drawdown_to_acceptable = (raw_acceptable_price / current_price) - Decimal("1")

    scenarios = tuple(
        (
            scenario.scenario_name,
            _as_decimal(scenario.probability),
            _as_decimal(scenario.total_payoff_per_share),
        )
        for scenario in sorted(
            odds.calculation.scenario_results,
            key=lambda item: (item.scenario_name, str(item.scenario_id)),
        )
    )

    return QuietOddsContext(
        expected_return=_as_decimal(brief.odds.expected_holding_period_return),
        positive_probability=_as_decimal(brief.odds.positive_return_probability),
        required_return=required_return,
        required_probability=required_probability,
        acceptable_price=acceptable_price,
        acceptable_operator=acceptable_operator,
        drawdown_to_acceptable=drawdown_to_acceptable,
        scenarios=scenarios,
    )


def _scenario_summary(
    context: QuietOddsContext,
    *,
    currency: object,
) -> str:
    prefix = _currency_prefix(currency)
    return " · ".join(
        f"{name} {_format_percent(probability)} → {prefix}{_format_money(payoff)}"
        for name, probability, payoff in context.scenarios
    )


def render_decision_inbox_markdown(
    decisions: Sequence[DecisionSpineResult],
    *,
    generated_at: datetime,
) -> str:
    ordered = _ordered(decisions)
    attention = tuple(item for item in ordered if item.human_surface.attention_eligible)
    quiet = tuple(item for item in ordered if not item.human_surface.attention_eligible)
    lines = [
        "# Decision Inbox",
        "",
        f"生成时间：{generated_at.isoformat()}",
        "",
        f"**需要关注：{len(attention)}**　·　安静：{len(quiet)}",
        "",
    ]
    if not attention:
        lines.extend(
            [
                "今天没有 case 需要人工复核。",
                "",
                "后台监控继续运行；没有新的 Human attention requirement。",
                "",
            ]
        )

    for decision in attention:
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
                    f"**当前状态：** Research 已存在 · "
                    f"`{brief.odds.participation_zone.value}` · "
                    f"{prefix}{_format_money(brief.current_price)} · "
                    f"行情 {brief.as_of.isoformat()}"
                ),
                "",
                "<details>",
                "<summary>深入查看</summary>",
                "",
                f"系统投资权限：`{surface.investment_authority}`",
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
                "</details>",
                "",
            ]
        )

    if quiet:
        lines.extend(["<details>", f"<summary>无需关注（{len(quiet)}）</summary>", ""])
        for decision in quiet:
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
                    "<details>",
                    "<summary>为什么安静</summary>",
                    "",
                    (
                        "- 当前：期望收益 "
                        f"`{_format_percent(context.expected_return)}` · "
                        "正收益概率 "
                        f"`{_format_percent(context.positive_probability)}`"
                    ),
                    (
                        "- `ACCEPTABLE_ODDS` 要求：期望收益 ≥ "
                        f"`{_format_percent(context.required_return)}` · "
                        "正收益概率 ≥ "
                        f"`{_format_percent(context.required_probability)}`"
                    ),
                    (
                        "- 重新值得看：`ACCEPTABLE_ODDS "
                        f"{context.acceptable_operator} "
                        f"{prefix}{_format_money(context.acceptable_price)}`"
                        "（距当前价约 "
                        f"`{_format_percent(context.drawdown_to_acceptable)}`）"
                    ),
                    (
                        "- Frozen scenarios："
                        f"{_scenario_summary(context, currency=brief.currency)}"
                    ),
                    "",
                    "</details>",
                ]
            )
        lines.extend(["", "</details>", ""])

    lines.extend(["_Research ≠ Recommendation · Investment Authority = NONE_", ""])
    return "\n".join(lines)


def render_decision_inbox_html(
    decisions: Sequence[DecisionSpineResult],
    *,
    generated_at: datetime,
) -> str:
    ordered = _ordered(decisions)
    attention = tuple(item for item in ordered if item.human_surface.attention_eligible)
    quiet = tuple(item for item in ordered if not item.human_surface.attention_eligible)

    def text(value: object) -> str:
        return escape(str(value), quote=True)

    def bullets(items: Sequence[str]) -> str:
        if not items:
            return '<p class="muted">暂无。</p>'
        return "<ul>" + "".join(f"<li>{text(item)}</li>" for item in items) + "</ul>"

    cards: list[str] = []
    for decision in attention:
        surface = decision.human_surface
        brief = surface.brief
        prefix = _currency_prefix(brief.currency)
        cards.append(
            f"""
            <article class="card attention">
              <div class="card-head">
                <div>
                  <p class="eyebrow">需要你看</p>
                  <h2>{text(brief.company_name)} <span>{text(brief.ticker)}</span></h2>
                </div>
                <div class="price">{text(prefix)}{text(_format_money(brief.current_price))}</div>
              </div>

              <section class="why-now">
                <h3>为什么值得看</h3>
                <p>{text(brief.why_now)}</p>
              </section>

              <div class="state-row">
                <span>Research 已存在</span>
                <span>{text(brief.odds.participation_zone.value)}</span>
                <span>{text(brief.as_of.isoformat())}</span>
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
            '<p class="muted">今天没有 case 需要人工复核。后台监控继续运行。</p></article>'
        )

    quiet_rows: list[str] = []
    for decision in quiet:
        brief = decision.human_surface.brief
        context = _quiet_odds_context(decision)
        prefix = _currency_prefix(brief.currency)
        scenario_summary = _scenario_summary(context, currency=brief.currency)
        quiet_rows.append(
            f"""
            <li>
              <div class="quiet-head">
                <strong>{text(brief.company_name)} {text(brief.ticker)}</strong>
                <span>{text(prefix)}{text(_format_money(brief.current_price))} · {text(brief.odds.participation_zone.value)}</span>
              </div>
              <div class="quiet-threshold">
                <b>重新值得看</b>　ACCEPTABLE_ODDS {text(context.acceptable_operator)} {text(prefix)}{text(_format_money(context.acceptable_price))}
                <span>距当前价约 {text(_format_percent(context.drawdown_to_acceptable))}</span>
              </div>
              <details class="quiet-detail">
                <summary>为什么安静</summary>
                <div class="quiet-metrics">
                  <span>当前：期望收益 {text(_format_percent(context.expected_return))} · 正收益概率 {text(_format_percent(context.positive_probability))}</span>
                  <span>ACCEPTABLE_ODDS 要求：期望收益 ≥ {text(_format_percent(context.required_return))} · 正收益概率 ≥ {text(_format_percent(context.required_probability))}</span>
                </div>
                <div class="quiet-scenarios"><b>Frozen scenarios</b>　{text(scenario_summary)}</div>
              </details>
            </li>
            """
        )
    quiet_block = (
        f'<details class="background"><summary>无需关注（{len(quiet)}）</summary>'
        f'<ul class="quiet-list">{"".join(quiet_rows)}</ul></details>'
        if quiet
        else ""
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision Inbox</title>
<style>
:root {{ color-scheme: light dark; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
body {{ margin:0; background:#f5f6f8; color:#16181d; }}
main {{ max-width:720px; margin:0 auto; padding:24px 16px 48px; }}
header {{ margin-bottom:20px; }}
h1 {{ margin:0 0 6px; font-size:30px; }}
.meta,.muted {{ color:#6b7280; }}
.counts {{ font-size:17px; font-weight:650; }}
.card {{ background:#fff; border:1px solid #e5e7eb; border-radius:18px; padding:20px; margin:16px 0; box-shadow:0 3px 14px rgba(0,0,0,.04); }}
.card.attention {{ border-width:2px; }}
.card-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }}
.eyebrow {{ margin:0 0 4px; font-size:13px; font-weight:750; text-transform:uppercase; letter-spacing:.04em; }}
h2 {{ margin:0; font-size:24px; }}
h2 span {{ color:#6b7280; font-size:16px; font-weight:600; }}
.price {{ font-size:25px; font-weight:750; white-space:nowrap; }}
.why-now {{ border-top:0; margin-top:18px; padding-top:0; }}
.state-row {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 2px; }}
.state-row span {{ background:#f0f1f3; border-radius:999px; padding:6px 10px; font-size:12px; }}
section {{ border-top:1px solid #eceef1; padding-top:14px; margin-top:14px; }}
h3 {{ margin:0 0 8px; font-size:15px; }}
p {{ line-height:1.65; margin:0; }}
ul {{ padding-left:20px; line-height:1.65; }}
.authority {{ margin-top:18px; font-size:12px; color:#6b7280; }}
details {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:14px 16px; margin-top:18px; }}
.card .drilldown {{ background:transparent; border-style:dashed; }}
summary {{ cursor:pointer; font-weight:650; }}
.quiet-list {{ list-style:none; padding:0; margin:12px 0 0; }}
.quiet-list li {{ border-top:1px solid #eceef1; padding:14px 0; }}
.quiet-head {{ display:flex; justify-content:space-between; gap:12px; }}
.quiet-head span {{ color:#6b7280; text-align:right; }}
.quiet-threshold {{ margin-top:8px; font-size:14px; line-height:1.5; }}
.quiet-threshold span {{ color:#6b7280; margin-left:8px; }}
.quiet-detail {{ margin-top:10px; padding:10px 12px; }}
.quiet-metrics {{ display:grid; gap:5px; margin-top:9px; font-size:13px; line-height:1.5; }}
.quiet-scenarios {{ margin-top:7px; color:#6b7280; font-size:12px; line-height:1.5; }}
footer {{ margin-top:22px; color:#6b7280; font-size:12px; }}
@media (max-width:560px) {{
  .quiet-head {{ display:block; }}
  .quiet-head span {{ display:block; margin-top:3px; text-align:left; }}
  .quiet-threshold span {{ display:block; margin:3px 0 0; }}
  .card-head {{ align-items:flex-start; }}
}}
@media (prefers-color-scheme: dark) {{
  body {{ background:#0f1115; color:#f3f4f6; }}
  .card,details {{ background:#171a21; border-color:#2a2f39; }}
  section,.quiet-list li {{ border-color:#2a2f39; }}
  .state-row span {{ background:#252a33; }}
  .meta,.muted,h2 span,.authority,.quiet-head span,.quiet-threshold span,.quiet-scenarios,footer {{ color:#9ca3af; }}
}}
</style>
</head>
<body>
<main>
<header>
  <h1>Decision Inbox</h1>
  <p class="meta">生成时间：{text(generated_at.isoformat())}</p>
  <p class="counts">需要关注：{len(attention)}　·　安静：{len(quiet)}</p>
</header>
{''.join(cards)}
{quiet_block}
<footer>Research ≠ Recommendation · Investment Authority = NONE</footer>
</main>
</body>
</html>
"""