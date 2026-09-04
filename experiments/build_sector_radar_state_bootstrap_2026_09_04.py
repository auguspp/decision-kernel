from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.runtime.sector_radar import SectorPricePoint, SectorPriceSeries
from decision_kernel.runtime.sector_radar_state import (
    SectorRadarStateSourceLineage,
    create_sector_radar_market_state,
    parse_sector_radar_market_state,
    serialize_sector_radar_market_state,
)


BROAD_ARTIFACT = Path("broad-artifact")
GRANULAR_ARTIFACT = Path("granular-artifact")
OUTPUT = Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz")
MANIFEST = Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json")
DOC = Path("docs/sector-radar-state-bootstrap-2026-09-04.md")

BROAD_RUN_ID = 33869436890
BROAD_ARTIFACT_ID = 9936117543
BROAD_ARTIFACT_DIGEST = (
    "sha256:58de421f48f5d8d5ddafd1a702e1f676367f450da145948e932b186d6cd78816"
)
GRANULAR_RUN_ID = 33878938737
GRANULAR_ARTIFACT_ID = 9941301222
GRANULAR_ARTIFACT_DIGEST = (
    "sha256:4f716374797350a1160f45ae8468834b6e9bcee0932327ad9cbdebd4802c3671"
)
GRANULAR_RESULT_HASH = (
    "6dcef7ac20360491059405163c29114a8a3e2f6f07352c774dda81262b8af633"
)
EXPECTED_CATALOG_HASH = (
    "367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360"
)
EXPECTED_SESSION = "2026-09-04"
EXPECTED_HISTORY_POINTS = 164


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def require_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return value


def verify_checkpoint(
    *,
    root: Path,
    checkpoint_path: str,
    expected_sha256: str,
    expected_code: str,
) -> Mapping[str, Any]:
    path = root / Path(checkpoint_path).name
    if not path.exists():
        raise ValueError(f"missing checkpoint for {expected_code}")
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"checkpoint hash mismatch for {expected_code}")
    payload = require_mapping(
        json.loads(path.read_text(encoding="utf-8")),
        label=f"checkpoint {expected_code}",
    )
    if payload.get("thscode") != expected_code:
        raise ValueError(f"checkpoint identity mismatch for {expected_code}")
    if payload.get("response_session") != EXPECTED_SESSION:
        raise ValueError(f"checkpoint response session mismatch for {expected_code}")
    if payload.get("expected_latest_session") != EXPECTED_SESSION:
        raise ValueError(f"checkpoint expected session mismatch for {expected_code}")
    points = payload.get("points")
    if not isinstance(points, list) or len(points) != EXPECTED_HISTORY_POINTS:
        raise ValueError(f"checkpoint history length mismatch for {expected_code}")
    return payload


def series_from_checkpoint(
    *,
    code: str,
    name: str,
    checkpoint: Mapping[str, Any],
) -> SectorPriceSeries:
    points = checkpoint["points"]
    normalized = []
    for index, raw in enumerate(points):
        row = require_mapping(raw, label=f"{code} point {index}")
        as_of = row.get("as_of")
        close = row.get("close")
        turnover = row.get("turnover")
        if not isinstance(as_of, str):
            raise ValueError(f"{code} point {index} has invalid as_of")
        if not isinstance(close, str) or not isinstance(turnover, str):
            raise ValueError(f"{code} point {index} has non-string market values")
        observed_at = datetime.fromisoformat(as_of)
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError(f"{code} point {index} has naive as_of")
        normalized.append(
            SectorPricePoint(
                session=observed_at.date(),
                close=Decimal(close),
                turnover=Decimal(turnover),
            )
        )
    return SectorPriceSeries(
        thscode=code,
        name=name,
        points=tuple(normalized),
    )


def load_benchmark_and_broad() -> tuple[
    SectorPriceSeries,
    tuple[SectorPriceSeries, ...],
    str,
    tuple[tuple[str, str], ...],
]:
    progress_path = BROAD_ARTIFACT / "sector-radar-pit-replay-progress.jsonl"
    rows = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    catalog_rows = [row for row in rows if row.get("stage") == "catalog"]
    if len(catalog_rows) != 1:
        raise ValueError("broad artifact must contain one catalog record")
    catalog_hash = catalog_rows[0].get("catalog_hash")
    if catalog_hash != EXPECTED_CATALOG_HASH:
        raise ValueError("broad artifact catalog hash mismatch")

    history_rows = [row for row in rows if row.get("stage") == "history"]
    if len(history_rows) != 101:
        raise ValueError("broad artifact must contain 101 completed history records")
    by_code = {row.get("thscode"): row for row in history_rows}
    if len(by_code) != len(history_rows):
        raise ValueError("broad artifact contains duplicate history identities")

    selected = [
        row
        for row in history_rows
        if row.get("thscode") == "000300.SH"
        or str(row.get("thscode", "")).startswith("881")
    ]
    if len(selected) != 91:
        raise ValueError("broad bootstrap selection must contain benchmark plus 90 industries")

    series_by_code: dict[str, SectorPriceSeries] = {}
    identities = []
    for row in selected:
        code = str(row["thscode"])
        name = str(row["name"])
        checkpoint = verify_checkpoint(
            root=BROAD_ARTIFACT / "sector-radar-pit-replay-inputs",
            checkpoint_path=str(row["checkpoint_path"]),
            expected_sha256=str(row["checkpoint_sha256"]),
            expected_code=code,
        )
        series_by_code[code] = series_from_checkpoint(
            code=code,
            name=name,
            checkpoint=checkpoint,
        )
        if code.startswith("881"):
            identities.append((code, name))

    benchmark = series_by_code.pop("000300.SH")
    broad = tuple(series_by_code[code] for code in sorted(series_by_code))
    if len(broad) != 90:
        raise ValueError("broad bootstrap must contain exactly 90 industries")
    return benchmark, broad, catalog_hash, tuple(sorted(identities))


