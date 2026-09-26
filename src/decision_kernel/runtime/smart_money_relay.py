"""Replayable Tushare Relay supplement for the existing Smart Money capture.

The primary HiThink/FTShare/Eastmoney/HKEX history remains unchanged.  Relay
rows are retained beside it with their own source identity and explicit gaps.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

from ..identity import canonical_hash
from . import smart_money_capture as primary
from . import smart_money_sources as s
from . import tushare_relay as relay
from . import smart_money_relay_contract as table_contract

VERSION = "smart-money-relay-supplement-v1"
APIS = ("hm_list", "hm_detail", "report_rc", "top_list", "top_inst")
AUTHORITY = {**s.AUTHORITY, "source_role": "SECONDARY_SUPPLEMENT_NOT_PRIMARY_REPLACEMENT"}
MAX_RAW = 20 * 1024 * 1024

def plan(market_session: str | None) -> list[dict]:
    if market_session is None:
        return []
    day = s.day(market_session).strftime("%Y%m%d")
    return [
        {"api": "hm_list", "params": {"__probe": "0", "limit": "5000"},
         "meaning": "VENDOR_HOT_MONEY_DIRECTORY_NOT_PERSON_IDENTITY"},
        {"api": "hm_detail", "params": {"trade_date": day, "limit": "5000"},
         "meaning": "VENDOR_HOT_MONEY_DETAIL_NOT_COMPLETE_HOLDING"},
        {"api": "report_rc", "params": {"report_date": day, "limit": "5000"},
         "meaning": "STRUCTURED_BROKER_FORECAST_CONTEXT_NOT_MODEL_TRUTH"},
        {"api": "top_list", "params": {"trade_date": day, "limit": "5000"},
         "meaning": "DRAGON_TIGER_CROSSCHECK_NOT_ACTOR_CERTIFICATION"},
        {"api": "top_inst", "params": {"trade_date": day, "limit": "5000"},
         "meaning": "INSTITUTIONAL_SEAT_CROSSCHECK_NOT_IDENTIFIABLE_FUND"},
    ]

def _manifest_hash(value: dict) -> str:
    return canonical_hash({k: v for k, v in value.items() if k != "capture_hash"})

def capture(output: Path, identity: dict, market_session: str | None, *,
            request=relay.request, clock=relay.now) -> dict:
    primary.validate_identity(identity)
    output = Path(output)
    s.require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)),
              "OUTPUT_EXISTS_OR_SYMLINK")
    output.mkdir(parents=True)
    started = clock()
    specs = plan(market_session)
    records = []
    raw_total = 0
    credential = os.environ.get(relay.SECRET_ENV, "")
    for index, spec in enumerate(specs):
        if not credential:
            records.append({"index": index, "spec": spec, "status": "CREDENTIAL_UNAVAILABLE",
                            "attempts": []})
            continue
        result = request(spec["api"], spec["params"], key=credential, clock=clock)
        attempts = []
        for attempt in result["attempts"]:
            raw = attempt.get("raw")
            item = {k: deepcopy(v) for k, v in attempt.items() if k != "raw"}
            if raw is not None:
                s.require(isinstance(raw, bytes) and len(raw) <= relay.MAX_BODY, "RELAY_BODY_SIZE")
                raw_total += len(raw)
                s.require(raw_total <= MAX_RAW, "RELAY_TOTAL_SIZE")
                name = f"raw-{index:02d}-{attempt['attempt']}.json"
                (output / name).write_bytes(raw)
                item.update(body=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
            else:
                item.update(body=None, bytes=None, sha256=None)
            attempts.append(item)
        records.append({"index": index, "spec": spec, "status": result["status"],
                        "attempts": attempts})
    manifest = {"version": VERSION, "identity": identity, "market_session": market_session,
                "started_at": started, "finished_at": clock(), "records": records,
                "authority": AUTHORITY, "relay_host": relay.PRO,
                "retry_wait_seconds": relay.RETRY_WAIT_SECONDS}
    manifest["capture_hash"] = _manifest_hash(manifest)
    (output / "capture.json").write_bytes(s.encoded(manifest))
    files = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
    result = replay(files, identity=identity, cutoff=manifest["finished_at"])
    compact={k:deepcopy(v) for k,v in result.items() if k!="families"}
    compact["families"]={api:{k:deepcopy(v) for k,v in item.items() if k!="rows"}
                         for api,item in result["families"].items()}
    (output / "summary.json").write_bytes(s.encoded(compact))
    (output / "summary.md").write_text(render(result), encoding="utf-8")
    return result

def _validate_attempt(item: dict, files: dict[str, bytes], *, first, finish):
    required = {"attempt", "http_status", "requested_at", "received_at", "headers",
                "classification", "business_code", "business_error", "business_msg",
                "body", "bytes", "sha256"}
    s.require(set(item) == required, "RELAY_ATTEMPT_FIELDS")
    requested, received = s.clock(item["requested_at"]), s.clock(item["received_at"])
    s.require(first <= requested <= received <= finish, "RELAY_CLOCKS")
    if item["body"] is None:
        s.require(item["bytes"] is None and item["sha256"] is None, "RELAY_BODY_RECEIPT")
        return None
    raw = files[item["body"]]
    s.require(len(raw) == item["bytes"] and sha256(raw).hexdigest() == item["sha256"],
              "RELAY_BODY_IDENTITY")
    if item["classification"] == "MALFORMED_RESPONSE":
        try:
            relay.decode(raw)
        except relay.RelayError as exc:
            s.require(str(exc) == item["business_error"], "RELAY_MALFORMED_REASON")
            return None
        raise s.SourceError("RELAY_MALFORMED_BECAME_VALID")
    body = relay.decode(raw)
    expected = relay.classify(item["http_status"], body)
    s.require(expected == item["classification"], "RELAY_CLASSIFICATION")
    return s.decode(raw)

def replay(files: dict[str, bytes], *, identity: dict, cutoff: str) -> dict:
    s.require("capture.json" in files, "RELAY_CAPTURE_MISSING")
    manifest = s.decode(files["capture.json"])
    s.require(manifest.get("version") == VERSION and manifest.get("authority") == AUTHORITY,
              "RELAY_CAPTURE_VERSION")
    primary.validate_identity(manifest["identity"])
    s.require(manifest["identity"] == identity and manifest.get("relay_host") == relay.PRO,
              "RELAY_CAPTURE_IDENTITY")
    s.require(manifest.get("retry_wait_seconds") == relay.RETRY_WAIT_SECONDS, "RELAY_RETRY_POLICY")
    s.require(manifest.get("capture_hash") == _manifest_hash(manifest), "RELAY_CAPTURE_HASH")
    begin, finish = s.clock(manifest["started_at"]), s.clock(manifest["finished_at"])
    s.require(begin <= finish <= s.clock(cutoff), "RELAY_CAPTURE_CLOCK")
    expected = plan(manifest.get("market_session"))
    records = manifest.get("records")
    s.require(isinstance(records, list) and len(records) == len(expected), "RELAY_RECORD_COUNT")
    expected_files = {"capture.json"}
    families = {}
    unresolved = []
    for index, (record, spec) in enumerate(zip(records, expected, strict=True)):
        s.require(record.get("index") == index and record.get("spec") == spec, "RELAY_PLAN_DIFFERS")
        attempts = record.get("attempts")
        s.require(isinstance(attempts, list) and len(attempts) <= 2, "RELAY_ATTEMPTS")
        bodies = []
        for attempt_no, item in enumerate(attempts, 1):
            s.require(item.get("attempt") == attempt_no, "RELAY_ATTEMPT_ORDER")
            body = _validate_attempt(item, files, first=begin, finish=finish)
            if item.get("body") is not None:
                expected_files.add(item["body"])
            bodies.append(body)
        status = record.get("status")
        if not attempts:
            s.require(status == "CREDENTIAL_UNAVAILABLE", "RELAY_EMPTY_ATTEMPT_STATUS")
            rows = []
        else:
            s.require(status == attempts[-1]["classification"], "RELAY_FINAL_STATUS")
            rows = []
        interpretation = None
        interpretation_error = None
        if status == "SUCCESS":
            try:
                interpretation = table_contract.qualify(
                    bodies[-1], spec, received_at=attempts[-1]["received_at"])
                rows = interpretation["rows"]
            except s.SourceError as exc:
                interpretation_error = str(exc)
            if interpretation_error or interpretation["issues"]:
                unresolved.append({"api": spec["api"], "status": "SOURCE_INTERPRETATION_GAP",
                                   "business_error": interpretation_error,
                                   "issues": interpretation["issues"] if interpretation else []})
        if status != "SUCCESS":
            unresolved.append({"api": spec["api"], "status": status,
                               "business_error": attempts[-1].get("business_error") if attempts else status})
        source_fields = sorted({key for row in rows
                                for key in ("source", "provider", "data_source")
                                if row.get(key) not in (None, "")})
        families[spec["api"]] = {"status": status, "rows": rows, "row_count": len(rows),
                                 "meaning": spec["meaning"], "source_fields_present": source_fields,
                                 "interpretation": ({k: v for k, v in interpretation.items()
                                                     if k not in {"rows", "row_count"}}
                                                    if interpretation else None),
                                 "interpretation_error": interpretation_error,
                                 "attempts": [{k: v for k, v in a.items()
                                               if k not in {"body", "bytes", "sha256"}}
                                              for a in attempts]}
    s.require(expected_files == set(files) - {"summary.json", "summary.md"}, "RELAY_FILE_SCOPE")
    succeeded = sum(v["interpretation"] is not None for v in families.values())
    overall = ("NO_COMPLETED_SESSION" if not families
               else "READY" if succeeded == len(families) and not unresolved
               else "PARTIAL_WITH_EXPLICIT_GAPS" if succeeded
               else "UNAVAILABLE_NOT_QUIET")
    return {"version": VERSION, "status": overall,
            "interpretation_revision": table_contract.REVISION,
            "market_session": manifest.get("market_session"), "cutoff": manifest["finished_at"],
            "relay_host": relay.PRO, "families": families, "unresolved": unresolved,
            "capture_hash": manifest["capture_hash"], "identity": identity, **AUTHORITY}

def render(result: dict) -> str:
    lines = ["## Tushare Relay 补充来源", "",
             f"状态 {result['status']}；市场日 {result.get('market_session') or 'UNKNOWN'}；"
             f"取得截止 {result['cutoff']}。第三方中转，不是官方Tushare或聪明钱评分。", "",
             "| 接口 | 取得状态 | 解析行数 | 日期/身份合格行数 |", "|---|---|---:|---:|"]
    for api in APIS:
        item = result["families"].get(api)
        if item:
            qualified = (item.get("interpretation") or {}).get("qualified_row_count", "UNKNOWN")
            lines.append(f"| {api} | {item['status']} | {item['row_count']} | {qualified} |")
    if result["unresolved"]:
        lines += ["", "缺口：" + "；".join(f"{x['api']}={x['status']}"
                                           for x in result["unresolved"])]
    lines += ["", "临时排队/业务 timeout 只等待30秒再试一次；仍失败留到下一自然运行。",
              "合格只指所收单页的日期/身份解释，不代表全市场、全部分页或经济正确；空结果不是没有行为。",
              "完整字段、来源声明、逐行缺口及原件定位见 [补充原件解释](smart-money/relay.json)。",
              "Relay 行为与既有 HiThink/FTShare/Eastmoney/HKEX 来源并列，不静默替代。", ""]
    return "\n".join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    primary_files = {p.name: p.read_bytes() for p in args.source_capture.iterdir() if p.is_file()}
    manifest = s.decode(primary_files["capture.json"])
    identity = manifest["identity"]
    observation = primary.replay(primary_files, identity, cutoff=relay.now())
    market_session = max(observation["trading_sessions"], default=None)
    result = capture(args.output, identity, market_session)
    print(json.dumps({k: result[k] for k in ("status", "market_session", "capture_hash", "unresolved")},
                     ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
