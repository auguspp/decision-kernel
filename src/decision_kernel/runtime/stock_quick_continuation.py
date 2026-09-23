"""Quick-only mode of the original daily host, at the original frozen cutoff.

Reuse the original executor, source checks, identity scope and create-only Git
retention. No fresh-source claim, new daily slot, Pre call or automatic retry.
"""
from __future__ import annotations

from functools import partial
import re

from ..identity import canonical_hash
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_daily_question as daily
from . import stock_question_continuation as previous
from . import stock_research_intake as intake
from . import reviewed_question_input as reviewed
from . import reviewed_full_input as full
from .external_research_execution import ExternalResearchInputPacket, ExternalResearchCandidate
from .stock_research_host import authorize, head, STOCK_PROMPT_BYTES

MODE = "FROZEN_REVIEWED_QUESTION_QUICK_CONTINUATION"
SOURCE_SCOPE = "ORIGINAL_RESEARCH_CUTOFF_NO_NEW_SOURCES"


def recheck_checkpoint_reviews(context, *, api, code, clock):
    """Read actual retained review notes, not just construct a lazy loader.

    The admitted parent binds the complete representation and original PDF.
    Reuse that checkpoint; compare the same-PDF note inventory and every note
    against current main without re-downloading or re-reading the entire PDF.
    This checks retained interpretation identity, never economic source truth.
    """
    from . import disclosure_source_reading as pages
    full.recheck_pages(context, api=api, code=code, clock=clock)
    trees = {}
    def tree(ref):
        if ref not in trees:
            trees[ref] = previous._tree(api, ref)
        return trees[ref]
    for doc in context['issuer_documents']:
        value = doc.get('page_reading')
        if not full.referenced_reading(value):
            continue
        load = full.replay_loader(api, code, value, clock)
        prefix = pages.REVIEW_ROOT + doc['pdf_sha256'] + '/'
        inventories = [{p: r for p, r in tree(ref).items() if p.startswith(prefix)}
                       for ref in (value['review_commit'], code)]
        before, current = inventories
        once.require(set(before) == set(current), 'QUICK_REVIEW_INVENTORY_CHANGED')
        for path, row in sorted(before.items()):
            match = re.fullmatch(re.escape(prefix) + r'page-([1-9][0-9]*)\.json', path)
            once.require(match is not None and 1 <= int(match[1]) <= doc['page_count']
                and all(r.get('type') == 'blob' and r.get('mode') == '100644'
                        and type(r.get('size')) is int and 0 < r['size'] <= pages.MAX_REVIEW_BYTES
                        and reading.SHA.fullmatch(r.get('sha', ''))
                        for r in (row, current[path]))
                and row['sha'] == current[path]['sha'], 'QUICK_REVIEW_BLOB_CHANGED')
            note, spec = load(doc['pdf_sha256'], int(match[1]))
            once.require(spec['git_blob'] == row['sha']
                and note['pdf_sha256'] == doc['pdf_sha256'] and note['page_number'] == int(match[1]),
                'QUICK_REVIEW_READBACK_DIFFERS')


def check_request(request):
    once.require(set(request) == {"schema_version", "enabled", "mode", "permission",
                                  "predecessor", "source_scope"}
        and request["schema_version"] == 1 and request["enabled"] is True
        and request["mode"] == MODE and request["source_scope"] == SOURCE_SCOPE,
        "QUICK_CONTINUATION_REQUEST_SHAPE")
    pred = request["predecessor"]
    once.require(set(pred) == {"run_id", "work_commit", "sources"}
        and type(pred["run_id"]) is int and pred["run_id"] > 0
        and reading.SHA.fullmatch(pred["work_commit"])
        and set(pred["sources"]) == set(previous.PREDECESSOR_FILES),
        "QUICK_CONTINUATION_PREDECESSOR_SHAPE")


