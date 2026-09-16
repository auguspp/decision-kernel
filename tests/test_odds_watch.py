from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.market import ObservedMarket
from decision_kernel.runtime import hithink_http, odds_watch


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 16, 16, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
CONFIG = ROOT / "decision_inputs/odds-watch-v0.json"
REGISTRY = ROOT / "current_state/registry.json"


def inputs():
    return json.loads(CONFIG.read_text(encoding="utf-8")), json.loads(REGISTRY.read_text(encoding="utf-8"))


def market(price: str) -> ObservedMarket:
    return ObservedMarket(
        market_price=Decimal(price),
        market_timestamp=datetime(2026, 9, 16, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        market_utc_offset_minutes=480,
        market_data_source="HiThink Financial-API raw daily close | synthetic-test",
        price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
        currency="CNY",
    )


def fetcher(prices: dict[str, str], calls: list[str], *, fail: str | None = None):
    def fetch_market(*, thscode: str, observed_at):
        assert observed_at == NOW
        calls.append(thscode)
        if thscode == fail:
            raise hithink_http.HithinkRuntimeError("synthetic qualified price unavailable")
        return market(prices[thscode])
    return fetch_market


def by_ticker(report):
    return {row["ticker"]: row for row in report["watch"]["active_cases"]}


def test_config_is_bounded_registry_backed_and_has_no_global_approaching_threshold():
    config, registry = inputs()
    odds_watch.validate_config(config, registry)
    assert config["approaching_policy"] == odds_watch.NO_PROXIMITY_POLICY
    assert len(config["active_cases"]) == 5 <= odds_watch.MAX_ACTIVE_CASES
    assert {row["ticker"] for row in config["active_cases"]} == {
        "600276.SH", "002674.SZ", "600598.SH", "002050.SZ", "603986.SH"
    }
    assert {row["ticker"] for row in config["inactive_cases"]} == {
        "600184.SH", "600967.SH", "600519.SH", "601088.SH", "300750.SZ", "600036.SH"
    }
    assert config["authority"] == odds_watch.AUTHORITY
    text = CONFIG.read_text(encoding="utf-8")
    assert "5%" not in text and "10%" not in text and "APPROACHING_REVIEW" not in text


def test_active_boundaries_are_tied_to_exact_retained_human_wording_not_model_thresholds():
    expected = {
        "docs/decisions/600276-hengrui-human-first-entry-2026-09-12.md": (
            "Around CNY39.6", "CNY37–38", "Around CNY35", "CNY32–32.5", "Around CNY29.45"
        ),
        "docs/decisions/002674-xingye-human-research-first-entry-acceptance-2026-09-14.md": (
            "CNY15–17", "CNY13–13.5", "~CNY12-"
        ),
        "docs/decisions/600598-beidahuang-human-odds-acceptance-2026-09-16.md": (
            "CNY11.0–11.3", "CNY9.8–10.3", "CNY9.3–9.6", "~CNY7 AND BELOW"
        ),
        "docs/decisions/002050-sanhua-human-decision-2026-09-03.md": (
            "INITIAL ENTRY CONDITION = around CNY30/share",
        ),
        "docs/decisions/603986-gigadevice-human-decision-2026-09-03.md": (
            "FIRST-ENTRY BAND = CNY320–335/share", "PRE-ENTRY REVIEW TRIGGER = around CNY350/share"
        ),
    }
    for path, phrases in expected.items():
        source = (ROOT / path).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in source, (path, phrase)
    assert "29.56" not in CONFIG.read_text(encoding="utf-8")
    assert "330.69" not in CONFIG.read_text(encoding="utf-8")


def test_above_all_boundaries_reports_factual_next_distance_without_waking_human():
    config, registry = inputs()
    prices = {
        "600276.SH": "42.50", "002674.SZ": "18.00", "600598.SH": "12.33",
        "002050.SZ": "31.00", "603986.SH": "360.00",
    }
    calls: list[str] = []
    report = odds_watch.build_watch(
        config=config, registry=registry, observed_at=NOW,
        fetch_market=fetcher(prices, calls),
    )
    odds_watch.validate_report(report)
    rows = by_ticker(report)
    assert report["watch"]["attention_case_count"] == 0
    assert report["watch"]["price_gap_count"] == 0
    assert all(row["status"] == "ACTIVE_ODDS_WATCH" for row in rows.values())
    assert rows["600276.SH"]["next_unreached_condition"]["upper_price"] == "39.6"
    assert rows["600276.SH"]["next_unreached_condition"]["signed_distance_to_upper_cny"] == "2.90"
    assert rows["603986.SH"]["next_unreached_condition"]["upper_price"] == "350"
    assert calls == ["600276.SH", "002674.SZ", "600598.SH", "002050.SZ", "603986.SH"]
    assert all(row["investment_authority"] == "NONE" and row["action_authority"] == "NONE" for row in rows.values())


def test_crossed_boundaries_wake_review_but_never_create_action_and_keep_next_deeper_boundary():
    config, registry = inputs()
    prices = {
        "600276.SH": "39.00", "002674.SZ": "13.20", "600598.SH": "9.50",
        "002050.SZ": "29.50", "603986.SH": "330.00",
    }
    report = odds_watch.build_watch(
        config=config, registry=registry, observed_at=NOW,
        fetch_market=fetcher(prices, []),
    )
    rows = by_ticker(report)
    assert report["watch"]["attention_case_count"] == 5
    assert all(row["status"] == "NEEDS_REVIEW_NOW" for row in rows.values())

    hengrui = rows["600276.SH"]
    assert [item["kind"] for item in hengrui["triggered_conditions"]] == ["RE_UNDERWRITE"]
    assert hengrui["next_unreached_condition"]["kind"] == "CONDITIONAL_FIRST_ENTRY_REVIEW"

    xingye = rows["002674.SZ"]
    assert [item["kind"] for item in xingye["triggered_conditions"]] == [
        "RE_UNDERWRITE", "CONDITIONAL_FIRST_ENTRY_REVIEW"
    ]
    assert xingye["next_unreached_condition"]["upper_price"] == "12"

    beidahuang = rows["600598.SH"]
    assert [item["kind"] for item in beidahuang["triggered_conditions"]] == [
        "RE_UNDERWRITE", "CONDITIONAL_FIRST_ENTRY_REVIEW", "MATERIALLY_BETTER_ODDS_REVIEW"
    ]
    assert beidahuang["next_unreached_condition"]["upper_price"] == "7"

    assert rows["002050.SZ"]["triggered_conditions"][0]["kind"] == "CONDITIONAL_FIRST_ENTRY_CONDITION"
    assert [item["kind"] for item in rows["603986.SH"]["triggered_conditions"]] == [
        "ASSUMPTION_RECHECK", "CONDITIONAL_FIRST_ENTRY_BAND"
    ]
    summary = odds_watch.render_markdown(report)
    assert "不是 BUY / ADD / SELL" in summary
    assert "Investment Authority = NONE" in summary


def test_price_below_a_range_does_not_silently_lose_the_original_review_condition():
    config, registry = inputs()
    prices = {
        "600276.SH": "36.00", "002674.SZ": "18", "600598.SH": "12.33",
        "002050.SZ": "31", "603986.SH": "360",
    }
    report = odds_watch.build_watch(
        config=config, registry=registry, observed_at=NOW,
        fetch_market=fetcher(prices, []),
    )
    hengrui = by_ticker(report)["600276.SH"]
    first_entry = next(item for item in hengrui["triggered_conditions"] if item["kind"] == "CONDITIONAL_FIRST_ENTRY_REVIEW")
    assert first_entry["condition_state"] == "PASSED_BELOW_RANGE"
    assert first_entry["attention_triggered"] is True


def test_one_provider_gap_is_visible_not_quiet_and_inactive_cases_never_fetch_price():
    config, registry = inputs()
    prices = {
        "600276.SH": "42", "002674.SZ": "18", "600598.SH": "12.33",
        "002050.SZ": "31", "603986.SH": "360",
    }
    calls: list[str] = []
    report = odds_watch.build_watch(
        config=config, registry=registry, observed_at=NOW,
        fetch_market=fetcher(prices, calls, fail="600598.SH"),
    )
    rows = by_ticker(report)
    assert rows["600598.SH"]["status"] == "PRICE_UNAVAILABLE_NOT_QUIET"
    assert rows["600598.SH"]["price"] is None
    assert rows["600598.SH"]["triggered_conditions"] == []
    assert report["watch"]["price_gap_count"] == 1
    assert set(calls) == {"600276.SH", "002674.SZ", "600598.SH", "002050.SZ", "603986.SH"}
    assert not ({row["ticker"] for row in report["watch"]["inactive_cases"]} & set(calls))
    assert all(row["price_fetch_performed"] is False for row in report["watch"]["inactive_cases"])


def test_watch_report_is_sealed_and_roundtrips_without_binary_float_or_authority(tmp_path):
    config, registry = inputs()
    prices = {ticker: "100" for ticker in ("600276.SH", "002674.SZ", "600598.SH", "002050.SZ", "603986.SH")}
    report = odds_watch.build_watch(
        config=config, registry=registry, observed_at=NOW,
        fetch_market=fetcher(prices, []),
    )
    out = tmp_path / "watch"
    odds_watch.write_watch(report=report, output_dir=out)
    loaded = odds_watch.read_and_validate(out / "watch.json")
    assert loaded == report
    assert odds_watch.canonical_hash(report["watch"]) == report["watch_hash"]
    assert "0.0" not in (out / "watch.json").read_text(encoding="utf-8")
    assert report["watch"]["authority"] == odds_watch.AUTHORITY


def test_invalid_registry_use_cannot_activate_a_price_watch():
    config, registry = inputs()
    broken = json.loads(json.dumps(registry))
    target = next(row for row in broken["references"] if row["id"] == "odds-beidahuang-human")
    target["use"] = "RETAINED_ODDS_DOCUMENT"
    with pytest.raises(ValueError, match="Human checkpoint"):
        odds_watch.validate_config(config, broken)
