"""Explicit question mode of the existing Stock workflow; no new executor.

Reuse the original Stock authorization/work ref, #453 prepare, launch-time
admission, saved Pre/conditional Quick and create-only Retainer. Disabled by
default. No source acquisition, automatic routing or investment authority.
"""
from __future__ import annotations

import argparse
from functools import partial
import os
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5

from ..evidence import EvidenceArtifact
from ..identity import canonical_hash
from ..research_funnel import DiscoveryInput
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_research_sources as sources
from . import single_quick_contract as single
from .current_state_delivery import GitHubReadError
from .pinned_reading_file import GitHubAPI
from .external_research_execution import ExternalResearchInputPacket
from .stock_research_host import authorize, head, STOCK_PROMPT_BYTES

# Question-scoped opt-in uses the same native work ref and one-shot executor.
QUESTION_REQUEST = "research_runs/stock-question-request.json"
QUESTION_MODE = "REVIEWED_RADAR_QUESTION"
QUESTION_BUDGET = {"max_tool_calls": 6, "max_search_queries": 0, "max_source_reads": 4,
    "max_technical_retries": 0, "max_elapsed_minutes": 15,
    **{k + "_enforcement": "SOFT_EXECUTOR" for k in
       ("tool_calls", "search_queries", "source_reads", "technical_retries", "elapsed_time")}}


def selected_method(request):
    """Explicit trusted-request selection, never inherited from an old approval."""
    if "research_method" not in request:
        once.require("method_permission" not in request, "QUESTION_METHOD_PERMISSION_WITHOUT_METHOD")
        return "research-funnel-v1"
    once.require(request["research_method"] == single.METHOD_VERSION
                 and isinstance(request.get("method_permission"), dict)
                 and set(request["method_permission"]) == {"comment_id", "body_sha256", "created_at"}
                 and request["method_permission"] != request["permission"], "QUESTION_NEW_METHOD_PERMISSION_REQUIRED")
    return single.METHOD_VERSION


def single_egress_hash(packet, discovery, context, *, daily=False, bound=None):
    """Same prepared inputs, explicit one-call contract; digest is not permission."""
    if bound is not None:
        return bound.egress_hash(packet, discovery, context)
    prompt = once.initial_prompt(packet, discovery, context)
    prompt["binding"]["as_of"] = "HOST_ASSIGNED_RESEARCH_CUTOFF"
    return canonical_hash({"prompt": prompt,
        "source_refs": [s.model_dump(mode="json") for s in packet.source_refs],
        "budget": packet.budget, "system_sha256": once.sha(once.SYSTEM.encode()),
        "model": once.DEEPSEEK_MODEL if daily else once.MODEL,
        "endpoint": once.DEEPSEEK_BASE_URL if daily else once.BASE_URL,
        "reasoning": {"effort": "none"} if daily else None,
        "max_output_tokens": once.MAX_OUTPUT_TOKENS, "max_prompt_bytes": STOCK_PROMPT_BYTES,
        "output_schema": single.QuickAssessment.model_json_schema()})


def question_execution(security_id, question_id):
    """A revision, run or execution rename must not create another spending root."""
    key = canonical_hash({"security_id": security_id, "question_id": question_id})
    return "stock-question-" + key, "research_runs/candidates/stock-questions/" + key + "/"


def question_egress_hash(packet, discovery, context):
    """Digest for independent review, never approval by this helper.

    Only the host's new cutoff is normalized; all actual public text, Evidence
    IDs, source references, budget and the existing model policy remain bound.
    No self-referential future main SHA or presigned stale execution token.
    """
    prompt = once.pre_prompt(packet, discovery, context)
    prompt["binding"]["as_of"] = "HOST_ASSIGNED_RESEARCH_CUTOFF"
    return canonical_hash({"pre_prompt": prompt,
        "source_refs": [s.model_dump(mode="json") for s in packet.source_refs],
        "budget": packet.budget, "system_sha256": once.sha(once.SYSTEM.encode()),
        "model": once.MODEL, "endpoint": once.BASE_URL, "max_output_tokens": once.MAX_OUTPUT_TOKENS,
        "max_prompt_bytes": STOCK_PROMPT_BYTES,
        "output_schemas": [once.PreResearchResult.model_json_schema(), once.QuickResearchResult.model_json_schema()],
        "quick": "ONLY_ORIGINAL_VALIDATED_PRE_AND_ITS_HASH_ADDED_IF_CONTINUE_TO_QUICK"})


