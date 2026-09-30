"""Selected registered securities -> bounded CNINFO capture and readable source fields.

Reuse AKShare's reviewed query, existing custody and original source-only workflow.
Selection is an explicit lookup, not a follow/holding or research acceptance decision.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from hashlib import sha1, sha256
from html import escape
import json
import os
from pathlib import Path
import re

import requests
from decision_kernel.runtime import tushare_relay as relay

ROOT = Path(__file__).resolve().parents[2]
URL = "https://www.cninfo.com.cn/new/information/getPrbookInfo"
MAX_BODY = 256 * 1024
MAX_COMPANIES = 6
WORKFLOW = ".github/workflows/b2-disclosure-appointments.yml"
CLIENT_BLOB = "d2ee02a81648eafe7204a47e7f8e41b56c3c48fd"
# Source keys, not DataFrame positions; preserve values, absent keys and slot order.
DATE_FIELDS = {
    "first_appointment": "f002d_0102", "change_1": "f003d_0102",
    "change_2": "f004d_0102", "change_3": "f005d_0102",
    "actual_disclosure": "f006d_0102",
}
CONTINUE = {"CAPTURED_REQUIRES_SOURCE_REVIEW", "EMPTY_RESPONSE_NOT_NO_APPOINTMENT",
            "NULL_RESPONSE_NOT_NO_APPOINTMENT", "CAPTURED_WITH_FIELD_GAPS"}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(path, raw):
    secret = os.environ.get(relay.SECRET_ENV, "").encode("utf-8")
    if secret and secret in raw:
        raise ValueError("B2_CREDENTIAL_REFLECTION")
    with path.open("xb") as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise OSError("B2_SAVE_READBACK")


def is_day(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def plan_requests(reference_ids, period, registry_raw, code_commit):
    """Select only explicit IDs from the existing index; never scan all saved stocks."""
    relay.require(is_day(period) and period[5:] in ("03-31", "06-30", "09-30", "12-31"),
                  "B2_REPORT_PERIOD")
    relay.require(isinstance(reference_ids, list) and 1 <= len(reference_ids) <= MAX_COMPANIES
                  and all(isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", v)
                          for v in reference_ids), "B2_SELECTION_INPUT")
    relay.require(len(reference_ids) == len(set(reference_ids)), "B2_DUPLICATE_SELECTION")
    relay.require(isinstance(code_commit, str) and re.fullmatch(r"[0-9a-f]{40}", code_commit),
                  "B2_CODE_COMMIT")
    relay.require(isinstance(registry_raw, bytes) and len(registry_raw) <= 512 * 1024,
                  "B2_REGISTRY_SIZE")
    registry = relay.decode(registry_raw)
    relay.require(type(registry.get("schema_version")) is int and registry["schema_version"] == 1 and registry.get("semantics") ==
                  "EXPLICIT_READ_PURPOSES_AND_RESOLUTION_REFERENCES_NOT_CANONICAL_STATE",
                  "B2_REGISTRY_KIND")
    refs = registry.get("references")
    relay.require(isinstance(refs, list) and len(refs) <= 1024
                  and all(isinstance(r, dict) for r in refs), "B2_REGISTRY_REFERENCES")
    plan = []
    for ref_id in reference_ids:
        matches = [r for r in refs if r.get("id") == ref_id]
        relay.require(len(matches) == 1, "B2_SELECTION_NOT_UNIQUE_OR_REGISTERED")
        selected = matches[0]
        code = selected.get("case")
        relay.require(isinstance(code, str) and re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", code),
                      "B2_UNSUPPORTED_SECURITY")
        source = selected.get("archive_source") or selected.get("source")
        relay.require(isinstance(source, dict) and isinstance(source.get("path"), str)
                      and bool(source["path"]) and isinstance(selected.get("use"), str),
                      "B2_SELECTION_SOURCE")
        # This locator is retained as data, never fetched/executed as an instruction.
        market = {"SH": "sh", "SZ": "sz", "BJ": "bj"}[code[-2:]]
        if code.endswith(".SH") and code.startswith(("688", "689")):
            market = "shkcp"
        plan.append({"code": code, "selection": deepcopy(selected),
            "relationship": "NOT_INFERRED_FROM_SOURCE_SELECTION", "report_period": period,
            "params": {"sectionTime": period, "firstTime": "", "lastTime": "",
                "market": market, "stockCode": code[:6], "orderClos": "", "isDesc": "",
                "pagesize": "100", "pagenum": "1"}})
    relay.require(len({r["code"] for r in plan}) == len(plan), "B2_DUPLICATE_SECURITY")
    scope = {"ref": code_commit, "path": "current_state/registry.json",
        "git_blob": sha1(f"blob {len(registry_raw)}\0".encode() + registry_raw).hexdigest(),
        "bytes": len(registry_raw), "sha256": sha256(registry_raw).hexdigest(),
        "selected_reference_ids": reference_ids,
        "meaning": "EXPLICIT_SOURCE_LOOKUP_NOT_FOLLOW_HOLDING_OR_AUTOMATIC_ADMISSION"}
    return plan, scope


def inspect_body(raw, code, period):
    """Mechanical request/field checks; not a complete history or date-truth verdict."""
    body = relay.decode(raw)
    relay.require(body.get("error") in (None, "") and body.get("success", True) is True
                  and body.get("ok", True) is True
                  and (body.get("code") is None or type(body["code"]) is int and body["code"] == 0),
                  "B2_BUSINESS_ERROR")
    rows = body["prbookinfos"]
    relay.require(body.get("hasNextPage") is False and body.get("hasPreviousPage") is False,
                  "B2_COVERAGE")
    total, pages = body.get("totalRows"), body.get("totalPages")
    relay.require(type(total) is int and type(pages) is int, "B2_COVERAGE")
    if rows is None or rows == []:
        relay.require(total == 0 and pages in (0, 1), "B2_COVERAGE")
        return {"status": "NULL_RESPONSE_NOT_NO_APPOINTMENT" if rows is None else
                "EMPTY_RESPONSE_NOT_NO_APPOINTMENT", "table_kind": "NULL" if rows is None else "LIST",
                "row_count": 0, "rows": [], "issues": ["NO_RECORD_RETURNED_NOT_NO_APPOINTMENT"]}
    relay.require(type(rows) is list and 0 < len(rows) < 100 and total == len(rows) and pages == 1
                  and all(type(row) is dict for row in rows), "B2_TABLE_SHAPE_OR_COVERAGE")
    relay.require(all(row.get("seccode") == code[:6] and row.get("f001d_0102") == period
                      for row in rows), "B2_REQUEST_IDENTITY")
    mapped, issues = [], []
    for index, row in enumerate(rows):
        dates = {name: row[key] for name, key in DATE_FIELDS.items() if key in row}
        missing = [key for key in ("secname", *DATE_FIELDS.values()) if key not in row]
        invalid = [DATE_FIELDS[name] for name, value in dates.items()
                   if value is not None and value != "" and not is_day(value)]
        if "secname" in row and (not isinstance(row["secname"], str) or not row["secname"].strip()):
            invalid.append("secname")
        if missing: issues.append("MISSING_FIELDS")
        if invalid: issues.append("INVALID_FIELDS")
        if not any(is_day(dates.get(name)) for name in ("first_appointment", "change_1", "change_2", "change_3")):
            issues.append("NO_USABLE_APPOINTMENT_VALUE")
        mapped.append({"source_row_index": index,
            "source_identity_fields": {key: row[key] for key in
                ("seccode", "secname", "f001d_0102", "orgId", "latest_time") if key in row},
            "date_fields": dates, "missing_fields": missing, "invalid_fields": invalid})
    return {"status": "CAPTURED_WITH_FIELD_GAPS" if issues else "CAPTURED_REQUIRES_SOURCE_REVIEW",
            "table_kind": "LIST", "row_count": len(rows), "rows": mapped,
            "issues": list(dict.fromkeys(issues)), "revision_history_complete": False}


def public_request(params, *, clock=relay.now, session_factory=requests.Session):
    """One POST, one fresh credential-free session; preserve complete/partial bytes."""
    result = {"requested_at": clock(), "http_status": None, "headers": {},
              "raw": None, "body_complete": False, "error_type": None}
    chunks = []
    length = 0
    try:
        with session_factory() as session:
            session.trust_env = False  # No netrc or environment proxy credentials.
            with session.post(URL, params=params, headers={"Accept": "application/json",
                    "Accept-Encoding": "identity"}, timeout=(5, 15),
                    allow_redirects=False, stream=True) as response:
                result["http_status"] = response.status_code
                result["headers"] = {k: response.headers[k] for k in
                    ("Content-Type", "Content-Length", "Content-Encoding", "Date", "Retry-After")
                    if k in response.headers}
                relay.require(response.headers.get("Content-Encoding", "identity")
                              in ("identity", ""), "B2_ENCODING")
                for chunk in response.iter_content(chunk_size=16384):
                    room = MAX_BODY - length
                    chunks.append(chunk[:room])
                    length += len(chunk)
                    relay.require(length <= MAX_BODY, "B2_BODY_LIMIT")
                result["body_complete"] = True
    except (requests.RequestException, ValueError) as exc:
        result["error_type"] = str(exc) if isinstance(exc, relay.RelayError) else type(exc).__name__
    finally:
        if chunks or result["body_complete"]:
            result["raw"] = b"".join(chunks)
        result["received_at"] = clock()  # Operation end, including stream/error handling.
    return result


def readable_summary(result):
    """Source-only Markdown consumable by the existing saved-document reader."""
    def cell(value):
        return escape(json.dumps(value, ensure_ascii=False), quote=False).replace("|", "&#124;").replace("`", "&#96;")
    lines = ["# 已选证券财报预约 · 标准通道结果", "",
        f"报告期：{result['report_period']}。本次取得结束：{result['finished_at']}。",
        "显式选择只用于本次取数，不是持仓、关注、监控、研究完成或投资接受；没有创建提醒。",
        "日期是来源字段，不推最终预约日；取消、改期或实际披露须有明确材料，不能从空值推断。", ""]
    for item in result["outcomes"]:
        lines.extend([f"## {item['code']}｜{item['status']}", "",
            f"选择依据：{item['reference_id']}；原用途：{cell(item['registered_use'])}。"])
        if item["receipt"] is None:
            lines.extend(["本次源访问停止后未查询，不是空表或没有预约。", ""])
            continue
        lines.append(f"请求／取得时钟：{item['requested_at']} / {item['received_at']}；原件：{item['receipt']}。")
        inspection = item.get("inspection")
        if inspection:
            lines.append(f"表形：{inspection['table_kind']}；返回行数：{inspection['row_count']}；缺口：{cell(inspection['issues'])}。")
            for row in inspection["rows"]:
                fields = row["date_fields"]
                lines.extend([f"来源行 {row['source_row_index']}：{cell(row['source_identity_fields'])}", "",
                    "| 首次预约 | 变更一 | 变更二 | 变更三 | 实际披露 |", "|---|---|---|---|---|",
                    "| " + " | ".join(cell(fields[name]) if name in fields else "缺列"
                                         for name in DATE_FIELDS) + " |",
                    f"缺列：{cell(row['missing_fields'])}；无效字段：{cell(row['invalid_fields'])}。"])
        lines.append("")
    lines.extend(["## 依据与读取范围", "",
        f"来源：{URL}；请求、索引版本与选择依据见plan.json；各项原始字节与HTTP状态见receipt.json/response.body。",
        "null、空字符串、缺列与空表分别保留；首次预约、三次变更、实际披露不互补、不取最大日期、不去重丢行。",
        "原件待复核：程序仅核请求身份、字段和格式；未取得PDF、完整修订链或独立来源确认。",
        "Git保存、用途登记、发布与实际读取另行完成；源请求成功不等于这些交付已完成。",
        "旧批次、R4、公司研究问题与Human历史不覆盖；Investment Authority=NONE。", ""])
    return "\n".join(lines).encode("utf-8")


def capture(output, identity, *, reference_ids, period, registry_raw=None,
            request=public_request, clock=relay.now):
    registry_raw = (ROOT / "current_state/registry.json").read_bytes() if registry_raw is None else registry_raw
    plan, scope = plan_requests(reference_ids, period, registry_raw, identity.get("GITHUB_SHA"))
    output = Path(output)
    output.mkdir()  # Existing or partial captures are never overwritten.
    save(output / "plan.json", encoded({"identity": identity, "scope_source": scope,
        "source": URL, "method": "POST", "requests": plan, "started_at": clock(),
        "max_requests": len(plan), "retries": 0, "redirects": False,
        "source_identity": "CNINFO_PUBLIC_ENDPOINT_NOT_RELAY",
        "reuse": "AKShare stock_yjyg_cninfo.py@0191689d57c667b7c7a198fd0cf97316837ef311",
        "investment_authority": "NONE"}))
    outcomes, stopped = [], False
    for spec in plan:
        code = spec["code"]
        outcome = {"code": code, "reference_id": spec["selection"]["id"],
                   "registered_use": spec["selection"]["use"],
                   "status": "NOT_QUERIED_AFTER_STOP", "receipt": None}
        if not stopped:
            directory = output / code
            directory.mkdir()
            record = {"request": spec, "invoked_at": clock(),
                      "date_qualification": "NOT_PERFORMED", "official_appointment_qualified": False}
            try:
                received = request(spec["params"], clock=clock)
            except Exception as exc:
                received = {"http_status": None, "raw": None, "body_complete": False,
                            "error_type": type(exc).__name__, "requested_at": record["invoked_at"],
                            "received_at": clock()}
            retained = deepcopy(received)
            raw = retained.pop("raw")
            retained.update(body=None, bytes=None, sha256=None)
            if raw is not None:
                relay.require(isinstance(raw, bytes) and len(raw) <= MAX_BODY, "B2_RAW_SIZE")
                save(directory / "response.body", raw)
                retained.update(body="response.body", bytes=len(raw), sha256=sha256(raw).hexdigest())
            record["response"] = retained
            status = "SOURCE_OR_TRANSPORT_GAP_RAW_RETAINED"
            if retained["http_status"] == 200 and retained["body_complete"] and not retained["error_type"]:
                try:
                    record["inspection"] = inspect_body(raw, code, period)
                    status = record["inspection"]["status"]
                except (ValueError, TypeError, KeyError):
                    status = "RESPONSE_GAP_RAW_RETAINED"
            stopped = status not in CONTINUE
            record.update(status=status, finished_at=clock())
            save(directory / "receipt.json", encoded(record))
            outcome.update(status=status, receipt=f"{code}/receipt.json",
                           requested_at=retained.get("requested_at", "UNKNOWN"),
                           received_at=retained.get("received_at", "UNKNOWN"))
            if "inspection" in record:
                outcome["inspection"] = record["inspection"]
        outcomes.append(outcome)
    field_gaps = any(o["status"] != "CAPTURED_REQUIRES_SOURCE_REVIEW" for o in outcomes)
    result = {"identity": identity, "source": URL, "report_period": period,
        "finished_at": clock(), "outcomes": outcomes,
        "status": "STOPPED_WITH_GAPS" if stopped else "CAPTURED_WITH_GAPS" if field_gaps else
                  "CAPTURED_REQUIRES_SOURCE_REVIEW",
        "official_appointment_qualified": False, "research_executed": False,
        "investment_authority": "NONE"}
    save(output / "capture.json", encoded(result))
    save(output / "summary.md", readable_summary(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference-ids", required=True, help="Comma-separated explicit current registry IDs; max six securities")
    parser.add_argument("--report-period", required=True, help="YYYY-MM-DD quarter end; no inferred current period")
    args = parser.parse_args()
    expected = "auguspp/decision-kernel/" + WORKFLOW + "@refs/heads/main"
    relay.require(os.environ.get("GITHUB_WORKFLOW_REF") == expected
                  and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
                  and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "B2_INVOCATION_SCOPE")
    identity = {key: os.environ.get(key) for key in
        ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
         "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW_REF", "GITHUB_EVENT_NAME")}
    result = capture(args.output, identity,
        reference_ids=[v.strip() for v in args.reference_ids.split(",")], period=args.report_period)
    print(result["status"])
    # A completed bounded capture can contain explicit data gaps, never silent success.
    return 1 if result["status"] == "STOPPED_WITH_GAPS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
