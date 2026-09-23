"""Resume the retained-context checkpoint of the existing source-only job.

No retry loop, source acquisition, research reservation or alternate writer.
The explicit main plan and immutable predecessor bytes define this one re-entry.
"""
from __future__ import annotations

import re

from . import saved_research_once as once, current_state as reading
from . import external_research_identity as identity, stock_daily_question as daily
from . import stock_retained_source_import as imports, reviewed_full_input as full

KIND = "SINGLE_RETAINED_CONTEXT_ORIGIN_REPAIR"
MARKER = "origin-continuation.json"


def shape(plan):
    from .industry_question_preparation import PREFIX
    value = plan["resume_from"]
    once.require(isinstance(value, dict) and set(value) == {
        "kind", "run", "artifact", "prepare_source", "continuation_source", "context_source", "receipt_sha256"}
        and value["kind"] == KIND, "INDUSTRY_CONTEXT_REENTRY_SHAPE")
    run, artifact = value["run"], value["artifact"]
    once.require(set(run) == {"id", "path", "head_branch", "head_sha", "event"}
        and type(run["id"]) is int and run["id"] > 0 and reading.SHA.fullmatch(run["head_sha"])
        and run["path"] == ".github/workflows/stock-business-research.yml"
        and run["head_branch"] == "main" and run["event"] == "issues"
        and set(artifact) == {"id", "name", "size_in_bytes", "digest", "head_sha"}
        and type(artifact["id"]) is int and artifact["id"] > 0
        and type(artifact["size_in_bytes"]) is int and 0 < artifact["size_in_bytes"] <= full.LIMITS["stored_bytes"] + 128 * 1024
        and artifact["head_sha"] == run["head_sha"]
        and artifact["name"] == f"declared-report-sources-{run['id']}-1"
        and re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["digest"])
        and re.fullmatch(r"[0-9a-f]{64}", value["receipt_sha256"]), "INDUSTRY_CONTEXT_REENTRY_IDENTITY")
    for key, name, purpose in (("prepare_source", "prepare.json", "ORIGINAL_FAILED_INPUT_PREPARATION"),
        ("continuation_source", "continuation.json", "EXPLICIT_INPUT_PREPARATION_CONTINUATION"),
        ("context_source", "context.json", "MODEL_CONTEXT")):
        spec = value[key]
        once.require(spec["path"] == PREFIX + plan["id"] + "/" + name and spec["purpose"] == purpose,
                     "INDUSTRY_CONTEXT_REENTRY_PATH")
    return value


