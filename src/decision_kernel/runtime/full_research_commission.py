"""One non-executing Full commission for qualified Quick and Human origins.

Only origin adapters inspect upstream forms. No researcher, queue, provider,
source acquisition or persistence is implemented here. Live admission still
owes original permissions, exact remote bytes/clocks, consumption and budget.
"""
from __future__ import annotations

from typing import Annotated, Literal
from pydantic import Field, model_validator

from ..primitives import AwareDateTime, DomainValidationError, KernelModel
from ..identity import canonical_hash
from ..evidence import EvidenceArtifact
from .external_research_execution import ResearchInputSourceRef, ResearchExecutionBudget
from . import external_research_identity as identity
from . import single_quick_contract as quick

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]


class QuickOrigin(KernelModel):
    research_origin: Literal["QUICK_RESEARCH_CANDIDATE"] = "QUICK_RESEARCH_CANDIDATE"
    handoff: quick.FullResearchHandoff
    question_source: ResearchInputSourceRef


class HumanOrigin(KernelModel):
    research_origin: Literal["HUMAN_ORIGIN_DIRECT_DEEP"] = "HUMAN_ORIGIN_DIRECT_DEEP"
    request_source: ResearchInputSourceRef
    permission_source: ResearchInputSourceRef
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class FullResearchCommission(KernelModel):
    """Full-level meaning is shared; source proof is explicitly discriminated."""
    security_id: Text
    ticker: Text
    question_id: Text
    question: Text
    scope: Text
    why_now: Text
    research_cutoff: AwareDateTime
    source_refs: tuple[ResearchInputSourceRef, ...]
    seed_evidence_artifacts: tuple[EvidenceArtifact, ...] = ()
    prior_research: tuple[ResearchInputSourceRef, ...] = ()
    predecessor_relation: Text
    known_limitations: tuple[Text, ...] = ()
    origin: Annotated[QuickOrigin | HumanOrigin, Field(discriminator="research_origin")]
    # A candidate does not allocate a budget or create an execution ID.
    execution_id: Text | None = None
    permission_source: ResearchInputSourceRef | None = None
    execution_budget: ResearchExecutionBudget | None = None
    outcome_contract: Literal["research-outcome-contract-v1"] = "research-outcome-contract-v1"
    execution_authority: Literal["NONE"] = "NONE"
    investment_authority: Literal["NONE"] = "NONE"
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def scope_shape(self):
        if isinstance(self.origin, QuickOrigin):
            h = self.origin.handoff
            if (self.security_id, self.research_cutoff, self.question) != (
                    h.security_id, h.research_cutoff, h.proposed_investigation.question):
                raise ValueError("Quick commission changed origin identity or question")
            if any(x is not None for x in (self.execution_id, self.permission_source, self.execution_budget)):
                raise ValueError("Quick proposal does not allocate Full execution")
        elif self.execution_id is None or self.execution_budget is None or self.permission_source != self.origin.permission_source:
            raise ValueError("Human commission requires its original bounded request and permission")
        return self


def from_quick(*, input_source, candidate_source, question_source,
               input_raw: bytes, candidate_raw: bytes, question_raw: bytes) -> FullResearchCommission:
    from .reviewed_question_input import _declaration, PURPOSE
    h = quick.build_full_handoff(input_source=input_source, candidate_source=candidate_source,
                                 input_raw=input_raw, candidate_raw=candidate_raw)
    identity._checked_source(question_source, lambda _: question_raw)
    q = _declaration(question_raw)
    packet, _, _ = quick.read_saved_result(input_raw, candidate_raw)
    if (question_source.get("purpose") != PURPOSE
        or ResearchInputSourceRef.model_validate(question_source) not in packet.source_refs
        or (q["security_id"], q["ticker"], q["question"]) != (packet.security_id, packet.ticker, packet.research_question)):
        raise DomainValidationError("Full commission question root differs from Quick input")
    return FullResearchCommission(security_id=packet.security_id, ticker=packet.ticker,
        question_id=q["question_id"], question=h.proposed_investigation.question,
        scope=h.proposed_investigation.available_work, why_now=h.proposed_investigation.why_material,
        research_cutoff=h.research_cutoff, source_refs=h.source_refs,
        seed_evidence_artifacts=packet.seed_evidence_artifacts,
        prior_research=q["existing_research_relation"]["source_refs"],
        predecessor_relation=q["existing_research_relation"]["note"],
        known_limitations=tuple(dict.fromkeys((*h.input_known_unknowns, *h.open_unknowns))),
        origin=QuickOrigin(handoff=h, question_source=question_source))


def from_human(*, request_source, permission_source, request_raw: bytes,
               permission_raw: bytes) -> FullResearchCommission:
    """Adapt an explicit existing Direct Full request, without a fake Quick.

    Permission bytes are retained proof, not interpreted as independent consent.
    Runtime still checks the actual Human authorization and its allowed scope.
    """
    from .direct_deep import Request
    identity._checked_source(request_source, lambda _: request_raw)
    identity._checked_source(permission_source, lambda _: permission_raw)
    if request_source.get("purpose") != "HUMAN_DIRECT_FULL_REQUEST" or permission_source.get("purpose") != "HUMAN_FULL_PERMISSION":
        raise DomainValidationError("Human Full origin source purposes differ")
    req = Request.model_validate(identity._json(request_raw))
    # This adapter carries the existing request verbatim in origin provenance.
    # It does not carry max_passes into the researcher's outcome contract.
    sid = req.exchange + ":" + req.ticker
    return FullResearchCommission(security_id=sid, ticker=req.ticker,
        question_id=req.execution_id, question=req.human_request, scope=req.human_request,
        why_now="Explicit Human request; consult its exact retained context, not a synthesized Quick.",
        research_cutoff=req.research_cutoff, source_refs=(request_source, permission_source),
        seed_evidence_artifacts=req.seed_evidence_artifacts,
        predecessor_relation="Human request origin; no inherited Quick or prior Research acceptance.",
        origin=HumanOrigin(request_source=request_source, permission_source=permission_source,
                           request_hash=canonical_hash(req)),
        execution_id=req.execution_id, permission_source=permission_source, execution_budget=req.execution_budget)


def verify(commission: FullResearchCommission, *, load) -> FullResearchCommission:
    """Rebuild from supplied exact parents. Callback must enforce remote custody."""
    value = FullResearchCommission.model_validate(commission.model_dump(mode="json"))
    if isinstance(value.origin, QuickOrigin):
        h = value.origin.handoff
        ins = h.quick_input_source.model_dump(mode="json")
        cs = h.quick_candidate_source.model_dump(mode="json")
        qs = value.origin.question_source.model_dump(mode="json")
        rebuilt = from_quick(input_source=ins, candidate_source=cs, question_source=qs,
                             input_raw=load(ins), candidate_raw=load(cs), question_raw=load(qs))
    else:
        rs = value.origin.request_source.model_dump(mode="json")
        ps = value.origin.permission_source.model_dump(mode="json")
        rebuilt = from_human(request_source=rs, permission_source=ps,
                             request_raw=load(rs), permission_raw=load(ps))
    if value != rebuilt:
        raise DomainValidationError("Full commission differs from its exact origin")
    return rebuilt
