from __future__ import annotations

import copy
import json
import socket
from dataclasses import replace
from datetime import datetime, time, timedelta
from decimal import Decimal, localcontext
from io import StringIO
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION, HithinkQualifiedIndexSnapshotBatch,
    normalize_hithink_index_snapshot, normalize_hithink_industry_catalog,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_outcomes as outcome
from decision_kernel.runtime.sector_radar_events import (
    _with_event_hash, _with_ledger_hash, create_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_state import (
    _with_state_hash, append_qualified_sector_snapshot, serialize_sector_radar_market_state,
)
from test_sector_radar_audit import (
    TZ, MONDAY, SESSIONS, execute, resolution, catalog_envelope, ms,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("objective evaluator attempted network access")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    # Existing end-to-end fixture: actual adapters, ranks, gates, composition and
    # event creation; HTTP-shaped synthetic inputs only. No preselected candidates.
    result, _, _ = execute(tmp_path_factory.mktemp("synthetic-origin"))
    first = result.persistent_bundle.market_state
    ledger = result.persistent_bundle.event_ledger
    assert {e.candidate.thscode for e in ledger.events} == {"881101.TI", "884001.TI"}
    days = [MONDAY]
    day = MONDAY
    while len(days) < 26:
        day += timedelta(days=1)
        if day.weekday() < 5:
            days.append(day)
    calendar = (*SESSIONS, *days)  # Explicit synthetic calendar, not exchange truth.
    catalog = normalize_hithink_industry_catalog(catalog_envelope())
    origins = {s.thscode: s.closes[-1] for s in first.series}
    states = [first]
    changes = {1: "1.01", 2: "0.90", 3: "1.20", 4: "0.95", 5: "1.05", 20: "1.12", 21: "2.0"}
    for offset, day in enumerate(days[1:], 1):
        prior = states[-1]
        rows = []
        for s in prior.series:
            factor = (Decimal(changes.get(offset, "1.10")) if s.thscode in {"881101.TI", "884001.TI"}
                      else Decimal(1) + Decimal(offset) / Decimal(500))
            last, previous = origins[s.thscode] * factor, s.closes[-1]
            rows.append({
                "thscode": s.thscode, "ticker": "1B0300" if s.thscode == "000300.SH" else s.thscode[:6],
                "last_price": str(last), "prev_price": str(previous), "price_change": str(last - previous),
                "price_change_ratio_pct": str((last / previous - 1) * 100),
                "open_price": str(previous), "high_price": str(max(last, previous) + 1),
                "low_price": str(min(last, previous) - 1), "volume": "100", "turnover": str(s.turnovers[-1] + 1),
            })
        normalized = normalize_hithink_index_snapshot(
            {"code": 0, "data": {"timestamp": ms(day), "total": len(rows), "item": rows}},
            requested_thscodes=tuple(s.thscode for s in prior.series),
        )
        snapshot = HithinkQualifiedIndexSnapshotBatch(
            market_session=day, benchmark_thscode=prior.benchmark_thscode,
            provider_timestamp_ms=ms(day), qualification_method=HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
            points=normalized.points,
        )
        states.append(append_qualified_sector_snapshot(
            state=prior, catalog=catalog, snapshot=snapshot,
            observed_at=datetime.combine(day, time(16), tzinfo=TZ),
        ).state)
    return ledger, tuple(states), calendar, tuple(days)


def assess(sample, n=20, *, states=None, ledger=None, calendar=None, generated_at=None):
    original_ledger, original_states, original_calendar, days = sample
    return outcome.evaluate_sector_radar_outcomes(
        ledger=ledger or original_ledger, states=states if states is not None else original_states[:n + 1],
        trading_sessions=calendar if calendar is not None else original_calendar,
        as_of_session=days[n], generated_at=generated_at or datetime.combine(days[n], time(18), tzinfo=TZ),
    )


def selected(report, code="881101.TI", horizon=5):
    return next(r for r in report["evaluation"]["rows"] if r["thscode"] == code and r["horizon_sessions"] == horizon)


def test_actual_frozen_candidate_creation_to_mature_objective_outcomes(sample):
    ledger, states, _, days = sample
    originals = [serialize_sector_radar_market_state(s) for s in states]
    ledger_bytes = serialize_sector_radar_candidate_event_ledger(ledger)
    report = assess(sample)
    p = report["evaluation"]
    assert p["status_counts"] == {"EVALUATED": 4, "PENDING_HORIZON": 0, "INPUTS_INCOMPLETE": 0}
    assert p["event_count"] == 2 and p["horizon_assessment_count"] == 4
    assert len({r["first_group_hash"] for r in p["rows"]}) == 1
    for code in ("881101.TI", "884001.TI"):
        for horizon in (5, 20):
            row = selected(report, code, horizon)
            data = row["outcome"]
            m = data["metrics"]
            assert row["target_session"] == days[horizon].isoformat()
            assert len(data["path"]) == horizon + 1
            assert m["sector_return"] == ("0.05" if horizon == 5 else "0.12")
            assert Decimal(m["benchmark_return"]) == Decimal(horizon) / Decimal(500)
            assert Decimal(m["excess_return"]) == Decimal(m["sector_return"]) - Decimal(m["benchmark_return"])
            assert Decimal(m["close_path_mfe"]) == Decimal("0.20")
            assert Decimal(m["close_path_mae"]) == Decimal("-0.10")
            assert all(d["family_universe_size"] == 2 for d in data["path"])
            assert Decimal(m["rank_20d_change"]) == Decimal(data["path"][0]["rank_20d"]) - Decimal(data["path"][-1]["rank_20d"])
            flags = [d["original_gate_active"] for d in data["path"][1:]]
            prefix = next((i for i, active in enumerate(flags) if not active), horizon)
            assert m["original_gate_continuation_days"] == prefix
            without_hash = {k: v for k, v in data.items() if k != "outcome_hash"}
            assert data["outcome_hash"] == canonical_hash(without_hash)
    assert serialize_sector_radar_candidate_event_ledger(ledger) == ledger_bytes
    assert [serialize_sector_radar_market_state(s) for s in states] == originals


@pytest.mark.parametrize("elapsed", [0, 4, 5, 19, 20])
def test_horizons_use_sessions_and_never_partial_horizon_metrics(sample, elapsed):
    report = assess(sample, elapsed)
    for row in report["evaluation"]["rows"]:
        ready = elapsed >= row["horizon_sessions"]
        assert row["status"] == (outcome.EVALUATED if ready else outcome.PENDING)
        assert (row["outcome"] is not None) is ready
    if elapsed == 4:
        assert selected(report)["target_session"] == sample[3][5].isoformat()
        assert (sample[3][5] - MONDAY).days == 7  # five sessions, not five weekdays of prose


def test_calendar_need_not_expose_future_sessions_for_pending(sample):
    calendar = tuple(d for d in sample[2] if d <= MONDAY)
    report = assess(sample, 0, calendar=calendar)
    assert all(r["status"] == outcome.PENDING and r["target_session"] is None for r in report["evaluation"]["rows"])


@pytest.mark.parametrize("missing", [0, 1, 5, 10, 20])
def test_missing_daily_state_is_explicit_even_if_later_window_contains_its_prices(sample, missing):
    # Keep a later as-of state so missing maturity is not mistaken for not due.
    states = tuple(s for i, s in enumerate(sample[1][:22]) if i != missing)
    report = assess(sample, 21, states=states)
    for row in report["evaluation"]["rows"]:
        if missing <= row["horizon_sessions"]:
            assert row["status"] == outcome.INCOMPLETE and row["outcome"] is None
            assert row["missing_state_sessions"] == [sample[3][missing].isoformat()]
        else:
            assert row["status"] == outcome.EVALUATED


def test_mature_outcome_is_stable_under_later_states_new_clock_and_duplicate_input(sample):
    first = assess(sample, 20)
    second = assess(sample, 25)
    third = assess(sample, 20, states=(*sample[1][:21], sample[1][0]))
    for row in first["evaluation"]["rows"]:
        assert row["outcome"] == selected(second, row["thscode"], row["horizon_sessions"])["outcome"]
    assert first["evaluation"] == third["evaluation"]
    later_clock = assess(sample, 20, generated_at=datetime.combine(sample[3][25], time(18), tzinfo=TZ))
    assert first["evaluation_hash"] == later_clock["evaluation_hash"]


def test_ambient_decimal_context_cannot_change_a_frozen_outcome(sample):
    baseline = assess(sample, 5)
    with localcontext() as ctx:
        ctx.prec = 7
        assert assess(sample, 5) == baseline


@pytest.mark.parametrize("kind", ["close", "turnover", "catalog", "source"])
def test_rehashed_changed_market_history_or_lineage_rejected(sample, kind):
    states = list(sample[1][:6])
    last = states[-1]
    if kind in ("close", "turnover"):
        first = last.series[0]
        field = "closes" if kind == "close" else "turnovers"
        values = list(getattr(first, field)); values[-2] += 1
        changed = replace(first, **{field: tuple(values)})
        last = replace(last, series=(changed, *last.series[1:]))
    elif kind == "catalog":
        last = replace(last, catalog_hash="f" * 64)
    else:
        last = replace(last, source="different history")
    states[-1] = _with_state_hash(last)
    with pytest.raises(ValueError, match="changed|lineage|catalog"):
        assess(sample, 5, states=states)


def test_rehashed_candidate_must_reproduce_from_the_exact_origin(sample):
    event = sample[0].events[0]
    changed = replace(event.candidate, horizon_20_rank=Decimal(999))
    bad_event = _with_event_hash(replace(event, candidate=changed, candidate_hash=canonical_hash(changed.__dict__)))
    bad_ledger = _with_ledger_hash(replace(sample[0], events=(bad_event, *sample[0].events[1:])))
    with pytest.raises(ValueError, match="does not reproduce"):
        assess(sample, ledger=bad_ledger)


def test_event_origin_hash_is_not_silently_replaced(sample):
    event = _with_event_hash(replace(sample[0].events[0], source_market_state_hash="f" * 64))
    ledger = _with_ledger_hash(replace(sample[0], events=(event, *sample[0].events[1:])))
    with pytest.raises(ValueError, match="identity disagree"):
        assess(sample, ledger=ledger)


@pytest.mark.parametrize("kind", ["duplicate-calendar", "missing-calendar-day", "future-state", "conflict", "no-asof"])
def test_time_and_calendar_errors_are_not_returns(sample, kind):
    states, calendar = list(sample[1][:6]), sample[2]
    if kind == "duplicate-calendar": calendar = (*calendar, calendar[-1])
    elif kind == "missing-calendar-day": calendar = tuple(d for d in calendar if d != sample[3][2])
    elif kind == "future-state": states.append(sample[1][6])
    elif kind == "conflict": states.append(_with_state_hash(replace(states[-1], updated_at=states[-1].updated_at + timedelta(seconds=1))))
    else: states = states[:-1]
    with pytest.raises(ValueError):
        assess(sample, 5, states=states, calendar=calendar)


def test_before_close_and_future_recording_fail(sample):
    for clock in (datetime.combine(MONDAY, time(14), tzinfo=TZ), datetime.combine(MONDAY, time(16), tzinfo=TZ)):
        with pytest.raises(ValueError): assess(sample, 0, generated_at=clock)
    with pytest.raises(ValueError): assess(sample, 0, generated_at=datetime(2026, 9, 7, 18))


def test_empty_ledger_is_not_zero_performance(sample):
    empty = create_sector_radar_candidate_event_ledger(created_at=sample[0].created_at, source="SYNTHETIC_TEST_ONLY")
    report = assess(sample, 0, ledger=empty)
    assert report["evaluation"]["rows"] == []
    assert report["evaluation"]["event_count"] == 0
    assert "尚无账本候选可评估" in outcome.render_sector_radar_outcomes(report)


def test_close_path_extrema_include_anchor_and_reject_invalid_prices():
    flat = [Decimal(100)] * 6
    up = [Decimal(100 + i) for i in range(6)]
    down = list(reversed(up))
    assert outcome._path_metrics(up, flat)["close_path_mae"] == 0
    assert outcome._path_metrics(down, flat)["close_path_mfe"] == 0
    for broken in ([Decimal(100)] * 5, [Decimal("NaN")] * 6, [Decimal(0)] * 6, [100.0] * 6):
        with pytest.raises(ValueError): outcome._path_metrics(broken, flat)


def test_html_is_readonly_and_has_no_human_annotation_in_objective_hash(sample):
    report = assess(sample, 5)
    page = BeautifulSoup(outcome.render_sector_radar_outcomes(report), "html.parser")
    assert not page.select("script, form, input, iframe, img, link")
    assert len(page.select("article")) == 4
    assert "非判断质量评分" in page.get_text()
    assert "尚未到期" in page.get_text()
    altered = copy.deepcopy(report)
    altered["evaluation"]["investment_authority"] = "BUY"
    altered["evaluation_hash"] = canonical_hash(altered["evaluation"])
    with pytest.raises(ValueError): outcome.render_sector_radar_outcomes(altered)


def test_cli_reuses_saved_inputs_writes_separate_report_and_preserves_every_input(sample, tmp_path, monkeypatch):
    source = tmp_path / "source"; source.mkdir()
    ledger_path = source / "ledger.json"
    ledger_path.write_text(serialize_sector_radar_candidate_event_ledger(sample[0]), encoding="utf-8")
    cal = source / "calendar.json"
    cal.write_text(json.dumps({"code": 0, "data": {"item": [{"date": d.strftime("%Y%m%d")} for d in sample[2]]}}), encoding="utf-8")
    args = ["--ledger", str(ledger_path), "--calendar", str(cal), "--as-of", sample[3][5].isoformat()]
    for i, state in enumerate(sample[1][:6]):
        p = source / f"state-{i}.json"
        p.write_text(serialize_sector_radar_market_state(state), encoding="utf-8")
        args += ["--state", str(p)]
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.combine(sample[3][25], time(18), tzinfo=TZ)
    monkeypatch.setattr(outcome, "datetime", Clock)
    out = tmp_path / "report"
    assert outcome.main([*args, "--output", str(out)], stdout=StringIO()) == 0
    saved = json.loads((out / "outcomes.json").read_text(encoding="utf-8"))
    assert saved["evaluation"]["status_counts"][outcome.EVALUATED] == 2
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    assert outcome.main([*args, "--output", str(out)], stderr=StringIO()) == 2
    assert (out / "index.html").is_file()
