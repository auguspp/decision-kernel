from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_events import (
    create_sector_radar_candidate_event_ledger,
)
from decision_kernel.runtime.sector_radar_persistence import (
    SECTOR_RADAR_LONG_TERM_CHECKPOINT_POLICY,
    SECTOR_RADAR_PERSISTENCE_SEMANTICS,
    SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS,
    SOURCE_COMMITTED_BOOTSTRAP,
    SOURCE_LATEST_SUCCESS_ARTIFACT,
    SectorRadarPersistenceError,
    load_sector_radar_persistent_bundle,
    parse_sector_radar_persistent_manifest,
    resolve_sector_radar_persistence,
    serialize_sector_radar_persistent_manifest,
    write_sector_radar_persistent_bundle,
)
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
CREATED = datetime(2026, 9, 5, 8, 0, tzinfo=SHANGHAI)
UPDATED = datetime(2026, 9, 5, 8, 10, tzinfo=SHANGHAI)
REPOSITORY = "auguspp/decision-kernel"
WORKFLOW = ".github/workflows/sector-radar-shadow.yml"
COMMIT = "a" * 40
PARENT_HINT_HASH = "b" * 64
BOOTSTRAP = Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz")
BOOTSTRAP_MANIFEST = Path(
    "radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json"
)


def catalog():
    return normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": 1788500000000,
                "item": [
                    {"thscode": "881101.TI", "name": "种植业与林业"},
                    {"thscode": "881102.TI", "name": "养殖业"},
                    {"thscode": "884001.TI", "name": "种子生产"},
                    {"thscode": "884275.TI", "name": "生猪养殖"},
                ],
            },
        }
    )


def series(code: str, name: str, step: str) -> SectorPriceSeries:
    sessions = tuple(date(2026, 1, 1) + timedelta(days=index) for index in range(127))
    increment = Decimal(step)
    return SectorPriceSeries(
        thscode=code,
        name=name,
        points=tuple(
            SectorPricePoint(
                session=session,
                close=Decimal("100") + increment * index,
                turnover=Decimal("1000") + Decimal(index),
            )
            for index, session in enumerate(sessions)
        ),
    )


def state():
    return create_sector_radar_market_state(
        catalog=catalog(),
        benchmark=series("000300.SH", "沪深300", "0.2"),
        broad_series=(
            series("881101.TI", "种植业与林业", "0.3"),
            series("881102.TI", "养殖业", "0.4"),
        ),
        granular_series=(
            series("884001.TI", "种子生产", "0.5"),
            series("884275.TI", "生猪养殖", "0.6"),
        ),
        created_at=CREATED,
        source="qualified synthetic history",
        source_lineage=(
            SectorRadarStateSourceLineage(
                role="TEST_HISTORY",
                workflow_run_id=1,
                artifact_id=2,
                artifact_digest="sha256:" + "c" * 64,
                result_hash="d" * 64,
            ),
        ),
    )


def ledger():
    return create_sector_radar_candidate_event_ledger(
        created_at=CREATED,
        source="prospective Sector Radar test ledger",
    )


def write_bundle(
    directory: Path,
    *,
    run_id: int = 10,
    updated_at: datetime = UPDATED,
    operation: str = "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT",
):
    return write_sector_radar_persistent_bundle(
        directory,
        market_state=state(),
        event_ledger=ledger(),
        created_at=CREATED,
        updated_at=updated_at,
        source_repository=REPOSITORY,
        source_workflow=WORKFLOW,
        source_run_id=run_id,
        source_run_attempt=1,
        source_commit_sha=COMMIT,
        parent_hint_mapping_hash=PARENT_HINT_HASH,
        last_result_hash=None,
        last_operation_status=operation,
    )


def test_persistent_bundle_round_trips_with_explicit_recovery_policy(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "state"
    written = write_bundle(directory)
    loaded = load_sector_radar_persistent_bundle(
        directory,
        expected_repository=REPOSITORY,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )

    assert loaded == written
    assert loaded.manifest.artifact_retention_days == (
        SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS
    ) == 90
    assert loaded.manifest.recovery_policy == SECTOR_RADAR_PERSISTENCE_SEMANTICS
    assert loaded.manifest.long_term_checkpoint_policy == (
        SECTOR_RADAR_LONG_TERM_CHECKPOINT_POLICY
    )
    assert loaded.manifest.signal_transition_authority == "NONE"
    assert loaded.manifest.research_authority == "NONE"
    assert loaded.manifest.human_attention_authority == "NONE"
    assert loaded.manifest.investment_authority == "NONE"
    serialized = serialize_sector_radar_persistent_manifest(loaded.manifest)
    assert parse_sector_radar_persistent_manifest(serialized) == loaded.manifest


def test_persistent_bundle_detects_file_and_manifest_tampering(tmp_path: Path) -> None:
    directory = tmp_path / "state"
    write_bundle(directory)
    market_state_path = directory / "market-state.json"
    market_state_path.write_text(
        market_state_path.read_text(encoding="utf-8") + " ",
        encoding="utf-8",
    )
    with pytest.raises(SectorRadarPersistenceError, match="file SHA-256 mismatch"):
        load_sector_radar_persistent_bundle(directory)

    write_bundle(directory)
    manifest_path = directory / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["artifact_retention_days"] = 30
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        SectorRadarPersistenceError,
        match="artifact retention policy disagrees|manifest hash mismatch",
    ):
        load_sector_radar_persistent_bundle(directory)


