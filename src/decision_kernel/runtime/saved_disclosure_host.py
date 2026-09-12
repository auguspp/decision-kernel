"""Trusted host for existing saved scans -> original prepared Pre/Quick executor.

REUSE GitHub producer events, intake, preparation, admission and Retainer. No new
source requests, scheduler, provider, model loop, automatic Deep or promotion.
"""
from __future__ import annotations

import argparse
import os
import signal
from datetime import timedelta
from pathlib import Path

from ..research_funnel import DiscoveryInput
from . import current_state as read
from . import external_research_identity as identity
from . import incremental_disclosure as work
from . import incremental_disclosure_intake as intake
from . import saved_disclosure_preparation as preparation
from . import saved_research_once as once
from .current_state_delivery import GitHubAPI
from .external_research_execution import ExternalResearchInputPacket

RESOURCE_AUTHORIZATION = "https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5646037620"
# Known local format gaps may be retained while the original finite FIFO advances.
# Any unknown, transport, identity, admission, clock or model failure stops this batch.
LOCAL_SOURCE_GAPS = frozenset({"required body has no text", "required page text unavailable",
    "required text contains encoding damage", "required page visual review unavailable",
    "context exceeds saved executor bound; no clipping"})


def execute_prepared(*, api, prepared: dict, code_commit: str, output: Path, clock=once.now):
    from . import prepared_disclosure_research as executor
    source = prepared["input_source"]
    load = lambda s: api.file(s["path"], s["ref"])
    packet = ExternalResearchInputPacket.model_validate(identity._json(identity._checked_source(source, load)))
    refs = {s.purpose: s.model_dump(mode="json") for s in packet.source_refs}
    context = identity._json(identity._checked_source(refs["MODEL_CONTEXT"], load))
    discovery = DiscoveryInput.model_validate(identity._json(identity._checked_source(
        refs[preparation.DISCOVERY_PURPOSE], load)))
    # This trusted default-branch caller applies the actual Human resource grant
    # to a fixed, minimized public-data shape. A source string cannot approve itself.
    expected_keys = {"disclosure_packet", "source_limitations", "source_capture"}
    question, version = preparation.QUESTION, "saved-disclosure-preparation-v1"
    from . import disclosure_continuation as continuation
    if continuation.REQUEST_PURPOSE in refs:
        prior = continuation.check(api=api, code_commit=code_commit,
            request_source=refs[continuation.REQUEST_PURPOSE],
            new_packet_raw=identity._checked_source(refs[work.PACKET_PURPOSE], load), checked_at=clock())
        expected_keys.add("continuation_context")
        once.require(context.get("continuation_context") == prior["public_context"],
                     "continuation public context differs")
        question, version = prior["question"], "saved-disclosure-continuation-v1"
    once.require(set(context) == expected_keys and context["source_limitations"] == preparation.LIMITATIONS
                 and packet.research_question == question and packet.prompt_version == version,
                 "unsupported egress shape")
    from . import disclosure_source_reading as page_reading
    page_reading.validate_context(context,
        load_review=page_reading.main_review_loader(api, code_commit, clock))
    digest = executor.public_egress_hash(packet, discovery, context)
    return executor.run_prepared(api=api, code_commit=code_commit, input_source=source,
        expected_key=prepared["expected_key"], approved_egress_hash=digest, output=output, clock=clock)


