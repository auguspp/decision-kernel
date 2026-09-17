"""Real 600276 Human-price conditional Odds fixture; no Market/provider execution."""
from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import socket

import pytest

from decision_kernel.calculation import CalculationStatus
from decision_kernel.identity import canonical_hash
from decision_kernel.research import ModelRiskLevel, ResearchStatus
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.runtime import odds_retention as odds
from decision_kernel.runtime import research_commit_only as retained

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/readings/600276-hengrui-research-commit-2026-09-17"
ODDS = ROOT / "docs/readings/600276-hengrui-conditional-odds-2026-09-17"
SNAPSHOT_ID = "ea9b4e56-c998-5dcd-b8fa-3f1539612762"
SNAPSHOT_HASH = "c001d697620b6a547857832694af289239ad1f1a10bde62fa2e5a70373898dad"
INFO_HASH = "a289d5776ec39068318b2feb277d60a71a4e68a6bc0af1853210a84ea53799a5"
PACKAGE_HASH = "662bf206a1a3ec94d7889c6d1b00f2d378863c4487fcc2b56aff362103b859cc"
RESULT_HASH = "bb7ec7bdd63c3c651dd98e985e1f794cd2a1e95bdc2ae82c258551cd41be5c5f"
ARTIFACT_HASH = "31203cb32c8e30c7aead5b80fd4ceed9a4f683c5fa12dd3e7b0ebbc1f7b5c10c"
RESEARCH_SHA256 = {
    "input.json": "b5da506171b8cc8da48e239f1f79dde50bdc296e31d1de81c6fbbf0c9b03032d",
    "retention.json": "2a766bea98166edaf5dcc7eb587f3e2bcaab0d1e3e33c47c82e464763d017e90",
    "research-commit.json": "bb1fc4634ca2d899ef0f69e4634cc26aa5d0df02bd04871cc8c5c0a00fc7f925",
    "commit.json": "08bb7d471162faf6948a2af579fde91f2897c0cb9a89d90f9cfe0ce8e9bb07bd",
}
ODDS_SHA256 = {
    "result.json": "ef7b664dcebdff2e9688f1c96e47f5c3b4aea69462929f4fe65a2738fd902fc2",
    "retention.json": "92f4107a9f7bc60661a80add7175917518f56e0e7a51e3c35eec75f9bf80e6bb",
}
TERMINAL_EDGES = {
    Decimal(value)
    for value in ("22.6", "32.5", "39.2", "49.7", "52.7", "65.1", "69.9", "86.8")
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("real Hengrui Acceptance-6 regression cannot request network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def files(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def test_real_hengrui_human_price_conditional_odds_revalidates_without_market():
    research_files = files(RESEARCH)
    odds_files = files(ODDS)
    assert set(research_files) == set(RESEARCH_SHA256)
    assert set(odds_files) == set(ODDS_SHA256)
    assert {
        name: sha256(raw).hexdigest() for name, raw in research_files.items()
    } == RESEARCH_SHA256
    assert {
        name: sha256(raw).hexdigest() for name, raw in odds_files.items()
    } == ODDS_SHA256

    package = ResearchCommitPackage.model_validate_json(research_files["input.json"])
    source_snapshot = package.research_snapshot
    assert source_snapshot.status is ResearchStatus.REVIEW
    assert source_snapshot.schema_version == 2
    assert source_snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert source_snapshot.valuation_horizon_date is None
    assert source_snapshot.valuation_bases == ()
    assert source_snapshot.scenarios == ()

    research = retained.read_retained_commit(RESEARCH)
    snapshot = research.research_snapshot
    assert str(snapshot.id) == SNAPSHOT_ID
    assert canonical_hash(snapshot) == SNAPSHOT_HASH
    assert research.information_bundle_hash == INFO_HASH
    assert research.package_hash == PACKAGE_HASH
    assert snapshot.status is ResearchStatus.COMMITTED
    assert snapshot.model_risk_level is ModelRiskLevel.NOT_ESTABLISHED
    assert snapshot.valuation_bases == ()
    assert snapshot.scenarios == ()

    result = odds.read_retained_odds(
        ODDS,
        research_directory=RESEARCH,
        expected_research_hash=SNAPSHOT_HASH,
    )
    artifact = result.artifact
    assert canonical_hash(result) == RESULT_HASH
    assert result.artifact_hash == ARTIFACT_HASH
    assert artifact.research_snapshot_id == snapshot.id
    assert artifact.research_snapshot_hash == SNAPSHOT_HASH
    assert artifact.research_information_bundle_hash == INFO_HASH

    price = artifact.price_context
    assert price.price == Decimal("42.93")
    assert price.source == "HUMAN_SUPPLIED_PROVISIONAL_PRICE"
    assert price.authority == "CONTEXT_ONLY"
    assert price.qualified_market_observation is False
    assert price.canonical_market_state is False
    assert artifact.price_clock_semantics == "PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT"

    assert artifact.calculation_status is CalculationStatus.CALCULATED
    assert artifact.ordinal_status == "MIXED_OR_ZERO_DECLARED_WORLD_RETURNS"
    worlds = artifact.conditional_worlds.world_set.worlds
    assert len(worlds) == 8
    assert {world.terminal_equity_value_per_share for world in worlds} == TERMINAL_EDGES
    assert {
        world.terminal_equity_value_per_share for world in artifact.world_results
    } == TERMINAL_EDGES

    assert artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert artifact.probability_input == "ABSENT_BY_DESIGN"
    assert artifact.weighted_aggregate == "NOT_COMPUTED"
    assert artifact.market_qualification == "NOT_ESTABLISHED"
    assert artifact.canonical_odds == "NOT_ESTABLISHED"
    assert artifact.human_acceptance == "NOT_ESTABLISHED_BY_THIS_OPERATION"
    assert artifact.investment_authority == "NONE"
    assert b'"probability":' not in odds_files["result.json"]

    assert files(RESEARCH) == research_files
    assert files(ODDS) == odds_files
