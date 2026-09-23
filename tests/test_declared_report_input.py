"""Declared artifact through real Industry gates; only HTTP/Git/model edges fake."""
from copy import deepcopy
from datetime import timedelta
import io
import json
import socket
import zipfile

import pytest

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.runtime import saved_research_once as once, current_state as reading
from decision_kernel.runtime import declared_report_sources as capture
from decision_kernel.runtime import declared_report_input as adopted
from decision_kernel.runtime import disclosure_source_reading as pages
from decision_kernel.runtime import stock_retained_source_import as imports
from decision_kernel.runtime import stock_daily_question as daily, stock_question_host as host
from decision_kernel.runtime import reviewed_full_input as full, stock_research_intake as intake
from test_industry_daily_question import setup_industry
from test_reviewed_full_input import seal_full
from test_disclosure_source_reading import visual
from test_pdf_text import _pdf_with_text_pages


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("declared adoption tests cannot use network")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def rebuild(c):
    c.declared_files["git/source.json"] = once.raw(c.manifest)
    spec = c.profile["manifest_source"]
    c.profile["manifest_source"] = once.source_ref(spec["path"], spec["ref"],
        c.declared_files["git/source.json"], "source.json")
    c.api.files[spec["ref"]][spec["path"]] = c.declared_files["git/source.json"]
    c.receipt.update(**deepcopy(c.manifest), source_manifest=c.profile["manifest_source"])
    c.declared_files["source-receipt.json"] = once.raw(c.receipt)
    c.profile["files"] = {name: {"bytes": len(raw), "sha256": once.sha(raw), "git_blob": once.blob(raw)}
                           for name, raw in c.declared_files.items()}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as out:
        for name, raw in c.declared_files.items(): out.writestr(name, raw)
    c.archive_bytes = stream.getvalue()
    c.artifact.update(size_in_bytes=len(c.archive_bytes), digest="sha256:" + once.sha(c.archive_bytes))
    c.profile["artifact"] = {**{k: c.artifact[k] for k in ("id", "name", "size_in_bytes", "digest")},
                             "head_sha": c.source_run["head_sha"]}
    c.custody["source_artifact"] = deepcopy(c.profile["artifact"])
    c.api.files[c.args["code"]][imports.IMPORTS_PATH] = once.raw({"schema_version": 1, "imports": {"synthetic": c.profile}})
    seal_full(c)


