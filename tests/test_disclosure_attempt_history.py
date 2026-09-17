from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime.disclosure_attempt_history import (
    build_attempt_history,
    empty_attempt_history,
    packet_prefetch_identity,
    parse_attempt_history,
)

SHA = "a" * 40
PACKET = Path("eval/disclosure_cognition/packets/300750-2026-07-30-ba2ebf17c1f338f0.json")


def test_reserved_packet_builds_pinned_scheduling_history_without_authority():
    raw = PACKET.read_bytes()
    packet = work._packet(raw)
    key = packet.assessment_input_hash
    payload = build_attempt_history(
        work_files={work.request_path(key): raw},
        work_commit=SHA,
    )
    assert payload["work_commit"] == SHA
    assert payload["reserved_packet_count"] == 1
    assert payload["attempts"] == [{
        "prefetch_hash": packet_prefetch_identity(packet),
        "assessment_input_hashes": [key],
    }]
    assert payload["investment_authority"] == payload["action_authority"] == "NONE"
    assert parse_attempt_history(json.dumps(payload)) == payload


def test_empty_history_is_explicit_and_tamper_fails_closed():
    payload = empty_attempt_history(work_commit=SHA)
    assert parse_attempt_history(json.dumps(payload))["attempts"] == []

    broken = dict(payload)
    broken["reserved_packet_count"] = 1
    with pytest.raises(ValueError, match="reserved count|hash differs"):
        parse_attempt_history(json.dumps(broken))


def test_work_history_corruption_is_not_relabelled_empty():
    raw = PACKET.read_bytes()
    packet = work._packet(raw)
    bad_path = work.request_path("c" * 64)
    with pytest.raises(ValueError):
        build_attempt_history(work_files={bad_path: raw}, work_commit=SHA)
