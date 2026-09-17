"""#321 Direct Deep mechanics; retained Hengrui replay is not fresh quality acceptance."""
from __future__ import annotations
from datetime import timedelta
from pathlib import Path
import socket
from uuid import uuid4
import pytest
from decision_kernel.identity import canonical_hash
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage, commit_research_package, research_commit_information_bundle_hash
from decision_kernel.runtime.direct_deep import Pass, Request, StopReason, Unknown, UnknownImportance, UnknownStatus, run_direct_deep
from decision_kernel.runtime.external_research_execution import BudgetEnforcement, ResearchExecutionBudget, ResearchExecutionCompletion, ResearchExecutionReceipt

ROOT=Path(__file__).resolve().parents[1]
HENGRUI=ROOT/"docs/readings/600276-hengrui-research-commit-2026-09-17/input.json"
CLOSED_Q="Double counting deposit interest and cash principal"

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*a,**k): raise AssertionError("Direct Deep contract test cannot request network")
    monkeypatch.setattr(socket,"create_connection",denied); monkeypatch.setattr(socket.socket,"connect",denied)

def pkg(): return ResearchCommitPackage.model_validate_json(HENGRUI.read_bytes())
def budget(**u):
    d=dict(max_tool_calls=12,max_search_queries=4,max_source_reads=8,max_technical_retries=1,max_elapsed_minutes=30,
        tool_calls_enforcement=BudgetEnforcement.HARD_RUNTIME,search_queries_enforcement=BudgetEnforcement.HARD_RUNTIME,
        source_reads_enforcement=BudgetEnforcement.HARD_RUNTIME,technical_retries_enforcement=BudgetEnforcement.HARD_RUNTIME,
        elapsed_time_enforcement=BudgetEnforcement.HARD_RUNTIME); d.update(u); return ResearchExecutionBudget(**d)
def req(*,max_passes=4,b=None):
    p=pkg(); s=p.research_snapshot
    return Request(execution_id="hengrui-direct-deep-replay-20260917",human_request="深度研究恒瑞医药",ticker=s.ticker,
        company_name=s.company_name,exchange=s.exchange,currency=s.currency,requested_at=s.created_at-timedelta(minutes=39),
        research_cutoff=s.as_of_datetime,max_passes=max_passes,execution_budget=b or budget(),seed_evidence_artifacts=p.evidence_artifacts)
def ledger(p,index):
    closed=(UnknownStatus.OPEN,UnknownStatus.REDUCED,UnknownStatus.CLOSED)[min(index-1,2)]
    open_state=(UnknownStatus.OPEN,UnknownStatus.REDUCED,UnknownStatus.STOP_PUBLIC_EVIDENCE_EXHAUSTED)[min(index-1,2)]
    rows=[Unknown(id="double-count",question=CLOSED_Q,importance=UnknownImportance.HIGH,why_it_matters="Avoid double counting owner cash.",
        next_discriminating_evidence="Reconcile cash principal and interest.",can_public_evidence_reduce_it=index<3,status=closed)]
    for i,q in enumerate(p.research_snapshot.open_questions,1):
        rows.append(Unknown(id=f"u{i}",question=q,importance=UnknownImportance.DECISIVE,why_it_matters="Retained Round-3 decisive UNKNOWN.",
            next_discriminating_evidence=f"Historical replay boundary {i}; no fresh retrieval claimed.",can_public_evidence_reduce_it=index<3,status=open_state))
    return tuple(rows)
def receipt(r,index,*,completion=ResearchExecutionCompletion.COMPLETE,elapsed=1,input_hash=None,cutoff=None):
    start=r.requested_at+timedelta(minutes=index*2)
    return ResearchExecutionReceipt(execution_id=r.execution_id,input_hash=input_hash or canonical_hash(r),started_at=start,
        finished_at=start+timedelta(minutes=1),research_cutoff=cutoff or r.research_cutoff,completion=completion,tool_events=(),
        source_dispositions=(),tool_calls_used=0,search_queries_used=0,source_reads_used=0,technical_retries_used=0,
        elapsed_minutes_observed=elapsed,last_completed_stage=f"direct-deep-pass-{index}",model_or_executor="retained-replay")
def executor(final=None):
    final=final or pkg()
    def run(r,prior):
        i=len(prior)+1
        return Pass(pass_index=i,focus=("economic structure","owner cash/adversarial","UNKNOWN stop")[i-1],summary=f"retained replay {i}",
            unknowns=ledger(final,i),receipt=receipt(r,i),stop_reason=StopReason.PUBLIC_EVIDENCE_EXHAUSTED if i==3 else None,
            final_research_package=final if i==3 else None)
    return run
def rehash(p,**updates):
    s=p.research_snapshot.model_copy(update=updates); h=research_commit_information_bundle_hash(research_snapshot=s,evidence_artifacts=p.evidence_artifacts)
    return p.model_copy(update={"research_snapshot":s.model_copy(update={"information_bundle_hash":h})})

