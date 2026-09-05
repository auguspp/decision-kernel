from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json

from . import hithink_http, hithink_index_http, hithink_sector_breadth_http
from .sector_parent_hints import parse_sector_parent_hints
from .sector_radar_events import (
    parse_sector_radar_candidate_event_ledger,
    serialize_sector_radar_candidate_event_ledger,
)
from .sector_radar_persistence import (
    SectorRadarPersistenceResolution,
    parse_sector_radar_persistent_manifest,
    serialize_sector_radar_persistent_manifest,
    write_sector_radar_persistent_bundle,
)
from .sector_radar_shadow import (
    SECTOR_RADAR_SHADOW_POLICY_VERSION,
    _acceleration_gate,
    _persistent_gate,
)
from .sector_radar_state import (
    parse_sector_radar_market_state,
    serialize_sector_radar_market_state,
)


AUDIT_SCHEMA_VERSION = 1
AUDIT_SEMANTICS = "DECODED_PROVIDER_JSON_AND_EXACT_INPUT_STATE_FOR_OFFLINE_REPLAY"
REPLAY_SEMANTICS = "OFFLINE_VERIFICATION_ONLY_NOT_A_PROSPECTIVE_EVENT_OR_RECOVERY"
LIVE_PROVENANCE = "LIVE_HITHINK"
SYNTHETIC_PROVENANCE = "SYNTHETIC_TEST_ONLY"
MAX_REQUESTS = 128
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_AUDIT_BYTES = 64 * 1024 * 1024
AUTHORITY = {
    "signal_transition_authority": "NONE",
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
}

_ROUTES = {
    hithink_http.HITHINK_CALENDAR_PATH: frozenset(),
    hithink_index_http.HITHINK_INDEX_CATALOG_PATH: frozenset({"tag"}),
    hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH: frozenset({"thscodes"}),
    hithink_index_http.HITHINK_INDEX_HISTORY_PATH: frozenset(
        {"thscode", "interval", "start", "end"}
    ),
    hithink_sector_breadth_http.HITHINK_SECTOR_CONSTITUENTS_PATH: frozenset({"thscode"}),
    hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH: frozenset({"limit", "offset"}),
}
_OUTPUT_FILES = (
    "operations.json", "operations.md", "same-session-validation.json",
    "observations.json", "preparation.json", "preparation.md", "result.json", "summary.md",
)
_STATE_FILES = ("market-state.json", "candidate-events.json", "manifest.json")
_INPUT_FILES = ("market-state.json", "candidate-events.json", "parent-hints.json", "context.json", "resolution.json")
_SOURCE_FILES = (
    "identity.py", "adapters/hithink.py", "adapters/hithink_index.py",
    "runtime/hithink_http.py", "runtime/hithink_index_http.py",
    "runtime/hithink_sector_breadth_http.py", "runtime/sector_parent_hints.py",
    "runtime/sector_radar.py", "runtime/sector_breadth.py",
    "runtime/sector_radar_shadow.py", "runtime/sector_radar_state.py",
    "runtime/sector_radar_events.py", "runtime/sector_radar_daily.py",
    "runtime/sector_radar_persistence.py", "runtime/sector_radar_producer.py",
    "runtime/sector_radar_audit.py",
)
_SENSITIVE_KEY = re.compile(r"(?:api.?key|token|authorization|cookie|password|secret)", re.I)
_HASH = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_FIELDS = {
    "schema_version", "audit_semantics", "provenance", "implementation",
    "files", "requests", "run_clocks", "status", "error_type", "authority", "audit_hash",
}
_Request = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class SectorRadarAuditError(RuntimeError):
    """Audit or replay cannot prove complete, matching inputs and outputs."""


