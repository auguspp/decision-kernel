"""Fresh #321 Hengrui Direct Deep dogfood replay; no network, Market or Odds."""
from __future__ import annotations

import json
from pathlib import Path
import socket

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    ResearchCommitResult,
    commit_research_package,
)
from decision_kernel.runtime.direct_deep import Pass, Request, run_direct_deep


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs/readings/600276-hengrui-direct-deep-dogfood-2026-09-17"
PREDECESSOR = ROOT / "docs/readings/600276-hengrui-research-commit-2026-09-17/research-commit.json"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("retained Direct Deep dogfood replay must not use network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def load(name: str):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def rehydrate_passes():
    package = ResearchCommitPackage.model_validate(load("research-package.json"))
    evidence = {str(item.id): item for item in package.evidence_artifacts}
    result = []
    for record in load("pass-records.json")["passes"]:
        payload = {
            key: value for key, value in record.items()
            if key not in {"new_evidence_ids", "final_research_package_ref"}
        }
        payload["new_evidence_artifacts"] = tuple(
            evidence[item_id] for item_id in record["new_evidence_ids"]
        )
        payload["final_research_package"] = (
            package if record["final_research_package_ref"] == "research-package.json" else None
        )
        result.append(Pass.model_validate(payload))
    return tuple(result)


def test_fresh_hengrui_one_root_request_replays_exact_four_pass_result_and_commit():
    request = Request.model_validate(load("request.json"))
    recorded = rehydrate_passes()

    def executor(actual_request, prior):
        assert actual_request == request
        return recorded[len(prior)]

    result = run_direct_deep(request=request, execute_pass=executor)
    hashes = load("hashes.json")
    assert canonical_hash(result) == hashes["result_canonical_hash"]
    assert len(result.passes) == 4
    assert result.route == "HUMAN_ORIGIN_DIRECT_DEEP"
    assert result.market_status == "NOT_REQUESTED"
    assert result.odds_status == "NOT_COMPUTED"
    assert result.investment_authority == "NONE"

    package = ResearchCommitPackage.model_validate(load("research-package.json"))
    assert result.final_research_package == package
    assert package.schema_version == 2
    assert package.framing is None
    assert package.research_snapshot.status is ResearchStatus.REVIEW
    assert package.research_snapshot.scenarios == ()
    assert package.research_snapshot.valuation_bases == ()

    committed = commit_research_package(package)
    expected_commit = ResearchCommitResult.model_validate(load("commit-result.json"))
    assert canonical_json(committed) == canonical_json(expected_commit)

    assert canonical_hash(request) == hashes["request_hash"]
    assert committed.information_bundle_hash == hashes["information_bundle_hash"]
    assert committed.package_hash == hashes["package_hash"]
    assert canonical_hash(committed) == hashes["commit_result_canonical_hash"]


def test_fresh_hengrui_successor_lineage_and_unknown_stop_are_exact():
    package = ResearchCommitPackage.model_validate(load("research-package.json"))
    predecessor = ResearchCommitResult.model_validate_json(PREDECESSOR.read_bytes())
    snapshot = package.research_snapshot
    assert snapshot.version == predecessor.research_snapshot.version + 1
    assert snapshot.supersedes_snapshot_id == predecessor.research_snapshot.id
    assert snapshot.research_origin == "HUMAN_ORIGIN_DIRECT_DEEP_FRESH_DOGFOOD"

    trace = rehydrate_passes()
    final = trace[-1]
    unresolved = tuple(item.question for item in final.unknowns if item.status != "CLOSED")
    assert snapshot.open_questions == unresolved
    assert sum(item.status == "STOP_PUBLIC_EVIDENCE_EXHAUSTED" for item in final.unknowns) == 4
    assert sum(item.status == "CLOSED" for item in final.unknowns) == 1


def test_source_captures_are_exact_partial_evidence_not_full_source_claims():
    package = ResearchCommitPackage.model_validate(load("research-package.json"))
    captures = load("source-captures.json")
    captures.pop("schema_version")
    hashes = load("hashes.json")["source_capture_canonical_sha256"]
    by_location = {item.source_location: item for item in package.evidence_artifacts}
    for short_name, capture in captures.items():
        digest = canonical_hash(capture)
        assert digest == hashes[short_name]
        location = (
            "docs/readings/600276-hengrui-direct-deep-dogfood-2026-09-17/"
            f"source-captures.json#/{short_name}"
        )
        artifact = by_location[location]
        assert artifact.retention_mode == "EXTRACTED_VALUES"
        assert artifact.replayability_level == "PARTIAL"
        assert artifact.raw_storage_ref is None
        assert artifact.content_hash == f"sha256:{digest}"


def test_bundle_does_not_smuggle_price_odds_or_human_acceptance_into_research():
    package = ResearchCommitPackage.model_validate(load("research-package.json"))
    request = Request.model_validate(load("request.json"))
    assert package.research_snapshot.market_expectations_narrative is None
    assert package.research_snapshot.model_risk_level == "NOT_ESTABLISHED"
    assert request.investment_authority == "NONE"
    # Direct Deep runtime fixes Market/Odds/Human-acceptance authority on replay.
