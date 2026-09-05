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


def render_sector_radar_context_html(payload: dict[str, Any]) -> str:
    """Standalone escaped HTML, no JavaScript, remote assets or default alert list."""
    _validate_context(payload)
    esc = lambda value: html.escape(str(value), quote=True)

    def cards(rows):
        if not rows:
            return "<p>此读取分区没有匹配项；这不是市场没有机会的结论。</p>"
        output = []
        for item in rows:
            row = item["observation"]
            values = []
            for horizon in (5, 20, 60):
                observation = row[f"horizon_{horizon}"]
                values.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in (
                    f"{horizon}日", _percent(observation["sector_return"]),
                    _percent(observation["benchmark_return"]), _percent(observation["excess_return"]),
                    observation["cross_sectional_rank"], observation["cross_sectional_rating"],
                )) + "</tr>")
            event_session = item["first_recorded_event_session"] or "账本未记录；不能据此推断首次发现日期"
            pulse = row["turnover_pulse_5_vs_prior_20"]
            pulse_text = "不可用" if pulse is None else f"{Decimal(pulse):.2f}×"
            output.append(
                f'<article id="{esc(row["thscode"])}"><h3>{esc(row["name"])} <small>{esc(row["thscode"])}</small></h3>'
                f'<p>{esc(item["path_description"])}（20日）</p><div class="scroll"><table><thead><tr>'
                '<th>窗口</th><th>行业收益</th><th>基准收益</th><th>超额收益</th><th>层内排名</th><th>层内rating</th>'
                '</tr></thead><tbody>' + "".join(values) + '</tbody></table></div>'
                f'<p>正超额年龄：{esc(_age(row, "positive_20d_excess"))}<br>'
                f'前四分位年龄：{esc(_age(row, "top_quartile_20d"))}<br>'
                f'5日内20日排名变化：{esc(row["rank_change_5_sessions_20d"])}；'
                f'超额加速度：{esc(_percent(row["excess_acceleration_5_sessions_20d"]))}；成交额脉冲：{esc(pulse_text)}</p>'
                f'<p>账本中首次前瞻事件：{esc(event_session)}<br>系统首次观察时间：未记录，不以趋势起点或首次事件代替。</p>'
                '<p class="muted">本页未重新获取成员或宽度，也不沿用旧宽度。成员分母、集中度和分组请查看对应交易日的运行审计。</p></article>'
            )
        return "".join(output)

    sections = []
    for universe in payload["universes"]:
        family = universe["family"]
        title = "881 广义行业" if family == "BROAD_881" else "884 细分行业"
        rows = universe["rows"]
        active = [row for row in rows if row["currently_gate_active"]]
        weakening = [row for row in rows if row["recent_weakening"] or row["gate_exited_since_previous_session"]]
        # A row may be both active and weakening. These are views, not exclusive signal states.
        sections.append(f'<section><h2>{title} · {universe["count"]} 个</h2>'
            f'<details><summary>仍满足既有条件的路径 · {len(active)}</summary>{cards(active)}</details>'
            f'<details><summary>近期减弱／条件退出 · {len(weakening)}</summary>'
            '<p>仅说明排名变化和超额加速度均为负，或一个既有条件退出；不代表卖出信号，也不代表基本面恶化。</p>'
            f'{cards(weakening)}</details>'
            f'<details><summary>全部行业（按代码；非机会榜） · {len(rows)}</summary>{cards(rows)}</details></section>')
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>Sector Radar · 保存状态视图</title><style>'
        'body{font-family:system-ui,sans-serif;background:#f5f6f8;color:#202c3a;margin:0;padding:24px;line-height:1.65}'
        'main{max-width:1060px;margin:auto}header,article{background:white;padding:22px;margin:18px 0;border-radius:10px}'
        'header{border-top:5px solid #276b70}h1{font-size:28px}h2{font-size:22px}small,.muted{color:#5c6874}'
        'summary{cursor:pointer;padding:16px;background:#e8eef0;margin-top:10px;font-weight:600}'
        'table{border-collapse:collapse;min-width:600px;width:100%;font-size:14px}th,td{padding:8px;text-align:right;border-bottom:1px solid #ddd}'
        '.scroll{overflow-x:auto}code{overflow-wrap:anywhere;font-size:12px}.warning{color:#7c4414}'
        '@media(max-width:600px){body{padding:12px}header,article{padding:14px}h1{font-size:23px}}'
        '</style></head><body><main><header><h1>Sector Radar · 保存状态视图</h1>'
        '<p><strong>SHADOW OBSERVATION ONLY</strong> · NOT RESEARCH · NOT A RECOMMENDATION</p>'
        '<p>HUMAN ATTENTION AUTHORITY = NONE · INVESTMENT AUTHORITY = NONE</p>'
        f'<p>状态交易日：<strong>{esc(payload["market_session"])}</strong>；生成时间：{esc(payload["generated_at"])}<br>'
        f'基准：{esc(payload["benchmark_thscode"])}；距状态日 {payload["calendar_days_since_market_session"]} 个自然日（不是缺失交易日数）。</p>'
        '<p class="warning">这是保存数据的只读投影，不是实时行情。本次未重新验证最新完成交易日，也没有产生新提醒。</p>'
        f'<p>状态交易日账本已有事件：{payload["recorded_events_latest_session"]}。零事件不等于零强势行业。'
        '真正的0–3组新事件摘要仍以当次 producer 的 summary.md 为准；本页不重新排序或合并候选。</p>'
        '<p>“近期减弱”是阅读标记，不参与 gate。持续路径、减弱路径可重叠；881与884不混合排名。</p></header>'
        + "".join(sections) + f'<footer><p>Market state: <code>{esc(payload["market_state_hash"])}</code><br>'
        f'Ledger: <code>{esc(payload["event_ledger_hash"])}</code><br>'
        f'Context: <code>{esc(payload["context_hash"])}</code></p></footer></main></body></html>\n')


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
