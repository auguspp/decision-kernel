"""Thin Human-origin Direct Deep loop; no Funnel, provider, Market or persistence."""
from __future__ import annotations
from enum import StrEnum
from typing import Callable, Literal
from uuid import UUID
from pydantic import Field, model_validator
from ..evidence import EvidenceArtifact
from ..identity import canonical_hash
from ..primitives import AwareDateTime, CurrencyCode, DomainValidationError, KernelModel
from ..research import ResearchStatus
from ..research_commit import ResearchCommitPackage, validate_research_commit_package
from .external_research_execution import ResearchExecutionBudget, ResearchExecutionCompletion, ResearchExecutionReceipt

class UnknownStatus(StrEnum):
    OPEN="OPEN"; REDUCED="REDUCED"; CLOSED="CLOSED"; STOP_PUBLIC_EVIDENCE_EXHAUSTED="STOP_PUBLIC_EVIDENCE_EXHAUSTED"
class UnknownImportance(StrEnum):
    DECISIVE="DECISIVE"; HIGH="HIGH"; MEDIUM="MEDIUM"; LOW="LOW"
class StopReason(StrEnum):
    SUFFICIENTLY_COMPRESSED="SUFFICIENTLY_COMPRESSED"; PUBLIC_EVIDENCE_EXHAUSTED="PUBLIC_EVIDENCE_EXHAUSTED"
    MARGINAL_VALUE_LOW="MARGINAL_VALUE_LOW"; BUDGET_REACHED="BUDGET_REACHED"; TECHNICAL_GAP="TECHNICAL_GAP"
COMPLETE_STOPS={StopReason.SUFFICIENTLY_COMPRESSED,StopReason.PUBLIC_EVIDENCE_EXHAUSTED,StopReason.MARGINAL_VALUE_LOW}

class Unknown(KernelModel):
    id:str=Field(min_length=1,max_length=128); question:str=Field(min_length=1,max_length=2048)
    importance:UnknownImportance; why_it_matters:str=Field(min_length=1,max_length=4096)
    next_discriminating_evidence:str=Field(min_length=1,max_length=4096)
    can_public_evidence_reduce_it:bool; status:UnknownStatus

class Request(KernelModel):
    execution_id:str=Field(min_length=1,max_length=255); human_request:str=Field(min_length=1,max_length=4096)
    ticker:str=Field(min_length=1,max_length=32); company_name:str=Field(min_length=1,max_length=255)
    exchange:str=Field(min_length=1,max_length=32); currency:CurrencyCode
    requested_at:AwareDateTime; research_cutoff:AwareDateTime; max_passes:int=Field(ge=1,le=12)
    execution_budget:ResearchExecutionBudget; seed_evidence_artifacts:tuple[EvidenceArtifact,...]=()
    method_version:Literal["full-research-operating-v3"]="full-research-operating-v3"
    route:Literal["HUMAN_ORIGIN_DIRECT_DEEP"]="HUMAN_ORIGIN_DIRECT_DEEP"
    investment_authority:Literal["NONE"]="NONE"; schema_version:Literal[1]=1
    @model_validator(mode="after")
    def check(self):
        if self.research_cutoff>self.requested_at: raise ValueError("research cutoff cannot follow Human request")
        ids=[x.id for x in self.seed_evidence_artifacts]
        if len(set(ids))!=len(ids): raise ValueError("seed Evidence ids must be unique")
        if any(x.available_at>self.research_cutoff for x in self.seed_evidence_artifacts): raise ValueError("seed Evidence must be PIT-available")
        return self

