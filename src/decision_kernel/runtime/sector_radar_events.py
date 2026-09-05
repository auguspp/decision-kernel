from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json

from .sector_breadth import SectorCurrentBreadthObservation
from .sector_radar_shadow import (
    ACCELERATING,
    ACCELERATING_AND_PERSISTENT,
    BROAD_881,
    GRANULAR_884,
    PERSISTENT_TOP_DECILE,
    SECTOR_RADAR_SHADOW_SEMANTICS,
    SectorRadarShadowCandidate,
    SectorRadarShadowComposition,
    SectorRadarShadowGroup,
)


SECTOR_RADAR_EVENT_LEDGER_SCHEMA_VERSION = 1
SECTOR_RADAR_EVENT_LEDGER_SEMANTICS = (
    "APPEND_ONLY_SIGNAL_TIME_AUDIT_AND_EVALUATION_ANCHOR_ONLY"
)
SECTOR_RADAR_EVENT_LEDGER_SIGNAL_TRANSITION_AUTHORITY = "NONE"
SECTOR_RADAR_EVENT_LEDGER_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_EVENT_LEDGER_INVESTMENT_AUTHORITY = "NONE"

_BROAD_CODE = re.compile(r"^881\d{3}\.TI$")
_GRANULAR_CODE = re.compile(r"^884\d{3}\.TI$")
_INDEX_CODE = re.compile(r"^\d{6}\.(?:SH|SZ|TI)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EVENT_TYPES = {
    PERSISTENT_TOP_DECILE,
    ACCELERATING,
    ACCELERATING_AND_PERSISTENT,
}

_LEDGER_FIELDS = {
    "schema_version",
    "created_at",
    "updated_at",
    "source",
    "events",
    "ledger_semantics",
    "signal_transition_authority",
    "human_attention_authority",
    "investment_authority",
    "ledger_hash",
}
_EVENT_FIELDS = {
    "event_id",
    "first_recorded_at",
    "source_market_state_hash",
    "catalog_hash",
    "parent_hint_mapping_hash",
    "benchmark_thscode",
    "policy_version",
    "formula_version",
    "candidate",
    "candidate_hash",
    "first_breadth_hash",
    "first_group_hash",
    "source_composition_hash",
    "event_hash",
}
_CANDIDATE_FIELDS = {
    "thscode",
    "name",
    "family",
    "as_of_session",
    "event_type",
    "horizon_5_rank",
    "horizon_5_rating",
    "horizon_20_rank",
    "horizon_20_rating",
    "horizon_60_rating",
    "horizon_5_excess_return",
    "horizon_20_excess_return",
    "horizon_60_excess_return",
    "rank_change_5_sessions_20d",
    "excess_acceleration_5_sessions_20d",
    "positive_20d_excess_persistence_sessions",
    "top_quartile_20d_persistence_sessions",
    "turnover_pulse_5_vs_prior_20",
    "persistent_gate_entered",
    "acceleration_gate_entered",
}


@dataclass(frozen=True)
class SectorRadarCandidateEvent:
    """One immutable false-to-true signal-time record.

    The record is created only from an already-computed shadow composition.
    It is never consulted to determine whether a future transition exists.
    """

    event_id: str
    first_recorded_at: datetime
    source_market_state_hash: str
    catalog_hash: str
    parent_hint_mapping_hash: str
    benchmark_thscode: str
    policy_version: str
    formula_version: str
    candidate: SectorRadarShadowCandidate
    candidate_hash: str
    first_breadth_hash: str
    first_group_hash: str
    source_composition_hash: str
    event_hash: str


