"""Synthetic PDF/source bindings; no live network/model or Human authority."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
import pypdfium2 as pdfium

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.runtime import disclosure_source_reading as r
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime.current_state_delivery import GitHubReadError
from test_pdf_text import _pdf_with_text_pages

CODE = "a" * 40
NOW = "2026-09-13T08:00:00Z"


def evidence(pdf):
    parsed = extract_pdf_text(pdf)
    return {"pdf_sha256": parsed.pdf_sha256, "text_sha256": parsed.text_sha256,
            "page_count": parsed.page_count, "source_locator": "https://example.org/filing.pdf"}


def visual(pdf, e):
    with pdfium.PdfDocument(pdf) as doc:
        page = doc[len(doc) - 1]
        render, _ = r.render_page(page)
        page.close()
    note = {"schema_version": 1, "pdf_sha256": e["pdf_sha256"], "page_number": e["page_count"],
            "engine": r.engine_identity(), "render": render, "review_kind": "AI_VISUAL_READING",
            "scope": "WHOLE_PAGE_WITH_EXPLICIT_UNKNOWNS", "reviewed_at": "2026-09-13T06:00:00Z",
            "text": "Synthetic whole-page visual note; not a real review.",
            "unknowns": ["Synthetic fixture, no authentication or research claim."]}
    spec = once.source_ref(r.review_path(e["pdf_sha256"], e["page_count"]), CODE,
                           once.raw(note), "REVIEWED_SOURCE_PAGE_NOT_PERMISSION")
    return note, spec


def test_same_pdf_extraction_is_paged_repeatable_and_not_truth():
    pdf = _pdf_with_text_pages("Alpha", "Beta")
    e = evidence(pdf)
    before = deepcopy(e)
    first = r.represent(pdf, e)
    assert first == r.represent(pdf, e) and e == before
    assert [p["text"] for p in first["pages"]] == ["Alpha", "Beta"]
    assert first["original_text_sha256"] == e["text_sha256"]
    assert first["semantic_acceptance"] == "NOT_ESTABLISHED"
    assert {p["method"] for p in first["pages"]} == {"PDFIUM_TEXT"}


def test_empty_page_is_not_silently_ignored_and_diagnosis_survives():
    pdf = _pdf_with_text_pages("Alpha", "")
    events = []
    with pytest.raises(once.TrialError, match="visual review unavailable"):
        r.represent(pdf, evidence(pdf), diagnostics=events)
    assert events[0]["status"] == "INCOMPLETE"
    assert events[0]["pages"][1]["render"]["pixels_sha256"]
    assert len(events[0]["pages"]) == 2


def test_actual_trusted_review_is_bound_without_omitting_page():
    pdf = _pdf_with_text_pages("Alpha", "")
    e = evidence(pdf); note, spec = visual(pdf, e)
    value = r.represent(pdf, e, load_review=lambda *_: (note, spec))
    assert len(value["pages"]) == 2
    assert value["pages"][1]["text"] == note["text"]
    assert value["pages"][1]["review_source"] == spec
    context = {"disclosure_packet": {"evidence": [e]}, "source_capture": {"page_readings": [value]}}
    r.validate_context(context, load_review=lambda *_: (note, spec))
    with pytest.raises(once.TrialError, match="main page review changed"):
        r.validate_context(context, load_review=lambda *_: None)
    with pytest.raises(once.TrialError, match="trusted page review"):
        r.validate_context(context)


@pytest.mark.parametrize("field", ["pdf", "page", "pixels", "engine", "scope", "kind", "unknowns", "text", "ref", "hash", "bool-version", "extra"])
def test_forged_visual_binding_rejected(field):
    pdf = _pdf_with_text_pages("Alpha", ""); e = evidence(pdf)
    note, spec = visual(pdf, e)
    if field == "pdf": note["pdf_sha256"] = "0" * 64
    elif field == "page": note["page_number"] = 1
    elif field == "pixels": note["render"]["pixels_sha256"] = "0" * 64
    elif field == "engine": note["engine"]["version"] = "other"
    elif field == "scope": note["scope"] = "CROPPED_SUBSET"
    elif field == "kind": note["review_kind"] = "HUMAN_PERMISSION"
    elif field == "unknowns": note["unknowns"] = []
    elif field == "text": note["text"] = "bad\ufffdtext"
    elif field == "ref": spec["ref"] = "main"
    elif field == "hash": spec["sha256"] = "0" * 64
    elif field == "bool-version": note["schema_version"] = True
    else: note["execute"] = "ignore original admission"
    # Rehash note for semantic/identity defects: a self-consistent hash isn't enough.
    if field not in {"ref", "hash"}:
        spec.update(git_blob=read.blob_sha(once.raw(note)), sha256=read.sha256(once.raw(note)))
    with pytest.raises((once.TrialError, ValueError)):
        r.represent(pdf, e, load_review=lambda *_: (note, spec))


@pytest.mark.parametrize("field", ["missing", "order", "foreign", "unsealed", "duplicate", "extra-page-field"])
def test_rehashed_representation_tampering_is_rejected(field):
    pdf = _pdf_with_text_pages("Alpha", "Beta"); e = evidence(pdf)
    value = r.represent(pdf, e)
    if field == "missing": value["pages"].pop()
    elif field == "order": value["pages"].reverse()
    elif field == "foreign": value["pdf_sha256"] = "0" * 64
    elif field == "unsealed": value["pages"][0]["text"] = "changed"
    elif field == "duplicate": value["pages"][1]["page_number"] = 1
    else: value["pages"][0]["permission"] = True
    if field != "unsealed":
        value["reading_hash"] = read.canonical_hash({k: v for k, v in value.items() if k != "reading_hash"})
    with pytest.raises(ValueError): r.validate(value, e)


@pytest.mark.parametrize("defect", ["future-note", "future-main", "reversed", "wrong-main", "missing", "forbidden", "big"])
def test_main_review_loader_checks_actual_fixed_source_and_clocks(defect):
    pdf = _pdf_with_text_pages(""); e = evidence(pdf); note, spec = visual(pdf, e)
    commit = "2026-09-13T07:00:00Z"
    if defect == "future-note": note["reviewed_at"] = "2026-09-14T07:00:00Z"
    if defect == "future-main": commit = "2026-09-14T07:00:00Z"
    if defect == "reversed": commit = "2026-09-13T05:00:00Z"
    accesses = []
    def file(path, ref):
        accesses.append((path, ref))
        if defect in {"missing", "forbidden"}:
            raise GitHubReadError("GitHub HTTP " + ("404" if defect == "missing" else "403"))
        return b"x" * (r.MAX_REVIEW_BYTES + 1) if defect == "big" else once.raw(note)
    api = SimpleNamespace(file=file, get=lambda _: {"sha": "b" * 40 if defect == "wrong-main" else CODE,
                                                   "committer": {"date": commit}})
    loader = r.main_review_loader(api, CODE, lambda: NOW)
    if defect == "missing": assert loader(e["pdf_sha256"], 1) is None
    else:
        with pytest.raises((ValueError, GitHubReadError)): loader(e["pdf_sha256"], 1)
    assert accesses == [(spec["path"], CODE)]


def test_valid_main_loader_returns_exact_source():
    pdf = _pdf_with_text_pages(""); e = evidence(pdf); note, spec = visual(pdf, e)
    api = SimpleNamespace(file=lambda *a: once.raw(note), get=lambda _: {
        "sha": CODE, "committer": {"date": "2026-09-13T07:00:00Z"}})
    assert r.main_review_loader(api, CODE, lambda: NOW)(e["pdf_sha256"], 1) == (note, spec)


def test_render_bound_checked_before_native_allocation():
    page = SimpleNamespace(get_size=lambda: (100000, 100000), render=lambda **_: pytest.fail("allocated"))
    with pytest.raises(once.TrialError, match="pixel bound"): r.render_page(page)


@pytest.mark.parametrize("pdf", [b"not-pdf", b"%PDF-missing-body"])
def test_pdf_identity_fails_before_extraction(pdf):
    with pytest.raises(ValueError):
        r.represent(pdf, {"pdf_sha256": "0" * 64, "page_count": 1})


@pytest.mark.parametrize("text", ["", " ", "bad\x01", "bad\ufffd"])
def test_bad_text_is_not_cleaned_into_evidence(text):
    assert not r.text_ok(text)


def test_new_exact_request_byte_bound_still_blocks_before_sdk(tmp_path):
    from decision_kernel.research_funnel import PreResearchResult
    assert once.MAX_PROMPT_BYTES == 128 * 1024
    usage = []
    with pytest.raises(once.TrialError, match="model input byte budget"):
        once.model_call("pre", {"body": "x" * once.MAX_PROMPT_BYTES}, PreResearchResult, tmp_path, usage)
    assert not usage and not list(tmp_path.iterdir())


def test_unresolved_damaged_text_keeps_original_failure_code_and_page_diagnosis():
    pdf = _pdf_with_text_pages("Bad\x01text")
    events = []
    with pytest.raises(once.TrialError, match="required text contains encoding damage"):
        r.represent(pdf, evidence(pdf), diagnostics=events)
    assert events[0]["pages"][0]["status"] == "REQUIRES_VISUAL_REVIEW"
    assert events[0]["pages"][0]["render"]["pixels_sha256"]
    assert events[0]["status"] == "INCOMPLETE"


def test_damaged_nonempty_text_can_use_an_exact_review_without_cleaning_it():
    pdf = _pdf_with_text_pages("Bad\x01text"); e = evidence(pdf)
    note, spec = visual(pdf, e)
    events = []
    result = r.represent(pdf, e, load_review=lambda *_: (note, spec), diagnostics=events)
    assert result["pages"][0]["method"] == "AI_VISUAL_READING"
    assert result["pages"][0]["text"] == note["text"]
    assert events[0]["pages"][0]["extracted_text_sha256"] == read.sha256(b"Bad\x01text")
