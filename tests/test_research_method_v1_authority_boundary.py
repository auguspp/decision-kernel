from __future__ import annotations

from datetime import timedelta

import pytest

from decision_kernel.deep_research import (
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
    commit_deep_research_package,
)
from decision_kernel.primitives import DomainValidationError
from test_deep_research import AS_OF, _package, _rehash


def test_method_v1_acceptance_does_not_own_decision_spine_readiness() -> None:
    package = _package()
    snapshot = package.research_snapshot.model_copy(update={"core_thesis": ""})
    changed = _rehash(package, research_snapshot=snapshot)

    assert (
        assess_research_method_v1_acceptance(changed).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    with pytest.raises(DomainValidationError, match="core_thesis"):
        commit_deep_research_package(changed)


def test_method_v1_acceptance_does_not_own_commit_chronology() -> None:
    package = _package().model_copy(
        update={"proposed_committed_at": AS_OF - timedelta(seconds=1)}
    )

    assert (
        assess_research_method_v1_acceptance(package).status
        is ResearchMethodV1AcceptanceStatus.ACCEPTED
    )
    with pytest.raises(DomainValidationError, match="cannot precede"):
        commit_deep_research_package(package)
