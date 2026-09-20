#!/usr/bin/env python3
"""Bounded Industry Inflection source-reuse probe.

Uses the repository's existing HiThink HTTP transport for LC/CU/RB futures data.
Computes transparent time-series observations plus an optional ruptures PELT shadow.
No composite score, economic-exposure claim, Research routing, or investment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import ruptures as rpt

from decision_kernel.runtime import hithink_http

TARGETS = ("LC", "CU", "RB")
END_DATE = "2026-09-18"
START_DATE = "2026-08-01"
SHANGHAI = ZoneInfo("Asia/Shanghai")
ENDPOINTS = {
    "varieties": "/api/futures/varieties/list",
    "prices": "/api/futures/prices/daily",
    "basis": "/api/futures/basis/historical",
    "warehouse": "/api/futures/warehouse-receipts/historical",
    "positions": "/api/futures/positions/variety-daily",
}
AUTHORITY = {
    "human_attention_authority": "NONE",
    "research_authority": "NONE",
    "investment_authority": "NONE",
    "signal_transition_authority": "NONE",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def raw(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else raw(value))


def envelope_data(value):
    if not isinstance(value, dict) or value.get("code") != 0 or not isinstance(value.get("data"), dict):
        raise ValueError("HITHINK_ENVELOPE_NOT_SUCCESS")
    return value["data"]


class Recorder:
    def __init__(self, output: Path, api_key: str):
        self.output = output
        self.api_key = api_key
        self.rows = []
        self.number = 0

    def get(self, label: str, path: str, params: dict[str, str]):
        self.number += 1
        requested_at = now()
        record = {
            "sequence": self.number,
            "label": label,
            "path": path,
            "params": params,
            "requested_at": requested_at,
            "received_at": None,
            "status": "FAILED",
            "representation": "DECODED_JSON_TOOL_RETURN_NOT_WIRE_BYTES",
            "response_file": None,
            "response_sha256": None,
            "error_type": None,
            "error_summary": None,
        }
        self.rows.append(record)
        try:
            value = hithink_http._request_hithink_json(
                api_key=self.api_key, path=path, params=params, timeout_seconds=20.0)
            received_at = now()
            body = raw(value)
            name = f"{self.number:02d}-{label}.json"
            write(self.output / "raw" / name, body)
            record.update(
                received_at=received_at,
                status="CAPTURED_DECODED_RESPONSE",
                response_file="raw/" + name,
                response_sha256=sha(body),
                response_bytes=len(body),
            )
            return value
        except Exception as exc:
            record.update(
                received_at=now(),
                status="SOURCE_UNAVAILABLE",
                error_type=type(exc).__name__,
                error_summary=str(exc)[:1200],
            )
            return None


def item_list(envelope):
    data = envelope_data(envelope)
    items = data.get("item")
    if not isinstance(items, list):
        raise ValueError("HITHINK_ITEM_LIST_MISSING")
    return data, items


def price_points(envelope):
    data, items = item_list(envelope)
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        stamp, close = item.get("timestamp"), item.get("close_price")
        if not isinstance(stamp, (int, float)) or isinstance(stamp, bool) or not isinstance(close, (int, float)) or isinstance(close, bool):
            continue
        dt = datetime.fromtimestamp(float(stamp) / 1000, tz=timezone.utc).astimezone(SHANGHAI)
        rows.append({
            "date": dt.date().isoformat(),
            "timestamp": int(stamp),
            "close": float(close),
            "volume": item.get("volume"),
            "turnover": item.get("turnover"),
        })
    rows.sort(key=lambda x: x["timestamp"])
    if len({x["timestamp"] for x in rows}) != len(rows):
        raise ValueError("DUPLICATE_PRICE_TIMESTAMP")
    return rows


def dated_numeric(items, field: str):
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        date, value = item.get("date"), item.get(field)
        if isinstance(date, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
            rows.append((date, float(value)))
    rows.sort()
    return rows


def ret(values: list[float], periods: int):
    return None if len(values) <= periods or values[-periods-1] == 0 else values[-1] / values[-periods-1] - 1


def linear_slope(values: list[float]):
    if len(values) < 3:
        return None
    xbar = (len(values) - 1) / 2
    ybar = statistics.fmean(values)
    denom = sum((i - xbar) ** 2 for i in range(len(values)))
    if denom == 0 or ybar == 0:
        return None
    slope = sum((i - xbar) * (v - ybar) for i, v in enumerate(values)) / denom
    return slope / abs(ybar)


def pelt_shadow(points: list[tuple[str, float]], *, label: str):
    if len(points) < 20:
        return {
            "series": label,
            "status": "NOT_ENOUGH_OBSERVATIONS",
            "observations": len(points),
            "breakpoints": [],
            "truth_claim": False,
        }
    values = np.asarray([v for _, v in points], dtype=float)
    std = float(values.std())
    if not math.isfinite(std) or std == 0:
        return {
            "series": label,
            "status": "CONSTANT_OR_INVALID_SERIES",
            "observations": len(points),
            "breakpoints": [],
            "truth_claim": False,
        }
    normalized = (values - values.mean()) / std
    penalty = 3.0 * math.log(len(values))
    bkps = rpt.Pelt(model="l2", min_size=5, jump=1).fit(normalized).predict(pen=penalty)
    internal = [int(i) for i in bkps if int(i) < len(points)]
    return {
        "series": label,
        "status": "SHADOW_CHANGEPOINTS_COMPUTED",
        "algorithm": "ruptures.Pelt",
        "model": "l2",
        "min_size": 5,
        "jump": 1,
        "penalty": penalty,
        "observations": len(points),
        "breakpoints": [{"index": i, "first_post_break_date": points[i][0]} for i in internal],
        "terminal_sentinel_omitted": True,
        "truth_claim": False,
    }


def transparent_features(price_rows, basis_items, warehouse_items, position):
    closes = [x["close"] for x in price_rows]
    last20 = closes[-20:]
    current5 = ret(closes, 5)
    prior5 = None
    if len(closes) >= 11 and closes[-11] != 0:
        prior5 = closes[-6] / closes[-11] - 1
    basis = dated_numeric(basis_items, "close_basis_rate")
    warehouse = dated_numeric(warehouse_items, "amount")
    changes = []
    if current5 is not None:
        changes.append({"metric": "PRICE_RETURN_5_OBS", "value": current5})
    r20 = ret(closes, 20)
    if r20 is not None:
        changes.append({"metric": "PRICE_RETURN_20_OBS", "value": r20})
    if current5 is not None and prior5 is not None:
        changes.append({"metric": "PRICE_5_OBS_ACCELERATION", "value": current5 - prior5,
                        "current_5": current5, "previous_5": prior5})
    slope = linear_slope(last20)
    if slope is not None:
        changes.append({"metric": "PRICE_NORMALIZED_SLOPE_LAST_20", "value": slope})
    if len(basis) >= 2:
        changes.append({"metric": "CLOSE_BASIS_RATE_FIRST_TO_LAST_CHANGE",
                        "value": basis[-1][1] - basis[0][1],
                        "first": {"date": basis[0][0], "value": basis[0][1]},
                        "last": {"date": basis[-1][0], "value": basis[-1][1]}})
    if len(warehouse) >= 2:
        changes.append({"metric": "WAREHOUSE_AMOUNT_FIRST_TO_LAST_CHANGE",
                        "value": warehouse[-1][1] - warehouse[0][1],
                        "first": {"date": warehouse[0][0], "value": warehouse[0][1]},
                        "last": {"date": warehouse[-1][0], "value": warehouse[-1][1]}})
    if isinstance(position, dict):
        for key in ("volume_change", "long_position_change", "short_position_change",
                    "net_position_change", "main_change_ratio"):
            value = position.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                changes.append({"metric": "POSITION_" + key.upper(), "value": float(value)})
    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    key = os.environ.get(hithink_http.HITHINK_API_KEY_ENV, "")
    if not key:
        raise SystemExit("configured HiThink credential required")

    recorder = Recorder(args.output, key)
    varieties_env = recorder.get("varieties", ENDPOINTS["varieties"], {})
    positions_env = recorder.get("positions-20260918", ENDPOINTS["positions"], {"date": END_DATE})
    targets, gaps = {}, []
    if varieties_env is not None:
        try:
            _, items = item_list(varieties_env)
            by_code = {str(x.get("variety_code", "")).upper(): x for x in items if isinstance(x, dict)}
            for code in TARGETS:
                row = by_code.get(code)
                thscode = row.get("main_contract_thscode") if isinstance(row, dict) else None
                if not isinstance(thscode, str) or not thscode:
                    gaps.append({"target": code, "reason": "MAIN_CONTRACT_NOT_AVAILABLE_FROM_VARIETIES"})
                else:
                    targets[code] = {"variety": row, "main_contract_thscode": thscode}
        except ValueError as exc:
            gaps.append({"target": "ALL", "reason": str(exc)})
    else:
        gaps.append({"target": "ALL", "reason": "VARIETIES_SOURCE_UNAVAILABLE"})

    position_by_code = {}
    if positions_env is not None:
        try:
            _, items = item_list(positions_env)
            position_by_code = {str(x.get("variety_code", "")).upper(): x for x in items if isinstance(x, dict)}
        except ValueError as exc:
            gaps.append({"target": "POSITIONS", "reason": str(exc)})

    observations = []
    for code in TARGETS:
        target = targets.get(code)
        if target is None:
            continue
        contract = target["main_contract_thscode"]
        price_env = recorder.get(f"{code}-prices", ENDPOINTS["prices"], {"thscode": contract})
        basis_env = recorder.get(f"{code}-basis", ENDPOINTS["basis"], {"thscode": contract})
        warehouse_env = recorder.get(
            f"{code}-warehouse", ENDPOINTS["warehouse"],
            {"thscode": contract, "start_date": START_DATE, "end_date": END_DATE})
        source_status = {
            "prices": "AVAILABLE" if price_env is not None else "SOURCE_UNAVAILABLE",
            "basis": "AVAILABLE" if basis_env is not None else "SOURCE_UNAVAILABLE",
            "warehouse": "AVAILABLE" if warehouse_env is not None else "SOURCE_UNAVAILABLE",
            "positions": "AVAILABLE" if code in position_by_code else "SOURCE_UNAVAILABLE",
        }
        if price_env is None:
            gaps.append({"target": code, "reason": "PRICE_SOURCE_UNAVAILABLE"})
            observations.append({
                "variety_code": code, "main_contract_thscode": contract,
                "source_status": source_status, "transparent_features": [],
                "changepoint_shadow": [], "industry_inflection_truth_accepted": False, **AUTHORITY})
            continue
        try:
            price_rows = price_points(price_env)
            if not price_rows:
                raise ValueError("NO_QUALIFIED_PRICE_POINTS")
            basis_items = item_list(basis_env)[1] if basis_env is not None else []
            warehouse_items = item_list(warehouse_env)[1] if warehouse_env is not None else []
            position = position_by_code.get(code)
            features = transparent_features(price_rows, basis_items, warehouse_items, position)
            price_series = [(x["date"], x["close"]) for x in price_rows]
            warehouse_series = dated_numeric(warehouse_items, "amount")
            shadow = [pelt_shadow(price_series, label="DAILY_CLOSE")]
            if warehouse_series:
                shadow.append(pelt_shadow(warehouse_series, label="WAREHOUSE_AMOUNT"))
            observations.append({
                "variety_code": code,
                "variety_name": target["variety"].get("name"),
                "exchange_code": target["variety"].get("exchange_code"),
                "main_contract_thscode": contract,
                "price_window": {"first": price_rows[0]["date"], "last": price_rows[-1]["date"],
                                 "observations": len(price_rows)},
                "basis_observations": len(basis_items),
                "warehouse_observations": len(warehouse_items),
                "position_date": position.get("date") if isinstance(position, dict) else None,
                "source_status": source_status,
                "transparent_features": features,
                "changepoint_shadow": shadow,
                "industry_inflection_truth_accepted": False,
                "direct_company_exposure_established": False,
                "materiality_established": False,
                **AUTHORITY,
            })
        except ValueError as exc:
            gaps.append({"target": code, "reason": str(exc)})
            observations.append({
                "variety_code": code, "main_contract_thscode": contract,
                "source_status": source_status, "transparent_features": [],
                "changepoint_shadow": [], "industry_inflection_truth_accepted": False, **AUTHORITY})

    summary = {
        "schema_version": 1,
        "semantics": "HITHINK_FUTURES_CHANGE_OBSERVATION_PROBE_NOT_INDUSTRY_INFLECTION_TRUTH",
        "generated_at": now(),
        "official_contract": "HiThink-Tech/Financial-API@0a629aba2b3977a419f7c4330972d2047c8612da",
        "ruptures_contract": "deepcharles/ruptures@ee1c8ff8a548d54c641b2bb471562165931f31c7",
        "targets": list(TARGETS),
        "resolved_targets": sorted(targets),
        "requests": len(recorder.rows),
        "request_successes": sum(x["status"] == "CAPTURED_DECODED_RESPONSE" for x in recorder.rows),
        "request_failures": sum(x["status"] != "CAPTURED_DECODED_RESPONSE" for x in recorder.rows),
        "observations": len(observations),
        "gaps": gaps,
        "akshare_used": False,
        "composite_score_computed": False,
        "industry_inflection_truth_accepted": False,
        **AUTHORITY,
    }
    write(args.output / "requests.json", recorder.rows)
    write(args.output / "industry-observations.json", observations)
    write(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
