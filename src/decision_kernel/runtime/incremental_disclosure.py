"""One-at-a-time work selection over SAVED official disclosure packets.

Harness glue, not a scheduler, a second Funnel, or a source-quality certificate.
Reuse the original ZIP and packet validators and external-candidate validator.
The caller supplies one pinned, completely read work-ref inventory. On that
fixed ref, create packet.json WITHOUT a previous blob SHA to reserve a key before
preflight. A lost write response requires readback, not another launch. Never
execute code from the work ref. No network or remote writes occur here.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path

from ..identity import canonical_hash
from . import current_state as reading
from .disclosure_assessment import parse_disclosure_assessment_packet
from .external_research_execution import (
    ExternalResearchCandidate, ExternalResearchInputPacket,
    validate_external_research_candidate,
)
from .external_research_identity import _json

WORK_REF = "research-work/disclosures-v0"
WORK_PREFIX = "research_runs/candidates/incremental-disclosures/"
PACKET_PURPOSE = "INCREMENTAL_DISCLOSURE_PACKET"
POLICY = "saved-cninfo-fifo-one-v1"
MAX_PACKETS = 10  # The existing production scan's packet-limit, not a new scan.
MAX_HISTORY = 128
# Same six companies as the existing approved scan; not all A shares or new coverage.
SCOPE = frozenset({"600519", "300750", "600036", "601088", "603986", "002050"})


def request_path(key: str) -> str:
    reading.check(isinstance(key, str) and re.fullmatch(r"[0-9a-f]{64}", key) is not None,
                  "invalid work key")
    return WORK_PREFIX + key + "/packet.json"



def continuation_prefix(key: str, comment_id: int) -> str:
    reading.check(type(comment_id) is int and 0 < comment_id < 10**20, "invalid continuation permission ID")
    return request_path(key).removesuffix("packet.json") + f"continuations/{comment_id}/"


def split_work_path(path: str) -> tuple[str, str, str]:
    """Parent packet stays canonical. Child paths carry a permission, not a new key."""
    reading.safe_path(path)
    reading.check(path.startswith(WORK_PREFIX), "work path outside prefix")
    parts = path[len(WORK_PREFIX):].split("/")
    reading.check(len(parts) in {2, 4}, "work history path outside one request")
    key, name = parts[0], parts[-1]
    prefix = request_path(key).removesuffix("packet.json")
    if len(parts) == 4:
        reading.check(parts[1] == "continuations" and re.fullmatch(r"[1-9][0-9]{0,19}", parts[2])
                      and name != "packet.json", "invalid continuation history path")
        prefix = continuation_prefix(key, int(parts[2]))
    return key, prefix, name


def output_prefix(packet, key: str) -> str:
    """Check retained identity only. Live callers must independently check permission."""
    prefix = packet.candidate_output_prefix.rstrip("/") + "/"
    root = request_path(key).removesuffix("packet.json")
    if prefix != root:
        parsed_key, expected, _ = split_work_path(prefix + "input.json")
        comment_id = int(prefix.rstrip("/").rsplit("/", 1)[1])
        refs = {s.purpose: s for s in packet.source_refs}
        permission = refs.get("TRUSTED_HUMAN_CONTINUATION_REQUEST")
        failure = refs.get("CONTINUATION_PREDECESSOR_RESULT")
        reading.check(parsed_key == key and expected == prefix
            and packet.execution_id == f"saved-disclosure-{key}-reading-{comment_id}"
            and permission is not None and permission.ref == packet.code_commit
            and permission.path == "research_runs/disclosure-continuation-request.json"
            and failure is not None and failure.path == root + "failure.json",
            "output changed continuation identity")
    return prefix

def _packet(raw: bytes):
    _json(raw)  # Original size and duplicate-key checks before the packet parser.
    return parse_disclosure_assessment_packet(raw.decode("utf-8"))


def _history(files: Mapping[str, bytes]) -> set[str]:
    """A reservation blocks automatic re-execution even without any result.

    Missing/corrupt reserved packets invalidate this supplied history rather than
    pretending it is empty. WAIT, DROP, DEEPEN, gaps and interrupted executions all
    retain their original key. A new Evidence/context hash is a different request.
    """
    keys = set()
    for path, raw in files.items():
        reading.safe_path(path)
        if not path.startswith(WORK_PREFIX):
            continue
        key, _, name = split_work_path(path)
        if name != "packet.json":
            reading.check(request_path(key) in files, "work history lacks reserved packet")
            continue
        packet = _packet(raw)
        reading.check(packet.assessment_input_hash == key and packet.stock_code in SCOPE,
                      "work history packet/key or scope differs")
        keys.add(key)
    reading.check(len(keys) <= MAX_HISTORY, "work history bound exceeded; explicit partition needed")
    return keys


def plan_one(*, archive_raw: bytes, artifact: dict, run: dict,
             work_files: Mapping[str, bytes], work_commit: str,
             selected_at: str) -> dict:
    """Choose <=1 unseen packet, preserving the whole supplied scan denominator.

    Order is publication date, code, original assessment_input_hash. Parsing
    success/EXTRACTED does not imply readable text; readability belongs to actual
    source preflight. Invalid packets stay visible. All historical attempts stay
    reserved: no timeout reset, outcome-based retry or automatic Deep/registration.
    """
    reading.run_identity(run, "inbox", success=True)
    reading.check(artifact.get("name") == "official-disclosure-scan", "wrong scan artifact")
    reading.check(reading.SHA.fullmatch(work_commit) is not None, "work inventory must be pinned")
    now = reading.clock(selected_at)
    reading.check(reading.clock(run["updated_at"]) <= now, "scan is from the future")
    reserved = _history(work_files)  # Empty is legal only after caller read the empty ref.
    files = reading.unpack_archive(archive_raw, artifact, run)
    report = files["disclosure-scan.txt"].decode("utf-8")
    counts = re.findall(r"^ASSESSMENT PACKETS: (\d+) prepared(?: \||$)", report, re.M)
    reading.check(len(counts) == 1, "saved scan packet count unavailable")
    paths = sorted(p for p in files if p.startswith("disclosure-assessment-packets/"))
    reading.check(len(paths) == int(counts[0]) <= MAX_PACKETS, "saved packet inventory incomplete/over bound")
    rows, seen = [], set()
    for path in paths:
        raw = files[path]
        row = {"packet_path": path, "packet_sha256": reading.sha256(raw),
               "packet_blob": reading.blob_sha(raw), "bytes": len(raw)}
        try:
            packet = _packet(raw)
            key = packet.assessment_input_hash
            expected = (f"disclosure-assessment-packets/{packet.stock_code}-"
                        f"{packet.publication_date.isoformat()}-{key[:16]}.json")
            reading.check(path == expected and packet.prepared_at <= now,
                          "packet filename or preparation clock differs")
            reading.check(packet.prepared_at <= reading.clock(run["updated_at"]),
                          "packet was prepared after its producing run")
            reading.check(key not in seen, "duplicate packet in saved inventory")
            seen.add(key)
            row.update(assessment_input_hash=key, stock_code=packet.stock_code,
                       publication_date=packet.publication_date.isoformat(),
                       announcement_ids=list(packet.announcement_ids),
                       prepared_at=packet.prepared_at.isoformat(),
                       reservation_path=request_path(key),
                       status="ALREADY_RESERVED" if key in reserved else "DEFERRED_CAPACITY")
            if packet.stock_code not in SCOPE:
                row["status"] = "OUTSIDE_APPROVED_SCAN_SCOPE"
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            row.update(status="INPUT_REJECTED", error_type=type(exc).__name__, reason=str(exc)[:240])
        rows.append(row)
    eligible = sorted((r for r in rows if r["status"] == "DEFERRED_CAPACITY"),
                      key=lambda r: (r["publication_date"], r["stock_code"], r["assessment_input_hash"]))
    selected = eligible[0] if eligible else None
    if selected is not None:
        selected["status"] = "SELECTED_REQUIRES_RESERVATION_AND_ORIGINAL_ADMISSION"
    gaps = any(r["status"] in {"INPUT_REJECTED", "OUTSIDE_APPROVED_SCAN_SCOPE"} for r in rows)
    result = {"schema_version": 1, "policy": POLICY, "selected_at": selected_at,
              "status": "ONE_SELECTED" if selected else ("NO_ELIGIBLE_WITH_GAPS" if gaps else "NO_UNRESERVED_PACKET_IN_SAVED_SCAN"),
              "source_run": reading.concise_run(run), "source_artifact_id": artifact["id"],
              "archive_sha256": reading.sha256(archive_raw), "packet_count": len(paths),
              "selected": selected, "dispositions": rows,
              "work_ref": WORK_REF, "work_commit": work_commit,
              "reserved_count": len(reserved), "formal_research_executed": False,
              "history_scope": "CALLER_SUPPLIED_PINNED_WORK_REF_NOT_GLOBAL_ALL_BRANCH_HISTORY",
              "source_quality": "PACKET_INTEGRITY_ONLY_NOT_READABILITY_OR_COMPLETE_RESEARCH",
              **reading.AUTHORITY}
    result["plan_hash"] = canonical_hash(result)
    return result


def reservation(plan: dict, archive_raw: bytes, artifact: dict, run: dict) -> tuple[str, bytes]:
    """Return the exact create-only path/bytes. This does not itself claim a lock."""
    reading.sealed(plan, "plan_hash")
    reading.check(plan["policy"] == POLICY and plan["work_ref"] == WORK_REF, "unexpected plan")
    reading.run_identity(run, "inbox", success=True)
    reading.check(plan["archive_sha256"] == reading.sha256(archive_raw)
                  and plan["source_artifact_id"] == artifact["id"]
                  and plan["source_run"] == reading.concise_run(run), "reservation scan differs")
    chosen = plan["selected"]
    reading.check(chosen is not None and chosen in plan["dispositions"]
                  and chosen["status"] == "SELECTED_REQUIRES_RESERVATION_AND_ORIGINAL_ADMISSION"
                  and sum(r["status"] == chosen["status"] for r in plan["dispositions"]) == 1,
                  "no unique selected request")
    raw = reading.unpack_archive(archive_raw, artifact, run)[chosen["packet_path"]]
    packet = _packet(raw)
    reading.check(reading.sha256(raw) == chosen["packet_sha256"]
                  and packet.assessment_input_hash == chosen["assessment_input_hash"], "selected packet differs")
    return request_path(packet.assessment_input_hash), raw


def describe_outcome(*, reserved_packet: bytes, input_raw: bytes, candidate_raw: bytes) -> dict:
    """Derive a work outcome from the original validator, never a self-filled route.

    Necessary content binding only, not admission, semantic approval, registration
    or permission to mutate a historical candidate. Preserve its original Funnel.
    """
    saved = _packet(reserved_packet)
    packet = ExternalResearchInputPacket.model_validate(_json(input_raw))
    candidate = ExternalResearchCandidate.model_validate(_json(candidate_raw))
    refs = [s for s in packet.source_refs if s.purpose == PACKET_PURPOSE]
    reading.check(len(refs) == 1 and refs[0].repository == reading.REPOSITORY
                  and reading.SHA.fullmatch(refs[0].ref) is not None
                  and refs[0].path == request_path(saved.assessment_input_hash)
                  and refs[0].git_blob == reading.blob_sha(reserved_packet)
                  and refs[0].sha256 == reading.sha256(reserved_packet), "output changed reserved source")
    reading.check(packet.ticker == saved.stock_code and saved.stock_code in SCOPE
                  and output_prefix(packet, saved.assessment_input_hash)
                  and packet.source_lane == "CNINFO_INCREMENTAL",
                  "output changed work identity")
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    return {"assessment_input_hash": saved.assessment_input_hash,
            "execution_id": packet.execution_id, "canonical_input_hash": canonical_hash(packet),
            "validation_hash": canonical_hash(result), "validation": result.model_dump(mode="json"),
            "automatic_retry": False, "semantic_acceptance": "NOT_ESTABLISHED_BY_THIS_VALIDATOR",
            **reading.AUTHORITY}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    for name in ("archive", "artifact", "run", "worktree"):
        plan.add_argument("--" + name, required=True, type=Path)
    plan.add_argument("--work-commit", required=True)
    plan.add_argument("--selected-at", required=True)
    outcome = sub.add_parser("outcome")
    for name in ("packet", "input", "candidate"):
        outcome.add_argument("--" + name, required=True, type=Path)
    for command in (plan, outcome):
        command.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.command == "plan":
        reading.check(args.worktree.is_dir() and not args.worktree.is_symlink(), "worktree unavailable")
        paths = list(args.worktree.rglob("*"))
        reading.check(len(paths) <= 2048 and not any(p.is_symlink() for p in paths), "worktree unsafe/over bound")
        work = {}
        for p in paths:
            if p.is_file():
                reading.check(p.stat().st_size <= reading.MAX_ARCHIVE, "work record too large")
                work[p.relative_to(args.worktree).as_posix()] = p.read_bytes()
        reading.check(sum(map(len, work.values())) <= reading.MAX_EXPANDED, "worktree byte limit")
        value = plan_one(archive_raw=args.archive.read_bytes(),
                         artifact=json.loads(args.artifact.read_bytes()), run=json.loads(args.run.read_bytes()),
                         work_files=work, work_commit=args.work_commit, selected_at=args.selected_at)
    else:
        value = describe_outcome(reserved_packet=args.packet.read_bytes(),
                                 input_raw=args.input.read_bytes(), candidate_raw=args.candidate.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as output:
        output.write(reading.json_bytes(value))  # Never overwrite a historical output.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
