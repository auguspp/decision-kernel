"""Read one explicitly registered calendar bundle through existing Git custody.

No discovery, network provider, new state store or event-state transition. The
original v1 parser/replay owns date semantics; this adapter owns registration.
"""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory

from . import current_state as model
from . import research_calendar as calendar

VERSION = "research-calendar-reading-v1"
STATUS = "SAVED_REVIEWED_CALENDAR"
MEANING = "SAVED_APPOINTMENTS_NOT_RELEASE_OR_RESEARCH"


def read_registered(collector, config) -> dict:
    """A local gap never promotes partial bytes or silently substitutes an old R."""
    result = {"version": VERSION, "meaning": MEANING, **model.AUTHORITY}
    if config is None:
        return {**result, "status": "NOT_CONFIGURED"}
    files_before, sources_before = dict(collector.files), dict(collector.sources)
    try:
        model.check(isinstance(config, dict) and set(config) ==
                    {"ref", "directory", "calendar_hash", "blobs"}, "calendar registration fields")
        ref, directory, expected = config["ref"], config["directory"], config["calendar_hash"]
        model.check(isinstance(ref, str) and model.SHA.fullmatch(ref), "calendar source commit")
        model.safe_path(directory)
        model.check(directory.startswith("docs/readings/") and
                    re.fullmatch(r"[A-Za-z0-9_./-]+", directory), "calendar source directory")
        model.check(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), "calendar external hash")
        blobs = config["blobs"]
        model.check(isinstance(blobs, dict) and set(blobs) == calendar.FILES and
                    all(isinstance(b, str) and model.SHA.fullmatch(b) for b in blobs.values()),
                    "calendar complete registered inventory")
        references = {}
        with TemporaryDirectory(prefix="kernel-calendar-reading-") as tmp:
            folder = Path(tmp)
            for name in sorted(calendar.FILES):
                raw, source = collector.source({"path": directory + "/" + name,
                                                 "ref": ref, "git_blob": blobs[name]})
                model.check(isinstance(raw, bytes) and len(raw) <= calendar.MAX_SAVED_BYTES and
                            model.blob_sha(raw) == blobs[name], "calendar source bytes")
                # Independently bind returned descriptors, not just the caller's spec.
                model.check(source["repository"] == model.REPOSITORY and source["ref"] == ref and
                            source["path"] == directory + "/" + name and source["git_blob"] == blobs[name] and
                            source["bytes"] == len(raw) and source["sha256"] == model.sha256(raw) and
                            source["read_ref_rule"] == "USE_THE_SAME_PINNED_READING_COMMIT" and
                            source["read_path"] == "sources/git/" + blobs[name] + "/" + name,
                            "calendar source descriptor")
                (folder / name).write_bytes(raw)
                references[name] = source
            saved = calendar.read_calendar(folder, expected_hash=expected)
        model.check(saved["source"]["observation_kind"] == "REVIEWED_WEB_EXCERPT",
                    "synthetic calendar is not a published observation")
        checked = collector.now()
        model.check(model.clock(saved["as_of"]) <= model.clock(checked), "calendar check precedes source review")
        return {**result, "status": STATUS, "checked_at": checked, "as_of": saved["as_of"],
                "source_commit": ref, "calendar_hash": expected, "files": references,
                "coverage": saved["coverage"], "window": saved["window"],
                "event_count": len(saved["events"]), "company_events": saved["company_events"]}
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        collector.files, collector.sources = files_before, sources_before
        return {**result, "status": "UNAVAILABLE_OR_REJECTED", "error_type": type(exc).__name__,
                "limitation": "CALENDAR_READ_GAP_NOT_NO_EVENTS_OR_CANCELLATION"}


def navigation(saved: dict) -> bytes:
    """Same-R Markdown locator only; no live date or completion claim."""
    if saved.get("status") == STATUS:
        path = model.safe_path(saved["files"]["calendar.md"]["read_path"])
        return ("\n[研究日历：已保存的有限 BLS 预约](" + path + ")；原核读时刻保留，"
                "不是实时日历、实际发布确认或研究待办。\n").encode("utf-8")
    return b""  # The workbench explains absent/rejected registration without reading a fallback.
