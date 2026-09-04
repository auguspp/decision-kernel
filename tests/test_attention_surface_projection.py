from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from decision_kernel.odds import ParticipationZone
from decision_kernel.runtime.inbox import (
    render_decision_inbox_html,
    render_decision_inbox_markdown,
)


GENERATED_AT = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)


def _decision(*, attention: bool, ticker: str, company: str, price: str, zone: str):
    scenario_results = (
        SimpleNamespace(
            scenario_id="downside",
            scenario_name="downside",
            probability=Decimal("0.30"),
            total_payoff_per_share=Decimal("60"),
        ),
        SimpleNamespace(
            scenario_id="base",
            scenario_name="base",
            probability=Decimal("0.50"),
            total_payoff_per_share=Decimal("100"),
        ),
        SimpleNamespace(
            scenario_id="upside",
            scenario_name="upside",
            probability=Decimal("0.20"),
            total_payoff_per_share=Decimal("180"),
        ),
    )
    weighted_payoff = sum(
        (
            scenario.probability * scenario.total_payoff_per_share
            for scenario in scenario_results
        ),
        Decimal("0"),
    )
    current_price = Decimal(price)
    positive_probability = sum(
        (
            scenario.probability
            for scenario in scenario_results
            if scenario.total_payoff_per_share > current_price
        ),
        Decimal("0"),
    )
    brief = SimpleNamespace(
        ticker=ticker,
        company_name=company,
        current_price=price,
        currency="CNY",
        as_of=datetime(2026, 9, 3, 15, 0, tzinfo=timezone.utc),
        why_now="new evidence worth Human attention",
        current_belief="current belief stays frozen until evidence changes it",
        market_expectation="market expectation is separate from belief",
        open_questions=("question one",),
        invalidation=("destroyer one",),
        monitoring_triggers=("trigger one",),
        odds=SimpleNamespace(
            participation_zone=SimpleNamespace(value=zone),
            expected_holding_period_return=(weighted_payoff / current_price) - Decimal("1"),
            positive_return_probability=positive_probability,
        ),
        participation_condition=SimpleNamespace(
            threshold_basis_zone=ParticipationZone.ACCEPTABLE_ODDS,
            required_expected_return=Decimal("0.32"),
            required_positive_return_probability=Decimal("0.55"),
        ),
    )
    return SimpleNamespace(
        odds=SimpleNamespace(
            artifact=SimpleNamespace(
                calculation=SimpleNamespace(
                    aggregate=SimpleNamespace(
                        probability_weighted_total_payoff_per_share=weighted_payoff,
                    ),
                    scenario_results=scenario_results,
                ),
            )
        ),
        human_surface=SimpleNamespace(
            attention_eligible=attention,
            investment_authority="NONE",
            brief=brief,
        ),
    )


def test_attention_surface_is_ticker_first_and_detail_is_collapsed() -> None:
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
        price="358.10",
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

    assert "招商银行" in html
    assert "为什么值得看" in html
    assert "Research 已存在" in html
    assert '<summary>深入查看</summary>' in html
    assert html.index("为什么值得看") < html.index("我们相信什么")
    assert html.index("招商银行") < html.index("宁德时代")
    assert "无需关注（1）" in html
    assert '<summary>为什么安静</summary>' in html

    assert "## 招商银行 600036" in markdown
    assert "**为什么值得看**" in markdown
    assert "**当前状态：** Research 已存在" in markdown
    assert "<summary>深入查看</summary>" in markdown
    assert markdown.index("为什么值得看") < markdown.index("我们相信什么")


def test_empty_attention_surface_tells_human_to_close_it() -> None:
    quiet = _decision(
        attention=False,
        ticker="300750",
        company="宁德时代",
        price="358.10",
        zone="INSUFFICIENT_ODDS",
    )

    html = render_decision_inbox_html((quiet,), generated_at=GENERATED_AT)
    markdown = render_decision_inbox_markdown((quiet,), generated_at=GENERATED_AT)

    assert "没有需要你关注的东西" in html
    assert "后台监控继续运行" in html
    assert "今天没有 case 需要人工复核" in markdown
    assert "后台监控继续运行" in markdown
