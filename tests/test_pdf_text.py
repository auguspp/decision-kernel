from __future__ import annotations

from decision_kernel.adapters.pdf_text import (
    PdfTextExtractionError,
    PdfTextStatus,
    extract_pdf_text,
)


def _pdf_with_text_pages(*texts: str) -> bytes:
    """Build a tiny deterministic Type1-font PDF without another test dependency."""

    if not texts:
        texts = ("",)
    font_id = 3 + 2 * len(texts)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            f"<< /Type /Pages /Kids [{' '.join(f'{3 + 2 * i} 0 R' for i in range(len(texts)))}] "
            f"/Count {len(texts)} >>"
        ).encode("ascii"),
    ]

    for index, text in enumerate(texts):
        page_id = 3 + 2 * index
        content_id = page_id + 1
        escaped = (
            text.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        content = f"BT /F1 12 Tf 50 250 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            b"<< /Length "
            + str(len(content)).encode("ascii")
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    parts = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(sum(len(part) for part in parts))
        parts.append(
            f"{object_number} 0 obj\n".encode("ascii")
            + body
            + b"\nendobj\n"
        )

    xref_offset = sum(len(part) for part in parts)
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii")]
    xref.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return b"".join(parts + xref + [trailer])


def test_extract_pdf_text_preserves_page_boundaries_and_identity() -> None:
    payload = _pdf_with_text_pages("Alpha", "Beta")

    first = extract_pdf_text(payload)
    second = extract_pdf_text(payload)

    assert first.status is PdfTextStatus.EXTRACTED
    assert first.page_count == 2
    assert first.extracted_char_count == len("AlphaBeta")
    assert tuple((page.page_number, page.text) for page in first.pages) == (
        (1, "Alpha"),
        (2, "Beta"),
    )
    assert first.pdf_sha256 == second.pdf_sha256
    assert first.text_sha256 == second.text_sha256


def test_extract_pdf_text_marks_scanned_or_blank_like_pdf_as_no_text() -> None:
    result = extract_pdf_text(_pdf_with_text_pages(""))

    assert result.status is PdfTextStatus.NO_TEXT
    assert result.page_count == 1
    assert result.extracted_char_count == 0
    assert result.pages[0].text == ""


def test_extract_pdf_text_rejects_non_pdf_payload() -> None:
    try:
        extract_pdf_text(b"not a pdf")
    except PdfTextExtractionError as exc:
        assert "PDF header" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("non-PDF payload should fail closed")


def test_extract_pdf_text_enforces_page_limit() -> None:
    payload = _pdf_with_text_pages("Alpha", "Beta")

    try:
        extract_pdf_text(payload, max_pages=1)
    except PdfTextExtractionError as exc:
        assert "page extraction limit" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("page limit should fail closed")


def test_extract_pdf_text_enforces_character_limit() -> None:
    payload = _pdf_with_text_pages("Alpha")

    try:
        extract_pdf_text(payload, max_extracted_chars=4)
    except PdfTextExtractionError as exc:
        assert "character extraction limit" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("character limit should fail closed")


def test_extract_pdf_text_enforces_byte_limit_before_parsing() -> None:
    payload = _pdf_with_text_pages("Alpha")

    try:
        extract_pdf_text(payload, max_pdf_bytes=len(payload) - 1)
    except PdfTextExtractionError as exc:
        assert "byte extraction limit" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("byte limit should fail closed")
