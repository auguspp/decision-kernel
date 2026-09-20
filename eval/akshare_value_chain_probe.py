#!/usr/bin/env python3
"""Bounded AKShare value-chain discovery probe.

Uses AKShare's existing Eastmoney futures spot/stock mapping for three categories
only. Output is candidate discovery, never DIRECT_EXPOSURE, materiality, Evidence
truth, Research admission, or investment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import akshare as ak
import pandas as pd

CATEGORIES = ("有色", "钢铁", "化工")
TARGET_TERMS = {
    "LITHIUM": ("碳酸锂", "锂"),
    "COPPER": ("铜",),
    "BLACK_CHAIN": ("螺纹钢", "钢坯", "热轧", "冷轧", "铁矿石", "焦煤", "焦炭"),
}
AUTHORITY = {
    "human_attention_authority": "NONE",
    "research_authority": "NONE",
    "investment_authority": "NONE",
    "signal_transition_authority": "NONE",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else raw(value))


def company_catalog(path: Path):
    body = path.read_bytes()
    value = json.loads(body)
    companies = value.get("projection", {}).get("companies", [])
    rows = []
    for c in companies:
        code = c.get("thscode")
        if not isinstance(code, str):
            continue
        for name in c.get("source_names", []):
            if isinstance(name, str) and len(name.strip()) >= 3:
                rows.append((name.strip(), code))
    return rows, {"bytes": len(body), "sha256": sha(body), "names": len(rows)}


def split_entities(value):
    if not isinstance(value, str) or value.strip() in {"", "-"}:
        return []
    return [x.strip() for x in value.replace("，", ",").split(",") if x.strip()]


def map_company(entity: str, catalog):
    matches = []
    for name, code in catalog:
        if name in entity or entity in name:
            matches.append({
                "external_name": entity,
                "saved_company_name": name,
                "thscode": code,
                "qualification": "VALUE_CHAIN_TEXT_MATCH_CANDIDATE_ONLY",
                "direct_exposure_established": False,
                "materiality_established": False,
            })
    return matches


def target_kinds(commodity: str):
    return [kind for kind, terms in TARGET_TERMS.items() if any(t in commodity for t in terms)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--company-reading", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    catalog, company_reading = company_catalog(args.company_reading)

    calls, selected, all_rows = [], [], []
    for category in CATEGORIES:
        start = now()
        call = {"category": category, "started_at": start, "finished_at": None,
                "status": "FAILED", "error_type": None,
                "representation": "AKSHARE_PARSED_DATAFRAME_NOT_WIRE_BYTES"}
        calls.append(call)
        try:
            frame = ak.futures_spot_stock(symbol=category)
            if not isinstance(frame, pd.DataFrame) or "商品名称" not in frame.columns:
                raise ValueError("AKSHARE_SPOT_STOCK_SHAPE_UNSUPPORTED")
            records = json.loads(frame.to_json(orient="records", force_ascii=False))
            call.update(status="PARSED_DATAFRAME_AVAILABLE", rows=len(records),
                        columns=list(frame.columns))
            write(args.output / "raw" / f"{category}.json", {
                "category": category,
                "records": records,
                "meaning": "AKSHARE_PARSED_EASTMONEY_VIEW_NOT_PRIMARY_SOURCE",
            })
            for row in records:
                commodity = str(row.get("商品名称") or "")
                record = {"category": category, **row}
                all_rows.append(record)
                kinds = target_kinds(commodity)
                if not kinds:
                    continue
                producers = split_entities(row.get("生产商"))
                downstream = split_entities(row.get("下游用户"))
                candidates = []
                for role, entities in (("PRODUCER", producers), ("DOWNSTREAM", downstream)):
                    for entity in entities:
                        for match in map_company(entity, catalog):
                            candidates.append({"role": role, **match})
                selected.append({
                    "target_kinds": kinds,
                    "category": category,
                    "commodity": commodity,
                    "latest_price": row.get("最新价格"),
                    "half_year_change": row.get("近半年涨跌幅"),
                    "producer_names": producers,
                    "downstream_names": downstream,
                    "company_candidates": candidates,
                    "direct_exposure_established": False,
                    "materiality_established": False,
                    "value_chain_direction_established": False,
                    "source_semantics": "AKSHARE_EASTMONEY_DISCOVERY_ONLY",
                    **AUTHORITY,
                })
        except Exception as exc:
            call.update(status="SOURCE_UNAVAILABLE", error_type=type(exc).__name__,
                        error_summary=str(exc)[:1200])
        finally:
            call["finished_at"] = now()

    distinct = sorted({
        (c["thscode"], c["saved_company_name"])
        for row in selected for c in row["company_candidates"]
    })
    summary = {
        "schema_version": 1,
        "semantics": "VALUE_CHAIN_COMPANY_DISCOVERY_PROBE_NOT_DIRECT_EXPOSURE",
        "generated_at": now(),
        "akshare_source_commit": "akfamily/akshare@2e13a5f2fb003d299b5c299289c318b7979986e8",
        "categories": list(CATEGORIES),
        "calls": len(calls),
        "call_successes": sum(x["status"] == "PARSED_DATAFRAME_AVAILABLE" for x in calls),
        "call_failures": sum(x["status"] != "PARSED_DATAFRAME_AVAILABLE" for x in calls),
        "all_rows": len(all_rows),
        "target_rows": len(selected),
        "candidate_mentions": sum(len(x["company_candidates"]) for x in selected),
        "distinct_saved_company_candidates": [
            {"thscode": code, "name": name} for code, name in distinct
        ],
        "company_reading": company_reading,
        "direct_exposure_established": False,
        "materiality_established": False,
        **AUTHORITY,
    }
    write(args.output / "calls.json", calls)
    write(args.output / "target-value-chain-rows.json", selected)
    write(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
