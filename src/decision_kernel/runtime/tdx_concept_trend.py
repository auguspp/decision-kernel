"""Bounded same-source Concept history; preserve the original v1 capture/replay.

The existing daily workflow adds this optional sibling to its original snapshot.
SDK acquisition is separate from pure replay. No scheduler, historical universe,
Research, investment score, or independent state owner is introduced.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, localcontext
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import re

from decision_kernel.identity import canonical_hash, canonical_json
from . import tdx_concept_snapshot as old
from .sector_radar import _return_over, _persistence, SECTOR_RADAR_MAX_WINDOW_SESSIONS

VERSION = "tdx-concept-trend-v1"
COUNT = SECTOR_RADAR_MAX_WINDOW_SESSIONS
BENCHMARK = "sh000300"
MAX_READING_BYTES = 1024 * 1024
FILES = {"capture.json", "source.json", "trend.json", "summary.md"}
PARAMS = dict(period="day", start=0, count=COUNT, adjust=None, kind="index",
              all_pages=False, batch_size=old.HISTORY_BATCH)
POLICY = dict(version=VERSION, benchmark=BENCHMARK, request=PARAMS,
              arithmetic="EXISTING_SECTOR_RETURN_AND_POSITIVE_20D_EXCESS_PERSISTENCE",
              phase_basis="DESCRIPTIVE_20D_EXCESS_NOT_INVESTMENT_SIGNAL",
              history_membership="NOT_ESTABLISHED",
              session_basis="RETURNED_BENCHMARK_SESSIONS_NOT_EXCHANGE_CALENDAR",
              custody="EXTRACTED_SDK_TIME_AND_INTEGER_CLOSE_NOT_RAW_WIRE")
PHASES = {
    "EMERGING": "20日相对强势新进入",
    "STRENGTHENING": "持续强化",
    "PERSISTENT": "持续但未进一步强化",
    "MATURE_OR_DIVERGING": "强中分歧",
    "WEAKENING_OR_EXIT": "弱化或退出",
    "NOT_POSITIVE": "尚未形成20日相对强势",
    "UNKNOWN": "阶段未知",
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def encoded(value: dict, *, limit: int = old.MAX_FILE_BYTES) -> bytes:
    raw = (canonical_json(value) + "\n").encode("utf-8")
    require(len(raw) <= limit, "TREND_BYTE_LIMIT")
    return raw


def identity(raw: bytes) -> dict:
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def _implementation() -> dict:
    root = Path(__file__).resolve().parents[1]
    return {p: sha256((root / p).read_bytes()).hexdigest() for p in
            ("identity.py", "runtime/sector_radar.py", "runtime/tdx_concept_trend.py")}


def _scope(series: dict, code: str) -> None:
    require(isinstance(series, dict) and series.get("full_code") == code
            and series.get("market_id") == (1 if code.startswith("sh") else 0)
            and type(series.get("market_id")) is int
            and series.get("period_name") == "day" and series.get("adjust_mode") == "none"
            and series.get("start") == 0 and type(series.get("start")) is int
            and series.get("request_count") == COUNT
            and type(series.get("request_count")) is int, "TREND_SERIES_IDENTITY")


def _values(series, target):
    bars = series.get("bars")
    require(isinstance(bars, list) and len(bars) <= COUNT, "TREND_HISTORY_BOUND")
    days, values = [], []
    for bar in bars:
        require(isinstance(bar, list) and len(bar) == 2 and isinstance(bar[0], str)
                and type(bar[1]) is int and 0 < bar[1] <= 10**15, "TREND_BAR_INVALID")
        clock = old._clock(bar[0])
        # SDK daily timestamps are aware; compare the market-local date, not UTC.
        day = clock.astimezone(timezone(timedelta(hours=8))).date()
        require(day <= target, "TREND_FUTURE_BAR")
        days.append(day)
        values.append(Decimal(bar[1]) / 1000)
    require(all(a < b for a, b in zip(days, days[1:])), "TREND_DUPLICATE_OR_UNORDERED_SESSION")
    require(not days or days[-1] == target, "TREND_STALE_END")
    return days, values


def _compact(series, code):
    result = {k: getattr(series, k) for k in
              ("full_code", "market_id", "period_name", "adjust_mode", "start", "request_count")}
    _scope(result, code)
    result["bars"] = [[bar.time.isoformat(), bar.close_price_milli] for bar in series.bars]
    require(len(result["bars"]) <= COUNT, "TREND_HISTORY_BOUND")
    return result


def live_source(base_source: dict, base_receipt: dict) -> dict:
    """One existing-host connection and one bounded SDK batch; no rediscovery/retry."""
    from eltdx import TdxClient
    from eltdx.hosts import DEFAULT_HOSTS
    require(version("eltdx") == old.ELTDX_VERSION, "TREND_SDK_VERSION")
    host = base_source["chosen_host"]
    require(host in DEFAULT_HOSTS, "TREND_HOST_NOT_ADOPTED")
    codes = [r["full_code"] for r in base_source["boards"]]
    require(len(codes) == len(set(codes)) and 0 < len(codes) <= old.MAX_CONCEPTS
            and BENCHMARK not in codes, "TREND_CATALOG_SCOPE")
    require(os.environ.get("ELTDX_WHEEL_SHA256") == base_source["wheel_sha256"], "TREND_WHEEL_CHANGED")
    started = datetime.now(timezone.utc)
    # Old v1 already closed its client. Reuse its exact selected host; do not
    # duplicate host probes, member preparation, snapshots, or introduce fallback.
    with TdxClient(host=host, timeout=5, probe_hosts=False, heartbeat_interval=None,
                   pool_size=4, server_count=1, connections_per_server=4) as client:
        rows = client.bars.get([*codes, BENCHMARK], **PARAMS)
        require(isinstance(rows, dict) and set(rows) == set(codes) | {BENCHMARK},
                "TREND_RESPONSE_CATALOG")
        series = {code: _compact(rows[code], code) for code in [*codes, BENCHMARK]}
    return dict(version=VERSION, policy=POLICY, package_version=old.ELTDX_VERSION,
                wheel_sha256=base_source["wheel_sha256"], chosen_host=host,
                requested_market_session=base_receipt["market_session"],
                observed_started_at=started, observed_finished_at=datetime.now(timezone.utc),
                source_batch_calls=1, requested_series=len(series), series=series)


def _phase(horizons, previous, acceleration):
    if horizons["60"] is None or previous is None or acceleration is None:
        return "UNKNOWN", "INSUFFICIENT_COMPARABLE_HISTORY"
    e20, e5 = horizons["20"]["excess_return"], horizons["5"]["excess_return"]
    if e20 > 0:
        if previous <= 0:
            return "EMERGING", "TWENTY_DAY_EXCESS_CROSSED_POSITIVE_SINCE_PREVIOUS_SESSION"
        if e5 > 0 and acceleration > 0:
            return "STRENGTHENING", "POSITIVE_5D_AND_20D_EXCESS_WITH_POSITIVE_20D_ACCELERATION"
        if e5 <= 0 or acceleration < 0:
            return "MATURE_OR_DIVERGING", "POSITIVE_20D_BUT_NONPOSITIVE_5D_OR_NEGATIVE_ACCELERATION"
        return "PERSISTENT", "POSITIVE_20D_WITHOUT_FURTHER_ACCELERATION"
    if previous > 0:
        return "WEAKENING_OR_EXIT", "TWENTY_DAY_EXCESS_EXITED_POSITIVE_STATE"
    if acceleration < 0:
        return "WEAKENING_OR_EXIT", "NONPOSITIVE_20D_EXCESS_STILL_WEAKENING_NOT_NEW_EXIT"
    return "NOT_POSITIVE", "NO_POSITIVE_20D_STATE_NOT_A_PROVEN_TREND_REVERSAL"


def build(source: dict, observation: dict, base_receipt: dict, base_source: dict) -> dict:
    """Project every original Concept; never fill gaps, drop quiet rows, or rank a subset."""
    p = observation["projection"]
    require(observation["projection_hash"] == canonical_hash(p)
            and p["version"] == old.VERSION and p["taxonomy"] == old.POLICY["taxonomy"]
            and base_receipt["status"] == "CAPTURED_TDX_CONCEPT_SNAPSHOT"
            and base_receipt["market_session"] == p["market_session"]
            and all(p.get(k) == v == base_receipt.get(k) for k, v in old.AUTHORITY.items()),
            "TREND_BASE_SCOPE")
    require(source.get("version") == VERSION and source.get("policy") == POLICY
            and source.get("package_version") == old.ELTDX_VERSION
            and source.get("wheel_sha256") == p["wheel_sha256"]
            and source.get("chosen_host") == p["chosen_host"]
            and source.get("requested_market_session") == p["market_session"]
            and type(source.get("source_batch_calls")) is int and source["source_batch_calls"] == 1, "TREND_SOURCE_SCOPE")
    require(old._clock(base_receipt["finished_at"]) <= old._clock(source["observed_started_at"])
            <= old._clock(source["observed_finished_at"]), "TREND_SOURCE_CLOCK")
    originals = {r["full_code"]: r for r in base_source["boards"]}
    require(len(originals) == len(p["observations"]) == p["catalog_count"]
            and set(originals) == {r["full_code"] for r in p["observations"]}, "TREND_ORIGINAL_CATALOG")
    series = source.get("series")
    require(isinstance(series, dict) and set(series) == set(originals) | {BENCHMARK}
            and type(source.get("requested_series")) is int and source["requested_series"] == len(series), "TREND_RESPONSE_CATALOG")
    for code, data in series.items():
        _scope(data, code)
    target = old._day(p["market_session"])
    rows, coverage = [], Counter({"5": 0, "20": 0, "60": 0})
    with localcontext(Context(prec=28)):
        dates, benchmark = _values(series[BENCHMARK], target)
        require(len(dates) >= 2, "TREND_BENCHMARK_UNAVAILABLE")
        for original in p["observations"]:
            code = original["full_code"]
            row = dict(code=original["code"], name=original["name"], full_code=code,
                       horizons={str(n): None for n in (5, 20, 60)}, phase="UNKNOWN",
                       phase_reason="INSUFFICIENT_COMPARABLE_HISTORY", gap=None)
            try:
                ds, closes = _values(series[code], target)
                require(len(ds) >= 2 and len(ds) <= len(dates) and ds == dates[-len(ds):],
                        "TREND_CALENDAR_ALIGNMENT")
                saved = {old._clock(b["time"]).astimezone(timezone(timedelta(hours=8))).date(): old._dec(b["close"])
                         for b in originals[code]["bars"]}
                recent = dict(zip(ds, closes))
                require(saved and all(recent.get(d) == close for d, close in saved.items()),
                        "TREND_ORIGINAL_SHORT_PATH_DIFFERS")
                bench = benchmark[-len(ds):]
                end = len(ds) - 1
                returns = lambda values, i, n: _return_over(values, end_index=i, sessions=n)
                for n in (5, 20, 60):
                    if len(ds) > n:
                        a, b = returns(closes, end, n), returns(bench, end, n)
                        row["horizons"][str(n)] = dict(index_return=a, benchmark_return=b, excess_return=a-b)
                history = {i: {code: returns(closes, i, 20) - returns(bench, i, 20)}
                           for i in range(20, len(ds))}
                previous = history[end-1][code] if end-1 in history else None
                acceleration = history[end][code] - history[end-5][code] if end-5 in history else None
                count, started, censored = _persistence(sessions=ds, history=history, thscode=code,
                    condition=lambda value: value > 0, first_computable_index=20) if history else (None, None, None)
                row.update(history_points=len(ds), history_start=ds[0], history_end=ds[-1],
                           previous_session=ds[-2], previous_20d_excess=previous,
                           excess_acceleration_5_sessions_20d=acceleration,
                           positive_20d_excess_persistence_sessions=count,
                           positive_20d_excess_run_started=started,
                           positive_20d_excess_persistence_left_censored=censored)
                row["phase"], row["phase_reason"] = _phase(row["horizons"], previous, acceleration)
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                row["gap"] = str(exc) if type(exc) is ValueError and re.fullmatch(r"[A-Z_]+", str(exc)) else type(exc).__name__
            if row["gap"] is not None:
                row.update(horizons={str(n): None for n in (5, 20, 60)}, phase="UNKNOWN",
                           phase_reason="REJECTED_HISTORY_NOT_CONDITION_FAILURE")
            for n in (5, 20, 60):
                coverage[str(n)] += row["horizons"][str(n)] is not None
            rows.append(row)
    payload = dict(version=VERSION, taxonomy=p["taxonomy"], kind="MARKET_EXPRESSION",
        qualification="CONTEXT_ONLY", market_session=p["market_session"],
        observation_hash=observation["projection_hash"], base_capture_hash=base_receipt["capture_hash"],
        source_hash=canonical_hash(source), source_observed_at=source["observed_finished_at"],
        benchmark=dict(full_code=BENCHMARK, name="沪深300", source="SAME_TDX_HOST",
                       history_start=dates[0], history_end=dates[-1], history_points=len(dates)),
        policy=POLICY, return_unit="FRACTION_NOT_PERCENT", catalog_count=len(rows), observations=rows,
        coverage=dict(horizons=dict(coverage), phase_rows=sum(r["phase"] != "UNKNOWN" for r in rows),
                      unavailable_rows=sum(r["gap"] is not None for r in rows)),
        phases=dict(Counter(r["phase"] for r in rows)), source_calls_during_replay=0,
        historical_universe="CURRENT_CATALOG_NOT_HISTORICAL_MEMBERSHIP",
        trend_age="POSITIVE_20D_EXCESS_RUN_WITH_LEFT_CENSOR_NOT_THEME_LIFETIME", **old.AUTHORITY)
    report = dict(projection=payload, projection_hash=canonical_hash(payload))
    encoded(report, limit=MAX_READING_BYTES)
    return json.loads(canonical_json(report))


def render(report: dict) -> str:
    p = report["projection"]
    def text(v):
        return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' ')
    def percent(v):
        return "未知" if v is None else format(Decimal(v) * 100, '.2f') + "%"
    lines = ["# 概念多周期与相对阶段", "", f"保存市场日：{p['market_session']}；同期基准：沪深300（同TDX来源）。",
             f"完整来源目录 {p['catalog_count']} 个；5/20/60日可比条目：" + '/'.join(str(p['coverage']['horizons'][str(n)]) for n in (5,20,60)) + "。",
             "阶段描述20日相对路径，不是投资信号；跑赢基准不代表绝对上涨。未取得历史不能写成条件不满足。",
             "持续天数是本窗口可见的20日超额收益为正区间，左截断不是题材真实年龄；当前目录不代表历史成分。", "",
             "| 概念 | 阶段 | 5日超额 | 20日超额 | 60日超额 | 缺口 |", "|---|---|---:|---:|---:|---|"]
    for r in p["observations"]:
        values = [percent(r["horizons"][str(n)]["excess_return"] if r["horizons"][str(n)] else None) for n in (5,20,60)]
        lines.append('| ' + ' | '.join(map(text, [r['name']+' '+r['code'], PHASES[r['phase']], *values, r['gap'] or '无已识别数据错误'])) + ' |')
    return '\n'.join(lines) + '\n'


def _files(root: Path) -> dict:
    old._safe_root(root)
    paths = list(root.iterdir())
    require(all(p.is_file() and not p.is_symlink() and p.name in FILES for p in paths), "TREND_FILE_SCOPE")
    result = {}
    for p in paths:
        raw = p.read_bytes()
        require(len(raw) <= old.MAX_FILE_BYTES, "TREND_BYTE_LIMIT")
        if p.name != 'capture.json':
            result[p.name] = identity(raw)
    return result


def capture(base, output, *, source_fn=live_source, now=lambda: datetime.now(timezone.utc)):
    observation = old.replay(base)
    receipt = json.loads((base / 'capture.json').read_bytes())
    require(receipt['status'] == 'CAPTURED_TDX_CONCEPT_SNAPSHOT', 'TREND_BASE_NOT_QUALIFIED')
    base_source = json.loads((base / 'source.json').read_bytes())
    old._safe_root(output)
    require(not output.exists(), 'TREND_CREATE_ONLY')
    output.mkdir(parents=True)
    started = old._clock(now())
    require(started >= old._clock(receipt['finished_at']), 'TREND_CAPTURE_CLOCK')
    status, reason = 'INCOMPLETE_LONG_HISTORY', None
    try:
        source = json.loads(canonical_json(source_fn(base_source, receipt)))
        require(old._clock(source['observed_started_at']) >= started
                and old._clock(source['observed_finished_at']) <= old._clock(now()), 'TREND_CAPTURE_CLOCK')
        raw = encoded(source)
        base_size = sum(p.stat().st_size for p in base.rglob('*') if p.is_file())
        require(base_size + len(raw) + MAX_READING_BYTES*2 <= old.MAX_TOTAL_BYTES, 'TREND_COMBINED_BUDGET')
        (output / 'source.json').write_bytes(raw)
        report = build(source, observation, receipt, base_source)
        (output / 'trend.json').write_bytes(encoded(report, limit=MAX_READING_BYTES))
        summary = render(report).encode()
        require(len(summary) <= MAX_READING_BYTES, "TREND_BYTE_LIMIT")
        (output / 'summary.md').write_bytes(summary)
        status = 'CAPTURED_LONG_HISTORY'
    except Exception as exc:
        # Optional source failure is retained as such; it cannot erase the v1 result.
        reason = str(exc) if type(exc) is ValueError and re.fullmatch(r'[A-Z_]+', str(exc)) else type(exc).__name__
    finished = old._clock(now())
    require(finished >= started, 'TREND_CAPTURE_CLOCK')
    cap = dict(version=VERSION, status=status, reason_code=reason, policy=POLICY,
               base_capture_hash=receipt['capture_hash'], observation_hash=observation['projection_hash'],
               workflow=receipt['workflow'], started_at=started, finished_at=finished,
               implementation=_implementation(), files=_files(output), **old.AUTHORITY)
    cap['capture_hash'] = canonical_hash(cap)
    cap_bytes = encoded(cap)
    require(sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
            + sum(p.stat().st_size for p in output.iterdir()) + len(cap_bytes)
            <= old.MAX_TOTAL_BYTES, "TREND_COMBINED_BUDGET")
    (output / 'capture.json').write_bytes(cap_bytes)
    return json.loads(canonical_json(cap))


def replay(output: Path, observation: dict, receipt: dict, base_source: dict) -> dict:
    cap = json.loads((output / 'capture.json').read_bytes())
    require(cap['version'] == VERSION and cap['policy'] == POLICY
            and cap['capture_hash'] == canonical_hash({k:v for k,v in cap.items() if k != 'capture_hash'})
            and cap['implementation'] == _implementation() and cap['files'] == _files(output)
            and cap['base_capture_hash'] == receipt['capture_hash']
            and cap['observation_hash'] == observation['projection_hash']
            and cap['workflow'] == receipt['workflow']
            and all(cap.get(k) == v for k,v in old.AUTHORITY.items()), 'TREND_CAPTURE_IDENTITY')
    require(old._clock(receipt['finished_at']) <= old._clock(cap['started_at'])
            <= old._clock(cap['finished_at']), 'TREND_CAPTURE_CLOCK')
    require(sum(v['bytes'] for v in receipt['files'].values()) + len(old._encoded(receipt))
            + sum(v['bytes'] for v in cap['files'].values()) + (output/'capture.json').stat().st_size
            <= old.MAX_TOTAL_BYTES, 'TREND_COMBINED_BUDGET')
    if cap['status'] == 'INCOMPLETE_LONG_HISTORY':
        require(bool(cap['reason_code']), 'TREND_FAILURE_REASON')
        return dict(status='INCOMPLETE_LONG_HISTORY', reason_code=cap['reason_code'])
    require(cap['status'] == 'CAPTURED_LONG_HISTORY' and cap['reason_code'] is None
            and set(cap['files']) == FILES - {'capture.json'}, 'TREND_RESULT_SCOPE')
    source = json.loads((output / 'source.json').read_bytes())
    require(old._clock(cap['started_at']) <= old._clock(source['observed_started_at'])
            <= old._clock(source['observed_finished_at']) <= old._clock(cap['finished_at']), 'TREND_CAPTURE_CLOCK')
    report = build(source, observation, receipt, base_source)
    require((output / 'trend.json').read_bytes() == encoded(report, limit=MAX_READING_BYTES)
            and (output / 'summary.md').read_bytes() == render(report).encode(), 'TREND_DERIVED_DIFFERS')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['capture', 'replay'])
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'capture':
        receipt = json.loads((args.base / 'capture.json').read_bytes())
        require(receipt['workflow'] == old.workflow_identity(dict(os.environ), os.environ['EXPECTED_CODE']),
                'TREND_EXECUTION_IDENTITY')
        result = capture(args.base, args.output)
    else:
        observation = old.replay(args.base)
        receipt = json.loads((args.base / 'capture.json').read_bytes())
        result = replay(args.output, observation, receipt, json.loads((args.base / 'source.json').read_bytes()))
    print(result.get('status', 'VERIFIED_LONG_HISTORY'))


if __name__ == '__main__':
    main()
