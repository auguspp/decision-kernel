"""Admission-only edge controls; no model/provider execution or registration."""
from __future__ import annotations

import pytest

import test_external_research_execution as fx
from test_external_research_identity import raw, scoped, registered, reader
from decision_kernel.runtime import external_research_identity as guard


def test_execution_identity_is_not_the_observation_discovery_id():
    # Same valid observation, separately identified execution. The original
    # Discovery/Pre/Quick ids remain mutually bound by the unchanged Funnel.
    packet = fx.packet().model_copy(update={"execution_id": "different-execution-not-discovery"})
    candidate = fx.complete_candidate(packet)
    assert candidate.discovery.discovery_id != packet.execution_id
    scope, values, rows = scoped([packet])
    result = guard.require_promotion(raw(packet), raw(candidate), guard.input_key(packet), scope)
    assert result.funnel_result is not None
    entry = registered(packet, candidate, values, rows)
    reading = guard.project_registered_handoffs([entry], reader(values))
    assert reading["background"][0]["external_execution"] == guard.input_key(packet).as_dict()


@pytest.mark.parametrize("damage", ["missing-catalog", "invalid-catalog", "missing-input"])
def test_external_binding_does_not_fall_through_when_catalogue_is_unusable(damage):
    packet = fx.packet()
    _, values, rows = scoped([packet])
    entry = registered(packet, fx.complete_candidate(packet), values, rows)
    if damage == "missing-catalog":
        del values[guard.CATALOG_PATH]
    elif damage == "invalid-catalog":
        values[guard.CATALOG_PATH] = b"not json"
    else:
        del values["input-0.json"]
    result = guard.project_registered_handoffs([entry], reader(values))
    assert result["active"] == result["background"] == result["resolved_history"] == []
    assert result["execution_identity_scope"]["status"] == "EXECUTION_SCOPE_UNAVAILABLE"
    assert result["gaps"]
