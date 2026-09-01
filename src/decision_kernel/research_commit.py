from __future__ import annotations

from pydantic import Field, model_validator

from .evidence import EvidenceArtifact
from .identity import canonical_hash
from .primitives import AwareDateTime, DomainValidationError, KernelModel
from .rehearsal import NonAuthoritativeRehearsalFraming
from .research import ResearchSnapshot, ResearchStatus, commit_snapshot


class ResearchCommitPackage(KernelModel):
    """Method-agnostic handoff into Kernel commit authority."""

    research_snapshot: ResearchSnapshot
    evidence_artifacts: tuple[EvidenceArtifact, ...] = ()
    framing: NonAuthoritativeRehearsalFraming
    proposed_committed_at: AwareDateTime
    schema_version: int = Field(default=1, ge=1)


class ResearchCommitResult(KernelModel):
    package_hash: str = Field(min_length=64, max_length=64)
    information_bundle_hash: str = Field(min_length=64, max_length=64)
    research_snapshot: ResearchSnapshot

    @model_validator(mode="after")
    def validate_commit_result(self) -> "ResearchCommitResult":
        snapshot = self.research_snapshot
        if snapshot.status is not ResearchStatus.COMMITTED:
            raise ValueError("Research commit result requires COMMITTED ResearchSnapshot")
        if snapshot.information_bundle_hash != self.information_bundle_hash:
            raise ValueError("Research commit result must preserve information identity")
        return self


def research_commit_information_bundle_hash(
    *,
    research_snapshot: ResearchSnapshot,
    evidence_artifacts: tuple[EvidenceArtifact, ...],
) -> str:
    """Freeze the exact Kernel-visible research state without method-specific payloads."""

    snapshot_payload = research_snapshot.model_dump(
        mode="python",
        exclude={"information_bundle_hash", "status", "committed_at"},
    )
    return canonical_hash(
        {
            "schema_version": 1,
            "research_snapshot": snapshot_payload,
            "evidence_artifacts": tuple(
                sorted(evidence_artifacts, key=lambda item: str(item.id))
            ),
        }
    )


def research_commit_package_hash(package: ResearchCommitPackage) -> str:
    return canonical_hash(package)


def referenced_research_evidence_ids(snapshot: ResearchSnapshot) -> set:
    """Return every EvidenceArtifact id used by the frozen Kernel research state."""

    linked = {link.evidence_artifact_id for link in snapshot.evidence_links}
    valuation = {
        artifact_id
        for basis in snapshot.valuation_bases
        for artifact_id in basis.provenance_artifact_ids
    }
    cash_flows = {
        artifact_id
        for scenario in snapshot.scenarios
        for flow in scenario.expected_cash_flows
        for artifact_id in flow.provenance_artifact_ids
    }
    return linked | valuation | cash_flows


def validate_research_commit_package(package: ResearchCommitPackage) -> None:
    """Validate only method-agnostic evidence, PIT, identity, and commit prerequisites."""

    snapshot = package.research_snapshot
    if snapshot.status is not ResearchStatus.REVIEW:
        raise DomainValidationError(
            "generic ResearchCommitPackage requires a REVIEW ResearchSnapshot"
        )
    snapshot.assert_commit_ready()

    evidence_by_id = {artifact.id: artifact for artifact in package.evidence_artifacts}
    if len(evidence_by_id) != len(package.evidence_artifacts):
        raise DomainValidationError("ResearchCommitPackage evidence ids must be unique")

    package_ids = set(evidence_by_id)
    referenced_ids = referenced_research_evidence_ids(snapshot)
    missing = referenced_ids - package_ids
    if missing:
        ids = ", ".join(str(item) for item in sorted(missing, key=str))
        raise DomainValidationError(
            f"ResearchCommitPackage is missing referenced EvidenceArtifacts: {ids}"
        )
    unreferenced = package_ids - referenced_ids
    if unreferenced:
        ids = ", ".join(str(item) for item in sorted(unreferenced, key=str))
        raise DomainValidationError(
            f"ResearchCommitPackage contains unreferenced EvidenceArtifacts: {ids}"
        )

    future = tuple(
        artifact
        for artifact in package.evidence_artifacts
        if not artifact.is_available_at(snapshot.as_of_datetime)
    )
    if future:
        ids = ", ".join(str(item.id) for item in sorted(future, key=lambda item: str(item.id)))
        raise DomainValidationError(
            f"ResearchCommitPackage contains evidence unavailable at the PIT cutoff: {ids}"
        )

    expected_hash = research_commit_information_bundle_hash(
        research_snapshot=snapshot,
        evidence_artifacts=package.evidence_artifacts,
    )
    if snapshot.information_bundle_hash != expected_hash:
        raise DomainValidationError(
            "ResearchSnapshot information_bundle_hash must freeze the exact generic research package"
        )


def commit_research_package(package: ResearchCommitPackage) -> ResearchCommitResult:
    """Commit one method-agnostic research handoff through Kernel authority."""

    validate_research_commit_package(package)
    committed = commit_snapshot(
        package.research_snapshot,
        package.proposed_committed_at,
    )
    return ResearchCommitResult(
        package_hash=research_commit_package_hash(package),
        information_bundle_hash=committed.information_bundle_hash or "",
        research_snapshot=committed,
    )
