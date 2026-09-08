"""Read-path contracts, including average ties from the unchanged calculator.

Synthetic presentation fixtures are not live state or natural schedule evidence.
"""
import copy
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from decision_kernel.runtime import sector_radar_context as surface
from decision_kernel.runtime.sector_radar import _cross_section
from test_sector_radar_context_overview import _payload, _seal


@pytest.mark.parametrize("horizon", [5, 20, 60])
def test_average_tied_ranks_remain_exact_and_use_code_only_to_break_ties(monkeypatch, horizon):
    payload = _payload(monkeypatch)
    rows = payload["universes"][0]["rows"]
    codes = sorted(item["observation"]["thscode"] for item in rows)
    ranks = _cross_section({code: Decimal(1) if i < 2 else Decimal(-i)
                            for i, code in enumerate(codes)}).rank_by_thscode
    assert ranks[codes[0]] == ranks[codes[1]] == Decimal("1.5")
    for item in rows:
        item["observation"][f"horizon_{horizon}"]["cross_sectional_rank"] = str(ranks[item["observation"]["thscode"]])
    rows.reverse()
    _seal(payload)
    before = copy.deepcopy(payload)
    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    body = soup.select_one(f'section[data-family="BROAD_881"] details[data-horizon="{horizon}"] tbody')
    assert [a["href"][1:] for a in body.select("a")] == codes
    assert [tr.select_one("td").text for tr in body.select("tr")[:2]] == ["1.5", "1.5"]
    assert payload == before


def test_header_links_to_every_complete_view_and_detail_ids_are_unique(monkeypatch):
    payload = _payload(monkeypatch)
    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    nav = soup.select_one("header nav#read-nav")
    assert nav is not None
    assert len(nav.select("a")) == 12
    for universe in payload["universes"]:
        family = universe["family"]
        for suffix in ("new", "ongoing", "weakening", "window-5", "window-20", "window-60"):
            identifier = family + "-" + suffix
            assert nav.find("a", href="#" + identifier) is not None
            target = soup.find(id=identifier)
            assert target.find_parent("section")["data-family"] == family
            assert target.find_parent("details") is not None
            if suffix.startswith("window-"):
                assert len(target.select("tbody tr")) == universe["count"]
    identifiers = [node["id"] for node in soup.select("[id]")]
    assert len(identifiers) == len(set(identifiers))
    assert len(soup.select("article")) == sum(u["count"] for u in payload["universes"])
    for article in soup.select("article"):
        assert article.find("a", href="#read-nav") is not None
    assert soup.find("a", href="context.json") is not None


def test_overlapping_overview_counts_are_counts_of_saved_objects(monkeypatch):
    payload = _payload(monkeypatch)
    soup = BeautifulSoup(surface.render_sector_radar_context_html(payload), "html.parser")
    summary_rows = soup.select("header table tbody tr")
    for universe, tr in zip(payload["universes"], summary_rows, strict=True):
        rows = universe["rows"]
        expected = [len(rows), sum(len(i["recorded_event_ids_latest_session"]) for i in rows),
                    sum(i["currently_gate_active"] for i in rows), sum(i["recent_weakening"] for i in rows),
                    sum(i["gate_exited_since_previous_session"] for i in rows),
                    sum(i["currently_gate_active"] and (i["recent_weakening"] or i["gate_exited_since_previous_session"]) for i in rows)]
        assert [int(td.text) for td in tr.select("td")[1:]] == expected


def test_unprovided_breadth_or_cause_cannot_be_filled_by_extra_source_fields(monkeypatch):
    payload = _payload(monkeypatch)
    item = payload["universes"][0]["rows"][0]
    item["breadth"] = {"market_session": "1999-01-01", "leader": "OLD_OR_WRONG_IDENTITY_CANARY"}
    item["why"] = "UNVERIFIED_CAUSE_CANARY"
    _seal(payload)
    page = surface.render_sector_radar_context_html(payload)
    assert "OLD_OR_WRONG_IDENTITY_CANARY" not in page
    assert "UNVERIFIED_CAUSE_CANARY" not in page
    assert "本 context 未获取，也不复用旧交易日宽度" in page
    assert "NOT ESTABLISHED" in page


def test_navigation_source_text_cannot_create_remote_or_script_links(monkeypatch):
    payload = _payload(monkeypatch)
    payload["universes"][0]["rows"][0]["observation"]["name"] = '<img src="https://invalid.example/leak"><script>BAD</script>'
    _seal(payload)
    page = surface.render_sector_radar_context_html(payload)
    soup = BeautifulSoup(page, "html.parser")
    assert not soup.select("script, img, iframe, link")
    assert "&lt;script&gt;" in page
    assert all(a["href"].startswith("#") or a["href"] == "context.json" for a in soup.select("a"))


def test_generation_time_does_not_upgrade_old_market_session(monkeypatch):
    payload = _payload(monkeypatch)
    market_session = payload["market_session"]
    payload["generated_at"] = "2030-01-02T00:00:00Z"
    payload["calendar_days_since_market_session"] = 1000
    _seal(payload)
    page = surface.render_sector_radar_context_html(payload)
    assert f"状态交易日：<strong>{market_session}</strong>" in page
    assert payload["generated_at"] in page
    assert "本页不重新资格化完成交易日" in page
    assert "不是缺失交易日数" in page
    assert "20日滚动超额连续为正" in page