@dataclass(frozen=True)
class SectorRadarCandidateEventLedger:
    """Content-hashed append-only event memory with no signal authority."""

    schema_version: int
    created_at: datetime
    updated_at: datetime
    source: str
    events: tuple[SectorRadarCandidateEvent, ...]
    ledger_hash: str
    ledger_semantics: str = SECTOR_RADAR_EVENT_LEDGER_SEMANTICS
    signal_transition_authority: str = (
        SECTOR_RADAR_EVENT_LEDGER_SIGNAL_TRANSITION_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_RADAR_EVENT_LEDGER_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_EVENT_LEDGER_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorRadarCandidateEventLedgerUpdate:
    previous_ledger_hash: str
    ledger: SectorRadarCandidateEventLedger
    added_event_ids: tuple[str, ...]
    reused_event_ids: tuple[str, ...]
    signal_transition_authority: str = (
        SECTOR_RADAR_EVENT_LEDGER_SIGNAL_TRANSITION_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_RADAR_EVENT_LEDGER_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_RADAR_EVENT_LEDGER_INVESTMENT_AUTHORITY


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _require_non_empty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field} must be a non-empty trimmed string")
    return value


def _require_hash(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 string")
    return value


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


def _parse_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 datetime") from exc
    _require_aware(parsed, field=field)
    return parsed


def _parse_date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO date") from exc


def _parse_decimal(
    value: Any,
    *,
    field: str,
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
    if non_negative and parsed < 0:
        raise ValueError(f"{field} must be non-negative")
    return parsed


def _parse_int(
    value: Any,
    *,
    field: str,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{field} is outside its allowed range")
    return value


def _candidate_payload(candidate: SectorRadarShadowCandidate) -> dict[str, Any]:
    return json.loads(canonical_json(asdict(candidate)))


def _candidate_identity_payload(
    *,
    candidate: SectorRadarShadowCandidate,
    benchmark_thscode: str,
    policy_version: str,
    formula_version: str,
) -> dict[str, Any]:
    return {
        "as_of_session": candidate.as_of_session,
        "benchmark_thscode": benchmark_thscode,
        "event_type": candidate.event_type,
        "family": candidate.family,
        "formula_version": formula_version,
        "policy_version": policy_version,
        "thscode": candidate.thscode,
    }


def _event_payload_without_hash(event: SectorRadarCandidateEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "first_recorded_at": event.first_recorded_at,
        "source_market_state_hash": event.source_market_state_hash,
        "catalog_hash": event.catalog_hash,
        "parent_hint_mapping_hash": event.parent_hint_mapping_hash,
        "benchmark_thscode": event.benchmark_thscode,
        "policy_version": event.policy_version,
        "formula_version": event.formula_version,
        "candidate": _candidate_payload(event.candidate),
        "candidate_hash": event.candidate_hash,
        "first_breadth_hash": event.first_breadth_hash,
        "first_group_hash": event.first_group_hash,
        "source_composition_hash": event.source_composition_hash,
    }


def _ledger_payload_without_hash(
    ledger: SectorRadarCandidateEventLedger,
) -> dict[str, Any]:
    return {
        "schema_version": ledger.schema_version,
        "created_at": ledger.created_at,
        "updated_at": ledger.updated_at,
        "source": ledger.source,
        "events": [
            {
                **_event_payload_without_hash(event),
                "event_hash": event.event_hash,
            }
            for event in ledger.events
        ],
        "ledger_semantics": ledger.ledger_semantics,
        "signal_transition_authority": ledger.signal_transition_authority,
        "human_attention_authority": ledger.human_attention_authority,
        "investment_authority": ledger.investment_authority,
    }


def _with_event_hash(event: SectorRadarCandidateEvent) -> SectorRadarCandidateEvent:
    return replace(
        event,
        event_hash=canonical_hash(_event_payload_without_hash(event)),
    )


def _with_ledger_hash(
    ledger: SectorRadarCandidateEventLedger,
) -> SectorRadarCandidateEventLedger:
    return replace(
        ledger,
        ledger_hash=canonical_hash(_ledger_payload_without_hash(ledger)),
    )


def _event_sort_key(event: SectorRadarCandidateEvent) -> tuple[Any, ...]:
    return (
        event.candidate.as_of_session,
        event.candidate.family,
        event.candidate.thscode,
        event.candidate.event_type,
        event.event_id,
    )


def _validate_candidate(candidate: SectorRadarShadowCandidate) -> None:
    if candidate.family == BROAD_881:
        if not _BROAD_CODE.fullmatch(candidate.thscode):
            raise ValueError("Sector Radar event broad candidate identity is invalid")
    elif candidate.family == GRANULAR_884:
        if not _GRANULAR_CODE.fullmatch(candidate.thscode):
            raise ValueError("Sector Radar event granular candidate identity is invalid")
    else:
        raise ValueError("Sector Radar event candidate family is unsupported")
    _require_non_empty(candidate.name, field="event candidate name")
    if candidate.event_type not in _EVENT_TYPES:
        raise ValueError("Sector Radar event type is unsupported")
    for field, value in (
        ("horizon_5_rating", candidate.horizon_5_rating),
        ("horizon_20_rating", candidate.horizon_20_rating),
        ("horizon_60_rating", candidate.horizon_60_rating),
    ):
        _parse_int(value, field=f"event candidate {field}", minimum=1, maximum=99)
    for field, value in (
        (
            "positive_20d_excess_persistence_sessions",
            candidate.positive_20d_excess_persistence_sessions,
        ),
        (
            "top_quartile_20d_persistence_sessions",
            candidate.top_quartile_20d_persistence_sessions,
        ),
    ):
        _parse_int(value, field=f"event candidate {field}", minimum=0)
    for field, value in (
        ("horizon_5_rank", candidate.horizon_5_rank),
        ("horizon_20_rank", candidate.horizon_20_rank),
        ("horizon_5_excess_return", candidate.horizon_5_excess_return),
        ("horizon_20_excess_return", candidate.horizon_20_excess_return),
        ("horizon_60_excess_return", candidate.horizon_60_excess_return),
        ("rank_change_5_sessions_20d", candidate.rank_change_5_sessions_20d),
        (
            "excess_acceleration_5_sessions_20d",
            candidate.excess_acceleration_5_sessions_20d,
        ),
    ):
        if not value.is_finite():
            raise ValueError(f"event candidate {field} must be finite")
    if (
        candidate.turnover_pulse_5_vs_prior_20 is not None
        and (
            not candidate.turnover_pulse_5_vs_prior_20.is_finite()
            or candidate.turnover_pulse_5_vs_prior_20 < 0
        )
    ):
        raise ValueError("event candidate turnover pulse must be finite and non-negative")

    expected_gates = {
        PERSISTENT_TOP_DECILE: (True, False),
        ACCELERATING: (False, True),
        ACCELERATING_AND_PERSISTENT: (True, True),
    }[candidate.event_type]
    actual_gates = (
        candidate.persistent_gate_entered,
        candidate.acceleration_gate_entered,
    )
    if actual_gates != expected_gates:
        raise ValueError("Sector Radar event type and entered gates disagree")


def _validate_event(
    event: SectorRadarCandidateEvent,
    *,
    verify_hash: bool,
) -> None:
    _require_aware(event.first_recorded_at, field="event first_recorded_at")
    for field, value in (
        ("event_id", event.event_id),
        ("source_market_state_hash", event.source_market_state_hash),
        ("catalog_hash", event.catalog_hash),
        ("parent_hint_mapping_hash", event.parent_hint_mapping_hash),
        ("candidate_hash", event.candidate_hash),
        ("first_breadth_hash", event.first_breadth_hash),
        ("first_group_hash", event.first_group_hash),
        ("source_composition_hash", event.source_composition_hash),
    ):
        _require_hash(value, field=f"event {field}")
    if not _INDEX_CODE.fullmatch(event.benchmark_thscode):
        raise ValueError("event benchmark identity is invalid")
    _require_non_empty(event.policy_version, field="event policy_version")
    _require_non_empty(event.formula_version, field="event formula_version")
    _validate_candidate(event.candidate)

    expected_event_id = canonical_hash(
        _candidate_identity_payload(
            candidate=event.candidate,
            benchmark_thscode=event.benchmark_thscode,
            policy_version=event.policy_version,
            formula_version=event.formula_version,
        )
    )
    if event.event_id != expected_event_id:
        raise ValueError("Sector Radar event id mismatch")
    if event.candidate_hash != canonical_hash(asdict(event.candidate)):
        raise ValueError("Sector Radar event candidate hash mismatch")
    if verify_hash:
        _require_hash(event.event_hash, field="event_hash")
        if event.event_hash != canonical_hash(_event_payload_without_hash(event)):
            raise ValueError("Sector Radar event hash mismatch")


def _validate_ledger(
    ledger: SectorRadarCandidateEventLedger,
    *,
    verify_hash: bool,
) -> None:
    if ledger.schema_version != SECTOR_RADAR_EVENT_LEDGER_SCHEMA_VERSION:
        raise ValueError("unsupported Sector Radar event-ledger schema version")
    _require_aware(ledger.created_at, field="event ledger created_at")
    _require_aware(ledger.updated_at, field="event ledger updated_at")
    if ledger.updated_at < ledger.created_at:
        raise ValueError("event ledger updated_at precedes created_at")
    _require_non_empty(ledger.source, field="event ledger source")
    if ledger.ledger_semantics != SECTOR_RADAR_EVENT_LEDGER_SEMANTICS:
        raise ValueError("Sector Radar event-ledger semantics disagree")
    if ledger.signal_transition_authority != "NONE":
        raise ValueError("event ledger cannot carry signal-transition authority")
    if ledger.human_attention_authority != "NONE":
        raise ValueError("event ledger cannot carry Human attention authority")
    if ledger.investment_authority != "NONE":
        raise ValueError("event ledger cannot carry investment authority")

    if ledger.events != tuple(sorted(ledger.events, key=_event_sort_key)):
        raise ValueError("Sector Radar event ledger must be deterministically sorted")
    event_ids = [event.event_id for event in ledger.events]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Sector Radar event ledger contains duplicate event ids")
    for event in ledger.events:
        _validate_event(event, verify_hash=True)
        if event.first_recorded_at < ledger.created_at:
            raise ValueError("event predates its ledger")
        if event.first_recorded_at > ledger.updated_at:
            raise ValueError("event follows ledger updated_at")

    if verify_hash:
        _require_hash(ledger.ledger_hash, field="event ledger hash")
        if ledger.ledger_hash != canonical_hash(_ledger_payload_without_hash(ledger)):
            raise ValueError("Sector Radar event-ledger hash mismatch")


def create_sector_radar_candidate_event_ledger(
    *,
    created_at: datetime,
    source: str,
) -> SectorRadarCandidateEventLedger:
    _require_aware(created_at, field="event ledger created_at")
    ledger = SectorRadarCandidateEventLedger(
        schema_version=SECTOR_RADAR_EVENT_LEDGER_SCHEMA_VERSION,
        created_at=created_at,
        updated_at=created_at,
        source=_require_non_empty(source, field="event ledger source"),
        events=(),
        ledger_hash="",
    )
    _validate_ledger(ledger, verify_hash=False)
    return _with_ledger_hash(ledger)


def serialize_sector_radar_candidate_event_ledger(
    ledger: SectorRadarCandidateEventLedger,
) -> str:
    _validate_ledger(ledger, verify_hash=True)
    payload = _ledger_payload_without_hash(ledger)
    payload["ledger_hash"] = ledger.ledger_hash
    canonical_payload = json.loads(canonical_json(payload))
    return json.dumps(
        canonical_payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_sector_radar_candidate_event_ledger(
    path: Path,
    ledger: SectorRadarCandidateEventLedger,
) -> None:
    serialized = serialize_sector_radar_candidate_event_ledger(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _parse_candidate(raw: Any, *, event_index: int) -> SectorRadarShadowCandidate:
    if not isinstance(raw, Mapping):
        raise ValueError(f"event {event_index} candidate must be an object")
    _require_exact_fields(
        raw,
        _CANDIDATE_FIELDS,
        label=f"event {event_index} candidate",
    )
    family = _require_non_empty(
        raw["family"],
        field=f"event {event_index} candidate family",
    )
    thscode = _require_non_empty(
        raw["thscode"],
        field=f"event {event_index} candidate thscode",
    ).upper()
    event_type = _require_non_empty(
        raw["event_type"],
        field=f"event {event_index} candidate event_type",
    )
    turnover = raw["turnover_pulse_5_vs_prior_20"]
    if turnover is not None:
        turnover = _parse_decimal(
            turnover,
            field=f"event {event_index} candidate turnover pulse",
            non_negative=True,
        )
    persistent_entered = raw["persistent_gate_entered"]
    acceleration_entered = raw["acceleration_gate_entered"]
    if not isinstance(persistent_entered, bool) or not isinstance(
        acceleration_entered,
        bool,
    ):
        raise ValueError(f"event {event_index} candidate gate flags must be boolean")

    candidate = SectorRadarShadowCandidate(
        thscode=thscode,
        name=_require_non_empty(
            raw["name"],
            field=f"event {event_index} candidate name",
        ),
        family=family,
        as_of_session=_parse_date(
            raw["as_of_session"],
            field=f"event {event_index} candidate as_of_session",
        ),
        event_type=event_type,
        horizon_5_rank=_parse_decimal(
            raw["horizon_5_rank"],
            field=f"event {event_index} candidate horizon_5_rank",
        ),
        horizon_5_rating=_parse_int(
            raw["horizon_5_rating"],
            field=f"event {event_index} candidate horizon_5_rating",
            minimum=1,
            maximum=99,
        ),
        horizon_20_rank=_parse_decimal(
            raw["horizon_20_rank"],
            field=f"event {event_index} candidate horizon_20_rank",
        ),
        horizon_20_rating=_parse_int(
            raw["horizon_20_rating"],
            field=f"event {event_index} candidate horizon_20_rating",
            minimum=1,
            maximum=99,
        ),
        horizon_60_rating=_parse_int(
            raw["horizon_60_rating"],
            field=f"event {event_index} candidate horizon_60_rating",
            minimum=1,
            maximum=99,
        ),
        horizon_5_excess_return=_parse_decimal(
            raw["horizon_5_excess_return"],
            field=f"event {event_index} candidate horizon_5_excess_return",
        ),
        horizon_20_excess_return=_parse_decimal(
            raw["horizon_20_excess_return"],
            field=f"event {event_index} candidate horizon_20_excess_return",
        ),
        horizon_60_excess_return=_parse_decimal(
            raw["horizon_60_excess_return"],
            field=f"event {event_index} candidate horizon_60_excess_return",
        ),
        rank_change_5_sessions_20d=_parse_decimal(
            raw["rank_change_5_sessions_20d"],
            field=f"event {event_index} candidate rank change",
        ),
        excess_acceleration_5_sessions_20d=_parse_decimal(
            raw["excess_acceleration_5_sessions_20d"],
            field=f"event {event_index} candidate excess acceleration",
        ),
        positive_20d_excess_persistence_sessions=_parse_int(
            raw["positive_20d_excess_persistence_sessions"],
            field=f"event {event_index} candidate positive persistence",
            minimum=0,
        ),
        top_quartile_20d_persistence_sessions=_parse_int(
            raw["top_quartile_20d_persistence_sessions"],
            field=f"event {event_index} candidate top-quartile persistence",
            minimum=0,
        ),
        turnover_pulse_5_vs_prior_20=turnover,
        persistent_gate_entered=persistent_entered,
        acceleration_gate_entered=acceleration_entered,
    )
    _validate_candidate(candidate)
    return candidate


def parse_sector_radar_candidate_event_ledger(
    raw_ledger: str,
) -> SectorRadarCandidateEventLedger:
    try:
        raw = json.loads(raw_ledger)
    except json.JSONDecodeError as exc:
        raise ValueError("Sector Radar event ledger must contain valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("Sector Radar event ledger must be a JSON object")
    _require_exact_fields(raw, _LEDGER_FIELDS, label="Sector Radar event ledger")

    raw_events = raw["events"]
    if not isinstance(raw_events, list):
        raise ValueError("Sector Radar event ledger events must be an array")
    events: list[SectorRadarCandidateEvent] = []
    for index, item in enumerate(raw_events):
        if not isinstance(item, Mapping):
            raise ValueError(f"event {index} must be an object")
        _require_exact_fields(item, _EVENT_FIELDS, label=f"event {index}")
        event = SectorRadarCandidateEvent(
            event_id=_require_hash(item["event_id"], field=f"event {index} id"),
            first_recorded_at=_parse_datetime(
                item["first_recorded_at"],
                field=f"event {index} first_recorded_at",
            ),
            source_market_state_hash=_require_hash(
                item["source_market_state_hash"],
                field=f"event {index} source_market_state_hash",
            ),
            catalog_hash=_require_hash(
                item["catalog_hash"],
                field=f"event {index} catalog_hash",
            ),
            parent_hint_mapping_hash=_require_hash(
                item["parent_hint_mapping_hash"],
                field=f"event {index} parent_hint_mapping_hash",
            ),
            benchmark_thscode=_require_non_empty(
                item["benchmark_thscode"],
                field=f"event {index} benchmark_thscode",
            ).upper(),
            policy_version=_require_non_empty(
                item["policy_version"],
                field=f"event {index} policy_version",
            ),
            formula_version=_require_non_empty(
                item["formula_version"],
                field=f"event {index} formula_version",
            ),
            candidate=_parse_candidate(item["candidate"], event_index=index),
            candidate_hash=_require_hash(
                item["candidate_hash"],
                field=f"event {index} candidate_hash",
            ),
            first_breadth_hash=_require_hash(
                item["first_breadth_hash"],
                field=f"event {index} first_breadth_hash",
            ),
            first_group_hash=_require_hash(
                item["first_group_hash"],
                field=f"event {index} first_group_hash",
            ),
            source_composition_hash=_require_hash(
                item["source_composition_hash"],
                field=f"event {index} source_composition_hash",
            ),
            event_hash=_require_hash(
                item["event_hash"],
                field=f"event {index} event_hash",
            ),
        )
        _validate_event(event, verify_hash=True)
        events.append(event)

    ledger = SectorRadarCandidateEventLedger(
        schema_version=raw["schema_version"],
        created_at=_parse_datetime(raw["created_at"], field="ledger created_at"),
        updated_at=_parse_datetime(raw["updated_at"], field="ledger updated_at"),
        source=_require_non_empty(raw["source"], field="ledger source"),
        events=tuple(events),
        ledger_hash=_require_hash(raw["ledger_hash"], field="ledger_hash"),
        ledger_semantics=_require_non_empty(
            raw["ledger_semantics"],
            field="ledger semantics",
        ),
        signal_transition_authority=_require_non_empty(
            raw["signal_transition_authority"],
            field="ledger signal-transition authority",
        ),
        human_attention_authority=_require_non_empty(
            raw["human_attention_authority"],
            field="ledger Human attention authority",
        ),
        investment_authority=_require_non_empty(
            raw["investment_authority"],
            field="ledger investment authority",
        ),
    )
    _validate_ledger(ledger, verify_hash=True)
    return ledger


def load_sector_radar_candidate_event_ledger(
    path: Path,
) -> SectorRadarCandidateEventLedger:
    return parse_sector_radar_candidate_event_ledger(
        path.read_text(encoding="utf-8")
    )


def _candidate_enrichment_by_code(
    composition: SectorRadarShadowComposition,
) -> tuple[
    dict[str, SectorCurrentBreadthObservation],
    dict[str, SectorRadarShadowGroup],
]:
    breadth_by_code: dict[str, SectorCurrentBreadthObservation] = {}
    group_by_code: dict[str, SectorRadarShadowGroup] = {}
    for group in composition.all_groups:
        candidate_breadth = {
            group.primary_candidate.thscode: group.primary_breadth,
            **{
                candidate.thscode: breadth
                for candidate, breadth in zip(
                    group.granular_drivers,
                    group.granular_driver_breadth,
                    strict=True,
                )
            },
        }
        for candidate in group.all_candidates:
            breadth = candidate_breadth.get(candidate.thscode)
            if breadth is None:
                raise ValueError(
                    "Sector Radar event ledger cannot locate candidate breadth"
                )
            if candidate.thscode in group_by_code:
                raise ValueError(
                    "Sector Radar event ledger candidate appears in multiple groups"
                )
            breadth_by_code[candidate.thscode] = breadth
            group_by_code[candidate.thscode] = group
    if set(group_by_code) != {
        candidate.thscode for candidate in composition.all_candidates
    }:
        raise ValueError("Sector Radar event ledger composition is incomplete")
    return breadth_by_code, group_by_code


def _build_event(
    *,
    candidate: SectorRadarShadowCandidate,
    breadth: SectorCurrentBreadthObservation,
    group: SectorRadarShadowGroup,
    composition: SectorRadarShadowComposition,
    source_market_state_hash: str,
    catalog_hash: str,
    parent_hint_mapping_hash: str,
    benchmark_thscode: str,
    formula_version: str,
    recorded_at: datetime,
) -> SectorRadarCandidateEvent:
    candidate_hash = canonical_hash(asdict(candidate))
    event_id = canonical_hash(
        _candidate_identity_payload(
            candidate=candidate,
            benchmark_thscode=benchmark_thscode,
            policy_version=composition.policy_version,
            formula_version=formula_version,
        )
    )
    event = SectorRadarCandidateEvent(
        event_id=event_id,
        first_recorded_at=recorded_at,
        source_market_state_hash=source_market_state_hash,
        catalog_hash=catalog_hash,
        parent_hint_mapping_hash=parent_hint_mapping_hash,
        benchmark_thscode=benchmark_thscode,
        policy_version=composition.policy_version,
        formula_version=formula_version,
        candidate=candidate,
        candidate_hash=candidate_hash,
        first_breadth_hash=canonical_hash(asdict(breadth)),
        first_group_hash=canonical_hash(asdict(group)),
        source_composition_hash=canonical_hash(asdict(composition)),
        event_hash="",
    )
    event = _with_event_hash(event)
    _validate_event(event, verify_hash=True)
    return event


def append_sector_radar_candidate_events(
    *,
    ledger: SectorRadarCandidateEventLedger,
    composition: SectorRadarShadowComposition,
    source_market_state_hash: str,
    catalog_hash: str,
    parent_hint_mapping_hash: str,
    benchmark_thscode: str,
    formula_version: str,
    recorded_at: datetime,
) -> SectorRadarCandidateEventLedgerUpdate:
    """Append immutable signal events without participating in signal selection."""

    _validate_ledger(ledger, verify_hash=True)
    _require_aware(recorded_at, field="event recorded_at")
    if recorded_at < ledger.created_at:
        raise ValueError("event recorded_at predates the event ledger")
    _require_hash(source_market_state_hash, field="source market-state hash")
    _require_hash(catalog_hash, field="event catalog hash")
    _require_hash(parent_hint_mapping_hash, field="parent-hint mapping hash")
    if not _INDEX_CODE.fullmatch(benchmark_thscode):
        raise ValueError("event benchmark identity is invalid")
    _require_non_empty(formula_version, field="event formula_version")
    if composition.shadow_semantics != SECTOR_RADAR_SHADOW_SEMANTICS:
        raise ValueError("event composition shadow semantics disagree")
    if composition.human_attention_authority != "NONE":
        raise ValueError("event composition cannot carry Human attention authority")
    if composition.investment_authority != "NONE":
        raise ValueError("event composition cannot carry investment authority")

    breadth_by_code, group_by_code = _candidate_enrichment_by_code(composition)
    proposed = tuple(
        _build_event(
            candidate=candidate,
            breadth=breadth_by_code[candidate.thscode],
            group=group_by_code[candidate.thscode],
            composition=composition,
            source_market_state_hash=source_market_state_hash,
            catalog_hash=catalog_hash,
            parent_hint_mapping_hash=parent_hint_mapping_hash,
            benchmark_thscode=benchmark_thscode,
            formula_version=formula_version,
            recorded_at=recorded_at,
        )
        for candidate in composition.all_candidates
    )

    if ledger.events and proposed:
        latest_existing_session = ledger.events[-1].candidate.as_of_session
        if any(
            event.candidate.as_of_session < latest_existing_session
            for event in proposed
        ):
            raise ValueError(
                "Sector Radar event ledger cannot append retrospective signal events"
            )

    by_id = {event.event_id: event for event in ledger.events}
    additions: list[SectorRadarCandidateEvent] = []
    reused: list[str] = []
    immutable_fields = (
        "source_market_state_hash",
        "catalog_hash",
        "parent_hint_mapping_hash",
        "benchmark_thscode",
        "policy_version",
        "formula_version",
        "candidate_hash",
    )
    for event in proposed:
        existing = by_id.get(event.event_id)
        if existing is None:
            additions.append(event)
            by_id[event.event_id] = event
            continue
        for field in immutable_fields:
            if getattr(existing, field) != getattr(event, field):
                raise ValueError(
                    "existing Sector Radar event disagrees with recomputed signal "
                    f"identity for {event.event_id}"
                )
        reused.append(event.event_id)

    if not additions:
        return SectorRadarCandidateEventLedgerUpdate(
            previous_ledger_hash=ledger.ledger_hash,
            ledger=ledger,
            added_event_ids=(),
            reused_event_ids=tuple(sorted(reused)),
        )

    updated = SectorRadarCandidateEventLedger(
        schema_version=ledger.schema_version,
        created_at=ledger.created_at,
        updated_at=recorded_at,
        source=ledger.source,
        events=tuple(sorted((*ledger.events, *additions), key=_event_sort_key)),
        ledger_hash="",
    )
    _validate_ledger(updated, verify_hash=False)
    updated = _with_ledger_hash(updated)
    return SectorRadarCandidateEventLedgerUpdate(
        previous_ledger_hash=ledger.ledger_hash,
        ledger=updated,
        added_event_ids=tuple(sorted(event.event_id for event in additions)),
        reused_event_ids=tuple(sorted(reused)),
    )
