"""One explicitly approved dated-TDX source check, not a historical role engine.

Reuse the existing Relay transport/attempt validator and pinned native-member
reader. No source substitution, pagination, backfill, scheduler or live admission.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from . import global_market_context as common
from . import tushare_relay as relay

VERSION = "tdx-dated-member-source-check-v0"
PILOT = "c2-tdx-members-20261002"
WORKFLOW = ".github/workflows/tdx-member-source-check.yml"
BOARDS = {"880550.TDX": "PCB概念", "880706.TDX": "分散染料"}
NATIVE = {
    "20260929": ("bc519f1c81d0eb053a18051c5bd1918bf343c456",
                 "69d48a900e1d39cfa648ed681145f8941e4855059b497438b26b6100b7f3de71"),
    "20260930": ("f5dd2954c5e29dea77d875c013d399e78dc7270f",
                 "982f79e8f21f8bfa776df7015cad795caf063dbc448e4d3557d23318dd0b5c26"),
}
AUTHORITY = {"signal_transition_authority": "NONE", "human_attention_authority": "NONE",
             "research_authority": "NONE", "investment_authority": "NONE",
             "automatic_admission": False}
MAX_TOTAL = 16 * 1024 * 1024
FIELDS = {"tdx_index": ("ts_code", "trade_date", "name", "idx_type", "idx_count"),
          "tdx_member": ("ts_code", "trade_date", "con_code", "con_name")}
require, encoded, clock = common.require, common.encoded, common.clock


def plan():
    """Two dated catalogs plus four exact board/date member pages; no hidden call."""
    specs = []
    for day in NATIVE:
        specs.append({"api": "tdx_index", "params": {
            "trade_date": day, "idx_type": "概念板块", "limit": "1000",
            "fields": ",".join(FIELDS["tdx_index"])}})
        for board in BOARDS:
            specs.append({"api": "tdx_member", "params": {
                "trade_date": day, "ts_code": board, "limit": "3000",
                "fields": ",".join(FIELDS["tdx_member"])}})
    return specs


def qualify(raw, spec, received_at):
    """Qualify the requested page, never certify vintage or continuous membership."""
    require(spec in plan(), "TDX_REQUEST_SCOPE")
    return qualify_page(raw, spec, received_at, boards=BOARDS)


def qualify_page(raw, spec, received_at, *, boards):
    """Shared dated-page checks; the caller must independently freeze its plan.

    This pure parser grants no request permission. The original pilot wrapper
    above still rejects any spec outside its original six-query plan.
    """
    api, params = spec["api"], spec["params"]
    require(api in FIELDS and isinstance(boards, dict) and boards, "TDX_REQUEST_SCOPE")
    expected_keys = {"trade_date", "limit", "fields", "idx_type" if api == "tdx_index" else "ts_code"}
    require(set(params) == expected_keys and params["fields"] == ",".join(FIELDS[api])
            and params["limit"] == ("1000" if api == "tdx_index" else "3000")
            and (params.get("idx_type") == "概念板块" if api == "tdx_index" else params["ts_code"] in boards),
            "TDX_REQUEST_SCOPE")
    body = relay.decode(raw)
    require(type(body.get("code")) is int and body["code"] == 0
            and body.get("ok", True) is True and body.get("error") in (None, ""), "TDX_BUSINESS_STATUS")
    require(body.get("api_name") in (None, api), "TDX_RESPONSE_API")
    data = body.get("data")
    require(isinstance(data, dict), "TDX_ENVELOPE")
    fields = data.get("fields")
    require(isinstance(fields, list) and fields and all(isinstance(f, str) for f in fields)
            and len(fields) == len(set(fields)), "TDX_DUPLICATE_OR_INVALID_COLUMNS")
    require(set(FIELDS[api]) <= set(fields), "TDX_REQUIRED_COLUMNS")
    rows = relay.rows(body)
    require(len(rows) < int(params["limit"]), "TDX_POSSIBLE_TRUNCATION")
    require(body.get("count") is None or type(body["count"]) is int
            and body["count"] == len(rows), "TDX_COUNT_MISMATCH")
    require(datetime.strptime(params["trade_date"], "%Y%m%d").date()
            <= clock(received_at).date(), "TDX_FUTURE_DATE")
    require(bool(rows), "TDX_EMPTY_NOT_ZERO_MEMBERS")
    identities = set()
    selected = []
    for row in rows:
        require(row["trade_date"] == params["trade_date"], "TDX_DATE_FILTER_MISMATCH")
        require(isinstance(row["ts_code"], str)
                and re.fullmatch(r"[0-9]{6}\.TDX", row["ts_code"]), "TDX_BOARD_IDENTITY")
        if api == "tdx_index":
            identity = row["ts_code"]
            require(row["idx_type"] == params["idx_type"], "TDX_TAXONOMY_MISMATCH")
            require(type(row["idx_count"]) is int and row["idx_count"] >= 0, "TDX_MEMBER_COUNT")
            require(isinstance(row["name"], str) and bool(row["name"].strip()), "TDX_NAME")
        else:
            require(row["ts_code"] == params["ts_code"], "TDX_BOARD_FILTER_MISMATCH")
            identity = row["con_code"]
            require(isinstance(identity, str) and re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", identity),
                    "TDX_SECURITY_IDENTITY")
            require(isinstance(row["con_name"], str) and bool(row["con_name"].strip()), "TDX_NAME")
        require(identity not in identities, "TDX_DUPLICATE_IDENTITY")
        identities.add(identity)
        selected.append({key: row[key] for key in FIELDS[api]})
    if api == "tdx_index":
        catalog = {r["ts_code"]: r for r in selected}
        require(all(b in catalog and catalog[b]["name"] == n for b, n in boards.items()),
                "TDX_TARGET_CATALOG_IDENTITY")
    # Preserve every other field in the bound raw body, not an invented normal form.
    claims = json.loads(raw.decode("utf-8-sig"), parse_float=str)
    source_claims = [{"location": loc, "field": k, "value": item[k]}
                     for loc, item in (("envelope", claims), ("data", claims["data"]))
                     for k in ("source", "provider", "data_source") if k in item]
    return {"status": "DATED_PAGE_QUALIFIED", "rows": selected,
            "extra_columns_retained_in_raw": sorted(set(fields) - set(FIELDS[api])),
            "source_claims": source_claims}


def native_inputs(files):
    # Lazy import: table/receipt checks need no concept provider or new dependency.
    from .tdx_membership_comparison import _snapshot
    result = {}
    for day, (ref, expected) in NATIVE.items():
        p, catalog, origin = _snapshot(files[f"native-{day}-reading.json"],
                                      files[f"native-{day}-members.json"], ref, expected)
        require(p["source_prepared_date"].replace("-", "") == day, "TDX_NATIVE_DATE")
        require(all(b[:6] in catalog and catalog[b[:6]]["name"] == n
                    for b, n in BOARDS.items()), "TDX_NATIVE_BOARD_IDENTITY")
        result[day] = {"origin": origin, "boards": {b: catalog[b[:6]] for b in BOARDS}}
    return result


def validate_identity(identity):
    require(set(identity) == {"repository", "code_commit", "run_id", "run_attempt", "workflow"},
            "TDX_EXECUTION_IDENTITY")
    require(identity["repository"] == "auguspp/decision-kernel" and identity["workflow"] == WORKFLOW
            and type(identity["run_attempt"]) is int and identity["run_attempt"] == 1
            and isinstance(identity["run_id"], str) and re.fullmatch(r"[1-9][0-9]*", identity["run_id"])
            and isinstance(identity["code_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", identity["code_commit"]), "TDX_EXECUTION_IDENTITY")


def replay(files, expected_identity):
    validate_identity(expected_identity)
    require(len(files) <= 25 and sum(map(len, files.values())) <= MAX_TOTAL, "TDX_ARCHIVE_BOUND")
    native = native_inputs(files)
    m = relay.decode(files["capture.json"])
    require(m["version"] == VERSION and m["pilot"] == PILOT and m["identity"] == expected_identity
            and m["authority"] == AUTHORITY and m["relay_host"] == relay.PRO
            and m["retry_wait_seconds"] == relay.RETRY_WAIT_SECONDS
            and m["capture_hash"] == common.digest(m), "TDX_CAPTURE_IDENTITY")
    first, finish = clock(m["started_at"]), clock(m["finished_at"])
    require(first <= finish and type(m["execution_complete"]) is bool, "TDX_CAPTURE_TIME")
    specs = plan()
    require(len(m["records"]) == len(specs), "TDX_PLAN")
    consumed = {"capture.json", *[f"native-{d}-{kind}.json" for d in NATIVE
                                   for kind in ("reading", "members")]}
    outcomes, tables, stopped, previous = [], {}, False, first
    for index, (spec, record) in enumerate(zip(specs, m["records"], strict=True)):
        require(record["index"] == index and record["spec"] == spec, "TDX_RECORD_SCOPE")
        attempts = record["attempts"]
        require(isinstance(attempts, list) and len(attempts) <= 2, "TDX_ATTEMPT_BOUND")
        require(not stopped or not attempts and record["status"] == "NOT_ATTEMPTED_STOP", "TDX_STOP")
        if not attempts:
            require(record["status"] in {"NOT_ATTEMPTED", "REQUEST_IN_PROGRESS", "NOT_ATTEMPTED_STOP",
                    "CREDENTIAL_UNAVAILABLE", "REQUEST_RECEIPT_UNAVAILABLE"}, "TDX_MISSING_RECEIPT")
            require(not m["execution_complete"] or record["status"] not in
                    {"NOT_ATTEMPTED", "REQUEST_IN_PROGRESS"}, "TDX_FALSE_COMPLETION")
        for number, attempt in enumerate(attempts, 1):
            require(type(attempt["attempt"]) is int and attempt["attempt"] == number, "TDX_ATTEMPT_ORDER")
            require(clock(attempt["requested_at"]) >= previous, "TDX_REQUEST_TIME_ORDER")
            if number == 2:
                require(attempts[0]["classification"] == "TEMPORARY_QUEUE"
                        and (clock(attempt["requested_at"]) - clock(attempts[0]["received_at"])).total_seconds()
                        >= relay.RETRY_WAIT_SECONDS, "TDX_RETRY_SCOPE")
            name = attempt["body"]
            require(name is None or name == f"raw-{index:02d}-{number}.json", "TDX_RAW_PATH")
            common.validate_attempt(attempt, files[name] if name else None, first, finish)
            previous = clock(attempt["received_at"])
            if name:
                consumed.add(name)
        if attempts:
            require(record["status"] == attempts[-1]["classification"], "TDX_LAST_STATUS")
        outcome = {"spec": spec, "status": record["status"], "attempts": len(attempts),
                   "received_at": attempts[-1]["received_at"] if attempts else None}
        if record["status"] == "SUCCESS":
            try:
                table = qualify(files[attempts[-1]["body"]], spec, attempts[-1]["received_at"])
                tables[index] = table
                outcome.update(status=table["status"], row_count=len(table["rows"]),
                               source_claims=table["source_claims"],
                               extra_columns_retained_in_raw=table["extra_columns_retained_in_raw"])
            except (ValueError, TypeError, KeyError):
                outcome["status"] = "TABLE_UNQUALIFIED"
        stopped = stopped or outcome["status"] != "DATED_PAGE_QUALIFIED"
        outcomes.append(outcome)
    require(set(files) <= consumed | {"summary.json", "summary.md", "verification.json"}, "TDX_EXTRA_FILES")
    comparisons = []
    for i, day in enumerate(NATIVE):
        catalog = {r["ts_code"]: r for r in tables.get(i * 3, {}).get("rows", [])}
        for j, board in enumerate(BOARDS, 1):
            table = tables.get(i * 3 + j)
            row = {"trade_date": day, "board": board, "name": BOARDS[board],
                   "status": "INPUT_GAP", "native_origin": native[day]["origin"]}
            if board in catalog and table is not None:
                left = set(native[day]["boards"][board]["members"])
                right = {r["con_code"] for r in table["rows"]}
                row.update(native_count=len(left), relay_count=len(right),
                           catalog_count=catalog[board]["idx_count"],
                           only_native=sorted(left - right), only_relay=sorted(right - left))
                row["status"] = ("CATALOG_COUNT_MISMATCH" if len(right) != catalog[board]["idx_count"] else
                                 "MATCHES_NATIVE_SNAPSHOT" if left == right else "DIFFERS_FROM_NATIVE_SNAPSHOT")
            comparisons.append(row)
    complete = m["execution_complete"] and all(c["status"] == "MATCHES_NATIVE_SNAPSHOT" for c in comparisons)
    return {"version": VERSION, "pilot": PILOT, "identity": expected_identity,
            "capture_hash": m["capture_hash"], "captured_from": m["started_at"], "captured_through": m["finished_at"],
            "status": "FOUR_DATED_GROUPS_MATCH_NATIVE" if complete else "SOURCE_QUALIFICATION_GAP",
            "outcomes": outcomes, "comparisons": comparisons,
            "logical_queries_attempted": sum(bool(r["attempts"]) for r in m["records"]),
            "http_attempts_recorded": sum(len(r["attempts"]) for r in m["records"]),
            "unknown_request_receipt": any(r["status"] in {"REQUEST_IN_PROGRESS", "REQUEST_RECEIPT_UNAVAILABLE"}
                                            for r in m["records"]),
            "historical_pit_knowledge": "NOT_ESTABLISHED", "continuous_membership": "NOT_ESTABLISHED",
            "multi_horizon_roles": "NOT_COMPUTED", "independent_economic_evidence": False,
            "source": "THIRD_PARTY_TUSHARE_RELAY_NOT_OFFICIAL_SOURCE_IDENTITY",
            "source_calls_during_replay": 0, "authority": deepcopy(AUTHORITY)}


def render(report):
    lines = ["# C2：TDX 日期成员来源核查", "", "状态：" + report["status"],
             "实际取得截止：" + report["captured_through"],
             "第三方 Relay 与原保存成员逐项对照，不是新增市场信号、完整历史或当时已知证明。", "",
             "| 日期 | 板块 | 原保存/Relay/目录人数 | 对照状态 |", "|---|---|---|---|"]
    for c in report["comparisons"]:
        counts = "/".join(str(c.get(k, "未取得")) for k in ("native_count", "relay_count", "catalog_count"))
        lines.append(f"| {c['trade_date']} | {c['board']} {c['name']} | {counts} | {c['status']} |")
    lines += ["", "完整差异、请求状态与原件身份见 summary.json/capture.json；空返回不是零成员。",
              "两日期匹配不证明此前60日或两端之间持续有效；没有计算价格角色或启用生产采集。"]
    return "\n".join(lines) + "\n"


def capture(output, native_files, identity, *, request=relay.request, now=relay.now):
    validate_identity(identity)
    native_inputs(native_files)  # Must pass before any credential/source access.
    output = Path(output)
    require(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), "TDX_OUTPUT_EXISTS")
    output.mkdir(parents=True)
    for name, raw in native_files.items():
        require(name in {f"native-{d}-{k}.json" for d in NATIVE for k in ("reading", "members")}, "TDX_NATIVE_PATH")
        with (output / name).open("xb") as stream:
            stream.write(raw)
    started = now()
    records = [{"index": i, "spec": spec, "status": "NOT_ATTEMPTED", "attempts": []}
               for i, spec in enumerate(plan())]
    m = {"version": VERSION, "pilot": PILOT, "identity": identity, "authority": AUTHORITY,
         "relay_host": relay.PRO, "retry_wait_seconds": relay.RETRY_WAIT_SECONDS,
         "started_at": started, "finished_at": started, "execution_complete": False, "records": records}
    credential = os.environ.get(relay.SECRET_ENV, "")
    def checkpoint():
        m["finished_at"] = now()
        m["capture_hash"] = common.digest(m)
        payload = encoded(m)
        require(not credential or credential.encode() not in payload, "TDX_CREDENTIAL_REFLECTION")
        (output / ".capture.tmp").write_bytes(payload)
        (output / ".capture.tmp").replace(output / "capture.json")
    checkpoint()
    stopped = False
    for record in records:
        if stopped:
            record["status"] = "NOT_ATTEMPTED_STOP"
            checkpoint()
            continue
        if not credential:
            record["status"] = "CREDENTIAL_UNAVAILABLE"
            stopped = True
            checkpoint()
            continue
        record["status"] = "REQUEST_IN_PROGRESS"
        checkpoint()
        spec = record["spec"]
        try:
            result = request(spec["api"], spec["params"], key=credential, clock=now)
            require(result["api"] == spec["api"] and result["params"] == spec["params"]
                    and 1 <= len(result["attempts"]) <= 2, "TDX_REQUEST_RECEIPT")
            for attempt in result["attempts"]:
                item = {k: deepcopy(v) for k, v in attempt.items() if k != "raw"}
                raw = attempt.get("raw")
                item.update(body=None, bytes=None, sha256=None)
                if raw is not None:
                    require(isinstance(raw, bytes) and len(raw) <= relay.MAX_BODY
                            and credential.encode() not in raw, "TDX_UNSAFE_BODY")
                    require(sum(p.stat().st_size for p in output.iterdir()) + len(raw) <= MAX_TOTAL,
                            "TDX_ARCHIVE_BOUND")
                    name = f"raw-{record['index']:02d}-{attempt['attempt']}.json"
                    with (output / name).open("xb") as stream:
                        stream.write(raw)
                    item.update(body=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
                record["attempts"].append(item)
            record["status"] = result["status"]
            stopped = result["status"] != "SUCCESS"
            if not stopped:
                try:
                    qualify(result["attempts"][-1]["raw"], spec, result["attempts"][-1]["received_at"])
                except (ValueError, TypeError, KeyError):
                    stopped = True
        except Exception:
            # No error text/credential reflection and no local recovery request.
            record["status"] = "REQUEST_RECEIPT_UNAVAILABLE"
            checkpoint()
            raise
        checkpoint()
    m["execution_complete"] = True
    checkpoint()
    files = load_files(output)
    report = replay(files, identity)
    (output / "summary.json").write_bytes(encoded(report))
    (output / "summary.md").write_text(render(report), encoding="utf-8")
    return report


def load_files(root):
    paths = list(Path(root).iterdir())
    require(len(paths) <= 25 and all(p.is_file() and not p.is_symlink() for p in paths)
            and sum(p.stat().st_size for p in paths) <= MAX_TOTAL, "TDX_ARCHIVE_BOUND")
    return {p.name: p.read_bytes() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--native-inputs", type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    identity = {"repository": "auguspp/decision-kernel", "code_commit": args.code_commit,
                "run_id": args.run_id, "run_attempt": 1, "workflow": WORKFLOW}
    if args.mode == "capture":
        require(args.native_inputs is not None, "TDX_NATIVE_INPUTS_REQUIRED")
        report = capture(args.root, load_files(args.native_inputs), identity)
    else:
        files = load_files(args.root)
        report = replay(files, identity)
        require(files.get("summary.json") == encoded(report)
                and files.get("summary.md") == render(report).encode(), "TDX_REPLAY_MISMATCH")
        with (args.root / "verification.json").open("xb") as stream:
            stream.write(encoded({"status": "REPLAY_MATCHED", "source_calls": 0,
                                  "summary_sha256": sha256(files["summary.json"]).hexdigest()}))
    print(report["status"])
    if args.mode == "capture" and report["status"] != "FOUR_DATED_GROUPS_MATCH_NATIVE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