class Pass(KernelModel):
    pass_index:int=Field(ge=1); focus:str=Field(min_length=1,max_length=255); summary:str=Field(min_length=1,max_length=8192)
    unknowns:tuple[Unknown,...]=Field(min_length=1); new_evidence_artifacts:tuple[EvidenceArtifact,...]=()
    receipt:ResearchExecutionReceipt; stop_reason:StopReason|None=None; final_research_package:ResearchCommitPackage|None=None
    schema_version:Literal[1]=1
    @model_validator(mode="after")
    def check(self):
        if len({x.id for x in self.unknowns})!=len(self.unknowns): raise ValueError("UNKNOWN ids must be unique")
        if len({x.id for x in self.new_evidence_artifacts})!=len(self.new_evidence_artifacts): raise ValueError("Evidence ids must be unique")
        if self.stop_reason is None and self.final_research_package is not None: raise ValueError("non-terminal pass cannot finalize Research")
        if self.stop_reason in COMPLETE_STOPS and self.final_research_package is None: raise ValueError("completed stop requires Research package")
        if self.stop_reason is not None and self.stop_reason not in COMPLETE_STOPS and self.final_research_package is not None: raise ValueError("incomplete stop cannot finalize Research")
        return self

class Result(KernelModel):
    request_hash:str=Field(pattern=r"^[0-9a-f]{64}$"); passes:tuple[Pass,...]=Field(min_length=1)
    completion:ResearchExecutionCompletion; stop_reason:StopReason; final_unknowns:tuple[Unknown,...]=Field(min_length=1)
    evidence_artifacts:tuple[EvidenceArtifact,...]; final_research_package:ResearchCommitPackage|None=None
    route:Literal["HUMAN_ORIGIN_DIRECT_DEEP"]="HUMAN_ORIGIN_DIRECT_DEEP"; market_status:Literal["NOT_REQUESTED"]="NOT_REQUESTED"
    odds_status:Literal["NOT_COMPUTED"]="NOT_COMPUTED"; human_acceptance:Literal["NOT_ESTABLISHED_BY_THIS_OPERATION"]="NOT_ESTABLISHED_BY_THIS_OPERATION"
    investment_authority:Literal["NONE"]="NONE"; schema_version:Literal[1]=1
    @model_validator(mode="after")
    def check(self):
        if self.passes[-1].unknowns!=self.final_unknowns: raise ValueError("final UNKNOWN ledger differs")
        if self.completion is ResearchExecutionCompletion.COMPLETE:
            if self.stop_reason not in COMPLETE_STOPS or self.final_research_package is None: raise ValueError("completed result lacks terminal Research")
        elif self.final_research_package is not None: raise ValueError("incomplete result cannot carry final Research")
        return self

Executor=Callable[[Request,tuple[Pass,...]],Pass]
def _emap(items:tuple[EvidenceArtifact,...])->dict[UUID,EvidenceArtifact]: return {x.id:x for x in items}
def _budget(req:Request,passes:tuple[Pass,...]):
    used=(sum(p.receipt.tool_calls_used for p in passes),sum(p.receipt.search_queries_used for p in passes),sum(p.receipt.source_reads_used for p in passes),sum(p.receipt.technical_retries_used for p in passes),sum(p.receipt.elapsed_minutes_observed for p in passes))
    lim=(req.execution_budget.max_tool_calls,req.execution_budget.max_search_queries,req.execution_budget.max_source_reads,req.execution_budget.max_technical_retries,req.execution_budget.max_elapsed_minutes)
    if any(a>b for a,b in zip(used,lim)): raise DomainValidationError("Direct Deep execution exceeded declared budget")
def _pass(req:Request,h:str,p:Pass,prior:tuple[Pass,...],e:dict[UUID,EvidenceArtifact]):
    if p.pass_index!=len(prior)+1: raise DomainValidationError("pass index changed or skipped")
    r=p.receipt
    if (r.execution_id,r.input_hash,r.research_cutoff)!=(req.execution_id,h,req.research_cutoff): raise DomainValidationError("pass changed execution/request/cutoff identity")
    if r.started_at<req.requested_at or (prior and r.started_at<prior[-1].receipt.finished_at): raise DomainValidationError("pass chronology invalid")
    expected=ResearchExecutionCompletion.COMPLETE
    if p.stop_reason is StopReason.BUDGET_REACHED: expected=ResearchExecutionCompletion.INCOMPLETE_BUDGET
    if p.stop_reason is StopReason.TECHNICAL_GAP: expected=ResearchExecutionCompletion.INCOMPLETE_TECHNICAL_FAILURE
    if r.completion is not expected: raise DomainValidationError("receipt completion disagrees with stop state")
    if prior:
        before={x.id:x for x in prior[-1].unknowns}; after={x.id:x for x in p.unknowns}
        if set(before)-set(after): raise DomainValidationError("UNKNOWN cannot silently disappear")
        if any(before[i].question!=after[i].question for i in set(before)&set(after)): raise DomainValidationError("UNKNOWN identity changed question")
    for x in p.new_evidence_artifacts:
        if x.id in e: raise DomainValidationError("Evidence cannot replace existing artifact")
        if x.available_at>req.research_cutoff: raise DomainValidationError("Evidence unavailable at research cutoff")
        if not r.started_at<=x.retrieved_at<=r.finished_at: raise DomainValidationError("Evidence retrieval outside pass clock")
