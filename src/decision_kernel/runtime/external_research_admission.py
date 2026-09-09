"""Pre-execution Harness gate. No sensing, Research, promotion or registry writer.

A check receipt is not an execution receipt. Trusted adapters must call this gate
at launch; a JSON PASS is not a reusable capability or a hard tool sandbox.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from . import external_research_identity as identity
from .external_research_execution import ExternalResearchInputPacket

PREFLIGHT_PURPOSE = "PRE_EXECUTION_SOURCE_PREFLIGHT"
DYNAMIC_CLASSES = {"SUBSEQUENT_ISSUER_UPDATE_CHECK", "LATEST_UPDATE_CHECK",
                   "RECENT_MATERIAL_DISCLOSURE_CHECK"}
MARKER = re.compile(r"REQUIRED_SOURCE_CLASS:([A-Z0-9_]+):(STATIC|LATEST_INVENTORY)")
MAX_ITEMS = 64


class AdmissionRejected(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require(ok: bool, code: str) -> None:
    if not ok:
        raise AdmissionRejected(code)


def clock(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None and result.utcoffset() is not None, "CLOCK_UNQUALIFIED")
    return result.astimezone(timezone.utc)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def items(value, *, empty: bool = False) -> list:
    require(isinstance(value, list) and (empty or bool(value)) and len(value) <= MAX_ITEMS,
            "SOURCE_PREFLIGHT_INCOMPLETE")
    return value


def keyed(rows: list) -> dict:
    require(all(isinstance(r, dict) and text(r.get("id")) for r in rows), "SOURCE_PREFLIGHT_INCOMPLETE")
    result = {r["id"]: r for r in rows}
    require(len(result) == len(rows), "SOURCE_PREFLIGHT_INCOMPLETE")
    return result


def check_preflight(raw: bytes, *, checked_at: str) -> dict:
    """Check declared accessibility/inventory records, never infer research claims.

    Primary authority, body-vs-shell and relevance are accountable collector
    assessments, not facts authenticated by a schema or by this function.
    """
    p = identity._json(raw)
    require(p.get("schema_version") == 1 and p.get("provenance") == "RECORDED_TOOL_RETURNS",
            "SOURCE_PREFLIGHT_INCOMPLETE")
    require(not {"research_claims", "route", "conclusion", "evidence_artifacts"}.intersection(p),
            "PREFLIGHT_IS_NOT_RESEARCH")
    start, finish, until, now = map(clock, (p["started_at"], p["finished_at"], p["valid_until"], checked_at))
    require(start <= finish <= now <= until, "SOURCE_PREFLIGHT_STALE_OR_INVALID")
    reads = keyed(items(p["reads"]))
    classes = keyed(items(p["required_classes"]))
    inventories = keyed(items(p["inventories"], empty=True))
    for r in reads.values():
        require(all(text(r.get(k)) for k in ("identity", "locator", "tool_reference")),
                "SOURCE_PREFLIGHT_INCOMPLETE")
        url = urlsplit(r["locator"])
        require(url.scheme == "https" and bool(url.hostname) and not url.username and not url.password,
                "SOURCE_PREFLIGHT_INCOMPLETE")
        require(r["authority"] in {"PRIMARY", "SECONDARY"} and r["kind"] in {"BODY", "INDEX", "SHELL"}
                and type(r["succeeded"]) is bool and start <= clock(r["checked_at"]) <= finish,
                "SOURCE_PREFLIGHT_INCOMPLETE")
        if r["succeeded"] and r["kind"] == "BODY":
            require(re.fullmatch(r"[0-9a-f]{64}", r.get("body_sha256", "")) is not None,
                    "SOURCE_PREFLIGHT_INCOMPLETE")

    def primary_body(rid: str) -> dict:
        r = reads[rid]
        require(r["succeeded"] and r["kind"] == "BODY" and r["authority"] == "PRIMARY",
                "SOURCE_PREFLIGHT_INCOMPLETE")
        return r

    queries, used_inventories = 0, set()
    for cid, c in classes.items():
        require(re.fullmatch(r"[A-Z0-9_]+", cid) is not None and c["mode"] in {"STATIC", "LATEST_INVENTORY"},
                "SOURCE_PREFLIGHT_INCOMPLETE")
        if cid in DYNAMIC_CLASSES:
            require(c["mode"] == "LATEST_INVENTORY", "SOURCE_PREFLIGHT_INCOMPLETE")
        for rid in items(c["body_ids"], empty=c["mode"] == "LATEST_INVENTORY"):
            primary_body(rid)
        if c["mode"] == "STATIC":
            require(c.get("inventory_id") is None, "SOURCE_PREFLIGHT_INCOMPLETE")
            continue
        inv_id = c["inventory_id"]
        require(inv_id not in used_inventories, "SOURCE_PREFLIGHT_INCOMPLETE")
        used_inventories.add(inv_id)
        inv = inventories[inv_id]
        a, b = clock(inv["started_at"]), clock(inv["finished_at"])
        require(inv["class_id"] == cid and start <= a <= b <= finish, "SOURCE_PREFLIGHT_INCOMPLETE")
        planned = items(inv["planned_queries"])
        events = items(inv["query_events"])
        require(len(planned) == len(set(planned)) and all(text(q) for q in planned)
                and [e["query"] for e in events] == planned, "SOURCE_PREFLIGHT_INCOMPLETE")
        for e in events:
            require(e["status"] == "SUCCEEDED" and text(e["tool_reference"])
                    and a <= clock(e["checked_at"]) <= b, "SOURCE_PREFLIGHT_INCOMPLETE")
        queries += len(events)
        seen = set()
        for lead in items(inv["leads"], empty=True):
            require(text(lead["identity"]) and text(lead["locator"]) and text(lead["relevance_note"])
                    and type(lead["decision_relevant"]) is bool
                    and lead["authority"] in {"PRIMARY", "SECONDARY"}, "SOURCE_PREFLIGHT_INCOMPLETE")
            lk = (lead["identity"], lead["locator"])
            require(lk not in seen, "SOURCE_PREFLIGHT_INCOMPLETE")
            seen.add(lk)
            if lead["decision_relevant"]:
                # A secondary lead must resolve to an identified readable primary body.
                body = primary_body(lead["body_id"])
                if lead["authority"] == "PRIMARY":
                    require(lead["locator"] == lead["primary_locator"]
                            and lead["identity"] == lead["primary_identity"], "SOURCE_PREFLIGHT_INCOMPLETE")
                require(body["identity"] == lead["primary_identity"]
                        and body["locator"] == lead["primary_locator"]
                        and a <= clock(body["checked_at"]) <= b, "SOURCE_PREFLIGHT_INCOMPLETE")
    require(used_inventories == set(inventories), "SOURCE_PREFLIGHT_INCOMPLETE")
    limits = p["limits"]
    require(type(limits["max_queries"]) is int and type(limits["max_reads"]) is int
            and 0 <= queries <= limits["max_queries"] <= MAX_ITEMS
            and len(reads) <= limits["max_reads"] <= MAX_ITEMS, "SOURCE_PREFLIGHT_INCOMPLETE")
    return p


def _sources(packet):
    return [r.model_dump(mode="json") for r in packet.source_refs]


def _publication_checks(packet, preflight, load, commit) -> None:
    """Minimal supported seed: exact retained Git file with proved publication.

    Unsupported/unknown publication provenance is rejected, not guessed. The
    underlying observation date is never substituted for the internal Git clock.
    """
    proofs = preflight["seed_publications"]
    require(isinstance(proofs, list) and len(proofs) == len(packet.seed_evidence_artifacts), "INPUT_REJECTED")
    by_id = {r["evidence_id"]: r for r in proofs}
    require(len(by_id) == len(proofs), "INPUT_REJECTED")
    for seed in packet.seed_evidence_artifacts:
        proof = by_id[str(seed.id)]
        spec = proof["source"]
        require(proof["kind"] == "GIT_COMMIT" and spec in _sources(packet), "INPUT_REJECTED")
        body = identity._checked_source(spec, load)
        meta = commit(spec["ref"])
        published = clock(meta["committer"]["date"])
        require(meta["sha"] == spec["ref"] and published == seed.published_at
                and published <= seed.available_at <= packet.research_cutoff
                and published <= seed.retrieved_at <= packet.research_cutoff
                and seed.content_hash == digest(body)
                and seed.source_locator == f"https://github.com/{identity.REPOSITORY}/blob/{spec['ref']}/{spec['path']}",
                "INPUT_REJECTED")


def prepare_input(*, input_raw: bytes, preflight_raw: bytes, catalog_source: dict,
                  load: Callable[[dict], bytes], commit: Callable[[str], dict], checked_at: str,
                  current_code: Callable[[], str]):
    """No formal input write or Research call occurs in this prepare step."""
    p = check_preflight(preflight_raw, checked_at=checked_at)
    try:
        packet = ExternalResearchInputPacket.model_validate(identity._json(input_raw))
    except ValueError as exc:
        raise AdmissionRejected("INPUT_REJECTED") from exc
    require(current_code() == packet.code_commit, "ADMISSION_CODE_OR_SCOPE_MOVED")
    require(all(p[k] == getattr(packet, k) for k in ("case_id", "ticker", "security_id")), "INPUT_REJECTED")
    require(clock(p["finished_at"]) <= packet.selected_at <= packet.research_cutoff <= clock(checked_at),
            "INPUT_REJECTED")
    declarations = [MARKER.fullmatch(s) for s in packet.known_unknowns if s.startswith("REQUIRED_SOURCE_CLASS:")]
    require(declarations and all(declarations), "INPUT_REQUIRED_CLASSES_UNDECLARED")
    required = [(m[1], m[2]) for m in declarations]
    require(len(required) == len(set(k for k, _ in required))
            and set(required) == {(r["id"], r["mode"]) for r in p["required_classes"]},
            "SOURCE_PREFLIGHT_INCOMPLETE")
    refs = [s for s in _sources(packet) if s["purpose"] == PREFLIGHT_PURPOSE]
    require(len(refs) == 1 and identity._checked_source(refs[0], load) == preflight_raw,
            "PREFLIGHT_INPUT_BINDING_MISMATCH")
    pf_commit = commit(refs[0]["ref"])
    require(pf_commit["sha"] == refs[0]["ref"]
            and clock(p["finished_at"]) <= clock(pf_commit["committer"]["date"]) <= packet.selected_at,
            "PREFLIGHT_NOT_COMMITTED_BEFORE_SELECTION")
    try:
        _publication_checks(packet, p, load, commit)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        raise AdmissionRejected("INPUT_REJECTED") from exc
    key = identity.input_key(packet)  # Only the original parsed model is hashed.
    require(catalog_source["ref"] == packet.code_commit and catalog_source["path"] == identity.CATALOG_PATH,
            "EXECUTION_SCOPE_NOT_CURRENT_CODE")
    catalog_raw = identity._checked_source(catalog_source, load)
    scope = identity.load_execution_scope(catalog_raw, load)
    # Reuse #288's conflict check on the declared scope plus this prospective key.
    # This view does not claim the not-yet-committed input is already in the catalogue.
    prospective = identity.ExecutionScope(tuple(set(scope.keys) | {key}), scope.scope_hash)
    prospective.require_unambiguous(key)
    return packet, key, catalog_raw


def assess_admission(*, input_raw: bytes, preflight_raw: bytes, catalog_source: dict,
                     load: Callable[[dict], bytes], commit: Callable[[str], dict], checked_at: str,
                     current_code: Callable[[], str], now: Callable[[], str],
                     input_source: dict | None = None, expected_key: dict | None = None) -> dict:
    """Recheck before launch. A prepare PASS alone never permits execution."""
    report = {"schema_version": 1, "status": "NOT_EXECUTED", "reason": None,
              "research_execution_allowed": False, "formal_research_budget_used": 0,
              "funnel_invoked": False, "checked_at": checked_at, "execution_key": None,
              "input_source": None, "identity_scope_hash": None,
              "preflight_sha256": digest(preflight_raw), "input_file_sha256": digest(input_raw),
              "authority": "NONE", "human_attention_authority": "NONE",
              "research_authority": "NONE", "investment_authority": "NONE", "checks": {}, "proof_scope": "TRUSTED_ADAPTER_RECORDS_NOT_GLOBAL_LOCK_OR_HARD_SANDBOX"}
    phase = "SOURCE_PREFLIGHT_INCOMPLETE"
    try:
        packet, key, catalog_raw = prepare_input(input_raw=input_raw, preflight_raw=preflight_raw,
            catalog_source=catalog_source, load=load, commit=commit, checked_at=checked_at,
            current_code=current_code)
        report["execution_key"] = key.as_dict()
        report["checks"] = {"source_preflight": "PASS", "input_model_validation": "PASS",
                            "seed_publication": "PASS", "canonical_input_hash": "COMPUTED",
                            "identity_precheck": "PASS", "exact_input_readback": "NOT_CHECKED",
                            "identity_postcheck": "NOT_CHECKED"}
        if input_source is None:
            report["reason"] = "INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION"
            return report
        phase = "EXACT_INPUT_READBACK_REJECTED"
        require(expected_key == key.as_dict(), "EXECUTION_INPUT_BINDING_MISMATCH")
        require(input_source["path"] == packet.candidate_output_prefix.rstrip("/") + "/input.json",
                "EXECUTION_SOURCE_INVALID")
        remote = identity._checked_source(input_source, load)
        require(remote == input_raw, "EXACT_INPUT_BYTES_DIFFER")
        parsed = ExternalResearchInputPacket.model_validate(identity._json(remote))
        require(identity.input_key(parsed) == key, "EXECUTION_INPUT_BINDING_MISMATCH")
        meta = commit(input_source["ref"])
        require(meta["sha"] == input_source["ref"]
                and packet.research_cutoff <= clock(meta["committer"]["date"]) <= clock(checked_at),
                "INPUT_COMMIT_CLOCK_INVALID")
        # Read the pinned catalogue AGAIN after remote input readback, then use
        # the original loader to verify the whole declared scope plus exact input.
        latest_raw = identity._checked_source(catalog_source, load)
        require(latest_raw == catalog_raw, "EXECUTION_SCOPE_CHANGED")
        catalog = identity._json(latest_raw)
        catalog["inputs"].append({**key.as_dict(), "input": input_source})
        scope = identity.load_execution_scope(json.dumps(catalog).encode(), load)
        scope.require_unambiguous(key)
        require(current_code() == packet.code_commit, "ADMISSION_CODE_OR_SCOPE_MOVED")
        finished_at = now()
        require(clock(checked_at) <= clock(finished_at), "ADMISSION_CLOCK_REVERSED")
        check_preflight(preflight_raw, checked_at=finished_at)
        report["finished_at"] = finished_at
        report["checks"].update(exact_input_readback="PASS", identity_postcheck="PASS")
        report.update(reason="RESEARCH_EXECUTION_ALLOWED", research_execution_allowed=True,
                      input_source=dict(input_source), identity_scope_hash=scope.scope_hash)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        report["reason"] = getattr(exc, "code", phase)
        report["error_type"] = type(exc).__name__  # Never echo source instructions or tokens.
    return report


def execute_after_admission(*, executor: Callable, **checks):
    """The trusted adapter calls Research only after a fresh complete check.

    No generic shell/subprocess or model client is introduced here. A failed
    gate never invokes the callback, so it cannot spend its Research budget.
    """
    report = assess_admission(**checks)
    if not report["research_execution_allowed"]:
        return report, None
    return report, executor(checks["input_raw"], report["execution_key"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check pre-execution admission; never run Research.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--catalog-source", type=Path, required=True)
    parser.add_argument("--input-source", type=Path)
    parser.add_argument("--expected-key", type=Path)
    args = parser.parse_args(argv)
    try:
        from .current_state_delivery import GitHubAPI
        require(bool(os.environ.get("GH_TOKEN")), "GITHUB_READ_CONNECTION_REQUIRED")
        api = GitHubAPI(os.environ["GH_TOKEN"])
        report = assess_admission(input_raw=args.input.read_bytes(), preflight_raw=args.preflight.read_bytes(),
            catalog_source=identity._json(args.catalog_source.read_bytes()),
            input_source=identity._json(args.input_source.read_bytes()) if args.input_source else None,
            expected_key=identity._json(args.expected_key.read_bytes()) if args.expected_key else None,
            load=lambda spec: api.file(spec["path"], spec["ref"]),
            commit=lambda ref: api.get("git/commits/" + ref), checked_at=datetime.now(timezone.utc).isoformat(),
            # Bypass only the client's GET memo for this mutable ref. No write/retry.
            current_code=lambda: api._call("GET", "git/ref/heads/main").json()["object"]["sha"],
            now=lambda: datetime.now(timezone.utc).isoformat())
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, ImportError) as exc:
        report = {"status": "NOT_EXECUTED", "reason": getattr(exc, "code", "ADMISSION_INPUT_UNAVAILABLE"),
                  "research_execution_allowed": False, "formal_research_budget_used": 0,
                  "funnel_invoked": False, "error_type": type(exc).__name__}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["research_execution_allowed"] or report["reason"] == "INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
