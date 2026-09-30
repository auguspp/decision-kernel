"""Selected registered securities -> bounded CNINFO capture and readable source fields.

Reuse AKShare's reviewed query, existing custody and original source-only workflow.
Appointments and announcement directories remain separate explicit lookups, not follow/holding or research acceptance.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime
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
MAX_PDF = 512 * 1024
MAX_COMPANIES = 6
MAX_ANNOUNCEMENT_PAGES = 3
ANNOUNCEMENT_URLS = {
    "organization": "https://www.cninfo.com.cn/new/information/topSearch/query",
    "announcements": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
}
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


def select_references(reference_ids, registry_raw, code_commit):
    """Select only explicit IDs from the existing index; never scan all saved stocks."""
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
        # Source text is data, never execution permission.
        plan.append(deepcopy(selected))
    relay.require(len({r["case"] for r in plan}) == len(plan), "B2_DUPLICATE_SECURITY")
    scope = {"ref": code_commit, "path": "current_state/registry.json",
        "git_blob": sha1(f"blob {len(registry_raw)}\0".encode() + registry_raw).hexdigest(),
        "bytes": len(registry_raw), "sha256": sha256(registry_raw).hexdigest(),
        "selected_reference_ids": reference_ids,
        "meaning": "EXPLICIT_SOURCE_LOOKUP_NOT_FOLLOW_HOLDING_OR_AUTOMATIC_ADMISSION"}
    return plan, scope


def plan_requests(reference_ids, period, registry_raw, code_commit):
    relay.require(is_day(period) and period[5:] in ("03-31", "06-30", "09-30", "12-31"),
                  "B2_REPORT_PERIOD")
    selected, scope = select_references(reference_ids, registry_raw, code_commit)
    plan = []
    for record in selected:
        code = record["case"]
        market = {"SH": "sh", "SZ": "sz", "BJ": "bj"}[code[-2:]]
        if code.endswith(".SH") and code.startswith(("688", "689")):
            market = "shkcp"
        plan.append({"code": code, "selection": record,
            "relationship": "NOT_INFERRED_FROM_SOURCE_SELECTION", "report_period": period,
            "params": {"sectionTime": period, "firstTime": "", "lastTime": "",
                "market": market, "stockCode": code[:6], "orderClos": "", "isDesc": "",
                "pagesize": "100", "pagenum": "1"}})
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


def public_request(params, *, clock=relay.now, session_factory=requests.Session, kind="appointments"):
    """One POST, one fresh credential-free session; preserve complete/partial bytes."""
    relay.require(kind in {"appointments", *ANNOUNCEMENT_URLS}, "B2_SOURCE_KIND")
    endpoint = URL if kind == "appointments" else ANNOUNCEMENT_URLS[kind]
    payload = {"params" if kind == "appointments" else "data": params}
    headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
    if kind != "appointments":
        headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn/"})
    result = {"requested_at": clock(), "http_status": None, "headers": {},
              "raw": None, "body_complete": False, "error_type": None}
    chunks = []
    length = 0
    try:
        with session_factory() as session:
            session.trust_env = False  # No netrc or environment proxy credentials.
            with session.post(endpoint, **payload, headers=headers, timeout=(5, 15),
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


def retention_directory(identity, kind="appointments"):
    """Proposed native Git destination, not evidence that files have been saved there."""
    run_id = identity.get("GITHUB_RUN_ID")
    relay.require(isinstance(run_id, str) and re.fullmatch(r"[1-9][0-9]{0,19}", run_id)
                  and identity.get("GITHUB_RUN_ATTEMPT") == "1", "B2_RETENTION_IDENTITY")
    relay.require(kind in {"appointments", "announcements", "pdf"}, "B2_SOURCE_KIND")
    return f"docs/readings/b2-{kind}-{run_id}-1"


def readable_summary(result):
    """Source-only Markdown consumable by the existing saved-document reader."""
    def cell(value):
        return escape(json.dumps(value, ensure_ascii=False), quote=False).replace("|", "&#124;").replace("`", "&#96;")
    lines = ["# 已选证券财报预约 · 标准通道结果", "",
        f"报告期：{result['report_period']}。本次取得结束：{result['finished_at']}。",
        f"整批取得状态：{result['status']}；来源运行：{cell(result['identity'].get('GITHUB_RUN_ID'))}；"
        f"采集代码：{cell(result['identity'].get('GITHUB_SHA'))}。",
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


def save_security_readings(output, result, plan_raw, *, kind="appointments", summary_builder=readable_summary):
    """Reuse flat RETAINED_FILES archives and explicit purpose references.

    Only local create-only output. No registry edits, commit lookup, source request
    or publication. The source ref stays invalid until native Git custody is read back.
    """
    directory = retention_directory(result["identity"], kind)
    purpose = (f"公告原文来源资料（{result['announcement_id']}）" if kind == "pdf" else
               f"财报预约来源资料（{result['report_period']}）" if kind == "appointments" else
               f"公告目录来源资料（{result['publication_window']['start']}至{result['publication_window']['end']}）")
    references = []
    for item in result["outcomes"]:
        target = output / item["code"]
        if item["receipt"] is None:
            target.mkdir()  # Unqueried still gets a reading, never a fake response/receipt.
        # Exact original batch plan, not a newly authored one-stock request/clock.
        save(target / "plan.json", plan_raw)
        view = {**result, "outcomes": [deepcopy(item)]}
        if view["outcomes"][0]["receipt"] is not None:
            view["outcomes"][0]["receipt"] = "receipt.json"
        summary = summary_builder(view)
        save(target / "summary.md", summary)
        references.append({
            "id": f"b2-{kind}-{result['identity']['GITHUB_RUN_ID']}-1-{item['code'].replace('.', '-')}",
            "case": item["code"], "use": "NAVIGATION_ONLY",
            "purpose_note": f"{purpose}；原资料引用{item['reference_id']}。"
                            "仅作来源导航，不是研究、关注、持仓、Watch或投资接受。",
            "read_policy": "ON_DEMAND_ARCHIVE",
            "archive_source": {"path": f"{directory}/{item['code']}/summary.md", "ref": None,
                       "git_blob": sha1(f"blob {len(summary)}\0".encode() + summary).hexdigest(),
                       "bytes": len(summary), "sha256": sha256(summary).hexdigest()},
            "archive": {"format": "RETAINED_FILES"}})
    save(output / "registration-proposal.json", encoded({
        "status": "PROPOSED_NOT_SAVED_REGISTERED_OR_PUBLISHED", "directory": directory,
        "source_commit": "UNBOUND_REQUIRES_NATIVE_GIT_CUSTODY_READBACK",
        "references": references,
        "meaning": "BIND_ONE_VERIFIED_RETENTION_COMMIT_THEN_APPEND_EXPLICIT_REFERENCES; "
                   "NEVER_REPLACE_ORIGINAL_RESEARCH_HUMAN_REFERENCES_OR_RESEARCH_AGENDA"}))


def capture(output, identity, *, reference_ids, period, registry_raw=None,
            request=public_request, clock=relay.now):
    registry_raw = (ROOT / "current_state/registry.json").read_bytes() if registry_raw is None else registry_raw
    plan, scope = plan_requests(reference_ids, period, registry_raw, identity.get("GITHUB_SHA"))
    retention_directory(identity)  # Reject unsafe/unknown run paths before source effects.
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
    save_security_readings(output, result, (output / "plan.json").read_bytes())
    return result


def announcement_summary(result):
    """Directory metadata only: neither PDF custody nor an event-date extractor."""
    def cell(value):
        return escape(json.dumps(value, ensure_ascii=False), quote=False).replace("|", "&#124;").replace("`", "&#96;")
    window = result["publication_window"]
    lines = ["# 已选证券公告目录 · 标准通道结果", "",
        f"公告日期窗口：{window['start']} 至 {window['end']}（Asia/Shanghai）。",
        f"本次取得结束：{result['finished_at']}；状态：{result['status']}。",
        "来源公告时间不是正文中的股东会、解禁、分红实施日；原件链接不是PDF已下载或已阅读。",
        "显式选择仅用于本次目录查询，不建立关注、持仓、Watch、研究接受或提醒。", ""]
    for item in result["outcomes"]:
        lines += [f"## {item['code']}｜{item['status']}", "", f"选择依据：{item['reference_id']}。"]
        if item["receipt"] is None:
            lines += ["来源停止后未查询，不是空目录或没有公司事件。", ""]
            continue
        lines += [f"原请求和响应：{item['receipt']}；实际请求数：{len(item['requests'])}。",
                  f"原始页形：{cell(item['page_shapes'])}。"]
        if item["announcements"] is None:
            lines += ["目录未完整取得或未通过一致性检查；已收到的原始页仍保留，公告数量未知，不记零。", ""]
            continue
        lines += [f"本窗口接口返回 {len(item['announcements'])} 条；不是该公司的完整历史或未来事件清单。", "",
                  "| 公告ID | 来源公告时间 | 标题 | 原件定位（未下载） |", "|---|---|---|---|"]
        for row in item["announcements"]:
            lines.append("| " + " | ".join(cell(row[k]) for k in
                ("announcement_id", "source_announcement_time", "title", "source_locator")) + " |")
        lines.append("")
    lines += ["## 读取限制", "", "机构身份沿原CNINFO解析；原JSON、空值、来源时间和查询时间分别保留。",
        "本次最多每股一次组织码查询及三页公告，每页30条；页数截断、源失败和未查询分别记录。",
        "不按标题推实施日期、取消、改期、研究优先级或投资结论，不去重改写原始页。",
        "Git保存、按需登记、发布、原件恢复与PDF取得均需分别完成；Investment Authority=NONE。", ""]
    return "\n".join(lines).encode("utf-8")


def capture_announcements(output, identity, *, reference_ids, start_date, end_date,
                          registry_raw=None, request=public_request, clock=relay.now):
    """Reuse the original CNINFO batch resolver/parser with a bounded retained transport."""
    from decision_kernel.runtime import cninfo_http as cninfo

    relay.require(is_day(start_date) and is_day(end_date), "B2_PUBLICATION_WINDOW")
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    started = clock()
    observed = datetime.fromisoformat(started)
    relay.require(observed.tzinfo is not None and 0 <= (end - start).days <= 366
                  and end <= observed.astimezone(cninfo.SHANGHAI_TZ).date(), "B2_PUBLICATION_WINDOW")
    registry_raw = (ROOT / "current_state/registry.json").read_bytes() if registry_raw is None else registry_raw
    selected, scope = select_references(reference_ids, registry_raw, identity.get("GITHUB_SHA"))
    retention_directory(identity, "announcements")
    output = Path(output)
    output.mkdir()
    window = {"start": start_date, "end": end_date, "timezone": "Asia/Shanghai"}
    plan_raw = encoded({"identity": identity, "scope_source": scope, "selections": selected,
        "source_kind": "announcements", "source_endpoints": ANNOUNCEMENT_URLS,
        "publication_window": window, "started_at": started,
        "max_requests": len(selected) * (1 + MAX_ANNOUNCEMENT_PAGES), "page_size": 30,
        "max_pages_per_security": MAX_ANNOUNCEMENT_PAGES, "retries": 0, "redirects": False,
        "pdf_requests": 0, "investment_authority": "NONE"})
    save(output / "plan.json", plan_raw)
    outcomes, stopped = [], False
    for chosen in selected:
        code = chosen["case"]
        item = {"code": code, "reference_id": chosen["id"], "registered_use": chosen["use"],
                "status": "NOT_QUERIED_AFTER_STOP", "receipt": None, "requests": [], "page_shapes": [], "announcements": None}
        if not stopped:
            target = output / code
            target.mkdir()

            def retained_post(url, form):
                kind = {cninfo.CNINFO_STOCK_MAP_URL: "organization",
                        cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL: "announcements"}.get(url)
                relay.require(kind is not None, "B2_SOURCE_KIND")
                # The original batch may request further pages; reject BEFORE that HTTP call.
                relay.require(len(item["requests"]) < 1 + MAX_ANNOUNCEMENT_PAGES, "B2_DIRECTORY_PAGE_LIMIT")
                form = dict(form)
                if kind == "announcements":
                    form["column"] = "szse"  # AKShare's reviewed combined SH/SZ/BJ query column.
                ordinal = len(item["requests"]) + 1
                record = {"kind": kind, "endpoint": ANNOUNCEMENT_URLS[kind],
                          "method": "POST", "form": form, "invoked_at": clock()}
                try:
                    response = request(form, kind=kind, clock=clock)
                except Exception as exc:
                    response = {"http_status": None, "raw": None, "body_complete": False,
                                "error_type": type(exc).__name__, "requested_at": record["invoked_at"],
                                "received_at": clock()}
                response = deepcopy(response)
                raw = response.pop("raw")
                response.update(body=None, bytes=None, sha256=None)
                if raw is not None:
                    relay.require(isinstance(raw, bytes) and len(raw) <= MAX_BODY, "B2_RAW_SIZE")
                    name = f"query-{ordinal}.body"
                    save(target / name, raw)
                    response.update(body=name, bytes=len(raw), sha256=sha256(raw).hexdigest())
                record["response"] = response
                save(target / f"query-{ordinal}.json", encoded(record))
                item["requests"].append(record)
                relay.require(response["http_status"] == 200 and response["body_complete"]
                              and not response["error_type"], "B2_DIRECTORY_SOURCE_GAP")
                relay.require(isinstance(raw, bytes), "B2_DIRECTORY_RESPONSE_GAP")
                # Reuse the same duplicate-key guard, retaining arrays for the original org resolver.
                value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=relay._unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
                if kind == "announcements":
                    relay.require(isinstance(value, dict) and value.get("error") in (None, "")
                        and value.get("success", True) is True and value.get("ok", True) is True
                        and (value.get("code") is None or type(value["code"]) is int and value["code"] == 0),
                        "B2_DIRECTORY_RESPONSE_GAP")
                    # Do not let the old parser's missing-row-identity convenience infer an identity.
                    rows = value.get("announcements")
                    relay.require(rows is None or isinstance(rows, list) and len(rows) <= 30,
                                  "B2_DIRECTORY_RESPONSE_GAP")
                    total = value.get("totalAnnouncement")
                    item["page_shapes"].append({"query": ordinal,
                        "table_kind": "NULL" if rows is None else "LIST", "reported_total": total,
                        "returned_rows": None if rows is None else len(rows)})
                    if "hasMore" in value:
                        relay.require(type(total) is int and total >= 0 and type(value["hasMore"]) is bool
                            and value["hasMore"] == (int(form["pageNum"]) * 30 < total),
                            "B2_DIRECTORY_RESPONSE_GAP")
                    for row in rows or []:
                        relay.require(isinstance(row, dict) and row.get("secCode") == code[:6]
                                      and row.get("orgId") == form["stock"].split(",", 1)[1],
                                      "B2_DIRECTORY_IDENTITY_GAP")
                return value

            try:
                batch = cninfo.fetch_cninfo_disclosures(stock_code=code[:6], start_date=start,
                                                       end_date=end, post_json=retained_post)
                rows = []
                received_clock = datetime.fromisoformat(item["requests"][-1]["response"]["received_at"])
                relay.require(received_clock.tzinfo is not None, "B2_DIRECTORY_WINDOW_GAP")
                for row in batch.announcements:
                    relay.require(row.published_at is None or (start <= row.published_at.date() <= end
                                  and row.published_at <= received_clock), "B2_DIRECTORY_WINDOW_GAP")
                    rows.append({"announcement_id": row.announcement_id, "stock_code": row.stock_code,
                        "org_id": row.org_id, "title": row.title, "announcement_type": row.announcement_type,
                        "source_announcement_time": row.published_at.isoformat() if row.published_at else None,
                        "source_locator": row.source_locator})
                item.update(announcements=rows, status=("EMPTY_DIRECTORY_NOT_NO_EVENTS" if not rows else
                    "CAPTURED_WITH_FIELD_GAPS" if any(r["source_announcement_time"] is None for r in rows) else
                    "CAPTURED_REQUIRES_SOURCE_REVIEW"))
            except (ValueError, TypeError, KeyError, OverflowError, cninfo.CninfoRuntimeError) as exc:
                # Only local finite labels/class names: never exception text supplied by sources.
                limited = type(exc) is relay.RelayError and str(exc) == "B2_DIRECTORY_PAGE_LIMIT"
                codes = {"B2_DIRECTORY_PAGE_LIMIT", "B2_DIRECTORY_SOURCE_GAP", "B2_DIRECTORY_RESPONSE_GAP",
                         "B2_DIRECTORY_IDENTITY_GAP", "B2_DIRECTORY_WINDOW_GAP", "DUPLICATE_JSON_KEY"}
                item.update(status="DIRECTORY_PAGE_LIMIT_RAW_RETAINED" if limited else "DIRECTORY_GAP_RAW_RETAINED",
                            error_type=type(exc).__name__, gap_code=(str(exc) if type(exc) is relay.RelayError
                                and str(exc) in codes else "CNINFO_RESPONSE_REJECTED"))
                stopped = not limited
            item["receipt"] = f"{code}/receipt.json"
            save(target / "receipt.json", encoded({"selection": chosen, "publication_window": window,
                "outcome": item, "finished_at": clock(), "pdf_status": "NOT_REQUESTED_LINKS_ONLY",
                "event_dates": "NOT_EXTRACTED_FROM_BODY", "investment_authority": "NONE"}))
        outcomes.append(item)
    gaps = any(o["status"] != "CAPTURED_REQUIRES_SOURCE_REVIEW" for o in outcomes)
    result = {"identity": identity, "source_kind": "announcements", "publication_window": window,
        "outcomes": outcomes, "finished_at": clock(), "research_executed": False, "pdf_requests": 0,
        "investment_authority": "NONE", "status": "STOPPED_WITH_GAPS" if stopped else
        "CAPTURED_WITH_GAPS" if gaps else "CAPTURED_REQUIRES_SOURCE_REVIEW"}
    save(output / "capture.json", encoded(result))
    save(output / "summary.md", announcement_summary(result))
    save_security_readings(output, result, plan_raw, kind="announcements", summary_builder=announcement_summary)
    return result


def pdf_summary(result):
    """Source-only summary; extracted text is not a read or an event-date verdict."""
    item = result["outcomes"][0]
    details = {k: item[k] for k in ("announcement", "source_status", "pdf_getter_invocations",
        "http_status", "getter_return", "pdf", "extraction", "failure")}
    text = "\n".join(["# 已选证券公告原文 · 单PDF标准通道", "",
        f"## {item['code']}｜{item['status']}", "",
        f"选择依据：{item['reference_id']}；明确公告ID：{result['announcement_id']}。",
        f"本次结束：{result['finished_at']}；原记录：receipt.json。",
        "原件及提取结果（仅存在时）：source.pdf / extraction.json；精确定位与失败见下方。",
        "```json", encoded(details).decode().rstrip(), "```", "",
        "原始字节先经原DisclosurePdfCapture保留，再逐字节复制到本平坦目录；"
        "capture-manifest.jsonl保持原清单，清单的objects路径属于原primary-bodies目录，不是本目录相对路径。",
        "原件预算524288字节；不重查目录、不重试、重定向、换源或截断冒充完整PDF。",
        "来源标题中的摘要仍是摘要，不是完整报告。source_announcement_time是公告目录时间，"
        "不是正文事件实施时间；取得/保留时间也不是公告时间。",
        "EXTRACTED仅表示原pypdf文本提取完成；NO_TEXT不是空PDF，也不表示正文已读懂。"
        "人工/交互式正文阅读、表格语义与事件日期核对尚未执行，另行留存，不回写本捕获。",
        "Git保管、用途登记、发布、固定R恢复及Human接受分别成立；"
        "没有研究、关注、持仓、Watch、提醒或投资执行。Investment Authority=NONE。", ""])
    raw = text.encode("utf-8")
    relay.require(len(raw) <= MAX_PDF, "B2_PDF_SUMMARY_LIMIT")
    return raw


def capture_pdf(output, identity, *, reference_ids, announcement_id, reading_commit,
                api, registry_raw=None, fetch_pdf=None, extract=None, clock=relay.now):
    """One selected saved announcement -> original getter/retainer/extractor.

    GitHub reads use their own existing client. Only the original credential-free
    getter contacts CNINFO, once; no directory requests, mirror or source replay.
    """
    from decision_kernel.runtime import cninfo_http as cninfo, research_archive as archive
    from decision_kernel.runtime.disclosure_pdf_capture import DisclosurePdfCapture
    from decision_kernel.adapters.pdf_text import extract_pdf_text

    registry_raw = (ROOT / "current_state/registry.json").read_bytes() if registry_raw is None else registry_raw
    selected, scope = select_references(reference_ids, registry_raw, identity.get("GITHUB_SHA"))
    relay.require(len(selected) == 1 and isinstance(announcement_id, str)
                  and re.fullmatch(r"[0-9]{1,20}", announcement_id) is not None, "B2_SINGLE_PDF_SELECTION")
    relay.require(isinstance(reading_commit, str) and re.fullmatch(r"[0-9a-f]{40}", reading_commit),
                  "B2_PDF_READING_COMMIT")
    retention_directory(identity, "pdf")
    chosen = selected[0]
    relay.require(chosen.get("archive") == {"format": "RETAINED_FILES"}
                  and chosen.get("read_policy") == "ON_DEMAND_ARCHIVE"
                  and chosen.get("use") == "NAVIGATION_ONLY", "B2_PDF_DIRECTORY_REFERENCE")
    output = Path(output); output.mkdir()
    target = output / chosen["case"]; target.mkdir()
    input_dir = output / "input-reading"; input_dir.mkdir()
    plan_raw = encoded({"identity": identity, "scope_source": scope, "selection": chosen,
        "reading_commit": reading_commit, "announcement_id": announcement_id,
        "source_kind": "pdf", "started_at": clock(), "max_pdf_requests": 1,
        "max_pdf_bytes": MAX_PDF, "directory_requests": 0, "retries": 0, "redirects": False,
        "investment_authority": "NONE"})
    save(output / "plan.json", plan_raw)
    item = {"code": chosen["case"], "reference_id": chosen["id"], "registered_use": chosen["use"],
        "status": "PDF_NOT_REQUESTED", "receipt": chosen["case"] + "/receipt.json",
        "announcement": None, "source_status": "NOT_RECOVERED", "pdf_getter_invocations": 0,
        "http_status": None, "getter_return": None, "pdf": None, "extraction": None, "failure": None,
        "body_reading": "NOT_PERFORMED", "event_dates": "NOT_EXTRACTED_FROM_BODY"}
    stage = "SAVED_DIRECTORY_READ"
    try:
        record, source = archive._record(api, reading_commit, chosen["id"], input_dir)
        relay.require(record == chosen and relay.decode((input_dir / "reading.json").read_bytes())["code_commit"]
                      == identity["GITHUB_SHA"], "B2_PDF_READING_CODE_OR_SELECTION")
        path = source["path"]
        relay.require(re.fullmatch(r"docs/readings/b2-announcements-[1-9][0-9]{0,19}-1/"
                      + re.escape(chosen["case"]) + r"/summary\.md", path) is not None,
                      "B2_PDF_DIRECTORY_PATH")
        summary_raw = api.file(path, source["ref"])
        archive._bound(summary_raw, source)
        receipt_path = path.rsplit("/", 1)[0] + "/receipt.json"
        receipt_raw = api.file(receipt_path, source["ref"])
        relay.require(len(receipt_raw) <= MAX_PDF, "B2_PDF_DIRECTORY_SIZE")
        save(target / "directory-receipt.json", receipt_raw)
        prior = relay.decode(receipt_raw)
        outcome = prior["outcome"]
        relay.require(outcome["code"] == chosen["case"] and outcome["status"] in
                      {"CAPTURED_REQUIRES_SOURCE_REVIEW", "CAPTURED_WITH_FIELD_GAPS"}
                      and isinstance(outcome["announcements"], list)
                      and 1 <= len(outcome["announcements"]) <= 90, "B2_PDF_DIRECTORY_RESULT")
        rows = [r for r in outcome["announcements"] if r["announcement_id"] == announcement_id]
        relay.require(len(rows) == 1 and rows[0]["stock_code"] == chosen["case"][:6],
                      "B2_PDF_ANNOUNCEMENT_IDENTITY")
        row = rows[0]
        locator = row["source_locator"]
        match = re.fullmatch(r"https://static\.cninfo\.com\.cn/finalpage/([0-9]{4}-[0-9]{2}-[0-9]{2})/"
                            + re.escape(announcement_id) + r"\.[Pp][Dd][Ff]", locator)
        relay.require(match is not None and is_day(match[1]), "B2_PDF_LOCATOR")
        item.update(announcement=deepcopy(row), source_status="EXACT_SAVED_DIRECTORY_LOCATED",
            directory_source={"ref": source["ref"], "path": receipt_path,
                "git_blob": sha1(f"blob {len(receipt_raw)}\0".encode() + receipt_raw).hexdigest(),
                "bytes": len(receipt_raw), "sha256": sha256(receipt_raw).hexdigest()})

        def bounded_fetch(*, source_locator):
            nonlocal stage
            stage = "PDF_GETTER"
            item["pdf_getter_invocations"] += 1
            item["requested_at"] = clock()
            raw = (fetch_pdf or cninfo.fetch_cninfo_pdf_bytes)(
                source_locator=source_locator, max_bytes=MAX_PDF)
            # The unchanged getter qualifies HTTP 200/complete body. This is not raw header telemetry.
            relay.require(isinstance(raw, bytes) and raw.startswith(b"%PDF-") and len(raw) <= MAX_PDF,
                          "B2_PDF_GETTER_CONTRACT")
            item.update(http_status=200, received_at=clock(), getter_return={"bytes": len(raw),
                "sha256": sha256(raw).hexdigest(), "body_complete": True,
                "http_status_basis": "EXISTING_GETTER_QUALIFICATION_NOT_RECORDED_HEADERS"})
            stage = "PDF_PRIMARY_RETENTION"
            return raw

        capture = DisclosurePdfCapture(output / "primary-bodies", fetch_pdf=bounded_fetch)
        raw = capture.fetch(source_locator=locator)
        stage = "PDF_FLAT_RETENTION"
        save(target / "source.pdf", raw)
        manifest = (output / "primary-bodies/manifest.jsonl").read_bytes()
        save(target / "capture-manifest.jsonl", manifest)
        item["pdf"] = {"path": "source.pdf", "bytes": len(raw), "sha256": sha256(raw).hexdigest(),
            "source_locator": locator, "body_complete": True,
            "original_capture_path": "primary-bodies/objects/" + sha256(raw).hexdigest() + ".pdf",
            "capture_manifest_sha256": sha256(manifest).hexdigest()}
        # complete() belongs to assessment packets; this source-only call must not invoke it.
        stage = "PDF_EXTRACTION"
        parsed = (extract or extract_pdf_text)(raw, max_pdf_bytes=MAX_PDF, max_extracted_chars=MAX_PDF)
        extraction = {"source_locator": locator, "pdf_sha256": parsed.pdf_sha256,
            "text_sha256": parsed.text_sha256, "page_count": parsed.page_count,
            "extracted_char_count": parsed.extracted_char_count, "status": parsed.status.value,
            "pages": [{"page_number": p.page_number, "text": p.text} for p in parsed.pages],
            "representation": "ORIGINAL_PYPDF_NOT_TABLE_OR_EVENT_TRUTH"}
        item["extraction"] = {k: v for k, v in extraction.items() if k != "pages"}
        item["extraction"]["retained"] = False
        relay.require(parsed.pdf_sha256 == sha256(raw).hexdigest(), "B2_PDF_EXTRACTION_IDENTITY")
        stage = "EXTRACTION_RETENTION"
        text_raw = encoded(extraction)
        relay.require(len(text_raw) <= MAX_PDF, "B2_PDF_EXTRACTION_FILE_LIMIT")
        save(target / "extraction.json", text_raw)
        item["extraction"].update(retained=True, path="extraction.json", bytes=len(text_raw),
                                  sha256=sha256(text_raw).hexdigest())
        item["status"] = "PDF_RETAINED_NO_TEXT" if parsed.status.value == "NO_TEXT" else "PDF_RETAINED_TEXT_EXTRACTED"
    except (ValueError, RuntimeError, KeyError, TypeError, OSError) as exc:
        diagnostic = cninfo.pdf_failure_diagnostic(exc)
        local_codes = {"B2_PDF_READING_CODE_OR_SELECTION", "B2_PDF_DIRECTORY_PATH", "B2_PDF_DIRECTORY_SIZE",
            "B2_PDF_DIRECTORY_RESULT", "B2_PDF_ANNOUNCEMENT_IDENTITY", "B2_PDF_LOCATOR",
            "B2_PDF_GETTER_CONTRACT", "B2_PDF_EXTRACTION_IDENTITY", "B2_PDF_EXTRACTION_FILE_LIMIT"}
        local_code = str(exc) if type(exc) is relay.RelayError and str(exc) in local_codes else None
        item.update(status="PDF_STAGE_GAP", failure={"stage": stage, "error_type": type(exc).__name__,
            "diagnostic": diagnostic, "local_code": local_code, "cause": "UNKNOWN"})
        if diagnostic is not None and item["http_status"] is None:
            item["http_status"] = diagnostic["http_status"]
    item["finished_at"] = clock()
    save(target / "receipt.json", encoded(item))
    result = {"identity": identity, "source_kind": "pdf", "announcement_id": announcement_id,
        "reading_commit": reading_commit, "outcomes": [item], "finished_at": clock(),
        "directory_requests": 0, "research_executed": False, "investment_authority": "NONE",
        "status": "STOPPED_WITH_GAPS" if item["failure"] else "CAPTURED_WITH_GAPS"
                  if item["status"] == "PDF_RETAINED_NO_TEXT" else "CAPTURED_REQUIRES_SOURCE_REVIEW"}
    save(output / "capture.json", encoded(result))
    save(output / "summary.md", pdf_summary(result))
    save_security_readings(output, result, plan_raw, kind="pdf", summary_builder=pdf_summary)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference-ids", required=True, help="Comma-separated explicit current registry IDs; max six securities")
    parser.add_argument("--source-kind", choices=("appointments", "announcements", "pdf"), default="appointments")
    parser.add_argument("--report-period", default="", help="Required for appointments: YYYY-MM-DD quarter end")
    parser.add_argument("--start-date", default="", help="Required for announcements: publication window start")
    parser.add_argument("--end-date", default="", help="Required for announcements: publication window end")
    parser.add_argument("--announcement-id", default="", help="PDF only: one exact saved announcement ID")
    parser.add_argument("--reading-commit", default="", help="PDF only: exact published R with current code")
    args = parser.parse_args()
    if args.source_kind != "pdf" and (args.announcement_id or args.reading_commit):
        parser.error("PDF inputs are exclusive to --source-kind pdf")
    if args.source_kind == "appointments":
        if not args.report_period or args.start_date or args.end_date:
            parser.error("appointments requires --report-period and no announcement dates")
    elif args.source_kind == "announcements":
        if not args.start_date or not args.end_date or args.report_period:
            parser.error("announcements requires --start-date/--end-date and no report period")
    elif not args.announcement_id or not args.reading_commit or args.report_period or args.start_date or args.end_date:
        parser.error("pdf requires --announcement-id/--reading-commit and no report period or date window")
    expected = "auguspp/decision-kernel/" + WORKFLOW + "@refs/heads/main"
    relay.require(os.environ.get("GITHUB_WORKFLOW_REF") == expected
                  and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
                  and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "B2_INVOCATION_SCOPE")
    identity = {key: os.environ.get(key) for key in
        ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
         "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW_REF", "GITHUB_EVENT_NAME")}
    reference_ids = [v.strip() for v in args.reference_ids.split(",")]
    if args.source_kind == "pdf":
        from decision_kernel.runtime.current_state_delivery import GitHubAPI
        api = GitHubAPI(os.environ["GH_TOKEN"], max_calls=4)
        try:
            result = capture_pdf(args.output, identity, reference_ids=reference_ids,
                announcement_id=args.announcement_id, reading_commit=args.reading_commit, api=api)
        finally:
            api.session.close()
    else:
        result = (capture(args.output, identity, reference_ids=reference_ids, period=args.report_period)
              if args.source_kind == "appointments" else capture_announcements(args.output, identity,
                  reference_ids=reference_ids, start_date=args.start_date, end_date=args.end_date))
    print(result["status"])
    # A completed bounded capture can contain explicit data gaps, never silent success.
    return 1 if result["status"] == "STOPPED_WITH_GAPS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
