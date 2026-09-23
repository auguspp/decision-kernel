"""Original executor/SDK with one new Quick; no live model or production proof."""
from copy import deepcopy
import json
import socket
from uuid import UUID

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_saved_research_once import fixture, pre
from test_saved_research_raw_retention import mock_stream


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("single Quick tests cannot open a network connection")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def case():
    packet, discovery, context = fixture()
    packet = ExternalResearchInputPacket.model_validate({**packet.model_dump(mode="json"),
        "method_version": single.METHOD_VERSION, "prompt_version": single.PROMPT_VERSION})
    return packet, discovery, context


def assessment(prompt, route="WAIT_FOR_TRIGGER"):
    return single.QuickAssessment(explanation="Synthetic company question, not real issuer Research.",
        claims=[{"kind": "FACT", "statement": "The synthetic source contains an observation.",
                 "evidence_artifact_ids": prompt["evidence_ids"]},
                {"kind": "INFERENCE", "statement": "A competing explanation remains possible.",
                 "evidence_artifact_ids": []}],
        counterevidence_review="Synthetic adverse evidence and alternatives inspected; external material not checked.",
        unknowns=["The future observation is not yet available."], route=route,
        route_reason="Synthetic scoped disposition, not an investment judgment.",
        wait_trigger="A specified future disclosure" if route == "WAIT_FOR_TRIGGER" else None,
        investigation={"question": "Can the current source distinguish profit from cash?",
                       "why_material": "It may change the causal explanation.",
                       "available_work": "Reconcile the already supplied cash and profit notes.",
                       "decision_test": "A funding-only explanation would refute the operating thesis."}
            if route == "FULL_CANDIDATE" else None)


@pytest.mark.parametrize("route,terminal", [("STOP", "DROP_FOR_NOW"),
    ("WAIT_FOR_TRIGGER", "WAIT_FOR_TRIGGER"), ("FULL_CANDIDATE", "DEEPEN_REQUIRED")])
def test_one_call_uses_original_loop_and_retains_all_outcomes(tmp_path, route, terminal):
    packet, discovery, context = case(); calls = []
    def call(stage, prompt, model, output, usage):
        calls.append((stage, deepcopy(prompt), model))
        assert model is single.QuickAssessment
        return assessment(prompt, route)
    candidate, checked, usage = once.research(packet, discovery, context, tmp_path, call=call)
    assert [row[0] for row in calls] == ["quick"]
    assert calls[0][1]["public_context"] == context
    assert not {"pre_research", "pre_research_hash"} & set(calls[0][1])
    assert candidate.schema_version == 2 and not hasattr(candidate, "pre_research")
    assert checked.status == "VALIDATED_QUICK_RESULT" and checked.terminal_state.value == terminal
    assert candidate.receipt.tool_calls_used == 2 and candidate.receipt.technical_retries_used == 0
    assert not list(tmp_path.glob("pre*"))
    assert json.loads((tmp_path / "candidate-before-validation.json").read_text()) == candidate.model_dump(mode="json")
    assert single.reading_view(once.raw(packet), once.raw(candidate))["pre_state"] == "NOT_APPLICABLE"
    assert (tmp_path / "quick-before-validation.json").exists()


@pytest.mark.parametrize("damage", ["method", "prompt", "security", "clock", "lineage", "budget", "context"])
def test_known_input_failures_spend_zero_calls(tmp_path, damage):
    packet, discovery, context = case(); calls = []
    if damage == "method": packet = packet.model_copy(update={"method_version": "unknown-method"})
    elif damage == "prompt": packet = packet.model_copy(update={"prompt_version": "unapproved"})
    elif damage == "security": discovery = discovery.model_copy(update={"security_id": "wrong"})
    elif damage == "clock":
        from datetime import timedelta
        discovery = discovery.model_copy(update={"as_of": discovery.as_of + timedelta(seconds=1)})
    elif damage == "lineage":
        discovery = discovery.model_copy(update={"source_lineage": (discovery.source_lineage[0].model_copy(
            update={"source_locator": "https://invalid.example/changed"}),)})
    elif damage == "budget": packet = packet.model_copy(update={"budget": packet.budget.model_copy(update={"max_tool_calls": 1})})
    else: context["unexpected_private_note"] = "not approved for egress"
    def call(*args): calls.append(args); pytest.fail("must not call model")
    if damage == "context":
        candidate, checked, _ = once.research(packet, discovery, context, tmp_path, call=call)
        assert checked.status == "EXECUTION_GAP" and candidate.assessment is None
    else:
        with pytest.raises(ValueError): once.research(packet, discovery, context, tmp_path, call=call)
    assert calls == []


