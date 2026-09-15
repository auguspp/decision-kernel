from __future__ import annotations

import json
import socket
from dataclasses import replace
from datetime import datetime, time
from decimal import Decimal

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_historical_study as study
from decision_kernel.runtime import sector_radar_outcomes as outcomes
from decision_kernel.runtime.sector_radar_state import (
    _with_state_hash,
    serialize_sector_radar_market_state,
)
from test_sector_radar_outcomes import TZ, sample as prospective_sample


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("historical outcome study attempted network access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture(scope="module")
def historical_sample(prospective_sample):
    ledger, states, calendar, days = prospective_sample
    return ledger, states[-1], calendar, days


@pytest.fixture(scope="module")
def report(historical_sample):
    state = historical_sample[1]
    return study.build_sector_radar_historical_study(
        state=state,
        generated_at=datetime.combine(state.sessions[-1], time(18), tzinfo=TZ),
    )


def selected_row(report, *, session, code):
    return next(
        item
        for item in report["study"]["rows"]
        if item["signal_session"] == session.isoformat() and item["thscode"] == code
    )


def test_real_detector_reproduces_original_false_to_true_codes(historical_sample, report):
    ledger, state, _, days = historical_sample
    original = serialize_sector_radar_market_state(state)
    event_codes = {event.candidate.thscode for event in ledger.events}
    selected = {
        item["thscode"]
        for item in report["study"]["rows"]
        if item["signal_session"] == days[0].isoformat() and item["radar_selected"]
    }
    assert selected == event_codes == {"881101.TI", "884001.TI"}
    assert serialize_sector_radar_market_state(state) == original
    assert report["study"]["formula_version"] == state.formula_version
    assert report["study"]["radar_policy_version"] == "sector-shadow-state-entry-hierarchy-v0"


def test_contract_is_frozen_and_not_an_investment_backtest(report):
    p = report["study"]
    assert p["horizons"] == [5, 20, 60]
    assert p["baseline_version"] == "positive-20d-excess-top-decile-v0"
    assert p["baseline_semantics"] == study.BASELINE_SEMANTICS
    assert p["historical_universe_identity_qualification"] == study.UNIVERSE_QUALIFICATION
    assert p["price_path_pit_qualification"] == study.PRICE_PATH_QUALIFICATION
    assert p["edge_acceptance"] == study.EDGE_ACCEPTANCE
    assert p["scope"] == "ONE_FROZEN_SECTOR_STATE_WINDOW_ONLY_NO_PROVIDER_CALLS_NO_PORTFOLIO_SIMULATION"
    assert all(
        p[key] == "NONE"
        for key in (
            "signal_transition_authority",
            "research_authority",
            "human_attention_authority",
            "investment_authority",
        )
    )
    assert "sharpe" not in json.dumps(p).lower()


def test_simple_baseline_is_exactly_the_precommitted_rule(report):
    for item in report["study"]["rows"]:
        features = item["signal_features"]
        expected = (
            Decimal(features["horizon_20_excess_return"]) > 0
            and features["horizon_20_rating"] >= 90
        )
        assert item["baseline_selected"] is expected


def test_future_price_change_cannot_change_prior_selection(historical_sample, report):
    _, state, _, days = historical_sample
    anchor = days[0]
    before = {
        item["thscode"]: (
            item["radar_selected"],
            item["baseline_selected"],
            item["radar_event_type"],
        )
        for item in report["study"]["rows"]
        if item["signal_session"] == anchor.isoformat()
    }
    anchor_index = state.sessions.index(anchor)
    future_index = anchor_index + 5
    series = list(state.series)
    target = series[1]
    closes = list(target.closes)
    closes[future_index] *= Decimal("3")
    series[1] = replace(target, closes=tuple(closes))
    changed = _with_state_hash(replace(state, series=tuple(series)))
    changed_report = study.build_sector_radar_historical_study(
        state=changed,
        generated_at=datetime.combine(state.sessions[-1], time(18), tzinfo=TZ),
    )
    after = {
        item["thscode"]: (
            item["radar_selected"],
            item["baseline_selected"],
            item["radar_event_type"],
        )
        for item in changed_report["study"]["rows"]
        if item["signal_session"] == anchor.isoformat()
    }
    assert after == before
    assert selected_row(report, session=anchor, code=target.thscode)["outcomes"]["5"] != selected_row(
        changed_report, session=anchor, code=target.thscode
    )["outcomes"]["5"]


def test_horizons_use_completed_sessions_and_pending_is_not_partial(historical_sample, report):
    state = historical_sample[1]
    for item in report["study"]["rows"]:
        signal_index = state.sessions.index(datetime.fromisoformat(item["signal_session"]).date())
        for horizon in study.HORIZONS:
            outcome = item["outcomes"][str(horizon)]
            due = signal_index + horizon < len(state.sessions)
            assert outcome["status"] == (outcomes.EVALUATED if due else outcomes.PENDING)
            assert (outcome["metrics"] is not None) is due
            if due:
                assert outcome["target_session"] == state.sessions[signal_index + horizon].isoformat()
            else:
                assert outcome["target_session"] is None


def test_t60_and_legacy_t5_t20_share_the_same_metric_contract():
    flat = [Decimal(100)] * 61
    trend = [Decimal(100 + i) for i in range(61)]
    metrics = study._historical_path_metrics(trend, flat)
    assert metrics["sector_return"] == Decimal("0.6")
    assert metrics["close_path_mfe"] == Decimal("0.6")
    assert metrics["close_path_mae"] == 0
    for length in (6, 21):
        sector = [Decimal(100 + i) for i in range(length)]
        benchmark = [Decimal(100)] * length
        assert study._historical_path_metrics(sector, benchmark) == outcomes._path_metrics(
            sector, benchmark
        )
    assert outcomes.HORIZONS == (5, 20)


def test_summary_retains_overlap_and_outcome_sign_proxies(report):
    p = report["study"]
    for family in ("BROAD_881", "GRANULAR_884"):
        for horizon in ("5", "20", "60"):
            summary = p["summary"][family][horizon]
            assert summary["proxy_semantics"] == study.PROXY_SEMANTICS
            assert summary["radar_false_positive_proxy_count"] >= 0
            assert summary["radar_false_negative_proxy_count"] >= 0
            assert summary["radar_baseline_overlap_count"] >= 0
            assert summary["cohort_overlap_note"] == "RADAR_AND_BASELINE_COHORTS_MAY_OVERLAP_NOT_INDEPENDENT_SAMPLES"


def test_study_hash_is_independent_of_report_clock(historical_sample, report):
    state = historical_sample[1]
    later = study.build_sector_radar_historical_study(
        state=state,
        generated_at=datetime.combine(state.sessions[-1], time(23), tzinfo=TZ),
    )
    assert report["study"] == later["study"]
    assert report["study_hash"] == later["study_hash"] == canonical_hash(report["study"])
    assert report["generated_at"] != later["generated_at"]


def test_full_window_and_post_close_boundary_are_required(historical_sample):
    state = historical_sample[1]
    shortened = _with_state_hash(
        replace(
            state,
            sessions=state.sessions[1:],
            series=tuple(
                replace(item, closes=item.closes[1:], turnovers=item.turnovers[1:])
                for item in state.series
            ),
        )
    )
    with pytest.raises(ValueError, match="full rolling"):
        study.build_sector_radar_historical_study(
            state=shortened,
            generated_at=datetime.combine(state.sessions[-1], time(18), tzinfo=TZ),
        )
    with pytest.raises(ValueError, match="final close"):
        study.build_sector_radar_historical_study(
            state=state,
            generated_at=datetime.combine(state.sessions[-1], time(14), tzinfo=TZ),
        )


def test_markdown_discloses_identity_limit_and_rejects_authority(report):
    text = study.render_sector_radar_historical_study_markdown(report)
    assert "**not** a trading backtest" in text
    assert study.UNIVERSE_QUALIFICATION in text
    assert study.EDGE_ACCEPTANCE in text
    altered = json.loads(json.dumps(report))
    altered["study"]["investment_authority"] = "BUY"
    altered["study_hash"] = canonical_hash(altered["study"])
    with pytest.raises(ValueError, match="forbidden authority"):
        study.render_sector_radar_historical_study_markdown(altered)


def test_cli_reads_one_frozen_state_and_writes_separate_artifact(historical_sample, tmp_path):
    state = historical_sample[1]
    state_path = tmp_path / "state.json"
    state_path.write_text(serialize_sector_radar_market_state(state), encoding="utf-8")
    output = tmp_path / "study"
    clock = datetime.combine(state.sessions[-1], time(18), tzinfo=TZ).isoformat()
    assert study.main([
        "--state", str(state_path), "--generated-at", clock, "--output", str(output)
    ]) == 0
    saved = json.loads((output / "study.json").read_text(encoding="utf-8"))
    assert saved["study_hash"] == canonical_hash(saved["study"])
    assert (output / "summary.md").is_file()
    with pytest.raises(ValueError, match="must not already exist"):
        study.main([
            "--state", str(state_path), "--generated-at", clock, "--output", str(output)
        ])
