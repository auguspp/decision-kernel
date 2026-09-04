from __future__ import annotations

import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from decision_kernel.adapters.hithink import SHANGHAI_TZ, require_hithink_data
from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.runtime.hithink_http import (
    HITHINK_API_KEY_ENV,
    _request_hithink_json,
)
from decision_kernel.runtime.hithink_index_http import HITHINK_INDEX_CATALOG_PATH
from decision_kernel.runtime.sector_breadth import (
    SectorConstituentIdentity,
    SectorMembershipSnapshot,
    normalize_sector_membership,
)


CONSTITUENTS_PATH = "/api/a-share-index/constituents/ths-stock-list"
PACE_SECONDS = float(
    os.environ.get("SECTOR_RADAR_HIERARCHY_PACE_SECONDS", "2.5")
)
MAX_TRANSPORT_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0

RESULT = Path("sector-radar-full-current-hierarchy.json")
SUMMARY = Path("sector-radar-full-current-hierarchy-summary.md")
PROGRESS = Path("sector-radar-full-current-hierarchy-progress.jsonl")
ERROR = Path("sector-radar-full-current-hierarchy-error.json")
CHECKPOINT_DIR = Path("sector-radar-full-current-hierarchy-inputs")

PRESSURE_CODES = (
    "881101.TI",
    "884001.TI",
    "881102.TI",
    "884005.TI",
    "884006.TI",
    "884275.TI",
    "884276.TI",
    "884277.TI",
    "881166.TI",
    "884182.TI",
    "884183.TI",
)


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def digest(value: Any) -> str:
    encoded = json.dumps(
        jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def locator(path: str, params: Mapping[str, str]) -> str:
    query = urlencode(sorted(params.items()))
    return f"https://fuyao.aicubes.cn{path}" + (f"?{query}" if query else "")


def progress(payload: Mapping[str, Any]) -> None:
    with PROGRESS.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(jsonable(payload), ensure_ascii=False, sort_keys=True) + "\n"
        )


