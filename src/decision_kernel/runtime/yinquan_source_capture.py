"""One-shot, bounded YinQuan study source capture. No DAT or trading in GitHub.

Exactly 14 fixed symbols, 2023-01-01 through 2026-09-30, Tushare Relay
daily + daily_basic. Existing authenticated HTTP transport; no retry/fallback.
Actual supplier vintage is a current historical retrieval, NOT historical PIT.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re

from . import tushare_relay as relay

VERSION = "yinquan-one-shot-source-v1"
SYMBOLS = (
    "000001.SZ", "000002.SZ", "000006.SZ", "000007.SZ",
    "000008.SZ", "000009.SZ", "000010.SZ", "000099.SZ",
    "000151.SZ", "000155.SZ", "600395.SH", "600397.SH",
    "603551.SH", "603580.SH",
)
START, END, LIMIT = "20230101", "20260930", "1800"
DAILY = "ts_code,trade_date,open,high,low,close,vol,amount"
BASIC = "ts_code,trade_date,turnover_rate"
MAX_CALLS, MAX_TOTAL_BYTES = 28, 24 * 1024 * 1024
REQUIRED = {
    "daily": set(DAILY.split(",")),
    "daily_basic": set(BASIC.split(",")),
}

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def plan():
    result = []
    for symbol in SYMBOLS:
        for api, fields in (("daily", DAILY), ("daily_basic", BASIC)):
            result.append({"api": api, "params": {"ts_code": symbol,
                "start_date": START, "end_date": END, "fields": fields,
                "limit": LIMIT}})
    require(len(result) == MAX_CALLS and len(set(SYMBOLS)) == len(SYMBOLS), "PLAN")
    return result

def day(raw):
    require(isinstance(raw, str) and re.fullmatch(r"\d{8}", raw), "BAD_DATE")
    value = date.fromisoformat(raw[:4] + "-" + raw[4:6] + "-" + raw[6:])
    require(START <= raw <= END, "DATE_OUT_OF_WINDOW")
    return value.isoformat()

def decimal(raw, *, positive=False, nullable=False):
    if raw is None and nullable:
        return None
    require(type(raw) in (str, int, float, Decimal) and not isinstance(raw, bool), "NUM_TYPE")
    try:
        v = Decimal(str(raw))
    except InvalidOperation as exc:
        raise ValueError("NUM_INVALID") from exc
    require(v.is_finite() and len(v.as_tuple().digits) <= 32 and
            (v > 0 if positive else v >= 0), "NUM_RANGE")
    return str(v)

def rows(raw, spec):
    obj = relay.decode(raw)
    require(obj.get("code") == 0 and obj.get("ok") is not False and
            obj.get("error") in (None, "") and
            obj.get("api_name", spec["api"]) == spec["api"], "PROVIDER_STATUS")
    body = obj.get("data")
    require(isinstance(body, dict), "DATA_ENVELOPE")
    fields = body.get("fields")
    require(isinstance(fields, list) and len(fields) == len(set(fields)) and
            REQUIRED[spec["api"]] <= set(fields), "REQUIRED_FIELDS")
    for holder in (obj, body):
        for k in ("has_more", "has_next", "truncated"):
            require(holder.get(k) in (None, False), "PAGINATION_UNKNOWN")
        for k in ("next", "next_page", "next_cursor"):
            require(holder.get(k) in (None, ""), "PAGINATION_UNKNOWN")
    result = relay.rows(obj)
    require(len(result) < int(LIMIT), "POSSIBLY_TRUNCATED")
    for holder in (obj, body):
        for k in ("count", "total"):
            if k in holder:
                require(type(holder[k]) is int and holder[k] == len(result), "COUNT_MISMATCH")
    out = {}
    for entry in result:
        require(entry.get("ts_code") == spec["params"]["ts_code"], "SYMBOL_MISMATCH")
        d = day(entry.get("trade_date"))
        require(d not in out, "DUPLICATE_DATE")
        keys = ("open", "high", "low", "close", "vol", "amount") if spec["api"] == "daily" else ("turnover_rate",)
        row = {k: decimal(entry.get(k), positive=k in ("open", "high", "low", "close"),
                         nullable=k == "turnover_rate") for k in keys}
        if spec["api"] == "daily":
            lo, hi, o, c = (Decimal(row[k]) for k in ("low", "high", "open", "close"))
            require(lo <= o <= hi and lo <= c <= hi, "BAD_OHLC")
        out[d] = row
    return out

def normalized(raw_by_index):
    csvs, summary = {}, []
    specs = plan()
    for i, symbol in enumerate(SYMBOLS):
        bars = rows(raw_by_index[2*i], specs[2*i])
        hsl = rows(raw_by_index[2*i+1], specs[2*i+1])
        require(set(hsl) <= set(bars), "UNMATCHED_BASIC_DATE")
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("date", "open", "high", "low", "close", "turnover_rate", "code"))
        for d in sorted(bars):
            bar = bars[d]
            writer.writerow((d, bar["open"], bar["high"], bar["low"], bar["close"],
                             hsl.get(d, {}).get("turnover_rate") or "", symbol))
        csvs[symbol[:6] + ".csv"] = out.getvalue().encode("utf-8")
        summary.append({"symbol": symbol, "price_rows": len(bars), "hsl_rows": len(hsl),
                        "matched_hsl": sum(hsl.get(d, {}).get("turnover_rate") is not None for d in bars),
                        "first": min(bars) if bars else None, "last": max(bars) if bars else None,
                        "empty_is_no_trading": False})
    return csvs, summary

def _write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")) + "\n", encoding="utf-8")

def identity(env):
    require(env.get("GITHUB_REPOSITORY") == "auguspp/decision-kernel" and
            env.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and
            env.get("GITHUB_REF") == "refs/heads/main" and
            env.get("GITHUB_RUN_ATTEMPT") == "1" and
            re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", "")) and
            env.get("EXPECTED_CODE") == env["GITHUB_SHA"] and
            re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")),
            "EXECUTION_IDENTITY")
    return {k: env[k] for k in ("GITHUB_REPOSITORY", "GITHUB_EVENT_NAME",
        "GITHUB_REF", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_RUN_ID")}

def capture(root, env, *, transport=None):
    root = Path(root)
    require(not root.exists() and not root.is_symlink() and
            not any(p.is_symlink() for p in root.parents), "OUTPUT_EXISTS_OR_SYMLINK")
    run_identity = identity(env)
    credential = env.get(relay.SECRET_ENV, "")
    require(isinstance(credential, str) and len(credential) >= 8 and
            credential.isascii() and all(32 < ord(c) < 127 for c in credential),
            "SOURCE_AUTH_UNAVAILABLE")
    root.mkdir(parents=True)
    (root / "raw").mkdir()
    (root / "prices").mkdir()
    transport = transport or relay._http_get  # Existing no-redirect, bounded HTTP; no retry.
    report = {"version": VERSION, "workflow": run_identity, "provider": "THIRD_PARTY_TUSHARE_RELAY",
              "window": [START, END], "plan": plan(), "calls": [], "status": "INCOMPLETE",
              "max_calls": MAX_CALLS, "max_raw_bytes": MAX_TOTAL_BYTES,
              "automatic_retry": False, "fallback": False,
              "source_historical_pit": "NOT_ESTABLISHED", "investment_authority": "NONE"}
    _write(root / "receipt.json", report)
    total, raw_map = 0, {}
    for i, spec in enumerate(plan()):
        record = {"index": i, **spec, "status": "REQUEST_STARTED", "raw_file": None}
        report["calls"].append(record)
        _write(root / "receipt.json", report)
        try:
            p = relay._params(spec["api"], spec["params"])
            response = transport(spec["api"], p, credential)
            require(isinstance(response, dict) and
                    set(response) == {"http_status", "raw", "requested_at", "received_at", "headers"}, "TRANSPORT_SHAPE")
            raw = response["raw"]
            require(isinstance(raw, bytes) and 0 < len(raw) <= relay.MAX_BODY and
                    total + len(raw) <= MAX_TOTAL_BYTES, "SOURCE_BYTE_BUDGET")
            total += len(raw)
            filename = "raw/" + str(i + 1).zfill(2) + "-" + spec["api"] + "-" + spec["params"]["ts_code"] + ".json"
            (root / filename).write_bytes(raw)
            record.update(raw_file=filename, sha256=sha256(raw).hexdigest(),
                          bytes=len(raw), http_status=response["http_status"],
                          requested_at=response["requested_at"], received_at=response["received_at"])
            require(response["http_status"] == 200, "HTTP_NOT_SUCCESS")
            rows(raw, spec)
            raw_map[i] = raw
            record["status"] = "VALIDATED"
        except Exception as exc:
            record["status"] = "SOURCE_OR_SCHEMA_STOP"
            record["error_type"] = type(exc).__name__
            report["status"] = "STOPPED_AT_" + str(i)
            _write(root / "receipt.json", report)
            break
        _write(root / "receipt.json", report)
    if len(raw_map) == MAX_CALLS:
        csvs, summary = normalized(raw_map)
        for name, raw in csvs.items():
            (root / "prices" / name).write_bytes(raw)
        report["coverage"] = summary
        report["price_sha256"] = {name: sha256(raw).hexdigest() for name, raw in csvs.items()}
        report["status"] = "COMPLETE_SOURCE_CAPTURE_NOT_PIT"
        _write(root / "receipt.json", report)
    return report

def verify(root):
    root = Path(root)
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents) and
            all(not p.is_symlink() for p in root.rglob("*")), "SOURCE_PATH_SYMLINK")
    report = json.loads((root / "receipt.json").read_bytes())
    require(report["version"] == VERSION and report["plan"] == plan() and
            report["provider"] == "THIRD_PARTY_TUSHARE_RELAY" and
            report["max_calls"] == MAX_CALLS and report["max_raw_bytes"] == MAX_TOTAL_BYTES and
            report["automatic_retry"] is False and report["fallback"] is False,
            "RECEIPT_SCOPE")
    calls, collected, total = report["calls"], {}, 0
    require(1 <= len(calls) <= MAX_CALLS, "CALL_COUNT")
    for i, item in enumerate(calls):
        require(item["index"] == i and {k: item[k] for k in ("api", "params")} == plan()[i],
                "CALL_ORDER")
        if item["raw_file"] is None:
            require(i == len(calls) - 1 and item["status"] == "SOURCE_OR_SCHEMA_STOP",
                    "MISSING_BODY_SCOPE")
            continue
        path = item["raw_file"]
        require(path == "raw/" + str(i + 1).zfill(2) + "-" + item["api"] + "-" +
                item["params"]["ts_code"] + ".json", "RAW_PATH")
        raw = (root / path).read_bytes()
        total += len(raw)
        require(len(raw) == item["bytes"] and sha256(raw).hexdigest() == item["sha256"] and
                len(raw) <= relay.MAX_BODY and total <= MAX_TOTAL_BYTES, "RAW_HASH_OR_BUDGET")
        if item["status"] == "VALIDATED":
            require(item["http_status"] == 200, "HTTP_STATUS")
            rows(raw, plan()[i])
            collected[i] = raw
        else:
            require(i == len(calls) - 1 and item["status"] == "SOURCE_OR_SCHEMA_STOP",
                    "STOP_ORDER")
    if report["status"] == "COMPLETE_SOURCE_CAPTURE_NOT_PIT":
        require(len(collected) == MAX_CALLS, "FALSE_COMPLETE")
        csvs, coverage = normalized(collected)
        require(report["coverage"] == coverage and report["price_sha256"] ==
                {name: sha256(data).hexdigest() for name, data in csvs.items()},
                "NORMALIZATION_RECEIPT")
        for name, data in csvs.items():
            require((root / "prices" / name).read_bytes() == data, "CSV_REPLAY_DIFFERENCE")
    else:
        require(report["status"] == "STOPPED_AT_" + str(len(calls)-1) and
                not any((root / "prices").iterdir()), "FALSE_PARTIAL")
    expected = {"receipt.json"} | {item["raw_file"] for item in calls if item["raw_file"]}
    if report["status"] == "COMPLETE_SOURCE_CAPTURE_NOT_PIT":
        expected |= {"prices/" + name for name in report["price_sha256"]}
    require({p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == expected,
            "INVENTORY_MISMATCH")
    return {"status": "OFFLINE_REPLAY_EXACT", "source_calls_during_verify": 0,
            "capture_status": report["status"], "source_call_count": len(calls),
            "raw_sha256_count": len([x for x in calls if x["raw_file"]])}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("capture", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "capture":
        result = capture(args.output, os.environ)
        print(json.dumps({"status": result["status"], "calls": len(result["calls"])}))
        return 0 if result["status"] == "COMPLETE_SOURCE_CAPTURE_NOT_PIT" else 1
    print(json.dumps(verify(args.output)))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
