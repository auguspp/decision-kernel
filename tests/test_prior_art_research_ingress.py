"""Synthetic acceptance cases, not an implementation of Trading Memory.

Prior art: TauricResearch/TradingAgents at
9dee508c44662702281a8dbaad1f7b42179b5ba7 (PIT lessons, revised vintages,
structured-output fallback). Tests are written against our existing interfaces;
no external code, date-only live exemption, rating parser or agent graph is used.
These prove the submitted-package boundary, not an LLM's pre-prompt isolation.
"""
from __future__ import annotations

import json
import socket
from datetime import timedelta, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest

from decision_kernel.cli import main
from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.primitives import DomainValidationError
from decision_kernel.rehearsal import NonAuthoritativeRehearsalFraming
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage, commit_research_package
from decision_kernel.runtime import hithink_http
from decision_kernel.workflow import run_decision_spine
from test_generic_research_commit import (
    AS_OF, _fake_market, _generic_package, _rehash_generic, _runtime_market,
)


@pytest.fixture(autouse=True)
def no_live_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acceptance fixture attempted a real network request")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(hithink_http, "_request_hithink_json", forbidden)
    monkeypatch.setattr(hithink_http, "_request_hithink_calendar", forbidden)


def assert_cli_rejected_before_market(raw: str, tmp_path: Path, monkeypatch) -> str:
    path = tmp_path / "candidate.json"
    path.write_text(raw, encoding="utf-8")
    calls = []

    def forbidden_market(**kwargs):
        calls.append(kwargs)
        raise AssertionError("invalid research reached market acquisition")

    # A missing credential must not be the reason the candidate fails.
    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "synthetic-unused-key")
    monkeypatch.setattr(hithink_http, "fetch_latest_hithink_observed_market", forbidden_market)
    stdout, stderr = StringIO(), StringIO()
    assert main(["run-research", str(path)], stdout=stdout, stderr=stderr) == 2
    assert calls == []
    assert stdout.getvalue() == "", "failure cannot emit an ordinary decision/quiet surface"
    assert stderr.getvalue().startswith("ERROR:")
    assert path.read_text(encoding="utf-8") == raw
    assert set(tmp_path.iterdir()) == {path}
    return stderr.getvalue()


@pytest.mark.parametrize("microseconds", [-1, 0, 1])
def test_available_instant_not_civil_date_or_later_retrieval_controls_commit(microseconds):
    package = _generic_package()
    first = package.evidence_artifacts[0]
    available = (AS_OF + timedelta(microseconds=microseconds)).astimezone(
        timezone(timedelta(hours=-10))
    )
    # The local calendar date appears earlier even for the forbidden +1us case.
    assert available.date() < AS_OF.date()
    evidence = EvidenceArtifact.model_validate({
        **first.model_dump(mode="python"),
        "available_at": available,
        "retrieved_at": AS_OF + timedelta(days=1),
    })
    candidate = _rehash_generic(package, evidence_artifacts=(evidence, package.evidence_artifacts[1]))
    parsed = ResearchCommitPackage.model_validate_json(candidate.model_dump_json())
    if microseconds > 0:
        with pytest.raises(DomainValidationError, match="unavailable at the PIT cutoff"):
            commit_research_package(parsed)
    else:
        result = commit_research_package(parsed)
        assert result.research_snapshot.status is ResearchStatus.COMMITTED
        assert result.information_bundle_hash == candidate.research_snapshot.information_bundle_hash
        assert parsed.evidence_artifacts[0].retrieved_at > AS_OF
        # Accepted public availability is NOT evidence of an actual earlier run,
        # earlier Human exposure, or a model free of hindsight knowledge.


@pytest.mark.parametrize("revision", ["values", "metadata"])
def test_old_period_revision_and_rehashed_package_still_fail_before_market(
    tmp_path, monkeypatch, revision,
):
    package = _generic_package()
    frozen = commit_research_package(package)
    before = frozen.model_dump_json()
    first = package.evidence_artifacts[0]
    payload = first.model_dump(mode="python")
    payload.update({
        "report_period_end": AS_OF.date() - timedelta(days=30),
        "available_at": AS_OF + timedelta(minutes=1),
        "retrieved_at": AS_OF + timedelta(minutes=2),
    })
    if revision == "values":
        payload["extracted_structured_values"] = {"claim": "later revised value"}
        payload["content_hash"] = canonical_hash(payload["extracted_structured_values"])
    else:
        payload["source_location"] = "later corrected units / table metadata"
    revised = EvidenceArtifact.model_validate(payload)
    assert revised.source_locator == first.source_locator
    assert revised.published_at == first.published_at
    assert revised.report_period_end < AS_OF.date()
    assert revised.available_at.date() == AS_OF.date()
    # Adversarial replacement under the same evidence id: neither that id, the
    # old publication date/period nor a newly correct hash certifies an old vintage.
    candidate = _rehash_generic(package, evidence_artifacts=(revised, package.evidence_artifacts[1]))
    assert candidate.research_snapshot.information_bundle_hash != frozen.information_bundle_hash
    ResearchCommitPackage.model_validate_json(candidate.model_dump_json())
    error = assert_cli_rejected_before_market(candidate.model_dump_json(), tmp_path, monkeypatch)
    assert "unavailable at the PIT cutoff" in error
    assert frozen.model_dump_json() == before
    assert commit_research_package(package).model_dump_json() == before


