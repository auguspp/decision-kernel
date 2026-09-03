from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from decision_kernel.research import ResearchSnapshot
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.runtime.disclosure_assessment import (
    DisclosureAssessmentPacket,
    parse_disclosure_assessment_packet,
)


CATL_PACKAGE = Path("dogfood/300750-catl.json")
CATL_GOLD = Path("eval/disclosure_cognition/catl-v0.json")
CATL_2026_08_12_PACKET = Path(
    "eval/disclosure_cognition/packets/300750-2026-08-12-d5c110be0932b634.json"
)
CATL_2026_08_25_PACKET = Path(
    "eval/disclosure_cognition/packets/300750-2026-08-25-97ce9a01b90840b4.json"
)


class CommitmentKind(str, Enum):
    OPEN_QUESTION = "OPEN_QUESTION"
    THESIS_INVALIDATION = "THESIS_INVALIDATION"
    MONITORING_TRIGGER = "MONITORING_TRIGGER"


@dataclass(frozen=True)
class CommitmentMatchCandidate:
    """Test-local semantic proposal; not a Kernel or Radar schema."""

    kind: CommitmentKind
    target_text: str
    evidence_announcement_ids: tuple[str, ...]


@dataclass(frozen=True)
class ValidatedCommitmentLineage:
    """Test-local exact lineage produced after semantic matching."""

    research_snapshot_id: str
    research_information_bundle_hash: str
    research_as_of: str
    assessment_input_hash: str
    kind: CommitmentKind
    target_text: str
    evidence_announcement_ids: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]


def _load_snapshot() -> ResearchSnapshot:
    package = ResearchCommitPackage.model_validate_json(
        CATL_PACKAGE.read_text(encoding="utf-8")
    )
    return package.research_snapshot


def _load_packet(path: Path) -> DisclosureAssessmentPacket:
    return parse_disclosure_assessment_packet(path.read_text(encoding="utf-8"))


def _gold_case(case_id: str) -> dict:
    manifest = json.loads(CATL_GOLD.read_text(encoding="utf-8"))
    return next(item for item in manifest["cases"] if item["case_id"] == case_id)


def _exact_commitments(
    snapshot: ResearchSnapshot,
    kind: CommitmentKind,
) -> tuple[str, ...]:
    if kind is CommitmentKind.OPEN_QUESTION:
        return snapshot.open_questions
    if kind is CommitmentKind.THESIS_INVALIDATION:
        return snapshot.thesis_invalidation
    if kind is CommitmentKind.MONITORING_TRIGGER:
        return snapshot.monitoring_triggers
    raise AssertionError(f"unsupported commitment kind: {kind}")


def _validate_commitment_lineage(
    *,
    snapshot: ResearchSnapshot,
    packet: DisclosureAssessmentPacket,
    candidate: CommitmentMatchCandidate,
) -> ValidatedCommitmentLineage:
    """Fail closed on exact Research/commitment/Evidence identity.

    Whether the Evidence *semantically* bears on the commitment remains an external
    Research-cognition judgment. This function only proves that a proposed match did
    not invent or drift its frozen target or source lineage.
    """

    assert packet.stock_code == snapshot.ticker, "packet/security mismatch"
    assert packet.research_snapshot_id == snapshot.id, "packet/Research id mismatch"
    assert (
        packet.research_as_of == snapshot.as_of_datetime
    ), "packet/Research PIT mismatch"
    assert (
        packet.research_information_bundle_hash == snapshot.information_bundle_hash
    ), "packet/Research information identity mismatch"

    exact_targets = _exact_commitments(snapshot, candidate.kind)
    assert (
        candidate.target_text in exact_targets
    ), "target is not an exact frozen Research commitment"

    assert candidate.evidence_announcement_ids, "commitment match needs exact Evidence"
    assert tuple(sorted(set(candidate.evidence_announcement_ids))) == tuple(
        sorted(candidate.evidence_announcement_ids)
    ), "commitment Evidence announcement ids must be unique"

    evidence_by_announcement = {
        item.announcement_id: item for item in packet.evidence
    }
    missing = set(candidate.evidence_announcement_ids) - set(evidence_by_announcement)
    assert not missing, "commitment Evidence falls outside exact assessment packet"

    selected = tuple(
        evidence_by_announcement[announcement_id]
        for announcement_id in candidate.evidence_announcement_ids
    )
    assert all(
        item.published_at > snapshot.as_of_datetime for item in selected
    ), "Commitment Radar Evidence must be newer than frozen Research"

    return ValidatedCommitmentLineage(
        research_snapshot_id=str(snapshot.id),
        research_information_bundle_hash=snapshot.information_bundle_hash or "",
        research_as_of=snapshot.as_of_datetime.isoformat(),
        assessment_input_hash=packet.assessment_input_hash,
        kind=candidate.kind,
        target_text=candidate.target_text,
        evidence_announcement_ids=candidate.evidence_announcement_ids,
        evidence_artifact_ids=tuple(
            str(item.evidence_artifact.id) for item in selected
        ),
    )


