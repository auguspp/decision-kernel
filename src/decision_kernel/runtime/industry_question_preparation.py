"""Prepare an explicitly declared Industry question from retained reports.

Source-only composition in the existing workflow: no model, research launch,
PDF reacquisition, new provider/scheduler or automatic request activation.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
from datetime import date, timedelta
import os
from pathlib import Path
import re
import time
from uuid import NAMESPACE_URL, uuid5

from ..adapters.pdf_text import extract_pdf_text
from . import current_state as reading, external_research_identity as identity
from . import saved_research_once as once, stock_daily_question as daily
from . import stock_retained_source_import as imports, declared_report_input as adopted
from . import reviewed_full_input as full, disclosure_source_reading as pages
from . import industry_daily_question as industry, reviewed_question_input as reviewed
from . import external_research_admission as admission, cninfo_http as cninfo
from .stock_research_host import authorize, head
from .stock_research_intake import WORK_REF, security
from .stock_question_host import question_execution
from .current_state_delivery import GitHubAPI

REQUEST = "research_runs/industry-question-preparation-request.json"
MODE = "PREPARE_RETAINED_INDUSTRY_QUESTION_INPUT"
LABEL = "industry-question-input-ready"
PREFIX = "research_runs/industry-question-preparation/"
STATIC = ("FULL_ANNUAL_REPORT", "FULL_INTERIM_REPORT")
UPDATE = "FINANCIAL_REPORT_CORRECTION_CHECK"


def check_plan(plan, clock):
    once.require(set(plan) == {"schema_version", "enabled", "mode", "permission", "id", "profile",
        "reading_commit", "market_session", "origin_thscode", "titles", "question",
        "predecessor_sources", "updates_start", "updates_end", "execute_before"}
        and plan["schema_version"] == 1 and plan["enabled"] is True and plan["mode"] == MODE
        and plan["permission"] == industry.PERMISSION
        and re.fullmatch(r"[a-z0-9-]{1,80}", plan["id"])
        and reading.SHA.fullmatch(plan["reading_commit"])
        and plan["origin_thscode"] == "CUZL.SHF"
        and set(plan["titles"]) == {"2025FY", "2026H1"}, "INDUSTRY_PREPARATION_PLAN")
    q = plan["question"]
    once.require(set(q) == {"question_id", "question", "why_now", "falsification_test",
        "known_unknowns", "known_counterevidence", "next_discriminating_search", "mechanism", "materiality_basis"}
        and re.fullmatch(r"[a-z0-9_-]{1,128}", q["question_id"])
        and all(admission.text(q[k]) for k in ("question", "why_now", "falsification_test",
               "next_discriminating_search", "mechanism", "materiality_basis"))
        and 0 < len(plan["predecessor_sources"]) <= 4
        and all(s["purpose"] == "RETAINED_ANALYSIS_PREDECESSOR" for s in plan["predecessor_sources"]),
        "INDUSTRY_PREPARATION_QUESTION")
    now = reading.clock(clock())
    once.require(reading.clock(plan["permission"]["created_at"]) <= now < reading.clock(plan["execute_before"])
        and date.fromisoformat(plan["updates_start"]) <= date.fromisoformat(plan["updates_end"]) <= now.date()
        and date.fromisoformat(plan["market_session"]) <= now.date(), "INDUSTRY_PREPARATION_CLOCK")
    return plan


def request_template(question_source, context_source, preflight_source, review_source, custody_source):
    return {"schema_version": 1, "enabled": True, "mode": daily.MODE, "permission": industry.PERMISSION,
        "question_source": question_source, "context_source": context_source,
        "preflight_source": preflight_source, "approved_egress_hash": None,
        "batch_review_source": review_source, "source_custody_source": custody_source}


def make_documents(profile, files, records, plan, api, code, clock):
    """Full plaintext once; same-PDF proof is rebuilt, not duplicated in model text."""
    docs, custody = [], []
    for source in records:
        route, record = source["route"], source["report"]
        pdf = files[source["pdf_name"]]
        parsed = extract_pdf_text(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES, max_pages=500, max_extracted_chars=1_000_000)
        original = source["extraction"]
        raw_pages = [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]
        once.require(raw_pages == original["pages"] and parsed.text_sha256 == original["text_sha256"],
                     "INDUSTRY_PREPARATION_EXTRACTION")
        title = plan["titles"][record["period"]]
        printed = re.sub(r"\s+", "", "".join(p.text for p in parsed.pages[:10]))
        once.require(profile["case_id"][:6] in printed and re.sub(r"\s+", "", title) in printed,
                     "INDUSTRY_PREPARATION_PRINTED_IDENTITY")
        represented = None
        supplied = raw_pages
        if not all(pages.text_ok(p["text"]) for p in raw_pages):
            value = pages.represent(pdf, {"pdf_sha256": parsed.pdf_sha256, "text_sha256": parsed.text_sha256,
                "page_count": parsed.page_count, "source_locator": route["locator"]},
                load_review=pages.main_review_loader(api, code, clock))
            supplied = [{"page_number": p["page_number"], "text": p["text"]} for p in value["pages"]]
            represented = {"policy": full.PAGE_REFERENCE, "reading_hash": value["reading_hash"], "review_commit": code}
        docs.append({"announcement_id": source["announcement_id"], "title": title,
            "source_locator": route["locator"], "pdf_sha256": parsed.pdf_sha256,
            "original_text_sha256": parsed.text_sha256, "page_count": parsed.page_count,
            "published_at": record["publication_date"] + "T00:00:00+08:00",
            "publication_precision": "DAY_NOT_AVAILABILITY_TIMESTAMP",
            "retrieved_at": source["request"]["received_at"],
            "reading_method": "BOUND_SAME_PDF_READING" if represented else "ORIGINAL_PYPDF",
            "page_reading": represented, "pages": supplied})
        custody.append({"announcement_id": source["announcement_id"], "bytes": len(pdf),
            "pdf_sha256": parsed.pdf_sha256, "page_count": parsed.page_count,
            "pdf_source": {**{k: v for k, v in route["pdf_source"].items() if k != "bytes"},
                           "purpose": "RETAINED_PUBLIC_ISSUER_PDF"}})
    return docs, custody


def classify_update(row, known):
    """Declared report-correction scope, not an all-events or title-truth assertion."""
    if row.announcement_id in known:
        return "BOUND_ORIGINAL_REPORT"
    if (re.search(r"(?:半年度|年度)报告", row.title) and not re.search(r"摘要|董事会|监事会|审计|核查|意见", row.title)) \
            or re.search(r"更正|修订|补充|会计差错|追溯调整", row.title):
        return "REQUIRES_BODY_REVIEW"
    return "OUTSIDE_DECLARED_REPORT_CORRECTION_SCOPE"



def check_inventory_window(batch, plan, ticker, known):
    """A query omitting known reports in its own window is not a no-correction proof."""
    once.require(batch.stock_code == ticker and batch.start_date == date.fromisoformat(plan["updates_start"])
        and batch.end_date == date.fromisoformat(plan["updates_end"])
        and set(known) <= {r.announcement_id for r in batch.announcements},
        "INDUSTRY_UPDATE_INVENTORY_INCOMPLETE")



def make_review(plan, question_source, context_source, rs, section, reviewed_at, case_id):
    projection = section["snapshot"]["projection"]
    rows = sorted(projection["observations"] + projection["invalid_rows"], key=lambda r: r["source_row"])
    items = []
    for row in rows:
        if row.get("lane") != "INDUSTRY_CANDIDATE_CONTEXT" or row.get("source_date_status") != "DATED_SOURCE_CLAIM":
            disposition, reason = "CONTEXT_ONLY", "本行没有本次铜链问题需要的合格产业观察口径；不是无市场变化。"
        elif row["raw"].get("spot_publish_date") != plan["market_session"]:
            disposition, reason = "DATA_UNAVAILABLE", "本行报价日期不同，保留原日期；不并入所选市场日。"
        elif row["raw"].get("thscode") == plan["origin_thscode"]:
            disposition, reason = "SELECTED_FOR_QUESTION", "仅用于已声明的铜链净经济敞口问题；不是公司受益证据或涨跌原因。"
        else:
            disposition, reason = "NOT_SELECTED", "本次有界铜链研究未展开该品种公司经济暴露；不表示无机会。"
        items.append({**industry.row_binding(row), "disposition": disposition, "reason": reason})
    q = plan["question"]
    return {"reading_source": rs, "question_source": question_source, "batch_id": industry.batch_id(rs, section),
        "reviewed_at": reviewed_at, "market_session": plan["market_session"], "items": items,
        "economic_exposure": {"case_id": case_id, "security_id": security(case_id),
            "context_source": context_source, "mechanism": q["mechanism"], "materiality_basis": q["materiality_basis"],
            "counterevidence": "；".join(q["known_counterevidence"]), "falsification_test": q["falsification_test"],
            "use": "QUESTION_FORMATION_NOT_QUANTIFIED_BENEFIT"}}


def run(*, api, code, output, clock=once.now, fetch=cninfo.fetch_cninfo_disclosures, retainer_factory=once.Retainer):
    once.require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 "INDUSTRY_PREPARATION_OUTPUT")
    output.mkdir(parents=True)
    receipt = {"status": "PREPARATION_INCOMPLETE", "code_commit": code, "started_at": clock(),
        "model_calls": 0, "research_executions": 0, "pdf_acquisitions": 0, "query_events": [], **reading.AUTHORITY}
    retain = None
    try:
        plan = check_plan(identity._json(api.file(REQUEST, code)), clock)
        def check():
            check_plan(plan, clock)
            authorize(api, code, plan, request_path=REQUEST, mode=MODE)
        check()
        work, tree = daily.work_tree(api)
        prefix = PREFIX + plan["id"] + "/"
        if any(path.startswith(prefix) for path in tree):
            receipt["status"] = "EXISTING_PREPARATION_NOT_REPEATED"
            return receipt
        once.require(work is not None, "INDUSTRY_PREPARATION_WORK_REF_MISSING")
        retain = retainer_factory(api, {"prefix": prefix, "id": plan["id"], "work_ref": WORK_REF}, code, output)
        retain.save("prepare.json", {"plan": plan, "code_commit": code, "started_at": clock(),
            "run_id": os.environ.get("GITHUB_RUN_ID"), "event": os.environ.get("GITHUB_EVENT_NAME"), **reading.AUTHORITY})
        def save(name, value, purpose):
            check()
            once.require(re.fullmatch(r"(?:context|question|preflight|review|custody|request|inventory|diagnostics|update-query-[0-9]+)\.json", name),
                         "INDUSTRY_PREPARATION_WRITE_SCOPE")
            data = value if isinstance(value, bytes) else once.raw(value)
            once.require(len(data) <= identity.MAX_BYTES, "INDUSTRY_PREPARATION_FILE_SIZE")
            (output / name).write_bytes(data)
            # Git timestamps are whole seconds. Do not backdate source/preflight clocks.
            observed = reading.clock(clock())
            if observed.microsecond:
                target = observed.replace(microsecond=0) + timedelta(seconds=1)
                time.sleep((target-observed).total_seconds())
                once.require(reading.clock(clock()) >= target, "INDUSTRY_PREPARATION_COMMIT_CLOCK")
            result = retain.native("PUT", "contents/" + prefix + name, {"branch": WORK_REF,
                "message": "Retain Industry question preparation: " + name, "content": base64.b64encode(data).decode()})
            retain.uncertain = True
            spec = once.source_ref(prefix + name, result["commit"]["sha"], data, purpose)
            once.require(result["content"]["sha"] == spec["git_blob"] and api.file(spec["path"], spec["ref"]) == data,
                         "INDUSTRY_PREPARATION_READBACK")
            retain.uncertain = False
            retain.writes.append(spec)
            return spec
        registry = identity._json(api.file(imports.IMPORTS_PATH, code))
        profile = registry["imports"][plan["profile"]]
        custody = {"format": adopted.CUSTODY, "source_import": plan["profile"],
            "ticker": profile["case_id"][:6], "checked_at": clock(), "source_run_id": profile["run"]["id"],
            "source_artifact": profile["artifact"]}
        profile, files, records = adopted.load(api, code, custody, clock, {})
        docs, custody["documents"] = make_documents(profile, files, records, plan, api, code, clock)
        context = {"issuer_documents": docs, "source_limitations":
            "完整2025年报和2026H1及同PDF阅读。公告日仅DAY精度，午夜非首次可得时间。"
            "报告更正目录单独按已声明窗口检查；其他临时公告依Human财报优先范围暂缓。"
            "产业报价仅是问题来路，不是公司Evidence。全部页正文保留；图像表阅读不认证经济真相。"}
        plain = once.raw(context)
        packed = full.pack(plain, ticker=custody["ticker"])
        receipt["context_bytes"] = len(plain)
        receipt["stored_context_bytes"] = len(packed)
        cs = save("context.json", packed, "MODEL_CONTEXT")
        custody["context"] = cs
        rs_raw = api.file("current-state.json", plan["reading_commit"])
        rs = once.source_ref("current-state.json", plan["reading_commit"], rs_raw, "SAVED_QUESTION_READING")
        state = identity._json(identity._checked_source(rs, lambda _: rs_raw))
        reading.validate_read_package(state)
        section, origin = industry._native(api, state, rs, clock, {})
        once.require(state["lanes"]["sector"]["last_qualified_result"]["market_session"] == plan["market_session"],
                     "INDUSTRY_PREPARATION_DAY_CHANGED")
        for spec in plan["predecessor_sources"]:
            daily._source(api, spec, "RETAINED_ANALYSIS_PREDECESSOR", clock)
        query = f"CNINFO:{custody['ticker']}:{plan['updates_start']}:{plan['updates_end']}:financial-report-corrections"
        scope = plan["question"]
        q = {"format": reviewed.FORMAT, "case_id": profile["case_id"], "ticker": custody["ticker"],
            "security_id": security(profile["case_id"]), "question_id": scope["question_id"], "revision": 1,
            "predecessor": None, "declared_at": clock(), "reading_source": rs,
            **{k: scope[k] for k in ("question", "why_now", "falsification_test", "known_counterevidence",
                                     "known_unknowns", "next_discriminating_search")},
            "required_classes": [{"id": cid, "mode": "STATIC", "planned_queries": []} for cid in STATIC]
                + [{"id": UPDATE, "mode": "LATEST_INVENTORY", "planned_queries": [query]}],
            "origins": [{"kind": industry.EXTENSION["origin_kind"], "source": origin,
                "observed_at": section["capture"]["receipt"]["received_at"], "qualification": "QUALIFIED_FOR_DECLARED_SCOPE",
                "qualification_reason": "核对原批次、日期与原始行；仅为净经济暴露问题来路，不推断受益。"}],
            "existing_research_relation": {"kind": "CONTINUE_ANALYSIS", "note":
                "延续已保存交互底稿的同一问题；此前未有正式宿主launch，本次是首次正式研究调用。",
                "source_refs": plan["predecessor_sources"]}}
        qs = save("question.json", q, reviewed.PURPOSE)
        pf_start = clock()
        reads = []
        # Actual retained-body reads after the question was frozen, not new HTTP retrievals.
        for i, source in enumerate(records):
            spec = source["route"]["pdf_source"]
            pdf_spec = {**{k: v for k, v in spec.items() if k != "bytes"}, "purpose": "RETAINED_PUBLIC_ISSUER_PDF"}
            daily._retained_pdf(api, pdf_spec, files[source["pdf_name"]], spec["bytes"], clock)
            reads.append({"id": "report-" + str(i), "identity": custody["ticker"] + ":" + source["announcement_id"],
                "locator": source["route"]["locator"], "authority": "PRIMARY", "kind": "BODY", "succeeded": True,
                "checked_at": clock(), "body_sha256": spec["sha256"],
                "tool_reference": "EXACT_RETAINED_GIT_AND_ARTIFACT_BYTE_READ:" + once.locator(pdf_spec)})
        def query_json(method, url, form=None):
            check()
            once.require(url in {cninfo.CNINFO_STOCK_MAP_URL, cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL}
                and len(receipt["query_events"]) < 48, "INDUSTRY_PREPARATION_QUERY_SCOPE")
            event = {"method": method, "url": url, "form": form, "started_at": clock(), "status": "FAILED"}
            receipt["query_events"].append(event)
            try:
                value = cninfo._request_json(url=url, method=method, form=form, timeout_seconds=20)
                event["source"] = save(f"update-query-{len(receipt['query_events'])}.json", once.raw(value), "RECORDED_ISSUER_QUERY")
                event["status"] = "SUCCEEDED"
                return value
            finally: event["finished_at"] = clock()
        inv_start = clock()
        batch = fetch(stock_code=custody["ticker"], start_date=date.fromisoformat(plan["updates_start"]),
            end_date=date.fromisoformat(plan["updates_end"]), get_json=lambda url: query_json("GET", url),
            post_json=lambda url, form: query_json("POST", url, form))
        known = {d["announcement_id"]: (d, reads[i]) for i, d in enumerate(docs)}
        check_inventory_window(batch, plan, custody["ticker"], known)
        leads, unresolved = [], []
        for row in batch.announcements:
            once.require(row.stock_code == custody["ticker"] and row.published_at is not None
                and reading.clock(row.published_at.isoformat()) <= reading.clock(clock()), "INDUSTRY_UPDATE_IDENTITY_OR_TIME")
            kind = classify_update(row, known)
            lead = {"identity": custody["ticker"] + ":" + row.announcement_id, "locator": row.source_locator,
                "authority": "PRIMARY", "decision_relevant": kind != "OUTSIDE_DECLARED_REPORT_CORRECTION_SCOPE",
                "relevance_note": kind + "; 当前仅检查两份完整财报及可能更正，不声称其他事件已审阅。"}
            if kind == "REQUIRES_BODY_REVIEW": unresolved.append(asdict(row))
            elif kind == "BOUND_ORIGINAL_REPORT":
                doc, old_read = known[row.announcement_id]
                once.require(row.source_locator == doc["source_locator"] and row.title == doc["title"], "INDUSTRY_UPDATE_ORIGINAL_CHANGED")
                # Re-read the bound PDF during this inventory window; no acquisition.
                index = docs.index(doc)
                record = custody["documents"][index]
                daily._retained_pdf(api, record["pdf_source"], files[records[index]["pdf_name"]], record["bytes"], clock)
                old_read["checked_at"] = clock()
                lead.update(body_id=old_read["id"], primary_identity=lead["identity"], primary_locator=lead["locator"])
            leads.append(lead)
        inv_end = clock()
        inventory = {"ticker": custody["ticker"], "start_date": plan["updates_start"], "end_date": plan["updates_end"],
            "scope": "TWO_FINANCIAL_REPORTS_AND_POSSIBLE_CORRECTIONS_NOT_ALL_EVENTS",
            "announcements": [{**asdict(r), "published_at": r.published_at.isoformat()} for r in batch.announcements],
            "unresolved_ids": [r["announcement_id"] for r in unresolved],
            "lead_dispositions": leads, "events": receipt["query_events"]}
        inv_source = save("inventory.json", inventory, "RECORDED_FINANCIAL_UPDATE_INVENTORY")
        receipt["inventory_source"] = inv_source
        once.require(not unresolved, "INDUSTRY_REPORT_CORRECTION_BODY_REVIEW_REQUIRED")
        eid = question_execution(q["security_id"], q["question_id"])[0]
        pf_end = clock()
        pf = {"schema_version": 1, "provenance": "RECORDED_TOOL_RETURNS", "case_id": q["case_id"],
            "ticker": q["ticker"], "security_id": q["security_id"], "started_at": pf_start, "finished_at": pf_end,
            "valid_until": (reading.clock(pf_end) + timedelta(hours=2)).isoformat(), "reads": reads,
            "required_classes": [{"id": cid, "mode": "STATIC", "body_ids": [reads[i]["id"]], "inventory_id": None}
                                 for i, cid in enumerate(STATIC)]
                + [{"id": UPDATE, "mode": "LATEST_INVENTORY", "body_ids": [], "inventory_id": "financial-updates"}],
            "inventories": [{"id": "financial-updates", "class_id": UPDATE, "started_at": inv_start, "finished_at": inv_end,
                "planned_queries": [query], "query_events": [{"query": query, "status": "SUCCEEDED",
                    "tool_reference": once.locator(inv_source), "checked_at": inv_end}],
                "leads": [lead for lead in leads if lead["decision_relevant"]]}],
            "limits": {"max_queries": 1, "max_reads": 4}, "seed_publications": [{
                "evidence_id": str(uuid5(NAMESPACE_URL, eid + ":" + cs["sha256"])), "kind": "GIT_COMMIT", "source": cs}],
            "notes": "真实原件读回和声明范围目录；不是全事件覆盖、经济判断或Research执行许可。"}
        admission.check_preflight(once.raw(pf), checked_at=clock())
        ps = save("preflight.json", pf, admission.PREFLIGHT_PURPOSE)
        custody["checked_at"] = clock()
        cus = save("custody.json", custody, daily.EXTRA_SOURCES["source_custody_source"])
        review = make_review(plan, qs, cs, rs, section, clock(), q["case_id"])
        rev = save("review.json", review, industry.PURPOSE)
        request = request_template(qs, cs, ps, rev, cus)
        proposed = save("request.json", request, "PROPOSED_DAILY_REQUEST_NOT_MAIN_ACTIVATION")
        receipt.update(request_source=proposed, question_source=qs, context_source=cs, preflight_source=ps,
                       main_request_activated=False, formal_admission=False)
        # Exercise the ORIGINAL input/source/consumption gates before activation,
        # without an execution reservation, model SDK or reusable admission token.
        from .stock_question_host import _question_inputs
        q, packet, _, decoded, checks = _question_inputs(api=api, code=code,
            request=daily.base_request(request), clock=clock, allow_full=True)
        packet, actual_state, _ = daily.bind(api, request, q, packet, decoded, clock, archives={})
        prepared = reviewed.prepare(question_source=qs, checked_at=clock(),
            **{**checks, "input_raw": once.raw(packet)})
        work, rows = daily.work_tree(api)
        daily.capacity(api, work, rows, actual_state, packet)
        diagnostic = save("diagnostics.json", {"input_prepare": prepared,
            "reader_capacity_checked_at": clock(), "research_execution_allowed": False,
            "model_calls": 0, "reservation_writes": 0}, "PREPARATION_DIAGNOSTICS_NOT_EXECUTION")
        receipt.update(status="INPUT_FILES_RETAINED_NOT_ADMITTED", diagnostics_source=diagnostic)
    except Exception as exc:
        receipt.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", None))
    finally:
        receipt.update(finished_at=clock(), mutation_uncertain=bool(retain and retain.uncertain))
        (output / "preparation-receipt.json").write_bytes(once.raw(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    e = os.environ
    once.require(e.get("GITHUB_REPOSITORY") == once.REPO and e.get("GITHUB_REF") == "refs/heads/main"
        and e.get("GITHUB_SHA") == args.code_commit and reading.SHA.fullmatch(args.code_commit)
        and e.get("GITHUB_WORKFLOW") == "stock-business-research" and e.get("GITHUB_RUN_ATTEMPT") == "1"
        and e.get("GITHUB_EVENT_NAME") == "issues" and e.get("SOURCE_ACTION") == "labeled"
        and e.get("SOURCE_ISSUE") == "297" and e.get("SOURCE_LABEL") == LABEL
        and e.get("SOURCE_SENDER") == "auguspp" and e.get("SOURCE_IS_PR") == "false", "INDUSTRY_PREPARATION_NATIVE_IDENTITY")
    api = GitHubAPI(e["GH_TOKEN"], max_calls=512)
    runs = api.get("actions/runs?head_sha=" + args.code_commit + "&event=push&per_page=30")["workflow_runs"]
    ci = [r for r in runs if r["path"] == ".github/workflows/ci.yml" and r["head_sha"] == args.code_commit
          and r["head_branch"] == "main" and r["event"] == "push"]
    last = max(ci, key=lambda r: r["id"]) if ci else {}
    once.require(last.get("status") == "completed" and last.get("conclusion") == "success"
                 and last.get("run_attempt") == 1, "INDUSTRY_PREPARATION_MAIN_CI")
    result = run(api=api, code=args.code_commit, output=args.output)
    print(result["status"])
    return 0 if result["status"] in {"INPUT_FILES_RETAINED_NOT_ADMITTED", "EXISTING_PREPARATION_NOT_REPEATED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
