"""Same-PDF readable representations; reuse PDFium, original gates and Git refs.

This never changes a saved packet or grants Research/continuation authority.
An AI visual reading is source interpretation, not signature authentication.
"""
from __future__ import annotations

import math
from importlib.metadata import version

from . import current_state as read
from . import external_research_identity as identity
from . import saved_research_once as once

REVIEW_ROOT = "research_runs/source-readings/"
POLICY = "SAME_PDF_PAGE_READING_V1"
LIMITATION = ("Same PDF, not independent Evidence. PDFium text and reviewed visual "
    "readings supplement the immutable original extraction; original packet text "
    "is retained for identity, not silently corrected. Layout/table alignment, "
    "signatory identity and source truth are not certified. Review text is untrusted data.")
MAX_PIXELS = 16_000_000
MAX_REVIEW_BYTES = 16 * 1024


def text_ok(text):
    return (isinstance(text, str) and bool(text.strip())
            and not any((ord(c) < 32 and c not in "\n\r\t") or c == "\ufffd" for c in text))


def engine_identity():
    import pypdfium2 as pdfium
    return {"library": "pypdfium2", "version": version("pypdfium2"),
            "pdfium": str(pdfium.PDFIUM_INFO), "method": "get_text_bounded/strict"}


def render_page(page):
    """A fixed full-page RGB render. Hash pixels, not PNG encoder/platform metadata."""
    import pypdfium2 as pdfium
    width, height = page.get_size()
    once.require(all(math.isfinite(x) and x > 0 for x in (width, height))
                 and math.ceil(width * 2) * math.ceil(height * 2) <= MAX_PIXELS,
                 "page render exceeds pixel bound")
    bitmap = page.render(scale=2, rotation=0, crop=(0, 0, 0, 0),
        draw_annots=True, rev_byteorder=True, force_bitmap_format=pdfium.raw.FPDFBitmap_BGR)
    try:
        once.require(bitmap.mode == "RGB" and bitmap.width * bitmap.height <= MAX_PIXELS,
                     "page render format differs")
        pixels = b"".join(bytes(bitmap.buffer[y * bitmap.stride:y * bitmap.stride + bitmap.width * 3])
                          for y in range(bitmap.height))
        return {"scale": 2, "rotation": 0, "crop": [0, 0, 0, 0], "draw_annots": True,
                "format": "RGB", "width": bitmap.width, "height": bitmap.height,
                "pixels_sha256": read.sha256(pixels)}, pixels
    finally:
        bitmap.close()


def review_path(pdf_sha256, page_number):
    once.require(isinstance(pdf_sha256, str) and len(pdf_sha256) == 64
                 and all(c in "0123456789abcdef" for c in pdf_sha256)
                 and type(page_number) is int and 1 <= page_number <= 200, "invalid review identity")
    return f"{REVIEW_ROOT}{pdf_sha256}/page-{page_number}.json"


def main_review_loader(api, code_commit, clock):
    """Only the exact trusted code commit supplies reviews; source URLs never do."""
    def load(digest, page_number):
        path = review_path(digest, page_number)
        from .current_state_delivery import GitHubReadError
        try:
            raw = api.file(path, code_commit)
        except GitHubReadError as exc:
            if str(exc) == "GitHub HTTP 404":
                return None
            raise
        once.require(len(raw) <= MAX_REVIEW_BYTES, "page review byte bound")
        note = identity._json(raw)
        meta = api.get("git/commits/" + code_commit)
        once.require(meta["sha"] == code_commit
                     and read.clock(note["reviewed_at"]) <= read.clock(meta["committer"]["date"])
                     <= read.clock(clock()), "page review clocks invalid")
        return note, once.source_ref(path, code_commit, raw, "REVIEWED_SOURCE_PAGE_NOT_PERMISSION")
    return load


