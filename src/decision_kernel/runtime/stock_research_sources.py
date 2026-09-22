"""Prepare full official business reports and subsequent issuer announcements.

Reuse CNINFO identity/pagination/PDF transport, original PDF qualification and
same-PDF reading. No model, title-based bullish filtering, OCR or silent clipping.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
import re

from ..adapters.pdf_text import extract_pdf_text
from ..adapters.cninfo import SHANGHAI_TZ
from . import cninfo_http as cninfo
from . import saved_research_once as once
from . import current_state as reading
from . import external_research_identity as identity

CONTEXT_BYTES = 448 * 1024
REPORT = re.compile(r"(20\d{2})年(半年度|年度)报告(?:[（(](?:更正后|修订版|修订后|更新|更新版|修正版|更正版)[）)])?\Z")
AUXILIARY = re.compile(r"关于|摘要|董事|监事|审计|核查|意见|公告|说明|问询|回复|报告")
LEGAL_NAME = re.compile(r"[\u4e00-\u9fffA-Za-z·＆&（）() -]{2,90}(?:股份有限公司|有限责任公司|有限公司)\Z")
SCOPE = ("CNINFO latest full annual/half-year report in a coherent 400-day query, "
         "and ALL disclosures dated on/after the earliest full version of that reporting period within the same query. "
         "Not all issuer channels or full company Research. Full required text is "
         "supplied without clipping. Parsed tables and issuer claims are not truth "
         "certification. Original PDFs and decoded query returns remain in this run artifact. "
         "Source acquisition can follow the price session; this is current research, "
         "not a reconstruction of what was known on the price date.")


def report_match(title, issuer_name=None):
    """Title is discovery only; original row and printed-PDF identity gates remain."""
    title = title.strip()
    match = REPORT.search(title)
    if match is None:
        return None
    prefix = title[:match.start()].strip().rstrip(":：").strip()
    if not prefix:
        return match
    if AUXILIARY.search(prefix):
        return None
    # A short name comes from the identity-bound Stock observation, not free text.
    # A legal-name prefix is still verified against the PDF's printed security.
    bound_legal = (isinstance(issuer_name, str) and bool(issuer_name)
                   and issuer_name in prefix and LEGAL_NAME.fullmatch(prefix))
    return match if prefix == issuer_name or bound_legal else None


def choose(batch, *, checked_at: str, issuer_name=None):
    rows = list(batch.announcements)
    now = reading.clock(checked_at)
    once.require(rows and all(r.published_at is not None and r.published_at <= now for r in rows),
                 "issuer inventory has unknown or future publication")
    reports = []
    for row in rows:
        match = report_match(row.title, issuer_name)
        if match is not None:
            period = date(int(match[1]), 6, 30) if match[2] == "半年度" else date(int(match[1]), 12, 31)
            once.require(period <= now.astimezone(SHANGHAI_TZ).date(), "business report period is in the future")
            reports.append((period, row))
    once.require(reports, "full annual or half-year business report unavailable")
    # A corrected old annual report must not displace a newer reporting period.
    latest_period = max(period for period, _ in reports)
    current = [row for period, row in reports if period == latest_period]
    latest = max(row.published_at for row in current)
    matches = [row for row in current if row.published_at == latest]
    once.require(len(matches) == 1, "latest business report ambiguous")
    report = matches[0]
    # A revised report must not erase risks disclosed since its original version.
    inventory_anchor = min(row.published_at for row in current)
    selected = sorted((r for r in rows if r.published_at >= inventory_anchor),
                      key=lambda r: (r.published_at, r.announcement_id))
    once.require(0 < len(selected) <= 32, "required issuer bodies exceed finite capture capacity")
    return report, selected


def capture(*, ticker: str, observation: dict, api, code_commit: str, output: Path,
            clock=once.now, fetch=cninfo.fetch_cninfo_disclosures,
            fetch_pdf=cninfo.fetch_cninfo_pdf_bytes, extract=extract_pdf_text,
            preparation_only=False):
    """Existing capture; optional source-only inventory is NOT execution admission.

    Only missing page reviews are collected instead of stopping at the first.
    Transport, security, clock, resource and malformed-review errors still raise.
    Default Research capture behavior and all byte limits remain unchanged.
    """
    once.require(type(preparation_only) is bool, "invalid source preparation mode")
    if preparation_only:
        once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                     "unsafe source preparation output")
    output.mkdir(parents=True, exist_ok=False)
    start = clock()
    end_date = reading.clock(start).astimezone(SHANGHAI_TZ).date()
    events, reads, body_events, representation_events = [], [], [], []
    total_pdf = 0
    preparation = {"schema_version": 1, "kind": "SOURCE_PREPARATION_ONLY",
        "ticker": ticker, "code_commit": code_commit, "started_at": start,
        "status": "PREPARATION_INCOMPLETE", "inventory_checked": False,
        "all_planned_bodies_inspected": False, "selected_ids": [],
        "checked_body_ids": [], "unattempted_ids": [], "missing_page_reviews": [],
        "complete_context": None, "research_execution_allowed": False,
        "meaning": "LOCAL_SOURCE_CHECK_NOT_ADMISSION_OR_RESEARCH_RESULT",
        "scope": SCOPE, **reading.AUTHORITY}

    def query(method, url, form=None):
        once.require(url in {cninfo.CNINFO_STOCK_MAP_URL, cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL},
                     "unexpected issuer query endpoint")
        once.require(len(events) < 48, "issuer query capacity exhausted")
        record = {"method": method, "url": url, "form": form, "started_at": clock(),
                  "status": "FAILED", "representation": "DECODED_TOOL_RETURN_NOT_WIRE_BYTES"}
        events.append(record)
        try:
            result = cninfo._request_json(url=url, method=method, form=form, timeout_seconds=20)
            name = "query-" + str(len(events)) + ".json"
            body = once.raw(result)
            once.require(len(body) <= 8 * 1024 * 1024, "issuer decoded query response too large")
            (output / name).write_bytes(body)
            record.update(status="SUCCEEDED", path=name, sha256=once.sha(body))
            return result
        finally:
            record["finished_at"] = clock()

    try:
        batch = fetch(stock_code=ticker, start_date=end_date - timedelta(days=400), end_date=end_date,
            get_json=lambda url: query("GET", url), post_json=lambda url, form: query("POST", url, form))
        inventory_end = clock()
        once.require(batch.stock_code == ticker, "issuer inventory security differs")
        report, selected = choose(batch, checked_at=inventory_end,
                                  issuer_name=observation.get("row", {}).get("company_name"))
        inventory = {"stock_code": batch.stock_code, "org_id": batch.org_id,
            "start_date": batch.start_date.isoformat(), "end_date": batch.end_date.isoformat(),
            "checked_at": inventory_end,
            "announcements": [{**asdict(row), "published_at": row.published_at.isoformat()} for row in batch.announcements],
            "report_id": report.announcement_id,
            "post_report_inventory_anchor": min(r.published_at for r in selected).isoformat(),
            "selected_ids": [r.announcement_id for r in selected]}
        (output / "inventory.json").write_bytes(once.raw(inventory))
        preparation.update(inventory_checked=True, selected_ids=inventory["selected_ids"],
            unattempted_ids=list(inventory["selected_ids"]),
            inventory_sha256=once.sha(once.raw(inventory)))
        documents = []
        for index, row in enumerate(selected, 1):
            event = {"announcement_id": row.announcement_id, "source_locator": row.source_locator,
                     "started_at": clock(), "status": "INCOMPLETE"}
            body_events.append(event)
            preparation["unattempted_ids"].remove(row.announcement_id)
            try:
                pdf = fetch_pdf(source_locator=row.source_locator, max_bytes=once.MAX_SOURCE_BYTES,
                                timeout_seconds=45)
            except Exception as exc:
                event["finished_at"] = clock()
                diagnostic = cninfo.pdf_failure_diagnostic(exc)
                if diagnostic is not None:
                    event["pdf_diagnostic"] = diagnostic
                raise
            total_pdf += len(pdf)
            once.require(total_pdf <= 128 * 1024 * 1024, "issuer total PDF capture capacity")
            digest = once.sha(pdf)
            event.update(pdf_sha256=digest, bytes=len(pdf), captured_at=clock())
            (output / (digest + ".pdf")).write_bytes(pdf)
            parsed = extract(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES, max_pages=500,
                             max_extracted_chars=1_000_000)
            pages = [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]
            once.require(parsed.pdf_sha256 == digest and len(pages) == parsed.page_count
                         and 0 < len(pages) <= 500, "issuer PDF page identity differs")
            evidence = {"pdf_sha256": digest, "text_sha256": parsed.text_sha256, "source_locator": row.source_locator,
                        "page_count": parsed.page_count, "pages": pages}
            (output / (digest + "-extraction.json")).write_bytes(once.raw(evidence))
            # Original extraction is kept separately, never rewritten as the fallback.
            from . import disclosure_source_reading as page_reading
            method = "ORIGINAL_PYPDF"
            represented = None
            if not all(page_reading.text_ok(p["text"]) for p in pages):
                try:
                    represented = page_reading.represent(pdf, evidence,
                        load_review=page_reading.main_review_loader(api, code_commit, clock),
                        diagnostics=representation_events,
                        **({"collect_missing": True} if preparation_only else {}))
                except once.TrialError as exc:
                    if not preparation_only or exc.code not in {
                        "required page visual review unavailable", "required text contains encoding damage"}:
                        raise
                    event.update(status="REQUIRED_PAGE_REVIEWS_MISSING", error_code=exc.code,
                                 finished_at=clock())
                    preparation["missing_page_reviews"].append({
                        "announcement_id": row.announcement_id, "pdf_sha256": digest,
                        "error_code": exc.code,
                        "pages": [p for p in representation_events[-1]["pages"]
                                  if p["status"] == "REQUIRES_VISUAL_REVIEW"]})
                    continue
                page_reading.validate(represented, evidence)
                (output / (digest + "-page-readings.json")).write_bytes(once.raw(represented))
                pages = represented["pages"]
                method = "BOUND_SAME_PDF_READING"
            if row.announcement_id == report.announcement_id:
                first = "".join(p["text"] for p in pages[:10])
                once.require(ticker in first and "报告" in first,
                             "business report printed security identity unavailable")
            documents.append({"announcement_id": row.announcement_id, "title": row.title,
                "published_at": row.published_at.isoformat(), "retrieved_at": clock(),
                "source_locator": row.source_locator, "pdf_sha256": digest,
                "original_text_sha256": parsed.text_sha256, "page_count": parsed.page_count,
                "reading_method": method, "pages": pages, "page_reading": represented})
            event.update(status="FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH", finished_at=clock())
            preparation["checked_body_ids"].append(row.announcement_id)
            reads.append({"id": "body" + str(index), "identity": ticker + ":" + row.announcement_id,
                "locator": row.source_locator, "authority": "PRIMARY", "kind": "BODY", "succeeded": True,
                "checked_at": clock(), "body_sha256": digest,
                "tool_reference": "SAME_RUN_ARTIFACT:" + ticker + (".SH" if ticker.startswith("6") else ".SZ") + "/sources/" + digest + ".pdf"})
        preparation["all_planned_bodies_inspected"] = True
        if preparation_only and preparation["missing_page_reviews"]:
            return preparation
        context = {"stock_observation": observation, "issuer_inventory": inventory,
                   "issuer_documents": documents, "source_limitations": SCOPE}
        if preparation_only:
            # Keep exact whole-context bytes, even when rejected for capacity.
            # A partial document set can never reach this artifact.
            context_raw = once.raw(context)
            (output / "prepared-context.json").write_bytes(context_raw)
            preparation["complete_context"] = {"path": "prepared-context.json",
                "bytes": len(context_raw), "sha256": once.sha(context_raw),
                "limit_bytes": CONTEXT_BYTES, "within_current_limit": len(context_raw) <= CONTEXT_BYTES,
                "source_reference_limit_bytes": identity.MAX_BYTES,
                "within_source_reference_limit": len(context_raw) <= identity.MAX_BYTES}
            if len(context_raw) <= min(CONTEXT_BYTES, identity.MAX_BYTES):
                preparation["status"] = "SOURCES_CHECKED_NOT_EXECUTION_ADMITTED"
            elif len(context_raw) > CONTEXT_BYTES:
                preparation["error_code"] = "full business context too large; no clipping"
            else:
                preparation["error_code"] = "complete source exceeds checked reference byte limit"
            return preparation
        once.require(len(once.raw(context)) <= CONTEXT_BYTES, "full business context too large; no clipping")
        return context, reads, {"started_at": start, "finished_at": clock(),
            "inventory_finished_at": inventory_end, "decoded_query_events": events,
            "scope": SCOPE, "captured_pdf_bytes": total_pdf}
    except Exception as exc:
        if preparation_only:
            preparation.update(error_type=type(exc).__name__)
            diagnostic = cninfo.pdf_failure_diagnostic(exc)
            if diagnostic is not None:
                preparation["pdf_diagnostic"] = diagnostic
            if isinstance(exc, once.TrialError):
                preparation["error_code"] = exc.code
        raise
    finally:
        if preparation_only:
            preparation["finished_at"] = clock()
            (output / "source-preparation.json").write_bytes(once.raw(preparation))
        (output / "source-journal.json").write_bytes(once.raw({"started_at": start,
            "finished_at": clock(), "events": events, "body_events": body_events,
            "representation_events": representation_events, "completed_reads": reads,
            "captured_pdf_bytes": total_pdf, "scope": SCOPE}))


def recheck(context, *, api, code_commit, clock):
    """Recheck the original bound page representation and trusted notes before egress."""
    from . import disclosure_source_reading as page_reading
    load = page_reading.main_review_loader(api, code_commit, clock)
    for doc in context["issuer_documents"]:
        value = doc.get("page_reading")
        if value is None:
            continue
        page_reading.validate(value, {"pdf_sha256": doc["pdf_sha256"],
            "text_sha256": doc["original_text_sha256"], "page_count": doc["page_count"],
            "source_locator": doc["source_locator"]})
        once.require(doc["pages"] == value["pages"], "Stock readable pages differ")
        for page in value["pages"]:
            if page["method"] == "AI_VISUAL_READING":
                once.require(load(value["pdf_sha256"], page["page_number"]) ==
                    (page["review"], page["review_source"]), "Stock main visual reading changed")


def prepare_report_discovery(*, ticker, announcement_date, period, issuer_name, output,
                             discover=None, fetch=None, clock=once.now):
    """FTShare lead -> original CNINFO identity/locator; no PDF/model/custody.

    Separate from capture's legacy all-post-report contract. The caller declares
    one reporting period/date. Neither a provider timestamp without a timezone
    nor url_hash is promoted to primary evidence or a guessed PDF URL.
    """
    from . import ftshare_discovery as ftshare
    once.require(isinstance(period, str) and re.fullmatch(r"20[0-9]{2}(H1|FY)", period),
                 "report discovery period invalid")
    once.require(isinstance(issuer_name, str) and bool(issuer_name.strip()), "report discovery issuer missing")
    once.require(type(announcement_date) is date, "report discovery date invalid")
    end = date(int(period[:4]), 6, 30) if period.endswith("H1") else date(int(period[:4]), 12, 31)
    once.require(end <= announcement_date, "report discovery period follows publication")
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 "unsafe report discovery output")
    output.mkdir(parents=True, exist_ok=False)
    result = {"kind": "REPORT_DISCOVERY_NOT_CUSTODY", "status": "INCOMPLETE",
              "ticker": ticker, "period": period, "started_at": clock(),
              "source_custody": "NOT_ESTABLISHED", "research_execution_allowed": False,
              "model_calls": 0, "pdf_calls": 0, "official_queries": [], **reading.AUTHORITY}
    try:
        discovered = (discover or ftshare.discover)(ticker=ticker, announcement_date=announcement_date,
                                                  output=output / "ftshare", clock=clock)
        result["discovery_status"] = discovered["status"]
        once.require(discovered["status"] == "COMPLETE", "FTShare discovery not complete")
        candidates = []
        for row in discovered["announcements"]:
            match = report_match(row["title"], issuer_name)
            if match and match[1] == period[:4] and ((match[2] == "半年度") == period.endswith("H1")):
                candidates.append(row)
        once.require(len(candidates) == 1, "full report discovery missing or ambiguous")
        lead = candidates[0]
        result["ftshare_lead"] = lead
        def query(method, url, form=None):
            once.require(url in {cninfo.CNINFO_STOCK_MAP_URL, cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL}
                         and len(result["official_queries"]) < 48, "official discovery query scope exceeded")
            event = {"method": method, "url": url, "form": form, "started_at": clock(),
                     "representation": "DECODED_RETURN_NOT_WIRE_BYTES", "status": "FAILED"}
            result["official_queries"].append(event)
            try:
                body = cninfo._request_json(url=url, method=method, form=form, timeout_seconds=20)
                raw = once.raw(body)
                once.require(len(raw) <= 8 * 1024 * 1024, "official discovery response too large")
                name = f"cninfo-query-{len(result['official_queries'])}.json"
                (output / name).write_bytes(raw)
                event.update(status="SUCCEEDED", path=name, sha256=once.sha(raw), bytes=len(raw))
                return body
            finally:
                event["finished_at"] = clock()
        batch = (fetch or cninfo.fetch_cninfo_disclosures)(stock_code=ticker,
            start_date=announcement_date, end_date=announcement_date,
            get_json=lambda url: query("GET", url), post_json=lambda url, form: query("POST", url, form))
        matches = [r for r in batch.announcements if r.announcement_id == lead["announcement_id"]]
        once.require(batch.stock_code == ticker and batch.start_date == batch.end_date == announcement_date
                     and len(matches) == 1, "official report identity differs")
        row = matches[0]
        once.require(row.stock_code == ticker and row.org_id == batch.org_id and row.title == lead["title"]
                     and row.published_at is not None and row.published_at <= reading.clock(clock())
                     and row.published_at.astimezone(SHANGHAI_TZ).date() == announcement_date,
                     "official report identity or time differs")
        result.update(status="OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED",
            official_report={**asdict(row), "published_at": row.published_at.isoformat()},
            provider_time_relation="NOT_EQUATED_WITH_CNINFO_CLOCK")
        return result
    except Exception as exc:
        result.update(status="DISCOVERY_UNAVAILABLE", error_type=type(exc).__name__)
        if isinstance(exc, once.TrialError):
            result["error_code"] = exc.code
        return result
    finally:
        result["finished_at"] = clock()
        (output / "report-discovery.json").write_bytes(once.raw(result))


def prepare_financial_context(*, ticker, year, report_type, output,
                              report_form="合并未调整", fetch=None, clock=once.now):
    """Existing source-preparation consumer; no primary-custody or egress grant."""
    from . import ftshare_financial as financial
    result = financial.prepare(ticker=ticker, year=year, report_type=report_type,
        report_form=report_form, output=output, clock=clock,
        **({"fetch": fetch} if fetch is not None else {}))
    once.require(len(financial.raw_json(result)) <= CONTEXT_BYTES,
                 "full financial context too large; no clipping")
    lines = ["# 财务资料输入 · " + ticker, "",
        "这是次级数据资料，不是已执行研究、原件核验或投资结论。", "",
        f"报告期：{year} {report_type}；报表口径：{report_form}。",
        "利润/现金为年初至报告期末累计数，不是单季数。供应商披露日仅有日期精度。", "",
        "| 数据族 | 本期可用状态 |", "|---|---|"]
    for family, item in result["families"].items():
        lines.append(f"| {family} | {item['status']} |")
    lines += ["", "## 已返回的本期金额（人民币元，未替代原件核对）", "",
              "| 字段 | 供应商口径 | 金额 |", "|---|---|---|"]
    for family in financial.METRICS:
        item = result["families"][family]
        if item["status"] != "SECONDARY_CONTEXT_READY":
            continue
        for field, metric in item["records"][0]["metrics"].items():
            lines.append(f"| {family}.{field} | {metric['label']} | " +
                         (metric["value"] if metric["value"] is not None else "未知") + " |")
    lines += ["", "预告/快报保留原字段；未核清的单位与利润归属不用于数值对比。",
        "parcomp_n_profit保留原名，不自动解释为归母或扣非。",
        "完整原响应、分页、期间排除与逐行来源在同目录JSON中；未返回不等于发行人没有披露。",
        "正式研究仍须原问题、原件、去重、外发和预算校验。", ""]
    (output / "financial-context.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def prepare_company_event_context(*, ticker, start_date, end_date, output,
                                  fetch=None, clock=once.now):
    """Original source entry consumes company events, not automatic Research."""
    from . import ftshare_company_events as events
    from .reviewed_question_reading import _text as _md
    result = events.prepare(ticker=ticker, start_date=start_date, end_date=end_date,
        output=output, clock=clock, **({"fetch": fetch} if fetch is not None else {}))
    once.require(len(events.raw_json(result)) <= CONTEXT_BYTES,
                 "full company event context too large; no clipping")
    lines = ["# 公司事件资料 · " + ticker, "",
        "次级资料，不是原件核验、已执行研究或投资信号。",
        f"公告日期窗口：{start_date} 至 {end_date}；不是当时已知信息的回放。", "",
        "| 数据族 | 状态 | 窗口内记录数 |", "|---|---|---|"]
    for family, item in result["families"].items():
        lines.append(f"| {family} | {item['status']} | {len(item['records'])} |")
    for family, item in result["families"].items():
        if item["status"] != "SECONDARY_CONTEXT_READY":
            continue
        lines += ["", "## " + family, "", "| 公告日 | 事件/观察 | 来源页/行 |", "|---|---|---|"]
        for record in item["records"]:
            row = record["provider_fields"]
            if family == "contracts":
                description = f"{row.get('contract_name') or '合同名称未知'}；金额 {record['contract_amount']['value'] or '未知'}（供应商元，币种未核清）"
            elif family == "holder_counts":
                description = f"持有人统计日 {record['report_date']}；股东人数 {record['holder_count']}"
            else:
                description = f"{record['holder_name']}；{record['direction']}；{record['change_start_date']} 至 {record['change_end_date']}；完成状态未核实"
            lines.append(f"| {record['publish_date']} | {_md(description)} | {family}/{record['raw_page']} 第{record['row_index'] + 1}行 |")
    lines += ["", "合同不等于收入或回款；人数变化不等于具体股东增减持。",
        "增减持保留原始数量，单位未核清不运算；原返回中的价格不是合格行情。",
        "空窗口不等于公司没有事件；原始返回、取得时点及失败详见同目录JSON。",
        "这份资料不会自动授予研究、通知或投资权限。", ""]
    rendered = "\n".join(lines)
    once.require(len(rendered.encode("utf-8")) <= CONTEXT_BYTES,
                 "full company event reading too large; no clipping")
    (output / "company-event-context.md").write_text(rendered, encoding="utf-8")
    return result


def main(argv=None):
    """Explicit source preparation only; no automatic daily execution."""
    import argparse
    parser = argparse.ArgumentParser(description="Prepare report discovery or secondary financial context; no Research")
    parser.add_argument("--mode", choices=["report-discovery", "financial", "company-events"], default="report-discovery")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--announcement-date", type=date.fromisoformat)
    parser.add_argument("--period")
    parser.add_argument("--issuer-name")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--year", type=int)
    parser.add_argument("--report-type", choices=["q1", "q2", "q3", "annual"])
    parser.add_argument("--report-form", choices=["合并未调整", "合并调整"], default="合并未调整")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.mode == "company-events":
        if args.start_date is None or args.end_date is None or any(v is not None for v in
                (args.year, args.report_type, args.announcement_date, args.period, args.issuer_name)):
            parser.error("company-events requires start/end-date only")
        result = prepare_company_event_context(ticker=args.ticker, start_date=args.start_date,
            end_date=args.end_date, output=args.output)
        success = "COMPANY_CONTEXT_PREPARED_NOT_ADMITTED"
    elif args.start_date is not None or args.end_date is not None:
        parser.error("start/end-date requires company-events mode")
    elif args.mode == "financial":
        if args.year is None or args.report_type is None or any(
                v is not None for v in (args.announcement_date, args.period, args.issuer_name)):
            parser.error("financial mode requires year/report-type and no report-discovery inputs")
        result = prepare_financial_context(ticker=args.ticker, year=args.year, report_type=args.report_type,
                                          report_form=args.report_form, output=args.output)
        success = "FINANCIAL_CONTEXT_PREPARED_NOT_ADMITTED"
    else:
        if any(v is None for v in (args.announcement_date, args.period, args.issuer_name)) or any(
                v is not None for v in (args.year, args.report_type)):
            parser.error("report discovery requires announcement-date/period/issuer-name and no financial inputs")
        result = prepare_report_discovery(ticker=args.ticker, announcement_date=args.announcement_date,
            period=args.period, issuer_name=args.issuer_name, output=args.output)
        success = "OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED"
    print(result["status"])
    return 0 if result["status"] == success else 1


if __name__ == "__main__":
    raise SystemExit(main())
