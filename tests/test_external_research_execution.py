from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from decision_kernel.evidence import EvidenceArtifact, ReplayabilityLevel, RetentionMode
from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
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
from decision_kernel.runtime.external_research_execution import (
    BudgetEnforcement,
    ExternalResearchCandidate,
    ExternalResearchInputPacket,
    ExternalResearchValidationStatus,
    ResearchExecutionBudget,
    ResearchExecutionCompletion,
    ResearchExecutionReceipt,
    ResearchInputSourceRef,
    ResearchSourceDisposition,
    ResearchToolEvent,
    ResearchToolKind,
    ResearchToolStatus,
    ToolRecordKind,
    validate_external_research_candidate,
)


CUTOFF = datetime(2026, 9, 8, 11, 0, tzinfo=timezone.utc)
START = CUTOFF + timedelta(minutes=1)
FINISH = START + timedelta(minutes=8)
SEED_ID = UUID("10000000-0000-0000-0000-000000000001")
SUPPORT_ID = UUID("10000000-0000-0000-0000-000000000002")
OPPOSE_ID = UUID("10000000-0000-0000-0000-000000000003")
FIXTURE = "tests/fixtures/p0_4a_untrusted_source_injection.txt"


def evidence(
    evidence_id: UUID,
    *,
    locator: str,
    available_at: datetime | None = None,
    retrieved_at: datetime | None = None,
) -> EvidenceArtifact:
    available = available_at or CUTOFF - timedelta(days=1)
    retrieved = retrieved_at or START + timedelta(minutes=2)
    return EvidenceArtifact(
        id=evidence_id,
        source_type="OFFICIAL_FILING",
        source_identifier=str(evidence_id),
        source_locator=locator,
        published_at=available - timedelta(days=1),
        available_at=available,
        retrieved_at=retrieved,
        content_hash="a" * 64,
        idempotency_key=str(evidence_id),
        retention_mode=RetentionMode.EXTRACTED_VALUES,
        replayability_level=ReplayabilityLevel.PARTIAL,
        extracted_structured_values={"statement": "retained source fact"},
    )


def source_ref(*, path: str = "current-state.json") -> ResearchInputSourceRef:
    return ResearchInputSourceRef(
        repository="auguspp/decision-kernel",
        ref="e" * 40,
        path=path,
        git_blob="b" * 40,
        sha256="c" * 64,
        purpose="frozen input",
    )


def budget() -> ResearchExecutionBudget:
    return ResearchExecutionBudget(
        max_tool_calls=8,
        max_search_queries=4,
        max_source_reads=6,
        max_technical_retries=1,
        max_elapsed_minutes=20,
        tool_calls_enforcement=BudgetEnforcement.SOFT_EXECUTOR,
        search_queries_enforcement=BudgetEnforcement.SOFT_EXECUTOR,
        source_reads_enforcement=BudgetEnforcement.SOFT_EXECUTOR,
        technical_retries_enforcement=BudgetEnforcement.SOFT_EXECUTOR,
        elapsed_time_enforcement=BudgetEnforcement.SOFT_EXECUTOR,
    )


def packet() -> ExternalResearchInputPacket:
    seed = evidence(
        SEED_ID,
        locator="https://github.com/auguspp/decision-kernel/blob/" + "e" * 40 + "/current-state.json",
        retrieved_at=CUTOFF - timedelta(hours=1),
    )
    return ExternalResearchInputPacket(
        execution_id="p0-4a-test-605296",
        case_id="605296.SH",
        ticker="605296",
        security_id="SSE:605296",
        source_lane="SAVED_STOCK_OBSERVATION",
        selected_at=CUTOFF - timedelta(minutes=5),
        research_cutoff=CUTOFF,
        code_commit="d" * 40,
        current_state_commit="e" * 40,
        current_state_reading_hash="f" * 64,
        source_refs=(source_ref(),),
        seed_evidence_artifacts=(seed,),
        research_question="What explains the saved stock observation without assuming price proves fundamentals?",
        known_unknowns=("current earnings driver", "whether the driver is durable"),
        next_discriminating_search="read first-party operating and financial disclosures",
        method_version="RESEARCH_METHOD_V1",
        prompt_version="P0_4A_EXTERNAL_RESEARCH_V1",
        allowed_tools=("WEB_SEARCH", "WEB_OPEN", "GITHUB_READ"),
        candidate_output_prefix="research_runs/candidates/p0-4a-test-605296/",
        budget=budget(),
        untrusted_test_material=source_ref(path=FIXTURE),
    )


