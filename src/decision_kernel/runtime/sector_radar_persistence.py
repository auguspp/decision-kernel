from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json

from .sector_radar_events import (
    SectorRadarCandidateEventLedger,
    create_sector_radar_candidate_event_ledger,
    parse_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from .sector_radar_shadow import SECTOR_RADAR_SHADOW_POLICY_VERSION
from .sector_radar_state import (
    SectorRadarMarketState,
    parse_sector_radar_market_state,
    serialize_sector_radar_market_state,
)


SECTOR_RADAR_PERSISTENCE_SCHEMA_VERSION = 1
SECTOR_RADAR_PRODUCER_CONTRACT_VERSION = (
    "sector-radar-prospective-shadow-producer-v0"
)
SECTOR_RADAR_STATE_ARTIFACT_NAME = "sector-radar-state-bundle"
SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS = 90
SECTOR_RADAR_STATE_MANIFEST_FILENAME = "manifest.json"
SECTOR_RADAR_MARKET_STATE_FILENAME = "market-state.json"
SECTOR_RADAR_EVENT_LEDGER_FILENAME = "candidate-events.json"
SECTOR_RADAR_PERSISTENCE_SEMANTICS = (
    "LATEST_SUCCESS_IMMUTABLE_ARTIFACT_IS_RESTORE_AUTHORITY_"
    "CACHE_IS_IDENTICAL_ACCELERATION_COPY_ONLY"
)
SECTOR_RADAR_LONG_TERM_CHECKPOINT_POLICY = (
    "NONE_IN_V0_AFTER_ARTIFACT_EXPIRY_EXPLICIT_QUALIFIED_RECOVERY_IS_REQUIRED"
)
SECTOR_RADAR_PERSISTENCE_SIGNAL_TRANSITION_AUTHORITY = "NONE"
SECTOR_RADAR_PERSISTENCE_RESEARCH_AUTHORITY = "NONE"
SECTOR_RADAR_PERSISTENCE_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_PERSISTENCE_INVESTMENT_AUTHORITY = "NONE"

SOURCE_LATEST_SUCCESS_ARTIFACT = "LATEST_SUCCESS_ARTIFACT"
SOURCE_COMMITTED_BOOTSTRAP = "COMMITTED_DURABLE_BOOTSTRAP"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

_MANIFEST_FIELDS = {
    "schema_version",
    "producer_contract_version",
    "created_at",
    "updated_at",
    "source_repository",
    "source_workflow",
    "source_run_id",
    "source_run_attempt",
    "source_commit_sha",
    "market_session",
    "market_state_filename",
    "market_state_file_sha256",
    "market_state_hash",
    "event_ledger_filename",
    "event_ledger_file_sha256",
    "event_ledger_hash",
    "formula_version",
    "shadow_policy_version",
    "benchmark_thscode",
    "catalog_hash",
    "parent_hint_mapping_hash",
    "last_result_hash",
    "last_operation_status",
    "artifact_retention_days",
    "recovery_policy",
    "long_term_checkpoint_policy",
    "signal_transition_authority",
    "research_authority",
    "human_attention_authority",
    "investment_authority",
    "manifest_hash",
}


class SectorRadarPersistenceError(RuntimeError):
    """Persistent state cannot satisfy the fail-closed restore contract."""


@dataclass(frozen=True)
class SectorRadarPersistentBundleManifest:
    schema_version: int
    producer_contract_version: str
    created_at: datetime
    updated_at: datetime
    source_repository: str
    source_workflow: str
    source_run_id: int
    source_run_attempt: int
    source_commit_sha: str
    market_session: date
    market_state_filename: str
    market_state_file_sha256: str
    market_state_hash: str
    event_ledger_filename: str
    event_ledger_file_sha256: str
    event_ledger_hash: str
    formula_version: str
    shadow_policy_version: str
    benchmark_thscode: str
    catalog_hash: str
    parent_hint_mapping_hash: str
    last_result_hash: str | None
    last_operation_status: str
    artifact_retention_days: int
    recovery_policy: str
    long_term_checkpoint_policy: str
    signal_transition_authority: str
    research_authority: str
    human_attention_authority: str
    investment_authority: str
    manifest_hash: str


@dataclass(frozen=True)
class SectorRadarPersistentBundle:
    manifest: SectorRadarPersistentBundleManifest
    market_state: SectorRadarMarketState
    event_ledger: SectorRadarCandidateEventLedger


@dataclass(frozen=True)
class SectorRadarPersistenceResolution:
    source_kind: str
    market_state: SectorRadarMarketState
    event_ledger: SectorRadarCandidateEventLedger
    source_bundle_manifest: SectorRadarPersistentBundleManifest | None
    bootstrap_manifest_hash: str | None
    resolution_semantics: str = SECTOR_RADAR_PERSISTENCE_SEMANTICS
    signal_transition_authority: str = (
        SECTOR_RADAR_PERSISTENCE_SIGNAL_TRANSITION_AUTHORITY
    )
    research_authority: str = SECTOR_RADAR_PERSISTENCE_RESEARCH_AUTHORITY
    human_attention_authority: str = (
        SECTOR_RADAR_PERSISTENCE_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_PERSISTENCE_INVESTMENT_AUTHORITY


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    *,
    label: str,
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise SectorRadarPersistenceError(
            f"{label} fields disagree; missing={missing}; unknown={unknown}"
        )


def _require_non_empty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SectorRadarPersistenceError(
            f"{field} must be a non-empty trimmed string"
        )
    return value


def _require_hash(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SectorRadarPersistenceError(
            f"{field} must be a lowercase SHA-256 string"
        )
    return value


def _require_positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SectorRadarPersistenceError(f"{field} must be a positive integer")
    return value


def _parse_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SectorRadarPersistenceError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SectorRadarPersistenceError(
            f"{field} is not a valid ISO-8601 datetime"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SectorRadarPersistenceError(f"{field} must be timezone-aware")
    return parsed


def _parse_date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        raise SectorRadarPersistenceError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SectorRadarPersistenceError(f"{field} is not a valid ISO date") from exc


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SectorRadarPersistenceError(f"{field} must be timezone-aware")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_payload_without_hash(
    manifest: SectorRadarPersistentBundleManifest,
) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "producer_contract_version": manifest.producer_contract_version,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
        "source_repository": manifest.source_repository,
        "source_workflow": manifest.source_workflow,
        "source_run_id": manifest.source_run_id,
        "source_run_attempt": manifest.source_run_attempt,
        "source_commit_sha": manifest.source_commit_sha,
        "market_session": manifest.market_session,
        "market_state_filename": manifest.market_state_filename,
        "market_state_file_sha256": manifest.market_state_file_sha256,
        "market_state_hash": manifest.market_state_hash,
        "event_ledger_filename": manifest.event_ledger_filename,
        "event_ledger_file_sha256": manifest.event_ledger_file_sha256,
        "event_ledger_hash": manifest.event_ledger_hash,
        "formula_version": manifest.formula_version,
        "shadow_policy_version": manifest.shadow_policy_version,
        "benchmark_thscode": manifest.benchmark_thscode,
        "catalog_hash": manifest.catalog_hash,
        "parent_hint_mapping_hash": manifest.parent_hint_mapping_hash,
        "last_result_hash": manifest.last_result_hash,
        "last_operation_status": manifest.last_operation_status,
        "artifact_retention_days": manifest.artifact_retention_days,
        "recovery_policy": manifest.recovery_policy,
        "long_term_checkpoint_policy": manifest.long_term_checkpoint_policy,
        "signal_transition_authority": manifest.signal_transition_authority,
        "research_authority": manifest.research_authority,
        "human_attention_authority": manifest.human_attention_authority,
        "investment_authority": manifest.investment_authority,
    }


def _with_manifest_hash(
    manifest: SectorRadarPersistentBundleManifest,
) -> SectorRadarPersistentBundleManifest:
    return replace(
        manifest,
        manifest_hash=canonical_hash(_manifest_payload_without_hash(manifest)),
    )


def _validate_manifest(
    manifest: SectorRadarPersistentBundleManifest,
    *,
    verify_hash: bool,
) -> None:
    if manifest.schema_version != SECTOR_RADAR_PERSISTENCE_SCHEMA_VERSION:
        raise SectorRadarPersistenceError(
            "unsupported Sector Radar persistence schema version"
        )
    if manifest.producer_contract_version != SECTOR_RADAR_PRODUCER_CONTRACT_VERSION:
        raise SectorRadarPersistenceError(
            "Sector Radar producer contract version is unsupported"
        )
    _require_aware(manifest.created_at, field="bundle created_at")
    _require_aware(manifest.updated_at, field="bundle updated_at")
    if manifest.updated_at < manifest.created_at:
        raise SectorRadarPersistenceError("bundle updated_at precedes created_at")
    if not _REPOSITORY.fullmatch(manifest.source_repository):
        raise SectorRadarPersistenceError("bundle source repository is invalid")
    source_workflow = _require_non_empty(
        manifest.source_workflow,
        field="bundle source workflow",
    )
    if not source_workflow.startswith(".github/workflows/") or not source_workflow.endswith(
        (".yml", ".yaml")
    ):
        raise SectorRadarPersistenceError("bundle source workflow path is invalid")
    _require_positive_int(manifest.source_run_id, field="bundle source run id")
    _require_positive_int(
        manifest.source_run_attempt,
        field="bundle source run attempt",
    )
    if not _COMMIT_SHA.fullmatch(manifest.source_commit_sha):
        raise SectorRadarPersistenceError("bundle source commit SHA is invalid")
    if manifest.market_state_filename != SECTOR_RADAR_MARKET_STATE_FILENAME:
        raise SectorRadarPersistenceError("bundle market-state filename disagrees")
    if manifest.event_ledger_filename != SECTOR_RADAR_EVENT_LEDGER_FILENAME:
        raise SectorRadarPersistenceError("bundle event-ledger filename disagrees")
    for field, value in (
        ("market_state_file_sha256", manifest.market_state_file_sha256),
        ("market_state_hash", manifest.market_state_hash),
        ("event_ledger_file_sha256", manifest.event_ledger_file_sha256),
        ("event_ledger_hash", manifest.event_ledger_hash),
        ("catalog_hash", manifest.catalog_hash),
        ("parent_hint_mapping_hash", manifest.parent_hint_mapping_hash),
    ):
        _require_hash(value, field=f"bundle {field}")
    if manifest.last_result_hash is not None:
        _require_hash(manifest.last_result_hash, field="bundle last result hash")
    _require_non_empty(manifest.formula_version, field="bundle formula version")
    if manifest.shadow_policy_version != SECTOR_RADAR_SHADOW_POLICY_VERSION:
        raise SectorRadarPersistenceError("bundle shadow policy version disagrees")
    _require_non_empty(manifest.benchmark_thscode, field="bundle benchmark")
    _require_non_empty(
        manifest.last_operation_status,
        field="bundle last operation status",
    )
    if (
        manifest.artifact_retention_days
        != SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS
    ):
        raise SectorRadarPersistenceError("bundle artifact retention policy disagrees")
    if manifest.recovery_policy != SECTOR_RADAR_PERSISTENCE_SEMANTICS:
        raise SectorRadarPersistenceError("bundle recovery policy disagrees")
    if (
        manifest.long_term_checkpoint_policy
        != SECTOR_RADAR_LONG_TERM_CHECKPOINT_POLICY
    ):
        raise SectorRadarPersistenceError(
            "bundle long-term checkpoint policy disagrees"
        )
    if manifest.signal_transition_authority != "NONE":
        raise SectorRadarPersistenceError(
            "persistent bundle cannot carry signal-transition authority"
        )
    if manifest.research_authority != "NONE":
        raise SectorRadarPersistenceError(
            "persistent bundle cannot carry Research authority"
        )
    if manifest.human_attention_authority != "NONE":
        raise SectorRadarPersistenceError(
            "persistent bundle cannot carry Human attention authority"
        )
    if manifest.investment_authority != "NONE":
        raise SectorRadarPersistenceError(
            "persistent bundle cannot carry investment authority"
        )
    if verify_hash:
        _require_hash(manifest.manifest_hash, field="bundle manifest hash")
        if manifest.manifest_hash != canonical_hash(
            _manifest_payload_without_hash(manifest)
        ):
            raise SectorRadarPersistenceError("bundle manifest hash mismatch")


def serialize_sector_radar_persistent_manifest(
    manifest: SectorRadarPersistentBundleManifest,
) -> str:
    _validate_manifest(manifest, verify_hash=True)
    payload = _manifest_payload_without_hash(manifest)
    payload["manifest_hash"] = manifest.manifest_hash
    canonical_payload = json.loads(canonical_json(payload))
    return json.dumps(
        canonical_payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def parse_sector_radar_persistent_manifest(
    raw_manifest: str,
) -> SectorRadarPersistentBundleManifest:
    try:
        raw = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise SectorRadarPersistenceError(
            "Sector Radar bundle manifest must contain valid JSON"
        ) from exc
    if not isinstance(raw, Mapping):
        raise SectorRadarPersistenceError(
            "Sector Radar bundle manifest must be a JSON object"
        )
    _require_exact_fields(raw, _MANIFEST_FIELDS, label="Sector Radar bundle manifest")
    last_result_hash = raw["last_result_hash"]
    if last_result_hash is not None:
        last_result_hash = _require_hash(
            last_result_hash,
            field="bundle last result hash",
        )
    manifest = SectorRadarPersistentBundleManifest(
        schema_version=raw["schema_version"],
        producer_contract_version=_require_non_empty(
            raw["producer_contract_version"],
            field="bundle producer contract version",
        ),
        created_at=_parse_datetime(raw["created_at"], field="bundle created_at"),
        updated_at=_parse_datetime(raw["updated_at"], field="bundle updated_at"),
        source_repository=_require_non_empty(
            raw["source_repository"],
            field="bundle source repository",
        ),
        source_workflow=_require_non_empty(
            raw["source_workflow"],
            field="bundle source workflow",
        ),
        source_run_id=_require_positive_int(
            raw["source_run_id"],
            field="bundle source run id",
        ),
        source_run_attempt=_require_positive_int(
            raw["source_run_attempt"],
            field="bundle source run attempt",
        ),
        source_commit_sha=_require_non_empty(
            raw["source_commit_sha"],
            field="bundle source commit SHA",
        ),
        market_session=_parse_date(
            raw["market_session"],
            field="bundle market session",
        ),
        market_state_filename=_require_non_empty(
            raw["market_state_filename"],
            field="bundle market-state filename",
        ),
        market_state_file_sha256=_require_hash(
            raw["market_state_file_sha256"],
            field="bundle market-state file SHA-256",
        ),
        market_state_hash=_require_hash(
            raw["market_state_hash"],
            field="bundle market-state hash",
        ),
        event_ledger_filename=_require_non_empty(
            raw["event_ledger_filename"],
            field="bundle event-ledger filename",
        ),
        event_ledger_file_sha256=_require_hash(
            raw["event_ledger_file_sha256"],
            field="bundle event-ledger file SHA-256",
        ),
        event_ledger_hash=_require_hash(
            raw["event_ledger_hash"],
            field="bundle event-ledger hash",
        ),
        formula_version=_require_non_empty(
            raw["formula_version"],
            field="bundle formula version",
        ),
        shadow_policy_version=_require_non_empty(
            raw["shadow_policy_version"],
            field="bundle shadow policy version",
        ),
        benchmark_thscode=_require_non_empty(
            raw["benchmark_thscode"],
            field="bundle benchmark",
        ).upper(),
        catalog_hash=_require_hash(
            raw["catalog_hash"],
            field="bundle catalog hash",
        ),
        parent_hint_mapping_hash=_require_hash(
            raw["parent_hint_mapping_hash"],
            field="bundle parent-hint mapping hash",
        ),
        last_result_hash=last_result_hash,
        last_operation_status=_require_non_empty(
            raw["last_operation_status"],
            field="bundle last operation status",
        ),
        artifact_retention_days=_require_positive_int(
            raw["artifact_retention_days"],
            field="bundle artifact retention days",
        ),
        recovery_policy=_require_non_empty(
            raw["recovery_policy"],
            field="bundle recovery policy",
        ),
        long_term_checkpoint_policy=_require_non_empty(
            raw["long_term_checkpoint_policy"],
            field="bundle long-term checkpoint policy",
        ),
        signal_transition_authority=_require_non_empty(
            raw["signal_transition_authority"],
            field="bundle signal-transition authority",
        ),
        research_authority=_require_non_empty(
            raw["research_authority"],
            field="bundle Research authority",
        ),
        human_attention_authority=_require_non_empty(
            raw["human_attention_authority"],
            field="bundle Human attention authority",
        ),
        investment_authority=_require_non_empty(
            raw["investment_authority"],
            field="bundle investment authority",
        ),
        manifest_hash=_require_hash(
            raw["manifest_hash"],
            field="bundle manifest hash",
        ),
    )
    _validate_manifest(manifest, verify_hash=True)
    return manifest


def _validate_bundle_relationships(
    bundle: SectorRadarPersistentBundle,
    *,
    expected_repository: str | None,
    expected_workflow: str | None,
    expected_parent_hint_mapping_hash: str | None,
) -> None:
    manifest = bundle.manifest
    state = bundle.market_state
    ledger = bundle.event_ledger
    if expected_repository is not None and manifest.source_repository != expected_repository:
        raise SectorRadarPersistenceError(
            "persistent bundle repository identity disagrees"
        )
    if expected_workflow is not None and manifest.source_workflow != expected_workflow:
        raise SectorRadarPersistenceError(
            "persistent bundle workflow identity disagrees"
        )
    if (
        expected_parent_hint_mapping_hash is not None
        and manifest.parent_hint_mapping_hash != expected_parent_hint_mapping_hash
    ):
        raise SectorRadarPersistenceError(
            "persistent bundle parent-hint mapping identity disagrees"
        )
    if state.sessions[-1] != manifest.market_session:
        raise SectorRadarPersistenceError(
            "persistent bundle market session disagrees with market state"
        )
    if state.state_hash != manifest.market_state_hash:
        raise SectorRadarPersistenceError(
            "persistent bundle market-state hash disagrees"
        )
    if state.formula_version != manifest.formula_version:
        raise SectorRadarPersistenceError(
            "persistent bundle formula version disagrees with market state"
        )
    if state.benchmark_thscode != manifest.benchmark_thscode:
        raise SectorRadarPersistenceError(
            "persistent bundle benchmark disagrees with market state"
        )
    if state.catalog_hash != manifest.catalog_hash:
        raise SectorRadarPersistenceError(
            "persistent bundle catalog hash disagrees with market state"
        )
    if ledger.ledger_hash != manifest.event_ledger_hash:
        raise SectorRadarPersistenceError(
            "persistent bundle event-ledger hash disagrees"
        )
    if ledger.signal_transition_authority != "NONE":
        raise SectorRadarPersistenceError(
            "persistent event ledger carries signal-transition authority"
        )


def load_sector_radar_persistent_bundle(
    directory: Path,
    *,
    expected_repository: str | None = None,
    expected_workflow: str | None = None,
    expected_parent_hint_mapping_hash: str | None = None,
) -> SectorRadarPersistentBundle:
    manifest_path = directory / SECTOR_RADAR_STATE_MANIFEST_FILENAME
    try:
        manifest = parse_sector_radar_persistent_manifest(
            manifest_path.read_text(encoding="utf-8")
        )
        state_bytes = (directory / manifest.market_state_filename).read_bytes()
        ledger_bytes = (directory / manifest.event_ledger_filename).read_bytes()
    except OSError as exc:
        raise SectorRadarPersistenceError(
            f"persistent bundle is missing or unreadable at {directory}"
        ) from exc
    if _sha256_bytes(state_bytes) != manifest.market_state_file_sha256:
        raise SectorRadarPersistenceError(
            "persistent market-state file SHA-256 mismatch"
        )
    if _sha256_bytes(ledger_bytes) != manifest.event_ledger_file_sha256:
        raise SectorRadarPersistenceError(
            "persistent event-ledger file SHA-256 mismatch"
        )
    try:
        state = parse_sector_radar_market_state(state_bytes.decode("utf-8"))
        ledger = parse_sector_radar_candidate_event_ledger(
            ledger_bytes.decode("utf-8")
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise SectorRadarPersistenceError(
            "persistent bundle state payload is invalid"
        ) from exc
    bundle = SectorRadarPersistentBundle(
        manifest=manifest,
        market_state=state,
        event_ledger=ledger,
    )
    _validate_bundle_relationships(
        bundle,
        expected_repository=expected_repository,
        expected_workflow=expected_workflow,
        expected_parent_hint_mapping_hash=expected_parent_hint_mapping_hash,
    )
    return bundle


def _directory_has_content(directory: Path | None) -> bool:
    if directory is None or not directory.exists():
        return False
    if not directory.is_dir():
        return True
    try:
        return any(directory.iterdir())
    except OSError as exc:
        raise SectorRadarPersistenceError(
            f"cannot inspect persistence directory {directory}"
        ) from exc


def write_sector_radar_persistent_bundle(
    directory: Path,
    *,
    market_state: SectorRadarMarketState,
    event_ledger: SectorRadarCandidateEventLedger,
    created_at: datetime,
    updated_at: datetime,
    source_repository: str,
    source_workflow: str,
    source_run_id: int,
    source_run_attempt: int,
    source_commit_sha: str,
    parent_hint_mapping_hash: str,
    last_result_hash: str | None,
    last_operation_status: str,
) -> SectorRadarPersistentBundle:
    """Atomically replace one validated cache/artifact bundle directory."""

    _require_aware(created_at, field="bundle created_at")
    _require_aware(updated_at, field="bundle updated_at")
    if updated_at < created_at:
        raise SectorRadarPersistenceError("bundle updated_at precedes created_at")
    state_text = serialize_sector_radar_market_state(market_state)
    ledger_text = serialize_sector_radar_candidate_event_ledger(event_ledger)
    state_bytes = state_text.encode("utf-8")
    ledger_bytes = ledger_text.encode("utf-8")
    manifest = SectorRadarPersistentBundleManifest(
        schema_version=SECTOR_RADAR_PERSISTENCE_SCHEMA_VERSION,
        producer_contract_version=SECTOR_RADAR_PRODUCER_CONTRACT_VERSION,
        created_at=created_at,
        updated_at=updated_at,
        source_repository=source_repository,
        source_workflow=source_workflow,
        source_run_id=source_run_id,
        source_run_attempt=source_run_attempt,
        source_commit_sha=source_commit_sha,
        market_session=market_state.sessions[-1],
        market_state_filename=SECTOR_RADAR_MARKET_STATE_FILENAME,
        market_state_file_sha256=_sha256_bytes(state_bytes),
        market_state_hash=market_state.state_hash,
        event_ledger_filename=SECTOR_RADAR_EVENT_LEDGER_FILENAME,
        event_ledger_file_sha256=_sha256_bytes(ledger_bytes),
        event_ledger_hash=event_ledger.ledger_hash,
        formula_version=market_state.formula_version,
        shadow_policy_version=SECTOR_RADAR_SHADOW_POLICY_VERSION,
        benchmark_thscode=market_state.benchmark_thscode,
        catalog_hash=market_state.catalog_hash,
        parent_hint_mapping_hash=parent_hint_mapping_hash,
        last_result_hash=last_result_hash,
        last_operation_status=last_operation_status,
        artifact_retention_days=SECTOR_RADAR_STATE_ARTIFACT_RETENTION_DAYS,
        recovery_policy=SECTOR_RADAR_PERSISTENCE_SEMANTICS,
        long_term_checkpoint_policy=SECTOR_RADAR_LONG_TERM_CHECKPOINT_POLICY,
        signal_transition_authority="NONE",
        research_authority="NONE",
        human_attention_authority="NONE",
        investment_authority="NONE",
        manifest_hash="",
    )
    manifest = _with_manifest_hash(manifest)
    _validate_manifest(manifest, verify_hash=True)
    manifest_text = serialize_sector_radar_persistent_manifest(manifest)

    directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = directory.with_name(f".{directory.name}.tmp")
    backup = directory.with_name(f".{directory.name}.backup")
    for candidate in (temporary, backup):
        if candidate.exists():
            if candidate.is_dir():
                shutil.rmtree(candidate)
            else:
                candidate.unlink()
    temporary.mkdir(parents=True)
    try:
        (temporary / SECTOR_RADAR_MARKET_STATE_FILENAME).write_bytes(state_bytes)
        (temporary / SECTOR_RADAR_EVENT_LEDGER_FILENAME).write_bytes(ledger_bytes)
        (temporary / SECTOR_RADAR_STATE_MANIFEST_FILENAME).write_text(
            manifest_text,
            encoding="utf-8",
        )
        candidate_bundle = load_sector_radar_persistent_bundle(
            temporary,
            expected_repository=source_repository,
            expected_workflow=source_workflow,
            expected_parent_hint_mapping_hash=parent_hint_mapping_hash,
        )
        if directory.exists():
            directory.replace(backup)
        temporary.replace(directory)
        if backup.exists():
            shutil.rmtree(backup)
        return candidate_bundle
    except Exception:
        if directory.exists() and backup.exists():
            shutil.rmtree(directory)
            backup.replace(directory)
        elif not directory.exists() and backup.exists():
            backup.replace(directory)
        raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
        if backup.exists():
            shutil.rmtree(backup)


def load_sector_radar_committed_bootstrap(
    *,
    bootstrap_path: Path,
    bootstrap_manifest_path: Path,
    ledger_created_at: datetime,
) -> SectorRadarPersistenceResolution:
    """Load the repository bootstrap only as the first explicit restore source."""

    _require_aware(ledger_created_at, field="bootstrap event-ledger created_at")
    try:
        raw_manifest = json.loads(
            bootstrap_manifest_path.read_text(encoding="utf-8")
        )
        compressed = bootstrap_path.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise SectorRadarPersistenceError(
            "committed Sector Radar bootstrap is missing or malformed"
        ) from exc
    if not isinstance(raw_manifest, Mapping):
        raise SectorRadarPersistenceError(
            "committed Sector Radar bootstrap manifest must be an object"
        )
    manifest = dict(raw_manifest)
    claimed_manifest_hash = manifest.pop("manifest_hash", None)
    claimed_manifest_hash = _require_hash(
        claimed_manifest_hash,
        field="bootstrap manifest hash",
    )
    if canonical_hash(manifest) != claimed_manifest_hash:
        raise SectorRadarPersistenceError("bootstrap manifest hash mismatch")
    if len(compressed) != manifest.get("compressed_bytes"):
        raise SectorRadarPersistenceError("bootstrap compressed byte size mismatch")
    if _sha256_bytes(compressed) != manifest.get("compressed_sha256"):
        raise SectorRadarPersistenceError("bootstrap compressed SHA-256 mismatch")
    try:
        uncompressed = gzip.decompress(compressed)
    except OSError as exc:
        raise SectorRadarPersistenceError("bootstrap gzip payload is invalid") from exc
    if len(uncompressed) != manifest.get("uncompressed_bytes"):
        raise SectorRadarPersistenceError("bootstrap uncompressed byte size mismatch")
    if _sha256_bytes(uncompressed) != manifest.get("uncompressed_sha256"):
        raise SectorRadarPersistenceError("bootstrap uncompressed SHA-256 mismatch")
    try:
        state = parse_sector_radar_market_state(uncompressed.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SectorRadarPersistenceError(
            "bootstrap market state fails strict parsing"
        ) from exc
    if state.state_hash != manifest.get("state_hash"):
        raise SectorRadarPersistenceError("bootstrap state hash disagrees")
    if state.catalog_hash != manifest.get("catalog_hash"):
        raise SectorRadarPersistenceError("bootstrap catalog hash disagrees")
    if state.formula_version != manifest.get("formula_version"):
        raise SectorRadarPersistenceError("bootstrap formula version disagrees")
    if state.sessions[-1].isoformat() != manifest.get("session_end"):
        raise SectorRadarPersistenceError("bootstrap terminal session disagrees")
    if len(state.sessions) != manifest.get("session_count"):
        raise SectorRadarPersistenceError("bootstrap session count disagrees")
    if len(state.series) != manifest.get("series_count"):
        raise SectorRadarPersistenceError("bootstrap series count disagrees")
    ledger = create_sector_radar_candidate_event_ledger(
        created_at=ledger_created_at,
        source="committed durable Sector Radar bootstrap",
    )
    return SectorRadarPersistenceResolution(
        source_kind=SOURCE_COMMITTED_BOOTSTRAP,
        market_state=state,
        event_ledger=ledger,
        source_bundle_manifest=None,
        bootstrap_manifest_hash=claimed_manifest_hash,
    )


def resolve_sector_radar_persistence(
    *,
    cache_directory: Path,
    artifact_directory: Path | None,
    prior_success_found: bool,
    artifact_available: bool,
    bootstrap_path: Path,
    bootstrap_manifest_path: Path,
    observed_at: datetime,
    expected_repository: str,
    expected_workflow: str,
    expected_parent_hint_mapping_hash: str,
) -> SectorRadarPersistenceResolution:
    """Resolve state without granting truth authority to an orphan cache.

    The newest successful workflow run is authoritative. If that run exists but its
    artifact is expired, missing, malformed, or conflicts with cache, ordinary daily
    production fails closed and requires an explicit qualified recovery procedure.
    The committed bootstrap is allowed only before any successful producer run.
    """

    _require_aware(observed_at, field="persistence resolution observed_at")
    if artifact_available and not prior_success_found:
        raise SectorRadarPersistenceError(
            "state artifact cannot exist without a prior successful producer run"
        )
    cache_present = _directory_has_content(cache_directory)

    if prior_success_found:
        if not artifact_available or artifact_directory is None:
            raise SectorRadarPersistenceError(
                "latest successful Sector Radar state artifact is unavailable or "
                "expired; explicit qualified recovery is required"
            )
        artifact_bundle = load_sector_radar_persistent_bundle(
            artifact_directory,
            expected_repository=expected_repository,
            expected_workflow=expected_workflow,
            expected_parent_hint_mapping_hash=expected_parent_hint_mapping_hash,
        )
        if cache_present:
            cache_bundle = load_sector_radar_persistent_bundle(
                cache_directory,
                expected_repository=expected_repository,
                expected_workflow=expected_workflow,
                expected_parent_hint_mapping_hash=expected_parent_hint_mapping_hash,
            )
            if cache_bundle.manifest.manifest_hash != artifact_bundle.manifest.manifest_hash:
                raise SectorRadarPersistenceError(
                    "Sector Radar cache conflicts with the latest successful artifact"
                )
            if (
                cache_bundle.market_state.state_hash
                != artifact_bundle.market_state.state_hash
                or cache_bundle.event_ledger.ledger_hash
                != artifact_bundle.event_ledger.ledger_hash
            ):
                raise SectorRadarPersistenceError(
                    "Sector Radar cache state conflicts with the latest successful artifact"
                )
        return SectorRadarPersistenceResolution(
            source_kind=SOURCE_LATEST_SUCCESS_ARTIFACT,
            market_state=artifact_bundle.market_state,
            event_ledger=artifact_bundle.event_ledger,
            source_bundle_manifest=artifact_bundle.manifest,
            bootstrap_manifest_hash=None,
        )

    if cache_present:
        raise SectorRadarPersistenceError(
            "Sector Radar cache has no matching successful artifact authority"
        )
    return load_sector_radar_committed_bootstrap(
        bootstrap_path=bootstrap_path,
        bootstrap_manifest_path=bootstrap_manifest_path,
        ledger_created_at=observed_at,
    )