def check(api, plan, work, tree, clock):
    from .industry_question_preparation import PREFIX, REQUEST
    value = shape(plan)
    prefix = PREFIX + plan["id"] + "/"
    specs = {key: value[key] for key in ("prepare_source", "continuation_source", "context_source")}
    once.require({p for p in tree if p.startswith(prefix)} == {s["path"] for s in specs.values()},
                 "INDUSTRY_CONTEXT_REENTRY_HAS_LATER_OUTPUT")
    run, files = imports._archive(api, value, {}, expected_conclusion="failure")
    once.require(set(files) == {"continuation.json", "context.json", "preparation-receipt.json"}
        and once.sha(files["preparation-receipt.json"]) == value["receipt_sha256"],
        "INDUSTRY_CONTEXT_REENTRY_FAILURE_BYTES")
    raw, clocks = {}, {}
    for key, spec in specs.items():
        data, saved_at = daily._source(api, spec, spec["purpose"], clock)
        row = tree[spec["path"]]
        once.require(data == api.file(spec["path"], work) and row.get("sha") == once.blob(data)
            and row.get("size") == len(data) and row.get("mode") == "100644" and row.get("type") == "blob",
            "INDUSTRY_CONTEXT_REENTRY_SAVED_BYTES")
        raw[key], clocks[key] = data, reading.clock(saved_at)
    once.require(raw["context_source"] == files["context.json"]
        and raw["continuation_source"] == files["continuation.json"], "INDUSTRY_CONTEXT_REENTRY_ARCHIVE_DIFFERS")
    prepared = identity._json(raw["prepare_source"])
    continuation = identity._json(raw["continuation_source"])
    failed = identity._json(files["preparation-receipt.json"])
    prior_plan = identity._json(api.file(REQUEST, run["head_sha"]))
    base = lambda p: {k: v for k, v in p.items() if k != "resume_from"}
    once.require(once.raw(continuation["plan"]) == once.raw(prior_plan)
        and once.raw(base(plan)) == once.raw(base(prior_plan)) == once.raw(prepared["plan"])
        and continuation["proof"]["parent"] == prior_plan["resume_from"]
        and prior_plan["resume_from"]["prepare_source"] == value["prepare_source"]
        and continuation["code_commit"] == failed["code_commit"] == run["head_sha"]
        and continuation["run_id"] == str(run["id"]) and continuation["event"] == run["event"]
        and continuation["automatic_retry"] is False and failed["continuation_source"] == value["continuation_source"]
        and failed["status"] == "PREPARATION_INCOMPLETE" and failed["error_type"] == "TrialError"
        and failed["error_code"] == "INDUSTRY_REPORT_SIZE" and failed["mutation_uncertain"] is False
        and failed["query_events"] == []
        and all(type(failed[k]) is int and failed[k] == 0 for k in ("model_calls", "research_executions", "pdf_acquisitions"))
        and all(all(v.get(k) == expected for k, expected in reading.AUTHORITY.items())
                for v in (prepared, continuation, failed)), "INDUSTRY_CONTEXT_REENTRY_NOT_MATCHED_FAILURE")
    once.require(set(failed) == {"status", "code_commit", "started_at", "finished_at", "model_calls",
        "research_executions", "pdf_acquisitions", "query_events", "mutation_uncertain", "error_type", "error_code",
        "context_bytes", "stored_context_bytes", "continuation_source", *reading.AUTHORITY}
        and type(failed["context_bytes"]) is int and type(failed["stored_context_bytes"]) is int,
        "INDUSTRY_CONTEXT_REENTRY_FAILURE_SHAPE")
    # Reuse the exact compressed/plain context; neither its review refs nor clocks change.
    context, bound = full.load_context(value["context_source"], lambda _: raw["context_source"],
                                      ticker=identity._json(raw["context_source"])["ticker"], allowed=True)
    once.require(bound is not None and len(bound.decoded_raw) == failed["context_bytes"]
        and len(raw["context_source"]) == failed["stored_context_bytes"], "INDUSTRY_CONTEXT_REENTRY_CONTEXT_SIZE")
    once.require(reading.clock(run["run_started_at"]) <= reading.clock(failed["started_at"])
        <= reading.clock(continuation["started_at"]) <= clocks["continuation_source"]
        <= clocks["context_source"] <= reading.clock(failed["finished_at"])
        <= reading.clock(run["updated_at"]) <= reading.clock(clock())
        and clocks["prepare_source"] <= clocks["continuation_source"], "INDUSTRY_CONTEXT_REENTRY_CLOCK")
    return {"parent": value, "failure_receipt": failed, "checked_at": clock()}


def retained_context(api, plan, profile, records, clock):
    """Reuse saved text; the original daily custody later replays every PDF/page."""
    spec = plan["resume_from"]["context_source"]
    context, bound = full.load_context(spec, lambda s: daily._source(api, s, "MODEL_CONTEXT", clock)[0],
                                      ticker=profile["case_id"][:6], allowed=True)
    once.require(bound is not None, "INDUSTRY_CONTEXT_REENTRY_COMPLETE_CONTEXT_REQUIRED")
    docs = context["issuer_documents"]
    once.require(len(docs) == len(records), "INDUSTRY_CONTEXT_REENTRY_DOCUMENTS")
    custody = []
    for doc, source in zip(docs, records, strict=True):
        route, report = source["route"], source["report"]
        once.require(doc["announcement_id"] == source["announcement_id"]
            and doc["title"] == plan["titles"][report["period"]]
            and doc["source_locator"] == route["locator"] and doc["pdf_sha256"] == route["pdf_sha256"]
            and doc["page_count"] == route["page_count"], "INDUSTRY_CONTEXT_REENTRY_DOCUMENTS")
        custody.append({"announcement_id": doc["announcement_id"], "bytes": route["bytes"],
            "pdf_sha256": route["pdf_sha256"], "page_count": route["page_count"],
            "pdf_source": {**{k: v for k, v in route["pdf_source"].items() if k != "bytes"},
                           "purpose": "RETAINED_PUBLIC_ISSUER_PDF"}})
    return context, custody, spec, bound