def discovery(p: ExternalResearchInputPacket) -> DiscoveryInput:
    seed = p.seed_evidence_artifacts[0]
    return DiscoveryInput(
        discovery_id="p0-4a-test-605296",
        source_lane=p.source_lane,
        ticker=p.ticker,
        security_id=p.security_id,
        economic_direction="saved price observation creates a research question only",
        as_of=p.research_cutoff,
        factual_observations=(
            DiscoveryObservation(
                statement="saved bounded Stock Reading surfaced the company",
                evidence_artifact_ids=(seed.id,),
            ),
        ),
        source_lineage=(
            DiscoverySource(
                evidence_artifact_id=seed.id,
                source_locator=seed.source_locator,
                available_at=seed.available_at,
            ),
        ),
        why_now="explicit single-case P0-4A selection",
        current_market_expression="saved observation only",
        contradiction_or_mapping_warning="price cannot establish the business driver",
        next_discriminating_search=p.next_discriminating_search,
        known_stop_or_downgrade_condition="stop if first-party evidence does not establish a discriminating business question",
    )


def pre(
    p: ExternalResearchInputPacket,
    supporting: EvidenceArtifact,
    *,
    route: PreResearchRoute = PreResearchRoute.CONTINUE_TO_QUICK,
) -> PreResearchResult:
    return PreResearchResult(
        discovery_id="p0-4a-test-605296",
        as_of=p.research_cutoff,
        what_is_this="single-company business-driver question",
        economic_direction="possible earnings/cost driver worth checking",
        why_surfaced_now="saved stock observation selected for bounded research",
        current_expression_or_leadership="saved price observation only",
        basic_business_role="integrated livestock company",
        potential_fundamental_driver="realized operating economics",
        current_market_expectation_hypothesis="market expectations are not established by the saved input",
        material_claims=(
            ResearchClaim(
                statement="first-party disclosure contains realized operating information",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(supporting.id,),
            ),
            ResearchClaim(
                statement="price strength alone does not establish a fundamental driver",
                kind=ResearchClaimKind.INFERENCE,
            ),
        ),
        largest_unknown="whether realized economics explain the observation and are durable",
        next_discriminating_search="compare realized earnings/cost evidence with contrary supply-price evidence",
        route=route,
        route_reason=f"test {route.value}",
    )


def quick(
    p: ExternalResearchInputPacket,
    pr: PreResearchResult,
    supporting: EvidenceArtifact,
    opposing: EvidenceArtifact,
    *,
    route: QuickResearchRoute = QuickResearchRoute.WAIT_FOR_TRIGGER,
    pre_hash: str | None = None,
) -> QuickResearchResult:
    return QuickResearchResult(
        discovery_id="p0-4a-test-605296",
        pre_research_hash=pre_hash or canonical_hash(pr),
        as_of=p.research_cutoff,
        business_model="integrated livestock producer",
        segment_mix="livestock and related processing",
        economic_role="producer exposed to selling price and cost",
        major_profit_drivers=("selling price", "unit cost"),
        industry_supply_demand_variables=("industry supply", "hog price"),
        value_chain_position="producer/processor",
        current_industry_state="mixed evidence",
        market_expectation_hypothesis="market expectation not directly observed",
        supporting_claims=(
            ResearchClaim(
                statement="company disclosure supports an operating-economics improvement question",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(supporting.id,),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="contrary first-party context limits a one-way interpretation",
                kind=ResearchClaimKind.MARKET_CONTEXT,
                evidence_artifact_ids=(opposing.id,),
            ),
        ),
        evidence_authority_assessment="first-party sources with explicit retained fields",
        variant_perception=None,
        unresolved_questions=("durability remains unknown",),
        next_discriminating_evidence=("next operating disclosure",),
        route=route,
        route_reason=f"test {route.value}",
    )


