from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha1, sha256
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from decision_kernel.evidence import (
    EvidenceArtifact,
    EvidenceArtifactLink,
    EvidenceRelationship,
    ReplayabilityLevel,
    RetentionMode,
)
from decision_kernel.identity import canonical_json
from decision_kernel.research import ModelRiskLevel, ResearchSnapshot, ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    research_commit_information_bundle_hash,
)
from decision_kernel.runtime.research_commit_only import commit_research_file


ROOT = Path(__file__).resolve().parents[1]
CUTOFF = datetime(2026, 9, 16, 2, 25, 49, tzinfo=timezone.utc)
RETENTION_COMMIT_AT = datetime(2026, 9, 16, 2, 29, 31, tzinfo=timezone.utc)
SOURCE_NOTE_AT = datetime(2026, 9, 10, 4, 50, 40, tzinfo=timezone.utc)
SOURCE_NOTE = ROOT / "research_runs/candidates/sector-origin/600598-materiality-20260910/source-note.json"
CALCULATIONS = ROOT / "docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/calculations.json"
SOURCES = ROOT / "docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/sources.md"
WORKPAPER = ROOT / "docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/README.md"

CORE_THESIS = (
    "北大荒的主要股东经济并不是“粮价上涨直接受益”，而是以国有耕地发包、统一管理与服务为核心的准租赁/管理现金流。"
    "2026 年 14.10 亿元历史补税及滞纳金是一次性结算冲击并已支付，不应年化；但非职工家庭农场对应的土地承包收入已明确不享受原优惠，"
    "使长期税后盈利和现金创造能力相对旧口径永久下调。现有 Evidence 更支持新增经常性所得税约 2 亿元量级的工作假设，而不是 0 或 14.10 亿元/年；精确税基仍 UNKNOWN。"
)
OPEN_QUESTIONS = (
    "非职工家庭农场对应的土地承包费收入、利润和亩数占比",
    "2026+ 年度实际新增所得税",
    "土地合同结构是否因税制重新设计",
    "成本增速快于土地承包费收入是否持续",
    "2026+ 分红能否维持历史水平",
    "黎东光被留置的具体原因及是否影响更广治理/内控",
)
REOPEN = "若取得税基/合同结构/治理的新 Evidence，再只重开受影响的桥。"
MODEL_RISK_NOTES = (
    "公司没有披露非职工家庭农场对应的精确收入、利润或未来合同结构，因此不能把1.75–2.05亿元/年的分析性税负区间升级为预测；"
    "黎东光被留置的具体原因及是否影响更广治理/内控保持 UNKNOWN。"
)


def _git_blob(data: bytes) -> str:
    return sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def _saved_observation(path: Path, *, artifact_id, identifier: str, locator: str,
                       expected_blob: str, published_at: datetime, available_at: datetime,
                       retrieved_at: datetime, note: str) -> EvidenceArtifact:
    data = path.read_bytes()
    assert _git_blob(data) == expected_blob
    return EvidenceArtifact(
        id=artifact_id,
        source_type="SAVED_RESEARCH_OBSERVATION",
        source_identifier=identifier,
        source_locator=locator,
        published_at=published_at,
        available_at=available_at,
        retrieved_at=retrieved_at,
        content_hash=sha256(data).hexdigest(),
        idempotency_key=identifier,
        retention_mode=RetentionMode.FULL_ARTIFACT,
        replayability_level=ReplayabilityLevel.PARTIAL,
        raw_storage_ref=locator,
        source_location=str(path.relative_to(ROOT)),
        license_terms_note=note,
    )


