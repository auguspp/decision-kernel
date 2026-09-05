from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json


COLUMNS = frozenset({"thscode", "currency", "interval", "adjusted", "date_ms",
                     "open_price", "high_price", "low_price", "close_price", "volume", "turnover"})
PRICE_FIELDS = ("open_price", "high_price", "low_price", "close_price")
NUMERIC_FIELDS = (*PRICE_FIELDS, "volume", "turnover")
MAX_ROWS = 1_000_000
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024
CODE = re.compile(r"^[0-9]{6}\.(SH|SZ|BJ)$")
TZ = ZoneInfo("Asia/Shanghai")
SEMANTICS = "OFFLINE_DUMP_INTEGRITY_STUDY_NOT_MARKET_STATE_OR_SIGNAL_AUTHORITY"


class DumpInspectionError(ValueError):
    pass


def _code(value: Any) -> str:
    if not isinstance(value, str) or CODE.fullmatch(value) is None:
        raise DumpInspectionError("invalid exact A-share identity")
    return value


def _number(value: Any, *, positive: bool) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise DumpInspectionError("missing or invalid numeric field; no zero filling")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise DumpInspectionError("invalid numeric field") from exc
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise DumpInspectionError("nonfinite or out-of-range numeric field")
    return number


def _session(milliseconds: Any) -> date:
    if isinstance(milliseconds, bool) or not isinstance(milliseconds, int):
        raise DumpInspectionError("date_ms must be integer milliseconds")
    try:
        timestamp = datetime.fromtimestamp(milliseconds / 1000, tz=TZ)
    except (OSError, ValueError, OverflowError) as exc:
        raise DumpInspectionError("invalid date_ms") from exc
    if timestamp.time() != time(0):
        raise DumpInspectionError("daily-k date_ms must be Shanghai midnight")
    return timestamp.date()


def inspect_daily_k_rows(
    rows: Iterable[Mapping[str, Any]], *, expected_sessions: Sequence[date],
    current_universe: Sequence[str], reference_snapshot: Mapping[str, Any],
    max_rows: int = MAX_ROWS,
) -> dict[str, Any]:
    """Bounded structural and same-source reconciliation, never qualification.

    All date/universe/reference inputs must be independently reviewed. They are
    not authenticated just because a local file passes this pure inspection.
    """
    sessions = tuple(expected_sessions)
    if len(sessions) < 2 or any(type(day) is not date for day in sessions) or sessions != tuple(sorted(set(sessions))):
        raise DumpInspectionError("explicit expected session window must be unique and ascending")
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows <= 0 or max_rows > MAX_ROWS:
        raise DumpInspectionError("invalid operations row budget")
    universe = tuple(_code(code) for code in current_universe)
    if not universe or len(universe) != len(set(universe)):
        raise DumpInspectionError("explicit current universe must be nonempty and unique")
    latest, previous = sessions[-1], sessions[-2]
    if reference_snapshot.get("market_session") != latest.isoformat():
        raise DumpInspectionError("reference snapshot session disagrees with expected latest session")
    refs = reference_snapshot.get("points")
    if not isinstance(refs, list) or not refs:
        raise DumpInspectionError("reference snapshot requires explicit points")
    reference = {}
    for item in refs:
        if not isinstance(item, Mapping):
            raise DumpInspectionError("malformed reference row")
        code = _code(item.get("thscode"))
        if code in reference or code not in set(universe):
            raise DumpInspectionError("duplicate or off-universe reference identity")
        reference[code] = {
            field: None if item.get(field) is None else _number(item[field], positive=field != "turnover")
            for field in ("last_price", "prev_price", "turnover")
        }

    seen = set()
    identities = set()
    by_session = {day: set() for day in sessions}
    latest_rows, previous_rows = {}, {}
    row_count, zero_volume_rows = 0, 0
    for row_count, row in enumerate(rows, 1):
        if row_count > max_rows:
            raise DumpInspectionError("daily-k scan exceeds the operations row budget")
        if not isinstance(row, Mapping) or set(row) != COLUMNS:
            raise DumpInspectionError("daily-k schema changed or contains missing/unknown columns")
        code = _code(row["thscode"])
        if (row["currency"], row["interval"], row["adjusted"]) != ("CNY", "1d", "none"):
            raise DumpInspectionError("currency/interval/adjustment convention disagrees")
        day = _session(row["date_ms"])
        if day not in by_session:
            raise DumpInspectionError("future, off-calendar or outside-window bar")
        key = (code, day)
        if key in seen:
            raise DumpInspectionError("duplicate identity/session; no UPSERT of frozen inputs")
        seen.add(key)
        values = {field: _number(row[field], positive=field in PRICE_FIELDS) for field in NUMERIC_FIELDS}
        if not (values["low_price"] <= values["open_price"] <= values["high_price"]
                and values["low_price"] <= values["close_price"] <= values["high_price"]):
            raise DumpInspectionError("OHLC daily range is inconsistent")
        identities.add(code)
        by_session[day].add(code)
        zero_volume_rows += values["volume"] == 0
        if day == latest:
            latest_rows[code] = values
        if day == previous:
            previous_rows[code] = values
    if not row_count:
        raise DumpInspectionError("empty daily-k dump")

    mismatches, unpriced = [], []
    checked = 0
    for code, expected in sorted(reference.items()):
        if any(value is None for value in expected.values()):
            unpriced.append(code)
            continue
        if code not in latest_rows:
            mismatches.append({"thscode": code, "field": "latest_bar", "reason": "MISSING"})
            continue
        checked += 1
        for actual_field, reference_field in (("close_price", "last_price"), ("turnover", "turnover")):
            actual = latest_rows[code][actual_field]
            if actual != expected[reference_field]:
                mismatches.append({"thscode": code, "field": actual_field,
                                   "dump": actual, "reference": expected[reference_field]})
        if code not in previous_rows:
            mismatches.append({"thscode": code, "field": "previous_bar", "reason": "MISSING_OR_NEW_LISTING_REQUIRES_REVIEW"})
        elif previous_rows[code]["close_price"] != expected["prev_price"]:
            mismatches.append({"thscode": code, "field": "raw_previous_close",
                               "dump": previous_rows[code]["close_price"], "reference": expected["prev_price"],
                               "reason": "CORPORATE_ACTION_OR_PRICE_CONVENTION_RECONCILIATION_REQUIRED"})

    missing_sessions = [day for day in sessions if not by_session[day]]
    payload = {
        "schema_version": 1, "semantics": SEMANTICS,
        "inspection_status": "DIFFERENCES_REQUIRE_REVIEW" if mismatches or missing_sessions else "CHECKED_FIELDS_MATCH",
        "production_qualification": "NOT_ESTABLISHED",
        "input_authenticity": "NOT_ESTABLISHED_BY_LOCAL_HASHES",
        "expected_sessions": sessions,
        "reference_universe_hash": canonical_hash(sorted(universe)),
        "reference_snapshot_hash": canonical_hash({"market_session": latest, "points_by_code": reference}),
        "row_count": row_count, "identity_count": len(identities), "zero_volume_rows": zero_volume_rows,
        "session_counts": [{"session": day, "rows": len(by_session[day])} for day in sessions],
        "missing_sessions": missing_sessions,
        "current_universe_missing_latest_bar": sorted(set(universe) - set(latest_rows)),
        "dump_identities_outside_current_universe": sorted(identities - set(universe)),
        "current_universe_missing_reference": sorted(set(universe) - set(reference)),
        "unpriced_reference_identities": unpriced,
        "checked_priced_latest_identities": checked, "reference_mismatches": mismatches,
        "not_established": ["ACCOUNT_ENTITLEMENT", "CONTINUOUS_DOWNLOAD_HEALTH", "VINTAGE_AND_REVISION_POLICY",
                            "DELISTING_AND_SUSPENSION_COVERAGE", "CORPORATE_ACTION_PIT", "HISTORICAL_MEMBERSHIP"],
        "market_state_writes": 0, "events_created": 0,
        "research_authority": "NONE", "human_attention_authority": "NONE", "investment_authority": "NONE",
    }
    payload["inspection_hash"] = canonical_hash(payload)
    return json.loads(canonical_json(payload))


