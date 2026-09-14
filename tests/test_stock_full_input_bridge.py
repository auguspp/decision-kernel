"""Original-host/admission/Funnel/SDK composition. ALL companies here are synthetic.

No live GitHub, source-site or model calls. Real SDK preview has a deny transport;
model tests install a separate deny transport. No SDK-absence skips.
"""
from copy import deepcopy
from dataclasses import replace
import json
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_full_input as full
from decision_kernel.runtime import stock_full_input_bridge as bridge
from test_stock_research_host import setup_host


def setup_full(tmp_path, monkeypatch, *, ticker="300711", mode="quick", fail=None):
    def deny(*args, **kwargs): pytest.fail("full-input test attempted network")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.delenv("SUB2API_API_KEY", raising=False)
    args, api, calls, captures, writes = setup_host(tmp_path, monkeypatch, mode=mode, fail=fail)
    code = ticker + (".SH" if ticker.startswith("6") else ".SZ")
    eid, prefix = intake.execution(code)
    args["item"].update(thscode=code, security_id=intake.security(code), execution_id=eid,
                         prefix=prefix, observation={"thscode": code, "eligible_for_shadow_reading": True})
    original_capture = args["capture"]
    contexts = []
    def capture(**kw):
        value, reads, process = original_capture(**kw)
        value["issuer_inventory"].update(stock_code=ticker, selected_ids=["synthetic-report"],
                                         checked_at=process["inventory_finished_at"])
        value["issuer_documents"][0].update(announcement_id="synthetic-report", page_count=1)
        value["issuer_documents"][0]["pages"][0]["text"] = "完整正文和反证。" * 26000
        contexts.append(value)
        return value, reads, process
    args.update(capture=capture, full_input=True)
    return args, api, calls, captures, writes, contexts


@pytest.mark.parametrize("ticker", ["300711", "603353"])
@pytest.mark.parametrize("mode,stages", [("STOP", ["pre"]), ("WAIT_FOR_TRIGGER", ["pre"]), ("quick", ["pre", "quick"])])
def test_original_host_stores_full_input_and_preserves_conditional_funnel(tmp_path, monkeypatch, ticker, mode, stages):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, ticker=ticker, mode=mode)
    result = host.run_item(**args)
    assert result["status"] == "VALIDATED_FUNNEL_CANDIDATE", result
    assert calls == stages and captures == [ticker]
    original = once.raw(contexts[0])
    stored = (args["output"] / "source.json").read_bytes()
    assert len(original) > 512 * 1024 and len(stored) <= 512 * 1024
    assert full.unpack(stored, ticker=ticker) == original
    launch = json.loads((args["output"] / "launch.json").read_bytes())
    preview = json.loads((args["output"] / "pre-request-preview.json").read_bytes())
    assert launch["pre_request_preview"] == preview
    assert 512 * 1024 < preview["request_bytes"] <= full.REQUEST_BYTES
    assert launch["full_input"]["stored_sha256"] == once.sha(stored)
    assert launch["full_input"]["decoded_sha256"] == once.sha(original)
    assert launch["full_input"]["stored_sha256"] != launch["full_input"]["decoded_sha256"]
    assert result["investment_authority"] == "NONE" and not result["registered_current_handoff"]
    before = deepcopy(api.files[api.heads[intake.WORK_REF]])
    args["output"] = tmp_path / "repeat"
    repeated = host.run_item(**args)
    assert repeated["status"] == "EXISTING_BASELINE_REUSED_NO_EXECUTION"
    assert before == api.files[api.heads[intake.WORK_REF]] and calls == stages and captures == [ticker]


def test_default_host_still_rejects_the_same_large_context(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch)
    args["full_input"] = False
    result = host.run_item(**args)
    assert result["status"] == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE", result
    assert not calls and not (args["output"] / "launch.json").exists()
    assert result["error_code"] == "full stock context too large; no clipping"


