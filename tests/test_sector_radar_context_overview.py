"""P0-2 read views over the existing saved context; no new market state or signal."""
from __future__ import annotations

import copy

from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import sector_radar_context as surface
from test_sector_radar_audit import PRODUCED, prohibit_network, resolution


def _payload(monkeypatch):
    restored = resolution()
    prohibit_network(monkeypatch)
    return surface.build_sector_radar_context(
        market_state=restored.market_state,
        event_ledger=restored.event_ledger,
        generated_at=PRODUCED,
    )


def _seal(payload):
    payload["context_hash"] = canonical_hash(
        {key: value for key, value in payload.items() if key != "context_hash"}
    )
    return payload


def _section(soup, family):
    found = soup.select(f'section[data-family="{family}"]')
    assert len(found) == 1
    return found[0]


def _details(section, prefix):
    matches = [item for item in section.find_all("details", recursive=False)
               if item.find("summary", recursive=False).get_text(" ", strip=True).startswith(prefix)]
    assert len(matches) == 1
    return matches[0]


def _row_for_link(details, code):
    link = details.find("a", href=f"#{code}")
    assert link is not None
    return link.find_parent("tr")


def test_zero_new_events_does_not_hide_ongoing_saved_market_state(monkeypatch):
    payload = _payload(monkeypatch)
    for universe in payload["universes"]:
        for item in universe["rows"]:
            item["recorded_event_ids_latest_session"] = []
    payload["recorded_events_latest_session"] = 0
    item = payload["universes"][0]["rows"][0]
    item["gates"] = {
        "persistent": {"previous": True, "current": True},
        "acceleration": {"previous": False, "current": False},
    }
    item["currently_gate_active"] = True
    item["gate_exited_since_previous_session"] = False
    _seal(payload)

    page = surface.render_sector_radar_context_html(payload)
    section = _section(BeautifulSoup(page, "html.parser"), "BROAD_881")
    assert "零新事件不等于市场没有持续状态" in page
    assert "NEW · 本交易日账本 sector event 0 个" in section.get_text(" ", strip=True)
    assert item["observation"]["thscode"] in _details(section, "ONGOING").get_text(" ", strip=True)
    assert payload["new_alerts_created"] == 0


def test_60_day_browser_is_complete_rank_sorted_and_does_not_require_current_gate(monkeypatch):
    payload = _payload(monkeypatch)
    rows = payload["universes"][0]["rows"]
    # Presentation-only fixture: make the reverse code order the exact saved 60d rank.
    ranked = list(reversed(rows))
    for rank, item in enumerate(ranked, 1):
        item["observation"]["horizon_60"]["cross_sectional_rank"] = str(rank)
    target = ranked[0]
    target["currently_gate_active"] = False
    target["recent_weakening"] = False
    target["gate_exited_since_previous_session"] = False
    target["recorded_event_ids_latest_session"] = []
    target["gates"] = {
        "persistent": {"previous": False, "current": False},
        "acceleration": {"previous": False, "current": False},
    }
    _seal(payload)

    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    section = _section(soup, "BROAD_881")
    window = section.select_one('details.window-view[data-horizon="60"]')
    table_rows = window.select("tbody tr")
    assert len(table_rows) == len(rows)
    assert [int(row.select("td")[0].get_text(strip=True)) for row in table_rows] == list(range(1, len(rows) + 1))
    first = table_rows[0].get_text(" ", strip=True)
    assert target["observation"]["thscode"] in first
    assert "NO CURRENT GATE" in first
    assert target["observation"]["thscode"] not in _details(section, "ONGOING").get_text(" ", strip=True)