def _question_context(context, packet, preflight):
    """Match the existing document/page representation to required body receipts.

    Does not fetch a PDF or certify collector assertions/extracted text as truth.
    Context source bytes are independently bound and approved before this check.
    """
    from .disclosure_source_reading import text_ok
    docs = admission.items(context.get("issuer_documents"))
    once.require(admission.text(context.get("source_limitations")), "QUESTION_CONTEXT_SCOPE_MISSING")
    reads = {r["identity"]: r for r in preflight["reads"]
             if r["kind"] == "BODY" and r["authority"] == "PRIMARY" and r["succeeded"]}
    once.require(len(reads) == sum(r["kind"] == "BODY" and r["authority"] == "PRIMARY"
                                 and r["succeeded"] for r in preflight["reads"]), "QUESTION_BODY_AMBIGUOUS")
    seen = set()
    for doc in docs:
        rid = packet.ticker + ":" + doc["announcement_id"]
        once.require(rid in reads and rid not in seen, "QUESTION_CONTEXT_BODY_MISMATCH")
        seen.add(rid)
        r = reads[rid]
        once.require(doc["source_locator"] == r["locator"] and doc["pdf_sha256"] == r["body_sha256"]
                     and admission.text(doc["title"]), "QUESTION_CONTEXT_BODY_MISMATCH")
        once.require(admission.clock(doc["published_at"]) <= admission.clock(doc["retrieved_at"])
                     <= admission.clock(r["checked_at"]), "QUESTION_BODY_CLOCK_MISMATCH")
        pages, count = doc["pages"], doc["page_count"]
        once.require(type(count) is int and 0 < count <= 500 and isinstance(pages, list)
                     and len(pages) == count and [p["page_number"] for p in pages] == list(range(1, count + 1))
                     and all(type(p["page_number"]) is int and text_ok(p["text"]) for p in pages),
                     "QUESTION_REQUIRED_PAGES_UNREADABLE_OR_INCOMPLETE")
        once.require(doc["reading_method"] in {"ORIGINAL_PYPDF", "BOUND_SAME_PDF_READING"}
                     and (doc.get("page_reading") is None) == (doc["reading_method"] == "ORIGINAL_PYPDF"),
                     "QUESTION_REPRESENTATION_UNSUPPORTED")
    once.require(seen == set(reads), "QUESTION_REQUIRED_BODIES_NOT_ALL_SUPPLIED")


