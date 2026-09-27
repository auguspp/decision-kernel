"""B1 finite daily context: two independently requested existing Relay families.

No source routing, research, calendar inference, current quote or investment
signal. The original tushare_relay HTTP client is reused unchanged. A replay
rebuilds the small reading from retained raw responses without credentials.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from . import tushare_relay as relay

VERSION = "global-market-context-v1"
REPOSITORY = "auguspp/decision-kernel"
WORKFLOW = ".github/workflows/radar-global-market.yml"
INDICES = {"SPX": "标普500", "IXIC": "纳斯达克综合", "HSI": "恒生指数",
           "HKTECH": "恒生科技", "N225": "日经225", "GDAXI": "德国DAX"}
TENORS = ("on", "1w", "2w", "1m", "3m", "6m", "9m", "1y")
FAMILIES = ("indices", "shibor")
MAX_RAW = 16 * 1024 * 1024
AUTHORITY = {"qualification": "MARKET_CONTEXT_ONLY", "signal_transition_authority": "NONE",
             "human_attention_authority": "NONE", "research_authority": "NONE",
             "investment_authority": "NONE", "automatic_admission": False,
             "company_mapping": "NOT_PERFORMED", "odds_recomputed": False}
ATTEMPT_KEYS = {"attempt", "http_status", "requested_at", "received_at", "headers",
                "classification", "business_code", "business_error", "business_msg"}
STOPS = {"AUTH_OR_ENTITLEMENT", "RATE_LIMIT", "CREDENTIAL_UNAVAILABLE",
         "REQUEST_RECEIPT_UNAVAILABLE"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return sha256(encoded({k: v for k, v in value.items() if k != "capture_hash"})).hexdigest()


def clock(value):
    require(isinstance(value, str) and len(value) <= 40, "GM_CLOCK")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "GM_CLOCK_ZONE")
    return result.astimezone(timezone.utc)


def day(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "GM_DATE")
    return date.fromisoformat(value)


def validate_identity(value):
    require(isinstance(value, dict) and set(value) == {
        "repository", "workflow", "ref", "event", "code_commit", "run_id", "attempt"}, "GM_IDENTITY")
    require(value["repository"] == REPOSITORY and value["workflow"] == WORKFLOW
            and value["ref"] == "refs/heads/main" and value["event"] == "workflow_dispatch"
            and type(value["attempt"]) is int and value["attempt"] == 1
            and type(value["run_id"]) is int and value["run_id"] > 0
            and isinstance(value["code_commit"], str)
            and re.fullmatch(r"[a-f0-9]{40}", value["code_commit"]), "GM_IDENTITY_SCOPE")


def identity(env):
    result = {"repository": env.get("GITHUB_REPOSITORY"), "workflow": WORKFLOW,
              "ref": env.get("GITHUB_REF"), "event": env.get("GITHUB_EVENT_NAME"),
              "code_commit": env.get("GITHUB_SHA"), "run_id": int(env.get("GITHUB_RUN_ID", "0")),
              "attempt": int(env.get("GITHUB_RUN_ATTEMPT", "0"))}
    validate_identity(result)
    return result


def plan(family, as_of):
    require(family in FAMILIES, "GM_FAMILY")
    end = day(as_of)
    params = {"start_date": (end - timedelta(days=13)).strftime("%Y%m%d"),
              "end_date": end.strftime("%Y%m%d")}
    if family == "shibor":
        return [{"id": "shibor", "api": "shibor", "params": params}]
    return [{"id": code, "api": "index_global", "params": {**params, "ts_code": code}}
            for code in INDICES]


def number(value, *, positive=False):
    require(not isinstance(value, bool) and isinstance(value, (str, int, float))
            and len(str(value)) <= 40, "GM_NUMBER")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("GM_NUMBER") from exc
    require(result.is_finite() and abs(result) < Decimal("1e12")
            and (not positive or result > 0), "GM_NUMBER")
    return result


def text_number(value):
    return format(value, "f")


def normalize(body, spec):
    """Dates/units are source declarations. Consecutive returned rows are not a calendar."""
    fields = body.get("data", {}).get("fields")
    require(isinstance(fields, list) and all(isinstance(f, str) for f in fields)
            and len(fields) == len(set(fields)), "GM_FIELDS")
    needed = {"ts_code", "trade_date", "close"} if spec["api"] == "index_global" else {"date", *TENORS}
    require(needed <= set(fields), "GM_FIELDS")
    rows = relay.rows(body)
    require(len(rows) <= 14 and (body.get("count") is None or body["count"] == len(rows)), "GM_ROW_COVERAGE")
    if not rows:
        return {"status": "EMPTY_RESPONSE_NOT_NO_CHANGE", "observations": []}
    key = "trade_date" if spec["api"] == "index_global" else "date"
    seen = set()
    for row in rows:
        value = row[key]
        require(isinstance(value, str) and re.fullmatch(r"\d{8}", value), "GM_SOURCE_DATE")
        day(value[:4] + "-" + value[4:6] + "-" + value[6:])
        require(spec["params"]["start_date"] <= value <= spec["params"]["end_date"]
                and value not in seen, "GM_SCOPE_OR_DUPLICATE_DATE")
        seen.add(value)
        if spec["api"] == "index_global":
            require(row["ts_code"] == spec["id"], "GM_SYMBOL")
            number(row["close"], positive=True)
            if row.get("pct_chg") is not None:
                number(row["pct_chg"])
        else:
            for tenor in TENORS:
                if row[tenor] is not None:
                    require(abs(number(row[tenor])) < 1000, "GM_RATE_UNIT")
    rows.sort(key=lambda row: row[key])
    latest, previous = rows[-1], rows[-2] if len(rows) > 1 else None
    def iso(row):
        v = row[key]
        return v[:4] + "-" + v[4:6] + "-" + v[6:]
    common = {"source_date": iso(latest), "previous_observed_date": iso(previous) if previous else None,
              "row_count": len(rows), "market_status": "UNKNOWN_NO_EXCHANGE_CALENDAR",
              "publication_time": None, "publication_time_status": "NOT_PROVIDED_BY_SOURCE",
              "calendar_age_at_requested_end": (day(spec["params"]["end_date"][:4] + "-" +
                  spec["params"]["end_date"][4:6] + "-" + spec["params"]["end_date"][6:]) - day(iso(latest))).days}
    observations = []
    with localcontext() as ctx:
        ctx.prec = 36
        if spec["api"] == "index_global":
            value = number(latest["close"], positive=True)
            prior = number(previous["close"], positive=True) if previous else None
            change = ((value / prior - 1) * 100).quantize(Decimal("0.000001")) if prior else None
            observations.append({**common, "symbol": spec["id"], "name": INDICES[spec["id"]],
                "unit": "INDEX_POINTS", "value": text_number(value),
                "previous_value": text_number(prior) if prior is not None else None,
                "observed_interval_change_pct": text_number(change) if change is not None else None,
                "change_scope": "TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS",
                "source_daily_pct_change": (text_number(number(latest["pct_chg"]))
                                            if latest.get("pct_chg") is not None else None)})
        else:
            for tenor in TENORS:
                value = number(latest[tenor]) if latest[tenor] is not None else None
                prior = number(previous[tenor]) if previous and previous[tenor] is not None else None
                change = (value - prior) * 100 if value is not None and prior is not None else None
                observations.append({**common, "symbol": "SHIBOR:" + tenor, "name": "Shibor " + tenor,
                    "currency": "CNY", "unit": "ANNUAL_PERCENT", "tenor": tenor,
                    "value": text_number(value) if value is not None else None,
                    "previous_value": text_number(prior) if prior is not None else None,
                    "observed_interval_change_bp": text_number(change) if change is not None else None,
                    "change_scope": "TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS"})
    available = sum(row["value"] is not None for row in observations)
    return {"status": "ROWS_NORMALIZED" if available == len(observations) else
            "PARTIAL_VALUES" if available else "VALUES_UNAVAILABLE", "observations": observations}


def service_stop(record):
    if record["status"] in STOPS:
        return record["status"]
    for attempt in record["attempts"]:
        if attempt["http_status"] in (401, 403, 429) or attempt["classification"] in STOPS:
            return "SERVICE_REFUSAL"
    return None


def validate_attempt(attempt, raw, first, finish):
    require(set(attempt) == ATTEMPT_KEYS | {"body", "bytes", "sha256"}, "GM_ATTEMPT_FIELDS")
    require(first <= clock(attempt["requested_at"]) <= clock(attempt["received_at"]) <= finish, "GM_TIMES")
    require(isinstance(attempt["headers"], dict) and set(attempt["headers"]) <= set(relay.HEADER_ALLOWLIST), "GM_HEADERS")
    if raw is None:
        require(attempt["body"] is None and attempt["bytes"] is None and attempt["sha256"] is None
                and attempt["http_status"] is None
                and attempt["classification"] in {"TEMPORARY_QUEUE", "TRANSPORT_CONNECTION", "TRANSPORT_ERROR"},
                "GM_MISSING_BODY")
        return
    require(isinstance(raw, bytes) and 0 < len(raw) <= relay.MAX_BODY
            and len(raw) == attempt["bytes"] and sha256(raw).hexdigest() == attempt["sha256"], "GM_RAW_IDENTITY")
    require(type(attempt["http_status"]) is int and 100 <= attempt["http_status"] <= 599, "GM_HTTP_STATUS")
    try:
        body = relay.decode(raw)
    except relay.RelayError:
        require(attempt["classification"] == "MALFORMED_RESPONSE", "GM_CLASSIFICATION")
    else:
        require(relay.classify(attempt["http_status"], body) == attempt["classification"], "GM_CLASSIFICATION")


def replay(files, expected_identity, cutoff):
    """Validate identities and rebuild observations; zero network/model calls."""
    validate_identity(expected_identity)
    require(len(files) <= 15 and sum(map(len, files.values())) <= MAX_RAW + 1024 * 1024, "GM_ARCHIVE_BOUND")
    manifest = relay.decode(files["capture.json"])
    require(manifest["version"] == VERSION and manifest["identity"] == expected_identity
            and manifest["authority"] == AUTHORITY and manifest["relay_host"] == relay.PRO
            and manifest["retry_wait_seconds"] == relay.RETRY_WAIT_SECONDS
            and manifest["capture_hash"] == digest(manifest), "GM_MANIFEST_IDENTITY")
    first, finish = clock(manifest["started_at"]), clock(manifest["finished_at"])
    require(first <= finish <= clock(cutoff), "GM_CAPTURE_TIME")
    require(first.date() - timedelta(days=31) <= day(manifest["as_of_date"]) <= first.date() - timedelta(days=1),
            "GM_RECENT_COMPLETED_DATE")
    specs = plan(manifest["family"], manifest["as_of_date"])
    require(type(manifest["execution_complete"]) is bool and len(manifest["records"]) == len(specs), "GM_PLAN")
    outcomes, consumed, stopped = [], {"capture.json"}, False
    for index, (spec, record) in enumerate(zip(specs, manifest["records"], strict=True)):
        require(record["spec"] == spec and record["index"] == index, "GM_RECORD_SCOPE")
        attempts = record["attempts"]
        require(isinstance(attempts, list) and len(attempts) <= 2, "GM_ATTEMPT_BOUND")
        require(not stopped or not attempts and record["status"] == "NOT_ATTEMPTED_SERVICE_STOP", "GM_SERVICE_STOP")
        if not attempts:
            require(record["status"] in {"NOT_ATTEMPTED", "REQUEST_IN_PROGRESS", "NOT_ATTEMPTED_SERVICE_STOP",
                    "CREDENTIAL_UNAVAILABLE", "REQUEST_RECEIPT_UNAVAILABLE"}, "GM_NO_RECEIPT")
            require(not manifest["execution_complete"] or record["status"] not in {"NOT_ATTEMPTED", "REQUEST_IN_PROGRESS"},
                    "GM_FALSE_COMPLETION")
        for num, attempt in enumerate(attempts, 1):
            require(type(attempt["attempt"]) is int and attempt["attempt"] == num, "GM_ATTEMPT_ORDER")
            if num == 2:
                require(attempts[0]["classification"] == "TEMPORARY_QUEUE"
                        and attempts[0]["http_status"] not in (401, 403, 429)
                        and clock(attempt["requested_at"]) >= clock(attempts[0]["received_at"]), "GM_RETRY_SCOPE")
            path = attempt["body"]
            require(path is None or path == f"raw-{index:02d}-{num}.json", "GM_RAW_PATH")
            validate_attempt(attempt, files[path] if path else None, first, finish)
            if path:
                consumed.add(path)
        if attempts:
            require(record["status"] == attempts[-1]["classification"], "GM_LAST_STATUS")
        stopped = stopped or service_stop(record) is not None
        result = {"id": spec["id"], "status": record["status"], "observations": [],
                  "attempt_count": len(attempts) if attempts else
                  None if record["status"] in {"REQUEST_IN_PROGRESS", "REQUEST_RECEIPT_UNAVAILABLE"} else 0,
                  "source_received_at": attempts[-1]["received_at"] if attempts else None}
        if record["status"] == "SUCCESS":
            try:
                result.update(normalize(relay.decode(files[attempts[-1]["body"]]), spec))
            except (ValueError, TypeError, KeyError, ArithmeticError):
                result.update(status="TABLE_UNCONFIRMED", observations=[])
        outcomes.append(result)
    require(set(files) <= consumed | {"summary.json", "summary.md"}, "GM_EXTRA_RAW_FILES")
    values = sum(row["value"] is not None for part in outcomes for row in part["observations"])
    complete = manifest["execution_complete"] and all(o["status"] == "ROWS_NORMALIZED" for o in outcomes)
    return {"version": VERSION, "identity": deepcopy(expected_identity), "family": manifest["family"],
            "as_of_date": manifest["as_of_date"], "captured_from": manifest["started_at"],
            "captured_through": manifest["finished_at"], "capture_hash": manifest["capture_hash"],
            "source": "TUSHARE_RELAY_THIRD_PARTY_NOT_OFFICIAL_TUSHARE", "source_url": relay.PRO,
            "status": "AVAILABLE" if complete else "PARTIAL" if values else "UNAVAILABLE",
            "outcomes": outcomes, "available_values": values,
            "coverage": "SELECTED_DAILY_SERIES_ONLY_NOT_COMPLETE_GLOBAL_MARKETS",
            "market_status": "UNKNOWN_NO_EXCHANGE_CALENDAR", "source_calls_during_replay": 0,
            "authority": deepcopy(AUTHORITY)}


def render(report):
    title = "全球指数 · 有限日线" if report["family"] == "indices" else "人民币同业利率 · Shibor"
    lines = ["# " + title, "", "这是数据观察，不是 Quick、原因解释或投资信号。",
             "请求窗口截止：" + report["as_of_date"] + "；实际抓取截止：" + report["captured_through"],
             "来源：第三方 Tushare Relay；不等同官方源，非实时行情。市场开闭状态 UNKNOWN。",
             "", "| 对象 | 原数据日期 | 数值/单位 | 上一返回日期 | 两次返回间变化 |", "|---|---|---|---|---|"]
    for outcome in report["outcomes"]:
        if not outcome["observations"]:
            lines.append(f"| {outcome['id']} | UNKNOWN | {outcome['status']} | — | 不作无变化推断 |")
        for row in outcome["observations"]:
            unit = "点" if row["unit"] == "INDEX_POINTS" else "%（年化）"
            change = row.get("observed_interval_change_pct") if row["unit"] == "INDEX_POINTS" else row.get("observed_interval_change_bp")
            suffix = "%" if row["unit"] == "INDEX_POINTS" else " bp"
            lines.append(f"| {row['name']} | {row['source_date']} | {row['value'] or 'UNKNOWN'} {unit} | "
                         f"{row['previous_observed_date'] or 'UNKNOWN'} | {(change + suffix) if change is not None else 'UNKNOWN'} |")
    lines += ["", "变化只比较同系列两个实际返回日期，不保证相邻交易日；日线日期不替代发布时间或抓取时刻。",
              "Shibor 不代表美债收益率。美债、黄金原油、外汇、加密资产及其市场日历尚未由本切片覆盖。",
              "失败与空返回保留为缺口，不清除旧档案、不解释为没有市场变化。"]
    return "\n".join(lines) + "\n"


def capture(output, run_identity, family, as_of, *, request=relay.request, now=relay.now):
    validate_identity(run_identity)
    started = now()
    require(clock(started).date() - timedelta(days=31) <= day(as_of) <= clock(started).date() - timedelta(days=1),
            "GM_RECENT_COMPLETED_DATE")
    specs = plan(family, as_of)
    output = Path(output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), "GM_OUTPUT_EXISTS_OR_SYMLINK")
    output.mkdir(parents=True)
    records = [{"index": i, "spec": spec, "status": "NOT_ATTEMPTED", "attempts": []} for i, spec in enumerate(specs)]
    manifest = {"version": VERSION, "identity": deepcopy(run_identity), "family": family,
                "as_of_date": as_of, "started_at": started, "finished_at": started,
                "execution_complete": False, "records": records, "authority": deepcopy(AUTHORITY),
                "relay_host": relay.PRO, "retry_wait_seconds": relay.RETRY_WAIT_SECONDS}
    def checkpoint():
        manifest["finished_at"] = now()
        manifest["capture_hash"] = digest(manifest)
        temp = output / ".capture.tmp"
        temp.write_bytes(encoded(manifest))
        temp.replace(output / "capture.json")
    checkpoint()
    credential = os.environ.get(relay.SECRET_ENV, "")
    stopped, total = False, 0
    for index, spec in enumerate(specs):
        record = records[index]
        if stopped:
            record["status"] = "NOT_ATTEMPTED_SERVICE_STOP"
        elif not credential:
            record["status"] = "CREDENTIAL_UNAVAILABLE"
        else:
            record["status"] = "REQUEST_IN_PROGRESS"
            checkpoint()
            try:
                result = request(spec["api"], spec["params"], key=credential, clock=now)
                require(result["api"] == spec["api"] and result["params"] == spec["params"]
                        and 1 <= len(result["attempts"]) <= 2, "GM_REQUEST_RECEIPT")
                bodies, attempts = {}, []
                for num, attempt in enumerate(result["attempts"], 1):
                    require(set(attempt) == ATTEMPT_KEYS | {"raw"} and attempt["attempt"] == num, "GM_REQUEST_RECEIPT")
                    raw = attempt["raw"]
                    item = {k: deepcopy(v) for k, v in attempt.items() if k != "raw"}
                    path = f"raw-{index:02d}-{num}.json" if raw is not None else None
                    item.update(body=path, bytes=len(raw) if raw is not None else None,
                                sha256=sha256(raw).hexdigest() if raw is not None else None)
                    validate_attempt(item, raw, clock(started), clock(now()))
                    if path:
                        bodies[path] = raw
                    attempts.append(item)
                candidate = {"index": index, "spec": spec, "status": result["status"], "attempts": attempts}
                require(candidate["status"] == attempts[-1]["classification"], "GM_REQUEST_RECEIPT")
                require(len(attempts) == 1 or attempts[0]["classification"] == "TEMPORARY_QUEUE"
                        and attempts[0]["http_status"] not in (401, 403, 429), "GM_RETRY_SCOPE")
                require(credential.encode() not in encoded(candidate)
                        and all(credential.encode() not in raw for raw in bodies.values()), "GM_CREDENTIAL_REFLECTION")
                require(total + sum(map(len, bodies.values())) <= MAX_RAW, "GM_RAW_BUDGET")
                for path, raw in bodies.items():
                    (output / path).write_bytes(raw)
                total += sum(map(len, bodies.values()))
                records[index] = record = candidate
            except Exception as exc:  # No upstream error text/credentials in retained diagnostics.
                record.update(status="REQUEST_RECEIPT_UNAVAILABLE", attempts=[], error_type=type(exc).__name__)
        stopped = stopped or service_stop(record) is not None
        checkpoint()
    manifest["execution_complete"] = True
    checkpoint()
    report = replay({p.name: p.read_bytes() for p in output.iterdir()}, run_identity, now())
    (output / "summary.json").write_bytes(encoded(report))
    (output / "summary.md").write_text(render(report), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=FAMILIES)
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD, at most yesterday UTC; default yesterday")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    as_of = args.as_of or (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    report = capture(args.output, identity(os.environ), args.family, as_of)
    print(json.dumps({"family": report["family"], "status": report["status"],
                      "available_values": report["available_values"], "capture_hash": report["capture_hash"]}))
    return 0 if report["available_values"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