def setup_declared(tmp_path, monkeypatch, *, image=False, route="WAIT_FOR_TRIGGER"):
    c = setup_industry(tmp_path, monkeypatch, route)
    now = reading.clock(c.args["clock"]())
    at = lambda minutes: (now - timedelta(minutes=minutes)).isoformat()
    title = "600184 Synthetic 2026 half-year report"
    pdf = _pdf_with_text_pages(title, "" if image else "Complete final report page")
    parsed = extract_pdf_text(pdf)
    doc = c.context["issuer_documents"][0]
    locator = doc["source_locator"]
    doc.update(title=title, published_at="2026-09-18T00:00:00+08:00", retrieved_at=at(15),
        pdf_sha256=once.sha(pdf), original_text_sha256=parsed.text_sha256, page_count=parsed.page_count,
        publication_precision="DAY_NOT_AVAILABILITY_TIMESTAMP",
        pages=[{"page_number": p.page_number, "text": p.text} for p in parsed.pages],
        reading_method="ORIGINAL_PYPDF", page_reading=None)
    root = capture.ROOT + "synthetic-industry-reports/"
    pdf_name, extraction_name = "2026H1-cninfo-source.pdf", "2026H1-cninfo-extraction.json"
    extraction = {"empty_pages": [2] if image else [], "locator": locator,
        "page_count": parsed.page_count, "pages": deepcopy(doc["pages"]),
        "pdf_sha256": parsed.pdf_sha256, "representation": "ORIGINAL_PYPDF",
        "text_sha256": parsed.text_sha256}
    ps = once.source_ref(root + pdf_name, "4" * 40, pdf, "DECLARED_REPORT_SOURCE_NOT_ADMISSION")
    es = once.source_ref(root + extraction_name, "5" * 40, once.raw(extraction), "DECLARED_REPORT_SOURCE_NOT_ADMISSION")
    for spec, data in ((ps, pdf), (es, once.raw(extraction))):
        c.api.files[spec["ref"]][spec["path"]] = data
        c.commits[spec["ref"]] = {"sha": spec["ref"], "committer": {"date": at(14)}}
    c.note_source = None
    if image:
        e = {"pdf_sha256": parsed.pdf_sha256, "text_sha256": parsed.text_sha256,
             "page_count": parsed.page_count, "source_locator": locator}
        note, spec = visual(pdf, e)
        c.api.files[spec["ref"]][spec["path"]] = once.raw(note)
        c.note_source = spec
        value = pages.represent(pdf, e, load_review=lambda *_: (note, spec))
        doc.update(reading_method="BOUND_SAME_PDF_READING", page_reading=value, pages=value["pages"])
    c.context["source_limitations"] += " Synthetic complete scope including risks." * 14500
    plan = {"schema_version": 1, "enabled": True, "mode": capture.MODE,
        "permission": deepcopy(c.request["permission"]), "batch_id": "synthetic-industry-reports",
        "subject": c.q["case_id"], "issuer_name": "Synthetic", "question_id": "synthetic-industry",
        "execute_before": "2026-10-20T00:00:00Z", "reports": [{"period": "2026H1",
            "announcement_date": "2026-09-18", "cninfo_locator": locator, "sina_id": "123"}]}
    c.source_run.update(event="issues")
    c.artifact["name"] = "declared-report-sources-102-1"
    c.api.files[c.source_run["head_sha"]] = {capture.REQUEST: once.raw(plan)}
    prepare = {"plan": plan, "code_commit": c.source_run["head_sha"], "event": "issues",
               "run_id": "102", "started_at": at(16), **reading.AUTHORITY}
    c.manifest = {"plan": plan, "code_commit": c.source_run["head_sha"], "model_calls": 0,
        "research_executions": 0, "automatic_retry": False, "started_at": at(16),
        "acquisition_finished_at": at(14), "status": "DECLARED_REPORTS_RETAINED_NOT_RESEARCH",
        "reports": [{"period": "2026H1", "publication_date": "2026-09-18",
            "publication_precision": "DAY_NOT_AVAILABILITY_TIMESTAMP", "selected_source": "cninfo", "routes": [{
                "provider": "cninfo", "locator": locator, "status": "REPORT_PARSED_NOT_ADMITTED",
                "provenance": "CNINFO_ISSUER_REPORT", "bytes": len(pdf), "page_count": parsed.page_count,
                "pdf_sha256": parsed.pdf_sha256, "pdf_source": {**ps, "bytes": len(pdf)},
                "extraction_source": {**es, "bytes": len(once.raw(extraction))}}]}],
        "requests": [{"url": locator, "body": pdf_name, "http_status": 200,
            "status": "HTTP_BODY_RETAINED", "bytes": len(pdf), "sha256": once.sha(pdf),
            "requested_at": at(16), "received_at": at(15), "finished_at": at(15)}], **reading.AUTHORITY}
    c.receipt = {**deepcopy(c.manifest), "mutation_uncertain": False, "finished_at": at(13)}
    ms = once.source_ref(root + "source.json", "6" * 40, once.raw(c.manifest), "source.json")
    c.commits[ms["ref"]] = {"sha": ms["ref"], "committer": {"date": at(13)}}
    c.profile = {"enabled": True, "format": adopted.FORMAT, "case_id": c.q["case_id"],
        "capture_code": c.source_run["head_sha"], "manifest_source": ms,
        "run": {k: c.source_run[k] for k in ("id", "path", "head_branch", "head_sha", "event")}}
    c.declared_files = {pdf_name: pdf, extraction_name: once.raw(extraction), "git/prepare.json": once.raw(prepare)}
    c.custody = {"format": adopted.CUSTODY, "source_import": "synthetic", "context": c.request["context_source"],
        "ticker": c.q["ticker"], "checked_at": at(7), "source_run_id": 102, "source_artifact": {},
        "documents": [{"announcement_id": doc["announcement_id"], "bytes": len(pdf),
            "pdf_source": {**ps, "purpose": "RETAINED_PUBLIC_ISSUER_PDF"},
            "pdf_sha256": parsed.pdf_sha256, "page_count": parsed.page_count}]}
    c.pf["reads"][0].update(identity=c.q["ticker"] + ":" + doc["announcement_id"], locator=locator,
        body_sha256=parsed.pdf_sha256)
    rebuild(c)
    return c