def _final(req:Request,p:Pass,e:dict[UUID,EvidenceArtifact]):
    pkg=p.final_research_package
    if pkg is None: raise DomainValidationError("completed stop lacks Research package")
    validate_research_commit_package(pkg)
    s=pkg.research_snapshot
    if pkg.schema_version!=2 or pkg.framing is not None or s.status is not ResearchStatus.REVIEW: raise DomainValidationError("Direct Deep requires REVIEW Research-only schema v2")
    if (s.ticker,s.company_name,s.exchange,s.currency,s.as_of_datetime)!=(req.ticker,req.company_name,req.exchange,req.currency,req.research_cutoff): raise DomainValidationError("final Research changed case/cutoff")
    if not s.research_origin or not s.research_origin.startswith("HUMAN_ORIGIN_DIRECT_DEEP"): raise DomainValidationError("final Research lost Human-origin provenance")
    if s.open_questions!=tuple(x.question for x in p.unknowns if x.status is not UnknownStatus.CLOSED): raise DomainValidationError("open_questions differ from unresolved UNKNOWN ledger")
    pe=_emap(pkg.evidence_artifacts)
    if set(pe)!=set(e) or any(canonical_hash(pe[i])!=canonical_hash(e[i]) for i in e): raise DomainValidationError("final Research Evidence differs from accumulated Evidence")
    if pkg.proposed_committed_at<p.receipt.finished_at: raise DomainValidationError("commit proposal precedes final pass")

def run_direct_deep(*,request:Request,execute_pass:Executor)->Result:
    req=Request.model_validate(request.model_dump(mode="python")); h=canonical_hash(req); e=_emap(req.seed_evidence_artifacts); ps=[]
    for _ in range(req.max_passes):
        p=execute_pass(req,tuple(ps))
        if not isinstance(p,Pass): raise DomainValidationError("executor must return Direct Deep Pass")
        p=Pass.model_validate(p.model_dump(mode="python")); _pass(req,h,p,tuple(ps),e)
        for x in p.new_evidence_artifacts:e[x.id]=x
        ps.append(p); _budget(req,tuple(ps))
        if p.stop_reason is None: continue
        if p.stop_reason in COMPLETE_STOPS:
            _final(req,p,e); return Result(request_hash=h,passes=tuple(ps),completion=ResearchExecutionCompletion.COMPLETE,stop_reason=p.stop_reason,final_unknowns=p.unknowns,evidence_artifacts=tuple(e.values()),final_research_package=p.final_research_package)
        c=ResearchExecutionCompletion.INCOMPLETE_BUDGET if p.stop_reason is StopReason.BUDGET_REACHED else ResearchExecutionCompletion.INCOMPLETE_TECHNICAL_FAILURE
        return Result(request_hash=h,passes=tuple(ps),completion=c,stop_reason=p.stop_reason,final_unknowns=p.unknowns,evidence_artifacts=tuple(e.values()))
    p=ps[-1]
    return Result(request_hash=h,passes=tuple(ps),completion=ResearchExecutionCompletion.INCOMPLETE_BUDGET,stop_reason=StopReason.BUDGET_REACHED,final_unknowns=p.unknowns,evidence_artifacts=tuple(e.values()))
