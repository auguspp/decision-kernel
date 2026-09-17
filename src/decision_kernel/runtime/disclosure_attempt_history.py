"""Read existing disclosure work history for bounded packet preparation.

Harness glue only. This module does not scan CNINFO, fetch PDFs, run Research, write
work state, or infer semantic assessment. Pre-PDF identity is scheduling priority
only: exact assessment hashes remain available so changed PDF Evidence can still
form a new packet after bounded revalidation.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from decision_kernel.identity import canonical_hash

from . import current_state as read
from . import incremental_disclosure as work
from . import incremental_disclosure_intake as intake
from .current_state_delivery import GitHubAPI
from .disclosure_receipts import CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID

SEMANTICS = "PINNED_DISCLOSURE_ATTEMPT_HISTORY_V1"
MEANING = "SCHEDULING_HISTORY_ONLY_NOT_SEMANTIC_ASSESSMENT_OR_QUIET"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _model_risk(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _research_context(value) -> dict:
    return {
        "research_snapshot_id": str(value.id if hasattr(value, "id") else value.research_snapshot_id),
        "research_as_of": (value.as_of_datetime if hasattr(value, "as_of_datetime") else value.research_as_of).isoformat(),
        "research_information_bundle_hash": value.information_bundle_hash if hasattr(value, "information_bundle_hash") else value.research_information_bundle_hash,
        "core_thesis": value.core_thesis,
        "market_expectations_narrative": value.market_expectations_narrative,
        "model_risk_level": _model_risk(value.model_risk_level),
        "model_risk_notes": value.model_risk_notes,
        "open_questions": list(value.open_questions),
        "thesis_invalidation": list(value.thesis_invalidation),
        "monitoring_triggers": list(value.monitoring_triggers),
    }


def _announcement_rows(items) -> list[dict]:
    rows = []
    for item in items:
        rows.append({
            "announcement_id": item.announcement_id,
            "title": item.title,
            "published_at": item.published_at.isoformat(),
            "source_locator": item.source_locator,
        })
    return sorted(rows, key=lambda row: row["announcement_id"])


def disclosure_prefetch_identity(*, research_snapshot, batch) -> str:
    """Stable scheduling identity available before a PDF body is fetched."""

    payload = {
        "source_lane": "CNINFO",
        "stock_code": batch.stock_code,
        "publication_date": batch.publication_date.isoformat(),
        "announcements": _announcement_rows(batch.announcements),
        "research_context": _research_context(research_snapshot),
        "assessment_semantics_id": CURRENT_DISCLOSURE_ASSESSMENT_SEMANTICS_ID,
    }
    return canonical_hash(payload)


def packet_prefetch_identity(packet) -> str:
    payload = {
        "source_lane": packet.source_lane,
        "stock_code": packet.stock_code,
        "publication_date": packet.publication_date.isoformat(),
        "announcements": _announcement_rows(packet.evidence),
        "research_context": _research_context(packet),
        "assessment_semantics_id": packet.assessment_semantics_id,
    }
    return canonical_hash(payload)


def build_attempt_history(*, work_files: dict[str, bytes], work_commit: str) -> dict:
    read.check(read.SHA.fullmatch(work_commit) is not None, "attempt history work commit must be pinned")
    reserved = work._history(work_files)
    identities: dict[str, set[str]] = {}
    for path, raw in work_files.items():
        if not (path.startswith(work.WORK_PREFIX) and path.endswith("/packet.json")):
            continue
        packet = work._packet(raw)
        read.check(packet.assessment_input_hash in reserved, "attempt history packet not reserved")
        identity = packet_prefetch_identity(packet)
        identities.setdefault(identity, set()).add(packet.assessment_input_hash)
    read.check(len(reserved) <= work.MAX_HISTORY and len(identities) <= work.MAX_HISTORY,
               "attempt identity history over bound")
    attempts = [
        {"prefetch_hash": identity, "assessment_input_hashes": sorted(keys)}
        for identity, keys in sorted(identities.items())
    ]
    payload = {
        "schema_version": 1,
        "semantics": SEMANTICS,
        "meaning": MEANING,
        "work_ref": work.WORK_REF,
        "work_commit": work_commit,
        "attempts": attempts,
        "reserved_packet_count": len(reserved),
        "investment_authority": "NONE",
        "action_authority": "NONE",
    }
    payload["history_hash"] = canonical_hash(payload)
    return payload


def parse_attempt_history(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("disclosure attempt history must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("disclosure attempt history must be an object")
    expected = {
        "schema_version", "semantics", "meaning", "work_ref", "work_commit",
        "attempts", "reserved_packet_count", "investment_authority",
        "action_authority", "history_hash",
    }
    if set(payload) != expected:
        raise ValueError("disclosure attempt history fields differ")
    if payload["schema_version"] != 1 or payload["semantics"] != SEMANTICS or payload["meaning"] != MEANING:
        raise ValueError("disclosure attempt history semantics differ")
    if payload["work_ref"] != work.WORK_REF or read.SHA.fullmatch(payload["work_commit"]) is None:
        raise ValueError("disclosure attempt history work identity differs")
    attempts = payload["attempts"]
    if not isinstance(attempts, list) or len(attempts) > work.MAX_HISTORY:
        raise ValueError("disclosure attempt history attempts are invalid")
    prior_prefetch = None
    exact_count = 0
    for row in attempts:
        if not isinstance(row, dict) or set(row) != {"prefetch_hash", "assessment_input_hashes"}:
            raise ValueError("disclosure attempt history row fields differ")
        prefetch = row["prefetch_hash"]
        keys = row["assessment_input_hashes"]
        if (not isinstance(prefetch, str) or _SHA256.fullmatch(prefetch) is None
                or prior_prefetch is not None and prefetch <= prior_prefetch
                or not isinstance(keys, list) or not keys
                or keys != sorted(set(keys))
                or any(not isinstance(key, str) or _SHA256.fullmatch(key) is None for key in keys)):
            raise ValueError("disclosure attempt history row identity is invalid")
        prior_prefetch = prefetch
        exact_count += len(keys)
    if (type(payload["reserved_packet_count"]) is not int
            or not 0 <= payload["reserved_packet_count"] <= work.MAX_HISTORY
            or exact_count != payload["reserved_packet_count"]):
        raise ValueError("disclosure attempt history reserved count is invalid")
    if payload["investment_authority"] != "NONE" or payload["action_authority"] != "NONE":
        raise ValueError("disclosure attempt history authority differs")
    sealed = dict(payload)
    history_hash = sealed.pop("history_hash")
    if not isinstance(history_hash, str) or _SHA256.fullmatch(history_hash) is None or canonical_hash(sealed) != history_hash:
        raise ValueError("disclosure attempt history hash differs")
    return payload


def empty_attempt_history(*, work_commit: str = "0" * 40) -> dict:
    """Test/manual helper for an explicitly known empty pinned history."""

    payload = {
        "schema_version": 1,
        "semantics": SEMANTICS,
        "meaning": MEANING,
        "work_ref": work.WORK_REF,
        "work_commit": work_commit,
        "attempts": [],
        "reserved_packet_count": 0,
        "investment_authority": "NONE",
        "action_authority": "NONE",
    }
    payload["history_hash"] = canonical_hash(payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        read.check(read.SHA.fullmatch(args.code_commit) is not None, "code commit must be pinned")
        read.check(os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
                   and os.environ.get("GITHUB_REF") == "refs/heads/main", "main attempt1 only")
        api = GitHubAPI(os.environ["GH_TOKEN"])
        read.check(intake.mutable_ref(api, "main") == args.code_commit, "main moved before attempt-history read")
        work_commit = intake.mutable_ref(api, work.WORK_REF)
        _, files = intake.work_inventory(api, work_commit)
        payload = build_attempt_history(work_files=files, work_commit=work_commit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2, sort_keys=True)
            out.write("\n")
        print(f"DISCLOSURE_ATTEMPT_HISTORY={work_commit} reserved={payload['reserved_packet_count']}")
        return 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        print("DISCLOSURE_ATTEMPT_HISTORY_FAILED: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