def test_one_human_request_runs_three_passes_without_funnel_and_leaves_review_package(monkeypatch):
    import decision_kernel.research_workflow_v1 as funnel
    monkeypatch.setattr(funnel,"run_research_funnel",lambda **_:(_ for _ in ()).throw(AssertionError("Funnel called")))
    out=run_direct_deep(request=req(),execute_pass=executor())
    assert len(out.passes)==3 and out.completion is ResearchExecutionCompletion.COMPLETE
    assert out.stop_reason is StopReason.PUBLIC_EVIDENCE_EXHAUSTED and out.route=="HUMAN_ORIGIN_DIRECT_DEEP"
    assert out.market_status=="NOT_REQUESTED" and out.odds_status=="NOT_COMPUTED" and out.investment_authority=="NONE"
    assert out.final_unknowns[0].status is UnknownStatus.CLOSED
    assert all(x.status is UnknownStatus.STOP_PUBLIC_EVIDENCE_EXHAUSTED for x in out.final_unknowns[1:])
    assert out.final_research_package.research_snapshot.status is ResearchStatus.REVIEW
    assert out.final_research_package.research_snapshot.open_questions==tuple(x.question for x in out.final_unknowns if x.status is not UnknownStatus.CLOSED)
    assert commit_research_package(out.final_research_package).research_snapshot.status is ResearchStatus.COMMITTED

def test_real_hengrui_replay_preserves_exact_package_evidence_and_cutoff():
    p=pkg(); r=req(); out=run_direct_deep(request=r,execute_pass=executor(p))
    assert out.final_research_package==p and out.final_research_package.research_snapshot.as_of_datetime==r.research_cutoff
    assert out.evidence_artifacts==p.evidence_artifacts and all(x.retrieved_at<r.requested_at for x in out.evidence_artifacts)
    assert p.research_snapshot.research_origin.startswith("HUMAN_ORIGIN_DIRECT_DEEP")

def test_pass_budget_exhaustion_and_technical_gap_stay_incomplete():
    r=req(max_passes=2)
    def keep(r,prior):
        i=len(prior)+1; return Pass(pass_index=i,focus="continue",summary="continue",unknowns=ledger(pkg(),i),receipt=receipt(r,i))
    out=run_direct_deep(request=r,execute_pass=keep)
    assert out.completion is ResearchExecutionCompletion.INCOMPLETE_BUDGET and out.final_research_package is None
    def gap(r,prior):
        return Pass(pass_index=1,focus="source",summary="technical gap",unknowns=ledger(pkg(),1),
            receipt=receipt(r,1,completion=ResearchExecutionCompletion.INCOMPLETE_TECHNICAL_FAILURE),stop_reason=StopReason.TECHNICAL_GAP)
    out=run_direct_deep(request=req(),execute_pass=gap)
    assert out.completion is ResearchExecutionCompletion.INCOMPLETE_TECHNICAL_FAILURE and out.final_research_package is None

@pytest.mark.parametrize("damage",["drop","question","input","cutoff"])
def test_pass_identity_unknown_continuity_and_cutoff_fail_closed(damage):
    r=req()
    def bad(r,prior):
        i=len(prior)+1; rows=list(ledger(pkg(),i)); ih=None; cutoff=None
        if i==2 and damage=="drop": rows.pop(0)
        if i==2 and damage=="question": rows[0]=rows[0].model_copy(update={"question":"changed"})
        if i==1 and damage=="input": ih="f"*64
        if i==1 and damage=="cutoff": cutoff=r.research_cutoff-timedelta(seconds=1)
        return Pass(pass_index=i,focus="bad",summary="bad",unknowns=tuple(rows),receipt=receipt(r,i,input_hash=ih,cutoff=cutoff))
    with pytest.raises(DomainValidationError): run_direct_deep(request=r,execute_pass=bad)

def test_cumulative_execution_budget_is_enforced():
    r=req(b=budget(max_elapsed_minutes=1))
    def bad(r,prior): return Pass(pass_index=1,focus="budget",summary="over",unknowns=ledger(pkg(),1),receipt=receipt(r,1,elapsed=2))
    with pytest.raises(DomainValidationError,match="exceeded declared budget"): run_direct_deep(request=r,execute_pass=bad)

def test_evidence_replacement_or_future_availability_fails_closed():
    p=pkg(); r=req(); seed=p.evidence_artifacts[0]
    future=seed.model_copy(update={"id":uuid4(),"available_at":r.research_cutoff+timedelta(seconds=1),"retrieved_at":r.requested_at+timedelta(minutes=3)})
    for item in (seed,future):
        def bad(r,prior,item=item): return Pass(pass_index=1,focus="evidence",summary="bad",unknowns=ledger(p,1),new_evidence_artifacts=(item,),receipt=receipt(r,1))
        with pytest.raises(DomainValidationError): run_direct_deep(request=r,execute_pass=bad)

@pytest.mark.parametrize("damage",["questions","case","evidence"])
def test_final_package_must_match_unknowns_case_and_exact_accumulated_evidence(damage):
    p=pkg()
    if damage=="questions": p=rehash(p,open_questions=("different",))
    elif damage=="case": p=rehash(p,ticker="000001")
    else:
        changed=p.evidence_artifacts[0].model_copy(update={"license_terms_note":"changed"}); ev=(changed,*p.evidence_artifacts[1:])
        s=p.research_snapshot; h=research_commit_information_bundle_hash(research_snapshot=s,evidence_artifacts=ev)
        p=p.model_copy(update={"evidence_artifacts":ev,"research_snapshot":s.model_copy(update={"information_bundle_hash":h})})
    with pytest.raises(DomainValidationError): run_direct_deep(request=req(),execute_pass=executor(p))
