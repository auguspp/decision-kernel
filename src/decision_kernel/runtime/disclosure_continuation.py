"""Thin exact Human-response/predecessor/new-source binding, not an approval engine.

Only a reviewed main request can opt in. Interaction owns genuine intent/semantic
interpretation; usernames, source prose and digest calculation are not permission.
"""
from __future__ import annotations

from . import current_state as read
from . import external_research_identity as identity
from . import incremental_disclosure as work
from . import saved_research_once as once
from .external_research_execution import ExternalResearchInputPacket, ExternalResearchCandidate

REQUEST_PATH = "research_runs/disclosure-continuation-request.json"
REQUEST_PURPOSE = "TRUSTED_HUMAN_CONTINUATION_REQUEST"
MODE = "HUMAN_AUTHORIZED_DISCLOSURE_CONTINUATION"
FIELDS = {"schema_version", "mode", "enabled", "permission", "predecessor",
          "exposed_reading", "new_assessment_input_hash", "prior_question",
          "follow_up_question", "new_evidence_reason"}


READING_MODE = "HUMAN_AUTHORIZED_SAME_SOURCE_READING_CONTINUATIONS"
READING_FIELDS = {"schema_version", "mode", "enabled", "permission", "exposed_reading", "source_run_id", "items"}
READING_ITEM_FIELDS = {"ticker", "assessment_input_hash", "predecessor", "prior_question",
                       "follow_up_question", "new_evidence_reason", "required_reading_pdf_sha256s"}


def reading_requests(request):
    """An explicit v2 envelope at the ORIGINAL request path; v1 remains unchanged."""
    if request.get("mode") != READING_MODE:
        return None
    once.require(set(request) == READING_FIELDS and type(request["schema_version"]) is int
        and request["schema_version"] == 2 and request["enabled"] is True
        and type(request["source_run_id"]) is int and request["source_run_id"] > 0
        and isinstance(request["items"], list) and 0 < len(request["items"]) <= work.MAX_PACKETS,
        "source-reading continuation not explicitly enabled")
    permission = request["permission"]
    once.require(set(permission) == {"issue_number", "comment_id", "body_sha256", "record_body", "verbatim", "response_kind", "tickers"}
        and isinstance(permission["tickers"], list), "source-reading permission fields differ")
    keys, tickers = [], set()
    for item in request["items"]:
        once.require(set(item) == READING_ITEM_FIELDS and item["ticker"] in work.SCOPE,
                     "source-reading continuation item differs")
        work.continuation_prefix(item["assessment_input_hash"], permission["comment_id"])
        hashes = item["required_reading_pdf_sha256s"]
        once.require(isinstance(hashes, list) and hashes and len(hashes) == len(set(hashes))
            and all(isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h) for h in hashes),
            "source-reading required body identity invalid")
        keys.append(item["assessment_input_hash"]); tickers.add(item["ticker"])
    once.require(len(keys) == len(set(keys)) and len(permission["tickers"]) == len(set(permission["tickers"]))
        and set(permission["tickers"]) == tickers, "source-reading permission targets differ")
    return request["items"]


def bound_public_context(checked, context):
    """Freeze actual same-PDF readings, not a new primary-source claim or permission."""
    if "execution_prefix" not in checked:
        return checked["public_context"]
    from . import disclosure_source_reading as pages
    values = context["source_capture"].get("page_readings", [])
    once.require({v["pdf_sha256"] for v in values} == set(checked["required_reading_pdf_sha256s"])
        and context["source_capture"]["run_id"] == checked["source_run_id"],
        "continuation has no exact newly readable required bodies")
    by_locator = {e["source_locator"]: e for e in context["disclosure_packet"]["evidence"]}
    for value in values:
        pages.validate(value, by_locator[value["source_locator"]])
    return {**checked["public_context"], "new_reading_hashes": sorted(v["reading_hash"] for v in values),
            "reading_increment_kind": "SAME_ORIGINAL_PDF_NEW_READABLE_REPRESENTATION_NOT_NEW_PRIMARY_SOURCE"}

def _same(left, right):
    return all(left.get(k) == right.get(k) for k in ("repository", "ref", "path", "git_blob", "sha256"))


