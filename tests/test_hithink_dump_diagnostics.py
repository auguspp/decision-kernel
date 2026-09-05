from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.hithink_dump_diagnostics import (
    INPUT_SEMANTICS, diagnose_inspection_report, main,
)


def seal(inspection):
    body = {k: v for k, v in inspection.items() if k != "inspection_hash"}
    body["inspection_hash"] = canonical_hash(body)
    report = {"input_file_sha256": dict.fromkeys(("parquet", "sessions", "universe", "snapshot"), "a" * 64),
              "inspection": body}
    report["report_hash"] = canonical_hash(report)
    return report


def fixture():
    # Reduced synthetic shape, not the complete frozen market report.
    return seal({"schema_version": 1, "semantics": INPUT_SEMANTICS,
        "inspection_status": "DIFFERENCES_REQUIRE_REVIEW",
        "production_qualification": "NOT_ESTABLISHED",
        "input_authenticity": "NOT_ESTABLISHED_BY_LOCAL_HASHES",
        "checked_priced_latest_identities": 5,
        "reference_mismatches": [
            {"thscode": "000001.SZ", "field": "turnover", "dump": "969948436.21", "reference": "969948440"},
            {"thscode": "920371.BJ", "field": "turnover", "dump": "49573155.51", "reference": "59885510"},
            {"thscode": "000001.SZ", "field": "raw_previous_close", "dump": "101", "reference": "100",
             "reason": "CORPORATE_ACTION_OR_PRICE_CONVENTION_RECONCILIATION_REQUIRED"},
            {"thscode": "920289.BJ", "field": "previous_bar", "reason": "MISSING_OR_NEW_LISTING_REQUIRES_REVIEW"},
        ],
        "current_universe_missing_latest_bar": ["603448.SH", "000016.SZ"],
        "current_universe_missing_reference": [],
        "unpriced_reference_identities": ["000016.SZ", "603448.SH"],
        "dump_identities_outside_current_universe": [], "missing_sessions": [],
        "human_attention_authority": "NONE", "research_authority": "NONE",
        "investment_authority": "NONE", "market_state_writes": 0, "events_created": 0})