def test_missing_availability_cannot_be_inferred_from_old_publication(tmp_path, monkeypatch):
    payload = _generic_package().model_dump(mode="json")
    del payload["evidence_artifacts"][0]["available_at"]
    error = assert_cli_rejected_before_market(json.dumps(payload), tmp_path, monkeypatch)
    assert "available_at" in error


@pytest.mark.parametrize("form", ["prose", "json-string", "rating-object", "fenced-package"])
def test_formal_cli_does_not_promote_fallback_text_to_a_decision(tmp_path, monkeypatch, form):
    raw = {
        "prose": "Rating：Hold\nBUY after further review; confidence is high.",
        "json-string": json.dumps("Rating: BUY. This is only unstructured model text."),
        "rating-object": json.dumps({"rating": "HOLD", "reason": "No parsed package was returned."}),
        "fenced-package": "```json\n" + _generic_package().model_dump_json() + "\n```",
    }[form]
    assert_cli_rejected_before_market(raw, tmp_path, monkeypatch)


@pytest.mark.parametrize("defect", ["missing-thesis", "non-unit-probabilities"])
def test_valid_schema_and_correct_hash_do_not_bypass_semantic_acceptance(tmp_path, monkeypatch, defect):
    package = _generic_package()
    snapshot = package.research_snapshot
    if defect == "missing-thesis":
        snapshot = snapshot.model_copy(update={"core_thesis": ""})
    else:
        snapshot = snapshot.model_copy(update={"scenarios": tuple(
            scenario.model_copy(update={"probability": Decimal("0")})
            for scenario in snapshot.scenarios
        )})
    candidate = _rehash_generic(package.model_copy(update={"research_snapshot": snapshot}))
    raw = candidate.model_dump_json()
    ResearchCommitPackage.model_validate_json(raw)  # Schema alone genuinely passes.
    error = assert_cli_rejected_before_market(raw, tmp_path, monkeypatch)
    assert ("core_thesis" if defect == "missing-thesis" else "probabilities must sum to one") in error


def test_external_authority_field_is_not_silently_ignored(tmp_path, monkeypatch):
    payload = _generic_package().model_dump(mode="json")
    payload["investment_authority"] = "EXECUTE"
    error = assert_cli_rejected_before_market(json.dumps(payload), tmp_path, monkeypatch)
    assert "investment_authority" in error


def test_valid_unwrapped_package_still_reaches_existing_mocked_decision_path(tmp_path, monkeypatch):
    raw = _generic_package().model_dump_json()
    path = tmp_path / "candidate.json"
    path.write_text(raw, encoding="utf-8")
    calls = []
    reference = _runtime_market("8")

    def market(**kwargs):
        calls.append(kwargs)
        return reference(**kwargs)

    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "synthetic-unused-key")
    monkeypatch.setattr(hithink_http, "fetch_latest_hithink_observed_market", market)
    stdout, stderr = StringIO(), StringIO()
    assert main(["run-research", str(path)], stdout=stdout, stderr=stderr) == 0
    assert len(calls) == 1
    assert "STATE: HUMAN_ATTENTION_REQUIRED" in stdout.getvalue()
    assert "INVESTMENT AUTHORITY: NONE" in stdout.getvalue()
    assert stderr.getvalue() == ""
    assert path.read_text(encoding="utf-8") == raw
    assert set(tmp_path.iterdir()) == {path}


def test_non_authoritative_rating_text_cannot_change_odds_or_human_authority():
    package = _generic_package()
    snapshot = commit_research_package(package).research_snapshot
    before = snapshot.model_dump_json()
    common = dict(
        research_snapshot=snapshot,
        observed_market=_fake_market("8")(thscode="600000.SH", observed_at=AS_OF + timedelta(hours=3)),
        odds_policy=load_live_odds_v0_1(),
        odds_artifact_id=uuid4(), odds_created_at=AS_OF + timedelta(hours=3),
        rehearsal_artifact_id=uuid4(), rehearsal_created_at=AS_OF + timedelta(hours=3),
    )
    first = run_decision_spine(**common, framing=package.framing)
    other = run_decision_spine(**common, framing=NonAuthoritativeRehearsalFraming(
        why_now="Synthetic presentation change only.",
        current_expression="Rating: BUY / HOLD / SELL are prose here, not executable states.",
    ))
    assert first.odds == other.odds
    assert first.rehearsal.artifact_hash != other.rehearsal.artifact_hash
    assert first.terminal_state == other.terminal_state
    assert first.human_surface.attention_eligible == other.human_surface.attention_eligible
    assert other.rehearsal.artifact.system_status == "DECISION_REHEARSAL_ONLY"
    assert other.rehearsal.artifact.human_status == "HUMAN_DECISION_REQUIRED"
    assert other.investment_authority == "NONE"
    assert snapshot.model_dump_json() == before
