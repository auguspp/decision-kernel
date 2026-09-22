"""Original same-PDF reader at full-report size; no network or Research execution."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import disclosure_source_reading as r
from decision_kernel.runtime import saved_research_once as once
from test_disclosure_source_reading import CODE, evidence, visual
from test_pdf_text import _pdf_with_text_pages

ROOT = Path(__file__).parents[1]
PDF_SHA = "034233ef8b8b392497ed6ad592ca04219eb71c4d4c93aa13a9ed3272e14b2caa"
REVIEW_PAGES = [24, 25, 53, *range(100, 116)]
REVIEW_BLOBS = {24: '75d2abb07388ef1e78f310bf77dc5c4019a6f121', 25: '86760ac5a703f93b3671475d98f33192640c09b8', 53: '4b4f00609b3b68e83a3744b23c59b4aed256d9ee', 100: '90c0ad16e303645ca23d001aaf33c2e96d6edbab', 101: '3ed4291887361dd83dbfd18107b24f98b16507b6', 102: '5ddba2cc122f2eb978b46442ec9476dd0b22e1f7', 103: '4a76cfc8211f62a08fe4d67aa2d93c6400939bb8', 104: 'd9aafa20efdf44355df6902d85b532e06aa79497', 105: 'ca42907478ca895204cd82a84f79d3cebe680e92', 106: 'ee22861d19dd2df15ff81852064755563a1ea32b', 107: '0cf2ce06dea28c8d6dc4785206f42c54c6ab2b17', 108: '10ab7f212789a1f78614a00e2d137073a3d67985', 109: 'bdb63805fc3c3872c0321bfdb927b3e6622824eb', 110: '6bfc10cff9bfa6a0802a010884129b96fc7f8872', 111: 'a4d1ec82e03aebc2ae1a54f3793309ffe4076f1d', 112: '259977d83229b135c9b97872d49e52a9b8db0d0b', 113: '470fcc49769bff94940e6742e336d203dedcf189', 114: '838358531c26412363048a01786d221ba235e4a9', 115: '84b5e910c4abf71933f4a366c283b5f7672b6200'}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("page reading tests cannot use networking")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@pytest.mark.parametrize("count", [201, 216, 262, 500])
def test_existing_reader_preserves_every_large_report_page(count):
    pdf = _pdf_with_text_pages(*(f"physical page {i}" for i in range(1, count + 1)))
    e = evidence(pdf)
    before = deepcopy(e)
    result = r.represent(pdf, e)
    assert e == before and result["page_count"] == count
    assert [p["page_number"] for p in result["pages"]] == list(range(1, count + 1))
    assert [p["text"] for p in result["pages"]] == [f"physical page {i}" for i in range(1, count + 1)]
    assert {p["method"] for p in result["pages"]} == {"PDFIUM_TEXT"}
    assert result["semantic_acceptance"] == "NOT_ESTABLISHED"
    assert result["original_text_sha256"] == e["text_sha256"]
    r.validate(result, e)


def test_report_501_pages_rejected_before_review_or_page_read(monkeypatch):
    pdf = _pdf_with_text_pages(*(["text"] * 501))
    e = evidence(pdf)
    def forbidden(*args):
        pytest.fail("over-limit report reached a page or review")
    monkeypatch.setattr(r, "text_ok", forbidden)
    with pytest.raises(once.TrialError, match="representation page count differs"):
        r.represent(pdf, e, load_review=forbidden)


@pytest.mark.parametrize("number", [201, 262, 500])
def test_page_locator_supports_full_report_boundary(number):
    assert r.review_path(PDF_SHA, number) == f"research_runs/source-readings/{PDF_SHA}/page-{number}.json"


@pytest.mark.parametrize("number", [0, 501, True, 1.5, "201"])
def test_bad_page_locator_still_rejected(number):
    with pytest.raises(once.TrialError, match="invalid review identity"):
        r.review_path(PDF_SHA, number)


def test_last_page_visual_review_reuses_original_binding_and_loader():
    pdf = _pdf_with_text_pages(*(["text"] * 499), "")
    e = evidence(pdf)
    note, source = visual(pdf, e)
    calls = []
    def load(digest, number):
        calls.append((digest, number))
        return note, source
    result = r.represent(pdf, e, load_review=load)
    assert calls == [(e["pdf_sha256"], 500)]
    assert result["pages"][-1]["review_source"] == source
    assert result["pages"][-1]["method"] == "AI_VISUAL_READING"
    assert len(result["pages"]) == 500
    context = {"disclosure_packet": {"evidence": [e]}, "source_capture": {"page_readings": [result]}}
    r.validate_context(context, load_review=load)
    with pytest.raises(once.TrialError, match="main page review changed"):
        r.validate_context(context, load_review=lambda *_: None)


def test_missing_large_report_page_remains_gap_not_blank_or_partial_result():
    pdf = _pdf_with_text_pages(*(["text"] * 200), "")
    events = []
    with pytest.raises(once.TrialError, match="visual review unavailable"):
        r.represent(pdf, evidence(pdf), diagnostics=events, collect_missing=True)
    assert events[0]["status"] == "REQUIRED_PAGE_REVIEWS_MISSING"
    assert events[0]["missing_review_count"] == 1
    assert events[0]["pages"][-1]["page_number"] == 201
    assert events[0]["pages"][-1]["render"]["pixels_sha256"]


@pytest.mark.parametrize("damage", ["missing", "reordered", "foreign", "over-limit"])
def test_large_report_resealed_tampering_still_fails(damage):
    pdf = _pdf_with_text_pages(*(["text"] * 201))
    e = evidence(pdf)
    result = r.represent(pdf, e)
    if damage == "missing": result["pages"].pop()
    elif damage == "reordered": result["pages"].reverse()
    elif damage == "foreign": result["pdf_sha256"] = "0" * 64
    else: result["page_count"] = e["page_count"] = 501
    result["reading_hash"] = r.read.canonical_hash({k: v for k, v in result.items() if k != "reading_hash"})
    with pytest.raises(once.TrialError):
        r.validate(result, e)


def test_page_limit_does_not_increase_other_resource_or_authority_bounds():
    assert r.MAX_PAGES == 500
    assert r.MAX_PIXELS == 16_000_000 and r.MAX_REVIEW_BYTES == 16 * 1024
    assert once.MAX_SOURCE_BYTES == 16 * 1024 * 1024
    assert r.POLICY == "SAME_PDF_PAGE_READING_V1"
    assert "not independent Evidence" in r.LIMITATION


def test_retained_real_review_inventory_has_canonical_original_note_contract():
    # This checks retained review records, NOT images/PDF bytes or company truth.
    directory = ROOT / r.REVIEW_ROOT / PDF_SHA
    files = sorted(directory.glob("page-*.json"), key=lambda p: int(p.stem[5:]))
    assert [int(p.stem[5:]) for p in files] == REVIEW_PAGES
    pixels = set()
    for path in files:
        data = path.read_bytes()
        note = json.loads(data)
        assert data == once.raw(note) and len(data) <= r.MAX_REVIEW_BYTES
        assert once.blob(data) == REVIEW_BLOBS[note["page_number"]]
        assert note["pdf_sha256"] == PDF_SHA and r.text_ok(note["text"])
        assert str(path.relative_to(ROOT)) == r.review_path(PDF_SHA, note["page_number"])
        source = once.source_ref(str(path.relative_to(ROOT)), CODE, data, "REVIEWED_SOURCE_PAGE_NOT_PERMISSION")
        checked = r.checked_visual(note, source, PDF_SHA, note["page_number"], note["engine"], note["render"])
        assert checked["method"] == "AI_VISUAL_READING"
        assert note["engine"] == {"library": "pypdfium2", "version": "5.8.0", "pdfium": "149.0.7825.0", "method": "get_text_bounded/strict"}
        pixels.add(note["render"]["pixels_sha256"])
    assert len(pixels) == len(REVIEW_PAGES)
