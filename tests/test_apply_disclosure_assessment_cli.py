from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.adapters.pdf_text import PagedPdfText, PdfPageText, PdfTextStatus
from decision_kernel.cli import main
from decision_kernel.evidence import EvidenceArtifact, ReplayabilityLevel, RetentionMode
from decision_kernel.identity import canonical_hash
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.research_funnel import (
    DiscoveryInput,
    DiscoveryObservation,
    DiscoverySource,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    QuickResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState
from decision_kernel.runtime.disclosure_assessment import (
    prepare_disclosure_assessment_packet,
    serialize_disclosure_assessment_packet,
)
from decision_kernel.runtime.disclosure_radar import DisclosureBatch
from decision_kernel.runtime.disclosure_receipts import parse_disclosure_assessment_receipts
from decision_kernel.runtime.disclosure_research import DisclosureResearchAssessment


SHANGHAI = ZoneInfo("Asia/Shanghai")
PREPARED_AT = datetime(2026, 9, 2, 6, 0, tzinfo=timezone.utc)
PACKAGE_PATH = Path("dogfood/300750-catl.json")


def _snapshot():
    return ResearchCommitPackage.model_validate_json(
        PACKAGE_PATH.read_text(encoding="utf-8")
    ).research_snapshot


def _text_sha256(*, page_number: int, text: str) -> str:
    payload = json.dumps(
        [{"page_number": page_number, "text": text}],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _packet():
    announcement = CninfoAnnouncement(
        announcement_id="1225519101",
        stock_code="300750",
        org_id="9900025790",
        title="关于2026年度第六期绿色科技创新债券发行完成的公告",
        announcement_type=None,
        published_at=datetime(2026, 8, 27, 17, 48, 11, tzinfo=SHANGHAI),
        source_locator="https://static.cninfo.com.cn/finalpage/2026-08-27/1225519101.PDF",
    )
    batch = DisclosureBatch(
        stock_code="300750",
        publication_date=date(2026, 8, 27),
        first_published_at=announcement.published_at,
        last_published_at=announcement.published_at,
        announcements=(announcement,),
    )

    def fetch_pdf(*, source_locator: str) -> bytes:
        return source_locator.encode("utf-8")

    def extract_pdf(_payload: bytes) -> PagedPdfText:
        text = "正文 1225519101"
        return PagedPdfText(
            pdf_sha256="a" * 64,
            text_sha256=_text_sha256(page_number=1, text=text),
            page_count=1,
            extracted_char_count=len(text),
            status=PdfTextStatus.EXTRACTED,
            pages=(PdfPageText(page_number=1, text=text),),
        )

    return prepare_disclosure_assessment_packet(
        research_snapshot=_snapshot(),
        batch=batch,
        prepared_at=PREPARED_AT,
        fetch_pdf=fetch_pdf,
        extract_pdf=extract_pdf,
    )


def _discovery(packet) -> DiscoveryInput:
    official = packet.evidence[0].evidence_artifact
    return DiscoveryInput(
        discovery_id=f"CNINFO:{packet.stock_code}:{packet.publication_date.isoformat()}",
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction="test whether the official disclosure changes frozen Research",
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement="the official disclosure batch requires semantic assessment",
                evidence_artifact_ids=(official.id,),
            ),
        ),
        source_lineage=(
            DiscoverySource(
                evidence_artifact_id=official.id,
                source_locator=official.source_locator,
                available_at=official.available_at,
            ),
        ),
        why_now="official evidence is newer than frozen Research",
        next_discriminating_search="compare the disclosure with frozen Research questions",
        known_stop_or_downgrade_condition="stop if decision-relevant context does not change",
    )


def _pre(packet, discovery: DiscoveryInput, *, route: PreResearchRoute) -> PreResearchResult:
    official = packet.evidence[0].evidence_artifact
    return PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=discovery.as_of,
        what_is_this="an official company disclosure",
        economic_direction="possible update to frozen company research",
        why_surfaced_now="the official batch is newer than frozen Research",
        basic_business_role="operating company",
        potential_fundamental_driver="capital allocation or operating evidence",
        current_market_expectation_hypothesis="the market may already expect the disclosed action",
        material_claims=(
            ResearchClaim(
                statement="the company published the official disclosure",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(official.id,),
            ),
        ),
        largest_unknown="whether the disclosure changes the core research questions",
        next_discriminating_search="look for corroborating operating evidence",
        route=route,
        route_reason=f"route={route.value}",
    )


