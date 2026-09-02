from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from decision_kernel.identity import canonical_hash
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
from decision_kernel.runtime.disclosure_assessment import parse_disclosure_assessment_packet
from decision_kernel.runtime.disclosure_research import DisclosureResearchAssessment


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "eval/disclosure_cognition/catl-v0.json"
SCORER_PATH = ROOT / "eval/disclosure_cognition/score_candidate_run.py"


def _load_scorer():
    spec = importlib.util.spec_from_file_location("disclosure_cognition_eval_scorer", SCORER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCORER = _load_scorer()


def _corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def _packet(case: dict):
    return parse_disclosure_assessment_packet(
        (ROOT / case["packet_path"]).read_text(encoding="utf-8")
    )


def _discovery(packet) -> DiscoveryInput:
    evidence_ids = tuple(item.evidence_artifact.id for item in packet.evidence)
    return DiscoveryInput(
        discovery_id=f"eval:{packet.stock_code}:{packet.publication_date.isoformat()}",
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction="evaluate whether the disclosure changes frozen Research",
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement="the exact official disclosure batch requires semantic assessment",
                evidence_artifact_ids=evidence_ids,
            ),
        ),
        source_lineage=tuple(
            DiscoverySource(
                evidence_artifact_id=item.evidence_artifact.id,
                source_locator=item.evidence_artifact.source_locator,
                available_at=item.evidence_artifact.available_at,
            )
            for item in packet.evidence
        ),
        why_now="official Evidence is newer than frozen Research",
        next_discriminating_search="compare the filing with the frozen open questions",
        known_stop_or_downgrade_condition="stop when no decision-relevant context changes",
    )


def _pre(packet, discovery: DiscoveryInput, route: PreResearchRoute) -> PreResearchResult:
    primary = packet.evidence[0].evidence_artifact
    return PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=discovery.as_of,
        what_is_this="an exact official company disclosure batch",
        economic_direction="possible update to frozen company Research",
        why_surfaced_now="the official batch is newer than the frozen Research cutoff",
        basic_business_role="operating company",
        potential_fundamental_driver="operating evidence or capital allocation",
        current_market_expectation_hypothesis="the market may already expect the disclosed action",
        material_claims=(
            ResearchClaim(
                statement="the company published the exact official disclosure batch",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(primary.id,),
            ),
        ),
        largest_unknown="whether this changes a frozen decision-relevant question",
        next_discriminating_search="look for execution or operating evidence that discriminates the thesis",
        route=route,
        route_reason=f"eval candidate route {route.value}",
    )


def _quick(
    packet,
    discovery: DiscoveryInput,
    pre: PreResearchResult,
    route: QuickResearchRoute,
    *,
    support_artifact=None,
):
    primary = support_artifact or packet.evidence[0].evidence_artifact
    support = ResearchClaim(
        statement="the cited official filing is the primary bounded evidence for this candidate pass",
        kind=ResearchClaimKind.FACT,
        evidence_artifact_ids=(primary.id,),
    )
    contradictory = ResearchClaim(
        statement="the same cited filing leaves a material uncertainty unresolved",
        kind=ResearchClaimKind.MARKET_CONTEXT,
        evidence_artifact_ids=(primary.id,),
    )
    return QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=discovery.as_of,
        business_model="battery manufacturer",
        segment_mix="power and storage batteries plus related businesses",
        economic_role="scaled capital-intensive battery supplier",
        major_profit_drivers=("utilization", "pricing", "mix"),
        industry_supply_demand_variables=("capacity", "EV demand", "storage demand"),
        value_chain_position="battery cell and system producer",
        market_expectation_hypothesis="growth is expected but capital intensity remains debated",
        supporting_claims=(support,),
        contradictory_claims=((contradictory,) if route is QuickResearchRoute.DEEPEN else ()),
        evidence_authority_assessment="exact official packet Evidence only",
        variant_perception=(
            "execution could change the capital-return interpretation"
            if route is QuickResearchRoute.DEEPEN
            else None
        ),
        unresolved_questions=("does later execution change cash conversion?",),
        next_discriminating_evidence=("actual execution and next operating disclosure",),
        route=route,
        route_reason=f"eval candidate quick route {route.value}",
    )


def _assessment_for(
    case: dict,
    *,
    force_deepen: bool = False,
    force_no_text_reference: bool = False,
) -> DisclosureResearchAssessment:
    packet = _packet(case)
    discovery = _discovery(packet)

    if force_deepen:
        pre = _pre(packet, discovery, PreResearchRoute.CONTINUE_TO_QUICK)
        quick = _quick(packet, discovery, pre, QuickResearchRoute.DEEPEN)
    elif case["gold_terminal_stage"] == "QUICK_RESEARCH":
        pre = _pre(packet, discovery, PreResearchRoute.CONTINUE_TO_QUICK)
        support_artifact = None
        if force_no_text_reference:
            support_artifact = next(
                item.evidence_artifact
                for item in packet.evidence
                if item.text_status.value == "NO_TEXT"
            )
        quick = _quick(
            packet,
            discovery,
            pre,
            QuickResearchRoute.WAIT_FOR_TRIGGER,
            support_artifact=support_artifact,
        )
    elif case["gold_terminal_state"] == "DROP_FOR_NOW":
        pre = _pre(packet, discovery, PreResearchRoute.STOP)
        quick = None
    else:
        pre = _pre(packet, discovery, PreResearchRoute.WAIT_FOR_TRIGGER)
        quick = None

    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
    )


