"""Synthetic original-host tests for history/current input framing, NOT model quality.

Use the existing full-input fixture and deny-network SDK preview. No live
sources/provider, new production identity or rewriting of saved candidates.
"""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_host as host
from decision_kernel.runtime import stock_full_input as full
from decision_kernel.runtime import stock_full_input_bridge as bridge
from test_stock_full_input_bridge import setup_full, saved_binding


def setup_scoped(tmp_path, monkeypatch, *, mode="quick", defect=None):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode=mode)
    capture = args["capture"]
    def supplied(**kwargs):
        context, reads, process = capture(**kwargs)
        history = {"execution_id": args["item"]["execution_id"],
            "prefix": args["item"]["prefix"], "thscode": args["item"]["thscode"],
            "current_reading": {"ref": args["reading_commit"]},
            "successor_request": {"ref": args["code"]},
            "current_reading_item_status": "PRE_EXECUTION_FAILURE",
            "material": {"missing_page_reviews": [{"pdf_sha256": "f"*64,
                "pages": [{"page_number": 23,
                    "error_code": "required page visual review unavailable"}]}]}}
        # A deliberately synthetic historical field, not a new source/read event.
        if defect in ("execution_id", "prefix", "thscode"):
            history[defect] = "wrong"
        elif defect in ("current_reading", "successor_request"):
            history[defect]["ref"] = "d"*40
        elif defect == "malformed":
            history["current_reading"] = None
        context["source_successor"] = history
        return context, reads, process
    args["capture"] = supplied
    call = args["call"]
    seen = []
    def recorded(stage, prompt, *more):
        seen.append((stage, deepcopy(prompt)))
        return call(stage, prompt, *more)
    args["call"] = recorded
    return args, api, calls, captures, writes, contexts, seen


@pytest.mark.parametrize("mode,stages", [
    ("STOP", ["pre"]), ("WAIT_FOR_TRIGGER", ["pre"]), ("quick", ["pre", "quick"])])
def test_original_host_frames_history_without_changing_source_or_forcing_route(tmp_path, monkeypatch, mode, stages):
    args, api, calls, captures, writes, contexts, seen = setup_scoped(tmp_path, monkeypatch, mode=mode)
    result = host.run_item(**args)
    assert result["status"] == "VALIDATED_FUNNEL_CANDIDATE", result
    assert calls == stages and [s for s, _ in seen] == stages
    original = once.raw(contexts[0])
    assert len(original) > full.STORED_BYTES
    assert full.unpack((args["output"] / "source.json").read_bytes(), ticker="300711") == original
    scope = seen[0][1]["source_state_interpretation"]
    assert scope["current_request"]["execution_id"] == args["item"]["execution_id"]
    assert scope["current_request"]["context_sha256"] == once.sha(original)
    assert scope["current_request"]["meaning"] == "REQUEST_INPUT_IDENTITY_NOT_EXECUTION_STATUS"
    assert scope["supplied_material"]["document_count"] == 1
    assert scope["supplied_material"]["page_count"] == 1
    assert scope["supplied_material"]["selected_ids"] == ["synthetic-report"]
    assert scope["historical_fields"]["public_context.source_successor.current_reading_item_status"] == \
        "INHERITED_PREDECESSOR_SNAPSHOT_NOT_CURRENT_EXECUTION_STATUS"
    assert "SAVED_SOURCE_ONLY" in scope["historical_fields"]["public_context.source_successor.material"]
    assert "prompt construction does not attest" in scope["rules"]
    assert "no route is forced" in scope["rules"]
    for stage, prompt in seen:
        assert once.raw(prompt["public_context"]) == original
        assert prompt["source_state_interpretation"] == scope
        assert prompt["public_context"]["source_successor"]["current_reading_item_status"] == "PRE_EXECUTION_FAILURE"
        assert prompt["public_context"]["source_successor"]["material"]["missing_page_reviews"]
    preview = json.loads((args["output"] / "pre-request-preview.json").read_bytes())
    assert preview["prompt_sha256"] == once.sha(once.raw(seen[0][1]))
    packet, discovery, bound = saved_binding(args, api, contexts)
    built = once.pre_prompt(packet, discovery, contexts[0], bound_context=bound)
    assert once.raw(built) == once.raw(seen[0][1])
    # A repeated request is still blocked by the original create-only history.
    args["output"] = tmp_path / "repeat"
    assert host.run_item(**args)["status"] == "EXISTING_BASELINE_REUSED_NO_EXECUTION"
    assert calls == stages and len(captures) == 1


@pytest.mark.parametrize("defect", [
    "execution_id", "prefix", "thscode", "current_reading", "successor_request", "malformed"])
def test_bad_scope_binding_stops_before_launch_and_model(tmp_path, monkeypatch, defect):
    args, api, calls, captures, writes, contexts, seen = setup_scoped(tmp_path, monkeypatch, defect=defect)
    result = host.run_item(**args)
    assert result["status"] == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE", result
    assert result["error_code"] == "full input successor prompt identity differs"
    assert result["formal_research_started"] is False and calls == seen == []
    assert not (args["output"] / "launch.json").exists()
    assert not (args["output"] / "funnel.json").exists()


def test_unrelated_full_input_and_default_builder_remain_identical(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts = setup_full(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    default = once.pre_prompt(packet, discovery, contexts[0])
    bound_prompt = once.pre_prompt(packet, discovery, contexts[0], bound_context=bound)
    assert once.raw(default) == once.raw(bound_prompt)
    assert "source_state_interpretation" not in bound_prompt


def test_changed_complete_body_cannot_be_framed_as_bound(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts, seen = setup_scoped(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    changed = deepcopy(contexts[0])
    changed["issuer_documents"][0]["pages"][0]["text"] = "summary replacing required text"
    with pytest.raises(once.TrialError, match="full input plain context changed"):
        once.pre_prompt(packet, discovery, changed, bound_context=bound)


def test_unbound_source_cannot_supply_a_trusted_top_level_scope(tmp_path, monkeypatch):
    args, api, calls, captures, writes, contexts, seen = setup_scoped(tmp_path, monkeypatch, mode="STOP")
    assert host.run_item(**args)["status"] == "VALIDATED_FUNNEL_CANDIDATE"
    packet, discovery, bound = saved_binding(args, api, contexts)
    # No explicit bound object means the legacy prompt, not a guessed source PASS.
    prompt = once.pre_prompt(packet, discovery, contexts[0])
    assert "source_state_interpretation" not in prompt
    with pytest.raises(once.TrialError, match="explicit bound context"):
        once.pre_prompt(packet, discovery, contexts[0], bound_context=object())