def _file_hash(path: Path, limit: int) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise DumpInspectionError("input is not a bounded regular local file")
    digest, count = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            count += len(chunk)
            if count > limit:
                raise DumpInspectionError("input grew beyond the operations byte budget")
            digest.update(chunk)
    return digest.hexdigest()


def parquet_rows(path: Path):
    """Optional isolated reader; no installation, network or production import."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise DumpInspectionError("PYARROW_UNAVAILABLE: use a separately reviewed research environment") from exc
    with path.open("rb") as stream:
        parquet = pq.ParquetFile(stream)
        if set(parquet.schema_arrow.names) != COLUMNS or len(parquet.schema_arrow.names) != len(COLUMNS):
            raise DumpInspectionError("Parquet columns disagree with daily-k contract")
        if parquet.metadata.num_rows > MAX_ROWS:
            raise DumpInspectionError("Parquet metadata exceeds the operations row budget")
        for batch in parquet.iter_batches(batch_size=4096):
            yield from batch.to_pylist()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inspect an already obtained daily-k-10d file; never download or publish market state.")
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--sessions", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    paths = [args.parquet, args.sessions, args.universe, args.snapshot]
    if args.output.exists() or args.output.resolve() in {path.resolve() for path in paths}:
        parser.error("output must be a new file, not an input")
    try:
        hashes = [_file_hash(path, MAX_FILE_BYTES if index == 0 else MAX_METADATA_BYTES) for index, path in enumerate(paths)]
        sessions = [date.fromisoformat(value) for value in json.loads(args.sessions.read_text(encoding="utf-8"))]
        if len(sessions) != 10:
            raise DumpInspectionError("this first CLI slice requires exactly ten independently qualified sessions")
        report = inspect_daily_k_rows(parquet_rows(args.parquet), expected_sessions=sessions,
            current_universe=json.loads(args.universe.read_text(encoding="utf-8")),
            reference_snapshot=json.loads(args.snapshot.read_text(encoding="utf-8")))
        if hashes != [_file_hash(path, MAX_FILE_BYTES if index == 0 else MAX_METADATA_BYTES) for index, path in enumerate(paths)]:
            raise DumpInspectionError("input bytes changed during inspection")
        payload = {"input_file_sha256": dict(zip(("parquet", "sessions", "universe", "snapshot"), hashes)), "inspection": report}
        payload["report_hash"] = canonical_hash(payload)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"Dump inspection unavailable: {exc}\n")
    print(f"{report['inspection_status']}; production qualification = NOT_ESTABLISHED")
    return 0 if report["inspection_status"] == "CHECKED_FIELDS_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
