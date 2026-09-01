from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest

import decision_kernel.live as live_module
from decision_kernel.adapters.hithink import (
    HITHINK_API_KEY_ENV,
    HithinkAdapterError,
    to_hithink_thscode,
)
from decision_kernel.cli import main
from decision_kernel.market import ObservedMarket
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.workflow import DecisionSpineTerminalState
from test_deep_research import AS_OF, _package


def _fake_market(price: str):
    def fetch_market(*, thscode: str, observed_at, api_key: str | None):
        if not api_key:
            raise HithinkAdapterError("HiThink credentials are required for ObservedMarket")
        assert thscode == "600000.SH"
        return ObservedMarket(
            market_price=price,
            market_timestamp=AS_OF + timedelta(hours=2),
            market_utc_offset_minutes=480,
            market_data_source="HiThink fixture completed close",
            price_convention="RAW_UNADJUSTED_LATEST_COMPLETED_A_SHARE_CLOSE",
            currency="CNY",
        )

    return fetch_market


def test_live_odds_policy_is_the_preserved_decision_os_v0_1_contract() -> None:
    policy = load_live_odds_v0_1()

    assert policy.policy_version == "decision-os-live-odds-v0.1"
    assert policy.minimum_holding_period_days == 180
    assert policy.maximum_holding_period_days == 730
    assert str(policy.acceptable_min_expected_return) == "0.20"
    assert str(policy.attractive_min_expected_return) == "0.35"
    assert str(policy.exceptional_min_expected_return) == "0.55"
    assert str(policy.medium_model_risk_addon) == "0.03"


def test_research_identity_maps_to_hithink_without_a_provider_registry() -> None:
    assert to_hithink_thscode(ticker="600000", exchange="SSE") == "600000.SH"
    assert to_hithink_thscode(ticker="000001", exchange="SZSE") == "000001.SZ"
    assert to_hithink_thscode(ticker="430047", exchange="BSE") == "430047.BJ"
    assert to_hithink_thscode(ticker="600000.SH", exchange="SSE") == "600000.SH"

    with pytest.raises(HithinkAdapterError, match="suffix disagrees"):
        to_hithink_thscode(ticker="600000.SZ", exchange="SSE")
    with pytest.raises(HithinkAdapterError, match="SSE, SZSE, or BSE"):
        to_hithink_thscode(ticker="600000", exchange="NYSE")


def test_live_runner_routes_same_research_to_quiet_or_human_from_live_price() -> None:
    package = _package()
    observed_at = AS_OF + timedelta(hours=3)

    quiet = live_module.run_live_deep_research_package(
        package=package,
        api_key="fixture-secret",
        observed_at=observed_at,
        fetch_market=_fake_market("10"),
    )
    wake = live_module.run_live_deep_research_package(
        package=package,
        api_key="fixture-secret",
        observed_at=observed_at,
        fetch_market=_fake_market("8"),
    )

    assert quiet.decision.terminal_state is DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS
    assert quiet.decision.human_surface.attention_eligible is False
    assert wake.decision.terminal_state is DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    assert wake.decision.human_surface.attention_eligible is True
    assert quiet.research_commit.research_snapshot.information_bundle_hash == (
        wake.research_commit.research_snapshot.information_bundle_hash
    )
    assert quiet.investment_authority == "NONE"
    assert wake.investment_authority == "NONE"


def test_cli_run_prints_human_summary_without_dumping_internal_artifacts(
    tmp_path,
    monkeypatch,
) -> None:
    package_path = tmp_path / "package.json"
    package_path.write_text(_package().model_dump_json(indent=2), encoding="utf-8")
    monkeypatch.setenv(HITHINK_API_KEY_ENV, "fixture-secret")
    monkeypatch.setattr(
        live_module,
        "fetch_hithink_observed_market",
        _fake_market("8"),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        ["run", str(package_path)],
        stdout=stdout,
        stderr=stderr,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "STATE: HUMAN_ATTENTION_REQUIRED" in output
    assert "SECURITY: 600000 Sample Co" in output
    assert "HUMAN ATTENTION: YES" in output
    assert "INVESTMENT AUTHORITY: NONE" in output
    assert "CURRENT BELIEF:" in output
    assert "OPEN QUESTIONS:" in output
    assert "artifact_hash" not in output
    assert "information_bundle_hash" not in output


def test_cli_missing_hithink_credentials_fails_visibly_without_network(
    tmp_path,
    monkeypatch,
) -> None:
    package_path = tmp_path / "package.json"
    package_path.write_text(_package().model_dump_json(), encoding="utf-8")
    monkeypatch.delenv(HITHINK_API_KEY_ENV, raising=False)
    monkeypatch.setattr(
        live_module,
        "fetch_hithink_observed_market",
        _fake_market("8"),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        ["run", str(package_path)],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "credentials are required" in stderr.getvalue()