def check(*, api, code_commit: str, request_source: dict, new_packet_raw: bytes,
          checked_at: str) -> dict:
    """Validate binding only. No writes, model, routing, approval or state mutation."""
    once.require(request_source["path"] == REQUEST_PATH and request_source["ref"] == code_commit
                 and request_source["purpose"] == REQUEST_PURPOSE, "continuation request is not trusted main input")
    now = read.clock(checked_at)
    sources, loaded = [], {}
    def load(spec, *, exposure_deadline=None):
        raw = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
        meta = api.get("git/commits/" + spec["ref"])
        once.require(meta["sha"] == spec["ref"] and read.clock(meta["committer"]["date"]) <= now,
                     "continuation source commit is from the future")
        if exposure_deadline is not None:
            once.require(read.clock(meta["committer"]["date"]) <= exposure_deadline,
                         "permission precedes its exposed reading commit")
        loaded[(spec["ref"], spec["path"])] = raw
        return raw
    request = identity._json(load(request_source))
    envelope = request
    entries = reading_requests(envelope)
    child = work._packet(new_packet_raw)
    entry = None
    if entries is not None:
        matches = [item for item in entries if item["assessment_input_hash"] == child.assessment_input_hash]
        once.require(len(matches) == 1 and matches[0]["ticker"] == child.stock_code, "continuation target differs")
        entry = matches[0]
        permission = {k: v for k, v in envelope["permission"].items() if k != "tickers"}
        permission["ticker"] = entry["ticker"]
        request = {"schema_version": 1, "mode": MODE, "enabled": True, "permission": permission,
            "exposed_reading": envelope["exposed_reading"], "new_assessment_input_hash": child.assessment_input_hash,
            **{k: entry[k] for k in ("predecessor", "prior_question", "follow_up_question", "new_evidence_reason")}}
    once.require(set(request) == FIELDS and request["schema_version"] == 1
                 and request["mode"] == MODE and request["enabled"] is True, "continuation not explicitly enabled")
    for key in ("prior_question", "follow_up_question", "new_evidence_reason"):
        once.require(isinstance(request[key], str) and 0 < len(request[key].strip()) <= 4000,
                     "continuation question or discriminating reason missing")
    child = work._packet(new_packet_raw)
    once.require(child.assessment_input_hash == request["new_assessment_input_hash"], "continuation target differs")
    prior = request["predecessor"]
    once.require(set(prior) == {"kind", "packet", "input", "result"}, "predecessor binding unsupported")
    old_raw, result_raw = load(prior["packet"]), load(prior["result"])
    old = work._packet(old_raw)
    once.require(old.stock_code == child.stock_code
                 and ((entry is None and old.assessment_input_hash != child.assessment_input_hash)
                      or (entry is not None and old_raw == new_packet_raw and prior["kind"] == "PRE_EXECUTION_FAILURE")),
                 "continuation must preserve company and not reset the old key")
    old_prefix = work.request_path(old.assessment_input_hash).removesuffix("packet.json")
    once.require(prior["packet"]["path"] == old_prefix + "packet.json", "predecessor packet path differs")
    if prior["kind"] == "CANDIDATE":
        once.require(prior["input"] is not None and prior["input"]["path"] == old_prefix + "input.json"
                     and prior["result"]["path"] == old_prefix + "candidate.json", "predecessor candidate paths differ")
        input_raw = load(prior["input"])
        packet = ExternalResearchInputPacket.model_validate(identity._json(input_raw))
        candidate = ExternalResearchCandidate.model_validate(identity._json(result_raw))
        work.describe_outcome(reserved_packet=old_raw, input_raw=input_raw, candidate_raw=result_raw)
        once.require(request["prior_question"] == packet.research_question,
                     "continuation changed the frozen predecessor question")
        public = {"kind": "PRIOR_AI_CANDIDATE_NOT_PRIMARY_EVIDENCE_OR_HUMAN_ACCEPTANCE",
                  "question": packet.research_question, "completion": candidate.completion.value,
                  "pre_research": candidate.pre_research.model_dump(mode="json") if candidate.pre_research else None,
                  "quick_research": candidate.quick_research.model_dump(mode="json") if candidate.quick_research else None}
        sources.append({**prior["input"], "purpose": "CONTINUATION_PREDECESSOR_INPUT"})
    else:
        failure = identity._json(result_raw)
        once.require(prior["kind"] == "PRE_EXECUTION_FAILURE" and prior["input"] is None
                     and prior["result"]["path"] == old_prefix + "failure.json"
                     and failure.get("schema_version") == 1 and failure.get("formal_research_budget_used") == 0
                     and all(failure.get(k, "NONE") == "NONE" for k in read.AUTHORITY)
                     and failure.get("record_kind") == "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT"
                     and failure.get("research_execution") == "NOT_EXECUTED"
                     and failure.get("funnel_status") == "NOT_REACHED"
                     and failure.get("assessment_input_hash") == old.assessment_input_hash
                     and failure.get("packet_blob") == read.blob_sha(old_raw)
                     and failure.get("packet_sha256") == read.sha256(old_raw), "predecessor failure differs")
        public = {"kind": "PRIOR_SOURCE_FAILURE_NOT_RESEARCH", "question": request["prior_question"],
                  "status": failure.get("status")}
    # A different input hash caused only by time/context/wording is not new Evidence.
    old_pdfs = {e.pdf_sha256 for e in old.evidence}
    old_unreadable = {e.pdf_sha256 for e in old.evidence if e.text_status.value == "NO_TEXT"}
    changed = [e.pdf_sha256 for e in child.evidence if e.pdf_sha256 not in old_pdfs
               or (e.pdf_sha256 in old_unreadable and e.text_status.value == "EXTRACTED")]
    if entry is None:
        once.require(bool(changed), "continuation has no new discriminating body or newly readable required body")
    else:
        from .disclosure_source_reading import text_ok
        from .saved_disclosure_preparation import QUESTION
        gaps = {e.pdf_sha256 for e in old.evidence if any(not text_ok(p.text) for p in e.pages)}
        once.require(gaps and set(entry["required_reading_pdf_sha256s"]) == gaps
            and failure.get("error_code") in {"required page text unavailable", "required body has no text",
                "required text contains encoding damage", "required page visual review unavailable"}
            and request["prior_question"] == request["follow_up_question"] == QUESTION,
            "source-reading continuation lacks the original required-source gap")
        changed = []  # New readability of the SAME PDF, never a new independent source.

    # REUSE the canonical Issue/comment response, not a second Human ledger.
    # Only the reviewed main request classifies actual intent. The GitHub author
    # is deliberately not used as a Human authority signal (AI writes use it too).
    permission = request["permission"]
    once.require(set(permission) == {"issue_number", "comment_id", "body_sha256", "record_body", "verbatim", "response_kind", "ticker"}
                 and permission["response_kind"] == "EXPLICIT_RESEARCH_CONTINUE"
                 and permission["ticker"] == child.stock_code
                 and isinstance(permission["verbatim"], str) and permission["verbatim"].strip()
                 and all(type(permission[k]) is int and permission[k] > 0 for k in ("issue_number", "comment_id")),
                 "genuine-response binding missing or not research continuation")
    comment = api._call("GET", "issues/comments/" + str(permission["comment_id"])).json()
    once.require(comment["id"] == permission["comment_id"]
                 and comment["issue_url"] == f"https://api.github.com/repos/{read.REPOSITORY}/issues/{permission['issue_number']}"
                 and isinstance(comment["body"], str) and len(comment["body"].encode()) <= 128 * 1024
                 and comment["body"] == permission["record_body"]
                 and read.sha256(comment["body"].encode()) == permission["body_sha256"]
                 and permission["verbatim"] in comment["body"], "recorded Issue response differs")
    recorded_at = read.clock(comment["created_at"])
    once.require(recorded_at <= read.clock(comment["updated_at"]) <= now,
                 "permission record clocks are invalid or future")
    # The preserved reading is historical exposure, not a current market input.
    exposure = identity._json(load(request["exposed_reading"], exposure_deadline=recorded_at))
    read.validate_read_package(exposure)
    once.require(request["exposed_reading"]["path"] == "current-state.json"
                 and read.clock(exposure["checks"]["finished_at"]) <= recorded_at,
                 "permission precedes its exposed reading")
    items = exposure.get("research", {}).get("candidate_work", {}).get("items", [])
    role = "candidate" if prior["kind"] == "CANDIDATE" else "failure"
    once.require(any(_same(item.get("sources", {}).get(role, {}), prior["result"]) for item in items),
                 "permission did not bind a result in the shown reading")
    # _checked_source already supports a Git-blob-only pinned reference. Normalize
    # from its actual bytes for the ORIGINAL input model; never invent a SHA256.
    def normalized(spec, purpose):
        return once.source_ref(spec["path"], spec["ref"], loaded[(spec["ref"], spec["path"])], purpose)
    sources += [normalized(request["exposed_reading"], "HUMAN_CONTINUATION_EXPOSURE"),
                normalized(prior["result"], "CONTINUATION_PREDECESSOR_RESULT"), request_source]
    if entry is None:
        sources.append(normalized(prior["packet"], "CONTINUATION_PREDECESSOR_PACKET"))
    extra = {} if entry is None else {
        "execution_prefix": work.continuation_prefix(child.assessment_input_hash, permission["comment_id"]),
        "execution_id": f"saved-disclosure-{child.assessment_input_hash}-reading-{permission['comment_id']}",
        "required_reading_pdf_sha256s": entry["required_reading_pdf_sha256s"],
        "source_run_id": envelope["source_run_id"]}
    return {**extra, "question": request["follow_up_question"], "source_refs": sources,
            "permission_receipt": {"comment_id": comment["id"], "issue_url": comment["issue_url"],
                                   "body_sha256": permission["body_sha256"],
                                   "recorded_at": comment["created_at"], "checked_at": checked_at,
                                   "clock_scope": "GitHub retention time, not invented Human message time"},
            "public_context": {"predecessor": public, "new_evidence_reason": request["new_evidence_reason"],
                               "new_body_hashes": sorted(set(changed)),
                               "limit": "Same problem interpretation is trusted Human-interaction judgment, not Kernel truth. Prior AI text is not new primary Evidence."}}