def load_checkpoint(api, code, request, clock):
    """Current permission is separate from reconstruction of the old source check."""
    from .stock_question_host import question_execution
    check_request(request)
    authorize(api, code, request, request_path=daily.REQUEST, mode=MODE)
    pred = request["predecessor"]
    commit, rows = daily.work_tree(api)
    raw, parsed = {}, {}
    for key, (name, purpose) in previous.PREDECESSOR_FILES.items():
        spec = pred["sources"][key]
        once.require(spec["ref"] == pred["work_commit"] and spec["purpose"] == purpose
            and rows.get(spec["path"], {}).get("sha") == spec["git_blob"]
            and rows[spec["path"]]["mode"] == "100644", "QUICK_PARENT_CHANGED")
        raw[key] = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
        parsed[key] = identity._json(raw[key])
    parent = ExternalResearchInputPacket.model_validate(parsed["input"])
    candidate = ExternalResearchCandidate.model_validate(parsed["candidate"])
    launch, host, admitted = (parsed[k] for k in ("launch", "host_receipt", "admission"))
    original_request = identity._json(api.file(daily.REQUEST, parent.code_commit))
    once.require(original_request["mode"] == daily.MODE
        and original_request["question_source"] == launch["question_source"], "QUICK_PARENT_REQUEST_DIFFERS")
    qspec = original_request["question_source"]
    once.require(all(original_request[k] in [s.model_dump(mode="json") for s in parent.source_refs]
                     for k in ("question_source", "context_source", "preflight_source",
                               "batch_review_source", "source_custody_source"))
        and launch["permission"] == original_request["permission"], "QUICK_PARENT_REQUEST_SOURCES")
    q = reviewed._declaration(identity._checked_source(qspec, lambda s: api.file(s["path"], s["ref"])))
    parent_id, root = question_execution(q["security_id"], q["question_id"])
    once.require(parent.execution_id == parent_id and parent.candidate_output_prefix == root
        and parent.source_lane == reviewed.LANE and parent.research_question == q["question"]
        and parent.security_id == q["security_id"] and parent.ticker == q["ticker"]
        and parent.case_id == q["case_id"]
        and all(pred["sources"][key]["path"] == root + name
                for key, (name, _) in previous.PREDECESSOR_FILES.items()), "QUICK_PARENT_QUESTION_DIFFERS")
    checked = once.validate_external_research_candidate(packet=parent, candidate=candidate)
    once.require(parsed["validation"] == checked.model_dump(mode="json")
        and parsed["receipt"] == candidate.receipt.model_dump(mode="json")
        and host["execution_id"] == launch["id"] == parent_id
        and host["code_commit"] == launch["code_commit"] == parent.code_commit
        and launch["input_hash"] == canonical_hash(parent)
        and host["candidate_hash"] == canonical_hash(candidate)
        and host["validation_hash"] == canonical_hash(checked)
        and host["status"] == "EXECUTION_GAP" and host["formal_research_started"] is True
        and host["mutation_uncertain"] is False and host["automatic_retry"] is False
        and host["registered_current_handoff"] is False
        and admitted["research_execution_allowed"] is True
        and admitted["execution_key"] == identity.input_key(parent).as_dict()
        and identity._checked_source(admitted["input_source"], lambda s: api.file(s["path"], s["ref"])) == raw["input"],
        "QUICK_PARENT_RECEIPTS_DIFFER")
    usage = host["provider_usage"]
    once.require(len(usage) == 2 and [u["stage"] for u in usage] == ["pre", "quick"]
        and all(u["provider"] == previous.PROVIDER and u["provider_status"] == "completed" for u in usage)
        and usage[0]["phase"] == "COMPLETE"
        and usage[1]["phase"] == "APPLICATION_VALIDATION"
        and usage[1]["application_validation"]["status"] == "REJECTED_BY_ORIGINAL_MODEL"
        and usage[1]["output_text_retained"] is True, "QUICK_PARENT_NOT_RETURNED_VALIDATION_FAILURE")
    run = api.get("actions/runs/" + str(pred["run_id"]))
    once.require(run["id"] == pred["run_id"] and run["head_sha"] == parent.code_commit
        and run["path"] == ".github/workflows/stock-business-research.yml"
        and run["head_branch"] == "main" and run["run_attempt"] == 1
        and run["event"] in {"issues", "workflow_dispatch"}
        and run["repository"]["full_name"] == run["head_repository"]["full_name"] == once.REPO
        and run["status"] == "completed" and run["conclusion"] == "failure"
        and candidate.receipt.platform_task_id == str(run["id"])
        and admission.clock(run["updated_at"]) <= admission.clock(clock()), "QUICK_PARENT_RUN_DIFFERS")
    proofs = [{**pred["sources"][key], "purpose": "QUICK_RESUME_PARENT_" + key.upper()}
              for key in ("input", "candidate")]
    checkpoint = once.QuickCheckpoint(raw["input"], raw["candidate"], *(once.raw(s) for s in proofs))
    values = parent.model_dump(mode="json")
    packet = ExternalResearchInputPacket.model_validate({**values,
        "execution_id": parent_id + "-technical-continuation-v1", "code_commit": code,
        "candidate_output_prefix": root + previous.CHILD,
        "source_refs": values["source_refs"] + proofs,
        "budget": {**values["budget"], "max_technical_retries": 1}})
    checkpoint.restore(packet, candidate.discovery)
    spec = original_request["context_source"]
    once.require(spec in values["source_refs"] and original_request["preflight_source"] in values["source_refs"],
                 "QUICK_PARENT_SOURCE_BINDING")
    context, bound = full.load_context(spec, lambda s: api.file(s["path"], s["ref"]),
                                      ticker=parent.ticker, allowed=True)
    if bound is not None:
        bound.check_packet(packet, context)
        recheck_checkpoint_reviews(context, api=api, code=code, clock=clock)
    else:
        once.require(once.sha(once.raw(context)) == spec["sha256"], "QUICK_CONTEXT_CHANGED")
    from .stock_question_host import _question_context
    pf = identity._json(identity._checked_source(original_request["preflight_source"],
        lambda s: api.file(s["path"], s["ref"])))
    _question_context(context, packet, pf)
    return packet, candidate.discovery, context, bound, checkpoint, q, original_request, commit, rows


