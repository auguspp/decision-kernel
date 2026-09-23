"""No live calls: historical bytes and explicitly synthetic new outcome cases."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import socket
from uuid import UUID

import pytest
from pydantic import ValidationError

from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.runtime.external_research_execution import (
    ExternalResearchCandidate, ExternalResearchInputPacket, ResearchExecutionReceipt,
)
from decision_kernel.runtime.single_quick_contract import (
    METHOD_VERSION, PROMPT_VERSION, FullResearchHandoff, Investigation,
    QuickAssessment, SingleQuickCandidate, SingleQuickValidation,
    build_full_handoff, read_saved_result, reading_view, validate_single_quick,
    verify_full_handoff,
)

FIXTURE = Path(__file__).parent / "fixtures/industry_quick_contract_20260923"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("contract tests must not acquire sources or call a provider")
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)


def raw(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def historical():
    return (FIXTURE / "input.json").read_bytes(), (FIXTURE / "candidate.json").read_bytes()


def synthetic(route="FULL_CANDIDATE"):
    input_raw, candidate_raw = historical()
    data = json.loads(input_raw)
    data.update(method_version=METHOD_VERSION, prompt_version=PROMPT_VERSION)
    packet = ExternalResearchInputPacket.model_validate(data)
    discovery = json.loads(candidate_raw)["discovery"]
    eid = str(packet.seed_evidence_artifacts[0].id)
    locator = packet.seed_evidence_artifacts[0].source_locator
    began = packet.research_cutoff + timedelta(seconds=1)
    receipt = ResearchExecutionReceipt(
        execution_id=packet.execution_id, input_hash=canonical_hash(packet),
        started_at=began, finished_at=began + timedelta(seconds=3),
        research_cutoff=packet.research_cutoff, completion="COMPLETE",
        tool_events=tuple({"sequence": i, "kind": "OTHER_READ", "status": "SUCCEEDED",
            "target": target, "observed_at": began + timedelta(seconds=i),
            "record_kind": "EXECUTOR_ACTION_SUMMARY"} for i, target in enumerate(
                [locator, "SYNTHETIC_PROVIDER:QUICK"], 1)),
        source_dispositions=({"source_locator": locator, "opened": True,
            "used_as_evidence": True, "evidence_artifact_id": eid,
            "disposition": "SYNTHETIC test context, not a new company execution"},),
        tool_calls_used=2, source_reads_used=2, search_queries_used=0,
        technical_retries_used=0, elapsed_minutes_observed=1,
        last_completed_stage="QUICK", model_or_executor="SYNTHETIC_NO_NETWORK",
    )
    assessment = QuickAssessment(
        explanation="SYNTHETIC：有来源的观察形成公司现金问题；不是实际公司结论。",
        claims=({"statement": "SYNTHETIC source-backed observation", "kind": "FACT",
                 "evidence_artifact_ids": [eid]},
                {"statement": "SYNTHETIC alternative explanation", "kind": "INFERENCE"}),
        counterevidence_review="SYNTHETIC：检查了给定范围；未建立相反事实不代表证伪已排除。",
        unknowns=("SYNTHETIC 尚未解释的差异",), route=route,
        route_reason="SYNTHETIC reason, not a repaired historical route",
        investigation=Investigation(question="SYNTHETIC差异是否来自期限错配？",
            why_material="SYNTHETIC不同归因影响现金判断。",
            available_work="SYNTHETIC核对已有附注与跨期口径。",
            decision_test="SYNTHETIC若只是期限错配，否定最初的经营恶化解释。")
            if route == "FULL_CANDIDATE" else None,
        wait_trigger="SYNTHETIC下一次尚未发布的定期报告" if route == "WAIT_FOR_TRIGGER" else None,
    )
    candidate = SingleQuickCandidate(input_hash=canonical_hash(packet), completion="COMPLETE",
        discovery=discovery, assessment=assessment, receipt=receipt,
        explicit_action_summary=("Synthetic result only; not retained issuer research",))
    return packet, candidate


def spec(packet, name, data, purpose):
    return {"repository": "auguspp/decision-kernel", "ref": "a" * 40,
        "path": packet.candidate_output_prefix + name,
        "git_blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(), "purpose": purpose}


def handoff_args(route="FULL_CANDIDATE"):
    packet, candidate = synthetic(route)
    inp, out = raw(packet), raw(candidate)
    return dict(input_raw=inp, candidate_raw=out,
        input_source=spec(packet, "input.json", inp, "SINGLE_QUICK_INPUT"),
        candidate_source=spec(packet, "candidate.json", out, "SINGLE_QUICK_CANDIDATE"))


def test_historical_gap_pre_hash_and_bytes_are_unchanged():
    inp, out = historical()
    before = (inp, out)
    packet, candidate, result = read_saved_result(inp, out)
    assert isinstance(candidate, ExternalResearchCandidate)
    assert result.status.value == "EXECUTION_GAP"
    assert result.candidate_hash == "fb7890f96979320d492f235caa215e3d1e0ef955cb21addf53d7debb7e2540da"
    assert canonical_hash(candidate.pre_research) == "cbe003b6122f6897da19f5fc47d2bb82b14d906eec38276d5aeab485c2ed772e"
    assert reading_view(inp, out)["pre_state"] == "PRESENT"
    assert historical() == before


@pytest.mark.parametrize("route,terminal", [("STOP", "DROP_FOR_NOW"),
    ("WAIT_FOR_TRIGGER", "WAIT_FOR_TRIGGER"), ("FULL_CANDIDATE", "DEEPEN_REQUIRED")])
def test_complete_new_results_need_no_pre_and_project_all_routes(route, terminal):
    packet, candidate = synthetic(route)
    result = validate_single_quick(packet=packet, candidate=candidate)
    view = reading_view(raw(packet), raw(candidate))
    assert result.status == view["status"] == "VALIDATED_QUICK_RESULT"
    assert result.terminal_state.value == view["terminal_state"] == terminal
    assert view["pre_state"] == "NOT_APPLICABLE" and view["explanation"]
    assert "pre_research" not in candidate.model_dump()
    assert "pre_research_hash" not in raw(candidate).decode()
    assert view["new_research_execution"] == "NOT_EXECUTED"
    assert view["semantic_acceptance"] == "NOT_ESTABLISHED_BY_READER"


def test_full_candidate_allows_inference_no_variant_and_no_forced_counterfact():
    packet, candidate = synthetic()
    assert candidate.assessment.claims[1].kind.value == "INFERENCE"
    assert "variant_perception" not in QuickAssessment.model_fields
    assert validate_single_quick(packet=packet, candidate=candidate).terminal_state.value == "DEEPEN_REQUIRED"


@pytest.mark.parametrize("damage", ["no_investigation", "no_source_observation", "blank_work", "blank_materiality"])
def test_unknown_alone_does_not_satisfy_full_shape(damage):
    _, candidate = synthetic()
    value = candidate.assessment.model_dump(mode="json")
    if damage == "no_investigation": value["investigation"] = None
    elif damage == "no_source_observation": value["claims"] = value["claims"][1:]
    elif damage == "blank_work": value["investigation"]["available_work"] = " \n"
    else: value["investigation"]["why_material"] = " "
    with pytest.raises(ValidationError): QuickAssessment.model_validate(value)


def test_wait_requires_trigger_but_does_not_require_an_unknown_quota():
    _, candidate = synthetic("WAIT_FOR_TRIGGER")
    value = candidate.assessment.model_dump(mode="json")
    value["unknowns"] = []
    assert QuickAssessment.model_validate(value).unknowns == ()
    value["wait_trigger"] = None
    with pytest.raises(ValidationError): QuickAssessment.model_validate(value)


@pytest.mark.parametrize("completion", ["INCOMPLETE_SOURCE", "INCOMPLETE_BUDGET", "INCOMPLETE_TECHNICAL_FAILURE"])
def test_gaps_are_visible_without_a_business_route(completion):
    packet, candidate = synthetic()
    value = candidate.model_dump(mode="json")
    value.update(completion=completion, assessment=None)
    value["receipt"].update(completion=completion, stop_or_failure_reason="SYNTHETIC_GAP")
    parsed = SingleQuickCandidate.model_validate(value)
    view = reading_view(raw(packet), raw(parsed))
    assert view["status"] == "EXECUTION_GAP" and view["gap_reason"] == "SYNTHETIC_GAP"
    assert view["terminal_state"] is view["terminal_reason"] is None
    assert view["pre_state"] == "NOT_APPLICABLE"
    value["assessment"] = candidate.assessment.model_dump(mode="json")
    with pytest.raises(ValidationError): SingleQuickCandidate.model_validate(value)


@pytest.mark.parametrize("field", ["pre_research", "pre_research_hash", "quick_research"])
def test_new_contract_rejects_virtual_or_mixed_pre_fields(field):
    packet, candidate = synthetic()
    value = candidate.model_dump(mode="json")
    value[field] = None
    with pytest.raises(ValidationError): read_saved_result(raw(packet), raw(value))


def test_legacy_missing_pre_does_not_become_legal():
    inp, out = historical()
    value = json.loads(out)
    value.update(completion="COMPLETE", pre_research=None)
    value["receipt"]["completion"] = "COMPLETE"
    with pytest.raises(ValidationError): read_saved_result(inp, raw(value))


@pytest.mark.parametrize("method,version", [("research-funnel-v1", 2),
    (METHOD_VERSION, 1), ("future-method", 2), (METHOD_VERSION, 3), (METHOD_VERSION, True)])
def test_unknown_or_mixed_versions_are_not_guessed(method, version):
    packet, candidate = synthetic()
    inp, out = packet.model_dump(mode="json"), candidate.model_dump(mode="json")
    inp["method_version"], out["schema_version"] = method, version
    with pytest.raises((DomainValidationError, ValidationError)):
        read_saved_result(raw(inp), raw(out))


def test_new_version_must_be_explicit_and_duplicate_json_keys_rejected():
    packet, candidate = synthetic()
    value = candidate.model_dump(mode="json")
    del value["schema_version"]
    with pytest.raises(DomainValidationError): read_saved_result(raw(packet), raw(value))
    duplicate = raw(candidate).replace(b'"schema_version": 2', b'"schema_version": 2, "schema_version": 2')
    with pytest.raises(DomainValidationError): read_saved_result(raw(packet), duplicate)


@pytest.mark.parametrize("damage", ["input_hash", "receipt_hash", "lineage", "claim", "budget", "cutoff", "security"])
def test_original_identity_lineage_budget_checks_are_reused(damage):
    packet, candidate = synthetic()
    value = candidate.model_dump(mode="json")
    if damage == "input_hash": value["input_hash"] = "0" * 64
    elif damage == "receipt_hash": value["receipt"]["input_hash"] = "0" * 64
    elif damage == "lineage": value["discovery"]["source_lineage"][0]["source_locator"] += "/wrong"
    elif damage == "claim": value["assessment"]["claims"][0]["evidence_artifact_ids"] = [str(UUID(int=123))]
    elif damage == "budget":
        data = packet.model_dump(mode="json")
        data["budget"]["max_tool_calls"] = 1
        packet = ExternalResearchInputPacket.model_validate(data)
        value["input_hash"] = value["receipt"]["input_hash"] = canonical_hash(packet)
    elif damage == "cutoff": value["discovery"]["as_of"] = (packet.research_cutoff + timedelta(seconds=1)).isoformat()
    else: value["discovery"]["security_id"] = "SSE:999999"
    with pytest.raises((ValidationError, DomainValidationError)):
        validate_single_quick(packet=packet, candidate=SingleQuickCandidate.model_validate(value))


def test_model_copy_cannot_bypass_new_contract_checks():
    packet, candidate = synthetic()
    bad = candidate.model_copy(update={"assessment": None})
    with pytest.raises(ValidationError): validate_single_quick(packet=packet, candidate=bad)
    bad_packet = packet.model_copy(update={"prompt_version": "unapproved-prompt"})
    with pytest.raises(DomainValidationError): validate_single_quick(packet=bad_packet, candidate=candidate)


def test_single_validation_cannot_gain_authority_or_mix_gap_with_route():
    packet, candidate = synthetic()
    value = validate_single_quick(packet=packet, candidate=candidate).model_dump(mode="json")
    with pytest.raises(ValidationError): SingleQuickValidation.model_validate({**value, "investment_authority": "BUY"})
    with pytest.raises(ValidationError): SingleQuickValidation.model_validate({**value, "status": "EXECUTION_GAP", "gap_reason": "x"})


def test_full_handoff_binds_real_bytes_but_does_not_authorize_execution():
    args = handoff_args()
    before = deepcopy(args)
    result = build_full_handoff(**args)
    assert result.origin == "QUICK_RESEARCH_CANDIDATE"
    assert result.execution_authority == result.investment_authority == "NONE"
    assert result.proposed_investigation.decision_test
    assert verify_full_handoff(result, input_raw=args["input_raw"], candidate_raw=args["candidate_raw"]) == result
    assert args == before


@pytest.mark.parametrize("route", ["STOP", "WAIT_FOR_TRIGGER"])
def test_nonfull_results_remain_readable_but_do_not_make_full_commissions(route):
    args = handoff_args(route)
    assert reading_view(args["input_raw"], args["candidate_raw"])["explanation"]
    with pytest.raises(DomainValidationError): build_full_handoff(**args)


@pytest.mark.parametrize("damage", ["raw", "path", "purpose", "hash", "security", "mandate", "unknowns"])
def test_handoff_tampering_is_rejected(damage):
    args = handoff_args()
    if damage in {"raw", "path", "purpose"}:
        if damage == "raw": args["candidate_raw"] += b" "
        elif damage == "path": args["candidate_source"]["path"] = "research_runs/candidates/other/candidate.json"
        else: args["input_source"]["purpose"] = "UNRELATED"
        with pytest.raises(DomainValidationError): build_full_handoff(**args)
        return
    result = build_full_handoff(**args)
    value = result.model_dump(mode="json")
    if damage == "hash": value["candidate_hash"] = "0" * 64
    elif damage == "security": value["security_id"] = "SSE:999999"
    elif damage == "mandate": value["proposed_investigation"]["question"] = "another question"
    else: value["open_unknowns"] = []
    with pytest.raises(DomainValidationError):
        verify_full_handoff(FullResearchHandoff.model_validate(value),
            input_raw=args["input_raw"], candidate_raw=args["candidate_raw"])
