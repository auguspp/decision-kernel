"""TEMP #321 Acceptance-6 generator from retained Hengrui Human-origin records."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import socket
from uuid import NAMESPACE_URL, uuid5

import pytest

from decision_kernel.calculation import CalculationStatus
from decision_kernel.conditional_odds import (
    DeclaredConditionalWorld,
    build_conditional_provisional_odds,
    build_conditional_world_set,
)
from decision_kernel.evidence import (
    EvidenceArtifact,
    EvidenceArtifactLink,
    EvidenceRelationship,
    ReplayabilityLevel,
    RetentionMode,
)
from decision_kernel.identity import canonical_hash
from decision_kernel.provisional_odds import HumanPriceContext
from decision_kernel.research import ModelRiskLevel, ResearchSnapshot, ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    research_commit_information_bundle_hash,
)
from decision_kernel.runtime import odds_retention as odds
from decision_kernel.runtime import research_commit_only as retained

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "docs/readings/hengrui-600276-research-odds-2026-09-11/provisional-odds.json"

FROZEN_BELIEF = (
    "恒瑞已经证明创新研发能够形成产品和交易价值，但尚未证明这些价值在承担持续研发、资本投入和授权履约成本后，"
    "可以稳定转化为足以支持当前价格要求的每股可支配现金。"
)
INVALIDATION = (
    "若连续可比期证明新增非肿瘤产品只有折价/首轮准入造成的收入增长，增量现金贡献无法覆盖存量衰退和必要再投入，"
    "且许可全周期剩余现金不能弥补，就应撤销“创新转型能持续增加每股可支配现金”的核心判断。"
    "单期GSK确认跨期或单次现金转换下降不构成该证伪。"
)
HORIZON = date(2029, 9, 10)


def uid(label: str):
    return uuid5(NAMESPACE_URL, "decision-kernel:#321:hengrui-acceptance6:" + label)


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Hengrui historical Acceptance-6 generation cannot request network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def git_record(*, key: str, title: str, path: str, ref: str, blob: str, at: str) -> EvidenceArtifact:
    locator = f"https://github.com/auguspp/decision-kernel/blob/{ref}/{path}"
    return EvidenceArtifact(
        id=uid("evidence:" + key),
        source_type="RETAINED_RESEARCH_MIGRATION_RECORD",
        source_identifier=f"GIT:{key}:{blob}",
        source_locator=locator,
        published_at=z(at),
        available_at=z(at),
        retrieved_at=z(at),
        content_hash=f"git-blob:{blob}",
        idempotency_key=f"HENGRUI-MIGRATION:{key}:{ref[:12]}",
        retention_mode=RetentionMode.FULL_ARTIFACT,
        replayability_level=ReplayabilityLevel.FULL,
        raw_storage_ref=locator,
        source_location=path,
        license_terms_note=(
            f"Full replay of the retained Git {title} only. This proves what the historical Research/"
            "Odds record declared; it does not recertify the underlying company sources or thesis truth."
        ),
    )


def research_package(legacy: dict) -> ResearchCommitPackage:
    assert legacy["frozen_belief"] == FROZEN_BELIEF
    assert legacy["price_context"] == {
        "price": "42.93",
        "price_date": "2026-09-10",
        "source": "HUMAN_SUPPLIED_PROVISIONAL_PRICE",
        "authority": "CONTEXT_ONLY",
        "qualified_market_observation": False,
        "canonical_market_state": False,
    }
    assert legacy["odds"]["cardinal_probability"] == "NOT_ESTABLISHED"

    records = (
        git_record(
            key="FINAL-INDEX",
            title="final Frozen-Belief index",
            path="docs/readings/hengrui-600276-research-odds-2026-09-11/README.md",
            ref="9801e4ec47534b2cc9a6bed7bd76b70f0a10564a",
            blob="ae03c48d04df7f9815e54244e2ca2f5020c0a8c1",
            at="2026-09-11T06:03:12Z",
        ),
        git_record(
            key="ROUND3-SUPPLEMENT",
            title="Round3 Research supplement",
            path="docs/readings/hengrui-600276-research-odds-2026-09-11/round3/research_supplement.md",
            ref="00f5f1d165195ad82b7eb571ced5bf7e34338dfa",
            blob="7927a8f0082c25ea48caa57f05b6302176fe3fdd",
            at="2026-09-11T06:01:34Z",
        ),
        git_record(
            key="ROUND3-SOURCES",
            title="Round3 source inventory",
            path="docs/readings/hengrui-600276-research-odds-2026-09-11/round3/sources.json",
            ref="00f5f1d165195ad82b7eb571ced5bf7e34338dfa",
            blob="aaf914c1275fb40a573666a89cfbe45dfda01fc1",
            at="2026-09-11T06:01:34Z",
        ),
        git_record(
            key="LEGACY-PROVISIONAL-ODDS",
            title="Human-price provisional ordinal Odds declaration",
            path="docs/readings/hengrui-600276-research-odds-2026-09-11/provisional-odds.json",
            ref="d99fa180329bba2aaa6ec12a6a58e42c73e50301",
            blob="8e3048b0b14d39fb2577f5b4427721407031e091",
            at="2026-09-11T05:50:04Z",
        ),
    )
    snapshot_id = uid("research-snapshot")
    links = tuple(
        EvidenceArtifactLink(
            id=uid("link:" + item.source_identifier),
            research_snapshot_id=snapshot_id,
            evidence_artifact_id=item.id,
            relationship=EvidenceRelationship.CONTEXT,
            relevance=(
                "Historical migration/provenance identity for the final retained Hengrui Research state; "
                "not independent source-truth certification."
            ),
            interpretation_notes=(
                "Use only to freeze declarations already retained before this migration. Do not add new company facts."
            ),
        )
        for item in records
    )
    created_at = datetime.now(timezone.utc)
    snapshot = ResearchSnapshot(
        id=snapshot_id,
        ticker="600276",
        company_name="恒瑞医药",
        exchange="SSE",
        currency="CNY",
        created_at=created_at,
        as_of_datetime=z("2026-09-11T06:03:12Z"),
        version=1,
        status=ResearchStatus.REVIEW,
        core_thesis=legacy["frozen_belief"],
        market_expectations_narrative=None,
        model_risk_level=ModelRiskLevel.NOT_ESTABLISHED,
        model_risk_notes=(
            "Final Round3 retained Research did not assign a scalar model-risk tier. The older VERY_HIGH label belonged "
            "to an uncalibrated external numerical sensitivity package and is not silently inherited as the final "
            "probability-free Research judgment. Cardinal probability remains NOT_ESTABLISHED."
        ),
        open_questions=tuple(legacy["decisive_unknowns"]),
        thesis_invalidation=(INVALIDATION,),
        monitoring_triggers=tuple(legacy["reopen_triggers"]),
        valuation_bases=(),
        scenarios=(),
        evidence_links=links,
        created_by="historical-human-origin-hengrui-migration",
        committed_at=None,
        research_engine_version="retained-round3-migration-v1",
        information_bundle_hash=None,
        research_origin="HUMAN_ORIGIN_DIRECT_DEEP_ROUND3_RETAINED_MIGRATION",
        schema_version=2,
    )
    digest = research_commit_information_bundle_hash(
        research_snapshot=snapshot, evidence_artifacts=records
    )
    snapshot = snapshot.model_copy(update={"information_bundle_hash": digest})
    return ResearchCommitPackage(
        research_snapshot=snapshot,
        evidence_artifacts=records,
        framing=None,
        proposed_committed_at=created_at,
        schema_version=2,
    )


def edge_worlds(legacy: dict, provenance_ids: tuple) -> tuple[DeclaredConditionalWorld, ...]:
    worlds = []
    for old in legacy["worlds"]:
        low, high = old["terminal_price_cny_range"]
        profit_low, profit_high = old["profit_cny_range"]
        pe_low, pe_high = old["terminal_pe_range"]
        for edge, terminal in (("LOWER", low), ("UPPER", high)):
            conditions = [
                f"Retained legacy world: {old['name']}",
                f"Retained normalized-profit range CNY {profit_low}–{profit_high}",
                f"Retained terminal-PE range {pe_low}–{pe_high}x",
                f"{edge} edge of the retained terminal-price range; no midpoint or probability is introduced.",
            ]
            conditions.extend(old.get("conditions", ()))
            if old.get("additional_requirement"):
                conditions.append(old["additional_requirement"])
            worlds.append(
                DeclaredConditionalWorld(
                    id=uid(f"world:{old['name']}:{edge}"),
                    name=f"{old['name']}_{edge}_EDGE",
                    terminal_equity_value_per_share=Decimal(terminal),
                    operating_conditions=tuple(conditions),
                    valuation_expression=(
                        f"Legacy retained {edge.lower()} endpoint CNY {terminal} from {old['name']} terminal-price "
                        f"range [{low}, {high}], with retained profit range [{profit_low}, {profit_high}] and PE "
                        f"range [{pe_low}, {pe_high}]x. No midpoint, probability or legacy annualized return is imported."
                    ),
                    provenance_artifact_ids=provenance_ids,
                    expected_distributions=(),
                    valuation_basis_id=None,
                )
            )
    return tuple(worlds)


def test_generate_real_hengrui_research_and_conditional_retention(tmp_path):
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    package = research_package(legacy)
    research_input = tmp_path / "research-input.json"
    research_input.write_bytes(retained._raw(package))
    research_dir = tmp_path / "research"
    research = retained.commit_research_file(research_input, output=research_dir)
    snapshot = research.research_snapshot
    assert snapshot.status is ResearchStatus.COMMITTED
    assert snapshot.schema_version == 2
    assert snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert snapshot.valuation_horizon_date is None and snapshot.valuation_bases == () and snapshot.scenarios == ()

    evidence = {item.source_identifier: item.id for item in package.evidence_artifacts}
    provenance = (
        evidence["GIT:LEGACY-PROVISIONAL-ODDS:8e3048b0b14d39fb2577f5b4427721407031e091"],
        evidence["GIT:ROUND3-SUPPLEMENT:7927a8f0082c25ea48caa57f05b6302176fe3fdd"],
        evidence["GIT:FINAL-INDEX:ae03c48d04df7f9815e54244e2ca2f5020c0a8c1"],
    )
    worlds = edge_worlds(legacy, provenance)
    assert len(worlds) == 8
    world_set = build_conditional_world_set(
        research_snapshot=snapshot,
        worlds=worlds,
        valuation_horizon_date=HORIZON,
        world_set_id=uid("world-set"),
        created_at=datetime.now(timezone.utc),
    )
    human = HumanPriceContext(
        ticker="600276",
        exchange="SSE",
        currency="CNY",
        price=Decimal("42.93"),
        price_timestamp=datetime.fromisoformat("2026-09-10T15:00:00+08:00"),
        utc_offset_minutes=480,
        supplied_at=z("2026-09-11T05:50:04Z"),
        source_reference=(
            "Git-retained Human declaration d99fa180329bba2aaa6ec12a6a58e42c73e50301/"
            "provisional-odds.json; exact original chat second is not claimed."
        ),
        price_convention="HUMAN_DECLARED_2026-09-10_A_SHARE_CLOSE_NOT_MARKET_QUALIFIED",
    )
    result = build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=world_set,
        price_context=human,
        artifact_id=uid("conditional-result"),
        created_at=datetime.now(timezone.utc),
    )
    assert result.artifact.price_clock_semantics == "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT"
    assert result.artifact.calculation_status is CalculationStatus.CALCULATED
    assert result.artifact.ordinal_status == "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"
    assert len(result.artifact.world_results) == 8
    assert result.artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert result.artifact.probability_input == "ABSENT_BY_DESIGN"
    assert result.artifact.weighted_aggregate == "NOT_COMPUTED"
    assert result.artifact.market_qualification == "NOT_ESTABLISHED"
    assert result.artifact.canonical_odds == "NOT_ESTABLISHED"
    assert result.artifact.investment_authority == "NONE"
    assert all("probability" not in world.model_dump() for world in result.artifact.conditional_worlds.world_set.worlds)

    result_input = tmp_path / "conditional-result.json"
    result_input.write_bytes(retained._raw(result))
    research_hash = canonical_hash(snapshot)
    odds_dir = tmp_path / "odds"
    assert odds.retain_odds_file(
        result_input,
        result_kind="CONDITIONAL_PROVISIONAL",
        research_directory=research_dir,
        expected_research_hash=research_hash,
        output=odds_dir,
    ) == result

    diagnostics = Path(os.environ["CI_REPORT_DIR"]) / "hengrui-acceptance6-generation"
    diagnostics.mkdir(parents=True, exist_ok=False)
    shutil.copytree(research_dir, diagnostics / "research")
    shutil.copytree(odds_dir, diagnostics / "odds")
    (diagnostics / "identities.json").write_bytes(retained._raw({
        "research_snapshot_id": str(snapshot.id),
        "research_snapshot_hash": research_hash,
        "research_information_bundle_hash": research.information_bundle_hash,
        "research_package_hash": research.package_hash,
        "world_set_hash": world_set.world_set_hash,
        "conditional_result_hash": canonical_hash(result),
        "conditional_artifact_hash": result.artifact_hash,
        "price": "42.93",
        "price_source": human.source,
        "price_authority": human.authority,
        "price_clock_semantics": result.artifact.price_clock_semantics,
        "world_count": len(result.artifact.world_results),
        "cardinal_probability": result.artifact.cardinal_probability,
        "market_qualification": result.artifact.market_qualification,
        "canonical_odds": result.artifact.canonical_odds,
        "investment_authority": result.artifact.investment_authority,
    }))
