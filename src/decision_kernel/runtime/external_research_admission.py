"""Pre-execution Harness admission; no Research/Funnel/schema/registry implementation.

Callbacks are trusted transports. Source records attest accessibility, not truth or
exhaustive discovery. A saved PASS is not a reusable execution capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
from typing import Callable

from . import external_research_identity as identity
from .external_research_execution import ExternalResearchInputPacket

PLAN_PURPOSE = "PRE_EXECUTION_REQUIRED_SOURCE_PLAN"
PREFLIGHT_PURPOSE = "PRE_EXECUTION_ACCESSIBILITY_RECORD"
DYNAMIC_CLASSES = frozenset({"SUBSEQUENT_ISSUER_UPDATE_CHECK", "LATEST_UPDATE_CHECK",
                             "RECENT_MATERIAL_DISCLOSURE_CHECK"})


class AdmissionError(ValueError):
    """Not an ExternalResearchValidationResult or a validator-produced EXECUTION_GAP."""
    def __init__(self, reason: str, detail: str | None = None):
        self.reason, self.detail = reason, detail
        super().__init__(reason)


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise AdmissionError(reason)


def clock(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    check(isinstance(value, datetime) and value.tzinfo is not None
          and value.utcoffset() is not None, "ADMISSION_CLOCK_INVALID")
    return value.astimezone(timezone.utc)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source(spec: dict, read_file: Callable) -> bytes:
    return identity._checked_source(spec, read_file)


def _model(raw: bytes) -> ExternalResearchInputPacket:
    try:
        return ExternalResearchInputPacket.model_validate(identity._json(raw))
    except (ValueError, TypeError, KeyError) as exc:
        raise AdmissionError("INPUT_REJECTED") from exc


def _one_ref(packet, purpose):
    refs = [r.model_dump(mode="json") for r in packet.source_refs if r.purpose == purpose]
    check(len(refs) == 1, "SOURCE_PLAN_OR_PREFLIGHT_BINDING_MISSING")
    return refs[0]


def _body(read: dict, *, start: datetime, end: datetime, subjects: list[str]) -> None:
    check(isinstance(read, dict) and read.get("authority") == "PRIMARY"
          and read.get("body_kind") == "SUBSTANTIVE_BODY"
          and read.get("read_status") == "SUCCEEDED"
          and all(isinstance(read.get(k), str) and read[k].strip() for k in
                  ("source_identity", "locator", "tool_return_reference")),
          "SOURCE_PREFLIGHT_INCOMPLETE")
    check(read.get("subject_id") in subjects, "SOURCE_PREFLIGHT_IDENTITY_MISMATCH")
    check(start <= clock(read["checked_at"]) <= end, "SOURCE_PREFLIGHT_CLOCK_INVALID")


def check_source_preflight(plan_raw: bytes, report_raw: bytes, *, now: datetime) -> dict:
    """Also usable before an input exists. Never parses source prose into Research."""
    try:
        plan, report = identity._json(plan_raw), identity._json(report_raw)
        start, end, now = clock(report["started_at"]), clock(report["finished_at"]), clock(now)
        check(plan["schema_version"] == report["schema_version"] == 1
              and report["plan_sha256"] == digest(plan_raw)
              and report["case_id"] == plan["case_id"]
              and report["security_id"] == plan["security_id"]
              and report["environment_id"] == plan["environment_id"], "SOURCE_PREFLIGHT_BINDING_MISMATCH")
        check(start <= end <= now <= clock(plan["expires_at"]), "SOURCE_PREFLIGHT_EXPIRED_OR_FUTURE")
        check(report.get("provenance_status") == "RETAINED_ACTION_RECORDS",
              "PROVENANCE_INCOMPLETE")
        required, rows = plan["required_classes"], report["classes"]
        check(isinstance(required, list) and 0 < len(required) <= 32
              and isinstance(rows, list) and len(rows) == len(required), "SOURCE_PREFLIGHT_INCOMPLETE")
        expected = {r["id"]: r for r in required}
        actual = {r["id"]: r for r in rows}
        check(len(expected) == len(required) and len(actual) == len(rows)
              and actual.keys() == expected.keys(), "SOURCE_PREFLIGHT_INCOMPLETE")
        for name, requirement in expected.items():
            row = actual[name]
            kind = requirement["kind"]
            check(kind in {"STATIC", "DYNAMIC"}
                  and (name not in DYNAMIC_CLASSES or kind == "DYNAMIC"), "SOURCE_PLAN_INVALID")
            check(row.get("status") == "ACCESSIBLE" and row.get("research_claims", []) == []
                  and row.get("route") is None, "SOURCE_PREFLIGHT_INCOMPLETE")
            subjects = requirement["subject_ids"]
            check(isinstance(subjects, list) and 0 < len(subjects) <= 32
                  and all(isinstance(s, str) and s.strip() for s in subjects), "SOURCE_PLAN_INVALID")
            reads = row["reads"]
            check(isinstance(reads, list) and len(reads) <= 64, "SOURCE_PREFLIGHT_INCOMPLETE")
            for read in reads:
                _body(read, start=start, end=end, subjects=subjects)
            if kind == "STATIC":
                check(bool(reads), "SOURCE_PREFLIGHT_INCOMPLETE")
                continue
            inv = row["inventory"]
            queries, leads = inv["queries"], inv["leads"]
            check(type(requirement["max_queries"]) is int and 1 <= requirement["max_queries"] <= 32
                  and type(requirement["max_leads"]) is int and 0 <= requirement["max_leads"] <= 128,
                  "SOURCE_PLAN_INVALID")
            check(isinstance(queries, list) and 0 < len(queries) <= requirement["max_queries"]
                  and isinstance(leads, list) and len(leads) <= requirement["max_leads"]
                  and inv.get("truncated") is False, "SOURCE_PREFLIGHT_INCOMPLETE")
            check(clock(inv["window_start"]) == clock(requirement["window_start"])
                  and clock(inv["window_start"]) <= clock(inv["checked_through"])
                  and start <= clock(inv["checked_through"]) <= end, "SOURCE_PREFLIGHT_CLOCK_INVALID")
            for query in queries:
                check(query.get("status") == "SUCCEEDED" and query.get("query")
                      and query.get("tool_return_reference")
                      and start <= clock(query["checked_at"]) <= end, "SOURCE_PREFLIGHT_INCOMPLETE")
            readable = {r["locator"] for r in reads}
            for lead in leads:
                check(lead.get("locator") and lead.get("discovered_by") in
                      {q["tool_return_reference"] for q in queries}, "SOURCE_PREFLIGHT_INCOMPLETE")
                if lead.get("disposition") == "OUT_OF_SCOPE":
                    check(lead.get("exclusion_basis") in {"FOREIGN_SUBJECT", "OUTSIDE_DECLARED_WINDOW",
                                                          "DUPLICATE_LOCATOR"}
                          and bool(lead.get("basis_reference")), "SOURCE_PREFLIGHT_INCOMPLETE")
                else:
                    # Relevance UNKNOWN is not a licence to ignore a primary lead.
                    check(lead.get("disposition") in {"REQUIRED", "UNKNOWN"}
                          and lead.get("primary_locator") in readable, "SOURCE_PREFLIGHT_INCOMPLETE")
        return {"status": "SOURCE_PREFLIGHT_PASS", "finished_at": end.isoformat(),
                "plan_sha256": digest(plan_raw), "preflight_sha256": digest(report_raw),
                "scope": "BOUNDED_RECORDED_INVENTORY_NOT_EXHAUSTIVE_OR_RESEARCH_EVIDENCE"}
    except AdmissionError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise AdmissionError("SOURCE_PREFLIGHT_INCOMPLETE") from exc


def _scope(catalogue_source: Callable, read_file: Callable):
    spec = catalogue_source()  # resolve once per check, not supplied by source prose
    raw = _source(spec, read_file)
    return identity.load_execution_scope(raw, lambda s: _source(s, read_file)), raw, spec


def _seed_publications(packet, read_file, commit_metadata, now):
    """This ingress supports retained-Git seeds; unsupported proofs fail closed.

    Commit time is the publication of the selected retained edition, NOT the
    underlying market/event time or proof of the earliest-ever publication.
    """
    for seed in packet.seed_evidence_artifacts:
        refs = [r for r in packet.source_refs if seed.source_locator ==
                f"https://github.com/{r.repository}/blob/{r.ref}/{r.path}"]
        check(len(refs) == 1, "SEED_PUBLICATION_UNPROVEN")
        ref = refs[0].model_dump(mode="json")
        raw = _source(ref, read_file)
        meta = commit_metadata(ref["repository"], ref["ref"])
        check(meta.get("sha") == ref["ref"], "SEED_PUBLICATION_UNPROVEN")
        published = clock(meta["committer"]["date"])
        check(clock(seed.published_at) == published and seed.content_hash == digest(raw)
              and published <= clock(seed.available_at) <= packet.research_cutoff
              and published <= clock(seed.retrieved_at) <= packet.research_cutoff <= now,
              "SEED_PUBLICATION_UNPROVEN")


@dataclass(frozen=True)
class PreparedInput:
    """Preparation proof, NEVER launch permission; immutable exact local input bytes."""
    raw: bytes
    key: identity.ExecutionKey
    checked_at: datetime
    preflight: bytes


def prepare_input(raw: bytes, *, read_file: Callable, catalogue_source: Callable,
                  commit_metadata: Callable, now: datetime, environment_id: str, code_commit: str) -> PreparedInput:
    packet, now = _model(raw), clock(now)
    check(packet.code_commit == code_commit, "INSTALLED_CODE_IDENTITY_MISMATCH")
    prefix = packet.candidate_output_prefix
    pure = PurePosixPath(prefix)
    check(prefix.endswith("/") and not pure.is_absolute() and ".." not in pure.parts
          and "\\" not in prefix and str(pure) + "/" == prefix
          and not any(ord(c) < 32 for c in prefix), "INPUT_OUTPUT_PATH_INVALID")
    check(set(packet.allowed_tools) <= {"WEB_SEARCH", "WEB_OPEN", "GITHUB_READ", "OTHER_READ"},
          "INPUT_TOOLS_NOT_READ_ONLY")
    plan_raw = _source(_one_ref(packet, PLAN_PURPOSE), read_file)
    report_raw = _source(_one_ref(packet, PREFLIGHT_PURPOSE), read_file)
    preflight = check_source_preflight(plan_raw, report_raw, now=now)
    plan = identity._json(plan_raw)
    check(plan["case_id"] == packet.case_id and plan["security_id"] == packet.security_id
          and plan["environment_id"] == environment_id, "SOURCE_PREFLIGHT_BINDING_MISMATCH")
    check(clock(preflight["finished_at"]) <= packet.selected_at <= packet.research_cutoff <= now,
          "SOURCE_PREFLIGHT_NOT_BEFORE_FREEZE")
    try:
        _seed_publications(packet, read_file, commit_metadata, now)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        raise AdmissionError("INPUT_REJECTED", "SEED_PUBLICATION_UNPROVEN") from exc
    key = identity.input_key(packet)  # the original model-normalized canonical_hash
    scope, _, _ = _scope(catalogue_source, read_file)
    # Provisional key has no source commit yet. Reuse #288 for conflict logic;
    # this temporary set NEVER leaves preparation or authorizes promotion.
    identity.ExecutionScope(tuple(sorted(set(scope.keys) | {key})), scope.scope_hash).require_unambiguous(key)
    return PreparedInput(bytes(raw), key, now, json.dumps(preflight, sort_keys=True).encode())


def admit_committed_input(prepared: PreparedInput, input_source: dict, *, read_file: Callable,
                          catalogue_source: Callable, commit_metadata: Callable,
                          now: datetime, environment_id: str, code_commit: str) -> tuple[dict, ExternalResearchInputPacket]:
    """Re-read exact bytes and recheck current pinned scope immediately before launch."""
    check(isinstance(prepared, PreparedInput), "PREPARATION_REQUIRED")
    now = clock(now)
    remote = _source(input_source, read_file)
    check(remote == prepared.raw, "EXACT_INPUT_READBACK_MISMATCH")
    packet = _model(remote)
    check(identity.input_key(packet) == prepared.key, "CANONICAL_INPUT_READBACK_MISMATCH")
    check(input_source["path"] == packet.candidate_output_prefix + "input.json",
          "EXACT_INPUT_PATH_MISMATCH")
    meta = commit_metadata(input_source["repository"], input_source["ref"])
    check(meta.get("sha") == input_source["ref"], "EXACT_INPUT_COMMIT_UNPROVEN")
    # Git commit clocks have one-second resolution. Never synthesize a publication date.
    check(prepared.checked_at.replace(microsecond=0) <= clock(meta["committer"]["date"]) <= now,
          "EXACT_INPUT_COMMIT_NOT_AFTER_PREPARATION")
    rechecked = prepare_input(remote, read_file=read_file, catalogue_source=catalogue_source,
                             commit_metadata=commit_metadata, now=now, environment_id=environment_id, code_commit=code_commit)
    check(rechecked.key == prepared.key and rechecked.preflight == prepared.preflight,
          "PREPARATION_READBACK_MISMATCH")
    _, catalog_raw, catalog_source = _scope(catalogue_source, read_file)
    catalog = identity._json(catalog_raw)
    catalog["inputs"].append({**prepared.key.as_dict(), "input": input_source})
    augmented = json.dumps(catalog, sort_keys=True).encode()
    checked_scope = identity.load_execution_scope(augmented, lambda s: _source(s, read_file))
    checked_scope.require_unambiguous(prepared.key)
    report = {"status": "RESEARCH_EXECUTION_ALLOWED", "stage": "PRE_EXECUTION_ADMISSION",
              **prepared.key.as_dict(), "input_source": input_source,
              "input_file_sha256": digest(remote), "prepared_at": prepared.checked_at.isoformat(),
              "admitted_at": now.isoformat(), "preflight": json.loads(prepared.preflight),
              "catalogue_source": catalog_source, "execution_scope_hash": checked_scope.scope_hash,
              "model_validation": "PASS", "exact_input_readback": "PASS",
              "formal_research_tool_calls_used": 0, "funnel_invoked": False,
              "authority": "NONE", "meaning": "START_PERMISSION_NOT_RESEARCH_ACCEPTANCE_OR_GLOBAL_LOCK"}
    return report, packet


def freeze_and_execute(raw: bytes, *, read_file: Callable, catalogue_source: Callable,
                       commit_metadata: Callable, commit_input: Callable, retain_admission: Callable,
                       executor: Callable, now: Callable, environment_id: str, code_commit: str):
    """Trusted call boundary: writer then executor are unreachable on earlier failure.

    commit_input writes only PreparedInput.raw under the isolated input path and
    returns its pinned source spec. retain_admission must durably save the report
    before executor is called. Neither callback is derived from untrusted text.
    """
    transport, cache = read_file, {}
    def read_file(spec):
        key = (spec.get("repository"), spec.get("ref"), spec.get("path"), spec.get("git_blob"))
        if key not in cache:
            cache[key] = transport(spec)
        return cache[key]
    try:
        prepared = prepare_input(raw, read_file=read_file, catalogue_source=catalogue_source,
                                 commit_metadata=commit_metadata, now=now(), environment_id=environment_id, code_commit=code_commit)
        spec = commit_input(prepared)
        admission, packet = admit_committed_input(prepared, spec, read_file=read_file,
            catalogue_source=catalogue_source, commit_metadata=commit_metadata,
            now=now(), environment_id=environment_id, code_commit=code_commit)
        retain_admission(admission)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        return {"status": "NOT_EXECUTED", "reason": getattr(exc, "reason", getattr(exc, "code", "ADMISSION_TECHNICAL_FAILURE")),
                "detail": getattr(exc, "detail", None),
                "formal_research_tool_calls_used": 0, "funnel_invoked": False,
                "funnel_status": "NOT_REACHED", "authority": "NONE", "error_type": type(exc).__name__}, None
    # Execution failures belong to the execution receipt, not NOT_EXECUTED.
    return admission, executor(packet, admission)
