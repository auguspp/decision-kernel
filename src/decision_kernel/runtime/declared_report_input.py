"""Read-only adoption of the original declared-report artifact and same-PDF pages.

No new acquisition or invented legacy inventory/journal. The existing native
artifact, PDF, main-review, preflight and question-host owners retain authority.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import re

from ..adapters.pdf_text import extract_pdf_text
from . import current_state as reading
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_daily_question as daily
from . import stock_retained_source_import as imports
from . import declared_report_sources as capture
from . import disclosure_source_reading as pages
from . import reviewed_full_input as full
from .external_research_execution import ExternalResearchInputPacket

FORMAT = "DECLARED_PUBLIC_REPORT_CAPTURE_V1"
CUSTODY = "DECLARED_REPORTS_SAME_PDF_CUSTODY_V1"


def project(profile, files):
    """Validate exact retained bytes without turning them into an old capture format."""
    expected = profile["files"]
    once.require(set(files) == set(expected) and 0 < len(files) <= 16,
                 "DECLARED_IMPORT_FILE_INVENTORY")
    for name, spec in expected.items():
        data = files[name]
        once.require(reading.safe_path(name) == name and type(spec["bytes"]) is int
            and isinstance(data, bytes) and len(data) == spec["bytes"]
            and once.sha(data) == spec["sha256"] and once.blob(data) == spec["git_blob"],
            "DECLARED_IMPORT_FILE_BYTES")
    manifest = identity._json(files["git/source.json"])
    receipt = identity._json(files["source-receipt.json"])
    prepared = identity._json(files["git/prepare.json"])
    plan = manifest["plan"]
    capture.check_request(plan, lambda: manifest["started_at"])
    once.require(profile["format"] == FORMAT and plan["subject"] == profile["case_id"]
        and prepared["plan"] == receipt["plan"] == plan
        and prepared["event"] == profile["run"]["event"] == "issues"
        and prepared["run_id"] == str(profile["run"]["id"])
        and prepared["code_commit"] == manifest["code_commit"] == receipt["code_commit"]
        == profile["capture_code"] == profile["run"]["head_sha"]
        and manifest["status"] == receipt["status"] == "DECLARED_REPORTS_RETAINED_NOT_RESEARCH"
        and receipt["mutation_uncertain"] is False
        and receipt["source_manifest"] == profile["manifest_source"]
        and all(manifest[k] == receipt[k] for k in ("reports", "requests", "started_at", "acquisition_finished_at"))
        and all(v.get("model_calls") == 0 and v.get("research_executions") == 0
                and v.get("automatic_retry") is False for v in (manifest, receipt))
        and all(all(v.get(k) == expected for k, expected in reading.AUTHORITY.items())
                for v in (manifest, receipt, prepared)), "DECLARED_IMPORT_ORIGINAL_RECEIPT")
    ordered = [manifest["started_at"], prepared["started_at"], manifest["acquisition_finished_at"], receipt["finished_at"]]
    once.require(list(map(reading.clock, ordered)) == sorted(map(reading.clock, ordered)),
                 "DECLARED_IMPORT_ORIGINAL_CLOCK")
    once.require([r["period"] for r in manifest["reports"]] == [r["period"] for r in plan["reports"]],
                 "DECLARED_IMPORT_PERIOD_INVENTORY")
    records = []
    for item, declared in zip(manifest["reports"], plan["reports"], strict=True):
        once.require(item["selected_source"] == "cninfo" and item["publication_date"] == declared["announcement_date"]
            and item["publication_precision"] == "DAY_NOT_AVAILABILITY_TIMESTAMP",
            "DECLARED_IMPORT_SOURCE_SEMANTICS")
        selected = [r for r in item["routes"] if r["provider"] == item["selected_source"]]
        once.require(len(selected) == 1, "DECLARED_IMPORT_SOURCE_AMBIGUOUS")
        route = selected[0]
        locator = route["locator"]
        match = re.fullmatch(r"https://static\.cninfo\.com\.cn/finalpage/"
                            + re.escape(item["publication_date"]) + r"/([0-9]+)\.[Pp][Dd][Ff]", locator)
        once.require(match is not None and route["status"] == "REPORT_PARSED_NOT_ADMITTED"
            and route["provenance"] == "CNINFO_ISSUER_REPORT", "DECLARED_IMPORT_CNINFO_IDENTITY")
        if declared["cninfo_locator"] is not None:
            once.require(locator == declared["cninfo_locator"], "DECLARED_IMPORT_LOCATOR_CHANGED")
        else:
            found = route["discovery"]
            official = found["official_report"]
            once.require(found["status"] == "OFFICIAL_REPORT_LOCATED_NOT_ACQUIRED"
                and official["source_locator"] == locator and official["stock_code"] == plan["subject"][:6]
                and official["announcement_id"] == found["ftshare_lead"]["announcement_id"] == match[1]
                and official["title"] == found["ftshare_lead"]["title"], "DECLARED_IMPORT_DISCOVERY_BINDING")
        pdf_name = PurePosixPath(route["pdf_source"]["path"]).name
        extraction_name = PurePosixPath(route["extraction_source"]["path"]).name
        for name, spec in ((pdf_name, route["pdf_source"]), (extraction_name, route["extraction_source"])):
            once.require(name in files and all(spec[k] == expected[name][k] for k in ("bytes", "sha256", "git_blob")),
                         "DECLARED_IMPORT_SOURCE_REFERENCE")
        requests = [r for r in manifest["requests"] if r["url"] == locator and r.get("body") == pdf_name]
        once.require(len(requests) == 1, "DECLARED_IMPORT_REQUEST_AMBIGUOUS")
        request = requests[0]
        once.require(request["http_status"] == 200 and request["status"] == "HTTP_BODY_RETAINED"
            and request["bytes"] == route["bytes"] == len(files[pdf_name])
            and request["sha256"] == route["pdf_sha256"] == once.sha(files[pdf_name])
            and reading.clock(prepared["started_at"]) <= reading.clock(request["requested_at"])
            <= reading.clock(request["received_at"]) <= reading.clock(request["finished_at"])
            <= reading.clock(manifest["acquisition_finished_at"]), "DECLARED_IMPORT_PDF_REQUEST")
        extraction = identity._json(files[extraction_name])
        once.require(extraction["pdf_sha256"] == route["pdf_sha256"] and extraction["locator"] == locator
            and extraction["page_count"] == route["page_count"], "DECLARED_IMPORT_EXTRACTION")
        records.append({"announcement_id": match[1], "report": item, "route": route, "request": request,
                        "pdf_name": pdf_name, "extraction_name": extraction_name, "extraction": extraction})
    return manifest, receipt, records


def load(api, code, custody, clock, cache):
    registry_raw = api.file(imports.IMPORTS_PATH, code)
    once.require(len(registry_raw) <= identity.MAX_BYTES, "DECLARED_IMPORT_REGISTRY_SIZE")
    registry = identity._json(registry_raw)
    once.require(registry.get("schema_version") == 1 and isinstance(registry.get("imports"), dict)
        and len(registry["imports"]) <= 16 and custody["source_import"] in registry["imports"],
        "DECLARED_IMPORT_NOT_REVIEWED")
    profile = registry["imports"][custody["source_import"]]
    once.require(profile["enabled"] is True and profile["format"] == FORMAT
        and profile["case_id"][:6] == custody["ticker"] and profile["run"]["id"] == custody["source_run_id"]
        and custody["source_artifact"] == profile["artifact"]
        and set(profile["run"]) == {"id", "path", "head_branch", "head_sha", "event"}
        and profile["run"]["path"] == ".github/workflows/stock-business-research.yml"
        and profile["run"]["event"] == "issues" and profile["run"]["head_branch"] == "main"
        and type(profile["run"]["id"]) is int and profile["run"]["id"] > 0
        and reading.SHA.fullmatch(profile["capture_code"])
        and profile["capture_code"] == profile["run"]["head_sha"]
        and profile["artifact"]["name"] == f"declared-report-sources-{profile['run']['id']}-1",
        "DECLARED_IMPORT_PROFILE_BINDING")
    run, files = imports._archive(api, profile, cache)
    manifest, receipt, records = project(profile, files)
    actual, saved_at = daily._source(api, profile["manifest_source"], "source.json", clock)
    once.require(actual == files["git/source.json"]
        # The trusted plan's original bytes need not have our JSON key order.
        # Strict decoding + canonical bytes preserve types and array order.
        and once.raw(identity._json(api.file(capture.REQUEST, profile["capture_code"]))) == once.raw(manifest["plan"])
        and reading.clock(run["run_started_at"]) <= reading.clock(manifest["started_at"])
        <= reading.clock(receipt["finished_at"]) <= reading.clock(run["updated_at"])
        <= reading.clock(custody["checked_at"]) <= reading.clock(clock())
        and reading.clock(saved_at) <= reading.clock(custody["checked_at"]), "DECLARED_IMPORT_RUN_CLOCK_OR_MAIN_PLAN")
    return profile, files, records


def bind_or_legacy(api, request, packet, context, clock, *, archives=None):
    """Industry-only extension; the original small Stock custody path is unchanged."""
    selected_clock = lambda: packet.selected_at.isoformat()
    raw, saved_at = daily._source(api, request["source_custody_source"],
                                 daily.EXTRA_SOURCES["source_custody_source"], selected_clock)
    custody = identity._json(raw)
    if custody.get("format") != CUSTODY:
        return daily.bind_custody(api, request, packet, context, clock, archives=archives)
    once.require(set(custody) == {"format", "source_import", "context", "ticker", "checked_at",
                                  "source_run_id", "source_artifact", "documents"}
        and custody["context"] == request["context_source"] and custody["ticker"] == packet.ticker
        and reading.clock(custody["checked_at"]) <= reading.clock(saved_at), "DECLARED_CUSTODY_SHAPE")
    decoded, bound = full.load_context(request["context_source"], lambda s: api.file(s["path"], s["ref"]),
                                      ticker=packet.ticker, allowed=True)
    once.require(bound is not None and decoded == context, "DECLARED_CUSTODY_FULL_CONTEXT_REQUIRED")
    profile, files, records = load(api, packet.code_commit, custody, selected_clock,
                                   {} if archives is None else archives)
    docs = context["issuer_documents"]
    once.require(profile["case_id"] == packet.case_id and len(docs) == len(records) == len(custody["documents"])
        <= daily.POLICY["max_documents"], "DECLARED_CUSTODY_DOCUMENT_INVENTORY")
    total, refs = 0, list(packet.source_refs)
    full.recheck_pages(context, api=api, code=packet.code_commit, clock=selected_clock)
    for doc, record, source in zip(docs, custody["documents"], records, strict=True):
        route, reported = source["route"], source["report"]
        once.require(record["announcement_id"] == doc["announcement_id"] == source["announcement_id"]
            and doc["source_locator"] == route["locator"]
            and doc["publication_precision"] == reported["publication_precision"] == "DAY_NOT_AVAILABILITY_TIMESTAMP"
            and doc["published_at"] == reported["publication_date"] + "T00:00:00+08:00"
            and doc["retrieved_at"] == source["request"]["received_at"], "DECLARED_CUSTODY_DOCUMENT_IDENTITY")
        expected_pdf = {k: v for k, v in route["pdf_source"].items() if k != "bytes"}
        expected_pdf["purpose"] = "RETAINED_PUBLIC_ISSUER_PDF"
        once.require(record["pdf_source"] == expected_pdf and record["bytes"] == route["bytes"]
            and record["pdf_sha256"] == doc["pdf_sha256"] == route["pdf_sha256"], "DECLARED_CUSTODY_PDF_REFERENCE")
        pdf, pdf_saved = daily._retained_pdf(api, expected_pdf, files[source["pdf_name"]], record["bytes"], selected_clock)
        total += len(pdf)
        once.require(total <= daily.POLICY["max_pdf_bytes"]
            and reading.clock(pdf_saved) <= reading.clock(custody["checked_at"]), "DECLARED_CUSTODY_PDF_LIMIT_OR_CLOCK")
        extraction_spec = {k: v for k, v in route["extraction_source"].items() if k != "bytes"}
        original, _ = daily._source(api, extraction_spec, "DECLARED_REPORT_SOURCE_NOT_ADMISSION", selected_clock)
        once.require(original == files[source["extraction_name"]], "DECLARED_CUSTODY_EXTRACTION_GIT_DIFFERS")
        parsed = extract_pdf_text(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES, max_pages=500, max_extracted_chars=1_000_000)
        original_pages = [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]
        e = source["extraction"]
        printed = re.sub(r"\s+", "", "".join(p.text for p in parsed.pages[:10]))
        once.require(packet.ticker in printed and re.sub(r"\s+", "", doc["title"]) in printed
            and bool(doc["title"].strip()) and parsed.text_sha256 == e["text_sha256"] == doc["original_text_sha256"]
            and parsed.page_count == e["page_count"] == doc["page_count"] == record["page_count"]
            and original_pages == e["pages"], "DECLARED_CUSTODY_ORIGINAL_EXTRACTION_DIFFERS")
        if doc["reading_method"] == "ORIGINAL_PYPDF":
            once.require(doc["page_reading"] is None and doc["pages"] == original_pages
                and all(pages.text_ok(p["text"]) for p in original_pages), "DECLARED_CUSTODY_UNREADABLE_ORIGINAL")
        else:
            once.require(doc["reading_method"] == "BOUND_SAME_PDF_READING", "DECLARED_CUSTODY_REPRESENTATION")
            value = doc["page_reading"]
            by_reference = full.referenced_reading(value)
            if by_reference:
                load_review = full.replay_loader(api, packet.code_commit, value, selected_clock)
            else:
                notes = {p["page_number"]: (p["review"], p["review_source"])
                         for p in value["pages"] if p["method"] == "AI_VISUAL_READING"}
                load_review = lambda digest, number: notes.get(number) if digest == doc["pdf_sha256"] else None
            replayed = pages.represent(pdf, {"pdf_sha256": doc["pdf_sha256"], "text_sha256": e["text_sha256"],
                "source_locator": doc["source_locator"], "page_count": parsed.page_count}, load_review=load_review)
            if by_reference:
                once.require(replayed["reading_hash"] == value["reading_hash"]
                    and doc["pages"] == [{"page_number": p["page_number"], "text": p["text"]} for p in replayed["pages"]],
                    "DECLARED_CUSTODY_PAGE_REPLAY_DIFFERS")
            else:
                once.require(replayed == value and value["pages"] == doc["pages"], "DECLARED_CUSTODY_PAGE_REPLAY_DIFFERS")
        refs.extend((expected_pdf, extraction_spec))
    refs.extend(request[k] for k in daily.EXTRA_SOURCES)
    refs.extend((profile["manifest_source"], once.source_ref(imports.IMPORTS_PATH, packet.code_commit,
        api.file(imports.IMPORTS_PATH, packet.code_commit), "REVIEWED_RETAINED_SOURCE_IMPORT")))
    return ExternalResearchInputPacket.model_validate({**packet.model_dump(mode="json"),
        "source_refs": [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in refs]}), total
