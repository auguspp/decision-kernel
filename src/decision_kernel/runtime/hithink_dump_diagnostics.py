"""Read-only field triage of an existing hashed offline dump inspection.

This is not another quote loader, adjustment engine, or acceptance gate. It reuses
an existing inspection and keeps its result unchanged. No input price is rounded,
no missing identity is excluded, and a small difference is not declared valid.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json


MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_DIAGNOSTICS = 100_000
CODE = re.compile(r"[0-9]{6}\.(?:SH|SZ|BJ)")
HASH = re.compile(r"[0-9a-f]{64}")
FIELDS = ("close_price", "turnover", "raw_previous_close")
GAPS = ("latest_bar", "previous_bar")
SEMANTICS = "READ_ONLY_FIELD_DIAGNOSTICS_NOT_DATA_ACCEPTANCE"
INPUT_SEMANTICS = "OFFLINE_DUMP_INTEGRITY_STUDY_NOT_MARKET_STATE_OR_SIGNAL_AUTHORITY"


def _hashed(value: Any, key: str) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get(key), str):
        raise ValueError(f"object with {key} required")
    body = {name: item for name, item in value.items() if name != key}
    if canonical_hash(body) != value[key]:
        raise ValueError(f"{key} mismatch")
    return body


def _code(value: Any) -> str:
    if not isinstance(value, str) or CODE.fullmatch(value) is None:
        raise ValueError("exact A-share code required")
    return value


def _codes(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_DIAGNOSTICS:
        raise ValueError("bounded identity list required")
    normalized = [_code(code) for code in value]
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate coverage identity")
    return sorted(normalized)


def _number(value: Any) -> Decimal:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError("bounded decimal string required")
    number = Decimal(value)
    if not number.is_finite() or number < 0 or abs(number.adjusted()) > 128:
        raise ValueError("finite nonnegative decimal required")
    return number


def _count(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError("bounded nonnegative count required")
    return value


def _distribution(rows: list[dict]) -> dict:
    if not rows:
        return {"count": 0, "sum_absolute_delta": "0", "nearest_rank": {}}
    values = sorted(_number(row["absolute_delta"]) for row in rows)
    ranks = {str(p): format(values[(len(values) * p + 99) // 100 - 1], "f")
             for p in (50, 95, 99, 100)}
    return {"count": len(values), "minimum_absolute_delta": format(values[0], "f"),
            "sum_absolute_delta": format(sum(values, Decimal(0)), "f"),
            "nearest_rank": ranks}


def diagnose_inspection_report(report: dict) -> dict:
    """Separate price, amount, base-price and coverage questions, never approve."""
    outer = _hashed(report, "report_hash")
    if set(outer) != {"input_file_sha256", "inspection"}:
        raise ValueError("expected the existing offline-inspection report")
    file_hashes = outer["input_file_sha256"]
    if (not isinstance(file_hashes, dict)
            or set(file_hashes) != {"parquet", "sessions", "universe", "snapshot"}
            or any(not isinstance(h, str) or HASH.fullmatch(h) is None
                   for h in file_hashes.values())):
        raise ValueError("four original input file hashes required")
    source = _hashed(outer["inspection"], "inspection_hash")
    if type(source.get("schema_version")) is not int or source["schema_version"] != 1 or source.get("semantics") != INPUT_SEMANTICS:
        raise ValueError("unsupported inspection schema or semantics")
    if source.get("inspection_status") not in {
        "CHECKED_FIELDS_MATCH", "DIFFERENCES_REQUIRE_REVIEW", "INCOMPLETE_REFERENCE_COVERAGE"
    } or source.get("production_qualification") != "NOT_ESTABLISHED":
        raise ValueError("unsupported inspection disposition")
    for name in ("human_attention_authority", "research_authority", "investment_authority"):
        if source.get(name) != "NONE":
            raise ValueError("inspection authority must remain NONE")
    for name in ("market_state_writes", "events_created"):
        if type(source.get(name)) is not int or source[name] != 0:
            raise ValueError("inspection must not write production state or events")
    checked = _count(source.get("checked_priced_latest_identities"))
    diagnostics = source.get("reference_mismatches")
    if not isinstance(diagnostics, list) or len(diagnostics) > MAX_DIAGNOSTICS:
        raise ValueError("bounded mismatch list required")
    fields: dict[str, list[dict]] = {name: [] for name in FIELDS}
    gaps: dict[str, list[dict]] = {name: [] for name in GAPS}
    seen: set[tuple[str, str]] = set()
    with localcontext() as ctx:
        ctx.prec = 300  # exact subtraction of bounded source strings; not a tolerance
        for item in diagnostics:
            if not isinstance(item, dict):
                raise ValueError("mismatch object required")
            code, field = _code(item.get("thscode")), item.get("field")
            if field not in (*FIELDS, *GAPS) or (code, field) in seen:
                raise ValueError("unknown or duplicate field diagnostic")
            seen.add((code, field))
            if field in GAPS:
                if set(item) != {"thscode", "field", "reason"} or not isinstance(item["reason"], str):
                    raise ValueError("exact missing-bar diagnostic required")
                gaps[field].append(dict(item))
                continue
            expected = {"thscode", "field", "dump", "reference"}
            if field == "raw_previous_close":
                expected.add("reason")
                if item.get("reason") != "CORPORATE_ACTION_OR_PRICE_CONVENTION_RECONCILIATION_REQUIRED":
                    raise ValueError("raw previous-close review reason required")
            if set(item) != expected:
                raise ValueError("exact numeric diagnostic required")
            dump, reference = _number(item["dump"]), _number(item["reference"])
            if field != "turnover" and (dump <= 0 or reference <= 0):
                raise ValueError("prices must be positive")
            if dump == reference:
                raise ValueError("equal values are not a mismatch")
            delta = reference - dump
            fields[field].append({**item, "reference_minus_dump": format(delta, "f"),
                                  "absolute_delta": format(abs(delta), "f")})
        summaries = {}
        for field, rows in fields.items():
            rows.sort(key=lambda row: (-_number(row["absolute_delta"]), row["thscode"]))
            missing = len(gaps["previous_bar"]) if field == "raw_previous_close" else 0
            matches = checked - len(rows) - missing
            if matches < 0:
                raise ValueError("diagnostics exceed checked denominator")
            summaries[field] = {
                "checked_latest_denominator": checked, "exact_matches": matches,
                "numeric_differences": len(rows), "missing_comparison_bar": missing,
                "distribution_of_differences": _distribution(rows),
                "largest_difference": rows[0] if rows else None,
                "remaining_after_largest_descriptive_only": _distribution(rows[1:]),
                "all_differences": rows,
            }
    for items in gaps.values():
        items.sort(key=lambda row: row["thscode"])
    coverage = {name: _codes(source.get(name)) for name in (
        "current_universe_missing_latest_bar", "current_universe_missing_reference",
        "unpriced_reference_identities", "dump_identities_outside_current_universe"
    )}
    missing_latest = set(coverage["current_universe_missing_latest_bar"])
    unpriced = set(coverage["unpriced_reference_identities"])
    coverage["missing_latest_and_unpriced_overlap"] = sorted(missing_latest & unpriced)
    coverage["missing_latest_or_unpriced_union"] = sorted(missing_latest | unpriced)
    if source["inspection_status"] == "CHECKED_FIELDS_MATCH" and (
        diagnostics or any(coverage.values()) or source.get("missing_sessions")
    ):
        raise ValueError("matching status conflicts with retained gaps or differences")
    result = {
        "schema_version": 1, "semantics": SEMANTICS,
        "source_report_hash": report["report_hash"],
        "source_inspection_hash": outer["inspection"]["inspection_hash"],
        "input_file_sha256": dict(file_hashes),
        "source_inspection_status": source["inspection_status"],
        "source_input_authenticity": source.get("input_authenticity"),
        "production_qualification": "NOT_ESTABLISHED",
        "field_summaries": summaries, "bar_gaps": gaps, "coverage": coverage,
        "diagnostic_entries": len(diagnostics),
        "distinct_diagnostic_identities": len({code for code, _ in seen}),
        "counts_are_not_disjoint_stock_counts": True,
        "cause_classification": "NOT_ESTABLISHED_BY_NUMERIC_PATTERN",
        "tolerance_added": False, "identities_excluded": [],
        "human_attention_authority": "NONE", "research_authority": "NONE",
        "investment_authority": "NONE", "market_state_writes": 0, "events_created": 0,
    }
    result["diagnostics_hash"] = canonical_hash(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.is_symlink() or args.report.stat().st_size > MAX_REPORT_BYTES:
        parser.error("bounded regular offline report required")
    if "decision-state" in args.output.resolve().parts:
        parser.error("diagnostics output must remain outside production state")
    raw = args.report.read_bytes()
    if len(raw) > MAX_REPORT_BYTES:
        parser.error("report byte budget exceeded")
    result = diagnose_inspection_report(json.loads(raw))
    # Exclusive creation: cannot overwrite the report, any old proof or state file.
    with args.output.open("x", encoding="utf-8") as output:
        output.write(canonical_json(result) + "\n")
    print(f"Diagnostics written; original result = {result['source_inspection_status']}; "
          "production qualification = NOT_ESTABLISHED")
    # Command success means the reading projection was built, not data approval.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
