from datetime import datetime, timezone
from types import SimpleNamespace

from decision_kernel.runtime.inbox import (
    render_decision_inbox_html,
    render_decision_inbox_markdown,
)


GENERATED_AT = datetime(2026, 9, 2, 8, 20, tzinfo=timezone.utc)


def _decision(
    *,
    attention: bool,
    ticker: str,
    company: str,
    price: str,
    zone: str,
):
    brief = SimpleNamespace(
        ticker=ticker,
        company_name=company,
        current_price=price,
        currency="CNY",
        as_of=datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc),
        why_now="why now",
        current_belief="current belief",
        market_expectation="market expectation",
        open_questions=("question one",),
        invalidation=("destroyer one",),
        monitoring_triggers=("trigger one",),
        odds=SimpleNamespace(
            participation_zone=SimpleNamespace(value=zone),
        ),
    )
    return SimpleNamespace(
        human_surface=SimpleNamespace(
            attention_eligible=attention,
            investment_authority="NONE",
            brief=brief,
        )
    )


def test_inbox_uses_existing_human_gate_and_collapses_quiet_cases() -> None:
    attention = _decision(
        attention=True,
        ticker="600036",
        company="招商银行",
        price="40.86",
        zone="ACCEPTABLE_ODDS",
    )
    quiet = _decision(
        attention=False,
        ticker="300750",
        company="宁德时代",
        price="358.1",
        zone="INSUFFICIENT_ODDS",
    )

    html = render_decision_inbox_html(
        (quiet, attention),
        generated_at=GENERATED_AT,
    )
    markdown = render_decision_inbox_markdown(
        (quiet, attention),
        generated_at=GENERATED_AT,
    )

    assert "需要关注：1" in html
    assert "招商银行" in html
    assert "为什么现在" in html
    assert "无需关注（1）" in html
    assert html.index("招商银行") < html.index("宁德时代")
    assert "**需要关注：1**" in markdown
    assert "## 招商银行 600036" in markdown
    assert "<summary>无需关注（1）</summary>" in markdown
    assert "Investment Authority = NONE" in html


def test_inbox_escapes_research_text_and_does_not_invent_attention() -> None:
    quiet = _decision(
        attention=False,
        ticker="600000",
        company="<script>alert(1)</script>",
        price="10",
        zone="INSUFFICIENT_ODDS",
    )

    html = render_decision_inbox_html((quiet,), generated_at=GENERATED_AT)

    assert "今天没有 case 需要人工复核" in html
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "需要关注：0" in html