def test_generate_exact_beidahuang_research_only_freeze(tmp_path: Path) -> None:
    workpaper = WORKPAPER.read_text(encoding="utf-8")
    assert CORE_THESIS in workpaper
    assert all(question in workpaper for question in OPEN_QUESTIONS)
    assert REOPEN in workpaper
    assert "ANALYST_DERIVED / NOT_COMPANY_GUIDANCE / LOW_TO_MEDIUM_CONFIDENCE" in workpaper
    assert "原因保持 UNKNOWN" in workpaper

    snapshot_id = uuid5(NAMESPACE_URL, "decision-kernel:600598:research-freeze:2026-09-16T02:25:49Z")
    old_id = uuid5(NAMESPACE_URL, "decision-kernel:600598:evidence:source-note:ae3193a2a9583950b626a8bff4269c447aae26ec")
    calculations_id = uuid5(NAMESPACE_URL, "decision-kernel:600598:evidence:calculations:0f9194d2c1236f51791198b1b6601276ce204946")
    sources_id = uuid5(NAMESPACE_URL, "decision-kernel:600598:evidence:sources:fbbcdea55850963ceb40c6c4ec1dee91a39ac5f9")

    evidence = (
        _saved_observation(
            SOURCE_NOTE,
            artifact_id=old_id,
            identifier="600598-materiality-20260910-source-note",
            locator="https://github.com/auguspp/decision-kernel/blob/62e6850322dfd1552dac871072a9002fa5ad7f82/research_runs/candidates/sector-origin/600598-materiality-20260910/source-note.json",
            expected_blob="ae3193a2a9583950b626a8bff4269c447aae26ec",
            published_at=SOURCE_NOTE_AT,
            available_at=SOURCE_NOTE_AT,
            retrieved_at=SOURCE_NOTE_AT,
            note="Exact retained primary-document extracts and observations, not full original filings or source-truth certification.",
        ),
        _saved_observation(
            CALCULATIONS,
            artifact_id=calculations_id,
            identifier="600598-tax-regime-continuation-calculations-20260916",
            locator="https://github.com/auguspp/decision-kernel/blob/fefff5b49ecfbe4f5cfb4aa62cf29f6f9f26aa03/docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/calculations.json",
            expected_blob="0f9194d2c1236f51791198b1b6601276ce204946",
            published_at=CUTOFF,
            available_at=CUTOFF,
            retrieved_at=RETENTION_COMMIT_AT,
            note="Hash covers the exact retained Research calculation/observation file. Primary filings were available by the declared Research cutoff; Git retention followed by minutes. This is not full-PDF retention or independent source-truth certification.",
        ),
        _saved_observation(
            SOURCES,
            artifact_id=sources_id,
            identifier="600598-tax-regime-continuation-source-inventory-20260916",
            locator="https://github.com/auguspp/decision-kernel/blob/fefff5b49ecfbe4f5cfb4aa62cf29f6f9f26aa03/docs/readings/600598-beidahuang-tax-regime-continuation-2026-09-16/sources.md",
            expected_blob="fbbcdea55850963ceb40c6c4ec1dee91a39ac5f9",
            published_at=CUTOFF,
            available_at=CUTOFF,
            retrieved_at=RETENTION_COMMIT_AT,
            note="Exact retained source inventory and FACT/DERIVED/UNKNOWN separation. URLs are locators; not every linked primary body is archived in Git.",
        ),
    )

    links = (
        EvidenceArtifactLink(
            id=uuid5(NAMESPACE_URL, "decision-kernel:600598:freeze-link:source-note"),
            research_snapshot_id=snapshot_id,
            evidence_artifact_id=old_id,
            relationship=EvidenceRelationship.SUPPORTS,
            relevance="Retained 2025 operating/profit base and June-2026 historical tax-notice extracts used by the continuation.",
            interpretation_notes="Primary-document extracts are partial; original source qualifications remain in the retained file.",
        ),
        EvidenceArtifactLink(
            id=uuid5(NAMESPACE_URL, "decision-kernel:600598:freeze-link:calculations"),
            research_snapshot_id=snapshot_id,
            evidence_artifact_id=calculations_id,
            relationship=EvidenceRelationship.SUPPORTS,
            relevance="Retained H1 reported amounts, derived bridges and bounded tax/cash sensitivities used by the final Research Belief.",
            interpretation_notes="Derived 1.75–2.05亿元 recurring-tax range is analyst-derived, not company guidance or a probability forecast.",
        ),
        EvidenceArtifactLink(
            id=uuid5(NAMESPACE_URL, "decision-kernel:600598:freeze-link:sources"),
            research_snapshot_id=snapshot_id,
            evidence_artifact_id=sources_id,
            relationship=EvidenceRelationship.CONTEXT,
            relevance="Exact source identity inventory, source-use boundaries and FACT/DERIVED/UNKNOWN separation for the continuation.",
            interpretation_notes="Locator inventory is not proof that every linked source body is fully retained.",
        ),
    )

    snapshot = ResearchSnapshot(
        id=snapshot_id,
        ticker="600598.SH",
        company_name="黑龙江北大荒农业股份有限公司",
        exchange="SSE",
        currency="CNY",
        created_at=CUTOFF,
        as_of_datetime=CUTOFF,
        valuation_horizon_date=None,
        version=1,
        status=ResearchStatus.REVIEW,
        core_thesis=CORE_THESIS,
        market_expectations_narrative=None,
        model_risk_level=ModelRiskLevel.NOT_ESTABLISHED,
        model_risk_notes=MODEL_RISK_NOTES,
        open_questions=OPEN_QUESTIONS,
        thesis_invalidation=(REOPEN,),
        monitoring_triggers=(),
        valuation_bases=(),
        scenarios=(),
        evidence_links=links,
        created_by="decision-kernel-retained-research-freeze-v1",
        committed_at=None,
        research_engine_version="retained-human-origin-research-v1",
        information_bundle_hash=None,
        research_origin="HUMAN_AUTHORIZED_CONTINUATION_RETAINED_RESEARCH",
        schema_version=2,
    )
    information_hash = research_commit_information_bundle_hash(
        research_snapshot=snapshot,
        evidence_artifacts=evidence,
    )
    snapshot = snapshot.model_copy(update={"information_bundle_hash": information_hash})
    package = ResearchCommitPackage(
        research_snapshot=snapshot,
        evidence_artifacts=evidence,
        framing=None,
        proposed_committed_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        schema_version=2,
    )

    package_path = tmp_path / "package.json"
    package_path.write_text(canonical_json(package) + "\n", encoding="utf-8")
    report_root = Path(os.environ["CI_REPORT_DIR"]) / "beidahuang-real-freeze"
    result = commit_research_file(package_path, output=report_root)

    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.research_snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert result.research_snapshot.scenarios == ()
    assert result.research_snapshot.valuation_bases == ()
    assert result.research_snapshot.core_thesis == CORE_THESIS
    assert result.research_snapshot.open_questions == OPEN_QUESTIONS
    assert result.research_snapshot.thesis_invalidation == (REOPEN,)
