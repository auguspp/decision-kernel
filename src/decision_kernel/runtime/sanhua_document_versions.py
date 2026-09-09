"""Pure title-family qualification for the fixed Sanhua source inventory.

No fetching, content interpretation, Evidence, or Research. A selected title is
not proof of PDF contents or of the activity discussed in an IR record. Version
relationships are deliberately narrower than a generic 'latest wins' ranking.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

REPORT = "2026年半年度报告"
IR = "投资者关系活动记录表"
REVISION = r"(?:修订|修正|更正|更新)"
REVISION_SUFFIX = re.compile(rf"\((?:{REVISION})(?:版|稿|本|后)?\)$")
VARIANT = re.compile(r"英文|english|H股|H-?share|港股|海外监管|海外監管", re.I)
CANCEL = re.compile(r"取消|撤销|撤回|作废")
DATE = r"(?:\d{4}年\d{1,2}月\d{1,2}日|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})"
IR_BODY = re.compile(rf"(?:{DATE})?{IR}(?:\({DATE}\))?$")


def _title(value: str) -> str:
    text = re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))
    for prefix in ("三花智控:", "浙江三花智能控制股份有限公司:"):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def classify_title(title: str, family: str) -> dict[str, str | None]:
    """Keep body type separate from version disposition; never rank by title."""
    if family not in {"H1_REPORT", "IR"}:
        raise ValueError("UNREVIEWED_DOCUMENT_FAMILY")
    text = _title(title)
    marker = REPORT if family == "H1_REPORT" else IR
    english_report = family == "H1_REPORT" and bool(re.search(
        r"2026.*(?:interim|half.?year).*report|(?:interim|half.?year).*report.*2026",
        text, re.I))
    related = marker in text or english_report
    if family == "IR" and "投资者关系活动记录" in text and re.search(REVISION + r"|补充|说明|取消|撤销", text):
        related = True  # A related notice need not repeat the trailing 表.
    kind, key = "OTHER", None
    if related:
        # A language/market variant does not cancel or supersede the A-share body.
        if VARIANT.search(text) or english_report:
            kind = "LANGUAGE_OR_MARKET_VARIANT"
        elif CANCEL.search(text):
            kind = "CANCELLATION_NOTICE_ONLY"
        elif "摘要" in text:
            kind = "SUMMARY"
        else:
            base = REVISION_SUFFIX.sub("", text)
            is_body = base == REPORT if family == "H1_REPORT" else bool(IR_BODY.fullmatch(base))
            if is_body:
                kind = "REVISED_OR_CORRECTED_BODY" if base != text else "FULL_BODY"
                key = base
            elif re.search(REVISION + r"|补充|说明", text):
                # A notice (or unrecognized revision label) cannot qualify a body.
                kind = "CORRECTION_NOTICE_ONLY"
    return {"classification": kind, "family_key": key}


def _publication(row: dict) -> datetime:
    value = datetime.fromisoformat(row["published_at"].replace("Z", "+00:00"))
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("QUALIFIED_PUBLICATION_CLOCK_REQUIRED")
    return value


def _decision(rows: list[dict], family: str, dates: tuple[str, ...]) -> dict:
    records = [{"announcement_id": r["announcement_id"], "title": r["title"],
                "published_at": r["published_at"], **classify_title(r["title"], family),
                "disposition": "NOT_CANDIDATE"} for r in rows]
    # Sorting is output determinism only; IDs/titles never break a selection tie.
    records.sort(key=lambda r: r["announcement_id"])
    ir = family == "IR"
    missing = "RELEVANT_IR_MISSING_FROM_BOUNDED_INVENTORY" if ir else "FORMAL_REPORT_MISSING"
    ambiguous = "RELEVANT_IR_AMBIGUOUS" if ir else "REPORT_VERSION_AMBIGUOUS"
    unresolved = "IR_VERSION_RELATION_UNRESOLVED" if ir else "VERSION_RELATION_UNRESOLVED"
    result = {"family": family, "status": missing, "selected_announcement_id": None,
              "reason": "NO_QUALIFIED_FULL_BODY", "records": records,
              "proof_scope": "TITLE_VERSION_RELATION_NOT_CONTENT_OR_ACTIVITY_CERTIFICATION"}
    notices = [r for r in records if r["classification"] in {
        "CORRECTION_NOTICE_ONLY", "CANCELLATION_NOTICE_ONLY"}]
    bodies = [r for r in records if r["classification"] in {
        "FULL_BODY", "REVISED_OR_CORRECTED_BODY"}]

    def reject(status, reason, affected):
        result.update(status=status, reason=reason)
        for row in affected:
            row["disposition"] = "AMBIGUOUS" if status == ambiguous else "RELATION_UNRESOLVED"
        return result

    unscoped = [r for r in records if r["classification"] == "OTHER"
        and CANCEL.search(_title(r["title"]))
        and REPORT not in _title(r["title"])
        and "投资者关系活动记录" not in _title(r["title"])
        and re.search(r"公告|披露|文件", _title(r["title"]))]
    if unscoped:
        return reject(unresolved, "CANCELLATION_TARGET_NOT_ESTABLISHED", unscoped + bodies)
    if notices:
        # No notice-to-body reference is established by title alone. Do not use
        # even a unique old body in the presence of an unresolved related notice.
        return reject(unresolved, "NOTICE_TO_BODY_RELATION_NOT_ESTABLISHED", notices + bodies)
    if ir:
        # Dates anchor the requested lead, NOT a claim about its activity date.
        # Examine the complete inventory for subsequent versions, not just the
        # Aug27/28 slice. An unrelatable revision blocks rather than disappearing.
        target = [r for r in bodies if _publication(r).astimezone(
            ZoneInfo("Asia/Shanghai")).date().isoformat() in dates]
        ordinary_target = [r for r in target if r["classification"] == "FULL_BODY"]
        keys = {r["family_key"] for r in (ordinary_target or target)}
        revisions = [r for r in bodies if r["classification"] == "REVISED_OR_CORRECTED_BODY"]
        unlinked = [r for r in revisions if r["family_key"] not in keys]
        if unlinked:
            return reject(unresolved, "REVISION_NOT_LINKED_TO_TARGET_IR_TITLE_FAMILY", target + unlinked)
        if not target:
            return result
        if len(keys) != 1:
            return reject(ambiguous, "MULTIPLE_TARGET_IR_TITLE_FAMILIES", target)
        for row in bodies:
            if row["family_key"] not in keys:
                row["disposition"] = "OUTSIDE_TARGET_TITLE_FAMILY"
        bodies = [r for r in bodies if r["family_key"] in keys]
    if not bodies:
        return result
    full = [r for r in bodies if r["classification"] == "FULL_BODY"]
    revised = [r for r in bodies if r["classification"] == "REVISED_OR_CORRECTED_BODY"]
    if len(full) > 1 or len(revised) > 1:
        return reject(ambiguous, "MULTIPLE_BODIES_WITHOUT_UNIQUE_VERSION_RELATION", bodies)
    if full and revised and _publication(revised[0]) < _publication(full[0]):
        return reject(unresolved, "REVISION_PREDATES_ORDINARY_BODY", bodies)
    selected = revised[0] if revised else full[0]
    for row in bodies:
        row["disposition"] = "CURRENT" if row is selected else "SUPERSEDED"
    result.update(status="SELECTED", selected_announcement_id=selected["announcement_id"],
                  reason="UNIQUE_EXPLICIT_REVISION" if revised else "ONLY_FULL_BODY")
    return result


def qualify_versions(inventory: list[dict], *, ir_publication_dates: list[str]) -> dict:
    """Pure projection of the already identity/date-qualified complete inventory.

    Both decisions finish before the caller may ask for ANY primary PDF. No
    fallback to a superseded body if the selected body later fails to download.
    """
    ids = [row["announcement_id"] for row in inventory]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_ANNOUNCEMENT_ID")
    return {"report": _decision(inventory, "H1_REPORT", ()),
            "ir": _decision(inventory, "IR", tuple(ir_publication_dates))}
