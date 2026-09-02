from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Literal, TextIO

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from decision_kernel.identity import canonical_hash
from decision_kernel.research_workflow_v1 import ResearchFunnelStage, ResearchFunnelTerminalState
from decision_kernel.runtime.disclosure_assessment import parse_disclosure_assessment_packet
from decision_kernel.runtime.disclosure_research import (
    DisclosureResearchAssessment,
    run_disclosure_research_assessment,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_PATH = Path(__file__).resolve().with_name("catl-v0.json")
_STAGE_RANK = {
    ResearchFunnelStage.PRE_RESEARCH.value: 0,
    ResearchFunnelStage.QUICK_RESEARCH.value: 1,
}


class ProducerProvenance(BaseModel):
    """Operational provenance for one replaceable semantic Research producer."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    producer_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)


class CandidateCase(BaseModel):
    """One producer invocation bound to one corpus case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    assessment_path: str = Field(min_length=1)
    raw_response_path: str | None = None
    invoked_at: AwareDatetime


class CandidateRunManifest(BaseModel):
    """Auditable description of a candidate cognition run, not investment state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    run_id: str = Field(min_length=1)
    corpus_id: str = Field(min_length=1)
    producer: ProducerProvenance
    cases: tuple[CandidateCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> "CandidateRunManifest":
        case_ids = tuple(case.case_id for case in self.cases)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("candidate run requires unique case ids")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _resolve_candidate_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (manifest_path.parent / path).resolve()


def _resolve_corpus_asset(corpus_path: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    repo_candidate = (REPO_ROOT / path).resolve()
    if repo_candidate.exists():
        return repo_candidate
    return (corpus_path.parent / path).resolve()


def _load_json_object(path: Path, *, label: str) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return raw, payload


def _candidate_structure_counts(assessment: DisclosureResearchAssessment) -> tuple[int, int]:
    unknown_count = 1 if assessment.pre_research.largest_unknown.strip() else 0
    next_evidence_count = 1 if assessment.pre_research.next_discriminating_search.strip() else 0
    if assessment.quick_research is not None:
        unknown_count += len(assessment.quick_research.unresolved_questions)
        next_evidence_count += len(assessment.quick_research.next_discriminating_evidence)
    return unknown_count, next_evidence_count


def _candidate_claims(assessment: DisclosureResearchAssessment):
    for claim in assessment.pre_research.material_claims:
        yield "PRE_RESEARCH", "material", claim
    if assessment.quick_research is None:
        return
    for claim in assessment.quick_research.supporting_claims:
        yield "QUICK_RESEARCH", "supporting", claim
    for claim in assessment.quick_research.contradictory_claims:
        yield "QUICK_RESEARCH", "contradictory", claim


def _claim_reference_signals(packet, assessment: DisclosureResearchAssessment, gold_case: dict[str, Any]):
    """Report deterministic suspicious-reference signals without claiming semantic entailment."""

    official_by_evidence_id = {
        item.evidence_artifact.id: item
        for item in packet.evidence
    }
    no_text_evidence_ids = {
        evidence_id
        for evidence_id, item in official_by_evidence_id.items()
        if item.text_status.value == "NO_TEXT"
    }
    gold_no_claim_announcement_ids = set(
        gold_case.get("gold_no_claim_from_announcement_ids", ())
    )

    total_claims = 0
    evidenced_claims = 0
    no_text_reference_claims: list[dict[str, Any]] = []
    no_text_only_claims = 0
    gold_no_claim_reference_claims: list[dict[str, Any]] = []

    for stage, group, claim in _candidate_claims(assessment):
        total_claims += 1
        refs = set(claim.evidence_artifact_ids)
        if refs:
            evidenced_claims += 1
        official_refs = refs & official_by_evidence_id.keys()
        no_text_refs = official_refs & no_text_evidence_ids
        no_text_announcements = sorted(
            official_by_evidence_id[evidence_id].announcement_id
            for evidence_id in no_text_refs
        )
        gold_no_claim_refs = sorted(
            official_by_evidence_id[evidence_id].announcement_id
            for evidence_id in official_refs
            if official_by_evidence_id[evidence_id].announcement_id
            in gold_no_claim_announcement_ids
        )
        claim_identity = {
            "stage": stage,
            "group": group,
            "kind": claim.kind.value,
            "statement_sha256": _sha256_bytes(claim.statement.encode("utf-8")),
        }
        if no_text_announcements:
            no_text_reference_claims.append(
                {
                    **claim_identity,
                    "announcement_ids": no_text_announcements,
                }
            )
            if refs and refs <= no_text_evidence_ids:
                no_text_only_claims += 1
        if gold_no_claim_refs:
            gold_no_claim_reference_claims.append(
                {
                    **claim_identity,
                    "announcement_ids": gold_no_claim_refs,
                }
            )

    return {
        "candidate_claims": total_claims,
        "evidenced_claims": evidenced_claims,
        "no_text_reference_claims": no_text_reference_claims,
        "no_text_only_claims": no_text_only_claims,
        "gold_no_claim_reference_claims": gold_no_claim_reference_claims,
    }


def score_candidate_run(
    run_manifest_path: Path,
    *,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    """Score one candidate run against frozen inputs without making the gold Kernel law.

    Deterministic checks cover schema/input binding, exact Evidence lineage, Research Funnel
    terminal/stage drift, cognitive-budget inflation, and suspicious references to packet Evidence
    with no extracted text. Semantic entailment quality of prose, unknowns, and next-evidence
    requests is intentionally not guessed by string heuristics.
    """

    run_manifest_path = run_manifest_path.resolve()
    corpus_path = corpus_path.resolve()

    run_raw, run_payload = _load_json_object(run_manifest_path, label="candidate run manifest")
    run = CandidateRunManifest.model_validate(run_payload)
    _corpus_raw, corpus = _load_json_object(corpus_path, label="cognition corpus")

    corpus_id = corpus.get("corpus_id")
    if run.corpus_id != corpus_id:
        raise ValueError(
            f"candidate run corpus_id {run.corpus_id!r} does not match corpus {corpus_id!r}"
        )

    raw_cases = corpus.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("cognition corpus must contain a non-empty cases array")
    gold_by_id: dict[str, dict[str, Any]] = {}
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("cognition corpus cases must be JSON objects")
        case_id = raw_case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("cognition corpus case_id must be a non-empty string")
        if case_id in gold_by_id:
            raise ValueError(f"duplicate cognition corpus case_id: {case_id}")
        gold_by_id[case_id] = raw_case

    candidate_by_id = {case.case_id: case for case in run.cases}
    missing_case_ids = sorted(set(gold_by_id) - set(candidate_by_id))
    unexpected_case_ids = sorted(set(candidate_by_id) - set(gold_by_id))

    terminal_confusion: Counter[str] = Counter()
    case_reports: list[dict[str, Any]] = []
    valid_cases = 0
    invalid_cases = 0
    terminal_matches = 0
    stage_matches = 0
    stage_inflations = 0
    stage_deflations = 0
    candidate_deepen_cases = 0
    deepen_overcalls = 0
    candidate_claims = 0
    evidenced_claims = 0
    no_text_reference_claims = 0
    no_text_only_claims = 0
    gold_no_claim_reference_claims = 0

    for case_id, gold_case in gold_by_id.items():
        gold_terminal = ResearchFunnelTerminalState(gold_case["gold_terminal_state"]).value
        gold_stage = ResearchFunnelStage(gold_case["gold_terminal_stage"]).value
        candidate_case = candidate_by_id.get(case_id)
        if candidate_case is None:
            case_reports.append(
                {
                    "case_id": case_id,
                    "status": "MISSING",
                    "gold_terminal_state": gold_terminal,
                    "gold_terminal_stage": gold_stage,
                }
            )
            continue

        report: dict[str, Any] = {
            "case_id": case_id,
            "status": "INVALID",
            "gold_terminal_state": gold_terminal,
            "gold_terminal_stage": gold_stage,
            "invoked_at": candidate_case.invoked_at.isoformat(),
        }
        try:
            packet_path = _resolve_corpus_asset(corpus_path, gold_case["packet_path"])
            packet = parse_disclosure_assessment_packet(packet_path.read_text(encoding="utf-8"))
            expected_input_hash = gold_case["assessment_input_hash"]
            if packet.assessment_input_hash != expected_input_hash:
                raise ValueError(
                    "corpus packet assessment input hash does not match gold manifest"
                )

            assessment_path = _resolve_candidate_path(
                run_manifest_path, candidate_case.assessment_path
            )
            assessment_raw = assessment_path.read_bytes()
            assessment = DisclosureResearchAssessment.model_validate_json(assessment_raw)
            raw_response_path = _resolve_candidate_path(
                run_manifest_path,
                candidate_case.raw_response_path or candidate_case.assessment_path,
            )
            raw_response = raw_response_path.read_bytes()

            result = run_disclosure_research_assessment(
                packet=packet,
                assessment=assessment,
            )
            candidate_terminal = result.terminal_state.value
            candidate_stage = result.terminal_stage.value
            terminal_match = candidate_terminal == gold_terminal
            stage_match = candidate_stage == gold_stage
            stage_inflation = _STAGE_RANK[candidate_stage] > _STAGE_RANK[gold_stage]
            stage_deflation = _STAGE_RANK[candidate_stage] < _STAGE_RANK[gold_stage]
            deepen_overcall = (
                candidate_terminal == ResearchFunnelTerminalState.DEEPEN_REQUIRED.value
                and gold_terminal != ResearchFunnelTerminalState.DEEPEN_REQUIRED.value
            )
            unknown_count, next_evidence_count = _candidate_structure_counts(assessment)
            claim_signals = _claim_reference_signals(packet, assessment, gold_case)

            valid_cases += 1
            terminal_matches += int(terminal_match)
            stage_matches += int(stage_match)
            stage_inflations += int(stage_inflation)
            stage_deflations += int(stage_deflation)
            candidate_deepen_cases += int(
                candidate_terminal == ResearchFunnelTerminalState.DEEPEN_REQUIRED.value
            )
            deepen_overcalls += int(deepen_overcall)
            candidate_claims += claim_signals["candidate_claims"]
            evidenced_claims += claim_signals["evidenced_claims"]
            no_text_reference_claims += len(claim_signals["no_text_reference_claims"])
            no_text_only_claims += claim_signals["no_text_only_claims"]
            gold_no_claim_reference_claims += len(
                claim_signals["gold_no_claim_reference_claims"]
            )
            terminal_confusion[f"{gold_terminal}->{candidate_terminal}"] += 1

            report.update(
                {
                    "status": "VALID",
                    "assessment_input_hash": assessment.assessment_input_hash,
                    "raw_response_sha256": _sha256_bytes(raw_response),
                    "assessment_json_sha256": _sha256_bytes(assessment_raw),
                    "parsed_assessment_hash": canonical_hash(assessment),
                    "supplemental_evidence_count": len(
                        assessment.supplemental_evidence_artifacts
                    ),
                    "candidate_pre_route": assessment.pre_research.route.value,
                    "candidate_quick_route": (
                        assessment.quick_research.route.value
                        if assessment.quick_research is not None
                        else None
                    ),
                    "candidate_terminal_state": candidate_terminal,
                    "candidate_terminal_stage": candidate_stage,
                    "terminal_match": terminal_match,
                    "stage_match": stage_match,
                    "stage_inflation": stage_inflation,
                    "stage_deflation": stage_deflation,
                    "deepen_overcall": deepen_overcall,
                    "unknown_structure_count": unknown_count,
                    "next_evidence_structure_count": next_evidence_count,
                    "claim_reference_signals": claim_signals,
                    "investment_authority": result.investment_authority,
                }
            )
        except (OSError, ValueError) as exc:
            invalid_cases += 1
            report["error_type"] = type(exc).__name__
            report["error"] = str(exc)

        case_reports.append(report)

    summary = {
        "corpus_cases": len(gold_by_id),
        "submitted_cases": len(candidate_by_id),
        "valid_cases": valid_cases,
        "invalid_cases": invalid_cases,
        "missing_cases": len(missing_case_ids),
        "unexpected_cases": len(unexpected_case_ids),
        "terminal_matches": terminal_matches,
        "terminal_drifts": valid_cases - terminal_matches,
        "stage_matches": stage_matches,
        "stage_drifts": valid_cases - stage_matches,
        "stage_inflations": stage_inflations,
        "stage_deflations": stage_deflations,
        "candidate_deepen_cases": candidate_deepen_cases,
        "gold_deepen_cases": sum(
            case["gold_terminal_state"] == ResearchFunnelTerminalState.DEEPEN_REQUIRED.value
            for case in gold_by_id.values()
        ),
        "deepen_overcalls": deepen_overcalls,
        "candidate_claims": candidate_claims,
        "evidenced_claims": evidenced_claims,
        "no_text_reference_claims": no_text_reference_claims,
        "no_text_only_claims": no_text_only_claims,
        "gold_no_claim_reference_claims": gold_no_claim_reference_claims,
    }

    return {
        "schema_version": 1,
        "run_id": run.run_id,
        "corpus_id": corpus_id,
        "run_manifest_sha256": _sha256_bytes(run_raw),
        "producer": run.producer.model_dump(mode="json"),
        "coverage": {
            "missing_case_ids": missing_case_ids,
            "unexpected_case_ids": unexpected_case_ids,
        },
        "summary": summary,
        "terminal_confusion": dict(sorted(terminal_confusion.items())),
        "cases": case_reports,
        "semantic_quality_note": (
            "V0 flags structurally invalid Evidence references and suspicious claims citing "
            "official packet Evidence with NO_TEXT extraction, but it does not infer prose "
            "entailment. Unknown quality, next-evidence quality, and whether a valid citation "
            "actually supports a claim remain semantic review questions."
        ),
        "investment_authority": "NONE",
    }


def report_exit_code(report: dict[str, Any]) -> int:
    """Fail only for unauditable/incomplete candidate runs, never for semantic drift alone."""

    summary = report["summary"]
    if (
        summary["invalid_cases"]
        or summary["missing_cases"]
        or summary["unexpected_cases"]
    ):
        return 1
    return 0


def _print_summary(report: dict[str, Any], *, stdout: TextIO) -> None:
    summary = report["summary"]
    producer = report["producer"]
    print(
        "DISCLOSURE COGNITION EVAL: "
        f"{summary['valid_cases']} valid / {summary['corpus_cases']} corpus | "
        f"terminal {summary['terminal_matches']}/{summary['valid_cases']} match | "
        f"stage {summary['stage_matches']}/{summary['valid_cases']} match | "
        f"stage-inflation={summary['stage_inflations']} | "
        f"deepen-overcalls={summary['deepen_overcalls']} | "
        f"no-text-claim-refs={summary['no_text_reference_claims']} | "
        f"invalid={summary['invalid_cases']} | missing={summary['missing_cases']}",
        file=stdout,
    )
    print(
        "PRODUCER: "
        f"{producer['provider']} / {producer['model']} | "
        f"producer={producer['producer_version']} | prompt={producer['prompt_version']}",
        file=stdout,
    )
    print("INVESTMENT AUTHORITY: NONE", file=stdout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score one external disclosure-cognition candidate run against frozen PIT cases."
    )
    parser.add_argument("run_manifest", type=Path)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_CORPUS_PATH,
        help="Frozen cognition corpus manifest. Defaults to catl-v0.json beside this script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON report path. Without this flag, the full report is printed as JSON.",
    )
    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        report = score_candidate_run(args.run_manifest, corpus_path=args.corpus)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2

    if args.output is None:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), file=stdout)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _print_summary(report, stdout=stdout)
        print(f"REPORT: {args.output}", file=stdout)

    return report_exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
