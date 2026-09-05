from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, TextIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from decision_kernel.adapters.hithink import latest_completed_a_share_session
from decision_kernel.identity import canonical_hash, canonical_json

from . import hithink_http, hithink_index_http, hithink_sector_breadth_http
from .sector_parent_hints import (
    SectorParentHintIndex,
    load_sector_parent_hints,
    validate_sector_parent_hint_catalog,
)
from .sector_radar_daily import (
    PREPARATION_BUDGET_EXCEEDED,
    PREPARATION_QUIET,
    PREPARATION_READY,
    SectorRadarDailyPreparation,
    SectorRadarDailyResult,
    finalize_sector_radar_daily_run,
    prepare_sector_radar_daily_run,
    render_sector_radar_daily_preparation_markdown,
    render_sector_radar_daily_summary,
    serialize_sector_radar_daily_preparation,
    serialize_sector_radar_daily_result,
)
from .sector_radar_persistence import (
    SECTOR_RADAR_STATE_ARTIFACT_NAME,
    SOURCE_COMMITTED_BOOTSTRAP,
    SectorRadarPersistenceResolution,
    SectorRadarPersistentBundle,
    resolve_sector_radar_persistence,
    write_sector_radar_persistent_bundle,
)
from .sector_radar_state import (
    STATE_UPDATE_ALREADY_CURRENT,
    STATE_UPDATE_APPENDED,
    append_qualified_sector_snapshot,
)


SECTOR_RADAR_WORKFLOW_PATH = ".github/workflows/sector-radar-shadow.yml"
SECTOR_RADAR_WORKFLOW_FILE = "sector-radar-shadow.yml"
SECTOR_RADAR_BOOTSTRAP_PATH = Path(
    "radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz"
)
SECTOR_RADAR_BOOTSTRAP_MANIFEST_PATH = Path(
    "radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json"
)
SECTOR_RADAR_PARENT_HINTS_PATH = Path(
    "radar_inputs/sector-parent-hints-2026-09-05.json"
)
SECTOR_RADAR_DEFAULT_STATE_DIRECTORY = Path("decision-state/sector-radar")
SECTOR_RADAR_DEFAULT_ARTIFACT_DIRECTORY = Path(
    "restored-artifact/sector-radar"
)
SECTOR_RADAR_DEFAULT_OUTPUT_DIRECTORY = Path("sector-radar-run")
SECTOR_RADAR_GITHUB_API_VERSION = "2022-11-28"
SECTOR_RADAR_MEMBERSHIP_REQUEST_DELAY_SECONDS = 0.25
SECTOR_RADAR_SAME_SESSION_VALIDATION_SCHEMA_VERSION = 1
SECTOR_RADAR_SAME_SESSION_VALIDATION_SEMANTICS = (
    "EXACT_SAME_COMPLETED_SESSION_MARKET_STATE_VALIDATION_ONLY"
)

PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT = (
    "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"
)
PRODUCER_STATUS_APPENDED_QUIET = "APPENDED_COMPLETED_SESSION_QUIET"
PRODUCER_STATUS_APPENDED_WITH_CANDIDATES = (
    "APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES"
)
PRODUCER_STATUS_FAILED = "FAILED_CLOSED"

SECTOR_RADAR_PRODUCER_OPERATIONS_SCHEMA_VERSION = 1
SECTOR_RADAR_PRODUCER_OPERATIONS_SEMANTICS = (
    "INDEPENDENT_PROSPECTIVE_SHADOW_OPERATIONS_ONLY"
)
SECTOR_RADAR_PRODUCER_SIGNAL_TRANSITION_AUTHORITY = "NONE"
SECTOR_RADAR_PRODUCER_RESEARCH_AUTHORITY = "NONE"
SECTOR_RADAR_PRODUCER_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_PRODUCER_INVESTMENT_AUTHORITY = "NONE"

_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")

_RequestJSON = Callable[[str], Mapping[str, Any]]
_Now = Callable[[], datetime]


class SectorRadarProducerError(RuntimeError):
    """The independent producer cannot publish the required shadow state."""


@dataclass(frozen=True)
class SectorRadarPreviousArtifactDiscovery:
    prior_success_found: bool
    artifact_available: bool
    prior_run_id: int | None
    prior_run_attempt: int | None
    prior_head_sha: str | None
    artifact_id: int | None
    artifact_expired: bool | None
    artifact_name: str


@dataclass(frozen=True)
class SectorRadarProducerContext:
    repository: str
    workflow_path: str
    run_id: int
    run_attempt: int
    commit_sha: str
    observed_at: datetime


