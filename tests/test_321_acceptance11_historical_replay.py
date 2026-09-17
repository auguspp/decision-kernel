"""#321 Acceptance 11: historical replay input is Evidence/cutoff, not saved answer prose."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.research_commit import ResearchCommitPackage


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs/readings/600276-hengrui-direct-deep-dogfood-2026-09-17"
MANIFEST = CASE / "replay-input.json"
REQUEST = CASE / "request.json"
SOURCES = CASE / "source-captures.json"
PACKAGE = CASE / "research-package.json"
METHOD = ROOT / "docs/full-research-method-v3.md"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def replay_identity(manifest: dict) -> str:
    return canonical_hash({
        "case": manifest["case"],
        "research_cutoff": manifest["research_cutoff"],
        "evidence": [
            {
                "id": item["id"],
                "content_hash": item["content_hash"],
                "source_capture_pointer": item["source_capture_pointer"],
            }
            for item in manifest["evidence"]
        ],
    })


def test_replay_manifest_binds_same_cutoff_and_exact_retained_evidence_set():
    manifest = load(MANIFEST)
    request = load(REQUEST)
    package = ResearchCommitPackage.model_validate_json(PACKAGE.read_bytes())
    cutoff = datetime.fromisoformat(manifest["research_cutoff"].replace("Z", "+00:00"))

    assert manifest["research_cutoff"] == request["research_cutoff"]
    assert package.research_snapshot.as_of_datetime == cutoff
    assert manifest["case"] == {
        "ticker": package.research_snapshot.ticker,
        "company_name": package.research_snapshot.company_name,
        "exchange": package.research_snapshot.exchange,
        "currency": package.research_snapshot.currency,
    }

    retained = {str(item.id): item for item in package.evidence_artifacts}
    assert {item["id"] for item in manifest["evidence"]} == set(retained)
    for item in manifest["evidence"]:
        artifact = retained[item["id"]]
        assert item["content_hash"] == artifact.content_hash
        assert item["retention_mode"] == artifact.retention_mode
        assert item["replayability_level"] == artifact.replayability_level
        assert item["source_locator"] == artifact.source_locator
        assert artifact.available_at <= cutoff


def test_replay_source_values_match_evidence_hashes_but_remain_partial():
    manifest = load(MANIFEST)
    captures = load(SOURCES)
    captures.pop("schema_version")
    package = ResearchCommitPackage.model_validate_json(PACKAGE.read_bytes())
    retained = {str(item.id): item for item in package.evidence_artifacts}

    assert set(captures) == {item["source_capture_pointer"] for item in manifest["evidence"]}
    for item in manifest["evidence"]:
        capture = captures[item["source_capture_pointer"]]
        assert "sha256:" + canonical_hash(capture) == item["content_hash"]
        artifact = retained[item["id"]]
        assert artifact.retention_mode == "EXTRACTED_VALUES"
        assert artifact.replayability_level == "PARTIAL"
        assert artifact.raw_storage_ref is None

    assert manifest["replay_qualification"] == {
        "retained_evidence_set_replay": "ESTABLISHED_INPUT",
        "full_original_source_replay": "NOT_ESTABLISHED_FOR_THIS_CASE",
        "reason": "All four EvidenceArtifacts are EXTRACTED_VALUES/PARTIAL; no FULL_ARTIFACT/FULL claim is permitted.",
    }


def test_replay_input_is_output_independent_and_allows_new_prompt_without_changing_evidence_identity():
    manifest = load(MANIFEST)
    package = ResearchCommitPackage.model_validate_json(PACKAGE.read_bytes())
    prompt = manifest["replay_prompt"]["instruction"]
    prior_thesis = package.research_snapshot.core_thesis

    assert prior_thesis not in prompt
    assert "Do not read or use the prior core thesis" in prompt
    excluded = "\n".join(manifest["excluded_prior_outputs"])
    assert "pass-records.json" in excluded
    assert "commit-result.json" in excluded
    assert "README.md" in excluded
    assert "research-package.json#/research_snapshot" in excluded

    original_identity = replay_identity(manifest)
    changed_prompt = deepcopy(manifest)
    changed_prompt["replay_prompt"]["version"] = "future-model-or-prompt-v2"
    changed_prompt["replay_prompt"]["instruction"] += " Challenge the strongest alternative explanation first."
    assert replay_identity(changed_prompt) == original_identity

    changed_evidence = deepcopy(manifest)
    changed_evidence["evidence"][0]["content_hash"] = "sha256:" + "0" * 64
    assert replay_identity(changed_evidence) != original_identity


def test_replay_manifest_pins_request_method_sources_and_never_gains_authority():
    manifest = load(MANIFEST)
    assert manifest["original_request"]["git_blob"] == git_blob_sha(REQUEST)
    assert manifest["source_capture"]["git_blob"] == git_blob_sha(SOURCES)
    assert manifest["method"]["git_blob"] == git_blob_sha(METHOD)
    assert manifest["method"]["version"] == "full-research-operating-v3"
    assert manifest["method"]["ref"] == "67701b4debd3b82971b78aa9650541f3f91b584a"
    assert manifest["authority"] == {
        "human_acceptance": "NOT_ESTABLISHED_BY_REPLAY_INPUT",
        "research_authority": "NONE",
        "investment_authority": "NONE",
        "action_authority": "NONE",
    }
