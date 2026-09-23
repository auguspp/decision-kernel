"""Harness-only execution identity gate; no Research, registration or network writes.

Historical validation is not promotion. Read an exact pair even when its name is
conflicted, but never promote either input under that name. The input catalogue
is a bounded, pinned observation scope, not a global lock or authority registry.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable

from ..identity import canonical_hash
from ..primitives import DomainValidationError
from .external_research_execution import (
    ExternalResearchCandidate, ExternalResearchInputPacket,
    ExternalResearchValidationStatus, validate_external_research_candidate,
)

CATALOG_PATH = "research_runs/execution-inputs.json"
MAX_INPUTS = 64
MAX_BYTES = 512 * 1024
# Published observation reports are not executable input packets or model prompts.
MAX_READING_BYTES = 4 * 1024 * 1024
INDUSTRY_ORIGIN_PATH = "details/radar/industry-breadth.json"
INDUSTRY_ORIGIN_PURPOSE = "SAVED_INDUSTRY_BATCH_ORIGIN"
REPOSITORY = "auguspp/decision-kernel"


class ExecutionIdentityError(DomainValidationError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ExecutionIdentityError(code)


def _json(raw: bytes, *, max_bytes: int = MAX_BYTES) -> dict:
    require(type(max_bytes) is int and 0 < max_bytes <= MAX_READING_BYTES, "EXECUTION_JSON_BOUND_INVALID")
    require(isinstance(raw, bytes) and len(raw) <= max_bytes, "EXECUTION_INPUT_SIZE_INVALID")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "EXECUTION_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    require(isinstance(value, dict), "EXECUTION_INPUT_NOT_OBJECT")
    return value


@dataclass(frozen=True, order=True)
class ExecutionKey:
    execution_id: str
    canonical_input_hash: str

    def __post_init__(self):
        require(isinstance(self.execution_id, str) and 0 < len(self.execution_id) <= 255
                and not any(ord(c) < 32 for c in self.execution_id), "EXECUTION_ID_INVALID")
        require(isinstance(self.canonical_input_hash, str)
                and re.fullmatch(r"[0-9a-f]{64}", self.canonical_input_hash) is not None,
                "EXECUTION_INPUT_HASH_INVALID")

    def as_dict(self) -> dict:
        return {"execution_id": self.execution_id,
                "canonical_input_hash": self.canonical_input_hash}


def input_key(packet: ExternalResearchInputPacket) -> ExecutionKey:
    # Use the installed model, including its datetime normalization, not raw JSON.
    return ExecutionKey(packet.execution_id, canonical_hash(packet))


def read_bound_execution(input_raw: bytes, candidate_raw: bytes, expected: ExecutionKey):
    """Read/validate one historical pair, without granting promotion eligibility."""
    packet = ExternalResearchInputPacket.model_validate(_json(input_raw))
    require(input_key(packet) == expected, "EXECUTION_INPUT_BINDING_MISMATCH")
    candidate = ExternalResearchCandidate.model_validate(_json(candidate_raw))
    require(candidate.receipt.execution_id == expected.execution_id
            and candidate.input_hash == candidate.receipt.input_hash == expected.canonical_input_hash,
            "EXECUTION_RECEIPT_BINDING_MISMATCH")
    # Discovery identity belongs to the existing Funnel; do not conflate an
    # observation id with this execution id. Candidate/receipt bind the latter.
    validation = validate_external_research_candidate(packet=packet, candidate=candidate)
    return packet, candidate, validation


def _checked_source(spec: dict, load: Callable[[dict], bytes]) -> bytes:
    require(isinstance(spec, dict), "EXECUTION_SOURCE_INVALID")
    path = spec.get("path", "")
    require(isinstance(path, str) and bool(path), "EXECUTION_SOURCE_INVALID")
    pure = PurePosixPath(path)
    require(not pure.is_absolute() and ".." not in pure.parts and "\\" not in path
            and str(pure) == path and not any(ord(c) < 32 for c in path), "EXECUTION_SOURCE_INVALID")
    require(spec.get("repository") == REPOSITORY
            and re.fullmatch(r"[0-9a-f]{40}", spec.get("ref", "")) is not None
            and re.fullmatch(r"[0-9a-f]{40}", spec.get("git_blob", "")) is not None,
            "EXECUTION_SOURCE_NOT_PINNED")
    # A purpose/path-specific storage allowance is not source admission. The
    # original native replay, clocks and host permission must still pass.
    limit = (MAX_READING_BYTES if path == INDUSTRY_ORIGIN_PATH
             and spec.get("purpose") == INDUSTRY_ORIGIN_PURPOSE else MAX_BYTES)
    raw = load(spec)
    require(isinstance(raw, bytes) and len(raw) <= limit, "EXECUTION_INPUT_SIZE_INVALID")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    require(blob == spec["git_blob"], "EXECUTION_SOURCE_BLOB_MISMATCH")
    if "sha256" in spec:
        require(hashlib.sha256(raw).hexdigest() == spec["sha256"], "EXECUTION_SOURCE_SHA256_MISMATCH")
    return raw


@dataclass(frozen=True)
class ExecutionScope:
    keys: tuple[ExecutionKey, ...]
    scope_hash: str

    def hashes(self, execution_id: str) -> tuple[str, ...]:
        return tuple(sorted({k.canonical_input_hash for k in self.keys if k.execution_id == execution_id}))

    def require_unambiguous(self, key: ExecutionKey) -> None:
        # Check the whole set before choosing either input; never first/last wins.
        require(len(self.hashes(key.execution_id)) <= 1, "EXECUTION_ID_CONFLICT")
        require(key in self.keys, "EXECUTION_INPUT_NOT_IN_SCOPE")

    def conflicts(self) -> list[dict]:
        return [{"execution_id": eid, "canonical_input_hashes": list(self.hashes(eid)),
                 "status": "EXECUTION_ID_CONFLICT", "promotion_allowed": False}
                for eid in sorted({k.execution_id for k in self.keys}) if len(self.hashes(eid)) > 1]


def load_execution_scope(catalog_raw: bytes, load: Callable[[dict], bytes]) -> ExecutionScope:
    catalog = _json(catalog_raw)
    require(catalog.get("schema_version") == 1 and isinstance(catalog.get("inputs"), list)
            and 0 < len(catalog["inputs"]) <= MAX_INPUTS, "EXECUTION_SCOPE_INVALID_OR_INCOMPLETE")
    memo, bound = {}, []
    for row in catalog["inputs"]:
        expected = ExecutionKey(row["execution_id"], row["canonical_input_hash"])
        spec = row["input"]
        # Memoize exact source, never by execution_id alone. Validate each spec.
        def cached(source):
            identity = (source["repository"], source["ref"], source["path"], source["git_blob"])
            if identity not in memo:
                memo[identity] = load(source)
            return memo[identity]
        packet = ExternalResearchInputPacket.model_validate(_json(_checked_source(spec, cached)))
        require(input_key(packet) == expected, "EXECUTION_CATALOG_BINDING_MISMATCH")
        bound.append({**expected.as_dict(), "input": {k: spec[k] for k in (
            "repository", "ref", "path", "git_blob")}})
    keys = tuple(sorted({ExecutionKey(r["execution_id"], r["canonical_input_hash"]) for r in bound}))
    unique_bound = {canonical_hash(r): r for r in bound}
    return ExecutionScope(keys, canonical_hash([unique_bound[k] for k in sorted(unique_bound)]))


def require_promotion(input_raw: bytes, candidate_raw: bytes, expected: ExecutionKey,
                      scope: ExecutionScope):
    """Necessary gate only; PASS is not demand-side semantic approval or a write."""
    require(isinstance(scope, ExecutionScope), "EXECUTION_SCOPE_REQUIRED")
    scope.require_unambiguous(expected)
    _, _, validation = read_bound_execution(input_raw, candidate_raw, expected)
    require(validation.status is ExternalResearchValidationStatus.VALIDATED_FUNNEL_RESULT,
            "EXECUTION_GAP")
    return validation


def check_handoff_registration(raw: bytes, binding: dict, scope: ExecutionScope,
                               load: Callable[[dict], bytes]) -> ExecutionKey:
    """Check a proposed existing handoff before admitting it to a reading/registry.

    No registry write is implemented. The caller still owes explicit Human
    semantic acceptance; this function cannot create or authenticate that decision.
    """
    require(isinstance(binding, dict), "EXECUTION_BINDING_REQUIRED")
    key = ExecutionKey(binding["execution_id"], binding["canonical_input_hash"])
    require(isinstance(scope, ExecutionScope), "EXECUTION_SCOPE_REQUIRED")
    scope.require_unambiguous(key)
    validation = require_promotion(_checked_source(binding["input"], load),
        _checked_source(binding["candidate"], load), key, scope)
    from .attention_inbox import parse_research_attention_handoff
    parsed = parse_research_attention_handoff(raw.decode("utf-8"))
    require(parsed.research_funnel == validation.funnel_result, "EXECUTION_HANDOFF_RESULT_MISMATCH")
    return key


def project_registered_handoffs(entries: list[dict], load: Callable[[dict], tuple[bytes, dict]]) -> dict:
    """Existing current-state read admission, with independent legacy isolation.

    Load the pinned catalogue via the collector's existing bounded source loader.
    A conflict is an operational gap, never a new Research request. Historical
    files stay untouched; new external registrations must carry the exact pair.
    """
    from .attention_inbox import parse_research_attention_handoff
    from .current_state import project_handoffs
    memo = {}
    def cached(spec):
        key = json.dumps(spec, sort_keys=True)
        if key not in memo:
            memo[key] = load(spec)
        return memo[key]
    scope, scope_source, scope_error, known_ids = None, None, None, set()
    try:
        catalog_raw, scope_source = cached({"path": CATALOG_PATH})
        catalog = _json(catalog_raw)
        known_ids = {r["execution_id"] for r in catalog["inputs"]}
        scope = load_execution_scope(catalog_raw, lambda s: cached(s)[0])
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        scope_error = getattr(exc, "code", "EXECUTION_SCOPE_UNAVAILABLE")
    admitted, gaps, bindings = [], [], {}
    for entry in entries:
        try:
            raw, _ = cached(entry["source"])
            funnel = parse_research_attention_handoff(raw.decode("utf-8")).research_funnel
            binding = entry.get("external_execution")
            tracked = funnel.discovery.discovery_id in known_ids
            if binding is not None or tracked:
                require(scope is not None, scope_error or "EXECUTION_SCOPE_REQUIRED")
                if tracked:
                    require(len(scope.hashes(funnel.discovery.discovery_id)) <= 1, "EXECUTION_ID_CONFLICT")
                key = check_handoff_registration(raw, binding, scope, lambda s: cached(s)[0])
                bindings[(entry["source"]["path"], hashlib.sha256(raw).hexdigest())] = key
            admitted.append(entry)
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
            gaps.append({"source": entry.get("source"),
                         "status": getattr(exc, "code", "HANDOFF_OR_RESOLUTION_REJECTED"),
                         "error_type": type(exc).__name__})
    result = project_handoffs(admitted, cached)
    for section in ("active", "background", "resolved_history"):
        for row in result[section]:
            source = row["source"]
            key = bindings.get((source["path"], source.get("sha256")))
            if key is not None:
                row["external_execution"] = key.as_dict()
    result["gaps"].extend(gaps)
    if scope is None:
        # An absent external catalogue is not an error in an unrelated legacy
        # handoff. Always expose availability below; affected external inputs
        # still fail closed above and retain their own gap records.
        if known_ids or any(e.get("external_execution") is not None for e in entries):
            result["gaps"].append({"status": scope_error, "source": scope_source,
                                   "meaning": "EXTERNAL_PROMOTION_NOT_VERIFIED_LEGACY_INPUTS_INDEPENDENT"})
    else:
        result["gaps"].extend(scope.conflicts())
    result["execution_identity_scope"] = {
        "status": scope_error or ("EXECUTION_ID_CONFLICT" if scope.conflicts() else "CHECKED_PINNED_INPUT_SCOPE"),
        "scope_hash": scope.scope_hash if scope else None, "source": scope_source,
        "meaning": "EXPLICIT_PINNED_INPUTS_NOT_GLOBAL_LOCK_OR_RESEARCH_REGISTRATION"}
    return result