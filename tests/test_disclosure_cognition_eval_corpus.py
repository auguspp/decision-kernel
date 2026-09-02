from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.research_workflow_v1 import (
    ResearchFunnelStage,
    ResearchFunnelTerminalState,
)
from decision_kernel.runtime.disclosure_assessment import parse_disclosure_assessment_packet


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "eval/disclosure_cognition/catl-v0.json"
EXPECTED_PACKET_FILE_SHA256 = {
    "300750-2026-07-30-ba2ebf17c1f338f0.json": "fa14ed13bfef9c9009860b93e9f9b0496829210a81ff4682b128e70dff61352b",
    "300750-2026-08-04-9076b90d4b7b5c36.json": "ebc0351c917d2c56f4b98de4efb669ea3a2eec51257a98e957077eaead06c63c",
    "300750-2026-08-06-68580c9ddba657bc.json": "e4c30da9baf4d8d6ad506117bd30d5a315d2a63b3b13b50b283f259093a67355",
    "300750-2026-08-07-d22eaa83781cca36.json": "e67dde73385d1c64b23be3bc5ba8553cc20dd5f9760dfa7146429fec2c68d060",
    "300750-2026-08-12-d5c110be0932b634.json": "6c738194e84b8624aa1b7a7056c43a285dbb504b36d4111f6e75e862f7577788",
    "300750-2026-08-25-97ce9a01b90840b4.json": "2d640bd5ee99af9c47dc5a9322d5b51e731e13eafc8dc6f0e15a7f78717fa9c3",
}


def _aware(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_catl_disclosure_cognition_corpus_is_frozen_and_auditable() -> None:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    assert corpus["schema_version"] == 1
    assert corpus["storage_classification"] == "GIT_DURABLE_EPISTEMIC_EVAL_FIXTURE"

    context = corpus["research_context"]
    package_path = ROOT / context["package_path"]
    package = ResearchCommitPackage.model_validate_json(
        package_path.read_text(encoding="utf-8")
    )
    snapshot = package.research_snapshot
    assert str(snapshot.id) == context["research_snapshot_id"]
    assert snapshot.as_of_datetime == _aware(context["research_as_of"])
    assert snapshot.information_bundle_hash == context["research_information_bundle_hash"]
    assert snapshot.ticker == context["stock_code"]

    freeze = corpus["packet_freeze_provenance"]
    prepared_at = _aware(freeze["prepared_at"])
    assert freeze["source_experiment_pr"] == 65
    assert freeze["source_workflow_run_id"] == 33602610093
    assert len(freeze["source_artifact_sha256"]) == 64

    gold = corpus["gold_provenance"]
    assert gold["source_experiment_pr"] == 44
    assert gold["assessment_semantics_id"] == "research-funnel-v1"

    cases = corpus["cases"]
    assert len(cases) == 6
    assert len({case["case_id"] for case in cases}) == len(cases)

    referenced_packets = set()
    state_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()

    for case in cases:
        ResearchFunnelTerminalState(case["gold_terminal_state"])
        ResearchFunnelStage(case["gold_terminal_stage"])
        state_counts[case["gold_terminal_state"]] += 1
        stage_counts[case["gold_terminal_stage"]] += 1

        packet_path = ROOT / case["packet_path"]
        referenced_packets.add(packet_path.resolve())
        raw_packet = packet_path.read_bytes()
        assert hashlib.sha256(raw_packet).hexdigest() == EXPECTED_PACKET_FILE_SHA256[
            packet_path.name
        ]
        packet = parse_disclosure_assessment_packet(raw_packet.decode("utf-8"))

        assert packet.stock_code == context["stock_code"]
        assert str(packet.research_snapshot_id) == context["research_snapshot_id"]
        assert packet.research_as_of == _aware(context["research_as_of"])
        assert (
            packet.research_information_bundle_hash
            == context["research_information_bundle_hash"]
        )
        assert packet.assessment_semantics_id == gold["assessment_semantics_id"]
        assert packet.prepared_at == prepared_at
        assert packet.publication_date.isoformat() == case["publication_date"]
        assert list(packet.announcement_ids) == case["announcement_ids"]
        assert packet.assessment_input_hash == case["assessment_input_hash"]

        evidence_by_id = {item.announcement_id: item for item in packet.evidence}
        assert set(evidence_by_id) == set(case["announcement_ids"])
        assert set(case["official_pdf_sha256"]) == set(case["announcement_ids"])
        for announcement_id, expected_hash in case["official_pdf_sha256"].items():
            evidence = evidence_by_id[announcement_id]
            assert evidence.pdf_sha256 == expected_hash
            assert evidence.evidence_artifact.content_hash == expected_hash

        claim_evidence_ids = set()
        assert case["gold_claims"]
        for claim in case["gold_claims"]:
            assert claim["statement"].strip()
            referenced_ids = set(claim["evidence_announcement_ids"])
            assert referenced_ids
            assert referenced_ids <= set(case["announcement_ids"])
            claim_evidence_ids |= referenced_ids

        no_claim_ids = set(case.get("gold_no_claim_from_announcement_ids", ()))
        assert no_claim_ids <= set(case["announcement_ids"])
        assert no_claim_ids.isdisjoint(claim_evidence_ids)
        assert case["gold_largest_unknown"].strip()
        assert case["gold_next_evidence"]
        assert case["gold_reason_summary"].strip()

    packet_dir = ROOT / "eval/disclosure_cognition/packets"
    actual_packets = {path.resolve() for path in packet_dir.glob("*.json")}
    assert actual_packets == referenced_packets
    assert set(EXPECTED_PACKET_FILE_SHA256) == {path.name for path in actual_packets}

    # This is corpus integrity, not a Kernel routing invariant: it records the reviewed v0 gold.
    assert state_counts == Counter({"DROP_FOR_NOW": 4, "WAIT_FOR_TRIGGER": 2})
    assert stage_counts == Counter({"PRE_RESEARCH": 5, "QUICK_RESEARCH": 1})
