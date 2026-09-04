from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from decision_kernel.adapters.hithink_index import (
    HITHINK_INDEX_SNAPSHOT_QUALIFICATION,
    HithinkIndustryCatalog,
    HithinkQualifiedIndexSnapshotBatch,
)
from decision_kernel.identity import canonical_hash

from .sector_radar import (
    SECTOR_RADAR_FORMULA_VERSION,
    SECTOR_RADAR_MAX_WINDOW_SESSIONS,
    SectorPricePoint,
    SectorPriceSeries,
    SectorRadarSnapshot,
    calculate_sector_radar_snapshot,
)


SECTOR_RADAR_STATE_SCHEMA_VERSION = 1
SECTOR_RADAR_STATE_WINDOW_SESSIONS = SECTOR_RADAR_MAX_WINDOW_SESSIONS + 1
SECTOR_RADAR_STATE_SEMANTICS = "QUALIFIED_COMPLETED_SESSION_MARKET_STATE_ONLY"
SECTOR_RADAR_STATE_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_STATE_INVESTMENT_AUTHORITY = "NONE"

BENCHMARK_FAMILY = "BENCHMARK"
BROAD_881_FAMILY = "BROAD_881"
GRANULAR_884_FAMILY = "GRANULAR_884"
STATE_UPDATE_APPENDED = "APPENDED_NEW_COMPLETED_SESSION"
STATE_UPDATE_ALREADY_CURRENT = "ALREADY_CURRENT_IDEMPOTENT"

_BROAD_CODE = re.compile(r"^881\d{3}\.TI$")
_GRANULAR_CODE = re.compile(r"^884\d{3}\.TI$")
_INDEX_CODE = re.compile(r"^\d{6}\.(?:SH|SZ|TI)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")

_ROOT_FIELDS = {
    "schema_version",
    "formula_version",
    "created_at",
    "updated_at",
    "source",
    "source_lineage",
    "catalog_hash",
    "benchmark",
    "broad_identities",
    "granular_identities",
    "sessions",
    "series",
    "last_provider_timestamp_ms",
    "state_semantics",
    "human_attention_authority",
    "investment_authority",
    "state_hash",
}
_IDENTITY_FIELDS = {"thscode", "name"}
_SERIES_FIELDS = {"thscode", "name", "family", "closes", "turnovers"}
_LINEAGE_FIELDS = {
    "role",
    "workflow_run_id",
    "artifact_id",
    "artifact_digest",
    "result_hash",
}


@dataclass(frozen=True)
class SectorRadarStateSourceLineage:
    role: str
    workflow_run_id: int
    artifact_id: int
    artifact_digest: str
    result_hash: str | None


@dataclass(frozen=True)
class SectorRadarStateSeries:
    thscode: str
    name: str
    family: str
    closes: tuple[Decimal, ...]
    turnovers: tuple[Decimal, ...]


