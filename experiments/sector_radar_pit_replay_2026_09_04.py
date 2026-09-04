from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from decision_kernel.adapters.hithink import (
    SHANGHAI_TZ,
    latest_completed_a_share_session,
    normalize_hithink_calendar,
)
from decision_kernel.adapters.hithink_index import (
    HithinkCompletedIndexHistory,
    HithinkIndustryCatalog,
    normalize_hithink_completed_index_history,
    normalize_hithink_industry_catalog,
)
from decision_kernel.runtime.hithink_http import (
    HITHINK_API_KEY_ENV,
    HITHINK_CALENDAR_PATH,
    _request_hithink_json,
)
from decision_kernel.runtime.hithink_index_http import (
    HITHINK_INDEX_CATALOG_PATH,
    HITHINK_INDEX_HISTORY_PATH,
)
from decision_kernel.runtime.sector_radar import (
    SECTOR_RADAR_FORMULA_VERSION,
    SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,
    SECTOR_RADAR_INVESTMENT_AUTHORITY,
    SECTOR_RADAR_SEMANTICS,
    SectorPricePoint,
    SectorPriceSeries,
    SectorRadarObservation,
    calculate_sector_radar_snapshot,
)

BENCHMARK = ("000300.SH", "沪深300")
HISTORY_START = date(2026, 1, 1)
PACE_SECONDS = float(os.environ.get("SECTOR_RADAR_HISTORY_PACE_SECONDS", "15"))
RESULT = Path("sector-radar-pit-replay.json")
SUMMARY = Path("sector-radar-pit-replay-summary.md")
PROGRESS = Path("sector-radar-pit-replay-progress.jsonl")
ERROR = Path("sector-radar-pit-replay-error.json")

GRANULAR_CODES = (
    "884002.TI", "884003.TI", "884004.TI",  # planting / forestry
    "884005.TI", "884006.TI", "884279.TI",  # fishery / aquaculture
    "884183.TI",                                # marine equipment
    "884275.TI", "884276.TI", "884277.TI",  # livestock
)
PRESSURE_CASES: Mapping[str, Mapping[str, Any]] = {
    "农业 / 种植": {
        "broad": ("881101.TI",),
        "granular": ("884002.TI", "884003.TI", "884004.TI"),
    },
    "养殖 / 猪肉 / 鸡肉": {
        "broad": ("881102.TI",),
        "granular": ("884275.TI", "884276.TI", "884277.TI"),
    },
    "水产": {
        "broad": ("881102.TI",),
        "granular": ("884005.TI", "884006.TI", "884279.TI"),
    },
    "造船 / 航海装备": {
        "broad": ("881166.TI",),
        "granular": ("884183.TI",),
        "mapping_warning": (
            "881166 军工装备 is broad context only and is not renamed shipbuilding."
        ),
    },
}


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    return value


def digest(value: Any) -> str:
    raw = json.dumps(
        jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def locator(path: str, params: Mapping[str, str]) -> str:
    query = urlencode(sorted(params.items()))
    return f"https://fuyao.aicubes.cn{path}" + (f"?{query}" if query else "")


def request(api_key: str, path: str, params: Mapping[str, str]):
    started = datetime.now(timezone.utc)
    envelope = _request_hithink_json(
        api_key=api_key,
        path=path,
        params=params,
        timeout_seconds=30.0,
    )
    completed = datetime.now(timezone.utc)
    meta = {
        "path": path,
        "params": dict(sorted(params.items())),
        "source_locator": locator(path, params),
        "request_started_at": started,
        "response_completed_at": completed,
        "duration_seconds": (completed - started).total_seconds(),
        "request_id": envelope.get("request_id"),
        "business_code": envelope.get("code"),
        "envelope_sha256": digest(envelope),
    }
    return envelope, meta


def progress(payload: Mapping[str, Any]) -> None:
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(jsonable(payload), ensure_ascii=False, sort_keys=True) + "\n")