def receipt(
    p: ExternalResearchInputPacket,
    completion: ResearchExecutionCompletion = ResearchExecutionCompletion.COMPLETE,
    *,
    tool_calls_used: int = 4,
    query_count: int = 1,
    stop_reason: str | None = None,
) -> ResearchExecutionReceipt:
    events = (
        ResearchToolEvent(
            sequence=1,
            kind=ResearchToolKind.GITHUB_READ,
            status=ResearchToolStatus.SUCCEEDED,
            target="frozen input",
            observed_at=START,
            record_kind=ToolRecordKind.PLATFORM_TOOL_RETURN_REFERENCE,
            platform_reference="turn-test-github",
        ),
        ResearchToolEvent(
            sequence=2,
            kind=ResearchToolKind.WEB_SEARCH,
            status=ResearchToolStatus.SUCCEEDED,
            target="first-party disclosure search",
            observed_at=START + timedelta(minutes=1),
            record_kind=ToolRecordKind.PLATFORM_TOOL_RETURN_REFERENCE,
            platform_reference="turn-test-search",
            query_count=query_count,
        ),
        ResearchToolEvent(
            sequence=3,
            kind=ResearchToolKind.WEB_OPEN,
            status=ResearchToolStatus.SUCCEEDED,
            target="https://example.test/filing",
            observed_at=START + timedelta(minutes=2),
            record_kind=ToolRecordKind.PLATFORM_TOOL_RETURN_REFERENCE,
            platform_reference="turn-test-open-1",
        ),
        ResearchToolEvent(
            sequence=4,
            kind=ResearchToolKind.WEB_OPEN,
            status=ResearchToolStatus.SUCCEEDED,
            target="https://example.test/contrary",
            observed_at=START + timedelta(minutes=3),
            record_kind=ToolRecordKind.PLATFORM_TOOL_RETURN_REFERENCE,
            platform_reference="turn-test-open-2",
        ),
    )
    return ResearchExecutionReceipt(
        execution_id=p.execution_id,
        input_hash=canonical_hash(p),
        started_at=START,
        finished_at=FINISH,
        research_cutoff=p.research_cutoff,
        completion=completion,
        tool_events=events,
        source_dispositions=(
            ResearchSourceDisposition(
                source_locator="https://example.test/filing",
                opened=True,
                used_as_evidence=True,
                disposition="used",
                evidence_artifact_id=str(SUPPORT_ID),
            ),
        ),
        tool_calls_used=tool_calls_used,
        search_queries_used=query_count,
        source_reads_used=3,
        technical_retries_used=0,
        elapsed_minutes_observed=8,
        last_completed_stage="QUICK_RESEARCH" if completion is ResearchExecutionCompletion.COMPLETE else "PRE_RESEARCH",
        stop_or_failure_reason=stop_reason,
        model_or_executor="external web executor",
        model_exact_version=None,
        platform_task_id=None,
    )


def complete_candidate(
    p: ExternalResearchInputPacket,
    *,
    route: QuickResearchRoute = QuickResearchRoute.WAIT_FOR_TRIGGER,
    pre_hash: str | None = None,
) -> ExternalResearchCandidate:
    supporting = evidence(
        SUPPORT_ID,
        locator="https://example.test/filing",
        retrieved_at=START + timedelta(minutes=2),
    )
    opposing = evidence(
        OPPOSE_ID,
        locator="https://example.test/contrary",
        retrieved_at=START + timedelta(minutes=3),
    )
    pr = pre(p, supporting)
    rec = receipt(p)
    rec = rec.model_copy(
        update={
            "source_dispositions": (
                rec.source_dispositions[0],
                ResearchSourceDisposition(
                    source_locator="https://example.test/contrary",
                    opened=True,
                    used_as_evidence=True,
                    disposition="used as contrary context",
                    evidence_artifact_id=str(OPPOSE_ID),
                ),
            )
        }
    )
    return ExternalResearchCandidate(
        input_hash=canonical_hash(p),
        completion=ResearchExecutionCompletion.COMPLETE,
        discovery=discovery(p),
        pre_research=pr,
        quick_research=quick(p, pr, supporting, opposing, route=route, pre_hash=pre_hash),
        supplemental_evidence_artifacts=(supporting, opposing),
        receipt=rec,
        explicit_action_summary=("searched first-party sources", "checked contrary explanation"),
    )


