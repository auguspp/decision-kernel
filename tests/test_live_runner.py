from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink import HithinkAdapterError, to_hithink_thscode
from decision_kernel.cli import main
from decision_kernel.live import run_live_deep_research_package
from decision_kernel.market import ObservedMarket
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.runtime import hithink_http
from decision_kernel.runtime.hithink_http import HithinkRuntimeError
from decision_kernel.workflow import DecisionSpineTerminalState
from test_deep_research import AS_OF, _package


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _fake_market(price: str):
    def fetch_market(*, thscode: str, observed_at):
        assert thscode == "600000.SH"
        return ObservedMarket(
            market_price=price,
            market_timestamp=AS_OF + timedelta(hours=2),
            market_utc_offset_minutes=480,
            market_data_source="HiThink fixture completed close",
            price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
            currency="CNY",
        )

    return fetch_market


def _runtime_market(price: str):
    inner = _fake_market(price)

    def fetch_market(*, thscode: str, observed_at, api_key: str | None):
        if not api_key:
            raise HithinkRuntimeError("HiThink credentials are required for live market data")
        return inner(thscode=thscode, observed_at=observed_at)

    return fetch_market


def _sessions() -> tuple[date, ...]:
    return (
        date(2026, 8, 24),
        date(2026, 8, 25),
        date(2026, 8, 26),
        date(2026, 8, 27),
        date(2026, 8, 28),
    )


def _date_ms(value: date) -> int:
    return int(datetime.combine(value, time(), tzinfo=SHANGHAI).timestamp() * 1000)


def _calendar_envelope(sessions: tuple[date, ...]) -> dict:
    return {
        "code": 0,
        "data": {
            "item": [{"date": session.strftime("%Y%m%d")} for session in sessions]
        },
    }


def _history_envelope(sessions: tuple[date, ...]) -> dict:
    return {
        "code": 0,
        "data": {
            "adjust": "none",
            "interval": "1d",
            "thscode": "600000.SH",
            "timestamp": _date_ms(sessions[-1]),
            "item": [
                {
                    "date_ms": _date_ms(session),
                    "close_price": str(Decimal("10") + Decimal(index)),
                    "volume": "100",
                    "turnover": "1000",
                }
                for index, session in enumerate(sessions)
            ],
        },
    }


def test_live_odds_policy_is_the_preserved_decision_os_v0_1_contract() -> None:
    policy = load_live_odds_v0_1()

    assert policy.policy_version == "decision-os-live-odds-v0.1"
    assert policy.minimum_holding_period_days == 180
    assert policy.maximum_holding_period_days == 730
    assert str(policy.acceptable_min_expected_return) == "0.20"
    assert str(policy.attractive_min_expected_return) == "0.35"
    assert str(policy.exceptional_min_expected_return) == "0.55"
    assert str(policy.medium_model_risk_addon) == "0.03"


def test_research_identity_maps_to_hithink_without_provider_registry() -> None:
    assert to_hithink_thscode(ticker="600000", exchange="SSE") == "600000.SH"
    assert to_hithink_thscode(ticker="000001", exchange="SZSE") == "000001.SZ"
    assert to_hithink_thscode(ticker="430047", exchange="BSE") == "430047.BJ"

    with pytest.raises(HithinkAdapterError, match="suffix disagrees"):
        to_hithink_thscode(ticker="600000.SZ", exchange="SSE")
    with pytest.raises(HithinkAdapterError, match="SSE, SZSE, or BSE"):
        to_hithink_thscode(ticker="600000", exchange="NYSE")


def test_runtime_fetches_only_calendar_and_raw_history() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)
    calls: list[tuple[str, dict[str, str]]] = []

    def request_json(path: str, params):
        calls.append((path, dict(params)))
        if path == "/api/a-share/calendar/trading-days":
            return _calendar_envelope(sessions)
        if path == "/api/a-share/prices/historical":
            return _history_envelope(sessions)
        raise AssertionError(path)

    market = hithink_http.fetch_latest_hithink_observed_market(
        thscode="600000.SH",
        observed_at=observed_at,
        api_key="fixture-secret",
        request_json=request_json,
    )

    assert market.market_price == Decimal("14")
    assert market.market_timestamp.date() == sessions[-1]
    assert [path for path, _ in calls] == [
        "/api/a-share/calendar/trading-days",
        "/api/a-share/prices/historical",
    ]
    assert calls[1][1]["adjust"] == "none"


def test_runtime_rejects_missing_credentials_and_stale_live_price() -> None:
    sessions = _sessions()
    observed_at = datetime.combine(sessions[-1], time(16), tzinfo=SHANGHAI)

    with pytest.raises(HithinkRuntimeError, match="credentials"):
        hithink_http.fetch_latest_hithink_observed_market(
            thscode="600000.SH",
            observed_at=observed_at,
            api_key=None,
            request_json=lambda path, params: {},
        )

    def stale_request(path: str, params):
        if path == "/api/a-share/calendar/trading-days":
            return _calendar_envelope(sessions)
        return _history_envelope(sessions[:-1])

    with pytest.raises(HithinkRuntimeError, match="latest completed"):
        hithink_http.fetch_latest_hithink_observed_market(
            thscode="600000.SH",
            observed_at=observed_at,
            api_key="fixture-secret",
            request_json=stale_request,
        )


def test_live_runner_routes_same_research_to_quiet_or_human_from_price() -> None:
    package = _package()
    observed_at = AS_OF + timedelta(hours=3)

    quiet = run_live_deep_research_package(
        package=package,
        observed_at=observed_at,
        fetch_market=_fake_market("10"),
    )
    wake = run_live_deep_research_package(
        package=package,
        observed_at=observed_at,
        fetch_market=_fake_market("8"),
    )

    assert quiet.decision.terminal_state is DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS
    assert quiet.decision.human_surface.attention_eligible is False
    assert wake.decision.terminal_state is DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    assert wake.decision.human_surface.attention_eligible is True
    assert quiet.investment_authority == "NONE"
    assert wake.investment_authority == "NONE"


def test_cli_prints_human_summary_without_internal_artifact_dump(
    tmp_path,
    monkeypatch,
) -> None:
    package_path = tmp_path / "package.json"
    package_path.write_text(_package().model_dump_json(indent=2), encoding="utf-8")
    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "fixture-secret")
    monkeypatch.setattr(
        hithink_http,
        "fetch_latest_hithink_observed_market",
        _runtime_market("8"),
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
    monkeypatch.delenv(hithink_http.HITHINK_API_KEY_ENV, raising=False)
    monkeypatch.setattr(
        hithink_http,
        "fetch_latest_hithink_observed_market",
        _runtime_market("8"),
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
