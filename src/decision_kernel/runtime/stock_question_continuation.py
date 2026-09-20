"""One create-only technical continuation of an exact reviewed-question execution gap.

This is the question-mode analogue of the existing Stock source-successor
continuation. It does not reopen the consumed parent root or create a generic
retry framework. The original question/context/Funnel remain authoritative;
only a fresh STATIC preflight, DeepSeek-specific egress approval and new Human
permission may authorize the one fixed child continuation.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import partial
import os
from pathlib import Path
import re

from ..identity import canonical_hash
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import reviewed_question_input as reviewed
from . import saved_research_once as once
from . import stock_question_host as question
from . import stock_research_intake as intake
from . import stock_research_sources as sources
from .current_state_delivery import GitHubAPI, GitHubReadError
from .external_research_execution import ExternalResearchInputPacket
from .stock_research_host import authorize, head, STOCK_PROMPT_BYTES

REQUEST = "research_runs/stock-question-continuation-request.json"
MODE = "HUMAN_AUTHORIZED_REVIEWED_QUESTION_TECHNICAL_CONTINUATION"
CHILD = "technical-continuation-v1/"
PROVIDER = "DEEPSEEK_OFFICIAL"
REASONING = {"effort": "none"}
MODEL_OR_EXECUTOR = "trusted Python + DeepSeek Responses / deepseek-flash"
PROVIDER_EVENT_PREFIX = "DEEPSEEK_RESPONSES"

PREDECESSOR_FILES = {
    "host_receipt": ("host-receipt.json", "QUESTION_TECHNICAL_PREDECESSOR_HOST"),
    "candidate": ("candidate.json", "QUESTION_TECHNICAL_PREDECESSOR_CANDIDATE"),
    "receipt": ("receipt.json", "QUESTION_TECHNICAL_PREDECESSOR_RECEIPT"),
    "validation": ("validation.json", "QUESTION_TECHNICAL_PREDECESSOR_VALIDATION"),
    "launch": ("launch.json", "QUESTION_TECHNICAL_PREDECESSOR_LAUNCH"),
    "input": ("input.json", "QUESTION_TECHNICAL_PREDECESSOR_INPUT"),
    "admission": ("admission.json", "QUESTION_TECHNICAL_PREDECESSOR_ADMISSION"),
}


def execution(security_id: str, question_id: str) -> tuple[str, str]:
    parent_id, parent_prefix = question.question_execution(security_id, question_id)
    return parent_id + "-technical-continuation-v1", parent_prefix + CHILD


def _deepseek_request(prompt, output_type):
    """Build the exact accepted DeepSeek wire without sending it."""
    body, schema, output_format, _ = once.model_request(
        prompt, output_type, max_prompt_bytes=STOCK_PROMPT_BYTES,
        model=once.DEEPSEEK_MODEL, extra_parameters={"reasoning": REASONING})
    once.require(output_format.get("type") == "json_schema"
        and output_format.get("strict") is True
        and set(output_format) == {"type", "strict", "name", "schema"},
        "QUESTION_CONTINUATION_DEEPSEEK_FORMAT_CHANGED")
    output_format = {k: v for k, v in output_format.items() if k != "strict"}
    parameters = once.response_parameters(
        body, output_format, model=once.DEEPSEEK_MODEL,
        extra_parameters={"reasoning": REASONING})
    return body, schema, output_format, parameters


def egress_hash(packet, discovery, context):
    """Bind all public material plus the exact DeepSeek provider/wire contract."""
    prompt = once.pre_prompt(packet, discovery, context)
    prompt["binding"]["as_of"] = "HOST_ASSIGNED_RESEARCH_CUTOFF"
    _, pre_schema, pre_format, pre_parameters = _deepseek_request(prompt, once.PreResearchResult)
    quick_prompt = deepcopy(prompt)
    quick_prompt.update(stage="QUICK",
        pre_research="ONLY_ORIGINAL_VALIDATED_PRE_AT_RUNTIME",
        pre_research_hash="CANONICAL_HASH_OF_VALIDATED_PRE_AT_RUNTIME")
    _, quick_schema, quick_format, quick_parameters = _deepseek_request(
        quick_prompt, once.QuickResearchResult)
    # Dynamic Pre content is represented by an explicit placeholder; the runtime
    # reconstructs and validates the exact Quick prompt from the actual Pre.
    return canonical_hash({
        "pre_prompt": prompt,
        "source_refs": [s.model_dump(mode="json") for s in packet.source_refs],
        "budget": packet.budget,
        "system_sha256": once.sha(once.SYSTEM.encode()),
        "provider": PROVIDER,
        "endpoint": once.DEEPSEEK_BASE_URL,
        "model": once.DEEPSEEK_MODEL,
        "credential_binding": "DEEPSEEK_API_KEY",
        "reasoning": REASONING,
        "max_output_tokens": once.MAX_OUTPUT_TOKENS,
        "max_prompt_bytes": STOCK_PROMPT_BYTES,
        "pre_schema_sha256": once.sha(once.raw(pre_schema)),
        "quick_schema_sha256": once.sha(once.raw(quick_schema)),
        "pre_output_format_sha256": once.sha(once.raw(pre_format)),
        "quick_output_format_sha256": once.sha(once.raw(quick_format)),
        "pre_parameters": {k: v for k, v in pre_parameters.items() if k != "input"},
        "quick_parameters": {k: v for k, v in quick_parameters.items() if k != "input"},
        "quick": "ONLY_ORIGINAL_VALIDATED_PRE_AND_ITS_HASH_ADDED_IF_CONTINUE_TO_QUICK",
    })


def _tree(api, commit):
    tree = api.get("git/trees/" + commit + "?recursive=1")
    once.require(tree.get("truncated") is False and len(tree["tree"]) <= 5000,
                 "QUESTION_CONTINUATION_WORK_TREE_INCOMPLETE")
    return {r["path"]: r for r in tree["tree"] if r["type"] != "tree"}


def _checked(api, spec):
    return identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))


def _predecessor(api, request, q):
    """Verify the immutable failed parent without treating it as a retry token."""
    pred = request["predecessor"]
    parent_id, parent_prefix = question.question_execution(q["security_id"], q["question_id"])
    once.require(isinstance(pred, dict) and set(pred) == {
        "run_id", "artifact", "work_commit", "execution_id", "root", "sources"},
        "QUESTION_CONTINUATION_PREDECESSOR_SHAPE")
    once.require(pred["execution_id"] == parent_id and pred["root"] == parent_prefix
                 and reading.SHA.fullmatch(pred["work_commit"]) is not None
                 and type(pred["run_id"]) is int and pred["run_id"] > 0,
                 "QUESTION_CONTINUATION_PREDECESSOR_IDENTITY")

    current_work = head(api, intake.WORK_REF)
    rows = _tree(api, current_work)
    child_id, child_prefix = execution(q["security_id"], q["question_id"])
    child_paths = sorted(p for p in rows if p.startswith(child_prefix))

    source_rows = pred["sources"]
    once.require(isinstance(source_rows, dict) and set(source_rows) == set(PREDECESSOR_FILES),
                 "QUESTION_CONTINUATION_PREDECESSOR_SOURCES")
    raw, parsed, refs = {}, {}, []
    for key, (filename, purpose) in PREDECESSOR_FILES.items():
        spec = source_rows[key]
        once.require(spec["repository"] == once.REPO and spec["ref"] == pred["work_commit"]
            and spec["path"] == parent_prefix + filename and spec["purpose"] == purpose
            and rows.get(spec["path"], {}).get("sha") == spec["git_blob"],
            "QUESTION_CONTINUATION_PREDECESSOR_FILE_CHANGED")
        body = _checked(api, spec)
        raw[key] = body
        parsed[key] = identity._json(body)
        refs.append(spec)

    # The first attempt reached Research admission but retained no Pre/Quick result.
    host = parsed["host_receipt"]
    usage = host.get("provider_usage")
    once.require(host.get("execution_id") == parent_id
        and host.get("status") == "EXECUTION_GAP"
        and host.get("phase") == "COMPLETE"
        and host.get("formal_research_started") is True
        and host.get("mutation_uncertain") is False
        and host.get("automatic_retry") is False
        and host.get("semantic_acceptance") == "NOT_ESTABLISHED"
        and isinstance(usage, list) and len(usage) == 1
        and usage[0].get("stage") == "pre"
        and usage[0].get("status") == "FAILED"
        and usage[0].get("error_type") == "PermissionDeniedError"
        and usage[0].get("requested_model") == "gpt-6-astra"
        and usage[0].get("response_received") is False
        and usage[0].get("output_text_retained") is False,
        "QUESTION_CONTINUATION_PREDECESSOR_NOT_EXACT_TECHNICAL_FAILURE")

    candidate = parsed["candidate"]
    receipt = parsed["receipt"]
    validation = parsed["validation"]
    once.require(candidate.get("completion") == "INCOMPLETE_TECHNICAL_FAILURE"
        and candidate.get("pre_research") is None and candidate.get("quick_research") is None
        and candidate.get("receipt") == receipt
        and receipt.get("execution_id") == parent_id
        and receipt.get("platform_task_id") == str(pred["run_id"])
        and receipt.get("stop_or_failure_reason") == "PermissionDeniedError"
        and receipt.get("technical_retries_used") == 0
        and validation.get("status") == "EXECUTION_GAP"
        and validation.get("completion") == "INCOMPLETE_TECHNICAL_FAILURE"
        and validation.get("gap_reason") == "PermissionDeniedError"
        and validation.get("funnel_result") is None,
        "QUESTION_CONTINUATION_PREDECESSOR_RESULT_CHANGED")

    old_input = ExternalResearchInputPacket.model_validate(parsed["input"])
    once.require(old_input.execution_id == parent_id
        and old_input.candidate_output_prefix == parent_prefix
        and old_input.case_id == q["case_id"]
        and old_input.security_id == q["security_id"]
        and old_input.research_question == q["question"],
        "QUESTION_CONTINUATION_PREDECESSOR_INPUT_CHANGED")
    old_refs = [s.model_dump(mode="json") for s in old_input.source_refs]
    once.require(request["question_source"] in old_refs
        and request["context_source"] in old_refs,
        "QUESTION_CONTINUATION_PREDECESSOR_PUBLIC_CONTEXT_CHANGED")

    launch = parsed["launch"]
    once.require(launch.get("id") == parent_id and launch.get("automatic_retry") is False
        and launch.get("question_source") == request["question_source"],
        "QUESTION_CONTINUATION_PREDECESSOR_LAUNCH_CHANGED")
    once.require(parsed["admission"].get("research_execution_allowed") is True
        and parsed["admission"].get("reason") == "RESEARCH_EXECUTION_ALLOWED",
        "QUESTION_CONTINUATION_PREDECESSOR_ADMISSION_CHANGED")

    parent_names = {p[len(parent_prefix):] for p in rows
                    if p.startswith(parent_prefix) and "/" not in p[len(parent_prefix):]}
    once.require("pre.json" not in parent_names and "funnel.json" not in parent_names,
                 "QUESTION_CONTINUATION_PREDECESSOR_HAS_RESEARCH_RESULT")

    run = api.get("actions/runs/" + str(pred["run_id"]))
    artifact = pred["artifact"]
    once.require(run["path"] == ".github/workflows/stock-business-research.yml"
        and run["event"] == "workflow_dispatch" and run["run_attempt"] == 1
        and run["head_branch"] == "main" and run["head_sha"] == artifact["head_sha"]
        and run["status"] == "completed" and run["conclusion"] == "failure",
        "QUESTION_CONTINUATION_PREDECESSOR_RUN_CHANGED")
    jobs = api.get(f"actions/runs/{pred['run_id']}/jobs?per_page=100")
    once.require(jobs["total_count"] == len(jobs["jobs"])
        and {j["name"]: j.get("conclusion") for j in jobs["jobs"]} == {
            "research-stock-business": "failure", "prepare-stock-sources": "skipped"},
        "QUESTION_CONTINUATION_PREDECESSOR_JOBS_CHANGED")
    artifacts = api.get(f"actions/runs/{pred['run_id']}/artifacts?per_page=100")
    matches = [a for a in artifacts["artifacts"] if a["id"] == artifact["id"]]
    once.require(artifacts["total_count"] == len(artifacts["artifacts"]) and len(matches) == 1
        and all(matches[0].get(k) == artifact[k] for k in
                ("id", "name", "size_in_bytes", "digest"))
        and matches[0]["workflow_run"]["head_sha"] == artifact["head_sha"]
        and not matches[0].get("expired", True),
        "QUESTION_CONTINUATION_PREDECESSOR_ARTIFACT_CHANGED")

    return {
        "parent_execution_id": parent_id,
        "parent_prefix": parent_prefix,
        "child_execution_id": child_id,
        "child_prefix": child_prefix,
        "current_work": current_work,
        "child_paths": child_paths,
        "source_refs": refs,
        "host": host,
        "input": old_input,
        "artifact": artifact,
        "run_id": pred["run_id"],
    }


def _inputs(*, api, code, request, clock):
    """Reuse original question construction, then bind a fixed technical child."""
    once.require(set(request) == {
        "schema_version", "enabled", "mode", "permission", "question_source",
        "context_source", "preflight_source", "approved_egress_hash", "predecessor"},
        "QUESTION_CONTINUATION_REQUEST_SHAPE")
    base = {k: request[k] for k in (
        "schema_version", "enabled", "permission", "question_source",
        "context_source", "preflight_source", "approved_egress_hash")}
    base["mode"] = question.QUESTION_MODE
    q, packet, discovery, context, checks = question._question_inputs(
        api=api, code=code, request=base, clock=clock)
    predecessor = _predecessor(api, request, q)
    refs = [s.model_dump(mode="json") for s in packet.source_refs]
    for spec in predecessor["source_refs"]:
        if spec not in refs:
            refs.append(spec)
    packet_data = packet.model_dump(mode="json")
    packet_data.update({
        "execution_id": predecessor["child_execution_id"],
        "candidate_output_prefix": predecessor["child_prefix"],
        "source_refs": refs,
        "known_unknowns": list(dict.fromkeys([
            *packet.known_unknowns,
            "TECHNICAL_CONTINUATION_OF:" + predecessor["parent_execution_id"],
            "PREDECESSOR_RESULT:EXECUTION_GAP_PERMISSION_DENIED_NO_PRE_OUTPUT",
            "PROVIDER_CONTINUATION:DEEPSEEK_OFFICIAL_DEEPSEEK_FLASH",
        ])),
        "prompt_version": "reviewed-question-technical-continuation-v1",
    })
    packet = ExternalResearchInputPacket.model_validate(packet_data)
    discovery = discovery.model_copy(update={
        "discovery_id": packet.execution_id,
        "as_of": packet.research_cutoff,
    })
    checks = {**checks, "input_raw": once.raw(packet)}
    return q, packet, discovery, context, checks, predecessor


def run_continuation(*, api, code, output, clock=once.now, call=None):
    from . import reviewed_question_input as reviewed_input

    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 "QUESTION_CONTINUATION_UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    result = {"status": "NOT_EXECUTED", "question_kind": MODE, "code_commit": code,
        "started_at": clock(), "phase": "AUTHORIZATION", "formal_research_started": False,
        "automatic_retry": False, "registered_current_handoff": False,
        "semantic_acceptance": "NOT_ESTABLISHED", **reading.AUTHORITY}
    retain = None
    reserved = False
    try:
        request = identity._json(api.file(REQUEST, code))
        authorize(api, code, request, request_path=REQUEST, mode=MODE)
        q, packet, discovery, context, checks, predecessor = _inputs(
            api=api, code=code, request=request, clock=clock)
        result.update(question_id=q["question_id"], revision=q["revision"],
            thscode=packet.case_id, execution_id=packet.execution_id,
            predecessor_execution_id=predecessor["parent_execution_id"],
            predecessor_run_id=predecessor["run_id"], phase="INPUT_PREPARATION")

        if predecessor["child_paths"]:
            result.update(status="EXISTING_QUESTION_CONTINUATION_REUSED_NO_EXECUTION",
                existing_paths=predecessor["child_paths"],
                reuse_meaning="EXISTING_RESULT_OR_PARTIAL_ATTEMPT_NOT_PROOF_OF_COMPLETION")
            return result

        def recheck():
            authorize(api, code, request, request_path=REQUEST, mode=MODE)
            prepared = reviewed_input.prepare(
                question_source=request["question_source"], checked_at=clock(), **checks)
            once.require(identity._checked_source(
                request["context_source"], checks["load"]) == once.raw(context),
                "QUESTION_CONTINUATION_CONTEXT_CHANGED_BEFORE_EGRESS")
            question._question_context(
                context, packet, identity._json(checks["preflight_raw"]))
            sources.recheck(context, api=api, code_commit=code, clock=clock)
            live_pred = _predecessor(api, request, q)
            once.require(live_pred["child_execution_id"] == packet.execution_id
                and live_pred["child_prefix"] == packet.candidate_output_prefix,
                "QUESTION_CONTINUATION_PREDECESSOR_MOVED")
            once.require(egress_hash(packet, discovery, context)
                == request["approved_egress_hash"],
                "QUESTION_CONTINUATION_PUBLIC_EGRESS_NOT_APPROVED")
            return prepared

        prepared = recheck()
        _deepseek_request(once.pre_prompt(packet, discovery, context), once.PreResearchResult)

        retain = once.Retainer(api, {
            "prefix": packet.candidate_output_prefix,
            "id": packet.execution_id,
            "work_ref": intake.WORK_REF,
        }, code, output)
        # Create-only prepare is the continuation reservation.
        recheck()
        retain.save("prepare.json", prepared)
        reserved = True
        retain.save("source.json", context)
        ins = retain.save("input.json", checks["input_raw"])
        launch_checks = {**checks, "input_source": ins,
            "expected_key": identity.input_key(packet).as_dict(),
            "now": clock, "checked_at": clock()}
        recheck()
        admitted = admission.assess_admission(**launch_checks)
        once.require(admitted["research_execution_allowed"], admitted["reason"])
        result["phase"] = "LAUNCH"
        launch = retain.save("launch.json", {
            "id": packet.execution_id,
            "input_hash": canonical_hash(packet),
            "code_commit": code,
            "question_source": request["question_source"],
            "approved_egress_hash": request["approved_egress_hash"],
            "permission": request["permission"],
            "provider": {
                "name": PROVIDER, "base_url": once.DEEPSEEK_BASE_URL,
                "model": once.DEEPSEEK_MODEL, "reasoning": REASONING,
                "credential_binding": "DEEPSEEK_API_KEY",
            },
            "predecessor": {
                "execution_id": predecessor["parent_execution_id"],
                "run_id": predecessor["run_id"],
                "artifact": predecessor["artifact"],
                "work_commit": request["predecessor"]["work_commit"],
                "sources": request["predecessor"]["sources"],
            },
            "automatic_retry": False,
        })
        recheck()
        launch_checks["checked_at"] = clock()

        def execute(exact, key):
            once.require(exact == checks["input_raw"]
                and key == launch_checks["expected_key"],
                "QUESTION_CONTINUATION_CALLBACK_MISMATCH")

            def guarded(stage, prompt, model, out, usage):
                recheck()
                live = admission.assess_admission(
                    **{**launch_checks, "checked_at": clock()})
                once.require(live["research_execution_allowed"], live["reason"])
                identity._checked_source(launch, checks["load"])
                expected = once.pre_prompt(packet, discovery, context)
                if stage == "quick":
                    pre = once.PreResearchResult.model_validate(prompt["pre_research"])
                    once.validate_pre_research_transition(
                        discovery, pre, packet.seed_evidence_artifacts)
                    once.require(pre.route.value == "CONTINUE_TO_QUICK",
                                 "QUESTION_CONTINUATION_QUICK_NOT_QUALIFIED")
                    expected.update(stage="QUICK",
                        pre_research=pre.model_dump(mode="json"),
                        pre_research_hash=canonical_hash(pre))
                once.require((stage, model) in {
                    ("pre", once.PreResearchResult),
                    ("quick", once.QuickResearchResult),
                } and prompt == expected,
                    "QUESTION_CONTINUATION_MODEL_PROMPT_CHANGED")
                fn = call or partial(once.model_call,
                    max_prompt_bytes=STOCK_PROMPT_BYTES,
                    base_url=once.DEEPSEEK_BASE_URL,
                    model=once.DEEPSEEK_MODEL,
                    api_key_env="DEEPSEEK_API_KEY",
                    provider=PROVIDER,
                    extra_parameters={"reasoning": REASONING})
                return fn(stage, prompt, model, out, usage)

            result.update(phase="RESEARCH", formal_research_started=True)
            return once.research(packet, discovery, context, output,
                call=guarded, clock=clock,
                provider_event_prefix=PROVIDER_EVENT_PREFIX,
                model_or_executor=MODEL_OR_EXECUTOR)

        report, outcome = admission.execute_after_admission(
            executor=execute, **launch_checks)
        retain.save("admission.json", report)
        once.require(outcome is not None, report["reason"])
        candidate, validation, usage = outcome
        result["phase"] = "RETENTION"
        retain.save("candidate.json", candidate)
        retain.save("receipt.json", candidate.receipt)
        retain.save("validation.json", validation)
        if validation.funnel_result is not None:
            retain.save("funnel.json", validation.funnel_result)
        result.update(status=validation.status.value, phase="COMPLETE",
            provider_usage=usage, candidate_hash=canonical_hash(candidate),
            validation_hash=canonical_hash(validation))
        retain.save("README.md", (
            f"# {packet.case_id} 问题式研究技术接续候选\n\n"
            f"{packet.research_question}\n\n"
            f"前序：{predecessor['parent_execution_id']} / run {predecessor['run_id']}。\n\n"
            f"原验证器：{validation.status.value}。"
            "未语义接受、未登记当前handoff、未自动发布。\n"
            "本次仅技术接续旧EXECUTION_GAP；Human判断和投资决定仍独立。\n"
        ).encode())
    except Exception as exc:
        result.update(
            status="EXECUTION_INCOMPLETE" if result["formal_research_started"]
                   else "NOT_EXECUTED",
            error_type=type(exc).__name__)
        reason = getattr(exc, "code", None)
        if isinstance(reason, str) and re.fullmatch(r"[A-Z0-9_]{1,128}", reason):
            result["error_code"] = reason
    finally:
        result.update(finished_at=clock(),
                      mutation_uncertain=bool(retain and retain.uncertain))
        if reserved and retain is not None and not retain.uncertain:
            try:
                retain.save("host-receipt.json", result)
            except Exception:
                result.update(status="RETENTION_INCOMPLETE",
                              mutation_uncertain=retain.uncertain)
                with (output / "host-retention-failure.json").open("xb") as f:
                    f.write(once.raw(result))
        else:
            with (output / "host-receipt-local.json").open("xb") as f:
                f.write(once.raw(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    once.require(os.environ.get("GITHUB_REPOSITORY") == once.REPO
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and reading.SHA.fullmatch(args.code_commit) is not None
        and os.environ.get("GITHUB_SHA") == args.code_commit,
        "QUESTION_CONTINUATION_NATIVE_IDENTITY_REQUIRED")
    once.require(bool(os.environ.get("DEEPSEEK_API_KEY")),
                 "QUESTION_CONTINUATION_MODEL_CONNECTION_REQUIRED")
    result = run_continuation(
        api=GitHubAPI(os.environ["GH_TOKEN"], max_calls=1024),
        code=args.code_commit, output=args.output)
    print(once.raw(result).decode())
    return 0 if result["status"] in {
        "VALIDATED_FUNNEL_RESULT",
        "EXISTING_QUESTION_CONTINUATION_REUSED_NO_EXECUTION",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
