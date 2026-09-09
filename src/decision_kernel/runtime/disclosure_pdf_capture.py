"""Retain bytes returned by the existing PDF fetcher; no new acquisition policy.

The manifest records retention time, NOT publication time or a Research tool trace.
Original assessment packets and Evidence retention semantics are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.pdf_text import MAX_PDF_BYTES
from . import cninfo_http


class DisclosurePdfCapture:
    """A fresh per-invocation directory, not a cache, provider or retry service."""

    def __init__(self, root: Path, *, fetch_pdf: Callable | None = None):
        self.root = root
        root.mkdir(parents=True, exist_ok=False)
        (root / "objects").mkdir()
        (root / "manifest.jsonl").touch(exist_ok=False)
        self.fetch_pdf = fetch_pdf or cninfo_http.fetch_cninfo_pdf_bytes
        self.reads = 0
        self.objects: set[str] = set()
        self.finished = False

    def fetch(self, *, source_locator: str) -> bytes:
        if self.finished:
            raise ValueError("PDF capture already completed")
        # One original fetch, no retry, fallback, search, OCR or changed limits.
        payload = self.fetch_pdf(source_locator=source_locator)
        if (not isinstance(payload, bytes) or not payload.startswith(b"%PDF-")
                or len(payload) > MAX_PDF_BYTES):
            raise ValueError("PDF capture requires the original bounded PDF bytes")
        digest = hashlib.sha256(payload).hexdigest()
        relative = "objects/" + digest + ".pdf"
        target = self.root / relative
        if target.is_symlink():
            raise ValueError("PDF capture target is a symlink")
        if target.exists():
            if target.read_bytes() != payload:
                raise ValueError("retained PDF bytes changed")
        else:
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        row = {"sequence": self.reads + 1, "source_locator": source_locator,
               "retained_at": datetime.now(timezone.utc).isoformat(),
               "pdf_sha256": digest, "bytes": len(payload), "path": relative}
        with (self.root / "manifest.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.reads += 1
        self.objects.add(digest)
        return payload  # The original extractor receives the very same bytes.

    def complete(self) -> None:
        """Called only after all assessment packets have been written successfully."""
        if self.finished:
            raise ValueError("PDF capture already completed")
        manifest = (self.root / "manifest.jsonl").read_bytes()
        summary = {"schema_version": 1, "status": "PACKET_PREPARATION_COMPLETED",
                   "returned_pdf_reads": self.reads, "unique_pdf_objects": len(self.objects),
                   "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
                   "completed_at": datetime.now(timezone.utc).isoformat(),
                   "semantics": "RETAINED_BYTES_NOT_READABILITY_OR_RESEARCH_ACCEPTANCE",
                   "investment_authority": "NONE"}
        with (self.root / "capture-summary.json").open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=True, sort_keys=True) + "\n")
        self.finished = True