def _question_inputs(*, api, code, request, clock, allow_full=False):
    """Construct a NEW input from declared sources, not rewrite a frozen packet.

    Like the original Stock host, code and selection clocks are bound at runtime.
    Question, preflight, primary context and public-egress approval are pre-saved.
    """
    from . import reviewed_question_input as reviewed
    method = selected_method(request)
    extra = {"research_method", "method_permission"} if method == single.METHOD_VERSION else set()
    once.require(set(request) == {"schema_version", "enabled", "mode", "permission",
        "question_source", "context_source", "preflight_source", "approved_egress_hash", *extra},
        "QUESTION_REQUEST_SHAPE")
    load = lambda s: api.file(s["path"], s["ref"])
    qs, cs, ps = (request[k] for k in ("question_source", "context_source", "preflight_source"))
    once.require(qs["purpose"] == reviewed.PURPOSE and cs["purpose"] == "MODEL_CONTEXT"
                 and ps["purpose"] == admission.PREFLIGHT_PURPOSE, "QUESTION_SOURCE_PURPOSE_MISMATCH")
    q = reviewed._declaration(identity._checked_source(qs, load))
    once.require(q["security_id"] == intake.security(q["case_id"])
                 and q["ticker"] == q["case_id"][:6], "QUESTION_SECURITY_MISMATCH")
    context_raw = identity._checked_source(cs, load)
    from . import reviewed_full_input as full_input
    from . import industry_daily_question as industry
    context, bound = full_input.load_context(cs, lambda _: context_raw, ticker=q["ticker"],
        allowed=allow_full is True and request["permission"] == industry.PERMISSION)
    if bound is None:
        once.require(once.raw(context) == context_raw and len(context_raw) <= sources.CONTEXT_BYTES,
                     "QUESTION_CONTEXT_REPRESENTATION_OR_SIZE")
    pf_raw = identity._checked_source(ps, load)
    pf = admission.check_preflight(pf_raw, checked_at=clock())
    rs = q["reading_source"]
    state = identity._json(identity._checked_source(rs, load))
    reading.validate_read_package(state)
    eid, prefix = question_execution(q["security_id"], q["question_id"])
    meta = api.get("git/commits/" + cs["ref"])
    once.require(meta["sha"] == cs["ref"], "QUESTION_CONTEXT_COMMIT_MISMATCH")
    selected = clock()
    seed = EvidenceArtifact(id=uuid5(NAMESPACE_URL, eid + ":" + cs["sha256"]),
        source_type="SAVED_RESEARCH_OBSERVATION", source_identifier=eid,
        source_locator=once.locator(cs), published_at=meta["committer"]["date"],
        available_at=selected, retrieved_at=selected, content_hash=cs["sha256"],
        idempotency_key=eid + ":" + cs["sha256"], retention_mode="FULL_ARTIFACT",
        replayability_level="PARTIAL", raw_storage_ref=once.locator(cs),
        license_terms_note="Approved retained public question context; primary-read declarations are not truth certification.")
    refs = []
    for spec in [qs, cs, ps, rs, *[o["source"] for o in q["origins"]],
                 *q["existing_research_relation"]["source_refs"],
                 *([q["predecessor"]] if q["predecessor"] else [])]:
        if spec not in refs:
            refs.append(spec)
    packet = ExternalResearchInputPacket(execution_id=eid, case_id=q["case_id"],
        ticker=q["ticker"], security_id=q["security_id"], source_lane=reviewed.LANE,
        selected_at=selected, research_cutoff=selected, code_commit=code,
        current_state_commit=rs["ref"], current_state_reading_hash=state["reading_hash"],
        source_refs=refs, seed_evidence_artifacts=[seed], research_question=q["question"],
        known_unknowns=list(dict.fromkeys([*q["known_unknowns"],
            *[f"REQUIRED_SOURCE_CLASS:{c['id']}:{c['mode']}" for c in q["required_classes"]],
            "FALSIFICATION_TEST:" + q["falsification_test"],
            *["KNOWN_COUNTEREVIDENCE:" + x for x in q["known_counterevidence"]],
            "EXISTING_RESEARCH_RELATION:" + q["existing_research_relation"]["note"]])),
        next_discriminating_search=q["next_discriminating_search"],
        method_version=method, prompt_version=(single.PROMPT_VERSION if method == single.METHOD_VERSION else "reviewed-question-stock-v0"),
        allowed_tools=["OTHER_READ"], candidate_output_prefix=prefix, budget=QUESTION_BUDGET)
    _question_context(context, packet, pf)
    discovery = DiscoveryInput(discovery_id=eid, source_lane=packet.source_lane,
        ticker=packet.ticker, security_id=packet.security_id, as_of=packet.research_cutoff,
        economic_direction="已声明的有限经济问题，方向未定；不从来路标签或价格推断受益。",
        factual_observations=[{"statement": "已保存的公开正文用于核验这个问题；原件与表示的范围限制仍保留。",
                               "evidence_artifact_ids": [seed.id]}],
        source_lineage=[{"evidence_artifact_id": seed.id, "source_locator": seed.source_locator,
                         "available_at": seed.available_at}], why_now=q["why_now"],
        contradiction_or_mapping_warning=q["falsification_test"],
        next_discriminating_search=packet.next_discriminating_search,
        known_stop_or_downgrade_condition="必要正文或技术失败不得称业务WAIT；不强制Quick、Deep或投资决定。")
    catalog = api.file(identity.CATALOG_PATH, code)
    checks = dict(input_raw=once.raw(packet), preflight_raw=pf_raw,
        catalog_source=once.source_ref(identity.CATALOG_PATH, code, catalog, "CURRENT_CODE_EXECUTION_SCOPE"),
        load=load, commit=lambda ref: api.get("git/commits/" + ref),
        current_code=lambda: head(api, "main"))
    return q, packet, discovery, context, checks


