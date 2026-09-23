"""Pure single-Quick contracts and historical reading, not a second executor.

No provider, source acquisition, persistence, scheduling, admission or promotion.
The legacy models remain authoritative for v1 data. Host integration must still
bind actual calls, permission, source custody, consumption and normal delivery.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ..evidence import EvidenceArtifact
from ..identity import canonical_hash
from ..primitives import AwareDateTime, DomainValidationError, KernelModel
from ..research_funnel import DiscoveryInput, ResearchClaim, ResearchClaimKind
from ..research_workflow_v1 import ResearchFunnelTerminalState
from .external_research_execution import (
    ExternalResearchCandidate, ExternalResearchInputPacket,
    ExternalResearchValidationResult, ResearchExecutionCompletion,
    ResearchExecutionReceipt, ResearchInputSourceRef,
    _validate_candidate_identity, validate_external_research_candidate,
)

METHOD_VERSION = "single-quick-v1"
PROMPT_VERSION = "single-quick-outcomes-v1"
Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class QuickRoute(StrEnum):
    STOP = "STOP"
    WAIT_FOR_TRIGGER = "WAIT_FOR_TRIGGER"
    FULL_CANDIDATE = "FULL_CANDIDATE"


class Investigation(KernelModel):
    """A falsifiable commission, not a prescribed investigation procedure."""
    question: Text
    why_material: Text
    available_work: Text = Field(description=(
        "Concrete discriminating work possible now, not merely a future disclosure. "
        "Do not prescribe agent count, filenames, passes or a mandatory reasoning order."
    ))
    decision_test: Text = Field(description=(
        "Explain how different findings could change or refute the assessment. "
        "Full is allowed to replace the question and discover additional unknowns."
    ))


class QuickAssessment(KernelModel):
    """Model content only. Identity, clocks, hashes and authority belong to host."""
    explanation: Text = Field(description=(
        "Readable answer to what is worth attention and why: observation/why now, "
        "company economic connection and potential materiality, current evidence and "
        "existing-research relation when supplied. These are outcome responsibilities, "
        "not mandatory headings, reasoning order or a miniature Full Research report."
    ))
    claims: tuple[ResearchClaim, ...] = ()
    counterevidence_review: Text = Field(description=(
        "State the actual counterevidence review scope, adverse information, strongest "
        "alternative explanation and unexamined areas. Having no established contrary FACT is permitted; "
        "not checked is not ruled out. Keep inference honestly labelled."
    ))
    unknowns: tuple[Text, ...] = ()
    route: QuickRoute
    route_reason: Text
    investigation: Investigation | None = None
    wait_trigger: Text | None = None

    @model_validator(mode="after")
    def route_shape(self) -> "QuickAssessment":
        if self.route is QuickRoute.FULL_CANDIDATE:
            if self.investigation is None:
                raise ValueError("Full candidate requires a concrete investigation commission")
            if not any(c.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}
                       and c.evidence_artifact_ids for c in self.claims):
                raise ValueError("Full candidate requires a source-backed observation")
        if self.route is QuickRoute.WAIT_FOR_TRIGGER and self.wait_trigger is None:
            raise ValueError("WAIT requires a specific future trigger")
        # No variant-perception requirement, forced opposite FACT, UNKNOWN quota,
        # arbitrary quality score or automatic semantic certification.
        return self


class SingleQuickCandidate(KernelModel):
    input_hash: Hash
    completion: ResearchExecutionCompletion
    discovery: DiscoveryInput | None = None
    assessment: QuickAssessment | None = None
    supplemental_evidence_artifacts: tuple[EvidenceArtifact, ...] = ()
    receipt: ResearchExecutionReceipt
    explicit_action_summary: tuple[str, ...] = ()
    method_version: Literal["single-quick-v1"] = METHOD_VERSION
    schema_version: Literal[2] = 2

    @model_validator(mode="after")
    def result_shape(self) -> "SingleQuickCandidate":
        if self.completion is ResearchExecutionCompletion.COMPLETE:
            if self.discovery is None or self.assessment is None:
                raise ValueError("Complete single Quick requires Discovery and assessment")
        elif self.assessment is not None:
            raise ValueError("Execution gap cannot publish a business route; retain raw output")
        return self


class SingleQuickValidation(KernelModel):
    status: Literal["VALIDATED_QUICK_RESULT", "EXECUTION_GAP"]
    input_hash: Hash
    candidate_hash: Hash
    completion: ResearchExecutionCompletion
    terminal_state: ResearchFunnelTerminalState | None = None
    terminal_reason: Text | None = None
    gap_reason: Text | None = None
    validation_scope: Literal["IDENTITY_LINEAGE_ROUTE_SHAPE_NOT_RESEARCH_QUALITY"] = (
        "IDENTITY_LINEAGE_ROUTE_SHAPE_NOT_RESEARCH_QUALITY"
    )
    human_attention_authority: Literal["NONE"] = "NONE"
    investment_authority: Literal["NONE"] = "NONE"
    signal_transition_authority: Literal["NONE"] = "NONE"
    schema_version: Literal[2] = 2

    @model_validator(mode="after")
    def status_shape(self) -> "SingleQuickValidation":
        complete = self.completion is ResearchExecutionCompletion.COMPLETE
        if self.status == "VALIDATED_QUICK_RESULT":
            if not complete or self.terminal_state is None or self.terminal_reason is None or self.gap_reason is not None:
                raise ValueError("Validated Quick requires a complete outcome without a gap")
        elif complete or self.terminal_state is not None or self.terminal_reason is not None or self.gap_reason is None:
            raise ValueError("Execution gap requires no business outcome and an explicit reason")
        return self


def validate_single_quick(
    *, packet: ExternalResearchInputPacket, candidate: SingleQuickCandidate,
) -> SingleQuickValidation:
    # model_copy/model_construct are not validation. Revalidate at the boundary.
    packet = ExternalResearchInputPacket.model_validate(packet.model_dump(mode="json"))
    candidate = SingleQuickCandidate.model_validate(candidate.model_dump(mode="json"))
    if packet.schema_version != 1 or (packet.method_version, packet.prompt_version) != (METHOD_VERSION, PROMPT_VERSION):
        raise DomainValidationError("Unsupported single-Quick input contract")
    # Reuse the existing identity/receipt/budget/tool/source-disposition checks.
    # This helper only accesses fields shared by the two explicit candidate types.
    evidence = _validate_candidate_identity(packet, candidate)
    artifacts = {a.id: a for a in evidence}
    if candidate.discovery is not None:
        for source in candidate.discovery.source_lineage:
            artifact = artifacts.get(source.evidence_artifact_id)
            if artifact is None or (source.source_locator, source.available_at) != (artifact.source_locator, artifact.available_at):
                raise DomainValidationError("Quick Discovery lineage differs from supplied Evidence")
    if candidate.assessment is not None:
        for claim in candidate.assessment.claims:
            for eid in claim.evidence_artifact_ids:
                if eid not in artifacts or artifacts[eid].available_at > packet.research_cutoff:
                    raise DomainValidationError("Quick claim references missing or future Evidence")
    common = dict(input_hash=canonical_hash(packet), candidate_hash=canonical_hash(candidate),
                  completion=candidate.completion)
    if candidate.completion is not ResearchExecutionCompletion.COMPLETE:
        return SingleQuickValidation(status="EXECUTION_GAP", **common,
            gap_reason=candidate.receipt.stop_or_failure_reason or candidate.completion.value)
    assessment = candidate.assessment
    assert assessment is not None
    terminal = {
        QuickRoute.STOP: ResearchFunnelTerminalState.DROP_FOR_NOW,
        QuickRoute.WAIT_FOR_TRIGGER: ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
        QuickRoute.FULL_CANDIDATE: ResearchFunnelTerminalState.DEEPEN_REQUIRED,
    }[assessment.route]
    return SingleQuickValidation(status="VALIDATED_QUICK_RESULT", **common,
        terminal_state=terminal, terminal_reason=assessment.route_reason)


def read_saved_result(input_raw: bytes, candidate_raw: bytes) -> tuple[
    ExternalResearchInputPacket,
    ExternalResearchCandidate | SingleQuickCandidate,
    ExternalResearchValidationResult | SingleQuickValidation,
]:
    """Explicit version dispatch; no parser fallback, source fetch or promotion.

    Current callers must still verify source bytes, launch, permission and saved
    validation independently. Reading does not create a new consumption right.
    """
    from .external_research_identity import _json
    inp, value = _json(input_raw), _json(candidate_raw)
    version = inp.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise DomainValidationError("Unsupported input schema version")
    packet = ExternalResearchInputPacket.model_validate(inp)
    version = value.get("schema_version", 1)
    if type(version) is not int:
        raise DomainValidationError("Candidate schema version must be an integer")
    if packet.method_version == "research-funnel-v1" and version == 1:
        candidate = ExternalResearchCandidate.model_validate(value)
        return packet, candidate, validate_external_research_candidate(packet=packet, candidate=candidate)
    if packet.method_version == METHOD_VERSION and version == 2:
        candidate = SingleQuickCandidate.model_validate(value)
        return packet, candidate, validate_single_quick(packet=packet, candidate=candidate)
    raise DomainValidationError("Unknown or mixed research method/result versions")


def reading_view(input_raw: bytes, candidate_raw: bytes) -> dict:
    """Common, non-authoritative display data; not a fabricated v1 Funnel."""
    packet, candidate, validation = read_saved_result(input_raw, candidate_raw)
    single = isinstance(candidate, SingleQuickCandidate)
    if single:
        terminal = validation.terminal_state
        reason = validation.terminal_reason
        content = candidate.assessment
        explanation = content.explanation if content else None
        unknowns = list(content.unknowns) if content else list(packet.known_unknowns)
    else:
        funnel = validation.funnel_result
        terminal = funnel.terminal_state if funnel else None
        reason = funnel.terminal_reason if funnel else None
        explanation = reason
        pre = candidate.pre_research
        unknowns = list(candidate.quick_research.unresolved_questions) if candidate.quick_research else ([pre.largest_unknown] if pre else list(packet.known_unknowns))
    return {
        "format": "research-result-reading-v1", "method_version": packet.method_version,
        "result_schema_version": candidate.schema_version, "execution_id": packet.execution_id,
        "security_id": packet.security_id, "ticker": packet.ticker,
        "question": packet.research_question, "source_lane": packet.source_lane,
        "research_cutoff": packet.research_cutoff.isoformat(),
        "status": validation.status if single else validation.status.value,
        "terminal_state": terminal.value if terminal else None,
        "terminal_reason": reason, "explanation": explanation, "unknowns": unknowns,
        "pre_state": "NOT_APPLICABLE" if single else ("PRESENT" if candidate.pre_research else "MISSING"),
        "gap_reason": validation.gap_reason, "input_hash": validation.input_hash,
        "candidate_hash": validation.candidate_hash,
        "semantic_acceptance": "NOT_ESTABLISHED_BY_READER",
        "human_attention_authority": "NONE", "investment_authority": "NONE",
        "signal_transition_authority": "NONE", "new_research_execution": "NOT_EXECUTED",
    }


class FullResearchHandoff(KernelModel):
    """An immutable, non-executable commission referencing real saved inputs."""
    origin: Literal["QUICK_RESEARCH_CANDIDATE"] = "QUICK_RESEARCH_CANDIDATE"
    quick_input_source: ResearchInputSourceRef
    quick_candidate_source: ResearchInputSourceRef
    input_hash: Hash
    candidate_hash: Hash
    method_version: Literal["single-quick-v1"] = METHOD_VERSION
    execution_id: str
    security_id: str
    research_cutoff: AwareDateTime
    original_question: str
    proposed_investigation: Investigation
    input_known_unknowns: tuple[str, ...]
    open_unknowns: tuple[str, ...]
    source_refs: tuple[ResearchInputSourceRef, ...]
    execution_authority: Literal["NONE"] = "NONE"
    investment_authority: Literal["NONE"] = "NONE"
    schema_version: Literal[1] = 1


def build_full_handoff(
    *, input_source: dict, candidate_source: dict,
    input_raw: bytes, candidate_raw: bytes,
) -> FullResearchHandoff:
    """Bind supplied saved bytes; do not create evidence, authority or a Full run."""
    from .external_research_identity import _checked_source
    _checked_source(input_source, lambda _: input_raw)
    _checked_source(candidate_source, lambda _: candidate_raw)
    packet, candidate, checked = read_saved_result(input_raw, candidate_raw)
    if not isinstance(candidate, SingleQuickCandidate) or checked.status != "VALIDATED_QUICK_RESULT":
        raise DomainValidationError("Full handoff requires a validated single-Quick candidate")
    assessment = candidate.assessment
    if assessment is None or assessment.route is not QuickRoute.FULL_CANDIDATE:
        raise DomainValidationError("STOP, WAIT and gaps cannot generate a Full commission")
    if input_source.get("purpose") != "SINGLE_QUICK_INPUT" or candidate_source.get("purpose") != "SINGLE_QUICK_CANDIDATE":
        raise DomainValidationError("Full handoff source purpose differs")
    if input_source["path"] != packet.candidate_output_prefix + "input.json" or candidate_source["path"] != packet.candidate_output_prefix + "candidate.json":
        raise DomainValidationError("Full handoff source paths differ from retained candidate root")
    assert assessment.investigation is not None
    return FullResearchHandoff(
        quick_input_source=input_source, quick_candidate_source=candidate_source,
        input_hash=checked.input_hash, candidate_hash=checked.candidate_hash,
        execution_id=packet.execution_id, security_id=packet.security_id,
        research_cutoff=packet.research_cutoff, original_question=packet.research_question,
        proposed_investigation=assessment.investigation,
        input_known_unknowns=packet.known_unknowns,
        open_unknowns=assessment.unknowns,
        source_refs=packet.source_refs,
    )


def verify_full_handoff(
    handoff: FullResearchHandoff, *, input_raw: bytes, candidate_raw: bytes,
) -> FullResearchHandoff:
    """Rebuild the entire commission from exact parents before later consumption."""
    supplied = FullResearchHandoff.model_validate(handoff.model_dump(mode="json"))
    rebuilt = build_full_handoff(
        input_source=supplied.quick_input_source.model_dump(mode="json"),
        candidate_source=supplied.quick_candidate_source.model_dump(mode="json"),
        input_raw=input_raw, candidate_raw=candidate_raw,
    )
    if supplied != rebuilt:
        raise DomainValidationError("Full handoff differs from its exact Quick parents")
    return rebuilt