def _quiet_assessment(packet, *, route: PreResearchRoute) -> DisclosureResearchAssessment:
    discovery = _discovery(packet)
    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=_pre(packet, discovery, route=route),
    )


def _supplemental_evidence() -> EvidenceArtifact:
    evidence_id = uuid4()
    available_at = PREPARED_AT - timedelta(hours=2)
    return EvidenceArtifact(
        id=evidence_id,
        source_type="research_reference",
        source_identifier=str(evidence_id),
        source_locator=f"https://example.test/{evidence_id}",
        published_at=available_at - timedelta(minutes=5),
        available_at=available_at,
        retrieved_at=PREPARED_AT,
        content_hash="e" * 64,
        idempotency_key=str(evidence_id),
        retention_mode=RetentionMode.METADATA_ONLY,
        replayability_level=ReplayabilityLevel.REFERENCE_ONLY,
    )


def _deepen_assessment(packet) -> DisclosureResearchAssessment:
    discovery = _discovery(packet)
    pre = _pre(packet, discovery, route=PreResearchRoute.CONTINUE_TO_QUICK)
    official = packet.evidence[0].evidence_artifact
    contrary = _supplemental_evidence()
    quick = QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=discovery.as_of,
        business_model="battery manufacturer",
        segment_mix="battery systems and related businesses",
        economic_role="scaled battery supplier",
        major_profit_drivers=("utilization", "pricing", "mix"),
        industry_supply_demand_variables=("capacity", "EV demand", "storage demand"),
        value_chain_position="battery cell and system producer",
        market_expectation_hypothesis="market expects continued scale and cash generation",
        supporting_claims=(
            ResearchClaim(
                statement="the official filing confirms the disclosed corporate action",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(official.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="supplemental evidence leaves an unresolved counterpoint",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(contrary.id,),
            ),
        ),
        evidence_authority_assessment="official filing plus bounded supplemental reference",
        variant_perception="the disclosure matters only if operating evidence later confirms it",
        unresolved_questions=("does execution change cash conversion?",),
        next_discriminating_evidence=("actual execution and next operating disclosure",),
        route=QuickResearchRoute.DEEPEN,
        route_reason="the existing Research Funnel requires deeper research",
    )
    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
        supplemental_evidence_artifacts=(contrary,),
    )