def test_active_and_recent_weakening_remain_overlapping_read_views(monkeypatch):
    payload = _payload(monkeypatch)
    item = payload["universes"][1]["rows"][0]
    item["gates"] = {
        "persistent": {"previous": True, "current": True},
        "acceleration": {"previous": False, "current": False},
    }
    item["currently_gate_active"] = True
    item["recent_weakening"] = True
    item["gate_exited_since_previous_session"] = False
    _seal(payload)

    section = _section(BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser"), "GRANULAR_884")
    code = item["observation"]["thscode"]
    assert _details(section, "ONGOING").find("a", href=f"#{code}") is not None
    weakening = _details(section, "WEAKENING / EXIT")
    assert weakening.find("a", href=f"#{code}") is not None
    assert "ONGOING · WEAKENING" in weakening.get_text(" ", strip=True)


def test_one_gate_can_exit_while_another_remains_active(monkeypatch):
    payload = _payload(monkeypatch)
    item = payload["universes"][0]["rows"][0]
    item["gates"] = {
        "persistent": {"previous": True, "current": True},
        "acceleration": {"previous": True, "current": False},
    }
    item["currently_gate_active"] = True
    item["recent_weakening"] = False
    item["gate_exited_since_previous_session"] = True
    _seal(payload)

    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    article = soup.find("article", id=item["observation"]["thscode"])
    text = article.get_text(" ", strip=True)
    assert "ONGOING · EXIT: acceleration" in text
    assert "persistent ✓→✓" in text
    assert "acceleration ✓→× EXIT" in text
    assert "全部条件退出" not in text


def test_negative_absolute_return_with_positive_excess_is_relative_resilience(monkeypatch):
    payload = _payload(monkeypatch)
    item = payload["universes"][0]["rows"][0]
    observed = item["observation"]["horizon_5"]
    observed.update(sector_return="-0.020", benchmark_return="-0.030", excess_return="0.010")
    _seal(payload)

    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    section = _section(soup, "BROAD_881")
    window = section.select_one('details.window-view[data-horizon="5"]')
    row = _row_for_link(window, item["observation"]["thscode"])
    text = row.get_text(" ", strip=True)
    assert "下跌但相对抗跌" in text
    assert "上涨且跑赢基准" not in text


def test_left_censor_and_missing_ledger_event_do_not_invent_dates(monkeypatch):
    payload = _payload(monkeypatch)
    item = payload["universes"][0]["rows"][0]
    row = item["observation"]
    row["positive_20d_excess_persistence_sessions"] = 100
    row["positive_20d_excess_persistence_left_censored"] = True
    row["positive_20d_excess_run_started"] = "1999-01-01"
    item["first_recorded_event_session"] = None
    item["system_first_observed_at"] = None
    _seal(payload)

    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    article = soup.find("article", id=row["thscode"])
    text = article.get_text(" ", strip=True)
    assert "至少 100 个交易日；真实起点早于可计算窗口" in text
    assert "1999-01-01" not in text
    assert "账本未记录；不能据此推断首次发现或首次观察日期" in text
    assert "系统首次观察时间：未记录" in text


def test_window_ranks_stay_separate_by_881_and_884_and_counts_do_not_inflate(monkeypatch):
    payload = _payload(monkeypatch)
    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    windows = soup.select('details.window-view[data-horizon="60"]')
    assert len(windows) == 2
    for universe, window in zip(payload["universes"], windows, strict=True):
        assert len(window.select("tbody tr")) == universe["count"]
        assert {link.get("href")[1:] for link in window.select('a[href^="#"]')} == {
            item["observation"]["thscode"] for item in universe["rows"]
        }
    assert "各视图可重叠，计数不能相加成独立机会数" in soup.get_text(" ", strip=True)
    assert "窗口排名只在本层内部排序" in soup.get_text(" ", strip=True)


def test_renderer_is_deterministic_keeps_context_contract_and_marks_missing_breadth(monkeypatch):
    payload = _payload(monkeypatch)
    before = copy.deepcopy(payload)
    first = surface.render_sector_radar_context_html(payload)
    second = surface.render_sector_radar_context_html(payload)
    assert first == second
    assert payload == before
    assert "overview" not in payload and "window_views" not in payload
    assert "Breadth / leaders：本 context 未获取，也不复用旧交易日宽度" in first
    assert f"状态交易日：<strong>{payload['market_session']}</strong>" in first
    assert str(payload["generated_at"]) in first
    assert payload["market_state_hash"] in first
    assert payload["event_ledger_hash"] in first
    assert payload["context_hash"] in first
    assert "原因、业务关系和持续性结论没有证据时保持未知" in first
