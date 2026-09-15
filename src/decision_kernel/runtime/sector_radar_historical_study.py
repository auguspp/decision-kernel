"""Bounded historical Sector Radar outcome study over one frozen market state.

This is not a trading backtest. Signal-time series are physically truncated at T
before the existing Radar formula and false-to-true policy are called. Later
closes are attached only after those selection flags are frozen.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, time
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json

from .sector_radar import SectorPricePoint, SectorPriceSeries, calculate_sector_radar_snapshot
from .sector_radar_outcomes import CONTEXT, EVALUATED, PENDING
from .sector_radar_shadow import (
    BROAD_881,
    GRANULAR_884,
    SECTOR_RADAR_SHADOW_POLICY_VERSION,
    select_sector_radar_state_entries,
)
from .sector_radar_state import (
    BENCHMARK_FAMILY,
    SECTOR_RADAR_STATE_WINDOW_SESSIONS,
    SectorRadarMarketState,
    _validate_state,
    load_sector_radar_market_state,
)

VERSION = "sector-frozen-universe-prefix-outcome-study-v0"
SEMANTICS = "HISTORICAL_PREFIX_DISCOVERY_STUDY_NOT_TRADING_BACKTEST"
HORIZONS = (5, 20, 60)
BASELINE_VERSION = "positive-20d-excess-top-decile-v0"
BASELINE_SEMANTICS = "20D_EXCESS_GT_ZERO_AND_20D_RATING_GTE_90_NO_PERSISTENCE_OR_ACCELERATION"
UNIVERSE_QUALIFICATION = (
    "FROZEN_UNIVERSE_PRICE_PATH_ONLY__CATALOG_EFFECTIVE_DATE_NOT_INDEPENDENTLY_PROVEN"
)
PRICE_PATH_QUALIFICATION = "PHYSICALLY_PREFIX_TRUNCATED_BEFORE_SIGNAL_CALCULATION"
OUTCOME_QUALIFICATION = "FUTURE_CLOSES_ATTACHED_ONLY_AFTER_PREFIX_SIGNAL_FREEZE"
EDGE_ACCEPTANCE = "NOT_CERTIFIED__HISTORICAL_CATALOG_EFFECTIVE_DATE_UNKNOWN"
PROXY_SEMANTICS = "FORWARD_EXCESS_SIGN_PROXY_ONLY_NOT_INVESTMENT_ERROR_CLASSIFICATION"
TZ = ZoneInfo("Asia/Shanghai")


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("historical study clock must be timezone-aware")


def _close(day) -> datetime:
    return datetime.combine(day, time(15), tzinfo=TZ)


def _price_series(state: SectorRadarMarketState) -> dict[str, SectorPriceSeries]:
    return {
        item.thscode: SectorPriceSeries(
            thscode=item.thscode,
            name=item.name,
            points=tuple(
                SectorPricePoint(session=day, close=close, turnover=turnover)
                for day, close, turnover in zip(
                    state.sessions, item.closes, item.turnovers, strict=True
                )
            ),
        )
        for item in state.series
    }


def _family_codes(state: SectorRadarMarketState, family: str) -> tuple[str, ...]:
    if family == BROAD_881:
        return tuple(code for code, _ in state.broad_identities)
    if family == GRANULAR_884:
        return tuple(code for code, _ in state.granular_identities)
    raise ValueError("unsupported historical-study family")


def _prefix(series: SectorPriceSeries, end_index: int) -> SectorPriceSeries:
    points = series.points[: end_index + 1]
    if len(points) != end_index + 1:
        raise ValueError("historical-study prefix index lies outside retained state")
    return SectorPriceSeries(thscode=series.thscode, name=series.name, points=points)


def _snapshots(
    *, state: SectorRadarMarketState,
    prices: dict[str, SectorPriceSeries],
    family: str,
) -> dict[int, Any]:
    codes = _family_codes(state, family)
    output: dict[int, Any] = {}
    for end_index in range(60, len(state.sessions)):
        snapshot = calculate_sector_radar_snapshot(
            sectors=tuple(_prefix(prices[code], end_index) for code in codes),
            benchmark=_prefix(prices[state.benchmark_thscode], end_index),
            as_of_session=state.sessions[end_index],
        )
        if snapshot.exclusions:
            raise ValueError("historical frozen-universe snapshot contains exclusions")
        output[end_index] = snapshot
    return output


def _baseline_selected(observation) -> bool:
    return (
        observation.horizon_20.excess_return > 0
        and observation.horizon_20.cross_sectional_rating >= 90
    )


def _historical_path_metrics(
    sector: Sequence[Decimal], benchmark: Sequence[Decimal]
) -> dict[str, Any]:
    """Prospective close-path contract, extended only to the frozen T+60 study."""
    if len(sector) != len(benchmark) or len(sector) not in tuple(h + 1 for h in HORIZONS):
        raise ValueError("historical objective path must be signal plus 5, 20 or 60 closes")
    if any(
        not isinstance(value, Decimal) or not value.is_finite() or value <= 0
        for value in (*sector, *benchmark)
    ):
        raise ValueError("historical objective path closes must be finite positive Decimal values")
    with localcontext(CONTEXT):
        sector_path = tuple(price / sector[0] - 1 for price in sector)
        benchmark_path = tuple(price / benchmark[0] - 1 for price in benchmark)
        excess_path = tuple(s - b for s, b in zip(sector_path, benchmark_path, strict=True))
        return {
            "sector_return": sector_path[-1],
            "benchmark_return": benchmark_path[-1],
            "excess_return": excess_path[-1],
            "close_path_mfe": max(sector_path),
            "close_path_mae": min(sector_path),
            "close_path_excess_mfe": max(excess_path),
            "close_path_excess_mae": min(excess_path),
            "excursion_basis": "CLOSES_INCLUDING_ZERO_AT_SIGNAL_NOT_INTRADAY_EXTREMES",
            "return_basis": "SIGNAL_CLOSE_PATH_NOT_EXECUTABLE_RETURN_OR_TOTAL_RETURN",
        }


def _outcome(
    *, sector: SectorPriceSeries,
    benchmark: SectorPriceSeries,
    signal_index: int,
    horizon: int,
) -> dict[str, Any]:
    target = signal_index + horizon
    if target >= len(sector.points):
        return {"status": PENDING, "target_session": None, "metrics": None}
    if len(sector.points) != len(benchmark.points):
        raise ValueError("historical-study sector and benchmark calendars disagree")
    metrics = _historical_path_metrics(
        tuple(point.close for point in sector.points[signal_index : target + 1]),
        tuple(point.close for point in benchmark.points[signal_index : target + 1]),
    )
    return {
        "status": EVALUATED,
        "target_session": sector.points[target].session,
        "metrics": metrics,
    }


def _median(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def _cohort_stats(
    rows: Sequence[dict[str, Any]], *, horizon: int, selector: str
) -> dict[str, Any]:
    selected = [row for row in rows if row[selector]]
    evaluated = [
        row for row in selected if row["outcomes"][horizon]["status"] == EVALUATED
    ]
    values = [row["outcomes"][horizon]["metrics"]["excess_return"] for row in evaluated]
    mfes = [row["outcomes"][horizon]["metrics"]["close_path_excess_mfe"] for row in evaluated]
    maes = [row["outcomes"][horizon]["metrics"]["close_path_excess_mae"] for row in evaluated]
    positive = sum(value > 0 for value in values)
    return {
        "selected_count": len(selected),
        "evaluated_count": len(evaluated),
        "pending_count": len(selected) - len(evaluated),
        "mean_excess_return": None if not values else sum(values, Decimal(0)) / Decimal(len(values)),
        "median_excess_return": _median(values),
        "positive_excess_count": positive,
        "positive_excess_rate": None if not values else Decimal(positive) / Decimal(len(values)),
        "mean_excess_mfe": None if not mfes else sum(mfes, Decimal(0)) / Decimal(len(mfes)),
        "mean_excess_mae": None if not maes else sum(maes, Decimal(0)) / Decimal(len(maes)),
    }


def _family_summary(
    rows: Sequence[dict[str, Any]], *, horizon: int
) -> dict[str, Any]:
    radar = _cohort_stats(rows, horizon=horizon, selector="radar_selected")
    baseline = _cohort_stats(rows, horizon=horizon, selector="baseline_selected")
    evaluated = [row for row in rows if row["outcomes"][horizon]["status"] == EVALUATED]
    false_positive = sum(
        row["radar_selected"]
        and row["outcomes"][horizon]["metrics"]["excess_return"] <= 0
        for row in evaluated
    )
    false_negative = sum(
        not row["radar_selected"]
        and row["outcomes"][horizon]["metrics"]["excess_return"] > 0
        for row in evaluated
    )
    mean_delta = None
    rate_delta = None
    if radar["mean_excess_return"] is not None and baseline["mean_excess_return"] is not None:
        mean_delta = radar["mean_excess_return"] - baseline["mean_excess_return"]
    if radar["positive_excess_rate"] is not None and baseline["positive_excess_rate"] is not None:
        rate_delta = radar["positive_excess_rate"] - baseline["positive_excess_rate"]
    return {
        "horizon_sessions": horizon,
        "radar": radar,
        "baseline": baseline,
        "radar_baseline_overlap_count": sum(
            row["radar_selected"] and row["baseline_selected"] for row in rows
        ),
        "radar_minus_baseline_mean_excess_return": mean_delta,
        "radar_minus_baseline_positive_excess_rate": rate_delta,
        "radar_false_positive_proxy_count": false_positive,
        "radar_false_negative_proxy_count": false_negative,
        "proxy_semantics": PROXY_SEMANTICS,
        "cohort_overlap_note": "RADAR_AND_BASELINE_COHORTS_MAY_OVERLAP_NOT_INDEPENDENT_SAMPLES",
    }


def build_sector_radar_historical_study(
    *, state: SectorRadarMarketState, generated_at: datetime
) -> dict[str, Any]:
    """Build a deterministic retrospective prefix study from one frozen state."""
    _aware(generated_at)
    _validate_state(state, verify_hash=True)
    if generated_at < _close(state.sessions[-1]):
        raise ValueError("historical study cannot precede the frozen state's final close")
    if len(state.sessions) != SECTOR_RADAR_STATE_WINDOW_SESSIONS:
        raise ValueError("historical study v0 requires one full rolling Sector state window")
    if not state.series or state.series[0].family != BENCHMARK_FAMILY:
        raise ValueError("historical study requires the canonical benchmark-first state series")

    prices = _price_series(state)
    benchmark = prices[state.benchmark_thscode]
    rows: list[dict[str, Any]] = []
    session_summaries: list[dict[str, Any]] = []

    with localcontext(CONTEXT):
        for family in (BROAD_881, GRANULAR_884):
            snapshots = _snapshots(state=state, prices=prices, family=family)
            for signal_index in range(61, len(state.sessions)):
                current = snapshots[signal_index]
                previous = snapshots[signal_index - 1]
                entries = select_sector_radar_state_entries(current=current, previous=previous)
                candidates = {candidate.thscode: candidate for candidate in entries.candidates}
                session_rows: list[dict[str, Any]] = []
                for observation in current.observations:
                    candidate = candidates.get(observation.thscode)
                    row = {
                        "signal_session": state.sessions[signal_index],
                        "family": family,
                        "thscode": observation.thscode,
                        "name": observation.name,
                        "radar_selected": candidate is not None,
                        "radar_event_type": None if candidate is None else candidate.event_type,
                        "baseline_selected": _baseline_selected(observation),
                        "signal_features": {
                            "horizon_5_rating": observation.horizon_5.cross_sectional_rating,
                            "horizon_20_rating": observation.horizon_20.cross_sectional_rating,
                            "horizon_20_excess_return": observation.horizon_20.excess_return,
                            "rank_change_5_sessions_20d": observation.rank_change_5_sessions_20d,
                            "positive_20d_excess_persistence_sessions": observation.positive_20d_excess_persistence_sessions,
                            "turnover_pulse_5_vs_prior_20": observation.turnover_pulse_5_vs_prior_20,
                        },
                        "outcomes": {
                            horizon: _outcome(
                                sector=prices[observation.thscode],
                                benchmark=benchmark,
                                signal_index=signal_index,
                                horizon=horizon,
                            )
                            for horizon in HORIZONS
                        },
                    }
                    rows.append(row)
                    session_rows.append(row)
                session_summaries.append({
                    "signal_session": state.sessions[signal_index],
                    "family": family,
                    "universe_count": len(session_rows),
                    "radar_selected_count": sum(row["radar_selected"] for row in session_rows),
                    "baseline_selected_count": sum(row["baseline_selected"] for row in session_rows),
                })

    summary = {
        family: {
            str(horizon): _family_summary(
                [row for row in rows if row["family"] == family], horizon=horizon
            )
            for horizon in HORIZONS
        }
        for family in (BROAD_881, GRANULAR_884)
    }
    payload = json.loads(canonical_json({
        "version": VERSION,
        "semantics": SEMANTICS,
        "source_state_hash": state.state_hash,
        "source_state_session": state.sessions[-1],
        "source_state_session_count": len(state.sessions),
        "catalog_hash": state.catalog_hash,
        "benchmark_thscode": state.benchmark_thscode,
        "formula_version": state.formula_version,
        "radar_policy_version": SECTOR_RADAR_SHADOW_POLICY_VERSION,
        "horizons": HORIZONS,
        "baseline_version": BASELINE_VERSION,
        "baseline_semantics": BASELINE_SEMANTICS,
        "historical_universe_identity_qualification": UNIVERSE_QUALIFICATION,
        "price_path_pit_qualification": PRICE_PATH_QUALIFICATION,
        "outcome_attachment_qualification": OUTCOME_QUALIFICATION,
        "edge_acceptance": EDGE_ACCEPTANCE,
        "first_signal_session": state.sessions[61],
        "last_signal_session": state.sessions[-1],
        "signal_session_count": len(state.sessions) - 61,
        "row_count": len(rows),
        "session_summaries": session_summaries,
        "summary": summary,
        "rows": rows,
        "signal_transition_authority": "NONE",
        "research_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
        "scope": "ONE_FROZEN_SECTOR_STATE_WINDOW_ONLY_NO_PROVIDER_CALLS_NO_PORTFOLIO_SIMULATION",
        "sample_note": "Repeated sector/session observations and overlapping Radar/baseline cohorts are not independent forecasts.",
    }))
    return {
        "generated_at": generated_at.isoformat(),
        "study": payload,
        "study_hash": canonical_hash(payload),
    }


def render_sector_radar_historical_study_markdown(report: dict[str, Any]) -> str:
    study = report.get("study")
    if not isinstance(study, dict) or report.get("study_hash") != canonical_hash(study):
        raise ValueError("invalid historical Sector outcome study report")
    if study.get("version") != VERSION or study.get("semantics") != SEMANTICS:
        raise ValueError("historical Sector outcome study identity changed")
    if any(study.get(key) != "NONE" for key in (
        "signal_transition_authority", "research_authority",
        "human_attention_authority", "investment_authority",
    )):
        raise ValueError("historical Sector outcome study acquired forbidden authority")

    def pct(value) -> str:
        return "—" if value is None else f"{Decimal(value) * 100:.2f}%"

    lines = [
        "# Sector Radar Historical Outcome Study v0", "",
        f"- source state session: `{study['source_state_session']}`",
        f"- source state hash: `{study['source_state_hash']}`",
        f"- study hash: `{report['study_hash']}`",
        f"- formula: `{study['formula_version']}`",
        f"- Radar policy: `{study['radar_policy_version']}`",
        f"- baseline: `{study['baseline_version']}`",
        f"- universe qualification: `{study['historical_universe_identity_qualification']}`",
        f"- edge acceptance: `{study['edge_acceptance']}`", "",
        "This is a frozen-universe discovery outcome study, **not** a trading backtest, Recommendation, Odds, Action, or Investment Authority.",
        "", "## Cohort summary", "",
        "| Family | Horizon | Radar n | Radar mean excess | Radar positive | Baseline n | Baseline mean excess | Baseline positive |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for family in (BROAD_881, GRANULAR_884):
        for horizon in HORIZONS:
            item = study["summary"][family][str(horizon)]
            radar, baseline = item["radar"], item["baseline"]
            lines.append(
                f"| {family} | {horizon} | {radar['evaluated_count']} | {pct(radar['mean_excess_return'])} | "
                f"{pct(radar['positive_excess_rate'])} | {baseline['evaluated_count']} | "
                f"{pct(baseline['mean_excess_return'])} | {pct(baseline['positive_excess_rate'])} |"
            )
    lines += [
        "",
        "False-positive / false-negative counts are forward-excess-sign proxies only; they are not investment-error labels.",
        "Historical catalog effective-date identity is not independently proven in v0, so these statistics cannot certify historical production PIT truth or investment edge.",
        "",
    ]
    return "\n".join(lines)


def _parse_generated_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _aware(parsed)
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a frozen-universe Sector Radar historical outcome study"
    )
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--generated-at", required=True, type=_parse_generated_at)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError("historical study output path must not already exist")
    report = build_sector_radar_historical_study(
        state=load_sector_radar_market_state(args.state), generated_at=args.generated_at
    )
    args.output.mkdir(parents=True)
    (args.output / "study.json").write_text(canonical_json(report) + "\n", encoding="utf-8")
    (args.output / "summary.md").write_text(
        render_sector_radar_historical_study_markdown(report), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