def _write_run(
    tmp_path: Path,
    *,
    deepen_case_id: str | None = None,
    corrupt_case_id: str | None = None,
    no_text_case_id: str | None = None,
) -> Path:
    corpus = _corpus()
    run_cases = []
    for case in corpus["cases"]:
        assessment = _assessment_for(
            case,
            force_deepen=case["case_id"] == deepen_case_id,
            force_no_text_reference=case["case_id"] == no_text_case_id,
        )
        payload = assessment.model_dump(mode="json")
        if case["case_id"] == corrupt_case_id:
            payload["assessment_input_hash"] = "f" * 64
        assessment_path = tmp_path / f"{case['case_id']}.json"
        assessment_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        run_cases.append(
            {
                "case_id": case["case_id"],
                "assessment_path": assessment_path.name,
                "raw_response_path": assessment_path.name,
                "invoked_at": "2026-09-02T08:00:00Z",
            }
        )

    run_path = tmp_path / "candidate-run.json"
    run_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "test-candidate-run",
                "corpus_id": corpus["corpus_id"],
                "producer": {
                    "provider": "test-provider",
                    "model": "test-model",
                    "producer_version": "producer-v1",
                    "prompt_version": "prompt-v1",
                },
                "cases": run_cases,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return run_path


def test_candidate_scorer_reports_exact_route_and_stage_matches(tmp_path: Path) -> None:
    report = SCORER.score_candidate_run(_write_run(tmp_path))
    summary = report["summary"]

    assert summary == {
        "corpus_cases": 6,
        "submitted_cases": 6,
        "valid_cases": 6,
        "invalid_cases": 0,
        "missing_cases": 0,
        "unexpected_cases": 0,
        "terminal_matches": 6,
        "terminal_drifts": 0,
        "stage_matches": 6,
        "stage_drifts": 0,
        "stage_inflations": 0,
        "stage_deflations": 0,
        "candidate_deepen_cases": 0,
        "gold_deepen_cases": 0,
        "deepen_overcalls": 0,
        "candidate_claims": 7,
        "evidenced_claims": 7,
        "no_text_reference_claims": 0,
        "no_text_only_claims": 0,
        "gold_no_claim_reference_claims": 0,
    }
    assert SCORER.report_exit_code(report) == 0
    assert all(case["investment_authority"] == "NONE" for case in report["cases"])
    assert all(len(case["raw_response_sha256"]) == 64 for case in report["cases"])
    assert report["investment_authority"] == "NONE"


def test_candidate_scorer_measures_deepen_bias_without_failing_the_run(tmp_path: Path) -> None:
    report = SCORER.score_candidate_run(
        _write_run(tmp_path, deepen_case_id="300750-2026-08-04")
    )
    summary = report["summary"]

    assert summary["valid_cases"] == 6
    assert summary["invalid_cases"] == 0
    assert summary["terminal_matches"] == 5
    assert summary["terminal_drifts"] == 1
    assert summary["stage_matches"] == 5
    assert summary["stage_drifts"] == 1
    assert summary["stage_inflations"] == 1
    assert summary["candidate_deepen_cases"] == 1
    assert summary["deepen_overcalls"] == 1
    assert report["terminal_confusion"]["WAIT_FOR_TRIGGER->DEEPEN_REQUIRED"] == 1
    assert SCORER.report_exit_code(report) == 0


def test_candidate_scorer_flags_claims_citing_no_text_official_evidence(tmp_path: Path) -> None:
    report = SCORER.score_candidate_run(
        _write_run(tmp_path, no_text_case_id="300750-2026-08-12")
    )
    summary = report["summary"]

    assert summary["valid_cases"] == 6
    assert summary["terminal_matches"] == 6
    assert summary["stage_matches"] == 6
    assert summary["no_text_reference_claims"] == 1
    assert summary["no_text_only_claims"] == 1
    assert summary["gold_no_claim_reference_claims"] == 1
    case = next(
        item for item in report["cases"] if item["case_id"] == "300750-2026-08-12"
    )
    signals = case["claim_reference_signals"]
    assert signals["no_text_reference_claims"][0]["announcement_ids"] == ["1225470689"]
    assert signals["gold_no_claim_reference_claims"][0]["announcement_ids"] == [
        "1225470689"
    ]
    assert SCORER.report_exit_code(report) == 0


def test_candidate_scorer_fails_only_when_candidate_is_not_auditable(tmp_path: Path) -> None:
    report = SCORER.score_candidate_run(
        _write_run(tmp_path, corrupt_case_id="300750-2026-07-30")
    )
    summary = report["summary"]

    assert summary["valid_cases"] == 5
    assert summary["invalid_cases"] == 1
    assert summary["missing_cases"] == 0
    invalid = next(
        case for case in report["cases"] if case["case_id"] == "300750-2026-07-30"
    )
    assert invalid["status"] == "INVALID"
    assert "exact assessment input" in invalid["error"]
    assert SCORER.report_exit_code(report) == 1