@pytest.mark.parametrize("defect", ["scope", "old-recovery", "bool", "old-history"])
def test_no_old_failure_recovery_or_other_issuer_activation(tmp_path, monkeypatch, defect):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch)
    if defect == "scope": args["item"]["thscode"] = "600184.SH"
    elif defect == "old-recovery": args["recovery_request"] = {}
    elif defect == "bool": args["full_input"] = 1
    else:
        api.heads[intake.WORK_REF] = args["code"]
        api.files[args["code"]][args["item"]["prefix"] + "failure.json"] = b"{}"
    if defect == "old-history":
        assert host.run_item(**args)["status"] == "EXISTING_BASELINE_REUSED_NO_EXECUTION"
    else:
        with pytest.raises(once.TrialError): host.run_item(**args)
    assert calls == captures == writes == []


def test_pre_request_capacity_failure_precedes_launch(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch)
    def reject(*args): raise once.TrialError("synthetic exact Pre request too large")
    monkeypatch.setattr(bridge, "preview_pre", reject)
    result = host.run_item(**args)
    assert result["status"] == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE", result
    assert not result["formal_research_started"] and not calls
    assert not (args["output"] / "launch.json").exists()
    assert (args["output"] / "failure.json").exists()


@pytest.mark.parametrize("defect", ["permission", "plain", "retained-source"])
def test_all_original_and_full_source_guards_recheck_before_quick(tmp_path, monkeypatch, defect):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch,
        fail="revoke_after_pre" if defect == "permission" else None)
    original_call = args["call"]
    def call(stage, prompt, *more):
        result = original_call(stage, prompt, *more)
        if stage == "pre" and defect == "plain":
            contexts[0]["issuer_documents"][0]["pages"][0]["text"] += "changed"
        if stage == "pre" and defect == "retained-source":
            packet = json.loads((args["output"] / "input.json").read_bytes())
            spec = next(s for s in packet["source_refs"] if s["purpose"] == "MODEL_CONTEXT")
            api.files[spec["ref"]][spec["path"]] = b"changed saved bytes"
        return result
    args["call"] = call
    result = host.run_item(**args)
    assert result["status"] == "VALIDATED_EXECUTION_GAP", result
    assert calls == ["pre"] and not (args["output"] / "quick.json").exists()
    assert not (args["output"] / "funnel.json").exists()


def saved_binding(args, api, contexts):
    packet = once.ExternalResearchInputPacket.model_validate(json.loads((args["output"] / "input.json").read_bytes()))
    candidate = json.loads((args["output"] / "candidate.json").read_bytes())
    discovery = once.DiscoveryInput.model_validate(candidate["discovery"])
    spec = next(s.model_dump(mode="json") for s in packet.source_refs if s.purpose == "MODEL_CONTEXT")
    bound = bridge.BoundFullContext.load(spec, lambda s: api.file(s["path"], s["ref"]), ticker=packet.ticker)
    preview = json.loads((args["output"] / "pre-request-preview.json").read_bytes())
    return packet, discovery, bound.prepared(preview)


@pytest.mark.parametrize("defect", ["source", "plain", "lane", "ticker", "seed", "constructor"])
def test_bound_context_cannot_substitute_a_different_packet_or_source(tmp_path, monkeypatch, defect):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    context = deepcopy(contexts[0]); data = packet.model_dump(mode="json")
    if defect == "source": data["source_refs"][0]["ref"] = "d" * 40
    elif defect == "plain": context["issuer_documents"][0]["pages"][0]["text"] = "summary"
    elif defect == "lane": data["source_lane"] = "OTHER"
    elif defect == "ticker": data["ticker"] = "603353"
    elif defect == "seed": data["seed_evidence_artifacts"][0]["content_hash"] = "0" * 64
    else: bound = replace(bound, stored_raw=b"{}")
    packet = once.ExternalResearchInputPacket.model_validate(data)
    with pytest.raises((ValueError, KeyError)):
        bound.check_packet(packet, context)


