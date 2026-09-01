from __future__ import annotations

from datetime import timedelta
from io import StringIO
from uuid import uuid4

import pytest

from decision_kernel.cli import main
from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.live import run_live_research_commit_package
from decision_kernel.market import ObservedMarket
from decision_kernel.primitives import DomainValidationError
from decision_kernel.rehearsal import NonAuthoritativeRehearsalFraming
from decision_kernel.research import ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    commit_research_package,
    research_commit_information_bundle_hash,
    research_commit_package_hash,
)
from decision_kernel.runtime import hithink_http
from decision_kernel.workflow import DecisionSpineTerminalState
from test_deep_research import AS_OF, COMMIT_AT, _package


def _generic_package() -> ResearchCommitPackage:
    method_package = _package()
    evidence = method_package.evidence_artifacts
    snapshot = method_package.research_snapshot.model_copy(
        update={
            "status": ResearchStatus.REVIEW,
            "information_bundle_hash": None,
        }
    )
    information_hash = research_commit_information_bundle_hash(
        research_snapshot=snapshot,
        evidence_artifacts=evidence,
    )
    snapshot = snapshot.model_copy(update={"information_bundle_hash": information_hash})
    return ResearchCommitPackage(
        research_snapshot=snapshot,
        evidence_artifacts=evidence,
        framing=NonAuthoritativeRehearsalFraming(
            why_now="reviewed research is ready for current-market odds",
            current_expression="listed equity research review only",
        ),
        proposed_committed_at=COMMIT_AT,
    )


def _fake_market(price: str):
    def fetch_market(*, thscode: str, observed_at):
        assert thscode == "600000.SH"
        return ObservedMarket(
            market_price=price,
            market_timestamp=AS_OF + timedelta(hours=2),
            market_utc_offset_minutes=480,
            market_data_source="HiThink generic fixture completed close",
            price_convention="RAW_UNADJUSTED_COMPLETED_A_SHARE_CLOSE",
            currency="CNY",
        )

    return fetch_market


def _runtime_market(price: str):
    inner = _fake_market(price)

    def fetch_market(*, thscode: str, observed_at, api_key: str | None):
        if not api_key:
            raise RuntimeError("HiThink credentials are required for live market data")
        return inner(thscode=thscode, observed_at=observed_at)

    return fetch_market


def _rehash_generic(
    package: ResearchCommitPackage,
    *,
    evidence_artifacts: tuple[EvidenceArtifact, ...] | None = None,
):
    evidence = evidence_artifacts or package.evidence_artifacts
    snapshot = package.research_snapshot.model_copy(update={"information_bundle_hash": None})
    snapshot = snapshot.model_copy(
        update={
            "information_bundle_hash": research_commit_information_bundle_hash(
                research_snapshot=snapshot,
                evidence_artifacts=evidence,
            )
        }
    )
    return package.model_copy(
        update={
            "research_snapshot": snapshot,
            "evidence_artifacts": evidence,
        }
    )


def test_generic_research_package_commits_without_research_method_v1() -> None:
    package = _generic_package()

    result = commit_research_package(package)

    assert package.research_snapshot.status is ResearchStatus.REVIEW
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.research_snapshot.committed_at == COMMIT_AT
    assert (
        result.research_snapshot.information_bundle_hash
        == package.research_snapshot.information_bundle_hash
    )


def test_generic_research_identity_ignores_incidental_evidence_order() -> None:
    package = _generic_package()
    reversed_package = package.model_copy(
        update={"evidence_artifacts": tuple(reversed(package.evidence_artifacts))}
    )

    assert research_commit_package_hash(reversed_package) == research_commit_package_hash(package)
    assert research_commit_information_bundle_hash(
        research_snapshot=package.research_snapshot,
        evidence_artifacts=reversed_package.evidence_artifacts,
    ) == research_commit_information_bundle_hash(
        research_snapshot=package.research_snapshot,
        evidence_artifacts=package.evidence_artifacts,
    )


