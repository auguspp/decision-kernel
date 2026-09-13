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

CONTEXT_BYTES = 448 * 1024
REPORT = re.compile(r"(20\d{2})年(半年度|年度)报告(?:[（(].*[）)])?\Z")
SCOPE = ("CNINFO latest full annual/half-year report in a coherent 400-day query, "
         "and ALL disclosures dated on/after the earliest full version of that reporting period within the same query. "
         "Not all issuer channels or full company Research. Full required text is "
         "supplied without clipping. Parsed tables and issuer claims are not truth "
         "certification. Original PDFs and decoded query returns remain in this run artifact. "
         "Source acquisition can follow the price session; this is current research, "
         "not a reconstruction of what was known on the price date.")


def choose(batch, *, checked_at: str):
    rows = list(batch.announcements)
    now = reading.clock(checked_at)
    once.require(rows and all(r.published_at is not None and r.published_at <= now for r in rows),
                 "issuer inventory has unknown or future publication")
    reports = []
    for row in rows:
        match = REPORT.fullmatch(row.title.strip())
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
            fetch_pdf=cninfo.fetch_cninfo_pdf_bytes, extract=extract_pdf_text):
    output.mkdir(parents=True, exist_ok=False)
    start = clock()
    end_date = reading.clock(start).astimezone(SHANGHAI_TZ).date()
    events, reads, body_events, representation_events = [], [], [], []
    total_pdf = 0

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
        report, selected = choose(batch, checked_at=inventory_end)
        inventory = {"stock_code": batch.stock_code, "org_id": batch.org_id,
            "start_date": batch.start_date.isoformat(), "end_date": batch.end_date.isoformat(),
            "checked_at": inventory_end,
            "announcements": [{**asdict(row), "published_at": row.published_at.isoformat()} for row in batch.announcements],
            "report_id": report.announcement_id,
            "post_report_inventory_anchor": min(r.published_at for r in selected).isoformat(),
            "selected_ids": [r.announcement_id for r in selected]}
        (output / "inventory.json").write_bytes(once.raw(inventory))
        documents = []
        for index, row in enumerate(selected, 1):
            event = {"announcement_id": row.announcement_id, "source_locator": row.source_locator,
                     "started_at": clock(), "status": "INCOMPLETE"}
            body_events.append(event)
            pdf = fetch_pdf(source_locator=row.source_locator, max_bytes=once.MAX_SOURCE_BYTES,
                            timeout_seconds=45)
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
                represented = page_reading.represent(pdf, evidence,
                    load_review=page_reading.main_review_loader(api, code_commit, clock), diagnostics=representation_events)
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
            reads.append({"id": "body" + str(index), "identity": ticker + ":" + row.announcement_id,
                "locator": row.source_locator, "authority": "PRIMARY", "kind": "BODY", "succeeded": True,
                "checked_at": clock(), "body_sha256": digest,
                "tool_reference": "SAME_RUN_ARTIFACT:" + ticker + (".SH" if ticker.startswith("6") else ".SZ") + "/sources/" + digest + ".pdf"})
        context = {"stock_observation": observation, "issuer_inventory": inventory,
                   "issuer_documents": documents, "source_limitations": SCOPE}
        once.require(len(once.raw(context)) <= CONTEXT_BYTES, "full business context too large; no clipping")
        return context, reads, {"started_at": start, "finished_at": clock(),
            "inventory_finished_at": inventory_end, "decoded_query_events": events,
            "scope": SCOPE, "captured_pdf_bytes": total_pdf}
    finally:
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