@pytest.mark.parametrize("stage", ["pre", "quick"])
def test_original_model_call_full_plain_wire_checked_before_fake_transport(tmp_path, monkeypatch, stage):
    import openai
    from openai import APIConnectionError
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch)
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    prompt = once.pre_prompt(packet, discovery, contexts[0])
    model = once.PreResearchResult
    if stage == "quick":
        pre = once.PreResearchResult.model_validate(json.loads((args["output"] / "pre.json").read_bytes()))
        assert pre.route.value == "CONTINUE_TO_QUICK"
        prompt.update(stage="QUICK", pre_research=pre.model_dump(mode="json"), pre_research_hash=once.canonical_hash(pre))
        model = once.QuickResearchResult
    original_client = openai.DefaultHttpxClient
    received, usage = [], []
    class DenyTransport:
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
        def close(self): pass
        def handle_request(self, request):
            assert usage[0]["pre_send"]["request_sha256"] == once.sha(request.content)
            received.append(request.content)
            raise OSError("intentional SDK fake-transport stop")
    monkeypatch.setattr(openai, "DefaultHttpxClient", lambda **kw: original_client(transport=DenyTransport(), **kw))
    monkeypatch.setenv("SUB2API_API_KEY", "synthetic-not-a-secret")
    output = tmp_path / "sdk"; output.mkdir()
    with pytest.raises(APIConnectionError):
        once.model_call(stage, prompt, model, output, usage, bound_context=bound)
    assert len(received) == 1 and usage[0]["response_received"] is False
    assert 512 * 1024 < usage[0]["pre_send"]["request_bytes"] <= full.REQUEST_BYTES
    actual = json.loads(received[0])
    assert once.raw(json.loads(actual["input"][0]["content"])["public_context"]) == once.raw(contexts[0])
    assert actual["instructions"] == once.SYSTEM and actual["tools"] == [] and actual["store"] is False
    if stage == "pre": assert once.sha(received[0]) == bound.pre_request_sha256