def request(
    api_key: str,
    path: str,
    params: Mapping[str, str],
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        started = datetime.now(timezone.utc)
        try:
            envelope = _request_hithink_json(
                api_key=api_key,
                path=path,
                params=params,
                timeout_seconds=30.0,
            )
        except ConnectionError as exc:
            completed = datetime.now(timezone.utc)
            attempt = {
                "attempt_number": attempt_number,
                "status": "TRANSIENT_CONNECTION_FAILURE",
                "request_started_at": started,
                "response_completed_at": completed,
                "duration_seconds": (completed - started).total_seconds(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            attempts.append(attempt)
            progress(
                {
                    "stage": "transport_retry",
                    "path": path,
                    "params": dict(sorted(params.items())),
                    **attempt,
                }
            )
            if attempt_number == MAX_TRANSPORT_ATTEMPTS:
                raise
            time.sleep(RETRY_BASE_SECONDS * (2 ** (attempt_number - 1)))
            continue

        completed = datetime.now(timezone.utc)
        attempts.append(
            {
                "attempt_number": attempt_number,
                "status": "SUCCESS",
                "request_started_at": started,
                "response_completed_at": completed,
                "duration_seconds": (completed - started).total_seconds(),
            }
        )
        return envelope, {
            "path": path,
            "params": dict(sorted(params.items())),
            "source_locator": locator(path, params),
            "request_started_at": started,
            "response_completed_at": completed,
            "duration_seconds": (completed - started).total_seconds(),
            "request_id": envelope.get("request_id"),
            "business_code": envelope.get("code"),
            "envelope_sha256": digest(envelope),
            "transport_attempt_count": attempt_number,
            "transport_retry_count": attempt_number - 1,
            "transport_attempts": attempts,
            "retry_scope": "TRANSIENT_CONNECTION_FAILURE_ONLY",
        }
    raise RuntimeError("unreachable request loop")


def membership_from_envelope(
    envelope: Mapping[str, Any],
    *,
    sector_thscode: str,
    sector_name: str,
) -> SectorMembershipSnapshot:
    data = require_hithink_data(envelope, endpoint=CONSTITUENTS_PATH)
    timestamp_raw = data.get("timestamp")
    if isinstance(timestamp_raw, bool):
        raise ValueError(f"membership timestamp is invalid for {sector_thscode}")
    try:
        timestamp_ms = int(timestamp_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"membership timestamp is invalid for {sector_thscode}"
        ) from exc
    if timestamp_ms <= 0:
        raise ValueError(f"membership timestamp is invalid for {sector_thscode}")
    captured_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=SHANGHAI_TZ)

    items = data.get("item")
    if not isinstance(items, list) or not items:
        raise ValueError(f"membership is empty for {sector_thscode}")
    members: list[SectorConstituentIdentity] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            raise ValueError(f"membership contains malformed row for {sector_thscode}")
        members.append(
            SectorConstituentIdentity(
                thscode=str(raw.get("thscode", "")),
                ticker=str(raw.get("ticker", "")),
                name=str(raw.get("name", "")),
            )
        )
    return normalize_sector_membership(
        sector_thscode=sector_thscode,
        sector_name=sector_name,
        captured_at=captured_at,
        members=members,
    )


def write_checkpoint(
    *,
    membership: SectorMembershipSnapshot,
    request_meta: Mapping[str, Any],
) -> tuple[Path, str]:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"{membership.sector_thscode.replace('.', '_')}.json"
    payload = {
        "schema_version": 1,
        "membership": membership,
        "request": request_meta,
        "checkpoint_semantics": "QUALIFIED_CURRENT_MEMBERSHIP_INPUT_ONLY",
        "historical_membership_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    serialized = (
        json.dumps(
            jsonable(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path, hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _member_set(membership: SectorMembershipSnapshot) -> frozenset[str]:
    return frozenset(member.thscode for member in membership.members)


def map_granular_to_broad(
    *,
    broad: Sequence[SectorMembershipSnapshot],
    granular: Sequence[SectorMembershipSnapshot],
) -> tuple[dict[str, Any], ...]:
    """Map by current exact set containment without inventing historical hierarchy."""

    broad_sets = {item.sector_thscode: _member_set(item) for item in broad}
    broad_by_code = {item.sector_thscode: item for item in broad}
    rows: list[dict[str, Any]] = []
    for child in granular:
        child_set = _member_set(child)
        containing: list[dict[str, Any]] = []
        partial: list[dict[str, Any]] = []
        for parent_code, parent_set in broad_sets.items():
            intersection = child_set & parent_set
            union = child_set | parent_set
            containment = Decimal(len(intersection)) / Decimal(len(child_set))
            jaccard = Decimal(len(intersection)) / Decimal(len(union))
            candidate = {
                "parent_thscode": parent_code,
                "parent_name": broad_by_code[parent_code].sector_name,
                "parent_member_count": len(parent_set),
                "intersection_count": len(intersection),
                "child_containment": containment,
                "jaccard": jaccard,
            }
            if child_set <= parent_set:
                containing.append(candidate)
            elif intersection:
                partial.append(candidate)

        containing.sort(
            key=lambda item: (
                item["parent_member_count"],
                -item["jaccard"],
                item["parent_thscode"],
            )
        )
        partial.sort(
            key=lambda item: (
                item["child_containment"],
                item["jaccard"],
                item["intersection_count"],
                item["parent_thscode"],
            ),
            reverse=True,
        )
        if len(containing) == 1:
            status = "UNIQUE_FULL_CONTAINMENT_PARENT"
        elif len(containing) > 1:
            status = "AMBIGUOUS_MULTIPLE_FULL_CONTAINMENT_PARENTS"
        else:
            status = "NO_FULL_CONTAINMENT_PARENT"
        rows.append(
            {
                "child_thscode": child.sector_thscode,
                "child_name": child.sector_name,
                "child_member_count": len(child_set),
                "child_constituent_set_hash": child.constituent_set_hash,
                "mapping_status": status,
                "full_containment_parents": tuple(containing),
                "selected_unique_parent": containing[0] if len(containing) == 1 else None,
                "best_partial_parents": tuple(partial[:5]),
                "mapping_semantics": "CURRENT_CONSTITUENT_SET_RELATION_ONLY",
                "historical_membership_authority": "NONE",
            }
        )
    rows.sort(key=lambda item: item["child_thscode"])
    return tuple(rows)


def exact_duplicate_groups(
    memberships: Sequence[SectorMembershipSnapshot],
) -> tuple[dict[str, Any], ...]:
    """Group industries by the member set itself, not a sector-scoped hash."""

    by_member_set: dict[tuple[str, ...], list[SectorMembershipSnapshot]] = defaultdict(list)
    for item in memberships:
        member_set = tuple(sorted(member.thscode for member in item.members))
        by_member_set[member_set].append(item)
    groups = []
    for member_set, items in by_member_set.items():
        if len(items) <= 1:
            continue
        ordered = sorted(items, key=lambda item: item.sector_thscode)
        groups.append(
            {
                "member_set_hash": digest(member_set),
                "member_count": len(member_set),
                "members": member_set,
                "industries": tuple(
                    {
                        "thscode": item.sector_thscode,
                        "name": item.sector_name,
                        "sector_scoped_constituent_set_hash": (
                            item.constituent_set_hash
                        ),
                    }
                    for item in ordered
                ),
            }
        )
    groups.sort(
        key=lambda item: (
            len(item["industries"]),
            item["member_count"],
            item["member_set_hash"],
        ),
        reverse=True,
    )
    return tuple(groups)

def broad_overlap_controls(
    broad: Sequence[SectorMembershipSnapshot],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for left_index, left in enumerate(broad):
        left_set = _member_set(left)
        for right in broad[left_index + 1 :]:
            right_set = _member_set(right)
            intersection = left_set & right_set
            if not intersection:
                continue
            union = left_set | right_set
            rows.append(
                {
                    "left_thscode": left.sector_thscode,
                    "left_name": left.sector_name,
                    "right_thscode": right.sector_thscode,
                    "right_name": right.sector_name,
                    "intersection_count": len(intersection),
                    "jaccard": Decimal(len(intersection)) / Decimal(len(union)),
                    "smaller_set_containment": (
                        Decimal(len(intersection))
                        / Decimal(min(len(left_set), len(right_set)))
                    ),
                    "intersection_sample": tuple(sorted(intersection)[:10]),
                }
            )
    rows.sort(
        key=lambda item: (
            item["jaccard"],
            item["smaller_set_containment"],
            item["intersection_count"],
            item["left_thscode"],
            item["right_thscode"],
        ),
        reverse=True,
    )
    return tuple(rows)


def summary_markdown(result: Mapping[str, Any]) -> str:
    mapping = result["mapping"]
    lines = [
        "# Sector Discovery Radar — full current hierarchy proof",
        "",
        f"- Captured: `{result['captured_at']}`",
        f"- Broad memberships: `{result['integrity']['broad_count']}`",
        f"- Granular memberships: `{result['integrity']['granular_count']}`",
        f"- Unique full-containment mappings: `{mapping['unique_count']}`",
        f"- Ambiguous mappings: `{mapping['ambiguous_count']}`",
        f"- Unmapped granular industries: `{mapping['unmapped_count']}`",
        f"- Exact duplicate granular sets: `{len(result['exact_duplicate_granular_sets'])}` groups",
        "- Historical membership authority: `NONE`",
        "- Human attention authority: `NONE`",
        "- Investment authority: `NONE`",
        "",
        "## Pressure-case mapping",
        "",
        "| Child | Status | Parent(s) | Members |",
        "| --- | --- | --- | ---: |",
    ]
    pressure = set(result["pressure_codes"])
    for row in result["granular_to_broad"]:
        if row["child_thscode"] not in pressure:
            continue
        parents = ", ".join(
            f"{item['parent_name']} `{item['parent_thscode']}`"
            for item in row["full_containment_parents"]
        ) or "none"
        lines.append(
            f"| {row['child_name']} `{row['child_thscode']}` | "
            f"{row['mapping_status']} | {parents} | {row['child_member_count']} |"
        )

    lines.extend(
        [
            "",
            "## Ambiguous or unmapped granular industries",
            "",
            "| Child | Status | Full parents | Best partial containment |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    exceptional = [
        row
        for row in result["granular_to_broad"]
        if row["mapping_status"] != "UNIQUE_FULL_CONTAINMENT_PARENT"
    ]
    for row in exceptional[:30]:
        best = row["best_partial_parents"]
        best_value = "NA" if not best else f"{Decimal(str(best[0]['child_containment'])):.1%}"
        lines.append(
            f"| {row['child_name']} `{row['child_thscode']}` | "
            f"{row['mapping_status']} | {len(row['full_containment_parents'])} | "
            f"{best_value} |"
        )
    if not exceptional:
        lines.append("| none | — | — | — |")

    lines.extend(
        [
            "",
            "## Parents with most uniquely mapped children",
            "",
            "| Parent | Children |",
            "| --- | ---: |",
        ]
    )
    for row in result["parents_by_unique_child_count"][:20]:
        lines.append(
            f"| {row['parent_name']} `{row['parent_thscode']}` | "
            f"{row['unique_child_count']} |"
        )

    lines.extend(
        [
            "",
            "Current-set containment is a routing and deduplication observation only. "
            "It does not establish historical taxonomy, Fundamental Belief, a Research "
            "route, Recommendation, Action, or investment authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    if PACE_SECONDS < 0:
        raise ValueError("hierarchy request pace must be non-negative")
    api_key = os.environ.get(HITHINK_API_KEY_ENV)
    if not api_key:
        raise ValueError(f"{HITHINK_API_KEY_ENV} is required")

    captured_at = datetime.now(timezone.utc)
    catalog_envelope, catalog_meta = request(
        api_key,
        HITHINK_INDEX_CATALOG_PATH,
        {"tag": "industry"},
    )
    catalog = normalize_hithink_industry_catalog(catalog_envelope)
    if len(catalog.broad_industries) != 90:
        raise ValueError(
            f"expected 90 current broad industries, got {len(catalog.broad_industries)}"
        )
    if len(catalog.granular_industries) != 230:
        raise ValueError(
            "expected 230 current granular industries, got "
            f"{len(catalog.granular_industries)}"
        )
    identities = catalog.broad_industries + catalog.granular_industries
    progress(
        {
            "stage": "catalog",
            "catalog_hash": catalog.catalog_hash,
            "broad_count": len(catalog.broad_industries),
            "granular_count": len(catalog.granular_industries),
            **catalog_meta,
        }
    )

    memberships: dict[str, SectorMembershipSnapshot] = {}
    request_records: list[dict[str, Any]] = []
    for index, identity in enumerate(identities):
        if index and PACE_SECONDS:
            time.sleep(PACE_SECONDS)
        envelope, meta = request(
            api_key,
            CONSTITUENTS_PATH,
            {"thscode": identity.thscode},
        )
        membership = membership_from_envelope(
            envelope,
            sector_thscode=identity.thscode,
            sector_name=identity.name,
        )
        checkpoint_path, checkpoint_sha256 = write_checkpoint(
            membership=membership,
            request_meta=meta,
        )
        record = {
            "stage": "membership",
            "index": index + 1,
            "total": len(identities),
            "sector_thscode": identity.thscode,
            "sector_name": identity.name,
            "family": "BROAD_881" if identity.thscode.startswith("881") else "GRANULAR_884",
            "member_count": len(membership.members),
            "constituent_set_hash": membership.constituent_set_hash,
            "membership_captured_at": membership.captured_at,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha256,
            **meta,
        }
        memberships[identity.thscode] = membership
        request_records.append(record)
        progress(record)
        print(
            f"MEMBERSHIP {index + 1}/{len(identities)} "
            f"{identity.thscode} {identity.name} members={len(membership.members)}",
            flush=True,
        )

    broad = tuple(memberships[item.thscode] for item in catalog.broad_industries)
    granular = tuple(
        memberships[item.thscode] for item in catalog.granular_industries
    )
    mapping_rows = map_granular_to_broad(broad=broad, granular=granular)
    unique = [
        row
        for row in mapping_rows
        if row["mapping_status"] == "UNIQUE_FULL_CONTAINMENT_PARENT"
    ]
    ambiguous = [
        row
        for row in mapping_rows
        if row["mapping_status"]
        == "AMBIGUOUS_MULTIPLE_FULL_CONTAINMENT_PARENTS"
    ]
    unmapped = [
        row
        for row in mapping_rows
        if row["mapping_status"] == "NO_FULL_CONTAINMENT_PARENT"
    ]

    parent_name = {item.sector_thscode: item.sector_name for item in broad}
    parent_counts: dict[str, int] = defaultdict(int)
    for row in unique:
        parent_counts[row["selected_unique_parent"]["parent_thscode"]] += 1
    parents_by_child_count = tuple(
        {
            "parent_thscode": code,
            "parent_name": parent_name[code],
            "unique_child_count": count,
        }
        for code, count in sorted(
            parent_counts.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
    )

    result: dict[str, Any] = {
        "schema_version": 1,
        "captured_at": captured_at,
        "source": "HiThink Financial-API current industry constituents",
        "catalog": {
            "catalog_hash": catalog.catalog_hash,
            "provider_timestamp_ms": catalog.provider_timestamp_ms,
            "request": catalog_meta,
        },
        "acquisition": {
            "request_count": 1 + len(identities),
            "membership_request_count": len(identities),
            "pace_seconds": PACE_SECONDS,
            "max_transport_attempts": MAX_TRANSPORT_ATTEMPTS,
            "retry_scope": "TRANSIENT_CONNECTION_FAILURE_ONLY",
            "transport_retry_count": sum(
                int(record["transport_retry_count"]) for record in request_records
            ),
            "records": tuple(request_records),
        },
        "integrity": {
            "broad_count": len(broad),
            "granular_count": len(granular),
            "checkpoint_count": len(tuple(CHECKPOINT_DIR.glob("*.json"))),
            "current_membership_only": True,
            "historical_membership_backfill": False,
        },
        "mapping": {
            "unique_count": len(unique),
            "ambiguous_count": len(ambiguous),
            "unmapped_count": len(unmapped),
            "unique_coverage_ratio": Decimal(len(unique)) / Decimal(len(granular)),
        },
        "granular_to_broad": mapping_rows,
        "parents_by_unique_child_count": parents_by_child_count,
        "exact_duplicate_granular_sets": exact_duplicate_groups(granular),
        "broad_overlap_controls": broad_overlap_controls(broad),
        "pressure_codes": PRESSURE_CODES,
        "mapping_semantics": "CURRENT_CONSTITUENT_SET_RELATION_ONLY",
        "historical_membership_authority": "NONE",
        "research_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
        "explicit_non_authorities": (
            "NO_HISTORICAL_TAXONOMY_CLAIM",
            "NO_RESEARCH_ROUTE",
            "NO_RECOMMENDATION",
            "NO_ACTION",
        ),
    }
    result["result_hash"] = digest(result)
    RESULT.write_text(
        json.dumps(jsonable(result), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    normalized = json.loads(RESULT.read_text(encoding="utf-8"))
    SUMMARY.write_text(summary_markdown(normalized), encoding="utf-8")

    print(f"RESULT={RESULT}")
    print(f"SUMMARY={SUMMARY}")
    print(f"UNIQUE_MAPPINGS={len(unique)}")
    print(f"AMBIGUOUS_MAPPINGS={len(ambiguous)}")
    print(f"UNMAPPED={len(unmapped)}")
    print("HISTORICAL_MEMBERSHIP_AUTHORITY=NONE")
    print("HUMAN_ATTENTION_AUTHORITY=NONE")
    print("INVESTMENT_AUTHORITY=NONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        ERROR.write_text(
            json.dumps(
                {
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "progress_path": str(PROGRESS),
                    "checkpoint_dir": str(CHECKPOINT_DIR),
                    "checkpoint_count": (
                        len(tuple(CHECKPOINT_DIR.glob("*.json")))
                        if CHECKPOINT_DIR.is_dir()
                        else 0
                    ),
                    "historical_membership_authority": "NONE",
                    "human_attention_authority": "NONE",
                    "investment_authority": "NONE",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
