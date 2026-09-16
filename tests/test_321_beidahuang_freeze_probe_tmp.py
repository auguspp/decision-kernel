"""TEMP probe: generate exact commit-only bytes for the real 600598 freeze candidate."""
from __future__ import annotations

import base64
from pathlib import Path
import socket

import pytest

from decision_kernel.evidence import ReplayabilityLevel, RetentionMode
from decision_kernel.research import ModelRiskLevel, ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage,
    research_commit_information_bundle_hash,
    research_commit_package_hash,
)
from decision_kernel.runtime import research_commit_only as retained

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/readings/600598-beidahuang-research-commit-2026-09-17/input.json"
INFO_HASH = "ed9793b143cf1ea66c8aa3a666c8ad5016ea4c920c9fbabbeb8a1fbd812bc211"
PACKAGE_HASH = "cc9dde40a47fc2b5533ca7379e4c043029e0323ea9741c4f800abb4430cd619d"
SNAPSHOT_ID = "fe4e89dc-0a2a-5943-b17f-1fafc57d17d9"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Research-only freeze probe cannot request network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def test_real_600598_research_only_package_and_generate_commit_bytes(tmp_path):
    package = ResearchCommitPackage.model_validate_json(PACKAGE.read_bytes())
    snapshot = package.research_snapshot
    assert str(snapshot.id) == SNAPSHOT_ID
    assert snapshot.ticker == "600598.SH"
    assert snapshot.status is ResearchStatus.REVIEW
    assert snapshot.schema_version == 2
    assert snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert snapshot.valuation_horizon_date is None
    assert snapshot.valuation_bases == () and snapshot.scenarios == ()
    assert snapshot.market_expectations_narrative is None
    assert package.framing is None
    assert package.evidence_artifacts
    assert all(item.retention_mode is RetentionMode.EXTRACTED_VALUES for item in package.evidence_artifacts)
    assert all(item.replayability_level is ReplayabilityLevel.PARTIAL for item in package.evidence_artifacts)
    assert all(item.raw_storage_ref is None for item in package.evidence_artifacts)
    assert all(item.available_at <= snapshot.as_of_datetime < item.retrieved_at for item in package.evidence_artifacts)
    assert research_commit_information_bundle_hash(
        research_snapshot=snapshot,
        evidence_artifacts=package.evidence_artifacts,
    ) == INFO_HASH == snapshot.information_bundle_hash
    assert research_commit_package_hash(package) == PACKAGE_HASH

    output = tmp_path / "saved"
    result = retained.commit_research_file(PACKAGE, output=output)
    assert result.package_hash == PACKAGE_HASH
    assert result.information_bundle_hash == INFO_HASH
    assert str(result.research_snapshot.id) == SNAPSHOT_ID
    assert result.research_snapshot.status is ResearchStatus.COMMITTED
    assert result.research_snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert result.research_snapshot.scenarios == ()

    for name in ("retention.json", "research-commit.json", "commit.json"):
        encoded = base64.b64encode((output / name).read_bytes()).decode("ascii")
        print(f"BEIDAHUANG_PROBE_{name.upper().replace('.', '_')}={encoded}")