def test_plain_or_stored_identity_not_bypassed_by_full_input_flag(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    out = tmp_path / "default"; out.mkdir()
    def denied(*args): pytest.fail("unbound compressed context reached model")
    # The Retainer fixture advances its clock to a Git commit second. Use that
    # SAME clock here; research's definition-time default is the real clock.
    candidate, validation, usage = once.research(
        packet, discovery, contexts[0], out, call=denied, clock=args["clock"])
    assert candidate.completion.value == "INCOMPLETE_TECHNICAL_FAILURE" and not usage
    assert candidate.receipt.stop_or_failure_reason == "egress context changed"
    assert candidate.receipt.started_at == once.admission.clock(args["clock"]())
    assert candidate.receipt.started_at >= packet.research_cutoff
    assert validation.status.value == "EXECUTION_GAP" and validation.funnel_result is None
    prompt = once.pre_prompt(packet, discovery, contexts[0]); usage = []
    with pytest.raises(once.TrialError, match="missing pre-launch"):
        once.model_call("pre", prompt, once.PreResearchResult, tmp_path, usage,
                       bound_context=replace(bound, pre_request_sha256=None, pre_prompt_sha256=None))
    with pytest.raises(once.TrialError, match="cannot override"):
        once.model_call("pre", prompt, once.PreResearchResult, tmp_path, usage,
                       bound_context=bound, max_prompt_bytes=full.REQUEST_BYTES)
    assert not usage


def test_original_receipt_still_rejects_a_clock_before_frozen_cutoff(tmp_path, monkeypatch):
    from datetime import timedelta
    from pydantic import ValidationError

    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, _ = saved_binding(args, api, contexts)
    out = tmp_path / "before-cutoff"; out.mkdir()
    # Deterministically reproduce the unrelated clock failure without waiting
    # for real wall time or weakening the production Receipt validator.
    before_cutoff = (packet.research_cutoff - timedelta(seconds=1)).isoformat()
    def denied(*args): pytest.fail("unbound compressed context reached model")
    with pytest.raises(ValidationError, match="execution cannot start before the frozen research cutoff"):
        once.research(packet, discovery, contexts[0], out,
                      call=denied, clock=lambda: before_cutoff)
    assert not list(out.iterdir())


def capture_fixture(tmp_path, monkeypatch, defect=None):
    from decision_kernel.runtime import stock_research_sources as sources
    from test_stock_full_input import context as byte_context
    stamp = "2026-09-13T15:19:00+00:00"
    value = byte_context(text="完整正文和反证。" * 26000)
    value["issuer_inventory"]["checked_at"] = stamp
    selected = value["issuer_inventory"]["selected_ids"]
    calls, rechecks = [], []
    path = tmp_path / "capture"
    prepared = dict(inventory_checked=True, all_planned_bodies_inspected=True,
        selected_ids=selected, checked_body_ids=selected, unattempted_ids=[], missing_page_reviews=[],
        inventory_sha256=once.sha(once.raw(value["issuer_inventory"])),
        complete_context=dict(path="prepared-context.json", bytes=len(once.raw(value)), sha256=once.sha(once.raw(value))),
        status="PREPARATION_INCOMPLETE")
    reads = [{"identity": "300711:" + item, "succeeded": True, "checked_at": stamp} for item in selected]
    journal = dict(completed_reads=reads, started_at=stamp, finished_at=stamp,
        events=[{"status": "SUCCEEDED", "finished_at": stamp}], scope="SYNTHETIC CAPTURE FIXTURE", captured_pdf_bytes=17)
    def capture(**kw):
        calls.append(kw)
        assert kw["preparation_only"] is True
        path.mkdir()
        (path / "prepared-context.json").write_bytes(once.raw(value))
        (path / "source-journal.json").write_bytes(once.raw(journal))
        if defect == "missing": prepared["missing_page_reviews"] = [{"page_number": 23}]
        elif defect == "unattempted": prepared["unattempted_ids"] = ["missing"]
        elif defect == "hash": prepared["complete_context"]["sha256"] = "0" * 64
        elif defect == "path": prepared["complete_context"]["path"] = "../context.json"
        elif defect == "inventory": prepared["inventory_sha256"] = "0" * 64
        elif defect == "reads":
            journal["completed_reads"] = []
            (path / "source-journal.json").write_bytes(once.raw(journal))
        elif defect == "symlink":
            target = path / "source-journal.json"
            target.unlink(); target.symlink_to(path / "prepared-context.json")
        return prepared
    monkeypatch.setattr(sources, "capture", capture)
    monkeypatch.setattr(sources, "recheck", lambda context, **kw: rechecks.append((context, kw)))
    args = dict(ticker="300711", output=path, observation=value["stock_observation"],
        api=object(), code_commit="a" * 40, clock=lambda: stamp)
    return args, value, prepared, journal, calls, rechecks


def test_original_preparation_composition_preserves_all_bytes_and_source_clocks(tmp_path, monkeypatch):
    args, value, prepared, journal, calls, rechecks = capture_fixture(tmp_path, monkeypatch)
    result, reads, process = bridge.capture_complete(**args)
    assert once.raw(result) == once.raw(value)
    assert reads == journal["completed_reads"] and process["started_at"] == journal["started_at"]
    assert process["inventory_finished_at"] == value["issuer_inventory"]["checked_at"]
    assert len(calls) == 1 and len(rechecks) == 1 and prepared["status"] == "PREPARATION_INCOMPLETE"
    record = json.loads((args["output"] / "full-input-preparation.json").read_bytes())
    assert record["decoded_sha256"] == once.sha(once.raw(value))
    assert record["status"] == "COMPLETE_SOURCE_REPRESENTATION_NOT_EXECUTION_ADMISSION"


@pytest.mark.parametrize("defect", ["missing", "unattempted", "hash", "path", "inventory", "reads", "symlink"])
def test_incomplete_or_changed_preparation_is_not_promoted_by_storage(tmp_path, monkeypatch, defect):
    args, value, prepared, journal, calls, rechecks = capture_fixture(tmp_path, monkeypatch, defect)
    with pytest.raises((ValueError, KeyError)):
        bridge.capture_complete(**args)
    assert len(calls) == 1 and not rechecks
    assert not (args["output"] / "full-input-preparation.json").exists()


def test_changed_pre_prompt_is_rejected_before_sdk_or_output_retention(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    prompt = once.pre_prompt(packet, discovery, contexts[0]); prompt["question"] += "changed"
    usage = []; output = tmp_path / "changed"; output.mkdir()
    with pytest.raises(once.TrialError, match="Pre prompt changed after preview"):
        once.model_call("pre", prompt, once.PreResearchResult, output, usage, bound_context=bound)
    assert not usage and not list(output.iterdir())


def test_full_input_is_internal_not_a_new_cli_or_shared_numeric_limit(tmp_path):
    with pytest.raises(SystemExit):
        host.main(["--source-run-id", "1", "--code-commit", "a" * 40,
                   "--output", str(tmp_path / "no-run"), "--full-input"])
    assert not (tmp_path / "no-run").exists()
    assert host.STOCK_PROMPT_BYTES == once.identity.MAX_BYTES == 512 * 1024
    assert once.MAX_PROMPT_BYTES == 128 * 1024