def run_question(*, api, code, output, clock=once.now, call=None, daily=False):
    """Explicit native host only: original prepare -> admission -> Pre/Quick.

    Default request is disabled. No acquisition, question selection or authority
    inferred from data; call substitutes only the model boundary in offline tests.
    """
    from . import reviewed_question_input as reviewed
    once.require(type(daily) is bool, "QUESTION_MODE_INVALID")
    if daily:
        from . import stock_daily_question as daily_policy
        from . import stock_question_continuation as deepseek
    request_path = daily_policy.REQUEST if daily else QUESTION_REQUEST
    mode = daily_policy.MODE if daily else QUESTION_MODE
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "QUESTION_UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "NOT_EXECUTED", "question_kind": mode, "code_commit": code,
        "started_at": clock(), "phase": "AUTHORIZATION", "formal_research_started": False,
        "automatic_retry": False, "registered_current_handoff": False,
        "semantic_acceptance": "NOT_ESTABLISHED", **reading.AUTHORITY}
    retain = None
    daily_retainers, daily_reservations = [], []
    daily_archives = {}
    daily_scope, egress = None, None
    bound = None
    reserved = False
    is_single = False
    try:
        request = identity._json(api.file(request_path, code))
        authorize(api, code, request, request_path=request_path, mode=mode)
        is_single = selected_method(request) == single.METHOD_VERSION
        if is_single:
            authorize(api, code, request, request_path=request_path, mode=mode, permission_key="method_permission")
        if daily:
            daily_policy.check_policy(api, code, request, clock)
        q, packet, discovery, context, checks = _question_inputs(api=api, code=code,
            request=daily_policy.base_request(request) if daily else request, clock=clock, allow_full=daily)
        if daily:
            from . import reviewed_full_input as full_input, industry_daily_question as industry
            decoded, bound = full_input.load_context(request["context_source"], checks["load"],
                ticker=packet.ticker, allowed=request["permission"] == industry.PERMISSION)
            once.require(decoded == context, "FULL_QUESTION_CONTEXT_CHANGED")
        base_packet = packet
        if daily:
            packet, daily_state, daily_scope = daily_policy.bind(api, request, q, packet, context, clock,
                                                               archives=daily_archives)
            daily_scope.update(execution_id=packet.execution_id, question_source=request["question_source"])
            checks = {**checks, "input_raw": once.raw(packet)}
            result["daily_scope"] = daily_scope
        result.update(question_id=q["question_id"], revision=q["revision"], thscode=packet.case_id,
                      execution_id=packet.execution_id, phase="INPUT_PREPARATION")
        def recheck():
            nonlocal egress
            authorize(api, code, request, request_path=request_path, mode=mode)
            if is_single:
                once.require(selected_method(request) == single.METHOD_VERSION, "QUESTION_METHOD_CHANGED")
                authorize(api, code, request, request_path=request_path, mode=mode, permission_key="method_permission")
            if daily:
                daily_policy.check_policy(api, code, request, clock)
                rebound, state, scope = daily_policy.bind(api, request, q, base_packet, context, clock,
                                                         archives=daily_archives)
                scope.update(execution_id=packet.execution_id, question_source=request["question_source"])
                once.require(once.raw(rebound) == checks["input_raw"] and scope == daily_scope,
                             "DAILY_BOUND_SCOPE_CHANGED")
                if daily_reservations:
                    current, rows = daily_policy.work_tree(api)
                    daily_policy.capacity(api, current, rows, state, packet)
                    daily_policy.reservation_plan(api, current, rows, scope, reserved=True)
                    for source in daily_reservations:
                        exact = identity._checked_source(source, checks["load"])
                        once.require(api.file(source["path"], current) == exact, "DAILY_RESERVATION_CHANGED")
            prepared = reviewed.prepare(question_source=request["question_source"], checked_at=clock(), **checks)
            if bound is None:
                once.require(identity._checked_source(request["context_source"], checks["load"]) == once.raw(context),
                             "QUESTION_CONTEXT_CHANGED_BEFORE_EGRESS")
                sources.recheck(context, api=api, code_commit=code, clock=clock)
            else:
                bound.recheck(checks["load"])
                bound.check_packet(packet, context)
                # Daily custody above already replays original PDFs and current-main notes.
            _question_context(context, packet, identity._json(checks["preflight_raw"]))
            if is_single:
                digest = single_egress_hash(packet, discovery, context, daily=daily, bound=bound)
                once.require(request["approved_egress_hash"] == digest
                             and egress in {None, digest}, "QUESTION_SINGLE_EGRESS_NOT_APPROVED")
                egress = digest
            elif daily:
                digest = (bound.egress_hash(packet, discovery, context) if bound is not None
                          else deepseek.egress_hash(packet, discovery, context))
                once.require(egress in {None, digest}, "DAILY_PUBLIC_EGRESS_CHANGED")
                egress = digest  # Authority comes from checked main policy, not this digest.
            else:
                egress = request["approved_egress_hash"]
                once.require(question_egress_hash(packet, discovery, context) == egress,
                             "QUESTION_PUBLIC_EGRESS_NOT_APPROVED")
            return prepared
        prepared = recheck()
        # Preview uses the SAME SDK request builder, before any reservation/spend.
        if bound is not None:
            bound = bound.preview(packet, discovery, context)
            result["full_input"] = {**bound.record(), **(
                {"single_quick_request_sha256": bound.single_quick_request_sha256,
                 "single_quick_prompt_sha256": bound.single_quick_prompt_sha256} if is_single else
                {"pre_request_sha256": bound.pre_request_sha256, "pre_prompt_sha256": bound.pre_prompt_sha256})}
        elif daily:
            deepseek._deepseek_request(once.initial_prompt(packet, discovery, context),
                                      single.QuickAssessment if is_single else once.PreResearchResult)
        else:
            once.model_request(once.initial_prompt(packet, discovery, context),
                               single.QuickAssessment if is_single else once.PreResearchResult,
                               max_prompt_bytes=STOCK_PROMPT_BYTES)
        try:
            work_head = head(api, intake.WORK_REF)
        except GitHubReadError as exc:
            if str(exc) != "GitHub HTTP 404": raise
            work_head = None
        if work_head is not None:
            tree = api.get("git/trees/" + work_head + "?recursive=1")
            once.require(tree.get("truncated") is False and len(tree["tree"]) <= 5000,
                         "QUESTION_WORK_TREE_INCOMPLETE")
            existing = sorted(r["path"] for r in tree["tree"] if r["path"].startswith(packet.candidate_output_prefix))
            if existing:
                result.update(status="EXISTING_QUESTION_REUSED_NO_EXECUTION", existing_paths=existing,
                              reuse_meaning="EXISTING_RESULT_OR_PARTIAL_ATTEMPT_NOT_PROOF_OF_COMPLETION")
                return result
        if daily:
            current, rows = daily_policy.work_tree(api)
            once.require(current == work_head, "DAILY_WORK_HEAD_MOVED")
            daily_policy.capacity(api, current, rows, daily_state, packet)
            slot_prefix, day_prefix = daily_policy.reservation_plan(api, current, rows, daily_scope)
        retain = once.Retainer(api, {"prefix": packet.candidate_output_prefix,
            "id": packet.execution_id, "work_ref": intake.WORK_REF}, code, output)
        if work_head is None:
            retain.native("POST", "git/refs", {"ref": "refs/heads/" + intake.WORK_REF, "sha": code})
        # Create-only stable prepare is also a competing-writer reservation.
        recheck()
        if daily:
            marker = {**daily_scope, "policy": daily_policy.POLICY, "code_commit": code,
                      "reserved_at": clock(), "automatic_retry": False, **reading.AUTHORITY}
            for label, prefix in (("daily-slot", slot_prefix), ("daily-day", day_prefix)):
                local = output / label
                local.mkdir()
                owner = once.Retainer(api, {"prefix": prefix, "id": packet.execution_id,
                                           "work_ref": intake.WORK_REF}, code, local)
                daily_retainers.append(owner)
                daily_reservations.append(owner.save("prepare.json", marker))
            result["daily_reservations"] = daily_reservations
        retain.save("prepare.json", prepared)
        reserved = True
        retain.save("source.json", context if bound is None else bound.stored_raw)
        ins = retain.save("input.json", checks["input_raw"])
        launch_checks = {**checks, "input_source": ins, "expected_key": identity.input_key(packet).as_dict(),
                         "now": clock, "checked_at": clock()}
        recheck()
        admitted = admission.assess_admission(**launch_checks)
        once.require(admitted["research_execution_allowed"], admitted["reason"])
        result["phase"] = "LAUNCH"
        launch = retain.save("launch.json", {"id": packet.execution_id, "input_hash": canonical_hash(packet),
            "code_commit": code, "question_source": request["question_source"],
            "approved_egress_hash": egress, "permission": request["permission"],
            "automatic_retry": False,
            **({"research_method": single.METHOD_VERSION, "method_permission": request["method_permission"]} if is_single else {}),
            **({"provider": daily_policy.POLICY["provider"], "daily_scope": daily_scope,
                "daily_reservations": daily_reservations} if daily else {})})
        recheck()
        launch_checks["checked_at"] = clock()
        def execute(exact, key):
            once.require(exact == checks["input_raw"] and key == launch_checks["expected_key"], "QUESTION_CALLBACK_MISMATCH")
            def guarded(stage, prompt, model, out, usage):
                recheck()
                live = admission.assess_admission(**{**launch_checks, "checked_at": clock()})
                once.require(live["research_execution_allowed"], live["reason"])
                identity._checked_source(launch, checks["load"])
                expected = once.initial_prompt(packet, discovery, context)
                if stage == "quick" and not is_single:
                    pre = once.PreResearchResult.model_validate(prompt["pre_research"])
                    once.validate_pre_research_transition(discovery, pre, packet.seed_evidence_artifacts)
                    once.require(pre.route.value == "CONTINUE_TO_QUICK", "QUESTION_QUICK_NOT_QUALIFIED")
                    expected.update(stage="QUICK", pre_research=pre.model_dump(mode="json"),
                                    pre_research_hash=canonical_hash(pre))
                allowed = ({("quick", single.QuickAssessment)} if is_single else
                           {("pre", once.PreResearchResult), ("quick", once.QuickResearchResult)})
                once.require((stage, model) in allowed and prompt == expected, "QUESTION_MODEL_PROMPT_CHANGED")
                if daily:
                    fn = call or partial(once.model_call,
                        **({"max_prompt_bytes": STOCK_PROMPT_BYTES} if bound is None else {"bound_context": bound}),
                        base_url=once.DEEPSEEK_BASE_URL, model=once.DEEPSEEK_MODEL,
                        api_key_env="DEEPSEEK_API_KEY", provider=deepseek.PROVIDER,
                        extra_parameters={"reasoning": deepseek.REASONING})
                else:
                    fn = call or partial(once.model_call, max_prompt_bytes=STOCK_PROMPT_BYTES)
                return fn(stage, prompt, model, out, usage)
            result.update(phase="RESEARCH", formal_research_started=True)
            return once.research(packet, discovery, context, output, call=guarded, clock=clock,
                **({"bound_context": bound} if bound is not None else {}),
                **({"provider_event_prefix": deepseek.PROVIDER_EVENT_PREFIX,
                    "model_or_executor": deepseek.MODEL_OR_EXECUTOR} if daily else {}))
        report, outcome = admission.execute_after_admission(executor=execute, **launch_checks)
        retain.save("admission.json", report)
        once.require(outcome is not None, report["reason"])
        candidate, validation, usage = outcome
        result["phase"] = "RETENTION"
        candidate_source = retain.save("candidate.json", candidate)
        retain.save("receipt.json", candidate.receipt)
        retain.save("validation.json", validation)
        if not is_single and validation.funnel_result is not None:
            retain.save("funnel.json", validation.funnel_result)
        status = validation.status if is_single else validation.status.value
        if is_single and status == "VALIDATED_QUICK_RESULT":
            from .attention_inbox import ResearchAttentionHandoff, serialize_research_attention_handoff
            attention = ResearchAttentionHandoff(single_quick_input=packet, single_quick_candidate=candidate)
            retain.save("research-attention.json", serialize_research_attention_handoff(attention).encode())
            if candidate.assessment.route is single.QuickRoute.FULL_CANDIDATE:
                from . import full_research_commission as commissions
                commission = commissions.from_quick(
                    input_source={**ins, "purpose": "SINGLE_QUICK_INPUT"},
                    candidate_source={**candidate_source, "purpose": "SINGLE_QUICK_CANDIDATE"},
                    question_source=request["question_source"], input_raw=checks["input_raw"],
                    candidate_raw=once.raw(candidate),
                    question_raw=identity._checked_source(request["question_source"], checks["load"]))
                retain.save("full-commission.json", commission)
        result.update(status=status, phase="COMPLETE", provider_usage=usage,
                      candidate_hash=canonical_hash(candidate), validation_hash=canonical_hash(validation))
        retain.save("README.md", (f"# {packet.case_id} 问题式研究候选\n\n{packet.research_question}\n\n"
            f"原验证器：{status}。未语义接受、未登记当前handoff、未自动发布。\n"
            "本问题及材料范围以input/source为准；准备、执行、Human判断和投资决定分别留存。\n").encode())
    except Exception as exc:
        result.update(status="EXECUTION_INCOMPLETE" if result["formal_research_started"] else "NOT_EXECUTED",
                      error_type=type(exc).__name__)
        reason = getattr(exc, "code", None)
        if isinstance(reason, str) and re.fullmatch(r"[A-Z0-9_]{1,128}", reason):
            result["error_code"] = reason
    finally:
        uncertain = bool(retain and retain.uncertain) or any(r.uncertain for r in daily_retainers)
        result.update(finished_at=clock(), mutation_uncertain=uncertain)
        if reserved and not uncertain:
            try:
                if is_single and result["formal_research_started"]:
                    outputs = {}
                    for name in sorted(once.MODEL_OUTPUT_NAMES):
                        path = output / name
                        if path.exists():
                            outputs[name] = retain.save(name, path.read_bytes(), existing_local=True)
                    result["model_output_sources"] = outputs
                retain.save("host-receipt.json", result)
            except Exception:
                result.update(status="RETENTION_INCOMPLETE", mutation_uncertain=retain.uncertain)
                with (output / "host-retention-failure.json").open("xb") as f: f.write(once.raw(result))
        else:
            with (output / "host-receipt-local.json").open("xb") as f: f.write(once.raw(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--daily-reviewed-question", action="store_true")
    args = parser.parse_args(argv)
    from . import stock_daily_question as daily_policy
    once.require(os.environ.get("GITHUB_REPOSITORY") == once.REPO
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and (os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
             or args.daily_reviewed_question and daily_policy.label_transport(os.environ))
        and reading.SHA.fullmatch(args.code_commit) is not None
        and os.environ.get("GITHUB_SHA") == args.code_commit, "QUESTION_NATIVE_IDENTITY_REQUIRED")
    credential = "DEEPSEEK_API_KEY" if args.daily_reviewed_question else "SUB2API_API_KEY"
    once.require(bool(os.environ.get(credential)), "QUESTION_MODEL_CONNECTION_REQUIRED")
    result = run_question(api=GitHubAPI(os.environ["GH_TOKEN"], max_calls=1024),
                          code=args.code_commit, output=args.output, daily=args.daily_reviewed_question)
    print(once.raw(result).decode())
    return 0 if result["status"] in {"VALIDATED_FUNNEL_RESULT", "VALIDATED_QUICK_RESULT", "EXISTING_QUESTION_REUSED_NO_EXECUTION"} else 2


if __name__ == "__main__":
    raise SystemExit(main())