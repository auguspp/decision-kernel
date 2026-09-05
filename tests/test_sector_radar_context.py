from __future__ import annotations

import copy
import gzip
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_context as surface
from decision_kernel.runtime.sector_radar_events import (
    create_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_state import (
    parse_sector_radar_market_state, serialize_sector_radar_market_state,
)
from test_sector_radar_audit import PRODUCED, execute, prohibit_network, resolution


def test_bootstrap_can_show_existing_strength_without_creating_any_alert(monkeypatch):
    raw = gzip.decompress(Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz").read_bytes())
    state = parse_sector_radar_market_state(raw.decode())
    clock = datetime(2026, 9, 5, 4, tzinfo=timezone.utc)
    ledger = create_sector_radar_candidate_event_ledger(created_at=clock, source="read-only test ledger")
    before = serialize_sector_radar_market_state(state), serialize_sector_radar_candidate_event_ledger(ledger)
    prohibit_network(monkeypatch)
    context = surface.build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=clock)
    assert [item["count"] for item in context["universes"]] == [90, 230]
    assert context["recorded_events_latest_session"] == 0
    assert context["new_alerts_created"] == 0
    assert any(row["currently_gate_active"] for group in context["universes"] for row in group["rows"])
    assert all(row["system_first_observed_at"] is None for group in context["universes"] for row in group["rows"])
    assert before == (serialize_sector_radar_market_state(state), serialize_sector_radar_candidate_event_ledger(ledger))
    assert context == surface.build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=clock)
    page = surface.render_sector_radar_context_html(context)
    assert "零事件不等于零强势行业" in page
    assert "保存数据的只读投影" in page
    assert "<script" not in page and "<iframe" not in page
    assert "行业收益" in page and "基准收益" in page and "超额收益" in page
    assert all(context[field] == "NONE" for field in surface.AUTHORITY)


def test_actual_calculated_events_are_read_without_reappending(tmp_path, monkeypatch):
    outcome, _, _ = execute(tmp_path, jump=True)
    state, ledger = outcome.persistent_bundle.market_state, outcome.persistent_bundle.event_ledger
    prohibit_network(monkeypatch)
    context = surface.build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=PRODUCED)
    assert context["recorded_events_latest_session"] == 2
    assert context["new_alerts_created"] == 0
    rows = [row for group in context["universes"] for row in group["rows"]]
    recorded = [row for row in rows if row["recorded_event_ids_latest_session"]]
    assert len(recorded) == 2
    assert all(row["first_recorded_event_session"] == "2026-09-07" for row in recorded)
    assert len(ledger.events) == 2


def test_source_state_disagreement_is_not_a_new_event(tmp_path):
    outcome, _, _ = execute(tmp_path, jump=True)
    bundle = outcome.persistent_bundle
    # The state remains valid, but its hash cannot be used with a different valid session ledger.
    older_state = resolution().market_state
    with pytest.raises(ValueError, match="ahead"):
        surface.build_sector_radar_context(market_state=older_state,
            event_ledger=bundle.event_ledger, generated_at=PRODUCED)


@pytest.mark.parametrize("naive", [True, False])
def test_invalid_generation_clocks_are_rejected(naive):
    restored = resolution()
    clock = restored.market_state.updated_at - timedelta(days=1)
    if naive:
        clock = clock.replace(tzinfo=None)
    with pytest.raises(ValueError):
        surface.build_sector_radar_context(market_state=restored.market_state,
            event_ledger=restored.event_ledger, generated_at=clock)


def test_left_censored_age_does_not_invent_an_exact_start():
    row = {"positive_20d_excess_persistence_sessions": 100,
           "positive_20d_excess_persistence_left_censored": True,
           "positive_20d_excess_run_started": "2026-01-01"}
    text = surface._age(row, "positive_20d_excess")
    assert "至少 100" in text and "2026-01-01" not in text


def test_view_hash_and_html_escaping():
    restored = resolution()
    payload = surface.build_sector_radar_context(market_state=restored.market_state,
        event_ledger=restored.event_ledger, generated_at=PRODUCED)
    broken = copy.deepcopy(payload)
    broken["new_alerts_created"] = 1
    with pytest.raises(ValueError):
        surface.render_sector_radar_context_html(broken)
    broken = copy.deepcopy(payload)
    broken["universes"][0]["rows"][0]["observation"]["name"] = '<script>alert("x")</script>'
    with pytest.raises(ValueError, match="hash"):
        surface.render_sector_radar_context_html(broken)
    broken["context_hash"] = canonical_hash({key: value for key, value in broken.items() if key != "context_hash"})
    page = surface.render_sector_radar_context_html(broken)
    assert '<script>alert' not in page
    assert '&lt;script&gt;' in page


def test_cli_read_only_report_and_protected_output(tmp_path, monkeypatch):
    _, _, audit_root = execute(tmp_path, jump=True)
    state = audit_root / "expected/state"
    hints = audit_root / "inputs/parent-hints.json"
    before = {path.name: path.read_bytes() for path in state.iterdir()}
    class Clock:
        @staticmethod
        def now(tz=None):
            return PRODUCED + timedelta(days=1)
    monkeypatch.setattr(surface, "datetime", Clock)
    prohibit_network(monkeypatch)
    args = ["--bundle", str(state), "--parent-hints", str(hints)]
    assert surface.main([*args, "--output", str(tmp_path / "context")]) == 0
    assert (tmp_path / "context/index.html").is_file()
    assert json.loads((tmp_path / "context/context.json").read_text())["new_alerts_created"] == 0
    assert before == {path.name: path.read_bytes() for path in state.iterdir()}
    for target in (state, state / "nested", tmp_path):
        with pytest.raises(SystemExit):
            surface.main([*args, "--output", str(target)])
