from __future__ import annotations

import argparse
import html
import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json


CONTEXT_SEMANTICS = "READ_ONLY_SAVED_MARKET_CONTEXT_NOT_A_NEW_ALERT_OR_RESEARCH_ROUTE"
AUTHORITY = {"signal_transition_authority": "NONE", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE"}
SHANGHAI = ZoneInfo("Asia/Shanghai")


def build_sector_radar_context(*, market_state, event_ledger, generated_at: datetime) -> dict[str, Any]:
    """Project a strictly validated saved state; never append or suppress an event.

    The two existing gate predicates are explanatory fields only. A reconstructed
    transition in bootstrap history is not promoted into a prospective event.
    """
    from .sector_radar_events import serialize_sector_radar_candidate_event_ledger
    from .sector_radar_state import calculate_sector_radar_state_snapshot_pair
    from .sector_radar_shadow import (
        SECTOR_RADAR_SHADOW_POLICY_VERSION, _acceleration_gate, _persistent_gate,
        select_sector_radar_state_entries,
    )

    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("context generation clock must be timezone-aware")
    if generated_at < market_state.updated_at or generated_at < event_ledger.updated_at:
        raise ValueError("context generation precedes saved inputs")
    serialize_sector_radar_candidate_event_ledger(event_ledger)
    pair = calculate_sector_radar_state_snapshot_pair(market_state)
    if any(event.candidate.as_of_session > pair.current_session for event in event_ledger.events):
        raise ValueError("event ledger is ahead of the displayed market state")

    compatible_events = tuple(event for event in event_ledger.events if (
        event.formula_version == market_state.formula_version
        and event.policy_version == SECTOR_RADAR_SHADOW_POLICY_VERSION
        and event.benchmark_thscode == market_state.benchmark_thscode
        and event.catalog_hash == market_state.catalog_hash
    ))
    latest_events = tuple(event for event in event_ledger.events
                          if event.candidate.as_of_session == pair.current_session)
    if any(event not in compatible_events or event.source_market_state_hash != market_state.state_hash
           for event in latest_events):
        raise ValueError("latest-session event lineage disagrees with the displayed state")

    universes = []
    for family, previous, current in (
        ("BROAD_881", pair.broad_previous, pair.broad_current),
        ("GRANULAR_884", pair.granular_previous, pair.granular_current),
    ):
        prior = {row.thscode: row for row in previous.observations}
        entries = select_sector_radar_state_entries(current=current, previous=previous)
        candidates = {item.thscode: item for item in entries.candidates}
        for event in latest_events:
            if event.candidate.family == family and candidates.get(event.candidate.thscode) != event.candidate:
                raise ValueError("recorded event differs from market-derived transition")
        rows = []
        for current_row in sorted(current.observations, key=lambda row: row.thscode):
            before = prior[current_row.thscode]
            gates = {
                name: {"previous": predicate(before), "current": predicate(current_row)}
                for name, predicate in (("persistent", _persistent_gate), ("acceleration", _acceleration_gate))
            }
            matching = [event for event in compatible_events
                        if event.candidate.family == family and event.candidate.thscode == current_row.thscode]
            observed = current_row.horizon_20
            absolute = observed.sector_return
            relative = observed.excess_return
            path_description = (
                "上涨且跑赢基准" if absolute > 0 and relative > 0 else
                "未上涨但相对抗跌" if absolute <= 0 and relative > 0 else
                "上涨但未跑赢基准" if absolute > 0 else "未上涨且未跑赢基准"
            )
            rows.append({
                "observation": asdict(current_row),
                "gates": gates,
                "currently_gate_active": any(gate["current"] for gate in gates.values()),
                "gate_exited_since_previous_session": any(gate["previous"] and not gate["current"] for gate in gates.values()),
                "recent_weakening": current_row.rank_change_5_sessions_20d < 0 and current_row.excess_acceleration_5_sessions_20d < 0,
                "path_description": path_description,
                "first_recorded_event_session": min((event.candidate.as_of_session for event in matching), default=None),
                "system_first_observed_at": None,
                "recorded_event_ids_latest_session": [event.event_id for event in matching if event.candidate.as_of_session == pair.current_session],
                "breadth_status": "NOT_IN_THIS_MARKET_CONTEXT_USE_SAME_SESSION_RUN_ARTIFACT",
            })
        universes.append({"family": family, "count": len(rows), "rows": rows})

    payload = {
        "schema_version": 1, "semantics": CONTEXT_SEMANTICS,
        "generated_at": generated_at, "market_session": pair.current_session,
        "previous_session": pair.previous_session,
        "calendar_days_since_market_session": (generated_at.astimezone(SHANGHAI).date() - pair.current_session).days,
        "freshness": "SAVED_STATE_ONLY_LATEST_COMPLETED_SESSION_NOT_REVALIDATED",
        "market_state_hash": market_state.state_hash, "event_ledger_hash": event_ledger.ledger_hash,
        "catalog_hash": market_state.catalog_hash, "formula_version": market_state.formula_version,
        "policy_version": SECTOR_RADAR_SHADOW_POLICY_VERSION,
        "benchmark_thscode": market_state.benchmark_thscode,
        "recorded_events_latest_session": len(latest_events), "new_alerts_created": 0,
        "universes": universes, **AUTHORITY,
    }
    payload["context_hash"] = canonical_hash(payload)
    return json.loads(canonical_json(payload))


def _validate_context(payload: dict[str, Any]) -> None:
    if payload.get("semantics") != CONTEXT_SEMANTICS or payload.get("schema_version") != 1:
        raise ValueError("unsupported context projection")
    if any(payload.get(key) != value for key, value in AUTHORITY.items()):
        raise ValueError("context cannot carry authority")
    if payload.get("new_alerts_created") != 0:
        raise ValueError("context cannot create alerts")
    claimed = payload.get("context_hash")
    if canonical_hash({key: value for key, value in payload.items() if key != "context_hash"}) != claimed:
        raise ValueError("context hash mismatch")
    if [item["family"] for item in payload["universes"]] != ["BROAD_881", "GRANULAR_884"]:
        raise ValueError("context universes must remain separate")


def _percent(value: str) -> str:
    return f"{Decimal(value) * 100:+.2f}%"


def _age(row: dict[str, Any], prefix: str) -> str:
    count = row[f"{prefix}_persistence_sessions"]
    if not count:
        return "无连续区间"
    if row[f"{prefix}_persistence_left_censored"]:
        return f"至少 {count} 个交易日；真实起点早于可计算窗口"
    start_key = "positive_20d_excess_run_started" if prefix == "positive_20d_excess" else "top_quartile_20d_run_started"
    return f"{count} 个交易日，自 {row[start_key]}"


def _window_path(observation: dict[str, Any]) -> str:
    absolute = Decimal(observation["sector_return"])
    relative = Decimal(observation["excess_return"])
    if absolute > 0 and relative > 0:
        return "上涨且跑赢基准"
    if absolute < 0 and relative > 0:
        return "下跌但相对抗跌"
    if absolute == 0 and relative > 0:
        return "持平但相对跑赢"
    if absolute > 0:
        return "上涨但未跑赢基准"
    if absolute < 0:
        return "下跌且未跑赢基准"
    return "持平且未跑赢基准"


def _state_markers(item: dict[str, Any]) -> tuple[str, ...]:
    markers = []
    if item["recorded_event_ids_latest_session"]:
        markers.append("NEW")
    if item["currently_gate_active"]:
        markers.append("ONGOING")
    if item["recent_weakening"]:
        markers.append("WEAKENING")
    exits = [name for name in ("persistent", "acceleration")
             if item["gates"][name]["previous"] and not item["gates"][name]["current"]]
    if exits:
        markers.append("EXIT: " + ", ".join(exits))
    return tuple(markers) if markers else ("NO CURRENT GATE",)


def _window_order(rows: list[dict[str, Any]], horizon: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda item: (
        int(item["observation"][f"horizon_{horizon}"]["cross_sectional_rank"]),
        item["observation"]["thscode"],
    ))


def render_sector_radar_context_html(payload: dict[str, Any]) -> str:
    """Render one read-only overview: state views, window ranks, then detail."""
    _validate_context(payload)
    esc = lambda value: html.escape(str(value), quote=True)

    def item_link(item: dict[str, Any]) -> str:
        row = item["observation"]
        return (f'<a href="#{esc(row["thscode"])}">{esc(row["name"])} '
                f'<small>{esc(row["thscode"])}</small></a>')

    def marker_text(item: dict[str, Any]) -> str:
        return " · ".join(_state_markers(item))

    def gate_text(item: dict[str, Any]) -> str:
        parts = []
        for name in ("persistent", "acceleration"):
            gate = item["gates"][name]
            transition = f'{"✓" if gate["previous"] else "×"}→{"✓" if gate["current"] else "×"}'
            if gate["previous"] and not gate["current"]:
                transition += " EXIT"
            parts.append(f"{name} {transition}")
        return "；".join(parts)

    def compact_table(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "<p>无匹配项；这不等于市场没有其他状态。</p>"
        body = []
        for item in rows:
            observed = item["observation"]["horizon_20"]
            body.append(
                "<tr>"
                f"<td>{item_link(item)}</td><td>{esc(marker_text(item))}</td>"
                f"<td>{esc(gate_text(item))}</td><td>{esc(_window_path(observed))}</td>"
                f"<td>{esc(_percent(observed['sector_return']))}</td>"
                f"<td>{esc(_percent(observed['excess_return']))}</td>"
                f"<td>{esc(observed['cross_sectional_rank'])}</td></tr>"
            )
        return (
            '<div class="scroll"><table class="compact"><thead><tr>'
            '<th>行业</th><th>阅读状态</th><th>条件前后</th><th>20日路径</th>'
            '<th>20日收益</th><th>20日超额</th><th>层内排名</th></tr></thead><tbody>'
            + "".join(body) + '</tbody></table></div>'
        )

    def window_table(rows: list[dict[str, Any]], horizon: int) -> str:
        body = []
        for item in _window_order(rows, horizon):
            observed = item["observation"][f"horizon_{horizon}"]
            body.append(
                "<tr>"
                f"<td>{esc(observed['cross_sectional_rank'])}</td><td>{item_link(item)}</td>"
                f"<td>{esc(_percent(observed['sector_return']))}</td>"
                f"<td>{esc(_percent(observed['benchmark_return']))}</td>"
                f"<td>{esc(_percent(observed['excess_return']))}</td>"
                f"<td>{esc(_window_path(observed))}</td>"
                f"<td>{esc(marker_text(item))}</td></tr>"
            )
        return (
            '<div class="scroll"><table class="compact window"><thead><tr>'
            '<th>排名</th><th>行业</th><th>行业收益</th><th>基准收益</th><th>超额</th>'
            '<th>绝对/相对描述</th><th>状态注记</th></tr></thead><tbody>'
            + "".join(body) + '</tbody></table></div>'
        )

    def cards(rows: list[dict[str, Any]]) -> str:
        output = []
        for item in rows:
            row = item["observation"]
            values = []
            for horizon in (5, 20, 60):
                observed = row[f"horizon_{horizon}"]
                values.append(
                    "<tr>"
                    f"<td>{horizon}日</td><td>{esc(_percent(observed['sector_return']))}</td>"
                    f"<td>{esc(_percent(observed['benchmark_return']))}</td>"
                    f"<td>{esc(_percent(observed['excess_return']))}</td>"
                    f"<td>{esc(_window_path(observed))}</td>"
                    f"<td>{esc(observed['cross_sectional_rank'])}</td>"
                    f"<td>{esc(observed['cross_sectional_rating'])}</td></tr>"
                )
            event_session = (item["first_recorded_event_session"]
                             or "账本未记录；不能据此推断首次发现或首次观察日期")
            pulse = row["turnover_pulse_5_vs_prior_20"]
            pulse_text = "不可用" if pulse is None else f"{Decimal(pulse):.2f}×"
            output.append(
                f'<article id="{esc(row["thscode"])}">'
                f'<h3>{esc(row["name"])} <small>{esc(row["thscode"])}</small></h3>'
                f'<p><strong>{esc(marker_text(item))}</strong></p>'
                f'<p>条件：{esc(gate_text(item))}。ONGOING 与 WEAKENING 可以同时成立；'
                'EXIT 只指具体 predicate 从 true→false。</p>'
                '<div class="scroll"><table><thead><tr><th>窗口</th><th>行业收益</th>'
                '<th>基准收益</th><th>超额收益</th><th>绝对/相对描述</th>'
                '<th>层内排名</th><th>层内rating</th></tr></thead><tbody>'
                + "".join(values) + '</tbody></table></div>'
                f'<p>正超额年龄：{esc(_age(row, "positive_20d_excess"))}<br>'
                f'前四分位年龄：{esc(_age(row, "top_quartile_20d"))}<br>'
                f'5日内20日排名变化：{esc(row["rank_change_5_sessions_20d"])}；'
                f'超额加速度：{esc(_percent(row["excess_acceleration_5_sessions_20d"]))}；'
                f'成交额脉冲：{esc(pulse_text)}</p>'
                f'<p>账本中首次前瞻事件：{esc(event_session)}<br>'
                '系统首次观察时间：未记录，不以趋势起点、首次事件或页面生成时间代替。</p>'
                '<p class="muted">Breadth / leaders：本 context 未获取，也不复用旧交易日宽度。'
                '原因、公司业务关系与持续性结论：NOT ESTABLISHED。</p></article>'
            )
        return "".join(output)

    summary_rows = []
    sections = []
    for universe in payload["universes"]:
        title = "881 广义行业" if universe["family"] == "BROAD_881" else "884 细分行业"
        rows = universe["rows"]
        active = [row for row in rows if row["currently_gate_active"]]
        weakening = [row for row in rows if row["recent_weakening"]]
        exits = [row for row in rows if row["gate_exited_since_previous_session"]]
        weakening_or_exit = [row for row in rows
                             if row["recent_weakening"] or row["gate_exited_since_previous_session"]]
        overlap = [row for row in rows if row["currently_gate_active"] and
                   (row["recent_weakening"] or row["gate_exited_since_previous_session"])]
        new_rows = [row for row in rows if row["recorded_event_ids_latest_session"]]
        event_count = sum(len(row["recorded_event_ids_latest_session"]) for row in rows)
        summary_rows.append(
            f"<tr><td>{esc(title)}</td><td>{len(rows)}</td><td>{event_count}</td>"
            f"<td>{len(active)}</td><td>{len(weakening)}</td><td>{len(exits)}</td>"
            f"<td>{len(overlap)}</td></tr>"
        )
        window_blocks = []
        for horizon in (5, 20, 60):
            window_blocks.append(
                f'<details class="window-view" data-horizon="{horizon}">'
                f'<summary>{horizon}日窗口 · 完整 {len(rows)} 个行业</summary>'
                f'{window_table(rows, horizon)}</details>'
            )
        sections.append(
            f'<section data-family="{esc(universe["family"])}"><h2>{esc(title)} · {len(rows)} 个</h2>'
            '<p class="muted">以下是重叠阅读视图，不是互斥信号状态；窗口排名只在本层内部排序。</p>'
            f'<details><summary>NEW · 本交易日账本 sector event {event_count} 个</summary>'
            '<p>这里只读取已保存 ledger；完整 qualified change 分组、breadth / leaders '
            '仍看同次运行 summary.md（若本页来自完整运行附件）。</p>'
            f'{compact_table(new_rows)}</details>'
            f'<details open><summary>ONGOING · 当前仍满足至少一个既有条件 · {len(active)}</summary>'
            f'{compact_table(active)}</details>'
            f'<details><summary>WEAKENING / EXIT · 近期减弱或具体条件退出 · '
            f'{len(weakening_or_exit)}</summary>'
            '<p>recent weakening = 20日层内排名的5-session变化与20日超额加速度都为负；'
            'EXIT 只表示具体 gate true→false，不等于全部条件退出、基本面恶化或卖出。</p>'
            f'{compact_table(weakening_or_exit)}</details>'
            '<h3>多时间窗口 · 原层内排名</h3>'
            '<p>这不是新综合分或机会榜；每个窗口完整列出本层全部行业，按保存的单窗口 '
            'cross-sectional rank 排序，平局按代码。</p>'
            + "".join(window_blocks)
            + f'<details><summary>行业详情 · 全部 {len(rows)} 个（按代码）</summary>'
            + cards(rows) + '</details></section>'
        )

    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>Sector Radar · 市场状态总览</title><style>'
        'body{font-family:system-ui,sans-serif;background:#f5f6f8;color:#202c3a;margin:0;padding:24px;line-height:1.65}'
        'main{max-width:1180px;margin:auto}header,section,article{background:white;padding:22px;margin:18px 0;border-radius:10px}'
        'header{border-top:5px solid #276b70}h1{font-size:28px}h2{font-size:22px}small,.muted{color:#5c6874}'
        'summary{cursor:pointer;padding:14px;background:#e8eef0;margin-top:10px;font-weight:600}'
        'table{border-collapse:collapse;min-width:720px;width:100%;font-size:14px}'
        'th,td{padding:8px;text-align:right;border-bottom:1px solid #ddd}'
        'th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}'
        '.scroll{overflow-x:auto}code{overflow-wrap:anywhere;font-size:12px}.warning{color:#7c4414}'
        '.overview{background:#f0f4f5;padding:14px;border-radius:8px}'
        'a{color:#195b70;text-decoration:none}a:hover{text-decoration:underline}'
        '@media(max-width:600px){body{padding:12px}header,section,article{padding:14px}'
        'h1{font-size:23px}table{min-width:680px}}'
        '</style></head><body><main><header><h1>Sector Radar · 市场状态总览</h1>'
        '<p><strong>READ-ONLY MARKET CONTEXT · SHADOW OBSERVATION ONLY</strong> · '
        'NOT RESEARCH · NOT A RECOMMENDATION</p>'
        '<p>HUMAN ATTENTION AUTHORITY = NONE · RESEARCH AUTHORITY = NONE · '
        'INVESTMENT AUTHORITY = NONE</p>'
        f'<p>状态交易日：<strong>{esc(payload["market_session"])}</strong>；'
        f'生成时间：{esc(payload["generated_at"]) }<br>'
        f'基准：{esc(payload["benchmark_thscode"]) }；距状态日 '
        f'{payload["calendar_days_since_market_session"]} 个自然日（不是缺失交易日数）。</p>'
        '<p class="warning">这是保存状态的只读投影，不是实时行情。本页不重新资格化完成交易日，'
        '不新增事件、提醒或 Research。</p>'
        '<div class="overview"><strong>怎么读：</strong> NEW 只读账本本次已记录事件；'
        'ONGOING 读当前 gate；WEAKENING / EXIT 读近期相对减弱与具体 predicate 退出；'
        '5/20/60 窗口直接按保存的层内排名浏览。各视图可重叠，计数不能相加成独立机会数。</div>'
        '<div class="scroll"><table><thead><tr><th>层级</th><th>行业总数</th><th>本日账本事件</th>'
        '<th>ONGOING</th><th>WEAKENING</th><th>Gate EXIT</th><th>ONGOING∩减弱/退出</th>'
        '</tr></thead><tbody>' + "".join(summary_rows) + '</tbody></table></div>'
        f'<p>状态交易日账本共有 {payload["recorded_events_latest_session"]} 个 sector event；'
        '真正的 0–3 首页及全部 qualified change 分组仍以同次 producer summary.md 为准。'
        '零事件不等于零强势行业；零新事件不等于市场没有持续状态。</p>'
        '<p>窗口收益是滚动窗口表现，不是逐日连续上涨；绝对收益和相对基准分开。'
        '原因、业务关系和持续性结论没有证据时保持未知。</p></header>'
        + "".join(sections)
        + f'<footer><p>Market state: <code>{esc(payload["market_state_hash"])}</code><br>'
        f'Ledger: <code>{esc(payload["event_ledger_hash"])}</code><br>'
        f'Context: <code>{esc(payload["context_hash"])}</code></p></footer></main></body></html>\n'
    )


def main(argv=None) -> int:
    from .sector_parent_hints import load_sector_parent_hints
    from .sector_radar_persistence import load_sector_radar_persistent_bundle
    parser = argparse.ArgumentParser(description="Read a trusted Sector Radar state bundle without changing it.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--parent-hints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    source, hints_path, output = args.bundle.resolve(), args.parent_hints.resolve(), args.output.resolve()
    if output.exists() or source.is_relative_to(output) or output.is_relative_to(source) or hints_path.is_relative_to(output):
        parser.error("output must be a new directory outside all input paths")
    try:
        hints = load_sector_parent_hints(hints_path)
        bundle = load_sector_radar_persistent_bundle(
            source, expected_repository="auguspp/decision-kernel",
            expected_workflow=".github/workflows/sector-radar-shadow.yml",
            expected_parent_hint_mapping_hash=hints.mapping_hash,
        )
        payload = build_sector_radar_context(market_state=bundle.market_state,
            event_ledger=bundle.event_ledger, generated_at=datetime.now(timezone.utc))
        text = render_sector_radar_context_html(payload)
        output.mkdir(parents=True, exist_ok=False)
        try:
            (output / "context.json").write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            (output / "index.html").write_text(text, encoding="utf-8")
        except OSError:
            shutil.rmtree(output)
            raise
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Context unavailable: {exc}\n")
    print(f"Read-only context written to {output}; new alerts = 0; investment authority = NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