class _RecordedRequestFailure(RuntimeError):
    def __init__(self, original_type: str):
        super().__init__("Recorded transport failure; no network retry is permitted")
        self.original_type = original_type


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    # Provider envelopes can contain JSON floats. Preserve decoded JSON semantics;
    # do not pass these envelopes through the domain canonical Decimal encoder.
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _domain_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def _clock(value: Any) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError) as exc:
        raise SectorRadarAuditError("audit clock is not an ISO datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SectorRadarAuditError("audit clock must be timezone-aware")
    return parsed


def _implementation() -> dict[str, str]:
    package = Path(__file__).resolve().parents[1]
    return {name: _sha((package / name).read_bytes()) for name in _SOURCE_FILES}


def _check_safe_json(value: Any, credential: str | None = None, *, depth: int = 0) -> None:
    if depth > 32:
        raise SectorRadarAuditError("audit JSON nesting exceeds the safety limit")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or _SENSITIVE_KEY.search(key):
                raise SectorRadarAuditError("credential-like JSON fields cannot enter the input audit")
            _check_safe_json(item, credential, depth=depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _check_safe_json(item, credential, depth=depth + 1)
    elif isinstance(value, str) and credential and credential in value:
        raise SectorRadarAuditError("credential material cannot enter the input audit")


def _check_request(path: str, params: Mapping[str, str]) -> dict[str, str]:
    if path not in _ROUTES or set(params) != _ROUTES[path]:
        raise SectorRadarAuditError("request is outside the exact audited endpoint contract")
    if any(not isinstance(value, str) or len(value) > 16384 for value in params.values()):
        raise SectorRadarAuditError("audited request parameters are invalid")
    _check_safe_json(params)
    return dict(params)


def _allowed_file(name: str) -> bool:
    return (
        name in {f"inputs/{item}" for item in _INPUT_FILES}
        or name in {f"expected/state/{item}" for item in _STATE_FILES}
        or name in {f"expected/output/{item}" for item in _OUTPUT_FILES}
        or re.fullmatch(r"responses/[0-9]{4}\.json", name) is not None
    )


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


class _Recorder:
    def __init__(self, root: Path, *, provenance: str, credential: str | None, capture_now: Callable[[], datetime]):
        if root.is_symlink() or (root.exists() and any(root.iterdir())):
            raise SectorRadarAuditError("input audit requires a new empty directory")
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.credential = credential
        self.capture_now = capture_now
        self.manifest: dict[str, Any] = {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "audit_semantics": AUDIT_SEMANTICS,
            "provenance": provenance,
            "implementation": _implementation(),
            "files": {}, "requests": [], "run_clocks": [],
            "status": "RECORDING", "error_type": None, "authority": dict(AUTHORITY),
        }
        self.flush()

    def flush(self) -> None:
        payload = {**self.manifest, "audit_hash": canonical_hash(self.manifest)}
        _atomic_bytes(self.root / "manifest.json", _domain_bytes(payload))

    def add(self, name: str, data: bytes) -> None:
        if not _allowed_file(name) or name in self.manifest["files"]:
            raise SectorRadarAuditError("invalid or repeated audit file identity")
        if len(data) > MAX_FILE_BYTES:
            raise SectorRadarAuditError("input audit file exceeds the operations byte budget")
        total = sum(item["bytes"] for item in self.manifest["files"].values())
        if total + len(data) > MAX_AUDIT_BYTES:
            raise SectorRadarAuditError("input audit exceeds the operations byte budget")
        # Reject, rather than silently modifying, a credential-bearing response.
        if self.credential and self.credential.encode("utf-8") in data:
            raise SectorRadarAuditError("credential material cannot enter the input audit")
        _atomic_bytes(self.root / name, data)
        self.manifest["files"][name] = {"bytes": len(data), "sha256": _sha(data)}
        self.flush()

    def request(self, transport: _Request) -> _Request:
        def request_json(path: str, params: Mapping[str, str]) -> Mapping[str, Any]:
            parameters = _check_request(path, params)
            _check_safe_json(parameters, self.credential)
            index = len(self.manifest["requests"])
            if index >= MAX_REQUESTS:
                raise SectorRadarAuditError("input audit exceeds the operations request budget")
            record = {
                "path": path, "params": parameters,
                "captured_at": None, "response_file": None, "error_type": None,
            }
            try:
                envelope = transport(path, parameters)
            except (OSError, ValueError, RuntimeError) as exc:
                record["captured_at"] = _clock(self.capture_now()).isoformat()
                record["error_type"] = type(exc).__name__
                self.manifest["requests"].append(record)
                self.flush()
                raise
            if not isinstance(envelope, Mapping):
                raise SectorRadarAuditError("provider JSON envelope must be an object")
            _check_safe_json(envelope, self.credential)
            data = _json_bytes(envelope)
            record["captured_at"] = _clock(self.capture_now()).isoformat()
            record["response_file"] = f"responses/{index:04d}.json"
            self.add(record["response_file"], data)
            self.manifest["requests"].append(record)
            self.flush()
            # Use exactly the decoded JSON representation retained for replay.
            return json.loads(data)
        return request_json

    def run_clock(self, now: Callable[[], datetime]) -> Callable[[], datetime]:
        def recorded_now() -> datetime:
            value = _clock(now())
            self.manifest["run_clocks"].append(value.isoformat())
            self.flush()
            return value
        return recorded_now


def _fetchers(request: _Request) -> dict[str, Callable[..., Any]]:
    calendar: tuple | None = None

    def fetch_calendar(**kwargs):
        nonlocal calendar
        calendar = hithink_http.fetch_hithink_trading_calendar(request_json=request, **kwargs)
        return calendar

    def fetch_snapshot(**kwargs):
        if calendar is None:
            raise SectorRadarAuditError("snapshot requested before the exact calendar")
        return hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
            request_json=request, trading_sessions=calendar, **kwargs,
        )

    return {
        "fetch_calendar": fetch_calendar,
        "fetch_catalog": lambda **kwargs: hithink_index_http.fetch_hithink_industry_catalog(request_json=request, **kwargs),
        "fetch_snapshot": fetch_snapshot,
        "fetch_membership": lambda **kwargs: hithink_sector_breadth_http.fetch_hithink_sector_membership(request_json=request, **kwargs),
        "fetch_all_market": lambda **kwargs: hithink_sector_breadth_http.fetch_hithink_all_market_snapshot(request_json=request, **kwargs),
    }


def write_daily_observation_audit(preparation: Any, output_directory: Path) -> None:
    """Retain both full homogeneous universes and the existing gate decisions.

    Gate predicates are reused, not reimplemented or granted new authority. The
    ledger is neither an input nor an alternative trigger-state source.
    """
    pair = preparation.snapshot_pair
    decisions = []
    for family, previous, current, entries in (
        ("BROAD_881", pair.broad_previous, pair.broad_current, preparation.broad_entries),
        ("GRANULAR_884", pair.granular_previous, pair.granular_current, preparation.granular_entries),
    ):
        prior = {row.thscode: row for row in previous.observations}
        selected = {row.thscode: row.event_type for row in entries.candidates}
        for row in sorted(current.observations, key=lambda item: item.thscode):
            gates = {}
            for name, predicate in (("persistent", _persistent_gate), ("acceleration", _acceleration_gate)):
                before, after = predicate(prior[row.thscode]), predicate(row)
                gates[name] = {
                    "previous": before, "current": after,
                    "disposition": "ENTERED" if after and not before else (
                        "UNCHANGED_ACTIVE" if after else "INACTIVE_OR_EXITED"
                    ),
                }
            decisions.append({
                "family": family, "thscode": row.thscode,
                "gates": gates, "selected_event_type": selected.get(row.thscode),
            })
    payload = {
        "schema_version": 1, "policy_version": SECTOR_RADAR_SHADOW_POLICY_VERSION,
        "snapshot_pair": asdict(pair), "decisions": decisions,
        "semantics": "COMPLETE_SEPARATE_UNIVERSE_OBSERVATIONS_AND_SELECTION_AUDIT_ONLY",
        **AUTHORITY,
    }
    payload["observation_audit_hash"] = canonical_hash(payload)
    _atomic_bytes(output_directory / "observations.json", _domain_bytes(payload))


def _save_inputs(recorder: _Recorder, resolution: SectorRadarPersistenceResolution, parent_hints_json: str, context: Any) -> None:
    hints = parse_sector_parent_hints(parent_hints_json)
    recorder.add("inputs/market-state.json", serialize_sector_radar_market_state(resolution.market_state).encode("utf-8"))
    recorder.add("inputs/candidate-events.json", serialize_sector_radar_candidate_event_ledger(resolution.event_ledger).encode("utf-8"))
    recorder.add("inputs/parent-hints.json", parent_hints_json.encode("utf-8"))
    recorder.add("inputs/context.json", _domain_bytes(asdict(context)))
    source_manifest = resolution.source_bundle_manifest
    recorder.add("inputs/resolution.json", _domain_bytes({
        "source_kind": resolution.source_kind,
        "source_bundle_manifest": None if source_manifest is None else json.loads(serialize_sector_radar_persistent_manifest(source_manifest)),
        "bootstrap_manifest_hash": resolution.bootstrap_manifest_hash,
        "parent_hint_mapping_hash": hints.mapping_hash,
    }))


def _output_files(state_directory: Path, output_directory: Path) -> dict[str, bytes]:
    files = {}
    for category, directory, names in (
        ("state", state_directory, _STATE_FILES), ("output", output_directory, _OUTPUT_FILES),
    ):
        for name in names:
            path = directory / name
            if path.is_file():
                files[f"expected/{category}/{name}"] = path.read_bytes()
    return files


def _publish_bundle(bundle: Any, directory: Path) -> None:
    manifest = bundle.manifest
    write_sector_radar_persistent_bundle(
        directory, market_state=bundle.market_state, event_ledger=bundle.event_ledger,
        created_at=manifest.created_at, updated_at=manifest.updated_at,
        source_repository=manifest.source_repository, source_workflow=manifest.source_workflow,
        source_run_id=manifest.source_run_id, source_run_attempt=manifest.source_run_attempt,
        source_commit_sha=manifest.source_commit_sha,
        parent_hint_mapping_hash=manifest.parent_hint_mapping_hash,
        last_result_hash=manifest.last_result_hash,
        last_operation_status=manifest.last_operation_status,
    )


def run_audited_sector_radar_producer(
    *, resolution: SectorRadarPersistenceResolution, parent_hints: Any,
    parent_hints_json: str, context: Any, state_directory: Path,
    output_directory: Path, api_key: str | None,
    request_json: _Request | None = None,
    provenance: str = LIVE_PROVENANCE,
    now: Callable[[], datetime] | None = None,
    capture_now: Callable[[], datetime] | None = None,
) -> Any:
    """Stage a complete producer run; seal its audit before publishing live state.

    Injected transports must be explicitly synthetic. Their calculated state is
    retained only inside the labelled audit, never published to state_directory.
    No fixture, replay, or audit can become ordinary restoration authority.
    """
    from .sector_radar_producer import run_sector_radar_producer

    if provenance not in {LIVE_PROVENANCE, SYNTHETIC_PROVENANCE}:
        raise SectorRadarAuditError("unsupported audit provenance")
    if request_json is not None and provenance != SYNTHETIC_PROVENANCE:
        raise SectorRadarAuditError("injected transport requires SYNTHETIC_TEST_ONLY provenance")
    if provenance == SYNTHETIC_PROVENANCE and request_json is None:
        raise SectorRadarAuditError("synthetic audit cannot contact a live provider")
    if parse_sector_parent_hints(parent_hints_json) != parent_hints:
        raise SectorRadarAuditError("audit parent hints disagree with producer input")
    if output_directory.is_symlink() or (output_directory.exists() and any(output_directory.iterdir())):
        raise SectorRadarAuditError("audited run requires a new empty output directory")
    target = state_directory.resolve()
    output = output_directory.resolve()
    if target == output or target in output.parents or output in target.parents:
        raise SectorRadarAuditError("audit and live state directories must not overlap")
    now = now or (lambda: datetime.now(timezone.utc))
    capture_now = capture_now or (lambda: datetime.now(timezone.utc))
    transport = request_json
    if transport is None:
        if not api_key:
            raise SectorRadarAuditError("HiThink credentials are required for live audited input")
        transport = lambda path, params: hithink_http._request_hithink_json(
            api_key=api_key, path=path, params=params, timeout_seconds=10.0,
        )
    recorder = _Recorder(output_directory / "input-audit", provenance=provenance, credential=api_key, capture_now=capture_now)
    _save_inputs(recorder, resolution, parent_hints_json, context)
    with tempfile.TemporaryDirectory(prefix="sector-radar-audit-stage-") as temporary:
        staged_state = Path(temporary) / "state"
        try:
            outcome = run_sector_radar_producer(
                resolution=resolution, parent_hints=parent_hints, context=context,
                state_directory=staged_state, output_directory=output_directory,
                api_key=api_key, now=recorder.run_clock(now),
                membership_request_delay_seconds=0.25 if provenance == LIVE_PROVENANCE else 0.0,
                **_fetchers(recorder.request(transport)),
            )
        except (OSError, ValueError, RuntimeError) as exc:
            for name, data in _output_files(staged_state, output_directory).items():
                recorder.add(name, data)
            recorder.manifest.update(status="REJECTED", error_type=type(exc).__name__)
            recorder.flush()
            # The outer CLI may render this error; never propagate credentials.
            message = str(exc).replace(api_key, "[REDACTED]") if api_key else str(exc)
            raise SectorRadarAuditError(f"Audited producer rejected input ({type(exc).__name__}): {message[:1000]}") from None
        for name, data in _output_files(staged_state, output_directory).items():
            recorder.add(name, data)
        recorder.manifest.update(status="SUCCEEDED", error_type=None)
        recorder.flush()
        # Read back every retained byte before an ordinary state publication.
        validate_sector_radar_input_audit(recorder.root)
        if provenance == LIVE_PROVENANCE:
            _publish_bundle(outcome.persistent_bundle, state_directory)
        return outcome


def validate_sector_radar_input_audit(root: Path) -> dict[str, Any]:
    """Validate exact inventory, hashes, schema and code before any replay."""
    if root.is_symlink() or not root.is_dir():
        raise SectorRadarAuditError("audit root must be a real directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > MAX_FILE_BYTES:
        raise SectorRadarAuditError("audit manifest is invalid")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise SectorRadarAuditError("audit manifest fields disagree")
    payload = dict(manifest)
    digest = payload.pop("audit_hash")
    if digest != canonical_hash(payload):
        raise SectorRadarAuditError("audit manifest hash mismatch")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != AUDIT_SCHEMA_VERSION:
        raise SectorRadarAuditError("unsupported audit schema")
    if manifest["audit_semantics"] != AUDIT_SEMANTICS or manifest["authority"] != AUTHORITY:
        raise SectorRadarAuditError("audit semantics or authority disagrees")
    if manifest["provenance"] not in {LIVE_PROVENANCE, SYNTHETIC_PROVENANCE}:
        raise SectorRadarAuditError("audit provenance is invalid")
    if manifest["status"] not in {"SUCCEEDED", "REJECTED"}:
        raise SectorRadarAuditError("input audit is incomplete")
    if manifest["implementation"] != _implementation():
        raise SectorRadarAuditError("replay requires the exact recorded implementation files")
    files = manifest["files"]
    if not isinstance(files, dict) or len(files) > MAX_REQUESTS + 32:
        raise SectorRadarAuditError("audit file inventory is invalid")
    if not {f"inputs/{name}" for name in _INPUT_FILES} <= set(files):
        raise SectorRadarAuditError("audit is missing its exact input state")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SectorRadarAuditError("audit symlinks are prohibited")
        if path.is_file() and path != manifest_path:
            actual.add(path.relative_to(root).as_posix())
    if actual != set(files):
        raise SectorRadarAuditError("audit file inventory mismatch")
    total = 0
    for name, descriptor in files.items():
        if not _allowed_file(name) or set(descriptor) != {"bytes", "sha256"}:
            raise SectorRadarAuditError("audit file descriptor is invalid")
        size = descriptor["bytes"]
        if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES or not _HASH.fullmatch(descriptor["sha256"]):
            raise SectorRadarAuditError("audit file descriptor exceeds limits")
        path = root / name
        if path.stat().st_size != size:
            raise SectorRadarAuditError("audit file byte size mismatch")
        total += size
        if total > MAX_AUDIT_BYTES:
            raise SectorRadarAuditError("audit total byte limit exceeded")
        if _sha(path.read_bytes()) != descriptor["sha256"]:
            raise SectorRadarAuditError("audit file hash mismatch")
    requests = manifest["requests"]
    if not isinstance(requests, list) or len(requests) > MAX_REQUESTS:
        raise SectorRadarAuditError("audit request transcript is invalid")
    referenced = set()
    for index, record in enumerate(requests):
        if set(record) != {"path", "params", "captured_at", "response_file", "error_type"}:
            raise SectorRadarAuditError("audit request fields disagree")
        _check_request(record["path"], record["params"])
        _clock(record["captured_at"])
        if record["error_type"] is None:
            expected = f"responses/{index:04d}.json"
            if record["response_file"] != expected or expected not in files:
                raise SectorRadarAuditError("audit response identity is missing or reordered")
            referenced.add(expected)
        elif record["response_file"] is not None or not isinstance(record["error_type"], str):
            raise SectorRadarAuditError("recorded transport failure is malformed")
    if referenced != {name for name in files if name.startswith("responses/")}:
        raise SectorRadarAuditError("unreferenced response in audit")
    if not isinstance(manifest["run_clocks"], list) or len(manifest["run_clocks"]) > 16:
        raise SectorRadarAuditError("audit run clocks are invalid")
    for value in manifest["run_clocks"]:
        _clock(value)
    return manifest


def replay_sector_radar_input_audit(root: Path) -> dict[str, Any]:
    """Re-run qualification and composition using only sealed local inputs.

    There is no URL fetch, caller-supplied output path, cache save, workflow dispatch
    or production-ledger write. All regenerated artifacts live in a disposable
    temporary directory and are compared byte-for-byte with the recorded outputs.
    """
    from .sector_radar_producer import SectorRadarProducerContext, run_sector_radar_producer

    manifest = validate_sector_radar_input_audit(root)
    def read(name: str) -> str:
        return (root / name).read_text(encoding="utf-8")
    raw_context = json.loads(read("inputs/context.json"))
    raw_context["observed_at"] = _clock(raw_context["observed_at"])
    context = SectorRadarProducerContext(**raw_context)
    hints = parse_sector_parent_hints(read("inputs/parent-hints.json"))
    source = json.loads(read("inputs/resolution.json"))
    raw_manifest = source["source_bundle_manifest"]
    source_manifest = None if raw_manifest is None else parse_sector_radar_persistent_manifest(json.dumps(raw_manifest))
    resolution = SectorRadarPersistenceResolution(
        source_kind=source["source_kind"],
        market_state=parse_sector_radar_market_state(read("inputs/market-state.json")),
        event_ledger=parse_sector_radar_candidate_event_ledger(read("inputs/candidate-events.json")),
        source_bundle_manifest=source_manifest,
        bootstrap_manifest_hash=source["bootstrap_manifest_hash"],
    )
    if hints.mapping_hash != source["parent_hint_mapping_hash"]:
        raise SectorRadarAuditError("replay hint identity mismatch")
    request_index = 0
    clock_index = 0

    def request(path: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        nonlocal request_index
        if request_index >= len(manifest["requests"]):
            raise SectorRadarAuditError("replay requested an unrecorded input; no network fallback")
        record = manifest["requests"][request_index]
        if path != record["path"] or dict(params) != record["params"]:
            raise SectorRadarAuditError("replay request order or parameters disagree")
        request_index += 1
        if record["error_type"] is not None:
            raise _RecordedRequestFailure(record["error_type"])
        return json.loads(read(record["response_file"]))

    def now() -> datetime:
        nonlocal clock_index
        if clock_index >= len(manifest["run_clocks"]):
            raise SectorRadarAuditError("replay requested an unrecorded run clock")
        value = _clock(manifest["run_clocks"][clock_index])
        clock_index += 1
        return value

    with tempfile.TemporaryDirectory(prefix="sector-radar-offline-replay-") as temporary:
        state_dir, output_dir = Path(temporary) / "state", Path(temporary) / "output"
        error_type = None
        try:
            run_sector_radar_producer(
                resolution=resolution, parent_hints=hints, context=context,
                state_directory=state_dir, output_directory=output_dir,
                api_key="OFFLINE_REPLAY_NO_CREDENTIAL", now=now,
                membership_request_delay_seconds=0.0, **_fetchers(request),
            )
        except _RecordedRequestFailure as exc:
            error_type = exc.original_type
        except SectorRadarAuditError:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            error_type = type(exc).__name__
        status = "SUCCEEDED" if error_type is None else "REJECTED"
        if status != manifest["status"] or error_type != manifest["error_type"]:
            raise SectorRadarAuditError("replayed producer disposition does not match the recorded run")
        if request_index != len(manifest["requests"]) or clock_index != len(manifest["run_clocks"]):
            raise SectorRadarAuditError("replay left unused input records or clocks")
        actual = _output_files(state_dir, output_dir)
        expected = {name for name in manifest["files"] if name.startswith("expected/")}
        if set(actual) != expected:
            raise SectorRadarAuditError("replayed output inventory mismatch")
        for name, data in actual.items():
            if data != (root / name).read_bytes():
                raise SectorRadarAuditError(f"replayed output differs: {name}")
    report = {
        "schema_version": 1, "status": "MATCHED_" + status,
        "audit_hash": manifest["audit_hash"], "provenance": manifest["provenance"],
        "replay_semantics": REPLAY_SEMANTICS, "requests_replayed": request_index,
        "network_calls": 0, "production_state_writes": 0, **AUTHORITY,
    }
    report["report_hash"] = canonical_hash(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a sealed Sector Radar input audit without network or production-state writes.")
    parser.add_argument("audit_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        report = replay_sector_radar_input_audit(args.audit_directory)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"OFFLINE REPLAY FAILED: {exc}")
        return 2
    print(canonical_json(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
