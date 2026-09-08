from __future__ import annotations

import argparse
import json
from enum import StrEnum
from pathlib import Path

from pydantic import Field, model_validator

from ..evidence import EvidenceArtifact
from ..identity import canonical_hash
from ..primitives import AwareDateTime, DomainValidationError, KernelModel
from ..research_funnel import (
    DiscoveryInput,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    validate_pre_research_transition,
)
from ..research_workflow_v1 import ResearchFunnelResult, run_research_funnel


_HEX40 = r"^[0-9a-f]{40}$"
_HEX64 = r"^[0-9a-f]{64}$"


class BudgetEnforcement(StrEnum):
    HARD_RUNTIME = "HARD_RUNTIME"
    SOFT_EXECUTOR = "SOFT_EXECUTOR"


class ResearchExecutionCompletion(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE_BUDGET = "INCOMPLETE_BUDGET"
    INCOMPLETE_SOURCE = "INCOMPLETE_SOURCE"
    INCOMPLETE_TECHNICAL_FAILURE = "INCOMPLETE_TECHNICAL_FAILURE"


class ResearchToolKind(StrEnum):
    WEB_SEARCH = "WEB_SEARCH"
    WEB_OPEN = "WEB_OPEN"
    GITHUB_READ = "GITHUB_READ"
    OTHER_READ = "OTHER_READ"


class ResearchToolStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ToolRecordKind(StrEnum):
    PLATFORM_TOOL_RETURN_REFERENCE = "PLATFORM_TOOL_RETURN_REFERENCE"
    EXECUTOR_ACTION_SUMMARY = "EXECUTOR_ACTION_SUMMARY"


class ResearchExecutionBudget(KernelModel):
    max_tool_calls: int = Field(ge=1)
    max_search_queries: int = Field(ge=0)
    max_source_reads: int = Field(ge=1)
    max_technical_retries: int = Field(ge=0)
    max_elapsed_minutes: int = Field(ge=1)
    tool_calls_enforcement: BudgetEnforcement
    search_queries_enforcement: BudgetEnforcement
    source_reads_enforcement: BudgetEnforcement
    technical_retries_enforcement: BudgetEnforcement
    elapsed_time_enforcement: BudgetEnforcement


class ResearchInputSourceRef(KernelModel):
    repository: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    path: str = Field(min_length=1)
    git_blob: str = Field(pattern=_HEX40)
    sha256: str = Field(pattern=_HEX64)
    purpose: str = Field(min_length=1)


class ExternalResearchInputPacket(KernelModel):
    execution_id: str = Field(min_length=1, max_length=255)
    case_id: str = Field(min_length=1, max_length=255)
    ticker: str = Field(min_length=1, max_length=32)
    security_id: str = Field(min_length=1, max_length=128)
    source_lane: str = Field(min_length=1, max_length=128)
    selected_at: AwareDateTime
    research_cutoff: AwareDateTime
    code_commit: str = Field(pattern=_HEX40)
    current_state_commit: str = Field(pattern=_HEX40)
    current_state_reading_hash: str = Field(pattern=_HEX64)
    source_refs: tuple[ResearchInputSourceRef, ...] = Field(min_length=1)
    seed_evidence_artifacts: tuple[EvidenceArtifact, ...] = Field(min_length=1)
    research_question: str = Field(min_length=1)
    known_unknowns: tuple[str, ...] = Field(min_length=1)
    next_discriminating_search: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    allowed_tools: tuple[str, ...] = Field(min_length=1)
    candidate_output_prefix: str = Field(min_length=1)
    budget: ResearchExecutionBudget
    untrusted_test_material: ResearchInputSourceRef | None = None
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_input_contract(self) -> "ExternalResearchInputPacket":
        for field_name in ("selected_at", "research_cutoff"):
            value = getattr(self, field_name)
            if not hasattr(value, "tzinfo") or value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.selected_at > self.research_cutoff:
            raise ValueError("selected_at cannot be after research_cutoff")
        if any(item.available_at > self.research_cutoff for item in self.seed_evidence_artifacts):
            raise ValueError("seed Evidence must be available by the research cutoff")
        evidence_ids = {item.id for item in self.seed_evidence_artifacts}
        if len(evidence_ids) != len(self.seed_evidence_artifacts):
            raise ValueError("seed Evidence ids must be unique")
        if len({(r.repository, r.ref, r.path, r.git_blob) for r in self.source_refs}) != len(self.source_refs):
            raise ValueError("source refs must be unique")
        if not self.candidate_output_prefix.startswith("research_runs/candidates/"):
            raise ValueError("candidate outputs must stay in the isolated research_runs/candidates prefix")
        if self.untrusted_test_material is not None:
            fixture_key = (
                self.untrusted_test_material.repository,
                self.untrusted_test_material.ref,
                self.untrusted_test_material.path,
                self.untrusted_test_material.git_blob,
            )
            if fixture_key in {
                (r.repository, r.ref, r.path, r.git_blob) for r in self.source_refs
            }:
                raise ValueError("untrusted test material must remain outside qualified input sources")
        return self


class ResearchToolEvent(KernelModel):
    sequence: int = Field(ge=1)
    kind: ResearchToolKind
    status: ResearchToolStatus
    target: str = Field(min_length=1)
    observed_at: AwareDateTime
    record_kind: ToolRecordKind
    platform_reference: str | None = None
    query_count: int = Field(default=0, ge=0)
    technical_retry: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def validate_event_time(self) -> "ResearchToolEvent":
        if not hasattr(self.observed_at, "tzinfo") or self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("tool event observed_at must be timezone-aware")
        if self.kind is not ResearchToolKind.WEB_SEARCH and self.query_count:
            raise ValueError("query_count is only valid for WEB_SEARCH events")
        return self


class ResearchSourceDisposition(KernelModel):
    source_locator: str = Field(min_length=1)
    opened: bool
    used_as_evidence: bool
    disposition: str = Field(min_length=1)
    evidence_artifact_id: str | None = None


class ResearchExecutionReceipt(KernelModel):
    execution_id: str = Field(min_length=1, max_length=255)
    input_hash: str = Field(pattern=_HEX64)
    started_at: AwareDateTime
    finished_at: AwareDateTime
    research_cutoff: AwareDateTime
    completion: ResearchExecutionCompletion
    tool_events: tuple[ResearchToolEvent, ...]
    source_dispositions: tuple[ResearchSourceDisposition, ...]
    tool_calls_used: int = Field(ge=0)
    search_queries_used: int = Field(ge=0)
    source_reads_used: int = Field(ge=0)
    technical_retries_used: int = Field(ge=0)
    elapsed_minutes_observed: int = Field(ge=0)
    last_completed_stage: str = Field(min_length=1)
    stop_or_failure_reason: str | None = None
    model_or_executor: str = Field(min_length=1)
    model_exact_version: str | None = None
    platform_task_id: str | None = None
    private_chain_of_thought_recorded: bool = False

    @model_validator(mode="after")
    def validate_receipt(self) -> "ResearchExecutionReceipt":
        for field_name in ("started_at", "finished_at", "research_cutoff"):
            value = getattr(self, field_name)
            if not hasattr(value, "tzinfo") or value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")
        if self.started_at < self.research_cutoff:
            raise ValueError("execution cannot start before the frozen research cutoff")
        if self.finished_at < self.started_at:
            raise ValueError("receipt finished_at cannot be before started_at")
        sequences = [event.sequence for event in self.tool_events]
        if sequences != list(range(1, len(sequences) + 1)):
            raise ValueError("tool event sequences must be contiguous and ordered")
        if self.tool_calls_used != len(self.tool_events):
            raise ValueError("tool_calls_used must equal recorded tool event count")
        if self.search_queries_used != sum(event.query_count for event in self.tool_events):
            raise ValueError("search_queries_used must equal recorded query_count total")
        if self.technical_retries_used != sum(1 for event in self.tool_events if event.technical_retry):
            raise ValueError("technical_retries_used must match recorded technical retries")
        if self.source_reads_used != sum(
            1
            for event in self.tool_events
            if event.kind in {ResearchToolKind.WEB_OPEN, ResearchToolKind.GITHUB_READ, ResearchToolKind.OTHER_READ}
            and event.status is ResearchToolStatus.SUCCEEDED
        ):
            raise ValueError("source_reads_used must equal successful source-read event count")
        if self.private_chain_of_thought_recorded:
            raise ValueError("execution receipt must not record private chain of thought")
        return self


class ExternalResearchCandidate(KernelModel):
    input_hash: str = Field(pattern=_HEX64)
    completion: ResearchExecutionCompletion
    discovery: DiscoveryInput | None = None
    pre_research: PreResearchResult | None = None
    quick_research: QuickResearchResult | None = None
    supplemental_evidence_artifacts: tuple[EvidenceArtifact, ...] = ()
    receipt: ResearchExecutionReceipt
    explicit_action_summary: tuple[str, ...] = ()
    schema_version: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_shape(self) -> "ExternalResearchCandidate":
        if self.completion is ResearchExecutionCompletion.COMPLETE:
            if self.discovery is None or self.pre_research is None:
                raise ValueError("COMPLETE candidate requires Discovery and Pre Research")
        if self.quick_research is not None and (self.discovery is None or self.pre_research is None):
            raise ValueError("Quick Research cannot exist without Discovery and Pre Research")
        if self.completion is not ResearchExecutionCompletion.COMPLETE and self.quick_research is not None:
            raise ValueError("incomplete execution cannot publish a Quick Research result")
        return self


class ExternalResearchValidationStatus(StrEnum):
    VALIDATED_FUNNEL_RESULT = "VALIDATED_FUNNEL_RESULT"
    EXECUTION_GAP = "EXECUTION_GAP"


class ExternalResearchValidationResult(KernelModel):
    status: ExternalResearchValidationStatus
    input_hash: str = Field(pattern=_HEX64)
    candidate_hash: str = Field(pattern=_HEX64)
    completion: ResearchExecutionCompletion
    funnel_result: ResearchFunnelResult | None = None
    gap_reason: str | None = None
    human_attention_authority: str = "NONE"
    investment_authority: str = "NONE"
    signal_transition_authority: str = "NONE"
    schema_version: int = 1

    @model_validator(mode="after")
    def validate_result_authority(self) -> "ExternalResearchValidationResult":
        if {
            self.human_attention_authority,
            self.investment_authority,
            self.signal_transition_authority,
        } != {"NONE"}:
            raise ValueError("external research validation cannot gain authority")
        if self.status is ExternalResearchValidationStatus.VALIDATED_FUNNEL_RESULT:
            if self.funnel_result is None or self.gap_reason is not None:
                raise ValueError("validated result requires Funnel and no gap")
        else:
            if self.funnel_result is not None or not self.gap_reason:
                raise ValueError("execution gap requires a reason and no Funnel result")
        return self


def _validate_budget(packet: ExternalResearchInputPacket, receipt: ResearchExecutionReceipt) -> None:
    if receipt.execution_id != packet.execution_id:
        raise DomainValidationError("execution receipt changed execution identity")
    expected_input_hash = canonical_hash(packet)
    if receipt.input_hash != expected_input_hash:
        raise DomainValidationError("execution receipt changed input hash")
    if receipt.research_cutoff != packet.research_cutoff:
        raise DomainValidationError("execution receipt changed research cutoff")

    budget = packet.budget
    checks = (
        ("tool calls", receipt.tool_calls_used, budget.max_tool_calls),
        ("search queries", receipt.search_queries_used, budget.max_search_queries),
        ("source reads", receipt.source_reads_used, budget.max_source_reads),
        ("technical retries", receipt.technical_retries_used, budget.max_technical_retries),
        ("elapsed minutes", receipt.elapsed_minutes_observed, budget.max_elapsed_minutes),
    )
    exceeded = [f"{name} {used}>{limit}" for name, used, limit in checks if used > limit]
    if exceeded:
        raise DomainValidationError("research execution exceeded declared budget: " + ", ".join(exceeded))


def _validate_candidate_identity(
    packet: ExternalResearchInputPacket,
    candidate: ExternalResearchCandidate,
) -> tuple[EvidenceArtifact, ...]:
    expected_input_hash = canonical_hash(packet)
    if candidate.input_hash != expected_input_hash:
        raise DomainValidationError("external Research candidate does not reference the exact input")
    if candidate.receipt.completion is not candidate.completion:
        raise DomainValidationError("candidate completion and receipt completion disagree")
    _validate_budget(packet, candidate.receipt)
    allowed = set(packet.allowed_tools)
    used = {event.kind.value for event in candidate.receipt.tool_events}
    if not used.issubset(allowed):
        raise DomainValidationError(
            "execution receipt contains tool kinds outside the declared allowed_tools"
        )

    if candidate.discovery is not None:
        discovery = candidate.discovery
        if (
            discovery.ticker != packet.ticker
            or discovery.security_id != packet.security_id
            or discovery.source_lane != packet.source_lane
            or discovery.as_of != packet.research_cutoff
        ):
            raise DomainValidationError("external Research candidate changed frozen case identity or cutoff")
        expected_seed_ids = {item.id for item in packet.seed_evidence_artifacts}
        discovery_ids = {item.evidence_artifact_id for item in discovery.source_lineage}
        if discovery_ids != expected_seed_ids:
            raise DomainValidationError("Discovery must preserve the exact saved-observation seed Evidence")

    supplemental = candidate.supplemental_evidence_artifacts
    supplemental_ids = {item.id for item in supplemental}
    if len(supplemental_ids) != len(supplemental):
        raise DomainValidationError("supplemental Evidence ids must be unique")
    seed_ids = {item.id for item in packet.seed_evidence_artifacts}
    if seed_ids & supplemental_ids:
        raise DomainValidationError("supplemental Evidence cannot replace seed Evidence")
    if any(item.available_at > packet.research_cutoff for item in supplemental):
        raise DomainValidationError("supplemental Evidence was not available by the research cutoff")
    if any(
        item.retrieved_at < candidate.receipt.started_at
        or item.retrieved_at > candidate.receipt.finished_at
        for item in supplemental
    ):
        raise DomainValidationError("supplemental Evidence retrieval time must fall inside execution")
    if packet.untrusted_test_material is not None:
        fixture_path = packet.untrusted_test_material.path
        if any(fixture_path in item.source_locator for item in supplemental):
            raise DomainValidationError("untrusted test material cannot become qualified Evidence")

    evidence_ids = {str(item.id) for item in packet.seed_evidence_artifacts + supplemental}
    successful_read_targets = {
        event.target
        for event in candidate.receipt.tool_events
        if event.status is ResearchToolStatus.SUCCEEDED
        and event.kind in {
            ResearchToolKind.WEB_OPEN,
            ResearchToolKind.GITHUB_READ,
            ResearchToolKind.OTHER_READ,
        }
    }
    for disposition in candidate.receipt.source_dispositions:
        if disposition.opened and disposition.source_locator not in successful_read_targets:
            raise DomainValidationError("opened source disposition lacks a successful read event")
        if disposition.used_as_evidence:
            if not disposition.opened or disposition.evidence_artifact_id is None:
                raise DomainValidationError("Evidence disposition requires an opened source and Evidence id")
            if disposition.evidence_artifact_id not in evidence_ids:
                raise DomainValidationError("Evidence disposition references unknown Evidence")
    return packet.seed_evidence_artifacts + supplemental


def validate_external_research_candidate(
    *,
    packet: ExternalResearchInputPacket,
    candidate: ExternalResearchCandidate,
) -> ExternalResearchValidationResult:
    evidence_artifacts = _validate_candidate_identity(packet, candidate)
    candidate_hash = canonical_hash(candidate)

    if candidate.completion is not ResearchExecutionCompletion.COMPLETE:
        if candidate.discovery is not None and candidate.pre_research is not None:
            validate_pre_research_transition(
                candidate.discovery,
                candidate.pre_research,
                evidence_artifacts,
            )
            if candidate.pre_research.route is not PreResearchRoute.CONTINUE_TO_QUICK:
                raise DomainValidationError(
                    "incomplete execution cannot disguise a completed WAIT/STOP Pre route"
                )
        return ExternalResearchValidationResult(
            status=ExternalResearchValidationStatus.EXECUTION_GAP,
            input_hash=canonical_hash(packet),
            candidate_hash=candidate_hash,
            completion=candidate.completion,
            gap_reason=candidate.receipt.stop_or_failure_reason
            or candidate.completion.value,
        )

    assert candidate.discovery is not None
    assert candidate.pre_research is not None
    funnel = run_research_funnel(
        discovery=candidate.discovery,
        pre_research=candidate.pre_research,
        quick_research=candidate.quick_research,
        evidence_artifacts=evidence_artifacts,
    )
    return ExternalResearchValidationResult(
        status=ExternalResearchValidationStatus.VALIDATED_FUNNEL_RESULT,
        input_hash=canonical_hash(packet),
        candidate_hash=candidate_hash,
        completion=candidate.completion,
        funnel_result=funnel,
    )


def _read_model(path: Path, model_type):
    return model_type.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _schema_bundle() -> dict:
    return {
        "ExternalResearchInputPacket": ExternalResearchInputPacket.model_json_schema(),
        "ExternalResearchCandidate": ExternalResearchCandidate.model_json_schema(),
        "DiscoveryInput": DiscoveryInput.model_json_schema(),
        "PreResearchResult": PreResearchResult.model_json_schema(),
        "QuickResearchResult": QuickResearchResult.model_json_schema(),
        "EvidenceArtifact": EvidenceArtifact.model_json_schema(),
        "ResearchFunnelResult": ResearchFunnelResult.model_json_schema(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate one externally executed Research Method v1 candidate; no sensing or Research execution."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    schema = sub.add_parser("schema")
    schema.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--candidate", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "schema":
        _write_json(args.output, _schema_bundle())
        return 0

    packet = _read_model(args.input, ExternalResearchInputPacket)
    candidate = _read_model(args.candidate, ExternalResearchCandidate)
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    payload = result.model_dump(mode="json")
    payload["validation_hash"] = canonical_hash(result)
    _write_json(args.output, payload)
    print(f"INPUT_HASH={canonical_hash(packet)}")
    print(f"CANDIDATE_HASH={canonical_hash(candidate)}")
    print(f"VALIDATION_HASH={canonical_hash(result)}")
    print(f"STATUS={result.status.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