def test_field_lanes_keep_exact_prices_distinct_from_amounts_and_gaps():
    report = fixture()
    original = copy.deepcopy(report)
    result = diagnose_inspection_report(report)
    assert report == original
    assert result["source_inspection_status"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["field_summaries"]["close_price"]["exact_matches"] == 5
    amounts = result["field_summaries"]["turnover"]
    assert amounts["exact_matches"] == 3
    assert amounts["largest_difference"]["thscode"] == "920371.BJ"
    assert amounts["largest_difference"]["absolute_delta"] == "10312354.49"
    assert amounts["remaining_after_largest_descriptive_only"]["nearest_rank"]["100"] == "3.79"
    assert len(amounts["all_differences"]) == 2  # largest was not excluded
    prior = result["field_summaries"]["raw_previous_close"]
    assert prior["exact_matches"] == 3
    assert prior["numeric_differences"] == prior["missing_comparison_bar"] == 1
    assert result["diagnostic_entries"] == 4
    assert result["distinct_diagnostic_identities"] == 3
    assert len(result["coverage"]["missing_latest_or_unpriced_union"]) == 2
    assert len(result["coverage"]["missing_latest_and_unpriced_overlap"]) == 2
    assert result["identities_excluded"] == []
    assert result["cause_classification"] == "NOT_ESTABLISHED_BY_NUMERIC_PATTERN"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["tolerance_added"] is False
    for name in ("human_attention_authority", "research_authority", "investment_authority"):
        assert result[name] == "NONE"
    assert result["market_state_writes"] == result["events_created"] == 0
    claimed = result.pop("diagnostics_hash")
    assert claimed == canonical_hash(result)


def test_arbitrarily_small_difference_is_retained_not_accepted():
    source = fixture()["inspection"]
    source["reference_mismatches"] = [{"thscode": "600001.SH", "field": "close_price",
                                         "dump": "100.000000000001", "reference": "100"}]
    result = diagnose_inspection_report(seal(source))
    row = result["field_summaries"]["close_price"]["all_differences"][0]
    assert row["reference_minus_dump"] == "-0.000000000001"
    assert result["source_inspection_status"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["field_summaries"]["close_price"]["exact_matches"] == 4


def test_output_is_stable_with_input_order_and_decimal_context():
    from decimal import localcontext
    report = fixture()
    a = diagnose_inspection_report(report)
    with localcontext() as ctx:
        ctx.prec = 6
        b = diagnose_inspection_report(report)
    assert a == b
    assert canonical_json(a) == canonical_json(diagnose_inspection_report(report))


@pytest.mark.parametrize("target", ["outer", "inner"])
def test_tampered_hash_is_rejected(target):
    report = fixture()
    if target == "outer":
        report["report_hash"] = "f" * 64
    else:
        report["inspection"]["inspection_hash"] = "f" * 64
        report["report_hash"] = canonical_hash({k: v for k, v in report.items() if k != "report_hash"})
    with pytest.raises(ValueError, match="hash mismatch"):
        diagnose_inspection_report(report)


@pytest.mark.parametrize("change", ["duplicate", "unknown_field", "equal_values", "overcount", "fake_code", "promoted", "authority", "bool_schema", "numeric_string_missing"])
def test_invalid_or_promoted_input_is_not_a_valid_reading(change):
    source = fixture()["inspection"]
    rows = source["reference_mismatches"]
    if change == "duplicate": rows.append(copy.deepcopy(rows[0]))
    if change == "unknown_field": rows[0]["field"] = "opportunity_score"
    if change == "equal_values": rows[0]["reference"] = rows[0]["dump"]
    if change == "overcount": source["checked_priced_latest_identities"] = 1
    if change == "fake_code": rows[0]["thscode"] = "ABCDEF.XY"
    if change == "promoted": source["inspection_status"] = "CHECKED_FIELDS_MATCH"
    if change == "authority": source["research_authority"] = "DEEPEN"
    if change == "bool_schema": source["schema_version"] = True
    if change == "numeric_string_missing": rows[0]["dump"] = 100
    with pytest.raises(ValueError):
        diagnose_inspection_report(seal(source))


def test_even_matching_input_is_not_promoted_to_production():
    source = fixture()["inspection"]
    source["inspection_status"] = "CHECKED_FIELDS_MATCH"
    source["reference_mismatches"] = []
    source["current_universe_missing_latest_bar"] = []
    source["unpriced_reference_identities"] = []
    result = diagnose_inspection_report(seal(source))
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["field_summaries"]["turnover"]["distribution_of_differences"]["count"] == 0


def test_command_reads_existing_report_and_cannot_overwrite(tmp_path: Path):
    source = tmp_path / "offline-inspection.json"
    source.write_text(canonical_json(fixture()), encoding="utf-8")
    before = source.read_bytes()
    target = tmp_path / "diagnostics.json"
    assert main(["--report", str(source), "--output", str(target)]) == 0
    assert json.loads(target.read_text())["source_inspection_status"] == "DIFFERENCES_REQUIRE_REVIEW"
    with pytest.raises(FileExistsError):
        main(["--report", str(source), "--output", str(source)])
    with pytest.raises(FileExistsError):
        main(["--report", str(source), "--output", str(target)])
    assert source.read_bytes() == before


def test_command_rejects_production_state_output(tmp_path: Path):
    source = tmp_path / "offline-inspection.json"
    source.write_text(canonical_json(fixture()), encoding="utf-8")
    state = tmp_path / "decision-state"
    state.mkdir()
    with pytest.raises(SystemExit):
        main(["--report", str(source), "--output", str(state / "diagnostics.json")])
    assert list(state.iterdir()) == []
