"""Source-only composition through real source/Industry/prepare gates; I/O is synthetic."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.runtime import industry_question_preparation as prep
from decision_kernel.runtime import saved_research_once as once, current_state as reading
from test_declared_report_input import setup_declared, rebuild
from test_industry_input_continuation import Retainer
from test_pdf_text import _pdf_with_text_pages


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("full preparation must be offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@dataclass
class Announcement:
    stock_code: str
    announcement_id: str
    title: str
    source_locator: str
    published_at: datetime


def two_report_case(tmp_path, monkeypatch):
    c = setup_declared(tmp_path, monkeypatch)
    report = deepcopy(c.manifest["reports"][0])
    route = report["routes"][0]
    report["period"] = "2025FY"
    title = c.q["ticker"] + " Synthetic 2025 annual report"
    pdf = _pdf_with_text_pages(title, "Synthetic complete annual counterevidence")
    parsed = extract_pdf_text(pdf)
    locator = route["locator"].replace(c.context["issuer_documents"][0]["announcement_id"], "1234567891")
    root = route["pdf_source"]["path"].rsplit("/", 1)[0] + "/"
    pdf_name, extraction_name = "2025FY-cninfo-source.pdf", "2025FY-cninfo-extraction.json"
    extracted = {"empty_pages": [], "locator": locator, "page_count": parsed.page_count,
        "pages": [{"page_number": p.page_number, "text": p.text} for p in parsed.pages],
        "pdf_sha256": parsed.pdf_sha256, "representation": "ORIGINAL_PYPDF", "text_sha256": parsed.text_sha256}
    ps = once.source_ref(root + pdf_name, "9a" * 20, pdf, "DECLARED_REPORT_SOURCE_NOT_ADMISSION")
    es = once.source_ref(root + extraction_name, "9b" * 20, once.raw(extracted), "DECLARED_REPORT_SOURCE_NOT_ADMISSION")
    for spec, data in ((ps, pdf), (es, once.raw(extracted))):
        c.api.files[spec["ref"]] = {spec["path"]: data}
        c.commits[spec["ref"]] = {"sha": spec["ref"], "committer": {"date":
            (reading.clock(c.args["clock"]()) - timedelta(minutes=14)).isoformat()}}
    route.update(locator=locator, bytes=len(pdf), page_count=parsed.page_count, pdf_sha256=parsed.pdf_sha256,
        pdf_source={**ps, "bytes": len(pdf)}, extraction_source={**es, "bytes": len(once.raw(extracted))})
    c.declared_files.update({pdf_name: pdf, extraction_name: once.raw(extracted)})
    c.manifest["reports"].insert(0, report)
    declared = deepcopy(c.manifest["plan"]["reports"][0])
    declared.update(period="2025FY", cninfo_locator=locator)
    c.manifest["plan"]["reports"].insert(0, declared)
    request = deepcopy(c.manifest["requests"][0])
    request.update(url=locator, body=pdf_name, bytes=len(pdf), sha256=parsed.pdf_sha256)
    c.manifest["requests"].append(request)
    prepared = json.loads(c.declared_files["git/prepare.json"])
    prepared["plan"] = c.manifest["plan"]
    c.declared_files["git/prepare.json"] = once.raw(prepared)
    c.api.files[c.source_run["head_sha"]][prep.adopted.capture.REQUEST] = once.raw(c.manifest["plan"])
    rebuild(c)
    plan = json.loads(Path(prep.REQUEST).read_bytes())
    plan.pop("resume_from")
    plan.update(id="synthetic-two-report-preparation", profile="synthetic", reading_commit=c.q["reading_source"]["ref"],
                market_session="2026-09-18", updates_end="2026-09-22")
    prior_data = b"Synthetic prior analysis, not a formal invocation."
    prior = once.source_ref("docs/readings/synthetic/prior.md", "9c" * 20, prior_data, "RETAINED_ANALYSIS_PREDECESSOR")
    c.api.files[prior["ref"]] = {prior["path"]: prior_data}
    c.commits[prior["ref"]] = {"sha": prior["ref"], "committer": {"date":
        (reading.clock(c.args["clock"]()) - timedelta(minutes=10)).isoformat()}}
    plan["predecessor_sources"] = [prior]
    plan["titles"] = {"2025FY": title, "2026H1": c.context["issuer_documents"][0]["title"]}
    c.api.files[c.args["code"]][prep.REQUEST] = once.raw(plan)
    # Real source preparation requires an existing work ref. Keep the original
    # model-host fixture's no-work-ref case for its own tests, not this one.
    work = "9d" * 20
    c.api.heads[prep.WORK_REF] = work
    c.api.files[work] = {}
    stamp = reading.clock(c.args["clock"]()).replace(microsecond=0) + timedelta(seconds=1)
    c.args["clock"] = lambda: stamp.isoformat()
    c.commits[work] = {"sha": work, "committer": {"date": stamp.isoformat()}}
    c.api.writes = c.writes
    return c, plan


@pytest.mark.parametrize("correction", [False, True])
def test_source_only_roundtrip_reaches_original_prepare_or_retains_correction_gap(tmp_path, monkeypatch, correction):
    from types import SimpleNamespace
    c, plan = two_report_case(tmp_path, monkeypatch)
    class Native(Retainer):
        def native(self, *args):
            result = super().native(*args)
            ref = result["commit"]["sha"]
            c.commits[ref] = {"sha": ref, "committer": {"date": c.args["clock"]()}}
            return result
    def fetch(**kwargs):
        rows = []
        for report in c.manifest["reports"]:
            route = report["routes"][0]
            rows.append(Announcement(c.q["ticker"], route["locator"].rsplit("/", 1)[1].split(".")[0],
                plan["titles"][report["period"]], route["locator"], reading.clock(report["publication_date"] + "T00:00:00+08:00")))
        if correction:
            rows.append(Announcement(c.q["ticker"], "1234567892", "年度报告更正公告",
                "https://static.cninfo.com.cn/finalpage/2026-09-18/1234567892.PDF", rows[0].published_at))
        return SimpleNamespace(stock_code=c.q["ticker"], start_date=kwargs["start_date"],
                               end_date=kwargs["end_date"], announcements=tuple(rows))
    result = prep.run(api=c.api, code=c.args["code"], output=tmp_path / "prepared", clock=c.args["clock"],
                      fetch=fetch, retainer_factory=Native)
    assert result["model_calls"] == result["research_executions"] == result["pdf_acquisitions"] == 0
    assert c.calls == [] and not result["mutation_uncertain"]
    if correction:
        assert result["error_code"] == "INDUSTRY_REPORT_CORRECTION_BODY_REVIEW_REQUIRED", json.dumps(result, ensure_ascii=False)
        assert "inventory_source" in result and "request_source" not in result
    else:
        assert result["status"] == "INPUT_FILES_RETAINED_NOT_ADMITTED", json.dumps(result, ensure_ascii=False)
        assert result["main_request_activated"] is False and result["formal_admission"] is False
        assert "diagnostics_source" in result