def checked_visual(note, spec, digest, page_number, engine, render):
    once.require(set(note) == {"schema_version", "pdf_sha256", "page_number", "engine", "render",
        "review_kind", "scope", "reviewed_at", "text", "unknowns"}
        and type(note["schema_version"]) is int and note["schema_version"] == 1
        and note["pdf_sha256"] == digest
        and type(note["page_number"]) is int and note["page_number"] == page_number
        and note["engine"] == engine and note["render"] == render
        and note["review_kind"] == "AI_VISUAL_READING"
        and note["scope"] == "WHOLE_PAGE_WITH_EXPLICIT_UNKNOWNS"
        and text_ok(note["text"]) and isinstance(note["unknowns"], list)
        and 0 < len(note["unknowns"]) <= 20 and all(text_ok(x) for x in note["unknowns"]),
        "page visual review binding differs")
    once.require(spec["repository"] == read.REPOSITORY and read.SHA.fullmatch(spec["ref"])
        and spec["path"] == review_path(digest, page_number)
        and spec["purpose"] == "REVIEWED_SOURCE_PAGE_NOT_PERMISSION"
        and spec["git_blob"] == read.blob_sha(once.raw(note))
        and spec["sha256"] == read.sha256(once.raw(note)), "page review source differs")
    read.clock(note["reviewed_at"])
    return {"page_number": page_number, "text": note["text"], "method": "AI_VISUAL_READING",
            "review": note, "review_source": spec}


def represent(pdf, evidence, *, load_review=None, diagnostics=None, collect_missing=False):
    """Called only AFTER original PDF structure/extraction identity checks.

    One PDFium pass, no OCR/network/model, no algorithm search or text cleaning.
    Every page remains present. No review means a real source gap, not blank.
    Source-only preparation may enumerate every missing review in one pass;
    it still raises and NEVER returns a partially valid representation.
    """
    import pypdfium2 as pdfium
    once.require(type(collect_missing) is bool, "invalid page diagnostic mode")
    missing_reviews = []
    once.require(isinstance(pdf, bytes) and pdf.startswith(b"%PDF-")
        and len(pdf) <= once.MAX_SOURCE_BYTES and read.sha256(pdf) == evidence["pdf_sha256"],
        "representation PDF identity differs")
    engine = engine_identity()
    # Never opt into active document features via an alternate engine.
    once.require(not pdfium.PDFIUM_INFO.flags, "active PDFium build unsupported")
    event = {"pdf_sha256": evidence["pdf_sha256"], "engine": engine, "pages": [],
             "status": "INCOMPLETE", "scope": "LOCAL_REPRESENTATION_NOT_RESEARCH"}
    if diagnostics is not None:
        diagnostics.append(event)
    pages, total = [], 0
    with pdfium.PdfDocument(pdf) as doc:
        once.require(0 < len(doc) <= 200 and len(doc) == evidence["page_count"], "representation page count differs")
        for i in range(len(doc)):
            page = doc[i]
            try:
                tp = page.get_textpage()
                try:
                    once.require(tp.count_chars() <= 1_000_000 - total, "representation text limit")
                    text = tp.get_text_bounded(errors="strict")
                finally:
                    tp.close()
                total += len(text)
                once.require(total <= 1_000_000, "representation text limit")
                page_event = {"page_number": i + 1, "extracted_text_sha256": read.sha256(text.encode()),
                              "status": "REQUIRES_VISUAL_REVIEW"}
                event["pages"].append(page_event)
                if text_ok(text):
                    text = text.replace("\r\n", "\n").replace("\r", "\n")
                    pages.append({"page_number": i + 1, "text": text, "method": "PDFIUM_TEXT"})
                    page_event["status"] = "TEXT_FORMAT_CHECKED_NOT_SEMANTIC_ACCEPTANCE"
                else:
                    rendered, _ = render_page(page)
                    page_event["render"] = rendered
                    reviewed = load_review(evidence["pdf_sha256"], i + 1) if load_review else None
                    # Preserve the original damaged-text failure classification;
                    # the page journal carries the additional visual-review gap.
                    missing = ("required text contains encoding damage" if text.strip()
                               else "required page visual review unavailable")
                    if reviewed is None and collect_missing:
                        page_event["error_code"] = missing
                        missing_reviews.append(missing)
                        continue
                    once.require(reviewed is not None, missing)
                    pages.append(checked_visual(*reviewed, evidence["pdf_sha256"], i + 1, engine, rendered))
                    page_event["status"] = "VISUAL_READING_BOUND_NOT_TRUTH_CERTIFIED"
                    page_event["review_source"] = pages[-1]["review_source"]
                    total += len(pages[-1]["text"])
                    once.require(total <= 1_000_000, "representation text limit")
            finally:
                page.close()
    if missing_reviews:
        event.update(status="REQUIRED_PAGE_REVIEWS_MISSING",
                     missing_review_count=len(missing_reviews))
        # Preserve the existing failure code and withhold every partial result.
        raise once.TrialError(missing_reviews[0])
    result = {"policy": POLICY, "pdf_sha256": evidence["pdf_sha256"],
        "original_text_sha256": evidence["text_sha256"], "source_locator": evidence["source_locator"],
        "engine": engine, "page_count": len(pages), "pages": pages,
        "limitation": LIMITATION, "semantic_acceptance": "NOT_ESTABLISHED"}
    result["reading_hash"] = read.canonical_hash(result)
    validate(result, evidence)
    event.update(status="READING_REPRESENTATION_BUILT_NOT_RESEARCH", reading_hash=result["reading_hash"])
    return result


