"""Validate the exact, explicitly incomplete v2 record; never certify Research completion."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.external_research_execution import (
    ExternalResearchCandidate,
    ExternalResearchInputPacket,
    ExternalResearchValidationStatus,
    main,
    validate_external_research_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "research_runs/candidates/605296.SH/p0-4a-605296-2026-09-08-v2"


def test_p0_4a_v2_retained_execution_is_gap_not_quiet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = CASE / "input.json"
    candidate_path = CASE / "candidate.incomplete.json"
    packet = ExternalResearchInputPacket.model_validate_json(input_path.read_text(encoding="utf-8"))
    candidate = ExternalResearchCandidate.model_validate_json(candidate_path.read_text(encoding="utf-8"))
    audit = json.loads((CASE / "audit.json").read_text(encoding="utf-8"))
    assert packet.execution_id == "p0-4a-605296-2026-09-08-v2"
    assert canonical_hash(packet) == "0d20328995d5da2a31b6af2a0578c003304d3c676ea2828695acbef008d0ab55"
    assert candidate.completion.value == "INCOMPLETE_SOURCE"
    assert candidate.quick_research is None
    assert candidate.pre_research is not None
    assert candidate.pre_research.route.value == "CONTINUE_TO_QUICK"
    assert audit["source_inventory"]["status"] == "INCOMPLETE_SOURCE"
    assert len(audit["tool_action_records"]) == candidate.receipt.tool_calls_used == 16
    for action, event in zip(audit["tool_action_records"], candidate.receipt.tool_events, strict=True):
        assert action["sequence"] == event.sequence
        assert action["status"] == event.status.value
        assert action["platform_reference"] == event.platform_reference
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    assert result.status is ExternalResearchValidationStatus.EXECUTION_GAP
    assert result.funnel_result is None
    assert result.gap_reason
    assert result.human_attention_authority == result.investment_authority == result.signal_transition_authority == "NONE"
    # Exercise the real existing CLI as well as the real installed-model schema generator.
    schema_path, output_path = tmp_path / "schema.json", tmp_path / "validation.json"
    assert main(["schema", "--output", str(schema_path)]) == 0
    args = ["validate", "--input", str(input_path), "--candidate", str(candidate_path), "--output", str(output_path)]
    assert main(args) == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {**result.model_dump(mode="json"), "validation_hash": canonical_hash(result)}
    assert not (CASE / "candidate.json").exists()
    assert not (CASE / "funnel.json").exists()
    # The existing success-candidate scanner is unchanged. This test explicitly covers the gap.
    with capsys.disabled():
        print("P0_4A_V2_IN_PROCESS_CLI=main(" + repr(args) + ")", flush=True)
        print("P0_4A_V2_INPUT_SHA256=" + hashlib.sha256(input_path.read_bytes()).hexdigest(), flush=True)
        print("P0_4A_V2_CANDIDATE_SHA256=" + hashlib.sha256(candidate_path.read_bytes()).hexdigest(), flush=True)
        print("P0_4A_V2_VALIDATION_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
        print("P0_4A_V2_GAP_VALIDATION=PASS_NOT_COMPLETE_RESEARCH", flush=True)
