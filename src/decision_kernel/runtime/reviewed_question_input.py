"""Bind one authored Radar question to the existing input-preparation contract.

No question generation, selection, executor, file writer, source client or scheduler.
The declaration is data. Structural checks do not certify relevance or economic truth.
"""
from __future__ import annotations

import re
from typing import Callable

from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from .external_research_execution import ExternalResearchInputPacket

PURPOSE = "REVIEWED_RADAR_QUESTION"
LANE = "REVIEWED_RADAR_QUESTION"
FORMAT = "reviewed-radar-question-v0"
FIELDS = {
    "format", "case_id", "ticker", "security_id", "question_id", "revision",
    "predecessor", "declared_at", "reading_source", "question", "why_now",
    "falsification_test", "required_classes", "known_counterevidence", "known_unknowns",
    "next_discriminating_search", "origins", "existing_research_relation",
}
ORIGIN_KINDS = {"SECTOR_LEADER", "CONCEPT_CURRENT_MEMBER", "INSTITUTIONAL_WINDOWS",
                "NEWS_EVENT_CANDIDATE", "INDUSTRY_VARIABLE_OBSERVATION"}


def _require(ok: bool, code: str) -> None:
    admission.require(ok, code)


def _texts(value) -> list:
    _require(isinstance(value, list) and 0 < len(value) <= admission.MAX_ITEMS
             and all(admission.text(x) for x in value), "QUESTION_TEXT_LIST_INVALID")
    return value


def _declaration(raw: bytes) -> dict:
    q = identity._json(raw)
    _require(set(q) == FIELDS and q["format"] == FORMAT, "QUESTION_DECLARATION_SHAPE")
    for key in ("case_id", "ticker", "security_id", "question", "why_now",
                "falsification_test", "next_discriminating_search"):
        _require(admission.text(q[key]), "QUESTION_TEXT_MISSING")
    _require(isinstance(q["question_id"], str)
             and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,127}", q["question_id"]) is not None,
             "QUESTION_ID_INVALID")
    _require(type(q["revision"]) is int and q["revision"] >= 1, "QUESTION_REVISION_INVALID")
    _texts(q["known_counterevidence"])
    _texts(q["known_unknowns"])
    return q