def consume(*, api, source_run_id: int, code_commit: str, output: Path,
            clock=once.now, execute=execute_prepared, reserve=intake.intake,
            prepare=preparation.prepare_reserved, new_question_api=None, continuation_request_source=None) -> dict:
    """Consume a finite existing scan, serially; no retry/catch-up/new source scan.

    This is not a daily call quota. The existing scan's actual packet denominator
    limits this invocation. New source events may invoke it again, but reserved
    keys (including failures) are never relaunched by this host.
    """
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "unsafe output")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "BATCH_INCOMPLETE", "started_at": clock(), "items": [],
               "source_run_id": source_run_id, "code_commit": code_commit,
               "resource_authorization": RESOURCE_AUTHORIZATION, "daily_provider_quota": None,
               "automatic_retry": False, "semantic_acceptance": "NOT_ESTABLISHED", **read.AUTHORITY}
    clients = [api]
    try:
        once.require(type(source_run_id) is int and source_run_id > 0, "invalid source run")
        once.require(intake.mutable_ref(api, "main") == code_commit, "main moved")
        run = api.get("actions/runs/" + str(source_run_id))
        read.run_identity(run, "inbox", success=True)
        once.require(run["id"] == source_run_id, "source run differs")
        items = api.get(f"actions/runs/{source_run_id}/artifacts?per_page=100")
        once.require(items["total_count"] == len(items["artifacts"]) <= 100, "artifact inventory incomplete")
        def selected(name):
            matches = [a for a in items["artifacts"] if a["name"] == name]
            once.require(len(matches) == 1, "saved artifact missing or ambiguous")
            return matches[0]
        scan_artifact = selected("official-disclosure-scan")
        body_artifact = selected("official-disclosure-primary-bodies")
        scan_raw, body_raw = api.archive(scan_artifact), api.archive(body_artifact)
        for name, value in {"source-run.json": once.raw(run), "scan-artifact.json": once.raw(scan_artifact),
                            "body-artifact.json": once.raw(body_artifact), "scan.zip": scan_raw,
                            "bodies.zip": body_raw}.items():
            (output / name).write_bytes(value)
        # Fail the shared source set before reserving a new key if its capture is damaged.
        preparation.captured_bodies(archive_raw=body_raw, artifact=body_artifact, run=run)
        reading_commit = intake.mutable_ref(api, read.READ_REF)
        receipt["reading_commit"] = reading_commit
        target_key = None
        if continuation_request_source is not None:
            from . import disclosure_continuation as continuation
            spec = continuation_request_source
            request = identity._json(identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"])))
            target_key = request["new_assessment_input_hash"]
            scan_files = read.unpack_archive(scan_raw, scan_artifact, run)
            targets = [raw for path, raw in scan_files.items() if path.startswith("disclosure-assessment-packets/")
                       and work._packet(raw).assessment_input_hash == target_key]
            once.require(len(targets) == 1, "continuation target absent or ambiguous in saved scan")
            continuation.check(api=api, code_commit=code_commit, request_source=spec,
                               new_packet_raw=targets[0], checked_at=clock())
            receipt["continuation_request_source"] = spec
        for index in range(work.MAX_PACKETS):
            # One original bounded GitHub client per independent work unit.
            # Never reset a client inside an attempt or after an uncertain failure.
            # Collector limits are unchanged; these are not daily provider quotas.
            if new_question_api is not None:
                api = new_question_api()
                clients.append(api)
            w = intake.mutable_ref(api, work.WORK_REF)
            _, files = intake.work_inventory(api, w)
            plan = work.plan_one(archive_raw=scan_raw, artifact=scan_artifact, run=run,
                                 work_files=files, work_commit=w, selected_at=clock())
            (output / f"plan-{index}.json").write_bytes(once.raw(plan))
            if index == 0:
                if target_key is not None:
                    target_rows = [r for r in plan["dispositions"] if r.get("assessment_input_hash") == target_key]
                    once.require(len(target_rows) == 1 and target_rows[0]["status"] in {
                        "DEFERRED_CAPACITY", "SELECTED_REQUIRES_RESERVATION_AND_ORIGINAL_ADMISSION"},
                        "continuation target already attempted or not eligible")
                receipt["initial_plan_hash"] = plan["plan_hash"]
                receipt["packet_count"] = plan["packet_count"]
            if plan["selected"] is None:
                once.require(target_key is None, "continuation target not reached")
                receipt["status"] = plan["status"]
                break
            chosen = plan["selected"]
            directory = output / chosen["assessment_input_hash"]
            request = {"schema_version": 1, "source_run_id": source_run_id,
                "artifact_id": scan_artifact["id"], "expected_work_commit": w,
                "expected_key": chosen["assessment_input_hash"],
                "expected_packet_sha256": chosen["packet_sha256"],
                "expires_at": (read.clock(clock()) + timedelta(minutes=15)).isoformat()}
            retained = reserve(api=api, request=request, code_commit=code_commit,
                               output=directory / "intake", now=clock)
            once.require(retained["status"] == "RESERVED_EXACT_BYTES_NOT_RESEARCH", "reservation not new")
            original = api.file(retained["packet_path"], retained["reservation_commit"])
            source = once.source_ref(retained["packet_path"], retained["reservation_commit"], original, work.PACKET_PURPOSE)
            continuation_args = {"continuation_request_source": continuation_request_source} if chosen["assessment_input_hash"] == target_key else {}
            prepared = prepare(api=api, code_commit=code_commit, packet_source=source, scan_raw=scan_raw,
                scan_artifact=scan_artifact, body_raw=body_raw, body_artifact=body_artifact, run=run,
                reading_commit=reading_commit, output=directory / "preparation", clock=clock, **continuation_args)
            record = {"assessment_input_hash": chosen["assessment_input_hash"],
                      "preparation_status": prepared["status"], "research_status": "NOT_EXECUTED"}
            receipt["items"].append(record)
            if prepared["status"] != "INPUT_PREPARED_NOT_EXECUTED":
                record["error_code"] = prepared.get("error_code")
                once.require(chosen["assessment_input_hash"] != target_key
                             and not prepared["mutation_uncertain"] and prepared.get("error_code") in LOCAL_SOURCE_GAPS,
                             "preparation failure stops batch")
                continue
            result = execute(api=api, prepared=prepared, code_commit=code_commit,
                             output=directory / "execution", clock=clock)
            record["research_status"] = result["status"]
            once.require(result["status"] == "VALIDATED_FUNNEL_RESULT" and not result["mutation_uncertain"],
                         "Research or retention failure stops batch")
            if chosen["assessment_input_hash"] == target_key:
                receipt["status"] = "EXPLICIT_CONTINUATION_CANDIDATE_RETAINED"
                break
        else:
            receipt["status"] = "FINITE_SCAN_PASS_COMPLETED"
    except Exception as exc:
        receipt.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", None))
    finally:
        receipt["finished_at"] = clock()
        receipt["github_client_calls"] = [getattr(client, "calls", None) for client in clients]
        receipt["github_accounting_scope"] = "Original per-client GET budget; native create-only writes are in intake/Retainer receipts, not this counter"
        (output / "batch-receipt.json").write_bytes(once.raw(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--continuation", action="store_true")
    args = parser.parse_args(argv)
    once.require(os.environ.get("GITHUB_RUN_ATTEMPT") == "1"
                 and os.environ.get("GITHUB_REF") == "refs/heads/main", "main attempt1 only")
    # Reuse the original one-shot SIGALRM pattern for EACH question, not a
    # daily quota. The finite scan and workflow timeout bound the whole batch.
    def timed_out(*_): raise TimeoutError("saved question wall limit")
    signal.signal(signal.SIGALRM, timed_out)
    def bounded_execute(**kwargs):
        signal.alarm(15 * 60)
        try:
            return execute_prepared(**kwargs)
        finally:
            signal.alarm(0)
    try:
        api = GitHubAPI(os.environ["GH_TOKEN"])
        continuation_source = None
        if args.continuation:
            from . import disclosure_continuation as continuation
            raw = api.file(continuation.REQUEST_PATH, args.code_commit)
            continuation_source = once.source_ref(continuation.REQUEST_PATH, args.code_commit, raw,
                                                   continuation.REQUEST_PURPOSE)
        result = consume(api=api, source_run_id=args.source_run_id,
                         code_commit=args.code_commit, output=args.output, execute=bounded_execute,
                         new_question_api=lambda: GitHubAPI(os.environ["GH_TOKEN"]),
                         continuation_request_source=continuation_source)
        print(result["status"])
        return 2 if result["status"] == "BATCH_INCOMPLETE" else 0
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    raise SystemExit(main())