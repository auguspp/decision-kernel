"""Real 600598 Research-only commit fixture; read-only regression, no Market/Odds."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.evidence import ReplayabilityLevel, RetentionMode
from decision_kernel.research import ModelRiskLevel, ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.runtime import research_commit_only as retained

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/readings/600598-beidahuang-research-commit-2026-09-17"
SNAPSHOT_ID = "fe4e89dc-0a2a-5943-b17f-1fafc57d17d9"
INFO_HASH = "ed9793b143cf1ea66c8aa3a666c8ad5016ea4c920c9fbabbeb8a1fbd812bc211"
PACKAGE_HASH = "cc9dde40a47fc2b5533ca7379e4c043029e0323ea9741c4f800abb4430cd619d"
FILE_SHA256 = {
    "input.json": "10c92d09e4fc9b603707ed38f92c8f312dfe7c0a4662ade3e52a4037985050c0",
    "retention.json": "01902630c3385594e75ffc64d70c6d4c5ca1c6c00100ea3f7f79dd1506c3b221",
    "research-commit.json": "5422e2ff67b90a97142e2d66cad58008347f90e980e5c562a491d7ff92ef201e",
    "commit.json": "c4201b36788285c75ba703cd3ecadd40b4962232c11c4fd751fff4f58cddc572",
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("real Research archive regression cannot request network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def test_real_600598_commit_archive_revalidates_fixed_bytes_without_promotion():
    before = {path.name: path.read_bytes() for path in ARCHIVE.iterdir()}
    assert set(before) == set(FILE_SHA256)
    assert {name: sha256(raw).hexdigest() for name, raw in before.items()} == FILE_SHA256

    package = ResearchCommitPackage.model_validate_json(before["input.json"])
    snapshot = package.research_snapshot
    assert str(snapshot.id) == SNAPSHOT_ID
    assert snapshot.status is ResearchStatus.REVIEW
    assert snapshot.schema_version == 2
    assert snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert snapshot.valuation_horizon_date is None
    assert snapshot.valuation_bases == () and snapshot.scenarios == ()
    assert package.framing is None
    assert package.evidence_artifacts
    assert all(item.retention_mode is RetentionMode.EXTRACTED_VALUES for item in package.evidence_artifacts)
    assert all(item.replayability_level is ReplayabilityLevel.PARTIAL for item in package.evidence_artifacts)
    assert all(item.raw_storage_ref is None for item in package.evidence_artifacts)
    assert all(item.available_at <= snapshot.as_of_datetime < item.retrieved_at for item in package.evidence_artifacts)

    result = retained.read_retained_commit(ARCHIVE)
    committed = result.research_snapshot
    assert result.package_hash == PACKAGE_HASH
    assert result.information_bundle_hash == INFO_HASH
    assert str(committed.id) == SNAPSHOT_ID
    assert committed.status is ResearchStatus.COMMITTED
    assert committed.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert committed.valuation_bases == () and committed.scenarios == ()

    receipt = json.loads(before["commit.json"])
    assert receipt["market_status"] == "NOT_REQUESTED"
    assert receipt["odds_status"] == "NOT_COMPUTED"
    assert receipt["human_acceptance"] == "NOT_ESTABLISHED_BY_THIS_OPERATION"
    assert receipt["investment_authority"] == "NONE"
    assert {path.name: path.read_bytes() for path in ARCHIVE.iterdir()} == before