def series_from(history: HithinkCompletedIndexHistory, name: str) -> SectorPriceSeries:
    if history.response_session != history.expected_latest_session:
        raise ValueError(f"stale history: {history.thscode}")
    return SectorPriceSeries(
        thscode=history.thscode,
        name=name,
        points=tuple(
            SectorPricePoint(
                session=point.as_of.astimezone(SHANGHAI_TZ).date(),
                close=point.close,
                turnover=point.turnover,
            )
            for point in history.points
        ),
    )


def exact_sessions(benchmark: SectorPriceSeries, others: Sequence[SectorPriceSeries]) -> None:
    expected = tuple(point.session for point in benchmark.points)
    if len(expected) < 61:
        raise ValueError("benchmark has fewer than 61 sessions")
    for item in others:
        actual = tuple(point.session for point in item.points)
        if actual != expected:
            raise ValueError(
                f"history sessions differ for {item.thscode}; "
                f"missing={sorted(set(expected) - set(actual))[:3]}; "
                f"extra={sorted(set(actual) - set(expected))[:3]}"
            )


def ret(closes: Sequence[Decimal], end: int, sessions: int) -> Decimal:
    return closes[end] / closes[end - sessions] - Decimal(1)


def avg(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def trace_row(item: SectorRadarObservation) -> dict[str, Any]:
    return {
        "as_of_session": item.as_of_session,
        "horizon_5": item.horizon_5,
        "horizon_20": item.horizon_20,
        "horizon_60": item.horizon_60,
        "rank_change_5_sessions_20d": item.rank_change_5_sessions_20d,
        "excess_acceleration_5_sessions_20d": item.excess_acceleration_5_sessions_20d,
        "positive_20d_excess_persistence_sessions": (
            item.positive_20d_excess_persistence_sessions
        ),
        "positive_20d_excess_run_started": item.positive_20d_excess_run_started,
        "top_quartile_20d_persistence_sessions": (
            item.top_quartile_20d_persistence_sessions
        ),
        "top_quartile_20d_run_started": item.top_quartile_20d_run_started,
        "turnover_pulse_5_vs_prior_20": item.turnover_pulse_5_vs_prior_20,
    }


def first(trace: Sequence[Mapping[str, Any]], predicate):
    return next((row for row in trace if predicate(row)), None)


def milestones(trace: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "first_positive_20d_excess": first(
            trace, lambda row: row["horizon_20"]["excess_return"] > 0
        ),
        "first_top_quartile_20d": first(
            trace, lambda row: row["horizon_20"]["cross_sectional_rating"] >= 75
        ),
        "first_top_decile_20d": first(
            trace, lambda row: row["horizon_20"]["cross_sectional_rating"] >= 90
        ),
        "first_five_session_positive_run": first(
            trace,
            lambda row: row["positive_20d_excess_persistence_sessions"] >= 5,
        ),
        "first_ten_session_top_quartile_run": first(
            trace,
            lambda row: row["top_quartile_20d_persistence_sessions"] >= 10,
        ),
        "first_top_quartile_with_1_2x_turnover": first(
            trace,
            lambda row: (
                row["horizon_20"]["cross_sectional_rating"] >= 75
                and row["turnover_pulse_5_vs_prior_20"] is not None
                and row["turnover_pulse_5_vs_prior_20"] >= Decimal("1.2")
            ),
        ),
    }


def granular_trace(series: SectorPriceSeries, benchmark: SectorPriceSeries):
    sessions = tuple(point.session for point in benchmark.points)
    sector_close = tuple(point.close for point in series.points)
    benchmark_close = tuple(point.close for point in benchmark.points)
    turnover = tuple(point.turnover for point in series.points)
    rows = []
    positive_run = 0
    for end in range(60, len(sessions)):
        sector_20 = ret(sector_close, end, 20)
        benchmark_20 = ret(benchmark_close, end, 20)
        excess_20 = sector_20 - benchmark_20
        positive_run = positive_run + 1 if excess_20 > 0 else 0
        prior_turnover = avg(turnover[end - 24 : end - 4])
        recent_turnover = avg(turnover[end - 4 : end + 1])
        rows.append(
            {
                "as_of_session": sessions[end],
                "horizon_5": {
                    "sector_return": ret(sector_close, end, 5),
                    "benchmark_return": ret(benchmark_close, end, 5),
                    "excess_return": (
                        ret(sector_close, end, 5) - ret(benchmark_close, end, 5)
                    ),
                },
                "horizon_20": {
                    "sector_return": sector_20,
                    "benchmark_return": benchmark_20,
                    "excess_return": excess_20,
                },
                "horizon_60": {
                    "sector_return": ret(sector_close, end, 60),
                    "benchmark_return": ret(benchmark_close, end, 60),
                    "excess_return": (
                        ret(sector_close, end, 60) - ret(benchmark_close, end, 60)
                    ),
                },
                "positive_20d_excess_persistence_sessions": positive_run,
                "turnover_pulse_5_vs_prior_20": (
                    None if prior_turnover == 0 else recent_turnover / prior_turnover
                ),
                "rank_semantics": "NO_BROAD_RANK_GRANULAR_DRILL_DOWN_ONLY",
            }
        )
    return rows


def controls(snapshots, sectors, benchmark):
    sessions = tuple(point.session for point in benchmark.points)
    benchmark_close = tuple(point.close for point in benchmark.points)
    one_day = []
    for series in sectors:
        closes = tuple(point.close for point in series.points)
        for end in range(60, len(sessions) - 5):
            one_day.append(
                {
                    "thscode": series.thscode,
                    "name": series.name,
                    "as_of_session": sessions[end],
                    "one_day_excess_return": (
                        ret(closes, end, 1) - ret(benchmark_close, end, 1)
                    ),
                    "forward_5d_excess_outcome_only": (
                        closes[end + 5] / closes[end] - Decimal(1)
                        - (
                            benchmark_close[end + 5] / benchmark_close[end]
                            - Decimal(1)
                        )
                    ),
                }
            )
    one_day.sort(
        key=lambda row: (
            row["one_day_excess_return"], row["as_of_session"], row["thscode"]
        ),
        reverse=True,
    )

    benchmark_weakness = []
    fading = []
    for snapshot in snapshots:
        for item in snapshot.observations:
            if item.horizon_20.sector_return < 0 < item.horizon_20.excess_return:
                benchmark_weakness.append(
                    {
                        "thscode": item.thscode,
                        "name": item.name,
                        "as_of_session": item.as_of_session,
                        "sector_20d_return": item.horizon_20.sector_return,
                        "benchmark_20d_return": item.horizon_20.benchmark_return,
                        "excess_20d_return": item.horizon_20.excess_return,
                        "20d_rating": item.horizon_20.cross_sectional_rating,
                        "turnover_pulse_5_vs_prior_20": item.turnover_pulse_5_vs_prior_20,
                    }
                )
            if (
                item.horizon_60.cross_sectional_rating >= 75
                and item.horizon_20.cross_sectional_rating >= 75
                and item.horizon_5.cross_sectional_rating < 50
                and item.rank_change_5_sessions_20d < 0
            ):
                fading.append(
                    {
                        "thscode": item.thscode,
                        "name": item.name,
                        "as_of_session": item.as_of_session,
                        "5d_rating": item.horizon_5.cross_sectional_rating,
                        "20d_rating": item.horizon_20.cross_sectional_rating,
                        "60d_rating": item.horizon_60.cross_sectional_rating,
                        "rank_change_5_sessions_20d": item.rank_change_5_sessions_20d,
                        "excess_acceleration_5_sessions_20d": (
                            item.excess_acceleration_5_sessions_20d
                        ),
                    }
                )
    benchmark_weakness.sort(
        key=lambda row: (
            row["excess_20d_return"], row["as_of_session"], row["thscode"]
        ),
        reverse=True,
    )
    fading.sort(
        key=lambda row: (row["as_of_session"], row["20d_rating"], row["thscode"]),
        reverse=True,
    )
    return {
        "largest_one_day_events": one_day[:30],
        "benchmark_weakness_examples": benchmark_weakness[:30],
        "fading_leader_examples": fading[:30],
        "narrow_leadership_status": (
            "NOT_ASSERTED: historical constituent membership is unavailable; "
            "current constituents are not backfilled."
        ),
    }


def pct(value: Any) -> str:
    return "NA" if value is None else f"{Decimal(str(value)):+.1%}"


def ratio(value: Any) -> str:
    return "NA" if value is None else f"{Decimal(str(value)):.2f}x"


def summary_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# Sector Discovery Radar — frozen-PIT replay",
        "",
        f"- Captured: `{result['captured_at']}`",
        f"- Latest session: `{result['latest_completed_session']}`",
        f"- Broad universe: `{result['catalog']['broad_count']}` exact `881*.TI` industries",
        f"- Replay snapshots: `{result['replay']['snapshot_count']}`",
        f"- History calls: `{result['acquisition']['history_request_count']}`; retries `0`; pace `{result['acquisition']['history_pace_seconds']}`s",
        "- Human attention authority: `NONE`",
        "- Investment authority: `NONE`",
        "",
        "## Current 20-session broad cross-section",
        "",
        "| Rank | Industry | 5d excess | 20d excess | 60d excess | Rating | Positive run | Turnover |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["current_broad_cross_section"][:15]:
        lines.append(
            f"| {row['horizon_20']['cross_sectional_rank']} | {row['name']} `{row['thscode']}` | "
            f"{pct(row['horizon_5']['excess_return'])} | "
            f"{pct(row['horizon_20']['excess_return'])} | "
            f"{pct(row['horizon_60']['excess_return'])} | "
            f"{row['horizon_20']['cross_sectional_rating']} | "
            f"{row['positive_20d_excess_persistence_sessions']} | "
            f"{ratio(row['turnover_pulse_5_vs_prior_20'])} |"
        )

    lines.extend(["", "## Human pressure cases", ""])
    broad = result["replay"]["broad_pressure_traces"]
    granular = result["replay"]["granular_pressure_traces"]
    for label, mapping in result["pressure_cases"].items():
        lines.append(f"### {label}")
        if mapping.get("mapping_warning"):
            lines.append(f"> {mapping['mapping_warning']}")
        for code in mapping.get("broad", []):
            trace = broad[code]
            row = trace["current"]
            milestone = trace["milestones"]["first_top_quartile_20d"]
            lines.append(
                f"- `{code} {trace['name']}`: 20d excess "
                f"{pct(row['horizon_20']['excess_return'])}, rating "
                f"{row['horizon_20']['cross_sectional_rating']}, positive run "
                f"{row['positive_20d_excess_persistence_sessions']} sessions; first "
                f"top-quartile milestone "
                f"{milestone['as_of_session'] if milestone else 'not reached'}"
            )
        for code in mapping.get("granular", []):
            trace = granular[code]
            row = trace["current"]
            lines.append(
                f"- `{code} {trace['name']}` drill-down: 20d excess "
                f"{pct(row['horizon_20']['excess_return'])}, positive run "
                f"{row['positive_20d_excess_persistence_sessions']} sessions, turnover "
                f"{ratio(row['turnover_pulse_5_vs_prior_20'])}; no broad rank"
            )
        lines.append("")

    lines.extend(
        [
            "## Retained controls",
            "",
            f"- Largest one-day moves + separate T+5 outcomes: `{len(result['controls']['largest_one_day_events'])}`",
            f"- Positive relative / negative absolute 20d examples: `{len(result['controls']['benchmark_weakness_examples'])}`",
            f"- Long-horizon leaders with short-horizon fading: `{len(result['controls']['fading_leader_examples'])}`",
            "- Historical narrow-leadership is not asserted without historical membership.",
            "",
            "Descriptive milestones are replay diagnostics, not alert thresholds. No detector, lifecycle state, Research route, recommendation, action, or investment authority is created.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    if PACE_SECONDS < 0:
        raise ValueError("pace must be non-negative")
    api_key = os.environ.get(HITHINK_API_KEY_ENV)
    if not api_key:
        raise ValueError(f"{HITHINK_API_KEY_ENV} is required")

    captured_at = datetime.now(timezone.utc)
    calendar_envelope, calendar_meta = request(api_key, HITHINK_CALENDAR_PATH, {})
    calendar = normalize_hithink_calendar(calendar_envelope)
    latest = latest_completed_a_share_session(calendar, observed_at=captured_at)
    progress({"stage": "calendar", "latest_session": latest, **calendar_meta})

    catalog_envelope, catalog_meta = request(
        api_key, HITHINK_INDEX_CATALOG_PATH, {"tag": "industry"}
    )
    catalog: HithinkIndustryCatalog = normalize_hithink_industry_catalog(catalog_envelope)
    identity = {item.thscode: item for item in catalog.identities}
    if len(catalog.broad_industries) != 90:
        raise ValueError(
            f"expected current 90-member 881 family, got {len(catalog.broad_industries)}"
        )
    missing = sorted(set(GRANULAR_CODES) - set(identity))
    if missing:
        raise ValueError(f"granular targets missing from catalog: {missing}")
    progress(
        {
            "stage": "catalog",
            "catalog_hash": catalog.catalog_hash,
            "broad_count": len(catalog.broad_industries),
            "granular_count": len(catalog.granular_industries),
            **catalog_meta,
        }
    )

    requested = [(BENCHMARK[0], BENCHMARK[1], "BENCHMARK")]
    requested += [
        (item.thscode, item.name, "BROAD_881") for item in catalog.broad_industries
    ]
    requested += [
        (code, identity[code].name, "GRANULAR_884") for code in GRANULAR_CODES
    ]
    if len(requested) != len({row[0] for row in requested}):
        raise ValueError("duplicate history request identity")

    start = datetime.combine(HISTORY_START, datetime.min.time(), tzinfo=SHANGHAI_TZ)
    end = datetime.combine(
        latest + timedelta(days=1), datetime.min.time(), tzinfo=SHANGHAI_TZ
    )
    common = {
        "interval": "1d",
        "start": str(int(start.timestamp() * 1000)),
        "end": str(int(end.timestamp() * 1000)),
    }

    histories = {}
    frozen_inputs = []
    for index, (code, name, family) in enumerate(requested):
        if index and PACE_SECONDS:
            time.sleep(PACE_SECONDS)
        envelope, meta = request(
            api_key, HITHINK_INDEX_HISTORY_PATH, {"thscode": code, **common}
        )
        history = normalize_hithink_completed_index_history(
            envelope, thscode=code, sessions=calendar, observed_at=captured_at
        )
        if history.response_session != latest:
            raise ValueError(f"history is stale for {code}: {history.response_session}")
        histories[code] = history
        frozen_inputs.append(
            {
                "thscode": code,
                "name": name,
                "family": family,
                **meta,
                "response_session": history.response_session,
                "expected_latest_session": history.expected_latest_session,
                "points": history.points,
            }
        )
        progress(
            {
                "stage": "history",
                "index": index + 1,
                "total": len(requested),
                "thscode": code,
                "name": name,
                "family": family,
                "point_count": len(history.points),
                **meta,
            }
        )
        print(
            f"HISTORY {index + 1}/{len(requested)} {code} {name} "
            f"points={len(history.points)}",
            flush=True,
        )

    benchmark = series_from(histories[BENCHMARK[0]], BENCHMARK[1])
    broad_series = tuple(
        series_from(histories[item.thscode], item.name)
        for item in catalog.broad_industries
    )
    granular_series = tuple(
        series_from(histories[code], identity[code].name) for code in GRANULAR_CODES
    )
    exact_sessions(benchmark, (*broad_series, *granular_series))

    sessions = tuple(point.session for point in benchmark.points)
    snapshots = []
    for as_of in sessions[60:]:
        snapshot = calculate_sector_radar_snapshot(
            sectors=broad_series, benchmark=benchmark, as_of_session=as_of
        )
        if len(snapshot.observations) != 90 or snapshot.exclusions:
            raise ValueError(
                f"broad replay lost coverage at {as_of}: "
                f"observations={len(snapshot.observations)} "
                f"exclusions={len(snapshot.exclusions)}"
            )
        snapshots.append(snapshot)

    broad_codes = sorted(
        {code for case in PRESSURE_CASES.values() for code in case.get("broad", ())}
        | {"881103.TI"}
    )
    broad_traces = {}
    for code in broad_codes:
        rows = []
        for snapshot in snapshots:
            by_code = {item.thscode: item for item in snapshot.observations}
            rows.append(trace_row(by_code[code]))
        broad_traces[code] = {
            "name": identity[code].name,
            "milestone_semantics": "DESCRIPTIVE_ONLY_NOT_ALERT_RULES",
            "milestones": milestones(rows),
            "current": rows[-1],
            "trace": rows,
        }

    granular_traces = {}
    for item in granular_series:
        rows = granular_trace(item, benchmark)
        granular_traces[item.thscode] = {
            "name": item.name,
            "current": rows[-1],
            "trace": rows,
        }

    current = snapshots[-1]
    result = {
        "schema_version": 1,
        "captured_at": captured_at,
        "latest_completed_session": latest,
        "source": "HiThink Financial-API index daily market data",
        "benchmark": {"thscode": BENCHMARK[0], "name": BENCHMARK[1]},
        "formula_version": SECTOR_RADAR_FORMULA_VERSION,
        "catalog": {
            **catalog_meta,
            "catalog_hash": catalog.catalog_hash,
            "identity_count": len(catalog.identities),
            "broad_count": len(catalog.broad_industries),
            "granular_count": len(catalog.granular_industries),
            "unexpected_count": len(catalog.unexpected_industries),
            "broad_identities": catalog.broad_industries,
            "granular_targets": [identity[code] for code in GRANULAR_CODES],
        },
        "acquisition": {
            "request_count": 2 + len(requested),
            "history_request_count": len(requested),
            "history_pace_seconds": PACE_SECONDS,
            "retry_count": 0,
            "history_start": HISTORY_START,
            "history_end": latest,
            "calendar": calendar_meta,
            "frozen_history_inputs": frozen_inputs,
        },
        "pressure_cases": PRESSURE_CASES,
        "replay": {
            "snapshot_count": len(snapshots),
            "first_replay_session": snapshots[0].as_of_session,
            "last_replay_session": snapshots[-1].as_of_session,
            "broad_universe_count": len(broad_series),
            "broad_pressure_traces": broad_traces,
            "granular_pressure_traces": granular_traces,
        },
        "current_broad_cross_section": current.observations,
        "controls": controls(snapshots, broad_series, benchmark),
        "radar_semantics": SECTOR_RADAR_SEMANTICS,
        "replay_semantics": "FROZEN_PIT_RETROSPECTIVE_PRICE_PATH_REPLAY_ONLY",
        "milestone_semantics": "DESCRIPTIVE_ONLY_NOT_PRODUCTION_ALERT_RULES",
        "human_attention_authority": SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,
        "investment_authority": SECTOR_RADAR_INVESTMENT_AUTHORITY,
        "explicit_non_authorities": (
            "NO_DETECTOR",
            "NO_LIFECYCLE_STATE",
            "NO_RESEARCH_ROUTE",
            "NO_RECOMMENDATION",
            "NO_ACTION",
        ),
    }
    RESULT.write_text(
        json.dumps(jsonable(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    normalized = json.loads(RESULT.read_text(encoding="utf-8"))
    SUMMARY.write_text(summary_markdown(normalized), encoding="utf-8")
    print(f"RESULT={RESULT}")
    print(f"SUMMARY={SUMMARY}")
    print(f"BROAD_UNIVERSE={len(broad_series)}")
    print(f"REPLAY_SNAPSHOTS={len(snapshots)}")
    print("HUMAN_ATTENTION_AUTHORITY=NONE")
    print("INVESTMENT_AUTHORITY=NONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        ERROR.write_text(
            json.dumps(
                {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "progress_path": str(PROGRESS),
                    "human_attention_authority": "NONE",
                    "investment_authority": "NONE",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