def test_complete_candidate_runs_original_funnel_without_new_authority() -> None:
    p = packet()
    result = validate_external_research_candidate(packet=p, candidate=complete_candidate(p))
    assert result.status is ExternalResearchValidationStatus.VALIDATED_FUNNEL_RESULT
    assert result.funnel_result is not None
    assert result.funnel_result.terminal_state == "WAIT_FOR_TRIGGER"
    assert result.investment_authority == "NONE"
    assert result.human_attention_authority == "NONE"
    assert result.signal_transition_authority == "NONE"


def test_candidate_cannot_change_identity_or_cutoff() -> None:
    p = packet()
    candidate = complete_candidate(p)
    changed = candidate.model_copy(
        update={"discovery": candidate.discovery.model_copy(update={"ticker": "000000"})}
    )
    with pytest.raises(DomainValidationError, match="changed frozen case identity"):
        validate_external_research_candidate(packet=p, candidate=changed)


def test_quick_must_bind_exact_pre_hash() -> None:
    p = packet()
    candidate = complete_candidate(p, pre_hash="0" * 64)
    with pytest.raises(DomainValidationError, match="exact Pre-Research state"):
        validate_external_research_candidate(packet=p, candidate=candidate)


def test_future_evidence_is_rejected() -> None:
    p = packet()
    candidate = complete_candidate(p)
    future = candidate.supplemental_evidence_artifacts[0].model_copy(
        update={
            "available_at": p.research_cutoff + timedelta(seconds=1),
            "retrieved_at": START + timedelta(minutes=2),
        }
    )
    changed = candidate.model_copy(
        update={
            "supplemental_evidence_artifacts": (
                future,
                candidate.supplemental_evidence_artifacts[1],
            )
        }
    )
    with pytest.raises(DomainValidationError, match="not available by the research cutoff"):
        validate_external_research_candidate(packet=p, candidate=changed)


def test_wait_or_stop_pre_cannot_attach_quick() -> None:
    p = packet()
    candidate = complete_candidate(p)
    assert candidate.pre_research is not None
    wait_pre = candidate.pre_research.model_copy(update={"route": PreResearchRoute.WAIT_FOR_TRIGGER})
    changed = candidate.model_copy(update={"pre_research": wait_pre})
    with pytest.raises(DomainValidationError, match="cannot enter Quick Research"):
        validate_external_research_candidate(packet=p, candidate=changed)


def test_complete_continue_cannot_omit_quick() -> None:
    p = packet()
    supporting = evidence(SUPPORT_ID, locator="https://example.test/filing")
    candidate = ExternalResearchCandidate(
        input_hash=canonical_hash(p),
        completion=ResearchExecutionCompletion.COMPLETE,
        discovery=discovery(p),
        pre_research=pre(p, supporting),
        supplemental_evidence_artifacts=(supporting,),
        receipt=receipt(p),
    )
    with pytest.raises(DomainValidationError, match="requires a QuickResearchResult"):
        validate_external_research_candidate(packet=p, candidate=candidate)


def test_incomplete_continue_preserves_execution_gap_instead_of_fake_funnel() -> None:
    p = packet()
    supporting = evidence(SUPPORT_ID, locator="https://example.test/filing")
    incomplete_receipt = receipt(
        p,
        completion=ResearchExecutionCompletion.INCOMPLETE_BUDGET,
        stop_reason="budget exhausted before Quick",
    ).model_copy(update={"last_completed_stage": "PRE_RESEARCH"})
    candidate = ExternalResearchCandidate(
        input_hash=canonical_hash(p),
        completion=ResearchExecutionCompletion.INCOMPLETE_BUDGET,
        discovery=discovery(p),
        pre_research=pre(p, supporting),
        supplemental_evidence_artifacts=(supporting,),
        receipt=incomplete_receipt,
    )
    result = validate_external_research_candidate(packet=p, candidate=candidate)
    assert result.status is ExternalResearchValidationStatus.EXECUTION_GAP
    assert result.funnel_result is None
    assert "budget exhausted" in result.gap_reason