def test_latest_success_artifact_is_authority_and_identical_cache_is_allowed(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifact"
    cache = tmp_path / "cache"
    write_bundle(artifact)
    write_bundle(cache)

    resolved = resolve_sector_radar_persistence(
        cache_directory=cache,
        artifact_directory=artifact,
        prior_success_found=True,
        artifact_available=True,
        bootstrap_path=BOOTSTRAP,
        bootstrap_manifest_path=BOOTSTRAP_MANIFEST,
        observed_at=UPDATED,
        expected_repository=REPOSITORY,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )

    assert resolved.source_kind == SOURCE_LATEST_SUCCESS_ARTIFACT
    assert resolved.source_bundle_manifest is not None
    assert resolved.source_bundle_manifest.source_run_id == 10
    assert resolved.market_state.state_hash == state().state_hash
    assert resolved.event_ledger.ledger_hash == ledger().ledger_hash


def test_cache_artifact_conflict_fails_closed(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    cache = tmp_path / "cache"
    write_bundle(artifact, run_id=10)
    write_bundle(
        cache,
        run_id=11,
        updated_at=UPDATED + timedelta(minutes=1),
    )

    with pytest.raises(SectorRadarPersistenceError, match="cache conflicts"):
        resolve_sector_radar_persistence(
            cache_directory=cache,
            artifact_directory=artifact,
            prior_success_found=True,
            artifact_available=True,
            bootstrap_path=BOOTSTRAP,
            bootstrap_manifest_path=BOOTSTRAP_MANIFEST,
            observed_at=UPDATED,
            expected_repository=REPOSITORY,
            expected_workflow=WORKFLOW,
            expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
        )


def test_latest_success_without_artifact_never_trusts_cache_or_bootstrap(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache"
    write_bundle(cache)

    with pytest.raises(
        SectorRadarPersistenceError,
        match="artifact is unavailable or expired",
    ):
        resolve_sector_radar_persistence(
            cache_directory=cache,
            artifact_directory=None,
            prior_success_found=True,
            artifact_available=False,
            bootstrap_path=BOOTSTRAP,
            bootstrap_manifest_path=BOOTSTRAP_MANIFEST,
            observed_at=UPDATED,
            expected_repository=REPOSITORY,
            expected_workflow=WORKFLOW,
            expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
        )


def test_orphan_cache_is_rejected_before_first_success(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    write_bundle(cache)

    with pytest.raises(SectorRadarPersistenceError, match="no matching successful artifact"):
        resolve_sector_radar_persistence(
            cache_directory=cache,
            artifact_directory=None,
            prior_success_found=False,
            artifact_available=False,
            bootstrap_path=BOOTSTRAP,
            bootstrap_manifest_path=BOOTSTRAP_MANIFEST,
            observed_at=UPDATED,
            expected_repository=REPOSITORY,
            expected_workflow=WORKFLOW,
            expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
        )


def test_first_run_uses_verified_committed_bootstrap_only_without_prior_state(
    tmp_path: Path,
) -> None:
    resolved = resolve_sector_radar_persistence(
        cache_directory=tmp_path / "absent-cache",
        artifact_directory=None,
        prior_success_found=False,
        artifact_available=False,
        bootstrap_path=BOOTSTRAP,
        bootstrap_manifest_path=BOOTSTRAP_MANIFEST,
        observed_at=UPDATED,
        expected_repository=REPOSITORY,
        expected_workflow=WORKFLOW,
        expected_parent_hint_mapping_hash=PARENT_HINT_HASH,
    )

    manifest = json.loads(BOOTSTRAP_MANIFEST.read_text(encoding="utf-8"))
    assert resolved.source_kind == SOURCE_COMMITTED_BOOTSTRAP
    assert resolved.source_bundle_manifest is None
    assert resolved.bootstrap_manifest_hash == manifest["manifest_hash"]
    assert resolved.market_state.state_hash == manifest["state_hash"]
    assert resolved.market_state.sessions[-1].isoformat() == "2026-09-04"
    assert resolved.event_ledger.events == ()
    assert resolved.event_ledger.signal_transition_authority == "NONE"
