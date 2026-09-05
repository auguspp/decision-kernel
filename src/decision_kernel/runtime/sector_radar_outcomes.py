"""T+5/T+20 objective sector paths from a frozen event ledger and daily states.

This read-only Harness evaluator does not generate signals, fetch prices, restore
producer state, accept Human annotations, or adjudicate investment judgments.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, time, timezone
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Sequence
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from .sector_radar_events import SectorRadarCandidateEventLedger
    from .sector_radar_state import SectorRadarMarketState

from decision_kernel.identity import canonical_hash, canonical_json

VERSION = "sector-objective-close-path-t5-t20-v0"
SEMANTICS = "OBJECTIVE_SECTOR_PATH_NOT_INVESTMENT_JUDGMENT"
HORIZONS = (5, 20)
EVALUATED = "EVALUATED"
PENDING = "PENDING_HORIZON"
INCOMPLETE = "INPUTS_INCOMPLETE"
TZ = ZoneInfo("Asia/Shanghai")
# Explicitly match the existing sector calculation's Decimal precision; do not
# inherit a caller's mutable precision when recomputing the frozen entry.
CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)
LIMIT_BYTES = 16 * 1024 * 1024


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("evaluation clock must be timezone-aware")


def _close_at(session: date) -> datetime:
    return datetime.combine(session, time(15), tzinfo=TZ)


def _calendar(sessions: Sequence[date]) -> tuple[date, ...]:
    days = tuple(sessions)
    if (not days or any(type(d) is not date for d in days)
            or days != tuple(sorted(set(days)))):
        raise ValueError("explicit calendar must contain unique ascending dates")
    return days


def _check_inputs(ledger, states, calendar, as_of, generated_at):
    from .sector_radar_events import _validate_ledger
    from .sector_radar_state import _validate_state, SECTOR_RADAR_STATE_WINDOW_SESSIONS
    _aware(generated_at)
    if type(as_of) is not date or as_of not in calendar or generated_at < _close_at(as_of):
        raise ValueError("evaluation boundary must be a completed explicit calendar session")
    _validate_ledger(ledger, verify_hash=True)
    if ledger.updated_at > generated_at:
        raise ValueError("event ledger was recorded after the evaluation clock")
    if not states:
        raise ValueError("evaluation requires supplied market states, including its as-of session")
    by_day = {}
    for state in states:
        _validate_state(state, verify_hash=True)
        day = state.sessions[-1]
        if day > as_of or state.updated_at > generated_at or state.updated_at < _close_at(day):
            raise ValueError("market state is future or not a completed-session observation")
        if state.sessions != tuple(d for d in calendar if state.sessions[0] <= d <= day):
            raise ValueError("state history disagrees with the explicit calendar; no missing-day bridge")
        previous = by_day.get(day)
        if previous is not None and previous.state_hash != state.state_hash:
            raise ValueError("conflicting state versions for one session require explicit review")
        by_day[day] = state  # exact same-state duplicates are not extra observations
    if as_of not in by_day:
        raise ValueError("as-of session has no supplied verified market state")
    ordered = sorted(by_day)
    for older_day, newer_day in zip(ordered, ordered[1:]):
        older, newer = by_day[older_day], by_day[newer_day]
        for field in ("catalog_hash", "formula_version", "benchmark_thscode", "benchmark_name",
                      "broad_identities", "granular_identities", "created_at", "source", "source_lineage"):
            if getattr(older, field) != getattr(newer, field):
                raise ValueError(f"market-state lineage/universe changed: {field}")
        additions = tuple(d for d in calendar if older_day < d <= newer_day)
        if newer.sessions != (*older.sessions, *additions)[-SECTOR_RADAR_STATE_WINDOW_SESSIONS:]:
            raise ValueError("rolling-state session window disagrees with the supplied calendar")
        if newer.updated_at < older.updated_at:
            raise ValueError("market-state recording clock moved backwards")
        old_index = {d: i for i, d in enumerate(older.sessions)}
        new_index = {d: i for i, d in enumerate(newer.sessions)}
        overlap = set(old_index) & set(new_index)
        if not overlap:
            raise ValueError("state windows do not overlap; qualified recovery is outside this evaluator")
        old_series = {s.thscode: s for s in older.series}
        for s in newer.series:
            previous = old_series[s.thscode]
            if any((s.closes[new_index[d]], s.turnovers[new_index[d]]) !=
                   (previous.closes[old_index[d]], previous.turnovers[old_index[d]]) for d in overlap):
                raise ValueError("overlapping market observations changed; no silent price revision")
    for event in ledger.events:
        if event.candidate.as_of_session > as_of or event.first_recorded_at > generated_at:
            raise ValueError("event is after the evaluation boundary")
        if event.first_recorded_at < _close_at(event.candidate.as_of_session):
            raise ValueError("event precedes its completed signal-session close")
        if event.candidate.as_of_session not in calendar:
            raise ValueError("signal session is absent from the evaluation calendar")
    return by_day


def _snapshot_pair(state):
    from .sector_radar_state import calculate_sector_radar_state_snapshot_pair
    return calculate_sector_radar_state_snapshot_pair(state)


def _family_pair(pair, family):
    from .sector_radar_shadow import BROAD_881, GRANULAR_884
    if family == BROAD_881:
        return pair.broad_previous, pair.broad_current
    if family == GRANULAR_884:
        return pair.granular_previous, pair.granular_current
    raise ValueError("unsupported event family")


def _verify_anchor(event, anchor, pair):
    from .sector_radar_shadow import SECTOR_RADAR_SHADOW_POLICY_VERSION, select_sector_radar_state_entries
    if (event.source_market_state_hash != anchor.state_hash
            or event.catalog_hash != anchor.catalog_hash
            or event.benchmark_thscode != anchor.benchmark_thscode
            or event.formula_version != anchor.formula_version
            or event.policy_version != SECTOR_RADAR_SHADOW_POLICY_VERSION):
        raise ValueError("event and exact signal-time state identity disagree")
    if event.first_recorded_at < anchor.updated_at:
        raise ValueError("event was recorded before its source state")
    previous, current = _family_pair(pair, event.candidate.family)
    entries = select_sector_radar_state_entries(current=current, previous=previous)
    if event.candidate not in entries.candidates:
        raise ValueError("frozen event does not reproduce from its previous/current market state")


def _path_metrics(sector: Sequence[Decimal], benchmark: Sequence[Decimal]) -> dict:
    """Signal close is a descriptive anchor, NOT an executable post-signal fill."""
    if len(sector) != len(benchmark) or len(sector) not in (6, 21):
        raise ValueError("objective paths require exactly signal plus 5 or 20 closes")
    if any(not isinstance(x, Decimal) or not x.is_finite() or x <= 0 for x in (*sector, *benchmark)):
        raise ValueError("path closes must be finite positive Decimal values")
    with localcontext(CONTEXT):
        sector_path = tuple(p / sector[0] - 1 for p in sector)
        benchmark_path = tuple(p / benchmark[0] - 1 for p in benchmark)
        excess_path = tuple(s - b for s, b in zip(sector_path, benchmark_path))
        return {
            "sector_return": sector_path[-1], "benchmark_return": benchmark_path[-1],
            "excess_return": excess_path[-1],
            "close_path_mfe": max(sector_path), "close_path_mae": min(sector_path),
            "close_path_excess_mfe": max(excess_path), "close_path_excess_mae": min(excess_path),
            "excursion_basis": "CLOSES_INCLUDING_ZERO_AT_SIGNAL_NOT_INTRADAY_EXTREMES",
            "return_basis": "SIGNAL_CLOSE_PATH_NOT_EXECUTABLE_RETURN_OR_TOTAL_RETURN",
        }


def evaluate_sector_radar_outcomes(
    *, ledger: SectorRadarCandidateEventLedger, states: Sequence[SectorRadarMarketState],
    trading_sessions: Sequence[date], as_of_session: date, generated_at: datetime,
) -> dict:
    """Evaluate every ledger event at fixed horizons without modifying any input.

    Requires an exact saved state at the signal and each elapsed forward session.
    The explicit as-of boundary is NOT a claim that inputs are today's latest data.
    Hashes/validation prove supplied consistency, not external origin or live provenance.
    """
    from .sector_radar_shadow import _persistent_gate, _acceleration_gate
    calendar = _calendar(trading_sessions)
    by_day = _check_inputs(ledger, states, calendar, as_of_session, generated_at)
    indices = {day: i for i, day in enumerate(calendar)}
    snapshots = {}
    def pair(day):
        if day not in snapshots:
            snapshots[day] = _snapshot_pair(by_day[day])
        return snapshots[day]
    rows = []
    with localcontext(CONTEXT):
        for event in ledger.events:
            candidate = event.candidate
            start = indices[candidate.as_of_session]
            elapsed = indices[as_of_session] - start
            anchor = by_day.get(candidate.as_of_session)
            if anchor is not None:
                _verify_anchor(event, anchor, pair(candidate.as_of_session))
            for horizon in HORIZONS:
                due = calendar[start + horizon] if start + horizon < len(calendar) else None
                required = calendar[start:start + min(horizon, elapsed) + 1]
                missing = [day for day in required if day not in by_day]
                row = {
                    "event_id": event.event_id, "event_hash": event.event_hash,
                    "first_group_hash": event.first_group_hash,
                    "thscode": candidate.thscode, "name": candidate.name, "family": candidate.family,
                    "signal_session": candidate.as_of_session, "horizon_sessions": horizon,
                    "target_session": due, "elapsed_sessions": min(horizon, elapsed),
                    "missing_state_sessions": missing, "outcome": None,
                    "status": INCOMPLETE if missing else PENDING if elapsed < horizon else EVALUATED,
                }
                if row["status"] == EVALUATED:
                    sector_prices, benchmark_prices, daily = [], [], []
                    active_prefix, prefix_open, first_exit = 0, True, None
                    for index, day in enumerate(required):
                        state = by_day[day]
                        series = {s.thscode: s for s in state.series}
                        sector_prices.append(series[candidate.thscode].closes[-1])
                        benchmark_prices.append(series[event.benchmark_thscode].closes[-1])
                        _, current = _family_pair(pair(day), candidate.family)
                        if current.exclusions:
                            raise ValueError("outcome ranking requires an exclusion-free same-family snapshot")
                        observation = next(o for o in current.observations if o.thscode == candidate.thscode)
                        persistent, accelerating = _persistent_gate(observation), _acceleration_gate(observation)
                        original_active = ((candidate.persistent_gate_entered and persistent)
                                           or (candidate.acceleration_gate_entered and accelerating))
                        if index:
                            if not original_active:
                                prefix_open = False
                                if first_exit is None:
                                    first_exit = day
                            if prefix_open:
                                active_prefix += 1
                        daily.append({
                            "session": day, "state_hash": state.state_hash,
                            "sector_close": sector_prices[-1], "benchmark_close": benchmark_prices[-1],
                            "rank_20d": observation.horizon_20.cross_sectional_rank,
                            "rating_20d": observation.horizon_20.cross_sectional_rating,
                            "family_universe_size": len(current.observations),
                            "persistent_gate_active": persistent, "acceleration_gate_active": accelerating,
                            "original_gate_active": original_active,
                        })
                    outcome = {
                        "version": VERSION, "semantics": SEMANTICS,
                        "event_id": event.event_id, "event_hash": event.event_hash,
                        "source_market_state_hash": event.source_market_state_hash,
                        "catalog_hash": event.catalog_hash, "formula_version": event.formula_version,
                        "policy_version": event.policy_version, "benchmark_thscode": event.benchmark_thscode,
                        "first_group_hash": event.first_group_hash, "family": candidate.family,
                        "horizon_sessions": horizon, "path": daily,
                        "metrics": {
                            **_path_metrics(sector_prices, benchmark_prices),
                            "rank_20d_change": daily[0]["rank_20d"] - daily[-1]["rank_20d"],
                            "persistent_active_days": sum(d["persistent_gate_active"] for d in daily[1:]),
                            "acceleration_active_days": sum(d["acceleration_gate_active"] for d in daily[1:]),
                            "original_gate_continuation_days": active_prefix,
                            "first_original_gate_exit_session": first_exit,
                        },
                        "signal_transition_authority": "NONE", "research_authority": "NONE",
                        "human_attention_authority": "NONE", "investment_authority": "NONE",
                    }
                    outcome["outcome_hash"] = canonical_hash(outcome)
                    row["outcome"] = outcome
                rows.append(row)
    payload = json.loads(canonical_json({
        "version": VERSION, "semantics": SEMANTICS, "as_of_session": as_of_session,
        "ledger_hash": ledger.ledger_hash, "calendar_hash": canonical_hash(calendar),
        "state_hashes": {d.isoformat(): by_day[d].state_hash for d in sorted(by_day)},
        "event_count": len(ledger.events), "horizon_assessment_count": len(rows),
        "status_counts": {s: sum(r["status"] == s for r in rows) for s in (EVALUATED, PENDING, INCOMPLETE)},
        "rows": rows, "signal_transition_authority": "NONE", "research_authority": "NONE",
        "human_attention_authority": "NONE", "investment_authority": "NONE",
        "scope": "SUPPLIED_FROZEN_INPUTS_ONLY_NOT_LIVE_CORPUS_CERTIFICATION",
        "sample_note": "Events and two horizons are not independent forecasts; original groups remain linked.",
    }))
    return {"generated_at": generated_at.isoformat(), "evaluation": payload,
            "evaluation_hash": canonical_hash(payload)}


def render_sector_radar_outcomes(report: dict) -> str:
    p = report["evaluation"]
    if (report["evaluation_hash"] != canonical_hash(p) or p["version"] != VERSION
            or p["semantics"] != SEMANTICS
            or any(p[k] != "NONE" for k in ("investment_authority", "research_authority",
                                           "human_attention_authority", "signal_transition_authority"))):
        raise ValueError("invalid objective outcome report")
    e = escape
    def pct(value):
        with localcontext(CONTEXT):
            return f"{Decimal(value) * 100:.2f}%"
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>Sector Radar · 前瞻路径评估</title>',
             '<style>body{font:16px/1.65 system-ui,sans-serif;max-width:1050px;margin:32px auto;padding:0 18px;color:#22343b}article{border:1px solid #cddbd9;border-radius:10px;padding:18px;margin:18px 0}h1{font-size:30px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}p{overflow-wrap:anywhere}small{color:#536b70}</style>',
             '<h1>Sector Radar · 前瞻路径评估</h1>',
             '<p>SHADOW OBSERVATION ONLY · 非推荐、非交易收益、非判断质量评分。</p>',
             f'<p>输入评估边界：{e(p["as_of_session"])}；账本事件 {p["event_count"]} 个。不是今日完整性声明。</p>',
             '<p>按完整交易日计数；缺一天不补价。881／884 独立排名。收盘路径极值不是日内 MFE／MAE。</p>']
    if not p["rows"]:
        parts.append('<article><h2>尚无账本候选可评估</h2><p>不是零收益、不是市场没有机会，也没有创建历史预测。</p></article>')
    labels = {EVALUATED: "窗口已完整观测", PENDING: "尚未到期（截至输入边界）", INCOMPLETE: "缺少精确日状态"}
    for row in p["rows"]:
        parts.append(f'<article><h2>{e(row["name"])} · {e(row["thscode"])} · T+{row["horizon_sessions"]}</h2>'
                     f'<p>{e(row["family"])} · {e(row["signal_session"])} → {e(row["target_session"] or "未来目标交易日未提供")}</p>'
                     f'<p><strong>{labels[row["status"]]}</strong></p>')
        outcome = row["outcome"]
        if outcome:
            m = outcome["metrics"]
            parts.append(f'<p>行业 {pct(m["sector_return"])} ／ 基准 {pct(m["benchmark_return"])} ／ 超额 {pct(m["excess_return"])}</p>'
                         f'<p>收盘路径有利偏离 {pct(m["close_path_mfe"])} ／ 不利偏离 {pct(m["close_path_mae"])}</p>'
                         f'<p>20日排名：{e(outcome["path"][0]["rank_20d"])} → {e(outcome["path"][-1]["rank_20d"])}；原触发条件连续保持 {m["original_gate_continuation_days"]} 个后续交易日。</p>')
        elif row["missing_state_sessions"]:
            parts.append(f'<p>缺失：{e(", ".join(row["missing_state_sessions"]))}。不从较晚窗口回填当天状态。</p>')
        parts.append(f'<details><summary>完整路径、状态及原分组关联</summary><pre>{e(json.dumps(row, ensure_ascii=False, indent=2))}</pre></details></article>')
    parts.append(f'<footer><p>Human 注释、归因和方法学习不进入这些客观结果。原分组关联保留，不将父子行业或两个期限当作独立样本。</p><small>生成时间：{e(report["generated_at"])}，不是信号或行情时间。System investment authority = NONE。</small></footer></html>')
    return "\n".join(parts) + "\n"


def _read_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(LIMIT_BYTES + 1)
    if len(data) > LIMIT_BYTES:
        raise ValueError("input file exceeds evaluator read budget")
    return data.decode("utf-8")


def main(argv=None, *, stdout=None, stderr=None) -> int:
    from decision_kernel.adapters.hithink import normalize_hithink_calendar
    from .sector_radar_events import parse_sector_radar_candidate_event_ledger
    from .sector_radar_state import parse_sector_radar_market_state
    parser = argparse.ArgumentParser(description="Evaluate a supplied frozen Sector ledger; no network or state mutation.")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--state", type=Path, action="append", required=True)
    parser.add_argument("--calendar", type=Path, required=True, help="Saved HiThink calendar JSON envelope, not inferred dates")
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    owned = False
    try:
        inputs = [args.ledger, args.calendar, *args.state]
        if (len(args.state) > 128 or args.output.exists() or args.output.is_symlink()
                or any(args.output.resolve().is_relative_to(p.resolve().parent) for p in inputs)):
            raise ValueError("use a new output directory outside input directories; at most 128 states")
        report = evaluate_sector_radar_outcomes(
            ledger=parse_sector_radar_candidate_event_ledger(_read_file(args.ledger)),
            states=tuple(parse_sector_radar_market_state(_read_file(p)) for p in args.state),
            trading_sessions=normalize_hithink_calendar(json.loads(_read_file(args.calendar))),
            as_of_session=args.as_of, generated_at=datetime.now(timezone.utc),
        )
        page = render_sector_radar_outcomes(report)
        args.output.mkdir(parents=True, exist_ok=False)
        owned = True
        (args.output / "outcomes.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output / "index.html").write_text(page, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if owned:
            shutil.rmtree(args.output)
        print(f"OUTCOME EVALUATION FAILED: {exc}", file=stderr or sys.stderr)
        return 2
    print(f"READ-ONLY OBJECTIVE OUTCOMES: {report['evaluation']['status_counts']}", file=stdout or sys.stdout)
    # Incomplete data is not an ordinary successful complete evaluation.
    return 2 if report["evaluation"]["status_counts"][INCOMPLETE] else 0


if __name__ == "__main__":
    raise SystemExit(main())
