"""Replayable Tushare Relay supplement for the existing Smart Money capture.

The primary HiThink/FTShare/Eastmoney/HKEX history remains unchanged.  Relay
rows are retained beside it with their own source identity and explicit gaps.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
import re
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

def plan(market_session: str | None, *, revision: int = 1, as_of: str | None = None,
         reports_only: bool = False) -> list[dict]:
    s.require(type(reports_only) is bool and (not reports_only or revision == 3), "RELAY_REPORT_SCOPE")
    if market_session is None:
        return []
    day = s.day(market_session).strftime("%Y%m%d")
    specs = [
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
    s.require(type(revision) is int and revision in {1, 2, 3}, "RELAY_PLAN_REVISION")
    if revision >= 2:
        end = s.day(as_of)
        specs[0]["params"]["limit"] = "1000"
        specs[1]["params"]["limit"] = "2000"
        specs[2]["params"] = {"start_date": (end - timedelta(days=6)).strftime("%Y%m%d"),
                              "end_date": end.strftime("%Y%m%d"), "limit": "3000"}
    if revision == 3:
        # This relay rejects a range without report_date. Preserve the same
        # seven-day objective using seven independently qualified daily pages.
        reports = [{**specs[2], "params": {
            "report_date": (end - timedelta(days=i)).strftime("%Y%m%d"),
            "limit": "3000"}} for i in range(7)]
        specs = reports if reports_only else specs[:2] + reports + specs[3:]
    return specs


def source_binding(observation: dict) -> dict:
    """Exact already-qualified primary calendar, never a fresh calendar request."""
    primary.validate_identity(observation["identity"])
    sessions = observation["trading_sessions"]
    s.require(isinstance(sessions, list) and sessions == sorted(set(sessions)), "RELAY_SOURCE_SESSIONS")
    for session in sessions:
        s.day(session)
    return {"identity": deepcopy(observation["identity"]),
            "capture_hash": observation["capture_hash"], "cutoff": observation["cutoff"],
            "trading_sessions": list(sessions)}


def validate_binding(binding: dict, market_session: str | None, started_at: str) -> None:
    s.require(isinstance(binding, dict) and set(binding) ==
              {"identity", "capture_hash", "cutoff", "trading_sessions"}, "RELAY_SOURCE_BINDING")
    primary.validate_identity(binding["identity"])
    s.require(isinstance(binding["capture_hash"], str) and
              re.fullmatch(r"[0-9a-f]{64}", binding["capture_hash"]), "RELAY_SOURCE_HASH")
    sessions = binding["trading_sessions"]
    s.require(isinstance(sessions, list) and sessions == sorted(set(sessions)) and
              max(sessions, default=None) == market_session, "RELAY_SOURCE_SESSIONS")
    cutoff = s.clock(binding["cutoff"])
    s.require(cutoff <= s.clock(started_at), "RELAY_SOURCE_FUTURE")
    for session in sessions:
        s.require(s.day(session) <= cutoff.astimezone(s.ZONE).date(), "RELAY_SOURCE_SESSION_FUTURE")


def service_stop(record: dict) -> str | None:
    """Caller-wide stop from recorded refusals; the existing HTTP client stays unchanged."""
    if record["status"] in {"CREDENTIAL_UNAVAILABLE", "REQUEST_RECEIPT_UNAVAILABLE"}:
        return record["status"]
    for attempt in record["attempts"]:
        if attempt.get("http_status") in {401, 403, 429}:
            return "HTTP_" + str(attempt["http_status"])
        if attempt.get("classification") in {"AUTH_OR_ENTITLEMENT", "RATE_LIMIT"}:
            return attempt["classification"]
        error = attempt.get("business_error")
        if error in ("unauthorized", "forbidden", "rate_limited", "ip_rate_limited"):
            return "SERVICE_REFUSAL"
    return None


def _manifest_hash(value: dict) -> str:
    return canonical_hash({k: v for k, v in value.items() if k != "capture_hash"})

def capture(output: Path, identity: dict, market_session: str | None, *,
            request=relay.request, clock=relay.now, revision: int = 1,
            source_capture: dict | None = None, reports_only: bool = False) -> dict:
    s.require(type(reports_only) is bool and (not reports_only or revision == 3), "RELAY_REPORT_SCOPE")
    if revision in {2, 3}:
        return capture_checkpointed(output, identity, market_session, source_capture,
                                    request=request, clock=clock, revision=revision, reports_only=reports_only)
    s.require(revision == 1, "RELAY_PLAN_REVISION")
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


def capture_checkpointed(output, identity, market_session, source_capture, *, request, clock,
                         revision=2, reports_only=False):
    primary.validate_identity(identity)
    output = Path(output)
    s.require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)),
              "OUTPUT_EXISTS_OR_SYMLINK")
    started = clock()
    validate_binding(source_capture, market_session, started)
    as_of = s.clock(started).astimezone(s.ZONE).date().isoformat()
    specs = plan(market_session, revision=revision, as_of=as_of, reports_only=reports_only)
    output.mkdir(parents=True)
    records = [{"index": index, "spec": spec, "status": "NOT_ATTEMPTED", "attempts": []}
               for index, spec in enumerate(specs)]
    manifest = {"version": VERSION, "plan_revision": revision, "identity": identity,
                "market_session": market_session, "as_of_date": as_of,
                "source_capture": source_capture, "started_at": started,
                "finished_at": started, "records": records, "execution_complete": False,
                "authority": AUTHORITY, "relay_host": relay.PRO,
                "retry_wait_seconds": relay.RETRY_WAIT_SECONDS}
    if revision == 3:
        manifest["reports_only"] = reports_only
    def checkpoint():
        manifest["finished_at"] = clock()
        manifest["capture_hash"] = _manifest_hash(manifest)
        temp = output / ".capture.json.tmp"
        temp.write_bytes(s.encoded(manifest))
        temp.replace(output / "capture.json")
    checkpoint()
    credential = os.environ.get(relay.SECRET_ENV, "")
    total = 0
    stop = None
    for index, spec in enumerate(specs):
        if stop:
            records[index]["status"] = "NOT_ATTEMPTED_SERVICE_STOP"
            checkpoint()
            continue
        if not credential:
            records[index]["status"] = "CREDENTIAL_UNAVAILABLE"
        else:
            try:
                result = request(spec["api"], spec["params"], key=credential, clock=clock)
                s.require(result["api"] == spec["api"] and result["params"] == spec["params"],
                          "RELAY_REQUEST_RECEIPT_IDENTITY")
                s.require(isinstance(result["attempts"], list) and 1 <= len(result["attempts"]) <= 2,
                          "RELAY_REQUEST_ATTEMPTS")
                s.require(all(type(a.get("attempt")) is int and a["attempt"] == number
                              for number, a in enumerate(result["attempts"], 1)), "RELAY_REQUEST_ATTEMPT_ORDER")
                attempts = []
                bodies = []
                next_total = total
                for attempt in result["attempts"]:
                    raw = attempt.get("raw")
                    item = {k: deepcopy(v) for k, v in attempt.items() if k != "raw"}
                    if raw is not None:
                        s.require(isinstance(raw, bytes) and len(raw) <= relay.MAX_BODY, "RELAY_BODY_SIZE")
                        next_total += len(raw)
                        s.require(next_total <= MAX_RAW, "RELAY_TOTAL_SIZE")
                        name = f"raw-{index:02d}-{attempt['attempt']}.json"
                        item.update(body=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
                        bodies.append((name, raw))
                    else:
                        item.update(body=None, bytes=None, sha256=None)
                    attempts.append(item)
                record = {"index": index, "spec": spec, "status": result["status"], "attempts": attempts}
                # Do not persist reflected credentials in allowed response headers
                # or business metadata; there is no new request implementation.
                encoded = s.encoded(record)
                s.require(credential.encode() not in encoded and
                          all(credential.encode() not in raw for _, raw in bodies), "RELAY_RETENTION_REFLECTION")
                for name, raw in bodies:
                    (output / name).write_bytes(raw)
                total = next_total
                records[index] = record
            except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                # A missing receipt does not prove no HTTP attempt occurred.
                # Never invent attempt counts or serialize the exception text.
                records[index] = {"index": index, "spec": spec,
                                  "status": "REQUEST_RECEIPT_UNAVAILABLE", "attempts": [],
                                  "receipt_error_type": type(exc).__name__}
        stop = service_stop(records[index])
        checkpoint()
    manifest["execution_complete"] = True
    checkpoint()
    files = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
    result = replay(files, identity=identity, cutoff=manifest["finished_at"])
    compact = {k: deepcopy(v) for k, v in result.items() if k != "families"}
    compact["families"] = {api: {k: deepcopy(v) for k, v in item.items() if k != "rows"}
                           for api, item in result["families"].items()}
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
    revision = manifest.get("plan_revision", 1)
    s.require(type(revision) is int and revision in {1, 2, 3}, "RELAY_PLAN_REVISION")
    if revision >= 2:
        validate_binding(manifest["source_capture"], manifest.get("market_session"), manifest["started_at"])
        s.require(manifest["as_of_date"] == begin.astimezone(s.ZONE).date().isoformat(), "RELAY_ASOF_DATE")
        s.require(type(manifest.get("execution_complete")) is bool, "RELAY_EXECUTION_MARKER")
    reports_only = manifest.get("reports_only", False)
    if revision == 3:
        s.require(type(manifest.get("reports_only")) is bool, "RELAY_REPORT_SCOPE")
    else:
        s.require("reports_only" not in manifest, "RELAY_LEGACY_SCOPE")
    expected = plan(manifest.get("market_session"), revision=revision,
                    as_of=manifest.get("as_of_date"), reports_only=reports_only)
    records = manifest.get("records")
    s.require(isinstance(records, list) and len(records) == len(expected), "RELAY_RECORD_COUNT")
    expected_files = {"capture.json"}
    families = {}
    report_pages = []
    unresolved = []
    stopped = None
    not_started = False
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
            allowed = {"CREDENTIAL_UNAVAILABLE"}
            if revision >= 2:
                allowed |= {"REQUEST_RECEIPT_UNAVAILABLE", "NOT_ATTEMPTED", "NOT_ATTEMPTED_SERVICE_STOP"}
            s.require(status in allowed, "RELAY_EMPTY_ATTEMPT_STATUS")
            rows = []
        else:
            s.require(status == attempts[-1]["classification"], "RELAY_FINAL_STATUS")
            rows = []
        if revision >= 2:
            if stopped:
                s.require(not attempts and status in {"NOT_ATTEMPTED_SERVICE_STOP", "NOT_ATTEMPTED"},
                          "RELAY_REQUEST_AFTER_SERVICE_STOP")
            elif not_started:
                s.require(not attempts and status == "NOT_ATTEMPTED", "RELAY_NONCONTIGUOUS_CHECKPOINT")
            else:
                s.require(status != "NOT_ATTEMPTED_SERVICE_STOP", "RELAY_STOP_WITHOUT_REFUSAL")
            stopped = stopped or service_stop(record)
            not_started = not_started or status == "NOT_ATTEMPTED"
            if manifest["execution_complete"]:
                s.require(status != "NOT_ATTEMPTED", "RELAY_COMPLETE_WITH_UNATTEMPTED")
        first_gap = len(unresolved)
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
        item = {"status": status, "rows": rows, "row_count": len(rows),
                                 "meaning": spec["meaning"], "source_fields_present": source_fields,
                                 "interpretation": ({k: v for k, v in interpretation.items()
                                                     if k not in {"rows", "row_count"}}
                                                    if interpretation else None),
                                 "interpretation_error": interpretation_error,
                                 "receipt_error_type": record.get("receipt_error_type"),
                                 "recorded_http_attempt_count": (None if status == "REQUEST_RECEIPT_UNAVAILABLE"
                                                                 else len(attempts)),
                                 "attempts": [{k: v for k, v in a.items()
                                               if k not in {"body", "bytes", "sha256"}}
                                              for a in attempts]}
        if revision == 3 and spec["api"] == "report_rc":
            report_pages.append({"request_index": index,
                                 "report_date": spec["params"]["report_date"], **item})
            for gap in unresolved[first_gap:]:
                gap["report_date"] = spec["params"]["report_date"]
        else:
            families[spec["api"]] = item
    if report_pages:
        families["report_rc"] = combine_report_pages(report_pages)
    s.require(expected_files == set(files) - {"summary.json", "summary.md"}, "RELAY_FILE_SCOPE")
    if revision >= 2 and not manifest["execution_complete"]:
        unresolved.append({"api":"execution", "status":"CAPTURE_CHECKPOINT_NOT_FINAL"})
    succeeded = sum(v["interpretation"] is not None for v in families.values())
    overall = ("NO_COMPLETED_SESSION" if not families
               else "READY" if succeeded == len(families) and not unresolved
               else "PARTIAL_WITH_EXPLICIT_GAPS" if succeeded
               else "UNAVAILABLE_NOT_QUIET")
    result = {"version": VERSION, "status": overall,
            "plan_revision": revision, "source_capture": manifest.get("source_capture"),
            "execution_complete": manifest.get("execution_complete"),
            "as_of_date": manifest.get("as_of_date"),
            "interpretation_revision": table_contract.REVISION,
            "market_session": manifest.get("market_session"), "cutoff": manifest["finished_at"],
            "relay_host": relay.PRO, "families": families, "unresolved": unresolved,
            "capture_hash": manifest["capture_hash"], "identity": identity, **AUTHORITY}
    if revision == 3:
        result["reports_only"] = reports_only
    return result


def combine_report_pages(pages):
    """Concatenate dated pages, preserving offsets and independent failures.

    Each retained record is still a report/target-period row, not a unique
    report or a confirmed revision. No page's count is a market denominator.
    """
    rows, metadata, qualified, origins = [], [], [], []
    for page in pages:
        offset = len(rows)
        rows.extend(page["rows"])
        metadata.append({**{k: v for k, v in page.items() if k != "rows"}, "row_offset": offset})
        interpretation = page["interpretation"] or {}
        qualified.extend(offset + i for i in interpretation.get("qualified_row_indexes", []))
        origins.extend({"request_index": page["request_index"], "row_index": i,
                        "report_date": page["report_date"]} for i in range(page["row_count"]))
    interpreted = [p for p in pages if p["interpretation"] is not None]
    complete = all(p["status"] == "SUCCESS" and p["interpretation"] is not None for p in pages)
    issues = [{"report_date": p["report_date"], "status": p["status"],
               "interpretation_error": p["interpretation_error"],
               "issues": (p["interpretation"] or {}).get("issues", [])}
              for p in pages if p["status"] != "SUCCESS" or p["interpretation"] is None
              or p["interpretation"]["issues"]]
    counts = [p["recorded_http_attempt_count"] for p in pages]
    return {"status": "SUCCESS" if complete else "PARTIAL_DAILY_PAGES" if interpreted
            else "UNAVAILABLE_DAILY_PAGES", "rows": rows, "row_count": len(rows),
            "meaning": pages[0]["meaning"], "pages": metadata, "row_origins": origins,
            "source_fields_present": sorted({f for p in pages for f in p["source_fields_present"]}),
            "interpretation": {"qualified_row_count": len(qualified),
                "qualified_row_indexes": qualified, "issues": issues,
                "qualification": "WITH_EXPLICIT_GAPS" if issues else "BOUNDED_DAILY_PAGES_QUALIFIED",
                "coverage": {"complete_market": False, "requested_dates": [p["report_date"] for p in pages],
                    "interpreted_dates": [p["report_date"] for p in interpreted],
                    "status": "INDEPENDENT_SINGLE_PAGES_NOT_COMPLETE_MARKET"}}
                if interpreted else None,
            "interpretation_error": None, "receipt_error_type": None,
            "recorded_http_attempt_count": None if None in counts else sum(counts),
            "attempts": [{"report_date": p["report_date"], **a} for p in pages for a in p["attempts"]]}


def render(result: dict) -> str:
    lines = ["## Tushare Relay 补充来源", "",
             f"状态 {result['status']}；市场日 {result.get('market_session') or 'UNKNOWN'}；"
             f"取得截止 {result['cutoff']}。第三方中转，不是官方Tushare或聪明钱评分。", "",
             "| 接口 | 取得状态 | 解析行数 | 日期/身份合格行数 |", "|---|---|---:|---:|"]
    if result.get("reports_only"):
        lines += ["本次仅修复七个报告日；未请求游资名录、游资明细或龙虎榜。此前补充仍按原取得日单独保留。", ""]
    for api in APIS:
        item = result["families"].get(api)
        if item:
            qualified = (item.get("interpretation") or {}).get("qualified_row_count", "UNKNOWN")
            lines.append(f"| {api} | {item['status']} | {item['row_count']} | {qualified} |")
    reports = result["families"].get("report_rc", {})
    if reports.get("pages"):
        lines += ["", "报告日分别取得；每行仍是报告的一个预测期，不是独立新事件。", "",
                  "| 报告日 | 状态 | 保存行数 |", "|---|---|---:|"]
        lines += [f"| {p['report_date']} | {p['status']} | {p['row_count']} |" for p in reports["pages"]]
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
    parser.add_argument("--control", type=Path, required=True)
    args = parser.parse_args(argv)
    primary_files = {p.name: p.read_bytes() for p in args.source_capture.iterdir() if p.is_file()}
    manifest = s.decode(primary_files["capture.json"])
    identity = primary.identity(os.environ)
    control = json.loads(args.control.read_bytes())
    s.require(control["run_id"] == identity["run_id"] and
              control["code_commit"] == identity["code_commit"], "RELAY_CONTROL_IDENTITY")
    observation = primary.replay(primary_files, manifest["identity"], cutoff=relay.now())
    if observation["identity"] != identity:
        selected = control.get("relay_source") or {}
        s.require(control.get("decision") == "SKIP_RELAY_ONLY_REUSE_CAPTURE" and
                  observation["identity"]["run_id"] == selected.get("run_id") and
                  observation["identity"]["code_commit"] == selected.get("head_sha") and
                  observation["capture_hash"] == selected.get("capture_hash"), "RELAY_PRIOR_CAPTURE_BINDING")
    market_session = max(observation["trading_sessions"], default=None)
    reports_only = control.get("relay_reports_only", False)
    s.require(type(reports_only) is bool and (not reports_only or
              control.get("decision") == "SKIP_RELAY_ONLY_REUSE_CAPTURE"), "RELAY_REPORT_CONTROL")
    result = capture(args.output, identity, market_session, revision=3,
                     source_capture=source_binding(observation), reports_only=reports_only)
    print(json.dumps({k: result[k] for k in ("status", "market_session", "capture_hash", "unresolved")},
                     ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