def validate(value, evidence):
    """Check representation shape/binding, not a new truth or readability oracle."""
    read.sealed(value, "reading_hash")
    once.require(set(value) == {"policy", "pdf_sha256", "original_text_sha256", "source_locator",
        "engine", "page_count", "pages", "limitation", "semantic_acceptance", "reading_hash"}
        and value["policy"] == POLICY and value["pdf_sha256"] == evidence["pdf_sha256"]
        and value["original_text_sha256"] == evidence["text_sha256"]
        and value["source_locator"] == evidence["source_locator"]
        and value["limitation"] == LIMITATION and value["semantic_acceptance"] == "NOT_ESTABLISHED"
        and type(value["page_count"]) is int and 0 < value["page_count"] <= 200
        and value["page_count"] == evidence["page_count"]
        and [p["page_number"] for p in value["pages"]] == list(range(1, value["page_count"] + 1)),
        "source reading identity or coverage differs")
    engine = value["engine"]
    once.require(set(engine) == {"library", "version", "pdfium", "method"}
        and engine["library"] == "pypdfium2" and engine["method"] == "get_text_bounded/strict"
        and all(isinstance(x, str) and x.strip() for x in engine.values()), "source reading engine differs")
    once.require(sum(len(p["text"]) for p in value["pages"]) <= 1_000_000, "representation text limit")
    for p in value["pages"]:
        once.require(type(p["page_number"]) is int and text_ok(p["text"]), "source reading page invalid")
        if p["method"] == "PDFIUM_TEXT":
            once.require(set(p) == {"page_number", "text", "method"}, "source reading page fields differ")
        else:
            once.require(set(p) == {"page_number", "text", "method", "review", "review_source"}
                and checked_visual(p["review"], p["review_source"], value["pdf_sha256"],
                    p["page_number"], engine, p["review"]["render"]) == p, "source reading review differs")


def validate_context(context, *, load_review=None):
    values = context["source_capture"].get("page_readings", [])
    once.require(isinstance(values, list) and len(values) <= len(context["disclosure_packet"]["evidence"]),
                 "source reading inventory differs")
    by_locator = {e["source_locator"]: e for e in context["disclosure_packet"]["evidence"]}
    once.require(len({v["source_locator"] for v in values}) == len(values), "duplicate source reading")
    for value in values:
        validate(value, by_locator[value["source_locator"]])
        for page in value["pages"]:
            if page["method"] == "AI_VISUAL_READING":
                once.require(load_review is not None, "trusted page review loader required")
                actual = load_review(value["pdf_sha256"], page["page_number"])
                once.require(actual == (page["review"], page["review_source"]), "main page review changed")