def _prepare(*, question_source: dict, input_raw: bytes, preflight_raw: bytes,
            catalog_source: dict, load: Callable[[dict], bytes],
            commit: Callable[[str], dict], checked_at: str,
            current_code: Callable[[], str]) -> dict:
    """Read exact declared bytes, then call original prepare_input, never launch.

    load/commit are the caller's existing bounded, read-only Git access. No new
    network client or API allowance is supplied. Raises finite rejection errors.
    This receipt is not executable admission; the original launch-time gate remains.
    """
    packet = ExternalResearchInputPacket.model_validate(identity._json(input_raw))
    refs = [s.model_dump(mode="json") for s in packet.source_refs]
    _require(packet.source_lane == LANE
             and [s for s in refs if s["purpose"] == PURPOSE] == [question_source],
             "QUESTION_SOURCE_INPUT_BINDING_MISMATCH")
    qraw = identity._checked_source(question_source, load)
    q = _declaration(qraw)
    declared = admission.clock(q["declared_at"])
    pf = identity._json(preflight_raw)

    def published(spec: dict):
        meta = commit(spec["ref"])
        _require(meta["sha"] == spec["ref"], "QUESTION_SOURCE_COMMIT_MISMATCH")
        return admission.clock(meta["committer"]["date"])

    def prior_source(spec: dict) -> bytes:
        _require(spec in refs and spec != question_source, "QUESTION_CONTEXT_NOT_IN_INPUT")
        body = identity._checked_source(spec, load)
        _require(published(spec) <= declared, "QUESTION_CONTEXT_AFTER_DECLARATION")
        return body

    _require(declared <= published(question_source) <= admission.clock(pf["started_at"]),
             "QUESTION_NOT_FROZEN_BEFORE_PREFLIGHT")
    _require(all(q[k] == getattr(packet, k) for k in ("case_id", "ticker", "security_id"))
             and q["question"] == packet.research_question
             and q["next_discriminating_search"] == packet.next_discriminating_search,
             "QUESTION_PACKET_IDENTITY_MISMATCH")
    _require(set(q["known_unknowns"]) <= set(packet.known_unknowns), "QUESTION_UNKNOWNS_DROPPED")
    # A researcher-authored question is not newly acquired seed Evidence.
    _require(all(seed.content_hash != admission.digest(qraw) for seed in packet.seed_evidence_artifacts),
             "QUESTION_DECLARATION_IS_NOT_SEED_EVIDENCE")

    rs = q["reading_source"]
    _require(isinstance(rs, dict) and rs.get("ref") == packet.current_state_commit
             and rs.get("path") == "current-state.json", "QUESTION_READING_NOT_PINNED")
    context = identity._json(prior_source(rs))
    reading.validate_read_package(context)
    _require(context["reading_hash"] == packet.current_state_reading_hash
             and admission.clock(context["generated_at"]) <= declared,
             "QUESTION_READING_IDENTITY_MISMATCH")
    # Reusing a saved window is explicit; this is not current market qualification.
    _require(admission.clock(checked_at) <= admission.clock(context["checks"]["recheck_after"]),
             "QUESTION_READING_RECHECK_REQUIRED")

    origins = admission.items(q["origins"])
    qualified = False
    origin_bindings = set()
    for origin in origins:
        _require(isinstance(origin, dict) and set(origin) == {
            "kind", "source", "observed_at", "qualification", "qualification_reason"},
            "QUESTION_ORIGIN_SHAPE")
        _require(origin["kind"] in ORIGIN_KINDS and origin["qualification"] in {
            "QUALIFIED_FOR_DECLARED_SCOPE", "CONTEXT_ONLY", "UNKNOWN"}
            and admission.text(origin["qualification_reason"]), "QUESTION_ORIGIN_QUALIFICATION_UNDECLARED")
        prior_source(origin["source"])
        _require(admission.clock(origin["observed_at"]) <= published(origin["source"]),
                 "QUESTION_ORIGIN_CLOCK_INVALID")
        binding = (origin["kind"], origin["source"]["ref"], origin["source"]["path"])
        _require(binding not in origin_bindings, "QUESTION_DUPLICATE_ORIGIN")
        origin_bindings.add(binding)
        qualified |= origin["qualification"] == "QUALIFIED_FOR_DECLARED_SCOPE"
    _require(qualified, "QUESTION_HAS_NO_DECLARED_QUALIFIED_ORIGIN")

    relation = q["existing_research_relation"]
    _require(isinstance(relation, dict) and set(relation) == {"kind", "note", "source_refs"}
             and relation["kind"] in {"NEW_DISTINCT_QUESTION", "CONTINUE_ANALYSIS", "CHECK_TRIGGER", "METHOD_REVIEW"}
             and admission.text(relation["note"]), "QUESTION_RESEARCH_RELATION_INVALID")
    for spec in admission.items(relation["source_refs"], empty=True):
        prior_source(spec)
    # A declared complete Industry input may continue saved interactive analysis
    # for its FIRST formal invocation. This is input qualification, not permission.
    # The original catalogue and host's create-only question/day records still
    # reject any prior formal attempt. Default/other continuation kinds stay closed.
    retained_initial = False
    if (relation["kind"] == "CONTINUE_ANALYSIS" and relation["source_refs"]
        and all(s["purpose"] == "RETAINED_ANALYSIS_PREDECESSOR" for s in relation["source_refs"])
        and ((packet.method_version, packet.prompt_version) == ("single-quick-v1", "single-quick-outcomes-v1")
             or packet.prompt_version == "reviewed-question-stock-v0")
        and any(o["kind"] == "INDUSTRY_VARIABLE_OBSERVATION"
                and o["qualification"] == "QUALIFIED_FOR_DECLARED_SCOPE" for o in origins)):
        from . import reviewed_full_input as full
        contexts = [s for s in refs if s["purpose"] == "MODEL_CONTEXT"]
        if len(contexts) == 1:
            stored = identity._checked_source(contexts[0], load)
            if identity._json(stored).get("policy") == full.POLICY:
                full.unpack(stored, ticker=packet.ticker)
                retained_initial = True
    _require(relation["kind"] == "NEW_DISTINCT_QUESTION" or retained_initial,
             "QUESTION_CONTINUATION_REQUIRES_ORIGINAL_HOST")

    if q["predecessor"] is None:
        _require(q["revision"] == 1, "QUESTION_PREDECESSOR_REQUIRED")
    else:
        previous = _declaration(prior_source(q["predecessor"]))
        _require(all(previous[k] == q[k] for k in ("case_id", "ticker", "security_id", "question_id"))
                 and q["revision"] == previous["revision"] + 1
                 and admission.clock(previous["declared_at"]) <= published(q["predecessor"]),
                 "QUESTION_PREDECESSOR_MISMATCH")

    classes = admission.keyed(admission.items(q["required_classes"]))
    actual = admission.keyed(admission.items(pf["required_classes"]))
    _require(set(classes) == set(actual), "QUESTION_REQUIRED_CLASSES_CHANGED")
    inventories = admission.keyed(admission.items(pf["inventories"], empty=True))
    for cid, spec in classes.items():
        _require(set(spec) == {"id", "mode", "planned_queries"}
                 and spec["mode"] in {"STATIC", "LATEST_INVENTORY"}
                 and spec["mode"] == actual[cid]["mode"], "QUESTION_REQUIRED_CLASSES_CHANGED")
        if spec["mode"] == "STATIC":
            _require(spec["planned_queries"] == [], "QUESTION_STATIC_QUERY_PLAN_INVALID")
        else:
            planned = _texts(spec["planned_queries"])
            inv = inventories[actual[cid]["inventory_id"]]
            _require(planned == inv["planned_queries"], "QUESTION_UPDATE_SCOPE_CHANGED")

    # Original preflight, publication, input model and execution-scope gates, unchanged.
    checked_packet, key, catalog_raw = admission.prepare_input(
        input_raw=input_raw, preflight_raw=preflight_raw, catalog_source=catalog_source,
        load=load, commit=commit, checked_at=checked_at, current_code=current_code)
    for row in identity._json(catalog_raw)["inputs"]:
        prior = ExternalResearchInputPacket.model_validate(
            identity._json(identity._checked_source(row["input"], load)))
        if prior.security_id != packet.security_id or identity.input_key(prior) == key:
            continue
        question_refs = [s.model_dump(mode="json") for s in prior.source_refs if s.purpose == PURPOSE]
        _require(len(question_refs) <= 1, "QUESTION_CATALOG_DECLARATION_AMBIGUOUS")
        if prior.source_lane == LANE:
            _require(len(question_refs) == 1, "QUESTION_CATALOG_DECLARATION_MISSING")
        if question_refs:
            old = _declaration(identity._checked_source(question_refs[0], load))
            _require(all(old[k] == getattr(prior, k) for k in ("case_id", "ticker", "security_id"))
                     and old["question"] == prior.research_question, "QUESTION_CATALOG_BINDING_MISMATCH")
            _require(old["question_id"] != q["question_id"],
                     "QUESTION_ALREADY_HAS_EXECUTION_USE_ORIGINAL_HOST")

    return {
        "status": "QUESTION_INPUT_PREPARED_NOT_EXECUTED",
        "question_source": dict(question_source), "question_id": q["question_id"],
        "revision": q["revision"], "execution_key": key.as_dict(),
        "input_file_sha256": admission.digest(input_raw),
        "preflight_sha256": admission.digest(preflight_raw),
        "catalog_sha256": admission.digest(catalog_raw),
        "current_state_commit": checked_packet.current_state_commit,
        "current_state_reading_hash": checked_packet.current_state_reading_hash,
        "dedup_scope": "EXPLICIT_CATALOG_QUESTION_IDS_NOT_GLOBAL_SEMANTIC_DEDUP",
        "qualification": "DECLARATION_AND_SOURCE_BINDING_NOT_ECONOMIC_TRUTH_OR_QUESTION_QUALITY",
        "research_execution_allowed": False, "formal_research_budget_used": 0,
        "funnel_invoked": False, "human_acceptance": "NOT_ESTABLISHED",
        "investment_authority": "NONE", "remote_writes": 0,
    }


def prepare(*, question_source: dict, input_raw: bytes, preflight_raw: bytes,
            catalog_source: dict, load: Callable[[dict], bytes],
            commit: Callable[[str], dict], checked_at: str,
            current_code: Callable[[], str]) -> dict:
    """Prepare only, preserving original rejection codes without source text."""
    try:
        return _prepare(question_source=question_source, input_raw=input_raw,
            preflight_raw=preflight_raw, catalog_source=catalog_source, load=load,
            commit=commit, checked_at=checked_at, current_code=current_code)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        code = getattr(exc, "code", "QUESTION_PREPARATION_REJECTED")
        if not isinstance(code, str) or re.fullmatch(r"[A-Z0-9_]{1,128}", code) is None:
            code = "QUESTION_PREPARATION_REJECTED"
        raise admission.AdmissionRejected(code) from None