def _write_inputs(tmp_path: Path, packet, assessment: DisclosureResearchAssessment):
    packet_path = tmp_path / "packet.json"
    assessment_path = tmp_path / "assessment.json"
    packet_path.write_text(
        serialize_disclosure_assessment_packet(packet),
        encoding="utf-8",
    )
    assessment_path.write_text(
        assessment.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return packet_path, assessment_path


def _apply(packet_path: Path, assessment_path: Path, receipts_path: Path):
    stdout = StringIO()
    stderr = StringIO()
    code = main(
        [
            "apply-disclosure-assessment",
            str(packet_path),
            str(assessment_path),
            "--receipts",
            str(receipts_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )
    return code, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize(
    ("route", "terminal_state"),
    [
        (PreResearchRoute.WAIT_FOR_TRIGGER, ResearchFunnelTerminalState.WAIT_FOR_TRIGGER),
        (PreResearchRoute.STOP, ResearchFunnelTerminalState.DROP_FOR_NOW),
    ],
)
def test_apply_quiet_assessment_writes_exact_receipt(
    tmp_path: Path,
    route: PreResearchRoute,
    terminal_state: ResearchFunnelTerminalState,
) -> None:
    packet = _packet()
    packet_path, assessment_path = _write_inputs(
        tmp_path,
        packet,
        _quiet_assessment(packet, route=route),
    )
    receipts_path = tmp_path / "receipts.json"

    code, stdout, stderr = _apply(packet_path, assessment_path, receipts_path)

    assert code == 0, stderr
    receipts = parse_disclosure_assessment_receipts(
        receipts_path.read_text(encoding="utf-8")
    )
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt.stock_code == packet.stock_code
    assert receipt.announcement_ids == packet.announcement_ids
    assert receipt.research_snapshot_id == packet.research_snapshot_id
    assert receipt.research_as_of == packet.research_as_of
    assert receipt.assessment_semantics_id == packet.assessment_semantics_id
    assert receipt.assessment_result is terminal_state
    assert "ASSESSMENT DISPOSITION: QUIET" in stdout
    assert "RECEIPT: RECORDED" in stdout
    assert "INVESTMENT AUTHORITY: NONE" in stdout


def test_apply_same_quiet_assessment_is_idempotent(tmp_path: Path) -> None:
    packet = _packet()
    packet_path, assessment_path = _write_inputs(
        tmp_path,
        packet,
        _quiet_assessment(packet, route=PreResearchRoute.WAIT_FOR_TRIGGER),
    )
    receipts_path = tmp_path / "receipts.json"

    first_code, _first_stdout, first_stderr = _apply(
        packet_path,
        assessment_path,
        receipts_path,
    )
    assert first_code == 0, first_stderr
    first_memory = receipts_path.read_text(encoding="utf-8")

    second_code, second_stdout, second_stderr = _apply(
        packet_path,
        assessment_path,
        receipts_path,
    )

    assert second_code == 0, second_stderr
    assert receipts_path.read_text(encoding="utf-8") == first_memory
    assert "RECEIPT: UNCHANGED" in second_stdout


def test_apply_conflicting_quiet_result_fails_without_rewriting_memory(tmp_path: Path) -> None:
    packet = _packet()
    packet_path, wait_path = _write_inputs(
        tmp_path,
        packet,
        _quiet_assessment(packet, route=PreResearchRoute.WAIT_FOR_TRIGGER),
    )
    receipts_path = tmp_path / "receipts.json"
    first_code, _first_stdout, first_stderr = _apply(packet_path, wait_path, receipts_path)
    assert first_code == 0, first_stderr
    first_memory = receipts_path.read_text(encoding="utf-8")

    drop_path = tmp_path / "drop-assessment.json"
    drop_path.write_text(
        _quiet_assessment(packet, route=PreResearchRoute.STOP).model_dump_json(indent=2),
        encoding="utf-8",
    )
    code, _stdout, stderr = _apply(packet_path, drop_path, receipts_path)

    assert code == 2
    assert "conflicting disclosure assessment receipt" in stderr
    assert receipts_path.read_text(encoding="utf-8") == first_memory


def test_apply_deepen_remains_actionable_and_writes_no_receipt(tmp_path: Path) -> None:
    packet = _packet()
    packet_path, assessment_path = _write_inputs(
        tmp_path,
        packet,
        _deepen_assessment(packet),
    )
    receipts_path = tmp_path / "receipts.json"

    code, stdout, stderr = _apply(packet_path, assessment_path, receipts_path)

    assert code == 0, stderr
    assert not receipts_path.exists()
    assert "DISCLOSURE RESEARCH RESULT: DEEPEN_REQUIRED" in stdout
    assert "ASSESSMENT DISPOSITION: ACTIONABLE" in stdout
    assert "RECEIPT: NOT WRITTEN" in stdout
    assert "INVESTMENT AUTHORITY: NONE" in stdout


def test_apply_mismatched_assessment_hash_fails_before_receipt_write(tmp_path: Path) -> None:
    packet = _packet()
    assessment = _quiet_assessment(packet, route=PreResearchRoute.WAIT_FOR_TRIGGER).model_copy(
        update={"assessment_input_hash": "f" * 64}
    )
    packet_path, assessment_path = _write_inputs(tmp_path, packet, assessment)
    receipts_path = tmp_path / "receipts.json"

    code, _stdout, stderr = _apply(packet_path, assessment_path, receipts_path)

    assert code == 2
    assert "exact assessment input" in stderr
    assert not receipts_path.exists()


def test_apply_tampered_packet_fails_before_assessment_or_receipt(tmp_path: Path) -> None:
    packet = _packet()
    assessment = _quiet_assessment(packet, route=PreResearchRoute.WAIT_FOR_TRIGGER)
    packet_payload = json.loads(serialize_disclosure_assessment_packet(packet))
    packet_payload["evidence"][0]["pages"][0]["text"] += " altered"
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(
        json.dumps(packet_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")
    receipts_path = tmp_path / "receipts.json"

    code, _stdout, stderr = _apply(packet_path, assessment_path, receipts_path)

    assert code == 2
    assert "page text" in stderr
    assert not receipts_path.exists()