def test_rehearsal_framing_is_not_part_of_research_information_identity() -> None:
    package = _generic_package()
    alternate = package.model_copy(
        update={
            "framing": NonAuthoritativeRehearsalFraming(
                why_now="a different executable reason to review the same research",
                current_expression="a different non-authoritative presentation",
            )
        }
    )

    original_identity = research_commit_information_bundle_hash(
        research_snapshot=package.research_snapshot,
        evidence_artifacts=package.evidence_artifacts,
    )
    alternate_identity = research_commit_information_bundle_hash(
        research_snapshot=alternate.research_snapshot,
        evidence_artifacts=alternate.evidence_artifacts,
    )

    assert alternate_identity == original_identity
    assert alternate.research_snapshot.information_bundle_hash == original_identity
    assert research_commit_package_hash(alternate) != research_commit_package_hash(package)


def test_generic_commit_rejects_future_missing_and_unreferenced_evidence() -> None:
    package = _generic_package()

    first = package.evidence_artifacts[0]
    future = first.model_copy(
        update={
            "available_at": package.research_snapshot.as_of_datetime + timedelta(minutes=1),
            "retrieved_at": package.research_snapshot.as_of_datetime + timedelta(minutes=2),
        }
    )
    future_package = _rehash_generic(
        package,
        evidence_artifacts=(future, package.evidence_artifacts[1]),
    )
    with pytest.raises(DomainValidationError, match="unavailable at the PIT cutoff"):
        commit_research_package(future_package)

    missing = package.model_copy(update={"evidence_artifacts": package.evidence_artifacts[:1]})
    with pytest.raises(DomainValidationError, match="missing referenced EvidenceArtifacts"):
        commit_research_package(missing)

    extra = first.model_copy(
        update={
            "id": uuid4(),
            "source_identifier": "extra-unreferenced-evidence",
            "idempotency_key": "extra-unreferenced-evidence",
            "content_hash": "c" * 64,
        }
    )
    extra_package = _rehash_generic(
        package,
        evidence_artifacts=(*package.evidence_artifacts, extra),
    )
    with pytest.raises(DomainValidationError, match="unreferenced EvidenceArtifacts"):
        commit_research_package(extra_package)


def test_generic_commit_requires_review_and_exact_information_identity() -> None:
    package = _generic_package()

    draft = package.research_snapshot.model_copy(update={"status": ResearchStatus.DRAFT})
    with pytest.raises(DomainValidationError, match="requires a REVIEW"):
        commit_research_package(package.model_copy(update={"research_snapshot": draft}))

    wrong_hash = package.research_snapshot.model_copy(
        update={"information_bundle_hash": "f" * 64}
    )
    with pytest.raises(DomainValidationError, match="freeze the exact generic research package"):
        commit_research_package(
            package.model_copy(update={"research_snapshot": wrong_hash})
        )


def test_generic_live_path_routes_same_research_to_quiet_or_human_from_price() -> None:
    package = _generic_package()
    observed_at = AS_OF + timedelta(hours=3)

    quiet = run_live_research_commit_package(
        package=package,
        observed_at=observed_at,
        fetch_market=_fake_market("10"),
    )
    wake = run_live_research_commit_package(
        package=package,
        observed_at=observed_at,
        fetch_market=_fake_market("8"),
    )

    assert quiet.decision.terminal_state is DecisionSpineTerminalState.QUIET_INSUFFICIENT_ODDS
    assert quiet.decision.human_surface.attention_eligible is False
    assert wake.decision.terminal_state is DecisionSpineTerminalState.HUMAN_ATTENTION_REQUIRED
    assert wake.decision.human_surface.attention_eligible is True
    assert quiet.investment_authority == "NONE"
    assert wake.investment_authority == "NONE"


def test_cli_run_research_uses_generic_package_without_internal_dump(
    tmp_path,
    monkeypatch,
) -> None:
    package_path = tmp_path / "research-commit-package.json"
    package_path.write_text(_generic_package().model_dump_json(indent=2), encoding="utf-8")
    monkeypatch.setenv(hithink_http.HITHINK_API_KEY_ENV, "fixture-secret")
    monkeypatch.setattr(
        hithink_http,
        "fetch_latest_hithink_observed_market",
        _runtime_market("8"),
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        ["run-research", str(package_path)],
        stdout=stdout,
        stderr=stderr,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "STATE: HUMAN_ATTENTION_REQUIRED" in output
    assert "SECURITY: 600000 Sample Co" in output
    assert "HUMAN ATTENTION: YES" in output
    assert "INVESTMENT AUTHORITY: NONE" in output
    assert "CURRENT BELIEF:" in output
    assert "information_bundle_hash" not in output
    assert "package_hash" not in output