def assess(api, code, packet, request, original_request, clock, *, input_source=None):
    """Original source checks at frozen cutoff plus CURRENT input/authority checks.

    This deliberately does not call an expired preflight a current check. The
    exact checkpoint/run has been verified by load_checkpoint before this call.
    It is only used by this fixed Quick continuation, never ordinary admission.
    """
    check_request(request)
    now = clock()
    authorize(api, code, request, request_path=daily.REQUEST, mode=MODE)
    pf = identity._checked_source(original_request["preflight_source"], lambda s: api.file(s["path"], s["ref"]))
    original_at = packet.research_cutoff.isoformat()
    catalog_raw = api.file(identity.CATALOG_PATH, code)
    catalog_spec = once.source_ref(identity.CATALOG_PATH, code, catalog_raw, "CURRENT_CODE_EXECUTION_SCOPE")
    _, key, catalog_raw = admission.prepare_input(input_raw=once.raw(packet), preflight_raw=pf,
        catalog_source=catalog_spec, load=lambda s: api.file(s["path"], s["ref"]),
        commit=lambda ref: api.get("git/commits/" + ref), checked_at=original_at,
        current_code=lambda: head(api, "main"))
    once.require(admission.clock(original_at) <= admission.clock(now), "QUICK_CLOCK_REVERSED")
    report = {"status": "NOT_EXECUTED", "checked_at": now, "source_checked_at": original_at,
        "source_freshness": "ORIGINAL_CUTOFF_NOT_CURRENT_PREFLIGHT", "execution_key": key.as_dict(),
        "research_execution_allowed": False, "input_file_sha256": once.sha(once.raw(packet)),
        "reason": "QUICK_INPUT_READY_NOT_EXECUTED", **reading.AUTHORITY}
    if input_source is None:
        return report
    once.require(input_source["path"] == packet.candidate_output_prefix + "input.json"
        and identity._checked_source(input_source, lambda s: api.file(s["path"], s["ref"])) == once.raw(packet),
        "QUICK_INPUT_READBACK_DIFFERS")
    meta = api.get("git/commits/" + input_source["ref"])
    once.require(meta["sha"] == input_source["ref"]
        and packet.research_cutoff <= admission.clock(meta["committer"]["date"]) <= admission.clock(now),
        "QUICK_INPUT_COMMIT_CLOCK")
    catalog = identity._json(catalog_raw)
    catalog["inputs"].append({**key.as_dict(), "input": input_source})
    scope = identity.load_execution_scope(once.raw(catalog), lambda s: api.file(s["path"], s["ref"]))
    scope.require_unambiguous(key)
    once.require(head(api, "main") == code, "QUICK_MAIN_MOVED")
    report.update(reason="FROZEN_QUICK_CONTINUATION_ALLOWED", research_execution_allowed=True,
                  input_source=input_source, identity_scope_hash=scope.scope_hash)
    return report