@dataclass(frozen=True)
class SectorRadarProducerOperations:
    schema_version: int
    status: str
    started_at: datetime
    completed_at: datetime
    repository: str
    workflow_path: str
    run_id: int
    run_attempt: int
    commit_sha: str
    input_source_kind: str | None
    input_bundle_manifest_hash: str | None
    bootstrap_manifest_hash: str | None
    input_market_state_hash: str | None
    input_event_ledger_hash: str | None
    latest_cached_session: date | None
    latest_completed_session: date | None
    direct_next_session: date | None
    state_update_status: str | None
    preparation_status: str | None
    preparation_hash: str | None
    candidate_count: int | None
    membership_request_count: int | None
    output_market_state_hash: str | None
    output_event_ledger_hash: str | None
    result_hash: str | None
    error_type: str | None
    error_message: str | None
    operations_hash: str
    operations_semantics: str = SECTOR_RADAR_PRODUCER_OPERATIONS_SEMANTICS
    signal_transition_authority: str = (
        SECTOR_RADAR_PRODUCER_SIGNAL_TRANSITION_AUTHORITY
    )
    research_authority: str = SECTOR_RADAR_PRODUCER_RESEARCH_AUTHORITY
    human_attention_authority: str = (
        SECTOR_RADAR_PRODUCER_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_PRODUCER_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarProducerOutcome:
    status: str
    operations: SectorRadarProducerOperations
    persistent_bundle: SectorRadarPersistentBundle
    preparation: SectorRadarDailyPreparation | None
    result: SectorRadarDailyResult | None


def _positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SectorRadarProducerError(f"{field} must be a positive integer")
    return value


def _aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SectorRadarProducerError(f"{field} must be timezone-aware")


def _validate_context(context: SectorRadarProducerContext) -> None:
    if not _REPOSITORY.fullmatch(context.repository):
        raise SectorRadarProducerError("producer repository identity is invalid")
    if context.workflow_path != SECTOR_RADAR_WORKFLOW_PATH:
        raise SectorRadarProducerError("producer workflow identity disagrees")
    _positive_int(context.run_id, field="producer run id")
    _positive_int(context.run_attempt, field="producer run attempt")
    if not _COMMIT_SHA.fullmatch(context.commit_sha):
        raise SectorRadarProducerError("producer commit SHA is invalid")
    _aware(context.observed_at, field="producer observed_at")


def _default_github_request_json(*, token: str, timeout_seconds: float) -> _RequestJSON:
    def request_json(url: str) -> Mapping[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": SECTOR_RADAR_GITHUB_API_VERSION,
                "User-Agent": "decision-kernel-sector-radar",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SectorRadarProducerError(
                f"GitHub API request failed with status {exc.code}"
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SectorRadarProducerError(
                "GitHub API request or response decoding failed"
            ) from exc
        if not isinstance(payload, Mapping):
            raise SectorRadarProducerError("GitHub API response is not an object")
        return payload

    return request_json


def discover_previous_sector_radar_artifact(
    *,
    repository: str,
    workflow_file: str,
    current_run_id: int,
    token: str | None,
    request_json: _RequestJSON | None = None,
    api_base_url: str = "https://api.github.com",
    timeout_seconds: float = 15.0,
) -> SectorRadarPreviousArtifactDiscovery:
    """Inspect only the newest prior successful workflow run.

    If its state artifact is missing or expired, callers must fail closed rather than
    searching an older run and silently bridging a potentially missing state update.
    """

    if not _REPOSITORY.fullmatch(repository):
        raise SectorRadarProducerError("artifact discovery repository is invalid")
    if workflow_file != SECTOR_RADAR_WORKFLOW_FILE:
        raise SectorRadarProducerError("artifact discovery workflow file disagrees")
    _positive_int(current_run_id, field="current workflow run id")
    if timeout_seconds <= 0:
        raise SectorRadarProducerError("GitHub API timeout must be positive")
    if request_json is None:
        if not token:
            raise SectorRadarProducerError(
                "GITHUB_TOKEN is required for state-artifact discovery"
            )
        request_json = _default_github_request_json(
            token=token,
            timeout_seconds=timeout_seconds,
        )

    workflow_ref = quote(workflow_file, safe="")
    query = urlencode(
        {
            "branch": "main",
            "status": "success",
            "event": "workflow_dispatch",
            "per_page": "2",
        }
    )
    runs_url = (
        f"{api_base_url}/repos/{repository}/actions/workflows/"
        f"{workflow_ref}/runs?{query}"
    )
    runs_payload = request_json(runs_url)
    raw_runs = runs_payload.get("workflow_runs")
    if not isinstance(raw_runs, list):
        raise SectorRadarProducerError(
            "GitHub workflow-runs response has no workflow_runs array"
        )
    prior_runs = []
    for raw in raw_runs:
        if not isinstance(raw, Mapping):
            raise SectorRadarProducerError(
                "GitHub workflow-runs response contains a malformed run"
            )
        run_id = _positive_int(raw.get("id"), field="prior workflow run id")
        if run_id == current_run_id:
            continue
        if raw.get("conclusion") != "success" or raw.get("head_branch") != "main":
            raise SectorRadarProducerError(
                "GitHub workflow-runs response violates successful-main filtering"
            )
        prior_runs.append(raw)
    if not prior_runs:
        return SectorRadarPreviousArtifactDiscovery(
            prior_success_found=False,
            artifact_available=False,
            prior_run_id=None,
            prior_run_attempt=None,
            prior_head_sha=None,
            artifact_id=None,
            artifact_expired=None,
            artifact_name=SECTOR_RADAR_STATE_ARTIFACT_NAME,
        )

    prior = prior_runs[0]
    prior_run_id = _positive_int(prior.get("id"), field="prior workflow run id")
    prior_run_attempt = _positive_int(
        prior.get("run_attempt"),
        field="prior workflow run attempt",
    )
    prior_head_sha = prior.get("head_sha")
    if not isinstance(prior_head_sha, str) or not _COMMIT_SHA.fullmatch(prior_head_sha):
        raise SectorRadarProducerError("prior workflow head SHA is invalid")

    artifacts_url = (
        f"{api_base_url}/repos/{repository}/actions/runs/"
        f"{prior_run_id}/artifacts?per_page=100"
    )
    artifacts_payload = request_json(artifacts_url)
    raw_artifacts = artifacts_payload.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise SectorRadarProducerError(
            "GitHub artifacts response has no artifacts array"
        )
    matches = [
        item
        for item in raw_artifacts
        if isinstance(item, Mapping)
        and item.get("name") == SECTOR_RADAR_STATE_ARTIFACT_NAME
    ]
    if len(matches) > 1:
        raise SectorRadarProducerError(
            "latest successful run contains duplicate state artifacts"
        )
    if not matches:
        return SectorRadarPreviousArtifactDiscovery(
            prior_success_found=True,
            artifact_available=False,
            prior_run_id=prior_run_id,
            prior_run_attempt=prior_run_attempt,
            prior_head_sha=prior_head_sha,
            artifact_id=None,
            artifact_expired=None,
            artifact_name=SECTOR_RADAR_STATE_ARTIFACT_NAME,
        )
    artifact = matches[0]
    artifact_id = _positive_int(artifact.get("id"), field="state artifact id")
    expired = artifact.get("expired")
    if not isinstance(expired, bool):
        raise SectorRadarProducerError("state artifact expiration flag is invalid")
    size_in_bytes = _positive_int(
        artifact.get("size_in_bytes"),
        field="state artifact size",
    )
    del size_in_bytes
    return SectorRadarPreviousArtifactDiscovery(
        prior_success_found=True,
        artifact_available=not expired,
        prior_run_id=prior_run_id,
        prior_run_attempt=prior_run_attempt,
        prior_head_sha=prior_head_sha,
        artifact_id=artifact_id,
        artifact_expired=expired,
        artifact_name=SECTOR_RADAR_STATE_ARTIFACT_NAME,
    )


def write_github_output(
    path: Path,
    discovery: SectorRadarPreviousArtifactDiscovery,
) -> None:
    values = {
        "prior_success_found": str(discovery.prior_success_found).lower(),
        "artifact_available": str(discovery.artifact_available).lower(),
        "artifact_run_id": "" if discovery.prior_run_id is None else str(discovery.prior_run_id),
        "artifact_run_attempt": (
            "" if discovery.prior_run_attempt is None else str(discovery.prior_run_attempt)
        ),
        "artifact_head_sha": discovery.prior_head_sha or "",
        "artifact_id": "" if discovery.artifact_id is None else str(discovery.artifact_id),
        "artifact_expired": (
            "" if discovery.artifact_expired is None else str(discovery.artifact_expired).lower()
        ),
        "artifact_name": discovery.artifact_name,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            print(f"{key}={value}", file=output)


def _validated_calendar(
    sessions: Sequence[date],
    *,
    cached_session: date,
) -> tuple[date, ...]:
    normalized = tuple(sessions)
    if normalized != tuple(sorted(set(normalized))):
        raise SectorRadarProducerError(
            "A-share trading calendar must be unique and ascending"
        )
    if cached_session not in normalized:
        raise SectorRadarProducerError(
            "cached Sector Radar session is absent from the current trading calendar"
        )
    return normalized


def _next_calendar_session(
    sessions: Sequence[date],
    *,
    cached_session: date,
) -> date:
    normalized = _validated_calendar(
        sessions,
        cached_session=cached_session,
    )
    index = normalized.index(cached_session)
    if index + 1 >= len(normalized):
        raise SectorRadarProducerError(
            "trading calendar does not expose the session after cached state"
        )
    return normalized[index + 1]


def _operations_payload_without_hash(
    operations: SectorRadarProducerOperations,
) -> dict[str, Any]:
    payload = asdict(operations)
    payload.pop("operations_hash")
    return payload


def _with_operations_hash(
    operations: SectorRadarProducerOperations,
) -> SectorRadarProducerOperations:
    return replace(
        operations,
        operations_hash=canonical_hash(
            _operations_payload_without_hash(operations)
        ),
    )


def _validate_operations(operations: SectorRadarProducerOperations) -> None:
    if operations.schema_version != SECTOR_RADAR_PRODUCER_OPERATIONS_SCHEMA_VERSION:
        raise SectorRadarProducerError("unsupported producer operations schema")
    _aware(operations.started_at, field="operations started_at")
    _aware(operations.completed_at, field="operations completed_at")
    if operations.completed_at < operations.started_at:
        raise SectorRadarProducerError("operations completed_at precedes started_at")
    if operations.operations_semantics != SECTOR_RADAR_PRODUCER_OPERATIONS_SEMANTICS:
        raise SectorRadarProducerError("producer operations semantics disagree")
    if operations.signal_transition_authority != "NONE":
        raise SectorRadarProducerError(
            "producer operations cannot carry signal-transition authority"
        )
    if operations.research_authority != "NONE":
        raise SectorRadarProducerError(
            "producer operations cannot carry Research authority"
        )
    if operations.human_attention_authority != "NONE":
        raise SectorRadarProducerError(
            "producer operations cannot carry Human attention authority"
        )
    if operations.investment_authority != "NONE":
        raise SectorRadarProducerError(
            "producer operations cannot carry investment authority"
        )
    if operations.operations_hash != canonical_hash(
        _operations_payload_without_hash(operations)
    ):
        raise SectorRadarProducerError("producer operations hash mismatch")


def serialize_sector_radar_producer_operations(
    operations: SectorRadarProducerOperations,
) -> str:
    _validate_operations(operations)
    payload = _operations_payload_without_hash(operations)
    payload["operations_hash"] = operations.operations_hash
    return json.dumps(
        json.loads(canonical_json(payload)),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def render_sector_radar_producer_operations(
    operations: SectorRadarProducerOperations,
) -> str:
    _validate_operations(operations)
    lines = [
        f"## Sector Discovery Radar operations — `{operations.status}`",
        "",
        "**SHADOW OBSERVATION ONLY**",
        "",
        "`NOT RESEARCH` · `NOT A RECOMMENDATION`",
        "",
        "`HUMAN ATTENTION AUTHORITY = NONE` · `INVESTMENT AUTHORITY = NONE`",
        "",
        f"Run: `{operations.run_id}` attempt `{operations.run_attempt}`",
        "",
    ]
    if operations.input_source_kind is not None:
        lines.append(f"Restore source: `{operations.input_source_kind}`")
        lines.append("")
    if operations.latest_cached_session is not None:
        lines.append(
            f"Cached completed session: `{operations.latest_cached_session.isoformat()}`"
        )
        lines.append("")
    if operations.latest_completed_session is not None:
        lines.append(
            "Latest qualified completed session: "
            f"`{operations.latest_completed_session.isoformat()}`"
        )
        lines.append("")
    if operations.direct_next_session is not None:
        lines.append(
            "Direct next calendar session: "
            f"`{operations.direct_next_session.isoformat()}`"
        )
        lines.append("")
    if operations.candidate_count is not None:
        lines.append(
            f"New false→true candidates: **{operations.candidate_count}**"
        )
        lines.append("")
    if operations.membership_request_count is not None:
        lines.append(
            "Distinct current-membership requests: "
            f"**{operations.membership_request_count}**"
        )
        lines.append("")
    if operations.error_message is not None:
        lines.extend(
            [
                f"Failure: `{operations.error_type}`",
                "",
                operations.error_message,
                "",
                "No new persistent state was published by this failed run.",
                "",
            ]
        )
    elif operations.status == PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT:
        lines.extend(
            [
                "The restored market state exactly matched the provider's latest "
                "completed-session snapshot.",
                "",
                "This was validation only: no retrospective candidate was written "
                "to the prospective event ledger.",
                "",
            ]
        )
    elif operations.status == PRODUCER_STATUS_APPENDED_QUIET:
        lines.extend(
            [
                "Exactly one completed session was appended and no new qualified "
                "state entry was observed.",
                "",
            ]
        )
    elif operations.status == PRODUCER_STATUS_APPENDED_WITH_CANDIDATES:
        lines.extend(
            [
                "Exactly one completed session was appended and the complete "
                "candidate composition is retained in the run artifact.",
                "",
            ]
        )
    lines.extend(
        [
            f"Operations hash: `{operations.operations_hash}`",
            "",
            "Artifacts are retained for the declared workflow retention window. "
            "There is no automatic long-term checkpoint in v0; expiration of the "
            "latest successful state artifact requires explicit qualified recovery.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_sector_radar_operations(
    output_directory: Path,
    operations: SectorRadarProducerOperations,
) -> None:
    _write_text_atomic(
        output_directory / "operations.json",
        serialize_sector_radar_producer_operations(operations),
    )
    _write_text_atomic(
        output_directory / "operations.md",
        render_sector_radar_producer_operations(operations),
    )


def _same_session_validation_payload(
    *,
    context: SectorRadarProducerContext,
    validated_at: datetime,
    catalog_hash: str,
    parent_hint_mapping_hash: str,
    qualified_snapshot: Any,
    input_market_state_hash: str,
    output_market_state_hash: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": SECTOR_RADAR_SAME_SESSION_VALIDATION_SCHEMA_VERSION,
        "validated_at": validated_at,
        "repository": context.repository,
        "workflow_path": context.workflow_path,
        "run_id": context.run_id,
        "run_attempt": context.run_attempt,
        "commit_sha": context.commit_sha,
        "market_session": qualified_snapshot.market_session,
        "catalog_hash": catalog_hash,
        "parent_hint_mapping_hash": parent_hint_mapping_hash,
        "qualified_snapshot_hash": canonical_hash(asdict(qualified_snapshot)),
        "input_market_state_hash": input_market_state_hash,
        "output_market_state_hash": output_market_state_hash,
        "state_update_status": STATE_UPDATE_ALREADY_CURRENT,
        "validation_semantics": SECTOR_RADAR_SAME_SESSION_VALIDATION_SEMANTICS,
        "signal_transition_authority": "NONE",
        "research_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    payload["validation_hash"] = canonical_hash(payload)
    return payload


def write_sector_radar_same_session_validation(
    *,
    output_directory: Path,
    context: SectorRadarProducerContext,
    validated_at: datetime,
    catalog_hash: str,
    parent_hint_mapping_hash: str,
    qualified_snapshot: Any,
    input_market_state_hash: str,
    output_market_state_hash: str,
) -> str:
    payload = _same_session_validation_payload(
        context=context,
        validated_at=validated_at,
        catalog_hash=catalog_hash,
        parent_hint_mapping_hash=parent_hint_mapping_hash,
        qualified_snapshot=qualified_snapshot,
        input_market_state_hash=input_market_state_hash,
        output_market_state_hash=output_market_state_hash,
    )
    _write_text_atomic(
        output_directory / "same-session-validation.json",
        json.dumps(
            json.loads(canonical_json(payload)),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return payload["validation_hash"]


def _success_operations(
    *,
    status: str,
    context: SectorRadarProducerContext,
    completed_at: datetime,
    resolution: SectorRadarPersistenceResolution,
    latest_completed_session: date,
    direct_next_session: date | None,
    preparation: SectorRadarDailyPreparation | None,
    output_bundle: SectorRadarPersistentBundle,
    result: SectorRadarDailyResult | None,
) -> SectorRadarProducerOperations:
    source_manifest = resolution.source_bundle_manifest
    if preparation is None:
        if status != PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT or result is not None:
            raise SectorRadarProducerError(
                "only same-session validation may omit prospective preparation"
            )
        state_update_status = STATE_UPDATE_ALREADY_CURRENT
        preparation_status = None
        preparation_hash = None
        candidate_count = 0
        membership_request_count = 0
    else:
        state_update_status = preparation.state_update_status
        preparation_status = preparation.acquisition_plan.status
        preparation_hash = preparation.preparation_hash
        candidate_count = preparation.acquisition_plan.candidate_count
        membership_request_count = (
            preparation.acquisition_plan.distinct_membership_request_count
        )

    operations = SectorRadarProducerOperations(
        schema_version=SECTOR_RADAR_PRODUCER_OPERATIONS_SCHEMA_VERSION,
        status=status,
        started_at=context.observed_at,
        completed_at=completed_at,
        repository=context.repository,
        workflow_path=context.workflow_path,
        run_id=context.run_id,
        run_attempt=context.run_attempt,
        commit_sha=context.commit_sha,
        input_source_kind=resolution.source_kind,
        input_bundle_manifest_hash=(
            None if source_manifest is None else source_manifest.manifest_hash
        ),
        bootstrap_manifest_hash=resolution.bootstrap_manifest_hash,
        input_market_state_hash=resolution.market_state.state_hash,
        input_event_ledger_hash=resolution.event_ledger.ledger_hash,
        latest_cached_session=resolution.market_state.sessions[-1],
        latest_completed_session=latest_completed_session,
        direct_next_session=direct_next_session,
        state_update_status=state_update_status,
        preparation_status=preparation_status,
        preparation_hash=preparation_hash,
        candidate_count=candidate_count,
        membership_request_count=membership_request_count,
        output_market_state_hash=output_bundle.market_state.state_hash,
        output_event_ledger_hash=output_bundle.event_ledger.ledger_hash,
        result_hash=None if result is None else result.result_hash,
        error_type=None,
        error_message=None,
        operations_hash="",
    )
    operations = _with_operations_hash(operations)
    _validate_operations(operations)
    return operations


def write_sector_radar_failure_operations(
    *,
    output_directory: Path,
    context: SectorRadarProducerContext,
    error: Exception,
    completed_at: datetime,
    resolution: SectorRadarPersistenceResolution | None = None,
    latest_completed_session: date | None = None,
    direct_next_session: date | None = None,
    preparation: SectorRadarDailyPreparation | None = None,
) -> SectorRadarProducerOperations:
    _aware(completed_at, field="failure completed_at")
    source_manifest = None if resolution is None else resolution.source_bundle_manifest
    message = " ".join(str(error).split())[:1000]
    operations = SectorRadarProducerOperations(
        schema_version=SECTOR_RADAR_PRODUCER_OPERATIONS_SCHEMA_VERSION,
        status=PRODUCER_STATUS_FAILED,
        started_at=context.observed_at,
        completed_at=completed_at,
        repository=context.repository,
        workflow_path=context.workflow_path,
        run_id=context.run_id,
        run_attempt=context.run_attempt,
        commit_sha=context.commit_sha,
        input_source_kind=None if resolution is None else resolution.source_kind,
        input_bundle_manifest_hash=(
            None if source_manifest is None else source_manifest.manifest_hash
        ),
        bootstrap_manifest_hash=(
            None if resolution is None else resolution.bootstrap_manifest_hash
        ),
        input_market_state_hash=(
            None if resolution is None else resolution.market_state.state_hash
        ),
        input_event_ledger_hash=(
            None if resolution is None else resolution.event_ledger.ledger_hash
        ),
        latest_cached_session=(
            None if resolution is None else resolution.market_state.sessions[-1]
        ),
        latest_completed_session=latest_completed_session,
        direct_next_session=direct_next_session,
        state_update_status=(
            None if preparation is None else preparation.state_update_status
        ),
        preparation_status=(
            None if preparation is None else preparation.acquisition_plan.status
        ),
        preparation_hash=(
            None if preparation is None else preparation.preparation_hash
        ),
        candidate_count=(
            None if preparation is None else preparation.acquisition_plan.candidate_count
        ),
        membership_request_count=(
            None
            if preparation is None
            else preparation.acquisition_plan.distinct_membership_request_count
        ),
        output_market_state_hash=None,
        output_event_ledger_hash=None,
        result_hash=None,
        error_type=type(error).__name__,
        error_message=message or "Sector Radar producer failed without a diagnostic",
        operations_hash="",
    )
    operations = _with_operations_hash(operations)
    _validate_operations(operations)
    write_sector_radar_operations(output_directory, operations)
    return operations


def run_sector_radar_producer(
    *,
    resolution: SectorRadarPersistenceResolution,
    parent_hints: SectorParentHintIndex,
    context: SectorRadarProducerContext,
    state_directory: Path,
    output_directory: Path,
    api_key: str | None,
    fetch_calendar: Callable[..., tuple[date, ...]] | None = None,
    fetch_catalog: Callable[..., Any] | None = None,
    fetch_snapshot: Callable[..., Any] | None = None,
    fetch_membership: Callable[..., Any] | None = None,
    fetch_all_market: Callable[..., Any] | None = None,
    now: _Now | None = None,
    sleep: Callable[[float], None] = time.sleep,
    membership_request_delay_seconds: float = (
        SECTOR_RADAR_MEMBERSHIP_REQUEST_DELAY_SECONDS
    ),
) -> SectorRadarProducerOutcome:
    """Run one independent live producer from a previously resolved state source."""

    _validate_context(context)
    if membership_request_delay_seconds < 0:
        raise SectorRadarProducerError(
            "membership request delay must be non-negative"
        )
    now = now or (lambda: datetime.now(timezone.utc))
    fetch_calendar = fetch_calendar or hithink_http.fetch_hithink_trading_calendar
    fetch_catalog = fetch_catalog or hithink_index_http.fetch_hithink_industry_catalog
    fetch_snapshot = (
        fetch_snapshot or hithink_index_http.fetch_hithink_qualified_index_snapshot_batch
    )
    fetch_membership = (
        fetch_membership or hithink_sector_breadth_http.fetch_hithink_sector_membership
    )
    fetch_all_market = (
        fetch_all_market or hithink_sector_breadth_http.fetch_hithink_all_market_snapshot
    )

    state = resolution.market_state
    cached_session = state.sessions[-1]
    sessions = _validated_calendar(
        fetch_calendar(
            observed_at=context.observed_at,
            api_key=api_key,
        ),
        cached_session=cached_session,
    )
    latest_completed = latest_completed_a_share_session(
        sessions,
        observed_at=context.observed_at,
    )
    if latest_completed < cached_session:
        raise SectorRadarProducerError(
            "latest completed A-share session precedes restored market state"
        )
    completed_after_cache = tuple(
        session
        for session in sessions
        if cached_session < session <= latest_completed
    )
    if len(completed_after_cache) > 1:
        raise SectorRadarProducerError(
            "restored Sector Radar state missed one or more completed sessions; "
            "ordinary production cannot bridge the gap"
        )

    direct_next: date | None = None
    if completed_after_cache:
        direct_next = _next_calendar_session(
            sessions,
            cached_session=cached_session,
        )
        if completed_after_cache != (direct_next,):
            raise SectorRadarProducerError(
                "completed-session sequence after restored state is not directly contiguous"
            )

    catalog = fetch_catalog(api_key=api_key)
    snapshot = fetch_snapshot(
        thscodes=tuple(item.thscode for item in state.series),
        benchmark_thscode=state.benchmark_thscode,
        observed_at=context.observed_at,
        api_key=api_key,
    )
    if snapshot.market_session != latest_completed:
        raise SectorRadarProducerError(
            "qualified index snapshot does not match the latest completed session"
        )

    bundle_created_at = (
        context.observed_at
        if resolution.source_bundle_manifest is None
        else resolution.source_bundle_manifest.created_at
    )
    previous_result_hash = (
        None
        if resolution.source_bundle_manifest is None
        else resolution.source_bundle_manifest.last_result_hash
    )

    if latest_completed == cached_session:
        validate_sector_parent_hint_catalog(
            hints=parent_hints,
            catalog=catalog,
        )
        state_update = append_qualified_sector_snapshot(
            state=state,
            catalog=catalog,
            snapshot=snapshot,
            observed_at=context.observed_at,
        )
        if state_update.status != STATE_UPDATE_ALREADY_CURRENT:
            raise SectorRadarProducerError(
                "same-session validation unexpectedly changed market state"
            )
        if state_update.state != state:
            raise SectorRadarProducerError(
                "same-session validation returned a changed market-state object"
            )

        completed_at = now()
        _aware(completed_at, field="producer completion clock")
        output_directory.mkdir(parents=True, exist_ok=True)
        write_sector_radar_same_session_validation(
            output_directory=output_directory,
            context=context,
            validated_at=completed_at,
            catalog_hash=catalog.catalog_hash,
            parent_hint_mapping_hash=parent_hints.mapping_hash,
            qualified_snapshot=snapshot,
            input_market_state_hash=state.state_hash,
            output_market_state_hash=state_update.state.state_hash,
        )
        bundle = write_sector_radar_persistent_bundle(
            state_directory,
            market_state=state,
            event_ledger=resolution.event_ledger,
            created_at=bundle_created_at,
            updated_at=completed_at,
            source_repository=context.repository,
            source_workflow=context.workflow_path,
            source_run_id=context.run_id,
            source_run_attempt=context.run_attempt,
            source_commit_sha=context.commit_sha,
            parent_hint_mapping_hash=parent_hints.mapping_hash,
            last_result_hash=previous_result_hash,
            last_operation_status=PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
        )
        operations = _success_operations(
            status=PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
            context=context,
            completed_at=completed_at,
            resolution=resolution,
            latest_completed_session=latest_completed,
            direct_next_session=None,
            preparation=None,
            output_bundle=bundle,
            result=None,
        )
        write_sector_radar_operations(output_directory, operations)
        return SectorRadarProducerOutcome(
            status=PRODUCER_STATUS_VALIDATED_ALREADY_CURRENT,
            operations=operations,
            persistent_bundle=bundle,
            preparation=None,
            result=None,
        )

    if direct_next is None or latest_completed != direct_next:
        raise SectorRadarProducerError(
            "latest completed session is not the direct next session after state"
        )

    preparation = prepare_sector_radar_daily_run(
        market_state=state,
        catalog=catalog,
        qualified_snapshot=snapshot,
        parent_hints=parent_hints,
        prepared_at=context.observed_at,
        next_completed_session_after_state=direct_next,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(
        output_directory / "preparation.json",
        serialize_sector_radar_daily_preparation(preparation),
    )
    _write_text_atomic(
        output_directory / "preparation.md",
        render_sector_radar_daily_preparation_markdown(preparation),
    )

    if preparation.state_update_status != STATE_UPDATE_APPENDED:
        raise SectorRadarProducerError(
            "new completed session did not append exactly once"
        )
    if preparation.acquisition_plan.status == PREPARATION_BUDGET_EXCEEDED:
        raise SectorRadarProducerError(
            "Sector Radar current-membership acquisition budget exceeded; "
            "no candidate was truncated and no new state may be published"
        )

    memberships = []
    constituent_points = ()
    if preparation.acquisition_plan.status == PREPARATION_READY:
        requests = preparation.acquisition_plan.membership_requests
        for index, membership_request in enumerate(requests):
            if index and membership_request_delay_seconds:
                sleep(membership_request_delay_seconds)
            memberships.append(
                fetch_membership(
                    sector_thscode=membership_request.thscode,
                    sector_name=membership_request.name,
                    api_key=api_key,
                )
            )
        all_market = fetch_all_market(
            market_session=preparation.market_session,
            api_key=api_key,
        )
        constituent_points = all_market.points
    elif preparation.acquisition_plan.status != PREPARATION_QUIET:
        raise SectorRadarProducerError(
            "Sector Radar preparation has an unsupported acquisition status"
        )

    produced_at = now()
    _aware(produced_at, field="Sector Radar result clock")
    result = finalize_sector_radar_daily_run(
        preparation=preparation,
        parent_hints=parent_hints,
        memberships=tuple(memberships),
        constituent_points=constituent_points,
        event_ledger=resolution.event_ledger,
        produced_at=produced_at,
    )
    _write_text_atomic(
        output_directory / "result.json",
        serialize_sector_radar_daily_result(result),
    )
    _write_text_atomic(
        output_directory / "summary.md",
        render_sector_radar_daily_summary(result),
    )
    status = (
        PRODUCER_STATUS_APPENDED_QUIET
        if preparation.acquisition_plan.status == PREPARATION_QUIET
        else PRODUCER_STATUS_APPENDED_WITH_CANDIDATES
    )
    bundle = write_sector_radar_persistent_bundle(
        state_directory,
        market_state=result.market_state,
        event_ledger=result.event_ledger,
        created_at=bundle_created_at,
        updated_at=produced_at,
        source_repository=context.repository,
        source_workflow=context.workflow_path,
        source_run_id=context.run_id,
        source_run_attempt=context.run_attempt,
        source_commit_sha=context.commit_sha,
        parent_hint_mapping_hash=parent_hints.mapping_hash,
        last_result_hash=result.result_hash,
        last_operation_status=status,
    )
    operations = _success_operations(
        status=status,
        context=context,
        completed_at=produced_at,
        resolution=resolution,
        latest_completed_session=latest_completed,
        direct_next_session=direct_next,
        preparation=preparation,
        output_bundle=bundle,
        result=result,
    )
    write_sector_radar_operations(output_directory, operations)
    return SectorRadarProducerOutcome(
        status=status,
        operations=operations,
        persistent_bundle=bundle,
        preparation=preparation,
        result=result,
    )


def _parse_bool(value: str, *, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise SectorRadarProducerError(f"{field} must be true or false")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_kernel.runtime.sector_radar_producer",
        description="Run or restore the independent Sector Radar shadow producer.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover = subparsers.add_parser(
        "discover-artifact",
        help="Locate the latest successful workflow state artifact.",
    )
    discover.add_argument("--repository", required=True)
    discover.add_argument("--workflow-file", default=SECTOR_RADAR_WORKFLOW_FILE)
    discover.add_argument("--current-run-id", type=int, required=True)
    discover.add_argument("--github-output", type=Path, required=True)

    run = subparsers.add_parser(
        "run",
        help="Run one fail-closed live Sector Radar shadow composition.",
    )
    run.add_argument("--repository", required=True)
    run.add_argument("--workflow-path", default=SECTOR_RADAR_WORKFLOW_PATH)
    run.add_argument("--run-id", type=int, required=True)
    run.add_argument("--run-attempt", type=int, required=True)
    run.add_argument("--commit-sha", required=True)
    run.add_argument("--prior-success-found", required=True)
    run.add_argument("--artifact-available", required=True)
    run.add_argument(
        "--state-directory",
        type=Path,
        default=SECTOR_RADAR_DEFAULT_STATE_DIRECTORY,
    )
    run.add_argument(
        "--artifact-directory",
        type=Path,
        default=SECTOR_RADAR_DEFAULT_ARTIFACT_DIRECTORY,
    )
    run.add_argument(
        "--output-directory",
        type=Path,
        default=SECTOR_RADAR_DEFAULT_OUTPUT_DIRECTORY,
    )
    run.add_argument(
        "--bootstrap",
        type=Path,
        default=SECTOR_RADAR_BOOTSTRAP_PATH,
    )
    run.add_argument(
        "--bootstrap-manifest",
        type=Path,
        default=SECTOR_RADAR_BOOTSTRAP_MANIFEST_PATH,
    )
    run.add_argument(
        "--parent-hints",
        type=Path,
        default=SECTOR_RADAR_PARENT_HINTS_PATH,
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    if args.command == "discover-artifact":
        try:
            discovery = discover_previous_sector_radar_artifact(
                repository=args.repository,
                workflow_file=args.workflow_file,
                current_run_id=args.current_run_id,
                token=os.environ.get("GITHUB_TOKEN"),
            )
            write_github_output(args.github_output, discovery)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"ERROR: {exc}", file=stderr)
            return 2
        print(
            "SECTOR RADAR STATE DISCOVERY: "
            f"prior_success={discovery.prior_success_found} | "
            f"artifact_available={discovery.artifact_available} | "
            f"run_id={discovery.prior_run_id}",
            file=stdout,
        )
        return 0

    observed_at = datetime.now(timezone.utc)
    context = SectorRadarProducerContext(
        repository=args.repository,
        workflow_path=args.workflow_path,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        commit_sha=args.commit_sha,
        observed_at=observed_at,
    )
    output_directory = args.output_directory
    resolution = None
    preparation = None
    latest_completed = None
    direct_next = None
    try:
        _validate_context(context)
        parent_hints = load_sector_parent_hints(args.parent_hints)
        resolution = resolve_sector_radar_persistence(
            cache_directory=args.state_directory,
            artifact_directory=(
                args.artifact_directory
                if _parse_bool(
                    args.artifact_available,
                    field="artifact_available",
                )
                else None
            ),
            prior_success_found=_parse_bool(
                args.prior_success_found,
                field="prior_success_found",
            ),
            artifact_available=_parse_bool(
                args.artifact_available,
                field="artifact_available",
            ),
            bootstrap_path=args.bootstrap,
            bootstrap_manifest_path=args.bootstrap_manifest,
            observed_at=observed_at,
            expected_repository=context.repository,
            expected_workflow=context.workflow_path,
            expected_parent_hint_mapping_hash=parent_hints.mapping_hash,
        )
        outcome = run_sector_radar_producer(
            resolution=resolution,
            parent_hints=parent_hints,
            context=context,
            state_directory=args.state_directory,
            output_directory=output_directory,
            api_key=os.environ.get(hithink_http.HITHINK_API_KEY_ENV),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        completed_at = datetime.now(timezone.utc)
        write_sector_radar_failure_operations(
            output_directory=output_directory,
            context=context,
            error=exc,
            completed_at=completed_at,
            resolution=resolution,
            latest_completed_session=latest_completed,
            direct_next_session=direct_next,
            preparation=preparation,
        )
        print(f"ERROR: {exc}", file=stderr)
        return 2

    print(
        "SECTOR RADAR SHADOW PRODUCER: "
        f"{outcome.status} | "
        f"session={outcome.persistent_bundle.manifest.market_session} | "
        f"state={outcome.persistent_bundle.market_state.state_hash} | "
        f"events={len(outcome.persistent_bundle.event_ledger.events)}",
        file=stdout,
    )
    print("SHADOW OBSERVATION ONLY", file=stdout)
    print("HUMAN ATTENTION AUTHORITY: NONE", file=stdout)
    print("INVESTMENT AUTHORITY: NONE", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