def load_granular() -> tuple[
    tuple[SectorPriceSeries, ...],
    str,
    tuple[tuple[str, str], ...],
    datetime,
]:
    result_path = GRANULAR_ARTIFACT / "sector-radar-884-pit-replay.json"
    result = require_mapping(
        json.loads(result_path.read_text(encoding="utf-8")),
        label="granular replay result",
    )
    claimed_hash = result.get("result_hash")
    payload_without_hash = dict(result)
    payload_without_hash.pop("result_hash", None)
    if claimed_hash != GRANULAR_RESULT_HASH:
        raise ValueError("granular replay claimed result hash changed")
    if canonical_hash(payload_without_hash) != GRANULAR_RESULT_HASH:
        raise ValueError("granular replay result hash mismatch")

    integrity = require_mapping(result.get("integrity"), label="granular integrity")
    if integrity.get("catalog_hash") != EXPECTED_CATALOG_HASH:
        raise ValueError("granular artifact catalog hash mismatch")
    if integrity.get("granular_count") != 230:
        raise ValueError("granular artifact must contain 230 industries")
    if integrity.get("checkpoint_count") != 230:
        raise ValueError("granular artifact must contain 230 checkpoints")
    if integrity.get("history_end") != EXPECTED_SESSION:
        raise ValueError("granular artifact latest session changed")

    acquisition = require_mapping(result.get("acquisition"), label="granular acquisition")
    records = acquisition.get("records")
    if not isinstance(records, list) or len(records) != 230:
        raise ValueError("granular artifact acquisition records are incomplete")
    by_code = {record.get("thscode"): record for record in records}
    if len(by_code) != 230:
        raise ValueError("granular artifact contains duplicate identities")

    series_items = []
    identities = []
    for code in sorted(by_code):
        row = require_mapping(by_code[code], label=f"granular record {code}")
        name = str(row["name"])
        checkpoint = verify_checkpoint(
            root=GRANULAR_ARTIFACT / "sector-radar-884-pit-replay-inputs",
            checkpoint_path=str(row["checkpoint_path"]),
            expected_sha256=str(row["checkpoint_sha256"]),
            expected_code=str(code),
        )
        series_items.append(
            series_from_checkpoint(
                code=str(code),
                name=name,
                checkpoint=checkpoint,
            )
        )
        identities.append((str(code), name))

    captured_at = datetime.fromisoformat(str(result["captured_at"]))
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("granular replay captured_at is naive")
    return tuple(series_items), str(integrity["catalog_hash"]), tuple(identities), captured_at


def build_catalog(
    *,
    broad_identities: tuple[tuple[str, str], ...],
    granular_identities: tuple[tuple[str, str], ...],
):
    catalog = normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": 1,
                "item": [
                    {"thscode": code, "name": name}
                    for code, name in (*broad_identities, *granular_identities)
                ],
            },
        }
    )
    if catalog.catalog_hash != EXPECTED_CATALOG_HASH:
        raise ValueError("reconstructed catalog hash mismatch")
    if len(catalog.broad_industries) != 90:
        raise ValueError("reconstructed broad catalog shape mismatch")
    if len(catalog.granular_industries) != 230:
        raise ValueError("reconstructed granular catalog shape mismatch")
    if catalog.unexpected_industries:
        raise ValueError("reconstructed catalog contains unexpected identities")
    return catalog