def run(*, api, code, output, call=None, clock=once.now):
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 "QUICK_UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "NOT_EXECUTED", "phase": "AUTHORIZATION", "code_commit": code,
        "started_at": clock(), "formal_research_started": False, "automatic_retry": False,
        "registered_current_handoff": False, "semantic_acceptance": "NOT_ESTABLISHED",
        "pre_model_calls": 0, **reading.AUTHORITY}
    retain, reserved = None, False
    try:
        request = identity._json(api.file(daily.REQUEST, code))
        prepared = load_checkpoint(api, code, request, clock)
        packet, discovery, context, bound, checkpoint, q, original, work, rows = prepared
        result.update(execution_id=packet.execution_id, thscode=packet.case_id,
                      question_id=q["question_id"], revision=q["revision"], quick_resume=checkpoint.record())
        if any(p.startswith(packet.candidate_output_prefix) for p in rows):
            result.update(status="EXISTING_QUESTION_REUSED_NO_EXECUTION", phase="EXISTING_CHILD")
            return result
        state = identity._json(api.file(q["reading_source"]["path"], q["reading_source"]["ref"]))
        daily.capacity(api, work, rows, state, packet)
        assess(api, code, packet, request, original, clock)
        if bound is not None:
            # A local SDK envelope preview is not a Pre model invocation.
            bound = bound.preview(packet, discovery, context)
        prompt = once.pre_prompt(packet, discovery, context)
        rec = checkpoint.record()
        prompt.update(stage="QUICK", pre_research=checkpoint.restore(packet, discovery).model_dump(mode="json"),
            pre_research_hash=rec["pre_research_hash"],
            continuation_scope={k: rec[k] for k in ("mode", "research_cutoff", "pre_model_calls", "source_freshness")})
        if bound is None:
            previous._deepseek_request(prompt, once.QuickResearchResult)
        else:
            full._parameters(prompt, once.QuickResearchResult)
        retain = once.Retainer(api, {"prefix": packet.candidate_output_prefix,
            "id": packet.execution_id, "work_ref": intake.WORK_REF}, code, output)
        retain.save("prepare.json", {"status": "QUESTION_INPUT_PREPARED_NOT_EXECUTED",
            "question_id": q["question_id"], "revision": q["revision"], "question_source": original["question_source"],
            "execution_key": identity.input_key(packet).as_dict(), "input_file_sha256": once.sha(once.raw(packet)),
            "research_execution_allowed": False, "funnel_invoked": False, "quick_resume": rec})
        reserved = True
        ins = retain.save("input.json", packet)
        admitted = assess(api, code, packet, request, original, clock, input_source=ins)
        launch = retain.save("launch.json", {"id": packet.execution_id, "input_hash": canonical_hash(packet),
            "code_commit": code, "question_source": original["question_source"], "permission": request["permission"],
            "automatic_retry": False, "quick_resume": rec,
            "predecessor": {"execution_id": rec["parent_execution_id"], "sources": request["predecessor"]["sources"]}})
        calls = 0
        def guarded(stage, actual, model, out, usage):
            nonlocal calls
            once.require(calls == 0 and stage == "quick" and model is once.QuickResearchResult
                         and actual == prompt, "QUICK_ONLY_MODEL_BOUNDARY")
            again = load_checkpoint(api, code, request, clock)
            once.require(once.raw(again[0]) == once.raw(packet) and again[4] == checkpoint,
                         "QUICK_CHECKPOINT_CHANGED_BEFORE_SEND")
            once.require(all(again[8].get(s["path"], {}).get("sha") == s["git_blob"]
                             for s in retain.writes), "QUICK_CHILD_CHANGED_BEFORE_SEND")
            assess(api, code, packet, request, original, clock, input_source=ins)
            identity._checked_source(launch, lambda s: api.file(s["path"], s["ref"]))
            calls += 1
            invoke = call or partial(once.model_call,
                **({"max_prompt_bytes": STOCK_PROMPT_BYTES} if bound is None else {"bound_context": bound}),
                base_url=once.DEEPSEEK_BASE_URL, model=once.DEEPSEEK_MODEL,
                api_key_env="DEEPSEEK_API_KEY", provider=previous.PROVIDER,
                extra_parameters={"reasoning": previous.REASONING})
            return invoke(stage, actual, model, out, usage)
        result.update(phase="RESEARCH", formal_research_started=True)
        candidate, validation, usage = once.research(packet, discovery, context, output,
            call=guarded, clock=clock, bound_context=bound, quick_checkpoint=checkpoint,
            provider_event_prefix=previous.PROVIDER_EVENT_PREFIX, model_or_executor=previous.MODEL_OR_EXECUTOR)
        retain.save("admission.json", admitted)
        retain.save("candidate.json", candidate)
        retain.save("receipt.json", candidate.receipt)
        retain.save("validation.json", validation)
        if validation.funnel_result is not None:
            retain.save("funnel.json", validation.funnel_result)
        result.update(status=validation.status.value, phase="COMPLETE", provider_usage=usage,
            quick_model_attempts=calls, candidate_hash=canonical_hash(candidate), validation_hash=canonical_hash(validation))
        retain.save("README.md", ("# 已冻结问题的 Quick 接续\n\n" + q["question"] +
            "\n\n复用原有效 Pre；本次只调用 Quick。原截止时点及失败保留，不是最新资料检查、Human 接受或投资决定。\n").encode())
    except Exception as exc:
        result.update(status="EXECUTION_INCOMPLETE" if result["formal_research_started"] else "NOT_EXECUTED",
                      error_type=type(exc).__name__)
        reason = getattr(exc, "code", None)
        if isinstance(reason, str) and re.fullmatch(r"[A-Z0-9_]{1,128}", reason):
            result["error_code"] = reason
    finally:
        result.update(finished_at=clock(), mutation_uncertain=bool(retain and retain.uncertain))
        if reserved and not result["mutation_uncertain"]:
            try:
                retain.save("host-receipt.json", result)
            except Exception:
                result.update(status="RETENTION_INCOMPLETE", mutation_uncertain=retain.uncertain)
                with (output / "host-retention-failure.json").open("xb") as f: f.write(once.raw(result))
        else:
            with (output / "host-receipt-local.json").open("xb") as f: f.write(once.raw(result))
    return result
