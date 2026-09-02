from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO


MAX_PDF_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 2_000
MAX_EXTRACTED_CHARS = 20_000_000


class PdfTextExtractionError(ValueError):
    """A PDF cannot satisfy the bounded text-extraction contract."""


class PdfTextStatus(StrEnum):
    EXTRACTED = "EXTRACTED"
    NO_TEXT = "NO_TEXT"


@dataclass(frozen=True)
class PdfPageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class PagedPdfText:
    pdf_sha256: str
    text_sha256: str
    page_count: int
    extracted_char_count: int
    status: PdfTextStatus
    pages: tuple[PdfPageText, ...]


def extract_pdf_text(
    payload: bytes,
    *,
    max_pdf_bytes: int = MAX_PDF_BYTES,
    max_pages: int = MAX_PDF_PAGES,
    max_extracted_chars: int = MAX_EXTRACTED_CHARS,
) -> PagedPdfText:
    """Extract normalized page text from PDF bytes without doing OCR or I/O.

    This adapter deliberately owns only deterministic PDF qualification and text extraction.
    Fetching, caching, persistence, OCR, search, and Research/Radar interpretation stay outside.
    """

    if not isinstance(payload, bytes):
        raise PdfTextExtractionError("PDF payload must be bytes")
    if min(max_pdf_bytes, max_pages, max_extracted_chars) <= 0:
        raise PdfTextExtractionError("PDF extraction limits must be positive")
    if not payload.startswith(b"%PDF-"):
        raise PdfTextExtractionError("payload does not start with a PDF header")
    if len(payload) > max_pdf_bytes:
        raise PdfTextExtractionError(
            f"PDF exceeds the {max_pdf_bytes}-byte extraction limit"
        )

    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:  # pragma: no cover - exercised by packaging, not unit tests
        raise RuntimeError(
            "PDF text extraction requires the 'documents' extra: "
            "pip install 'decision-kernel[documents]'"
        ) from exc

    try:
        reader = PdfReader(BytesIO(payload), strict=False)
    except (PdfReadError, OSError, TypeError, ValueError) as exc:
        raise PdfTextExtractionError("PDF structure could not be parsed") from exc

    if reader.is_encrypted:
        raise PdfTextExtractionError("encrypted PDFs are not supported")

    try:
        page_count = len(reader.pages)
    except (PdfReadError, KeyError, TypeError, ValueError) as exc:
        raise PdfTextExtractionError("PDF page tree could not be read") from exc
    if page_count > max_pages:
        raise PdfTextExtractionError(
            f"PDF exceeds the {max_pages}-page extraction limit"
        )

    pages: list[PdfPageText] = []
    extracted_char_count = 0
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            extracted = page.extract_text() or ""
        except (PdfReadError, KeyError, TypeError, ValueError) as exc:
            raise PdfTextExtractionError(
                f"PDF text extraction failed on page {page_number}"
            ) from exc
        normalized = _normalize_text(extracted)
        extracted_char_count += len(normalized)
        if extracted_char_count > max_extracted_chars:
            raise PdfTextExtractionError(
                f"PDF text exceeds the {max_extracted_chars}-character extraction limit"
            )
        pages.append(PdfPageText(page_number=page_number, text=normalized))

    frozen_pages = tuple(pages)
    text_identity = json.dumps(
        [
            {"page_number": page.page_number, "text": page.text}
            for page in frozen_pages
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return PagedPdfText(
        pdf_sha256=hashlib.sha256(payload).hexdigest(),
        text_sha256=hashlib.sha256(text_identity).hexdigest(),
        page_count=page_count,
        extracted_char_count=extracted_char_count,
        status=(
            PdfTextStatus.EXTRACTED
            if any(page.text for page in frozen_pages)
            else PdfTextStatus.NO_TEXT
        ),
        pages=frozen_pages,
    )


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return "\n".join(line.rstrip() for line in normalized.split("\n")).strip()