def write_outputs() -> None:
    benchmark, broad, broad_catalog_hash, broad_identities = (
        load_benchmark_and_broad()
    )
    granular, granular_catalog_hash, granular_identities, captured_at = (
        load_granular()
    )
    if broad_catalog_hash != granular_catalog_hash:
        raise ValueError("source artifacts use different catalog identities")

    catalog = build_catalog(
        broad_identities=broad_identities,
        granular_identities=granular_identities,
    )
    state = create_sector_radar_market_state(
        catalog=catalog,
        benchmark=benchmark,
        broad_series=broad,
        granular_series=granular,
        created_at=captured_at,
        source="HiThink Financial-API index daily market data",
        source_lineage=(
            SectorRadarStateSourceLineage(
                role="BENCHMARK_AND_BROAD_881_QUALIFIED_HISTORY_CHECKPOINTS",
                workflow_run_id=BROAD_RUN_ID,
                artifact_id=BROAD_ARTIFACT_ID,
                artifact_digest=BROAD_ARTIFACT_DIGEST,
                result_hash=None,
            ),
            SectorRadarStateSourceLineage(
                role="GRANULAR_884_QUALIFIED_HISTORY_CHECKPOINTS",
                workflow_run_id=GRANULAR_RUN_ID,
                artifact_id=GRANULAR_ARTIFACT_ID,
                artifact_digest=GRANULAR_ARTIFACT_DIGEST,
                result_hash=GRANULAR_RESULT_HASH,
            ),
        ),
    )
    serialized = serialize_sector_radar_market_state(state).encode("utf-8")
    parsed = parse_sector_radar_market_state(serialized.decode("utf-8"))
    if parsed != state:
        raise ValueError("serialized bootstrap state does not round-trip")

    compressed = gzip.compress(serialized, compresslevel=9, mtime=0)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(compressed)
    gzip_sha256 = hashlib.sha256(compressed).hexdigest()
    uncompressed_sha256 = hashlib.sha256(serialized).hexdigest()

    manifest = {
        "schema_version": 1,
        "bootstrap_session": state.sessions[-1].isoformat(),
        "state_schema_version": state.schema_version,
        "formula_version": state.formula_version,
        "catalog_hash": state.catalog_hash,
        "state_hash": state.state_hash,
        "session_count": len(state.sessions),
        "session_start": state.sessions[0].isoformat(),
        "session_end": state.sessions[-1].isoformat(),
        "series_count": len(state.series),
        "benchmark_count": 1,
        "broad_count": len(state.broad_identities),
        "granular_count": len(state.granular_identities),
        "compressed_path": str(OUTPUT),
        "compressed_bytes": len(compressed),
        "compressed_sha256": gzip_sha256,
        "uncompressed_bytes": len(serialized),
        "uncompressed_sha256": uncompressed_sha256,
        "source_artifacts": [
            {
                "role": item.role,
                "workflow_run_id": item.workflow_run_id,
                "artifact_id": item.artifact_id,
                "artifact_digest": item.artifact_digest,
                "result_hash": item.result_hash,
            }
            for item in state.source_lineage
        ],
        "bootstrap_semantics": "DURABLE_INITIAL_STATE_ONLY_DAILY_STATE_MUST_APPEND_CONTIGUOUSLY",
        "historical_membership_authority": "NONE",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    DOC.write_text(
        f"""# Sector Radar state bootstrap — 2026-09-04

Status: **DURABLE QUALIFIED INITIAL STATE / CONTIGUOUS DAILY APPEND REQUIRED / NO HISTORICAL MEMBERSHIP / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**

## Frozen state

```text
latest completed session = {state.sessions[-1]}
rolling sessions = {len(state.sessions)}
window start = {state.sessions[0]}
series = {len(state.series)}
benchmark = {state.benchmark_thscode} / {state.benchmark_name}
broad industries = {len(state.broad_identities)}
granular industries = {len(state.granular_identities)}
catalog hash = {state.catalog_hash}
state hash = {state.state_hash}
compressed SHA-256 = {gzip_sha256}
uncompressed SHA-256 = {uncompressed_sha256}
```

Source lineage:

```text
broad / benchmark run = {BROAD_RUN_ID}
broad / benchmark artifact = {BROAD_ARTIFACT_ID}
broad / benchmark artifact digest = {BROAD_ARTIFACT_DIGEST}

granular run = {GRANULAR_RUN_ID}
granular artifact = {GRANULAR_ARTIFACT_ID}
granular artifact digest = {GRANULAR_ARTIFACT_DIGEST}
granular result hash = {GRANULAR_RESULT_HASH}
```

Every selected source checkpoint was re-hashed before state creation. The bootstrap is stored as deterministic gzip and round-tripped through the merged strict state parser.

## Use rule

```text
bootstrap only when no later qualified state exists
→ fetch exact current catalog
→ fetch one qualified complete index snapshot
→ require every provider prev_price to equal the cached latest close
→ append exactly one completed session
→ persist the new content-hashed state
```

A cache miss may restore this durable bootstrap only if the next completed market snapshot still proves direct continuity from 2026-09-04. Once the market has advanced beyond one session, this bootstrap cannot silently bridge the gap; recovery must use a separately qualified state rebuild.

The bootstrap carries no historical constituent membership, Research route, Human wake, Recommendation, Action, or investment authority.
""",
        encoding="utf-8",
    )

    print(f"STATE_HASH={state.state_hash}")
    print(f"GZIP_SHA256={gzip_sha256}")
    print(f"COMPRESSED_BYTES={len(compressed)}")
    print(f"UNCOMPRESSED_BYTES={len(serialized)}")
    print(f"SESSIONS={len(state.sessions)}")
    print(f"SERIES={len(state.series)}")
    print(f"OUTPUT={OUTPUT}")
    print(f"MANIFEST={MANIFEST}")
    print(f"DOC={DOC}")


if __name__ == "__main__":
    write_outputs()