def test_real_catl_capital_allocation_batch_can_bind_to_exact_prior_commitment() -> None:
    snapshot = _load_snapshot()
    packet = _load_packet(CATL_2026_08_12_PACKET)
    gold = _gold_case("300750-2026-08-12")

    # The existing reviewed disclosure-cognition corpus already says this batch
    # merits bounded Quick Research because it intersects capital allocation and
    # leaves actual cash deployment versus capex/OCF unresolved. Commitment Radar
    # v0 adds only an exact link back to the pre-existing frozen Research question.
    assert gold["gold_terminal_state"] == "WAIT_FOR_TRIGGER"
    assert gold["gold_terminal_stage"] == "QUICK_RESEARCH"
    assert "capital allocation" in gold["gold_reason_summary"]

    candidate = CommitmentMatchCandidate(
        kind=CommitmentKind.OPEN_QUESTION,
        target_text="在大规模扩产下，自由现金流转化能否跟上利润增长？",
        evidence_announcement_ids=("1225470687", "1225470688"),
    )
    lineage = _validate_commitment_lineage(
        snapshot=snapshot,
        packet=packet,
        candidate=candidate,
    )

    assert lineage.research_snapshot_id == str(snapshot.id)
    assert lineage.research_information_bundle_hash == snapshot.information_bundle_hash
    assert lineage.assessment_input_hash == gold["assessment_input_hash"]
    assert lineage.target_text in snapshot.open_questions
    assert lineage.evidence_artifact_ids == (
        "7827cfaf-96d6-5649-8bee-73683d07db39",
        "0d9ab86b-4f2a-54cb-a405-431ff0c8a681",
    )


def test_commitment_radar_rejects_paraphrased_or_invented_target() -> None:
    snapshot = _load_snapshot()
    packet = _load_packet(CATL_2026_08_12_PACKET)
    candidate = CommitmentMatchCandidate(
        kind=CommitmentKind.OPEN_QUESTION,
        target_text="资本配置是否会削弱未来自由现金流？",
        evidence_announcement_ids=("1225470687", "1225470688"),
    )

    with pytest.raises(
        AssertionError,
        match="target is not an exact frozen Research commitment",
    ):
        _validate_commitment_lineage(
            snapshot=snapshot,
            packet=packet,
            candidate=candidate,
        )


def test_commitment_radar_rejects_evidence_outside_exact_packet() -> None:
    snapshot = _load_snapshot()
    packet = _load_packet(CATL_2026_08_12_PACKET)
    candidate = CommitmentMatchCandidate(
        kind=CommitmentKind.OPEN_QUESTION,
        target_text="在大规模扩产下，自由现金流转化能否跟上利润增长？",
        # This is a real later CATL announcement, but it belongs to the 2026-08-25
        # address-change packet rather than this exact 2026-08-12 assessment input.
        evidence_announcement_ids=("1225502236",),
    )

    with pytest.raises(
        AssertionError,
        match="commitment Evidence falls outside exact assessment packet",
    ):
        _validate_commitment_lineage(
            snapshot=snapshot,
            packet=packet,
            candidate=candidate,
        )


def test_real_catl_administrative_address_change_is_reviewed_no_match_control() -> None:
    snapshot = _load_snapshot()
    packet = _load_packet(CATL_2026_08_25_PACKET)
    gold = _gold_case("300750-2026-08-25")

    assert packet.research_snapshot_id == snapshot.id
    assert packet.research_as_of == snapshot.as_of_datetime
    assert gold["gold_terminal_state"] == "DROP_FOR_NOW"
    assert gold["gold_terminal_stage"] == "PRE_RESEARCH"
    assert "no decision-context impact" in gold["gold_reason_summary"]

    # This is the semantic negative control: exact packet lineage by itself does
    # not imply a commitment match. The reviewed Research judgment is no match,
    # and v0 does not invent a keyword/embedding rule to override it.
    reviewed_matches: tuple[CommitmentMatchCandidate, ...] = ()
    assert reviewed_matches == ()