def test_source_unavailable_can_end_without_inventing_quiet_or_drop() -> None:
    p = packet()
    candidate = ExternalResearchCandidate(
        input_hash=canonical_hash(p),
        completion=ResearchExecutionCompletion.INCOMPLETE_SOURCE,
        receipt=ResearchExecutionReceipt(
            execution_id=p.execution_id,
            input_hash=canonical_hash(p),
            started_at=START,
            finished_at=START + timedelta(minutes=1),
            research_cutoff=p.research_cutoff,
            completion=ResearchExecutionCompletion.INCOMPLETE_SOURCE,
            tool_events=(),
            source_dispositions=(),
            tool_calls_used=0,
            search_queries_used=0,
            source_reads_used=0,
            technical_retries_used=0,
            elapsed_minutes_observed=1,
            last_completed_stage="INPUT",
            stop_or_failure_reason="qualified first-party source unavailable",
            model_or_executor="external web executor",
        ),
    )
    result = validate_external_research_candidate(packet=p, candidate=candidate)
    assert result.status is ExternalResearchValidationStatus.EXECUTION_GAP
    assert result.funnel_result is None


def test_declared_budget_is_enforced_post_hoc_even_when_executor_limit_is_soft() -> None:
    p = packet()
    candidate = complete_candidate(p)
    changed_receipt = candidate.receipt.model_copy(
        update={"tool_calls_used": p.budget.max_tool_calls + 1}
    )
    changed = candidate.model_copy(update={"receipt": changed_receipt})
    with pytest.raises((ValidationError, DomainValidationError)):
        validate_external_research_candidate(packet=p, candidate=changed)


def test_untrusted_fixture_cannot_be_promoted_to_qualified_evidence() -> None:
    p = packet()
    candidate = complete_candidate(p)
    injected = evidence(
        UUID("10000000-0000-0000-0000-000000000004"),
        locator=f"https://github.com/auguspp/decision-kernel/blob/main/{FIXTURE}",
        retrieved_at=START + timedelta(minutes=4),
    )
    changed = candidate.model_copy(
        update={
            "supplemental_evidence_artifacts": (
                *candidate.supplemental_evidence_artifacts,
                injected,
            )
        }
    )
    with pytest.raises(DomainValidationError, match="untrusted test material"):
        validate_external_research_candidate(packet=p, candidate=changed)


def test_input_and_candidate_hashes_are_deterministic() -> None:
    p = packet()
    candidate = complete_candidate(p)
    first = validate_external_research_candidate(packet=p, candidate=candidate)
    second = validate_external_research_candidate(packet=p, candidate=candidate)
    assert canonical_hash(p) == canonical_hash(packet())
    assert first.candidate_hash == second.candidate_hash
    assert canonical_hash(first) == canonical_hash(second)


def test_minimal_runtime_is_read_validation_only() -> None:
    source = Path("src/decision_kernel/runtime/external_research_execution.py").read_text()
    assert "import requests" not in source
    assert "run_live_package" not in source
    assert "run_research_workflow" not in source
    assert "workflow_dispatch" not in source
    assert "update_ref" not in source


def test_runtime_schema_is_generated_from_installed_models(tmp_path: Path) -> None:
    from decision_kernel.runtime.external_research_execution import main

    output = tmp_path / "schema.json"
    assert main(["schema", "--output", str(output)]) == 0
    schema = json.loads(output.read_text())
    assert set(schema) == {
        "ExternalResearchInputPacket",
        "ExternalResearchCandidate",
        "DiscoveryInput",
        "PreResearchResult",
        "QuickResearchResult",
        "EvidenceArtifact",
        "ResearchFunnelResult",
    }
    assert "properties" in schema["QuickResearchResult"]


def test_any_committed_real_candidates_are_deterministically_validated() -> None:
    root = Path("research_runs/candidates")
    for candidate_path in root.glob("**/candidate.json") if root.exists() else ():
        input_path = candidate_path.with_name("input.json")
        expected_path = candidate_path.with_name("funnel.json")
        assert input_path.exists(), candidate_path
        packet_model = ExternalResearchInputPacket.model_validate_json(input_path.read_text())
        candidate_model = ExternalResearchCandidate.model_validate_json(candidate_path.read_text())
        result = validate_external_research_candidate(
            packet=packet_model,
            candidate=candidate_model,
        )
        assert result.status is ExternalResearchValidationStatus.VALIDATED_FUNNEL_RESULT
        assert expected_path.exists(), candidate_path
        expected = json.loads(expected_path.read_text())
        assert result.funnel_result is not None
        assert result.funnel_result.model_dump(mode="json") == expected
