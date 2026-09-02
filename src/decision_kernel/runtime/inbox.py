from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from html import escape

from ..workflow import DecisionSpineResult


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
        lines.extend(["今天没有 case 需要人工复核。", ""])

    for decision in attention:
        surface = decision.human_surface
        brief = surface.brief
        lines.extend(
            [
                f"## {brief.company_name} {brief.ticker}",
                "",
                f"**当前价格：{brief.current_price} {brief.currency}**  ",
                f"赔率：`{brief.odds.participation_zone.value}`  ",
                f"行情时间：{brief.as_of.isoformat()}  ",
                f"系统投资权限：`{surface.investment_authority}`",
                "",
                f"**为什么现在**  \n{brief.why_now}",
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
            ]
        )

    if quiet:
        lines.extend(["<details>", f"<summary>无需关注（{len(quiet)}）</summary>", ""])
        for decision in quiet:
            brief = decision.human_surface.brief
            lines.append(
                f"- **{brief.company_name} {brief.ticker}** — "
                f"{brief.current_price} {brief.currency} — "
                f"`{brief.odds.participation_zone.value}`"
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
        cards.append(
            f"""
            <article class="card attention">
              <div class="card-head">
                <div>
                  <p class="eyebrow">需要你看</p>
                  <h2>{text(brief.company_name)} <span>{text(brief.ticker)}</span></h2>
                </div>
                <div class="price">¥{text(brief.current_price)}</div>
              </div>
              <div class="chips">
                <span>{text(brief.odds.participation_zone.value)}</span>
                <span>{text(brief.as_of.isoformat())}</span>
              </div>
              <section><h3>为什么现在</h3><p>{text(brief.why_now)}</p></section>
              <section><h3>我们相信什么</h3><p>{text(brief.current_belief)}</p></section>
              <section><h3>市场可能在定价什么</h3><p>{text(brief.market_expectation)}</p></section>
              <section><h3>关键问题</h3>{bullets(brief.open_questions)}</section>
              <section><h3>失效条件</h3>{bullets(brief.invalidation)}</section>
              <section><h3>监控指标</h3>{bullets(brief.monitoring_triggers)}</section>
              <p class="authority">系统投资权限：{text(surface.investment_authority)}</p>
            </article>
            """
        )

    if not cards:
        cards.append(
            '<article class="card empty"><h2>今天没有 case 需要人工复核。</h2>'
            '<p>当前 checked-in research cases 均未跨过 Human wake gate。</p></article>'
        )

    quiet_rows = "".join(
        f"<li><strong>{text(item.human_surface.brief.company_name)} "
        f"{text(item.human_surface.brief.ticker)}</strong>"
        f"<span>¥{text(item.human_surface.brief.current_price)} · "
        f"{text(item.human_surface.brief.odds.participation_zone.value)}</span></li>"
        for item in quiet
    )
    quiet_block = (
        f"<details><summary>无需关注（{len(quiet)}）</summary><ul class=\"quiet-list\">"
        f"{quiet_rows}</ul></details>"
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
main {{ max-width:760px; margin:0 auto; padding:24px 16px 48px; }}
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
.chips {{ display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 20px; }}
.chips span {{ background:#f0f1f3; border-radius:999px; padding:6px 10px; font-size:12px; }}
section {{ border-top:1px solid #eceef1; padding-top:14px; margin-top:14px; }}
h3 {{ margin:0 0 8px; font-size:15px; }}
p {{ line-height:1.65; margin:0; }}
ul {{ padding-left:20px; line-height:1.65; }}
.authority {{ margin-top:18px; font-size:12px; color:#6b7280; }}
details {{ background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:14px 16px; margin-top:18px; }}
summary {{ cursor:pointer; font-weight:650; }}
.quiet-list {{ list-style:none; padding:0; margin:12px 0 0; }}
.quiet-list li {{ display:flex; justify-content:space-between; gap:12px; border-top:1px solid #eceef1; padding:10px 0; }}
.quiet-list span {{ color:#6b7280; text-align:right; }}
footer {{ margin-top:22px; color:#6b7280; font-size:12px; }}
@media (prefers-color-scheme: dark) {{
  body {{ background:#0f1115; color:#f3f4f6; }}
  .card,details {{ background:#171a21; border-color:#2a2f39; }}
  section,.quiet-list li {{ border-color:#2a2f39; }}
  .chips span {{ background:#252a33; }}
  .meta,.muted,h2 span,.authority,.quiet-list span,footer {{ color:#9ca3af; }}
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
