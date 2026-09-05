from __future__ import annotations

import pytest
from decision_kernel.runtime.hithink_dump_inspection import inspect_daily_k_rows
from test_hithink_dump_inspection import DAYS, UNIVERSE, rows, reference


@pytest.mark.parametrize("mode", ["partial", "unpriced", "all_unpriced"])
def test_incomplete_references_are_never_a_full_match(mode):
    refs = reference()
    if mode == "partial":
        refs["points"] = refs["points"][:1]
    else:
        for item in refs["points"][:1 if mode == "unpriced" else 2]:
            item["last_price"] = None
    report = inspect_daily_k_rows(rows(), expected_sessions=DAYS,
        current_universe=UNIVERSE, reference_snapshot=refs)
    assert report["inspection_status"] == "INCOMPLETE_REFERENCE_COVERAGE"
    assert report["production_qualification"] == "NOT_ESTABLISHED"
    assert report["events_created"] == 0