@pytest.mark.parametrize("defect", ["json", "missing", "route", "extra", "no-trigger", "no-commission", "foreign-evidence"])
def test_original_sdk_saves_first_rejected_output_without_retry(tmp_path, monkeypatch, defect):
    packet, discovery, context = case(); prompt = once.initial_prompt(packet, discovery, context)
    value = assessment(prompt).model_dump(mode="json")
    if defect == "missing": del value["explanation"]
    elif defect == "route": value["route"] = "BUY"
    elif defect == "extra": value["position_size"] = "20%"
    elif defect == "no-trigger": value["wait_trigger"] = None
    elif defect == "no-commission": value.update(route="FULL_CANDIDATE", investigation=None)
    elif defect == "foreign-evidence": value["claims"][0]["evidence_artifact_ids"] = ["11111111-1111-4111-8111-111111111111"]
    text = '{"route":' if defect == "json" else json.dumps(value)
    calls, _ = mock_stream(monkeypatch, lambda _: text)
    candidate, checked, usage = once.research(packet, discovery, context, tmp_path)
    assert len(calls) == len(usage) == 1 and usage[0]["stage"] == "quick"
    assert checked.status == "EXECUTION_GAP" and candidate.assessment is None
    assert checked.terminal_state is None and candidate.receipt.technical_retries_used == 0
    assert (tmp_path / "quick-model-output.txt").read_text() == text
    assert usage[0]["output_text_retained"] and usage[0]["usage"]["total_tokens"] == 2
    assert not list(tmp_path.glob("pre*"))
    saved = "\n".join(p.read_text() for p in tmp_path.iterdir())
    assert "PRIVATE_REASONING_NOT_RETAINED" not in saved and "synthetic-only" not in saved


def test_transport_failure_remains_uncertain_output_not_business_wait(tmp_path, monkeypatch):
    packet, discovery, context = case()
    calls, _ = mock_stream(monkeypatch, lambda p: assessment(p).model_dump_json(), fail=True)
    candidate, checked, usage = once.research(packet, discovery, context, tmp_path)
    assert len(calls) == 1 and checked.status == "EXECUTION_GAP"
    assert candidate.assessment is None and not usage[0]["output_text_retained"]
    assert not (tmp_path / "quick-model-output.txt").exists()
    assert "SECRET_TRANSPORT_EXCEPTION" not in candidate.model_dump_json() + json.dumps(usage)


def test_unvalidated_model_copy_cannot_publish_a_route(tmp_path):
    packet, discovery, context = case()
    def call(stage, prompt, *args):
        return assessment(prompt).model_copy(update={"wait_trigger": None})
    candidate, checked, _ = once.research(packet, discovery, context, tmp_path, call=call)
    assert checked.status == "EXECUTION_GAP" and candidate.assessment is None
    assert json.loads((tmp_path / "quick-before-validation.json").read_text())["wait_trigger"] is None


@pytest.mark.parametrize("damage", ["pre-field", "pre-hash", "old-stage", "old-method", "old-prompt"])
def test_new_schema_rejects_hidden_pre_or_mixed_wire_before_sdk(tmp_path, damage):
    packet, discovery, context = case(); prompt = once.initial_prompt(packet, discovery, context)
    if damage == "pre-field": prompt["pre_research"] = {}
    elif damage == "pre-hash": prompt["pre_research_hash"] = "a" * 64
    elif damage == "old-stage": prompt["stage"] = "PRE"
    elif damage == "old-method": prompt["method_version"] = "research-funnel-v1"
    else: prompt["prompt_version"] = "test"
    with pytest.raises(ValueError, match="SINGLE_QUICK_WIRE_CONTRACT"):
        once.model_request(prompt, single.QuickAssessment, max_prompt_bytes=once.MAX_PROMPT_BYTES)


def test_evidence_whitelist_and_route_conditions_reach_actual_sdk_format():
    packet, discovery, context = case(); prompt = once.initial_prompt(packet, discovery, context)
    body, schema, fmt, parameters = once.model_request(prompt, single.QuickAssessment,
        max_prompt_bytes=once.MAX_PROMPT_BYTES)
    allowed = schema["$defs"]["ResearchClaim"]["properties"]["evidence_artifact_ids"]["items"]["enum"]
    assert allowed == prompt["evidence_ids"]
    assert "FULL_CANDIDATE" in fmt["schema"]["properties"]["route"]["description"]
    assert not {"pre_research", "pre_research_hash"} & set(fmt["schema"]["properties"])
    assert parameters["tools"] == [] and parameters["store"] is False
    assert parameters["max_output_tokens"] == once.MAX_OUTPUT_TOKENS == 6000


def test_legacy_first_prompt_and_result_contract_are_unchanged(tmp_path):
    packet, discovery, context = fixture(); calls = []
    assert once.raw(once.initial_prompt(packet, discovery, context)) == once.raw(once.pre_prompt(packet, discovery, context))
    def call(stage, prompt, *args): calls.append(stage); return pre(prompt)
    candidate, checked, _ = once.research(packet, discovery, context, tmp_path, call=call)
    assert calls == ["pre"] and checked.status.value == "VALIDATED_FUNNEL_RESULT"
    assert candidate.schema_version == 1 and candidate.pre_research is not None


def test_original_admission_refusal_cannot_reach_new_loop(monkeypatch):
    calls = []
    monkeypatch.setattr(once.admission, "assess_admission", lambda **_: {
        "research_execution_allowed": False, "reason": "SOURCE_PREFLIGHT_INCOMPLETE"})
    report, result = once.admission.execute_after_admission(executor=lambda *_: calls.append(1), input_raw=b"{}")
    assert not calls and result is None and report["research_execution_allowed"] is False