@dataclass(frozen=True)
class SectorRadarMarketState:
    """Content-hashed rolling state for completed-session Sector Radar replay.

    The state is a Harness market-observation cache. It carries no Research,
    recommendation, Human wake, Action, or investment authority.
    """

    schema_version: int
    formula_version: str
    created_at: datetime
    updated_at: datetime
    source: str
    source_lineage: tuple[SectorRadarStateSourceLineage, ...]
    catalog_hash: str
    benchmark_thscode: str
    benchmark_name: str
    broad_identities: tuple[tuple[str, str], ...]
    granular_identities: tuple[tuple[str, str], ...]
    sessions: tuple[date, ...]
    series: tuple[SectorRadarStateSeries, ...]
    last_provider_timestamp_ms: int | None
    state_hash: str
    state_semantics: str = SECTOR_RADAR_STATE_SEMANTICS
    human_attention_authority: str = (
        SECTOR_RADAR_STATE_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_STATE_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarStateUpdate:
    status: str
    previous_state_hash: str
    state: SectorRadarMarketState
    appended_session: date | None
    human_attention_authority: str = (
        SECTOR_RADAR_STATE_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_STATE_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarStateSnapshotPair:
    state_hash: str
    previous_session: date
    current_session: date
    broad_previous: SectorRadarSnapshot
    broad_current: SectorRadarSnapshot
    granular_previous: SectorRadarSnapshot
    granular_current: SectorRadarSnapshot
    human_attention_authority: str = (
        SECTOR_RADAR_STATE_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_STATE_INVESTMENT_AUTHORITY


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _require_non_empty(value: str, *, field: str) -> str:
    if not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


def _require_hash(value: str, *, field: str, prefixed: bool = False) -> str:
    pattern = _SHA256_PREFIXED if prefixed else _SHA256
    if not pattern.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 string")
    return value


def _require_positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _decimal_from_string(
    value: Any,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a valid decimal string") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    if positive and parsed <= 0:
        raise ValueError(f"{field} must be positive")
    if non_negative and parsed < 0:
        raise ValueError(f"{field} must be non-negative")
    return parsed


def _require_decimal(
    value: Decimal,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> None:
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{field} must be positive")
    if non_negative and value < 0:
        raise ValueError(f"{field} must be non-negative")


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
        raise ValueError(
            f"{label} fields disagree; missing={missing}; unknown={unknown}"
        )


def _identity_payload(identities: Sequence[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"thscode": thscode, "name": name}
        for thscode, name in identities
    ]


def _state_payload_without_hash(state: SectorRadarMarketState) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "formula_version": state.formula_version,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
        "source": state.source,
        "source_lineage": [
            {
                "role": item.role,
                "workflow_run_id": item.workflow_run_id,
                "artifact_id": item.artifact_id,
                "artifact_digest": item.artifact_digest,
                "result_hash": item.result_hash,
            }
            for item in state.source_lineage
        ],
        "catalog_hash": state.catalog_hash,
        "benchmark": {
            "thscode": state.benchmark_thscode,
            "name": state.benchmark_name,
        },
        "broad_identities": _identity_payload(state.broad_identities),
        "granular_identities": _identity_payload(state.granular_identities),
        "sessions": [session.isoformat() for session in state.sessions],
        "series": [
            {
                "thscode": item.thscode,
                "name": item.name,
                "family": item.family,
                "closes": [format(value, "f") for value in item.closes],
                "turnovers": [format(value, "f") for value in item.turnovers],
            }
            for item in state.series
        ],
        "last_provider_timestamp_ms": state.last_provider_timestamp_ms,
        "state_semantics": state.state_semantics,
        "human_attention_authority": state.human_attention_authority,
        "investment_authority": state.investment_authority,
    }


def _with_state_hash(state: SectorRadarMarketState) -> SectorRadarMarketState:
    return replace(state, state_hash=canonical_hash(_state_payload_without_hash(state)))


def _validate_lineage(item: SectorRadarStateSourceLineage) -> None:
    _require_non_empty(item.role, field="state source-lineage role")
    _require_positive_int(item.workflow_run_id, field="state workflow_run_id")
    _require_positive_int(item.artifact_id, field="state artifact_id")
    _require_hash(item.artifact_digest, field="state artifact_digest", prefixed=True)
    if item.result_hash is not None:
        _require_hash(item.result_hash, field="state source result_hash")


def _validate_state(
    state: SectorRadarMarketState,
    *,
    verify_hash: bool,
) -> None:
    if state.schema_version != SECTOR_RADAR_STATE_SCHEMA_VERSION:
        raise ValueError("unsupported Sector Radar state schema version")
    if state.formula_version != SECTOR_RADAR_FORMULA_VERSION:
        raise ValueError("Sector Radar state formula version is unsupported")
    _require_aware(state.created_at, field="state created_at")
    _require_aware(state.updated_at, field="state updated_at")
    if state.updated_at < state.created_at:
        raise ValueError("Sector Radar state updated_at precedes created_at")
    _require_non_empty(state.source, field="state source")
    if not state.source_lineage:
        raise ValueError("Sector Radar state requires source lineage")
    for item in state.source_lineage:
        _validate_lineage(item)
    _require_hash(state.catalog_hash, field="state catalog_hash")
    if not _INDEX_CODE.fullmatch(state.benchmark_thscode):
        raise ValueError("Sector Radar state benchmark identity is invalid")
    _require_non_empty(state.benchmark_name, field="state benchmark name")

    if not state.broad_identities or not state.granular_identities:
        raise ValueError("Sector Radar state requires broad and granular identities")
    if tuple(sorted(state.broad_identities)) != state.broad_identities:
        raise ValueError("Sector Radar state broad identities must be sorted")
    if tuple(sorted(state.granular_identities)) != state.granular_identities:
        raise ValueError("Sector Radar state granular identities must be sorted")
    if len({code for code, _ in state.broad_identities}) != len(
        state.broad_identities
    ):
        raise ValueError("Sector Radar state broad identities contain duplicates")
    if len({code for code, _ in state.granular_identities}) != len(
        state.granular_identities
    ):
        raise ValueError("Sector Radar state granular identities contain duplicates")
    for code, name in state.broad_identities:
        if not _BROAD_CODE.fullmatch(code) or not name.strip():
            raise ValueError("Sector Radar state contains an invalid broad identity")
    for code, name in state.granular_identities:
        if not _GRANULAR_CODE.fullmatch(code) or not name.strip():
            raise ValueError("Sector Radar state contains an invalid granular identity")

    if len(state.sessions) < 62:
        raise ValueError("Sector Radar state has insufficient history")
    if len(state.sessions) > SECTOR_RADAR_STATE_WINDOW_SESSIONS:
        raise ValueError("Sector Radar state exceeds its rolling window")
    if state.sessions != tuple(sorted(set(state.sessions))):
        raise ValueError("Sector Radar state sessions must be unique and ascending")

    expected_series_identity = (
        (state.benchmark_thscode, state.benchmark_name, BENCHMARK_FAMILY),
        *(
            (code, name, BROAD_881_FAMILY)
            for code, name in state.broad_identities
        ),
        *(
            (code, name, GRANULAR_884_FAMILY)
            for code, name in state.granular_identities
        ),
    )
    actual_series_identity = tuple(
        (item.thscode, item.name, item.family) for item in state.series
    )
    if actual_series_identity != expected_series_identity:
        raise ValueError("Sector Radar state series identities or order disagree")

    for item in state.series:
        if len(item.closes) != len(state.sessions) or len(item.turnovers) != len(
            state.sessions
        ):
            raise ValueError(
                f"Sector Radar state series length disagrees for {item.thscode}"
            )
        for value in item.closes:
            _require_decimal(
                value,
                field=f"Sector Radar state close for {item.thscode}",
                positive=True,
            )
        for value in item.turnovers:
            _require_decimal(
                value,
                field=f"Sector Radar state turnover for {item.thscode}",
                non_negative=True,
            )

    if state.last_provider_timestamp_ms is not None:
        _require_positive_int(
            state.last_provider_timestamp_ms,
            field="state last_provider_timestamp_ms",
        )
    if state.state_semantics != SECTOR_RADAR_STATE_SEMANTICS:
        raise ValueError("Sector Radar state semantics disagree")
    if state.human_attention_authority != "NONE":
        raise ValueError("Sector Radar state cannot carry Human attention authority")
    if state.investment_authority != "NONE":
        raise ValueError("Sector Radar state cannot carry investment authority")
    if verify_hash:
        _require_hash(state.state_hash, field="state_hash")
        if canonical_hash(_state_payload_without_hash(state)) != state.state_hash:
            raise ValueError("Sector Radar state hash mismatch")


def _catalog_identities(
    catalog: HithinkIndustryCatalog,
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    if catalog.unexpected_industries:
        raise ValueError("Sector Radar state catalog has unexpected industry families")
    broad = tuple(
        sorted((item.thscode, item.name) for item in catalog.broad_industries)
    )
    granular = tuple(
        sorted((item.thscode, item.name) for item in catalog.granular_industries)
    )
    if not broad or not granular:
        raise ValueError("Sector Radar state catalog is incomplete")
    return broad, granular


def _series_from_price_series(
    series: SectorPriceSeries,
    *,
    family: str,
    sessions: tuple[date, ...],
) -> SectorRadarStateSeries:
    by_session = {point.session: point for point in series.points}
    if len(by_session) != len(series.points):
        raise ValueError(f"bootstrap series contains duplicate sessions for {series.thscode}")
    missing = [session for session in sessions if session not in by_session]
    if missing:
        raise ValueError(
            f"bootstrap series lacks required sessions for {series.thscode}"
        )
    return SectorRadarStateSeries(
        thscode=series.thscode.strip().upper(),
        name=series.name.strip(),
        family=family,
        closes=tuple(by_session[session].close for session in sessions),
        turnovers=tuple(by_session[session].turnover for session in sessions),
    )


def create_sector_radar_market_state(
    *,
    catalog: HithinkIndustryCatalog,
    benchmark: SectorPriceSeries,
    broad_series: Sequence[SectorPriceSeries],
    granular_series: Sequence[SectorPriceSeries],
    created_at: datetime,
    source: str,
    source_lineage: Sequence[SectorRadarStateSourceLineage],
) -> SectorRadarMarketState:
    """Create one rolling state from fully qualified aligned history inputs."""

    _require_aware(created_at, field="state created_at")
    broad_identities, granular_identities = _catalog_identities(catalog)
    if tuple(sorted((item.thscode, item.name) for item in broad_series)) != (
        broad_identities
    ):
        raise ValueError("bootstrap broad histories disagree with the current catalog")
    if tuple(sorted((item.thscode, item.name) for item in granular_series)) != (
        granular_identities
    ):
        raise ValueError("bootstrap granular histories disagree with the current catalog")

    benchmark_sessions = tuple(point.session for point in benchmark.points)
    if benchmark_sessions != tuple(sorted(set(benchmark_sessions))):
        raise ValueError("bootstrap benchmark sessions must be unique and ascending")
    if len(benchmark_sessions) < SECTOR_RADAR_STATE_WINDOW_SESSIONS:
        raise ValueError("bootstrap benchmark has fewer than 127 completed sessions")
    sessions = benchmark_sessions[-SECTOR_RADAR_STATE_WINDOW_SESSIONS:]

    broad_by_code = {item.thscode: item for item in broad_series}
    granular_by_code = {item.thscode: item for item in granular_series}
    state_series = [
        _series_from_price_series(
            benchmark,
            family=BENCHMARK_FAMILY,
            sessions=sessions,
        )
    ]
    state_series.extend(
        _series_from_price_series(
            broad_by_code[code],
            family=BROAD_881_FAMILY,
            sessions=sessions,
        )
        for code, _ in broad_identities
    )
    state_series.extend(
        _series_from_price_series(
            granular_by_code[code],
            family=GRANULAR_884_FAMILY,
            sessions=sessions,
        )
        for code, _ in granular_identities
    )

    state = SectorRadarMarketState(
        schema_version=SECTOR_RADAR_STATE_SCHEMA_VERSION,
        formula_version=SECTOR_RADAR_FORMULA_VERSION,
        created_at=created_at,
        updated_at=created_at,
        source=_require_non_empty(source, field="state source"),
        source_lineage=tuple(source_lineage),
        catalog_hash=catalog.catalog_hash,
        benchmark_thscode=benchmark.thscode.strip().upper(),
        benchmark_name=benchmark.name.strip(),
        broad_identities=broad_identities,
        granular_identities=granular_identities,
        sessions=sessions,
        series=tuple(state_series),
        last_provider_timestamp_ms=None,
        state_hash="",
    )
    _validate_state(state, verify_hash=False)
    return _with_state_hash(state)


def serialize_sector_radar_market_state(state: SectorRadarMarketState) -> str:
    _validate_state(state, verify_hash=True)
    payload = _state_payload_without_hash(state)
    payload["state_hash"] = state.state_hash
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_sector_radar_market_state(
    path: Path,
    state: SectorRadarMarketState,
) -> None:
    """Atomically replace one explicit Harness-owned state file."""

    serialized = serialize_sector_radar_market_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 datetime") from exc
    _require_aware(parsed, field=field)
    return parsed


def _parse_identity_list(value: Any, *, family: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"state {family} identities must be a non-empty array")
    identities = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"state {family} identity {index} must be an object")
        _require_exact_fields(item, _IDENTITY_FIELDS, label=f"state {family} identity")
        code = _require_non_empty(
            item["thscode"],
            field=f"state {family} identity thscode",
        ).upper()
        name = _require_non_empty(
            item["name"],
            field=f"state {family} identity name",
        )
        identities.append((code, name))
    return tuple(identities)


def parse_sector_radar_market_state(raw_state: str) -> SectorRadarMarketState:
    """Parse one strict content-hashed Sector Radar state file."""

    try:
        raw = json.loads(raw_state)
    except json.JSONDecodeError as exc:
        raise ValueError("Sector Radar state must contain valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("Sector Radar state must be a JSON object")
    _require_exact_fields(raw, _ROOT_FIELDS, label="Sector Radar state")

    benchmark = raw["benchmark"]
    if not isinstance(benchmark, Mapping):
        raise ValueError("state benchmark must be a JSON object")
    _require_exact_fields(benchmark, _IDENTITY_FIELDS, label="state benchmark")

    raw_lineage = raw["source_lineage"]
    if not isinstance(raw_lineage, list) or not raw_lineage:
        raise ValueError("state source_lineage must be a non-empty array")
    lineage = []
    for index, item in enumerate(raw_lineage):
        if not isinstance(item, Mapping):
            raise ValueError(f"state source lineage {index} must be an object")
        _require_exact_fields(item, _LINEAGE_FIELDS, label="state source lineage")
        result_hash = item["result_hash"]
        if result_hash is not None:
            result_hash = _require_hash(
                result_hash,
                field="state source result_hash",
            )
        lineage.append(
            SectorRadarStateSourceLineage(
                role=_require_non_empty(item["role"], field="state source role"),
                workflow_run_id=_require_positive_int(
                    item["workflow_run_id"],
                    field="state workflow_run_id",
                ),
                artifact_id=_require_positive_int(
                    item["artifact_id"],
                    field="state artifact_id",
                ),
                artifact_digest=_require_hash(
                    item["artifact_digest"],
                    field="state artifact_digest",
                    prefixed=True,
                ),
                result_hash=result_hash,
            )
        )

    raw_sessions = raw["sessions"]
    if not isinstance(raw_sessions, list):
        raise ValueError("state sessions must be an array")
    sessions = []
    for index, item in enumerate(raw_sessions):
        if not isinstance(item, str):
            raise ValueError(f"state session {index} must be an ISO date string")
        try:
            sessions.append(date.fromisoformat(item))
        except ValueError as exc:
            raise ValueError(f"state session {index} is invalid") from exc

    raw_series = raw["series"]
    if not isinstance(raw_series, list):
        raise ValueError("state series must be an array")
    series = []
    for index, item in enumerate(raw_series):
        if not isinstance(item, Mapping):
            raise ValueError(f"state series {index} must be an object")
        _require_exact_fields(item, _SERIES_FIELDS, label=f"state series {index}")
        closes = item["closes"]
        turnovers = item["turnovers"]
        if not isinstance(closes, list) or not isinstance(turnovers, list):
            raise ValueError(f"state series {index} values must be arrays")
        series.append(
            SectorRadarStateSeries(
                thscode=_require_non_empty(
                    item["thscode"],
                    field=f"state series {index} thscode",
                ).upper(),
                name=_require_non_empty(
                    item["name"],
                    field=f"state series {index} name",
                ),
                family=_require_non_empty(
                    item["family"],
                    field=f"state series {index} family",
                ),
                closes=tuple(
                    _decimal_from_string(
                        value,
                        field=f"state series {index} close",
                        positive=True,
                    )
                    for value in closes
                ),
                turnovers=tuple(
                    _decimal_from_string(
                        value,
                        field=f"state series {index} turnover",
                        non_negative=True,
                    )
                    for value in turnovers
                ),
            )
        )

    last_provider_timestamp_ms = raw["last_provider_timestamp_ms"]
    if last_provider_timestamp_ms is not None:
        last_provider_timestamp_ms = _require_positive_int(
            last_provider_timestamp_ms,
            field="state last_provider_timestamp_ms",
        )

    state = SectorRadarMarketState(
        schema_version=raw["schema_version"],
        formula_version=_require_non_empty(
            raw["formula_version"],
            field="state formula_version",
        ),
        created_at=_parse_datetime(raw["created_at"], field="state created_at"),
        updated_at=_parse_datetime(raw["updated_at"], field="state updated_at"),
        source=_require_non_empty(raw["source"], field="state source"),
        source_lineage=tuple(lineage),
        catalog_hash=_require_hash(raw["catalog_hash"], field="state catalog_hash"),
        benchmark_thscode=_require_non_empty(
            benchmark["thscode"],
            field="state benchmark thscode",
        ).upper(),
        benchmark_name=_require_non_empty(
            benchmark["name"],
            field="state benchmark name",
        ),
        broad_identities=_parse_identity_list(
            raw["broad_identities"],
            family="broad",
        ),
        granular_identities=_parse_identity_list(
            raw["granular_identities"],
            family="granular",
        ),
        sessions=tuple(sessions),
        series=tuple(series),
        last_provider_timestamp_ms=last_provider_timestamp_ms,
        state_hash=_require_hash(raw["state_hash"], field="state_hash"),
        state_semantics=_require_non_empty(
            raw["state_semantics"],
            field="state_semantics",
        ),
        human_attention_authority=_require_non_empty(
            raw["human_attention_authority"],
            field="state human_attention_authority",
        ),
        investment_authority=_require_non_empty(
            raw["investment_authority"],
            field="state investment_authority",
        ),
    )
    _validate_state(state, verify_hash=True)
    return state


def load_sector_radar_market_state(path: Path) -> SectorRadarMarketState:
    return parse_sector_radar_market_state(path.read_text(encoding="utf-8"))


def validate_sector_radar_state_catalog(
    *,
    state: SectorRadarMarketState,
    catalog: HithinkIndustryCatalog,
) -> None:
    _validate_state(state, verify_hash=True)
    broad, granular = _catalog_identities(catalog)
    if catalog.catalog_hash != state.catalog_hash:
        raise ValueError("current industry catalog hash disagrees with Radar state")
    if broad != state.broad_identities:
        raise ValueError("current broad-industry catalog disagrees with Radar state")
    if granular != state.granular_identities:
        raise ValueError("current granular-industry catalog disagrees with Radar state")


def append_qualified_sector_snapshot(
    *,
    state: SectorRadarMarketState,
    catalog: HithinkIndustryCatalog,
    snapshot: HithinkQualifiedIndexSnapshotBatch,
    observed_at: datetime,
) -> SectorRadarStateUpdate:
    """Append exactly one contiguous completed session or return an idempotent no-op."""

    _require_aware(observed_at, field="Sector Radar state observed_at")
    validate_sector_radar_state_catalog(state=state, catalog=catalog)
    if snapshot.qualification_method != HITHINK_INDEX_SNAPSHOT_QUALIFICATION:
        raise ValueError("Sector Radar state snapshot qualification method disagrees")
    if snapshot.benchmark_thscode != state.benchmark_thscode:
        raise ValueError("Sector Radar state snapshot benchmark disagrees")

    expected_codes = tuple(item.thscode for item in state.series)
    by_code = {item.thscode: item for item in snapshot.points}
    if len(by_code) != len(snapshot.points):
        raise ValueError("Sector Radar state snapshot contains duplicate identities")
    if set(by_code) != set(expected_codes):
        missing = sorted(set(expected_codes) - set(by_code))
        extra = sorted(set(by_code) - set(expected_codes))
        raise ValueError(
            "Sector Radar state snapshot identity set disagrees; "
            f"missing={missing}; extra={extra}"
        )

    latest_session = state.sessions[-1]
    if snapshot.market_session < latest_session:
        raise ValueError("Sector Radar state received a stale completed session")
    current_by_code = {item.thscode: item for item in state.series}

    if snapshot.market_session == latest_session:
        for code in expected_codes:
            point = by_code[code]
            current = current_by_code[code]
            if point.last_price != current.closes[-1]:
                raise ValueError(
                    f"same-session Sector Radar close changed for {code}"
                )
            if point.turnover != current.turnovers[-1]:
                raise ValueError(
                    f"same-session Sector Radar turnover changed for {code}"
                )
        return SectorRadarStateUpdate(
            status=STATE_UPDATE_ALREADY_CURRENT,
            previous_state_hash=state.state_hash,
            state=state,
            appended_session=None,
        )

    for code in expected_codes:
        point = by_code[code]
        current = current_by_code[code]
        if point.prev_price != current.closes[-1]:
            raise ValueError(
                f"Sector Radar state continuity failed for {code}; "
                "the latest cached close is not the provider previous close"
            )

    new_sessions = (
        *state.sessions,
        snapshot.market_session,
    )[-SECTOR_RADAR_STATE_WINDOW_SESSIONS:]
    new_series = tuple(
        SectorRadarStateSeries(
            thscode=item.thscode,
            name=item.name,
            family=item.family,
            closes=(*item.closes, by_code[item.thscode].last_price)[
                -SECTOR_RADAR_STATE_WINDOW_SESSIONS:
            ],
            turnovers=(*item.turnovers, by_code[item.thscode].turnover)[
                -SECTOR_RADAR_STATE_WINDOW_SESSIONS:
            ],
        )
        for item in state.series
    )
    updated = SectorRadarMarketState(
        schema_version=state.schema_version,
        formula_version=state.formula_version,
        created_at=state.created_at,
        updated_at=observed_at,
        source=state.source,
        source_lineage=state.source_lineage,
        catalog_hash=state.catalog_hash,
        benchmark_thscode=state.benchmark_thscode,
        benchmark_name=state.benchmark_name,
        broad_identities=state.broad_identities,
        granular_identities=state.granular_identities,
        sessions=tuple(new_sessions),
        series=new_series,
        last_provider_timestamp_ms=snapshot.provider_timestamp_ms,
        state_hash="",
    )
    _validate_state(updated, verify_hash=False)
    updated = _with_state_hash(updated)
    return SectorRadarStateUpdate(
        status=STATE_UPDATE_APPENDED,
        previous_state_hash=state.state_hash,
        state=updated,
        appended_session=snapshot.market_session,
    )


def _price_series_from_state(
    state: SectorRadarMarketState,
    item: SectorRadarStateSeries,
) -> SectorPriceSeries:
    return SectorPriceSeries(
        thscode=item.thscode,
        name=item.name,
        points=tuple(
            SectorPricePoint(
                session=session,
                close=close,
                turnover=turnover,
            )
            for session, close, turnover in zip(
                state.sessions,
                item.closes,
                item.turnovers,
                strict=True,
            )
        ),
    )


def calculate_sector_radar_state_snapshot_pair(
    state: SectorRadarMarketState,
) -> SectorRadarStateSnapshotPair:
    """Calculate exact previous/current 881 and 884 snapshots from rolling state."""

    _validate_state(state, verify_hash=True)
    if len(state.sessions) < 63:
        raise ValueError("Sector Radar state lacks history for a snapshot pair")
    by_family: dict[str, list[SectorPriceSeries]] = {
        BENCHMARK_FAMILY: [],
        BROAD_881_FAMILY: [],
        GRANULAR_884_FAMILY: [],
    }
    for item in state.series:
        by_family[item.family].append(_price_series_from_state(state, item))
    benchmark_items = by_family[BENCHMARK_FAMILY]
    if len(benchmark_items) != 1:
        raise ValueError("Sector Radar state must contain one benchmark series")
    benchmark = benchmark_items[0]
    previous_session = state.sessions[-2]
    current_session = state.sessions[-1]

    return SectorRadarStateSnapshotPair(
        state_hash=state.state_hash,
        previous_session=previous_session,
        current_session=current_session,
        broad_previous=calculate_sector_radar_snapshot(
            sectors=by_family[BROAD_881_FAMILY],
            benchmark=benchmark,
            as_of_session=previous_session,
        ),
        broad_current=calculate_sector_radar_snapshot(
            sectors=by_family[BROAD_881_FAMILY],
            benchmark=benchmark,
            as_of_session=current_session,
        ),
        granular_previous=calculate_sector_radar_snapshot(
            sectors=by_family[GRANULAR_884_FAMILY],
            benchmark=benchmark,
            as_of_session=previous_session,
        ),
        granular_current=calculate_sector_radar_snapshot(
            sectors=by_family[GRANULAR_884_FAMILY],
            benchmark=benchmark,
            as_of_session=current_session,
        ),
    )
