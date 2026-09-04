from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace

from decision_kernel.cli import main
from decision_kernel.market import ObservedMarket
from decision_kernel.odds import ParticipationZone
from decision_kernel.runtime import hithink_http
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
    scenarios: tuple[tuple[str, str, str], ...] | None = None,
    required_return: str = "0.32",
    required_probability: str = "0.55",
):
    scenario_values = scenarios or (
        ("downside", "0.30", "60"),
        ("base", "0.50", "100"),
        ("upside", "0.20", "180"),
    )
    price_decimal = Decimal(price)
    scenario_results = tuple(
        SimpleNamespace(
            scenario_id=f"scenario-{index}",
            scenario_name=name,
            probability=Decimal(probability),
            total_payoff_per_share=Decimal(payoff),
        )
        for index, (name, probability, payoff) in enumerate(scenario_values)
    )
    weighted_payoff = sum(
        (
            scenario.probability * scenario.total_payoff_per_share
            for scenario in scenario_results
        ),
        Decimal("0"),
    )
    expected_return = (weighted_payoff / price_decimal) - Decimal("1")
    positive_probability = sum(
        (
            scenario.probability
            for scenario in scenario_results
            if scenario.total_payoff_per_share > price_decimal
        ),
        Decimal("0"),
    )
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
            expected_holding_period_return=expected_return,
            positive_return_probability=positive_probability,
        ),
        participation_condition=SimpleNamespace(
            threshold_basis_zone=ParticipationZone.ACCEPTABLE_ODDS,
            required_expected_return=Decimal(required_return),
            required_positive_return_probability=Decimal(required_probability),
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
    assert "为什么值得看" in html
    assert "无需关注（1）" in html
    assert html.index("招商银行") < html.index("宁德时代")
    assert "为什么安静" in html
    assert "重新值得看" in html
    assert "ACCEPTABLE_ODDS ≤ ¥78.78" in html
    assert "**需要关注：1**" in markdown
    assert "## 招商银行 600036" in markdown
    assert "<summary>无需关注（1）</summary>" in markdown
    assert "`ACCEPTABLE_ODDS ≤ ¥78.78`" in markdown
    assert "Investment Authority = NONE" in html


def test_quiet_threshold_preserves_strict_positive_probability_boundary() -> None:
    quiet = _decision(
        attention=False,
        ticker="600000",
        company="严格边界样例",
        price="350",
        zone="INSUFFICIENT_ODDS",
        scenarios=(
            ("downside", "0.30", "200"),
            ("base", "0.30", "300"),
            ("upside", "0.40", "500"),
        ),
        required_return="0.10",
        required_probability="0.55",
    )

    html = render_decision_inbox_html((quiet,), generated_at=GENERATED_AT)
    markdown = render_decision_inbox_markdown((quiet,), generated_at=GENERATED_AT)

    assert "ACCEPTABLE_ODDS &lt; ¥300.00" in html
    assert "`ACCEPTABLE_ODDS < ¥300.00`" in markdown


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


def test_build_inbox_cli_uses_real_checked_in_research_package(
    tmp_path,
    monkeypatch,
) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc)

    def fake_market(*, thscode: str, observed_at, api_key: str | None):
        assert thscode == "600036.SH"
        assert api_key == "fixture-secret"
        return ObservedMarket(
            market_price="40.86",
            market_timestamp=datetime(
                2026,
                9,
                1,
                15,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            ),
            market_utc_offset_minutes=480,
            market_data_source="HiThink fixture",
            price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
            currency="CNY",
        )

    output = tmp_path / "index.html"
    summary = tmp_path / "summary.md"
    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "fixture-secret")
    monkeypatch.setattr("decision_kernel.cli.datetime", FrozenDateTime)
    monkeypatch.setattr(
        hithink_http,
        "fetch_latest_hithink_observed_market",
        fake_market,
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "build-inbox",
            "dogfood/600036-cmb.json",
            "--output",
            str(output),
            "--summary",
            str(summary),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "1 attention / 1 total" in stdout.getvalue()
    assert "招商银行" in output.read_text(encoding="utf-8")
    assert "ACCEPTABLE_ODDS" in output.read_text(encoding="utf-8")
    assert "## 招商银行 600036" in summary.read_text(encoding="utf-8")


def test_gigadevice_quiet_inbox_explains_reentry_threshold(
    tmp_path,
    monkeypatch,
) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 2, 8, 30, tzinfo=timezone.utc)

    def fake_market(*, thscode: str, observed_at, api_key: str | None):
        assert thscode == "603986.SH"
        assert api_key == "fixture-secret"
        return ObservedMarket(
            market_price="388.86",
            market_timestamp=datetime(
                2026,
                9,
                2,
                15,
                0,
                tzinfo=timezone(timedelta(hours=8)),
            ),
            market_utc_offset_minutes=480,
            market_data_source="HiThink fixture",
            price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
            currency="CNY",
        )

    output = tmp_path / "index.html"
    summary = tmp_path / "summary.md"
    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "fixture-secret")
    monkeypatch.setattr("decision_kernel.cli.datetime", FrozenDateTime)
    monkeypatch.setattr(
        hithink_http,
        "fetch_latest_hithink_observed_market",
        fake_market,
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "build-inbox",
            "research_cases/603986-gigadevice-deep-research-v1.json",
            "--output",
            str(output),
            "--summary",
            str(summary),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    html = output.read_text(encoding="utf-8")
    markdown = summary.read_text(encoding="utf-8")

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "0 attention / 1 total" in stdout.getvalue()
    assert "兆易创新" in html
    assert "为什么安静" in html
    assert "期望收益 -9.7%" in html
    assert "正收益概率 20%" in html
    assert "ACCEPTABLE_ODDS ≤ ¥266.10" in html
    assert "距当前价约 -31.6%" in html
    assert "`ACCEPTABLE_ODDS ≤ ¥266.10`" in markdown
    assert "Research ≠ Recommendation · Investment Authority = NONE" in html
