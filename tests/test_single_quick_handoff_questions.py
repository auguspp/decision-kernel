"""Question-state provenance is not a mandatory decreasing UNKNOWN count."""
import pytest
from decision_kernel.primitives import DomainValidationError
from decision_kernel.runtime.single_quick_contract import (
    FullResearchHandoff, SingleQuickCandidate, build_full_handoff, verify_full_handoff,
)
from test_single_quick_contract import synthetic, raw, spec, no_network


def test_full_handoff_keeps_input_limits_separate_from_remaining_questions():
    packet, candidate = synthetic()
    value = candidate.model_dump(mode="json")
    value["assessment"]["unknowns"] = []
    candidate = SingleQuickCandidate.model_validate(value)
    inp, out = raw(packet), raw(candidate)
    args = dict(input_raw=inp, candidate_raw=out,
        input_source=spec(packet, "input.json", inp, "SINGLE_QUICK_INPUT"),
        candidate_source=spec(packet, "candidate.json", out, "SINGLE_QUICK_CANDIDATE"))
    result = build_full_handoff(**args)
    assert result.input_known_unknowns == packet.known_unknowns
    assert result.input_known_unknowns and result.open_unknowns == ()
    assert result.execution_authority == "NONE"
    assert verify_full_handoff(result, input_raw=inp, candidate_raw=out) == result
    changed = result.model_dump(mode="json")
    changed["input_known_unknowns"] = []
    with pytest.raises(DomainValidationError):
        verify_full_handoff(FullResearchHandoff.model_validate(changed),
                            input_raw=inp, candidate_raw=out)
