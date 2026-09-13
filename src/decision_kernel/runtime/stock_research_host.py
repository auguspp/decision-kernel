"""First business Pre/necessary Quick after a verified saved Stock result.

Reuses the original admission, SDK/model loop, validator and create-only Retainer.
No repeated first-baseline execution, automatic Deep, price-to-Belief or retry.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from functools import partial
import os
from pathlib import Path
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
from .current_state_delivery import GitHubAPI, GitHubReadError
from .external_research_execution import ExternalResearchInputPacket

REQUEST = "research_runs/stock-research-request.json"
STOCK_PROMPT_BYTES = 512 * 1024


def head(api, ref):
    result = api._call("GET", "git/ref/heads/" + ref).json()["object"]
    once.require(result["type"] == "commit" and reading.SHA.fullmatch(result["sha"]), "invalid branch identity")
    return result["sha"]


def authorize(api, code, request, *, request_path=REQUEST, mode=intake.QUESTION_KIND):
    once.require(head(api, "main") == code and request.get("schema_version") == 1
                 and request.get("enabled") is True
                 and request.get("mode") == mode, "Stock research not enabled on exact main")
    once.require(identity._json(api.file(request_path, code)) == request, "Stock request is not exact trusted main")
    p = request["permission"]
    comment = api._call("GET", "issues/comments/" + str(int(p["comment_id"]))).json()
    once.require(comment["id"] == p["comment_id"]
                 and comment["issue_url"] == "https://api.github.com/repos/" + once.REPO + "/issues/297"
                 and once.sha(comment["body"].encode()) == p["body_sha256"]
                 and comment["created_at"] == p["created_at"], "Stock research permission changed or unavailable")
    once.require(reading.clock(comment["created_at"]) <= reading.clock(once.now()), "future Stock permission")
    return {"comment_id": comment["id"], "body_sha256": p["body_sha256"],
            "meaning": "RECORDED_HUMAN_SCOPE_NOT_GITHUB_USERNAME_AUTHORITY"}


def run_item(*, api, code, request, item, origin, reading_commit, output,
             capture=sources.capture, call=None, clock=once.now, recovery_request=None):
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "unsafe Stock output")
    from . import stock_source_recovery as recovery
    expected = intake.execution(item["thscode"]) if recovery_request is None else recovery.execution(item["thscode"])
    once.require((item["execution_id"], item["prefix"]) == expected
        and item["security_id"] == intake.security(item["thscode"])
        and item["observation"]["thscode"] == item["thscode"], "Stock item identity differs")
    output.mkdir(parents=True, exist_ok=False)
    retain = once.Retainer(api, {"prefix": item["prefix"], "id": item["execution_id"],
        "work_ref": intake.WORK_REF}, code, output)
    receipt = {"schema_version": 1, "thscode": item["thscode"], "execution_id": item["execution_id"],
        "question_kind": intake.QUESTION_KIND, "started_at": clock(), "formal_research_started": False,
        "status": "NOT_EXECUTED", "phase": "HISTORY", "automatic_retry": False, **reading.AUTHORITY}
    reserved = False
    binding = None
    try:
        authorize(api, code, request)
        try:
            work_head = head(api, intake.WORK_REF)
        except GitHubReadError as exc:
            if str(exc) != "GitHub HTTP 404": raise
            retain.native("POST", "git/refs", {"ref": "refs/heads/" + intake.WORK_REF, "sha": code})
            work_head = head(api, intake.WORK_REF)
        paths = intake.inventory(api, work_head)
        existing = sorted(p for p in paths if p.startswith(item["prefix"]))
        if existing:
            receipt.update(status="EXISTING_BASELINE_REUSED_NO_EXECUTION", existing_paths=existing,
                reuse_meaning="EXISTING_RESULT_OR_PARTIAL_ATTEMPT_NOT_PROOF_OF_COMPLETION")
            return receipt
        if recovery_request is not None:
            binding = recovery.bind(api=api, code=code, request=recovery_request,
                item=item, origin=origin, clock=clock)
        reservation = retain.save("prepare.json", {"schema_version": 1, "thscode": item["thscode"],
            "execution_id": item["execution_id"], "question_kind": intake.QUESTION_KIND,
            "origin": origin, "observation": item["observation"], "code_commit": code,
            "permission": request["permission"], "started_at": clock(),
            **({"source_recovery": binding} if binding else {}), **reading.AUTHORITY})
        reservation["purpose"] = "STOCK_BASELINE_SELECTION"
        reserved = True
        receipt["phase"] = "SOURCE_PREPARATION"
        context, reads, source_process = capture(ticker=item["thscode"][:6],
            observation={"origin": origin, "row": item["observation"]}, api=api,
            code_commit=code, output=output / "sources", clock=clock)
        if binding is not None:
            recovery.check_materials(binding, context)
            context["source_recovery"] = binding
        once.require(len(once.raw(context)) <= sources.CONTEXT_BYTES, "full stock context too large; no clipping")
        cs = retain.save("source.json", context); cs["purpose"] = "MODEL_CONTEXT"
        meta = api.get("git/commits/" + cs["ref"])
        once.require(meta["sha"] == cs["ref"], "stock source commit differs")
        seed = EvidenceArtifact(id=uuid5(NAMESPACE_URL, item["execution_id"] + cs["sha256"]),
            source_type="SAVED_RESEARCH_OBSERVATION", source_identifier=item["execution_id"],
            source_locator=once.locator(cs), published_at=meta["committer"]["date"],
            available_at=clock(), retrieved_at=clock(), content_hash=cs["sha256"],
            idempotency_key=item["execution_id"], retention_mode="FULL_ARTIFACT",
            replayability_level="PARTIAL", raw_storage_ref=once.locator(cs),
            license_terms_note=sources.SCOPE)
        report_id = context["issuer_inventory"]["report_id"]
        report_read = next(r["id"] for r in reads if r["identity"] == item["thscode"][:6] + ":" + report_id)
        query = "CNINFO_COHERENT_400_DAY_QUERY:" + item["thscode"]
        end = clock()
        pf = {"schema_version": 1, "provenance": "RECORDED_TOOL_RETURNS", "case_id": item["thscode"],
            "ticker": item["thscode"][:6], "security_id": item["security_id"],
            "started_at": source_process["started_at"], "finished_at": end,
            "valid_until": (reading.clock(end) + timedelta(minutes=45)).isoformat(), "reads": reads,
            "required_classes": [
                {"id": "FULL_BUSINESS_REPORT", "mode": "STATIC", "body_ids": [report_read], "inventory_id": None},
                {"id": "RECENT_MATERIAL_DISCLOSURE_CHECK", "mode": "LATEST_INVENTORY", "body_ids": [r["id"] for r in reads], "inventory_id": "updates"}],
            "inventories": [{"id": "updates", "class_id": "RECENT_MATERIAL_DISCLOSURE_CHECK",
                "started_at": source_process["started_at"], "finished_at": end,
                "planned_queries": [query], "query_events": [{"query": query, "status": "SUCCEEDED",
                    "tool_reference": "SAME_RUN_ARTIFACT:" + item["thscode"] + "/sources/source-journal.json",
                    "checked_at": source_process["inventory_finished_at"]}],
                "leads": [{"identity": r["identity"], "locator": r["locator"], "authority": "PRIMARY",
                    "decision_relevant": True, "relevance_note": "Full body retained: report and all same/later dated disclosures, not a bullish title filter.",
                    "body_id": r["id"], "primary_identity": r["identity"], "primary_locator": r["locator"]} for r in reads]}],
            "limits": {"max_queries": 1, "max_reads": len(reads)},
            "seed_publications": [{"evidence_id": str(seed.id), "kind": "GIT_COMMIT", "source": cs}],
            "notes": sources.SCOPE + " Logical inventory query; individual HTTP returns recorded separately."}
        ps = retain.save("preflight.json", pf); ps["purpose"] = admission.PREFLIGHT_PURPOSE
        saved_reading = identity._json(api.file("current-state.json", reading_commit))
        reading.validate_read_package(saved_reading)
        once.require(reading.clock(saved_reading["checks"]["finished_at"]) <= reading.clock(clock())
                     <= reading.clock(saved_reading["checks"]["recheck_after"]), "Stock reading window expired")
        selected = clock(); cutoff = clock()
        parent_refs = [binding[k] for k in ("parent_failure", "parent_selection", "request", "exposure")] if binding else []
        packet = ExternalResearchInputPacket(execution_id=item["execution_id"], case_id=item["thscode"],
            ticker=item["thscode"][:6], security_id=item["security_id"], source_lane=intake.LANE,
            selected_at=selected, research_cutoff=cutoff, code_commit=code, current_state_commit=reading_commit,
            current_state_reading_hash=saved_reading["reading_hash"], source_refs=[cs, ps, reservation] + parent_refs,
            seed_evidence_artifacts=[seed], research_question=intake.QUESTION,
            known_unknowns=["REQUIRED_SOURCE_CLASS:FULL_BUSINESS_REPORT:STATIC",
                "REQUIRED_SOURCE_CLASS:RECENT_MATERIAL_DISCLOSURE_CHECK:LATEST_INVENTORY",
                "Price is a question, not evidence of business benefit or WHY. Tables require semantic interpretation.",
                "Only declared CNINFO window/channels inspected; external policy, competitor and customer evidence not acquired."],
            next_discriminating_search="用原定期报告和后续公告检查业务对应、经济重大性及反证；不把股份或行业分类当作盈利暴露。",
            method_version="research-funnel-v1", prompt_version="stock-business-baseline-v1",
            allowed_tools=["OTHER_READ"], candidate_output_prefix=item["prefix"],
            budget={"max_tool_calls": 6, "max_search_queries": 0, "max_source_reads": 4,
                "max_technical_retries": 0, "max_elapsed_minutes": 15,
                **{k+"_enforcement": "SOFT_EXECUTOR" for k in ("tool_calls", "search_queries", "source_reads", "technical_retries", "elapsed_time")}})
        catalogue = api.file(identity.CATALOG_PATH, code)
        checks = dict(input_raw=once.raw(packet), preflight_raw=once.raw(pf),
            catalog_source=once.source_ref(identity.CATALOG_PATH, code, catalogue, "CURRENT_CODE_EXECUTION_SCOPE"),
            load=lambda s: api.file(s["path"], s["ref"]), commit=lambda ref: api.get("git/commits/" + ref),
            current_code=lambda: head(api, "main"), now=clock, checked_at=clock())
        ready = admission.assess_admission(**checks)
        once.require(ready["reason"] == "INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION", ready["reason"])
        ins = retain.save("input.json", packet)
        discovery = DiscoveryInput(discovery_id=packet.execution_id, source_lane=packet.source_lane,
            ticker=packet.ticker, security_id=packet.security_id, as_of=cutoff,
            economic_direction="价格观察触发的首次公司业务与经济暴露核验，方向未定",
            factual_observations=[{"statement": "Saved dated Stock observation and full declared issuer bodies are supplied; price does not establish benefit.", "evidence_artifact_ids": [seed.id]}],
            source_lineage=[{"evidence_artifact_id": seed.id, "source_locator": seed.source_locator, "available_at": seed.available_at}],
            why_now=("Human许可的原Stock来源准备失败修复；保留父失败，不是新价格发现或独立新公告。"
                     if binding else "原Stock合格观察首次进入业务研究；不是今日新增公告或自动受益认定。"),
            contradiction_or_mapping_warning="行业成员身份不是收入/利润/现金流受益证明。",
            next_discriminating_search=packet.next_discriminating_search,
            known_stop_or_downgrade_condition="Pre可停止；Quick只在原路由要求时执行。必需来源或技术失败不得包装为WAIT。")
        egress = canonical_hash({"input_hash": canonical_hash(packet), "discovery": discovery, "context": context})
        checks.update(input_source=ins, expected_key=identity.input_key(packet).as_dict(), checked_at=clock())
        preliminary = admission.assess_admission(**checks)
        once.require(preliminary["research_execution_allowed"], preliminary["reason"])
        retain.save("launch.json", {"id": packet.execution_id, "input_hash": canonical_hash(packet),
            "public_egress_hash": egress, "permission": request["permission"], "automatic_retry": False})
        checks["checked_at"] = clock()
        def execute(exact, key):
            once.require(exact == checks["input_raw"] and key == checks["expected_key"], "Stock callback identity differs")
            def guarded(stage, prompt, model, out, usage):
                authorize(api, code, request)
                if binding is not None:
                    fresh = recovery.bind(api=api, code=code, request=recovery_request,
                        item=item, origin=origin, clock=clock)
                    once.require(fresh == binding, "Stock source recovery binding changed before model")
                    recovery.check_materials(fresh, context)
                sources.recheck(context, api=api, code_commit=code, clock=clock)
                once.require(once.sha(once.raw(context)) == cs["sha256"], "Stock context changed before egress")
                return (call or partial(once.model_call, max_prompt_bytes=STOCK_PROMPT_BYTES))(stage, prompt, model, out, usage)
            receipt.update(formal_research_started=True, phase="RESEARCH")
            return once.research(packet, discovery, context, output, call=guarded, clock=clock)
        report, result = admission.execute_after_admission(executor=execute, **checks)
        retain.save("admission.json", report)
        once.require(result is not None, report["reason"])
        candidate, validation, usage = result
        receipt["phase"] = "RETENTION"
        retain.save("candidate.json", candidate); retain.save("receipt.json", candidate.receipt)
        retain.save("validation.json", validation)
        if validation.funnel_result is not None: retain.save("funnel.json", validation.funnel_result)
        outcome = intake.describe(once.raw(packet), once.raw(candidate))
        receipt.update(outcome, provider_usage=usage, phase="COMPLETE")
        retain.save("README.md", ("# " + item["company_name"] + " " + item["thscode"] + " 首次业务研究候选\n\n"
            + intake.QUESTION + "\n\n" + outcome["status"] + "\n\n" + (outcome["terminal_reason"] or "技术缺口，未完成研究。")
            + "\n\nNOT HUMAN ACCEPTANCE / NO INVESTMENT AUTHORITY.\n").encode())
    except Exception as exc:
        receipt.update(status="EXECUTION_INCOMPLETE" if receipt["formal_research_started"] else "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE",
            error_type=type(exc).__name__)
        if isinstance(exc, (once.TrialError, identity.ExecutionIdentityError, admission.AdmissionRejected)):
            receipt["error_code"] = exc.code
        if reserved and not receipt["formal_research_started"] and not retain.uncertain:
            try:
                retain.save("failure.json", {**receipt, "record_kind": "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT",
                    "research_execution": "NOT_EXECUTED", "funnel_status": "NOT_REACHED", "finished_at": clock()})
            except Exception as failed_retention:
                receipt.update(status="RETENTION_INCOMPLETE", retention_error_type=type(failed_retention).__name__)
                (output / "failure-retention-gap.json").write_bytes(once.raw(receipt))
    finally:
        receipt.update(finished_at=clock(), mutation_uncertain=retain.uncertain)
        if reserved and not retain.uncertain:
            try: retain.save("host-receipt.json", receipt)
            except Exception:
                receipt.update(status="RETENTION_INCOMPLETE", mutation_uncertain=retain.uncertain)
                (output / "host-retention-failure.json").write_bytes(once.raw(receipt))
        else:
            (output / "host-receipt-local.json").write_bytes(once.raw(receipt))
    return receipt


def consume(*, api, code: str, source_run_id: int, output: Path, run_one=run_item, recover_sources=False):
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "unsafe output")
    output.mkdir(parents=True, exist_ok=False)
    request = identity._json(api.file(REQUEST, code)); authorize(api, code, request)
    run = api.get("actions/runs/" + str(source_run_id))
    reading.run_identity(run, "stock", success=True)
    artifacts = api.get(f"actions/runs/{source_run_id}/artifacts?per_page=100")
    once.require(artifacts["total_count"] == len(artifacts["artifacts"]), "Stock artifact enumeration incomplete")
    name = f"stock-reading-{source_run_id}-1"
    available = [a for a in artifacts["artifacts"] if a["name"] == name]
    if not available:
        jobs = api.get(f"actions/runs/{source_run_id}/jobs?per_page=100")
        once.require(jobs["total_count"] == len(jobs["jobs"]) and jobs["jobs"], "Stock purpose metadata incomplete")
        once.require(not any(j["name"] == "stock-reading" and j.get("conclusion") != "skipped"
                             for j in jobs["jobs"]), "Stock purpose run missing required artifact")
        result = {"status": "NOT_A_STOCK_READING_RUN", "source_run_id": source_run_id, "items": []}
        (output / "batch-receipt.json").write_bytes(once.raw(result)); return result
    artifact = reading.select_artifact(available, name)
    archive = api.archive(artifact); (output / "stock-origin.zip").write_bytes(archive)
    files = reading.unpack_archive(archive, artifact, run)
    selected = intake.plan(run, files)
    (output / "selection.json").write_bytes(once.raw(selected))
    recovery_request = None
    original_codes = [i["thscode"] for i in selected["items"]]
    if recover_sources:
        from . import stock_source_recovery as recovery
        recovery_request = identity._json(api.file(recovery.REQUEST, code))
        authorize(api, code, recovery_request, request_path=recovery.REQUEST, mode=recovery.MODE)
        selected = {**selected, "items": recovery.select(selected, recovery_request, source_run_id)}
    r = head(api, reading.READ_REF)
    origin = {"run": reading.concise_run(run), "artifact_id": artifact["id"],
        "archive_sha256": once.sha(archive), "projection_hash": selected["projection_hash"],
        "market_session": selected["market_session"]}
    result = {"status": "COMPLETED", "source_run_id": source_run_id, "items": [],
        "source_recovery": recover_sources, "original_qualified_issuers": original_codes,
        "excluded": selected["excluded"], "planned_issuers": [i["thscode"] for i in selected["items"]],
        "unattempted_issuers": [i["thscode"] for i in selected["items"]], "reading_commit": r, **reading.AUTHORITY}
    for item in selected["items"]:
        outcome = run_one(api=api, code=code, request=request, item=item, origin=origin,
            reading_commit=r, output=output / item["thscode"],
            **({"recovery_request": recovery_request} if recovery_request is not None else {}))
        result["items"].append(outcome)
        result["unattempted_issuers"].remove(item["thscode"])
        if outcome["status"] not in {"VALIDATED_FUNNEL_CANDIDATE", "EXISTING_BASELINE_REUSED_NO_EXECUTION"}:
            result["status"] = "BATCH_INCOMPLETE"
        (output / "batch-receipt.json").write_bytes(once.raw(result))
        if outcome.get("mutation_uncertain"): break
    (output / "batch-receipt.json").write_bytes(once.raw(result))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--recover-sources", action="store_true")
    args = parser.parse_args(argv)
    once.require(os.environ.get("GITHUB_REPOSITORY") == once.REPO
        and os.environ.get("GITHUB_REF") == "refs/heads/main" and os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
        and os.environ.get("GITHUB_SHA") == args.code_commit, "untrusted Stock research host")
    once.require(not args.recover_sources or os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch",
                 "Stock source recovery requires explicit native dispatch")
    try:
        result = consume(api=GitHubAPI(os.environ["GH_TOKEN"], max_calls=1024), code=args.code_commit,
                         source_run_id=args.source_run_id, output=args.output, recover_sources=args.recover_sources)
    except Exception as exc:
        if args.output.is_dir() and not args.output.is_symlink():
            (args.output / "batch-failure.json").write_bytes(once.raw({
                "status": "BATCH_INCOMPLETE", "error_type": type(exc).__name__,
                "source_run_id": args.source_run_id, "automatic_retry": False, **reading.AUTHORITY}))
        print("STOCK_RESEARCH_INCOMPLETE: " + type(exc).__name__)
        return 2
    print(once.raw(result).decode())
    return 0 if result["status"] in {"COMPLETED", "NOT_A_STOCK_READING_RUN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