@pytest.mark.parametrize("image,route,stages", [(False, "WAIT_FOR_TRIGGER", ["pre"]),
    (True, "WAIT_FOR_TRIGGER", ["pre"]), (True, "CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_complete_declared_source_reaches_original_host_without_fake_stock_capture(tmp_path, monkeypatch, image, route, stages):
    c = setup_declared(tmp_path, monkeypatch, image=image, route=route)
    result = host.run_question(**c.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert c.calls == stages and c.archive_calls == [1040, 1020]
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    decoded = full.unpack(saved[c.prefix + "source.json"], ticker=c.q["ticker"])
    assert decoded == once.raw(c.context) and len(decoded) > 512 * 1024
    assert c.source_run["event"] == "issues"
    assert not any("inventory.json" in name or "source-journal" in name for name in c.declared_files)
    assert json.loads(saved[c.prefix + "admission.json"])["research_execution_allowed"] is True
    assert result["investment_authority"] == "NONE"


@pytest.mark.parametrize("damage", ["pdf-bytes", "extraction-bytes", "missing-file", "model-calls",
    "wrong-event", "expired", "wrong-period", "wrong-precision", "wrong-title",
    "page-text", "current-note", "original-plan", "native-extraction", "wrong-case"])
def test_declared_import_failure_never_reserves_or_calls_model(tmp_path, monkeypatch, damage):
    c = setup_declared(tmp_path, monkeypatch, image=True)
    doc = c.context["issuer_documents"][0]
    if damage == "pdf-bytes": c.declared_files["2026H1-cninfo-source.pdf"] += b"changed"
    elif damage == "extraction-bytes": c.declared_files["2026H1-cninfo-extraction.json"] += b"changed"
    elif damage == "missing-file": del c.declared_files["2026H1-cninfo-extraction.json"]
    elif damage == "model-calls": c.manifest["model_calls"] = 1
    elif damage == "wrong-event": c.source_run["event"] = "workflow_dispatch"
    elif damage == "expired": c.artifact["expired"] = True
    elif damage == "wrong-period": c.manifest["reports"][0]["period"] = "2025FY"
    elif damage == "wrong-precision": doc["publication_precision"] = "EXACT_FIRST_AVAILABLE"
    elif damage == "wrong-title": doc["title"] = "Other company invented report"
    elif damage == "page-text": doc["pages"][0]["text"] += " tampered"
    elif damage == "current-note":
        spec = c.note_source
        c.api.files[c.args["code"]][spec["path"]] += b"changed"
    elif damage == "original-plan": c.api.files[c.source_run["head_sha"]][capture.REQUEST] = once.raw({})
    elif damage == "native-extraction":
        spec = c.manifest["reports"][0]["routes"][0]["extraction_source"]
        c.api.files[spec["ref"]][spec["path"]] += b"changed"
    else: c.profile["case_id"] = "600362.SH"
    rebuild(c)
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert not result["formal_research_started"] and c.calls == [] and c.writes == []
