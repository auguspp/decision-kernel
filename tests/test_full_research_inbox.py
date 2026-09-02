from datetime import datetime, timedelta, timezone
from io import StringIO

from decision_kernel.cli import main
from decision_kernel.market import ObservedMarket
from decision_kernel.runtime import hithink_http


def test_build_inbox_mixes_generic_and_full_research_packages(
    tmp_path,
    monkeypatch,
) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 2, 8, 20, tzinfo=timezone.utc)

    prices = {
        "600036.SH": "40.86",
        "603986.SH": "400",
    }

    def fake_market(*, thscode: str, observed_at, api_key: str | None):
        assert api_key == "fixture-secret"
        return ObservedMarket(
            market_price=prices[thscode],
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
            "dogfood/600036-cmb.json",
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
    assert "1 attention / 2 total" in stdout.getvalue()
    assert "招商银行" in html
    assert "兆易创新" in html
    assert html.index("招商银行") < html.index("兆易创新")
    assert "## 招商银行 600036" in markdown
    assert "兆易创新 603986" in markdown
