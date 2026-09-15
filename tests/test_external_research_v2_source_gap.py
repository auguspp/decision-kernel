"""Validate the real v2 incomplete-source receipt with the unchanged runtime."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.external_research_execution import (
    ExternalResearchCandidate, ExternalResearchInputPacket,
    ExternalResearchValidationStatus, ResearchExecutionCompletion,
    main, validate_external_research_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "research_runs/candidates/605296.SH/p0-4a-605296-2026-09-08-v2"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def test_real_v2_missing_primary_sources_is_execution_gap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    assert _blob(CASE / "input.json") == "de4b9dd901120600915bbe63dcafcd7037a5412c"
    assert _blob(ROOT / "src/decision_kernel/runtime/external_research_execution.py") == "9b2e9c62ed494e7a3d0ee70fe0d42234c8f02bef"
    packet = ExternalResearchInputPacket.model_validate_json((CASE / "input.json").read_text(encoding="utf-8"))
    candidate = ExternalResearchCandidate.model_validate_json((CASE / "candidate.incomplete.json").read_text(encoding="utf-8"))
    inventory = json.loads((CASE / "source-inventory.json").read_text(encoding="utf-8"))
    assert candidate.completion is ResearchExecutionCompletion.INCOMPLETE_SOURCE
    assert candidate.pre_research is None and candidate.quick_research is None
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    assert result.status is ExternalResearchValidationStatus.EXECUTION_GAP
    assert result.funnel_result is None and result.gap_reason
    assert result.human_attention_authority == result.investment_authority == result.signal_transition_authority == "NONE"
    assert candidate.receipt.tool_calls_used == 29 <= packet.budget.max_tool_calls
    assert candidate.receipt.search_queries_used == 12 == packet.budget.max_search_queries
    assert candidate.receipt.source_reads_used == 12 <= packet.budget.max_source_reads
    assert candidate.receipt.technical_retries_used == 0
    assert candidate.receipt.elapsed_minutes_observed == 11 <= packet.budget.max_elapsed_minutes
    assert inventory["read_counts"]["unique_company_primary_bodies_read"] == 0
    assert [c["status"] for c in inventory["required_classes"][:3]] == ["NOT_OBTAINED"] * 3
    assert not (CASE / "funnel.json").exists()
    # Exercise the real CLI; a zero exit code means valid gap shape, NOT complete Research.
    output = tmp_path / "validation.json"
    assert main(["validate", "--input", str(CASE / "input.json"), "--candidate", str(CASE / "candidate.incomplete.json"), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "EXECUTION_GAP" and payload["funnel_result"] is None
    assert payload["validation_hash"] == canonical_hash(result)
    assert payload["input_hash"] == canonical_hash(packet)
    with capsys.disabled():
        print("P0_4A_V2_ORIGINAL_CLI_VALIDATION=" + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
        print("P0_4A_V2_RESEARCH_COMPLETION=INCOMPLETE_SOURCE", flush=True)
