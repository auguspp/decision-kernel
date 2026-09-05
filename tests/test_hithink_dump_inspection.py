from __future__ import annotations

import copy
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_dump_inspection as probe

DAYS = (date(2026, 9, 3), date(2026, 9, 4))
UNIVERSE = ("600001.SH", "000001.SZ")


def row(code, day, close):
    return {"thscode": code, "currency": "CNY", "interval": "1d", "adjusted": "none",
            "date_ms": int(datetime.combine(day, time(0), tzinfo=ZoneInfo("Asia/Shanghai")).timestamp() * 1000),
            "open_price": "10", "low_price": "9", "high_price": "13", "close_price": close,
            "volume": "100", "turnover": "1000"}


def rows():
    return [row(code, day, "10" if day == DAYS[0] else "11") for code in UNIVERSE for day in DAYS]


def reference():
    return {"market_session": DAYS[-1].isoformat(), "points": [
        {"thscode": code, "last_price": "11", "prev_price": "10", "turnover": "1000"} for code in UNIVERSE]}


def inspect(data=None, **kwargs):
    return probe.inspect_daily_k_rows(rows() if data is None else data, expected_sessions=DAYS,
        current_universe=UNIVERSE, reference_snapshot=reference(), **kwargs)


def test_matching_rows_are_only_integrity_evidence():
    data = rows()
    saved = copy.deepcopy(data)
    result = inspect(data)
    assert result["inspection_status"] == "CHECKED_FIELDS_MATCH"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["row_count"] == 4
    assert result["checked_priced_latest_identities"] == 2
    assert result["current_universe_missing_latest_bar"] == []
    assert result["reference_mismatches"] == []
    assert result["market_state_writes"] == result["events_created"] == 0
    assert all(result[key] == "NONE" for key in ("research_authority", "human_attention_authority", "investment_authority"))
    claimed = result.pop("inspection_hash")
    assert canonical_hash(result) == claimed
    assert data == saved


@pytest.mark.parametrize("field,value", [
    ("thscode", "ABCDEF.XY"), ("currency", "USD"), ("interval", "1h"), ("adjusted", "qfq"),
    ("close_price", None), ("close_price", "NaN"), ("close_price", float("inf")),
    ("close_price", True), ("close_price", "-1"), ("close_price", "15"),
    ("volume", "-1"), ("date_ms", True), ("date_ms", 0),
])
def test_bad_source_rows_fail_closed(field, value):
    data = rows()
    data[0][field] = value
    with pytest.raises(probe.DumpInspectionError):
        inspect(data)


def test_duplicate_schema_and_budget_errors_do_not_upsert():
    with pytest.raises(probe.DumpInspectionError, match="duplicate"):
        inspect(rows() + [rows()[0]])
    data = rows()
    data[0]["guessed_field"] = 1
    with pytest.raises(probe.DumpInspectionError, match="schema"):
        inspect(data)
    with pytest.raises(probe.DumpInspectionError, match="budget"):
        inspect(max_rows=1)
    with pytest.raises(probe.DumpInspectionError, match="empty"):
        inspect([])


def test_missing_fields_and_price_differences_are_explicit():
    data = rows()
    data[-1]["close_price"] = "12"
    result = inspect(data)
    assert result["inspection_status"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["reference_mismatches"][0]["field"] == "close_price"
    result = inspect(rows()[:-1])
    assert result["current_universe_missing_latest_bar"] == ["000001.SZ"]
    assert result["production_qualification"] == "NOT_ESTABLISHED"


def test_raw_previous_close_mismatch_does_not_invent_a_return_or_split():
    data = rows()
    data[0]["close_price"] = "9.5"
    result = inspect(data)
    mismatch = result["reference_mismatches"][0]
    assert mismatch["field"] == "raw_previous_close"
    assert "CORPORATE_ACTION" in mismatch["reason"]
    assert "total_return" not in result


def test_off_universe_history_and_unpriced_references_stay_visible():
    data = rows() + [row("430001.BJ", DAYS[0], "10")]
    refs = reference()
    refs["points"][0]["last_price"] = None
    result = probe.inspect_daily_k_rows(data, expected_sessions=DAYS,
        current_universe=UNIVERSE, reference_snapshot=refs)
    assert result["dump_identities_outside_current_universe"] == ["430001.BJ"]
    assert result["unpriced_reference_identities"] == ["600001.SH"]
    assert result["production_qualification"] == "NOT_ESTABLISHED"


def test_local_input_and_output_protection(tmp_path):
    data = tmp_path / "prices.parquet"
    data.write_bytes(b"PAR1 fixture")
    before = data.read_bytes()
    with pytest.raises(SystemExit):
        probe.main(["--parquet", str(data), "--sessions", str(data), "--universe", str(data),
                    "--snapshot", str(data), "--output", str(data)])
    assert data.read_bytes() == before
    link = tmp_path / "link"
    link.symlink_to(data)
    with pytest.raises(probe.DumpInspectionError):
        probe._file_hash(link, 100)
