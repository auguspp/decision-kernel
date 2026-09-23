"""Known originals cannot disappear from a claimed complete correction inventory."""
from datetime import date
from types import SimpleNamespace
import pytest
from decision_kernel.runtime import industry_question_preparation as prep


@pytest.mark.parametrize("complete", [True, False])
def test_inventory_cannot_claim_no_corrections_after_omitting_known_reports(complete):
    plan = {"updates_start": "2026-03-27", "updates_end": "2026-09-23"}
    rows = [SimpleNamespace(announcement_id="annual"), SimpleNamespace(announcement_id="interim")]
    batch = SimpleNamespace(stock_code="600362", start_date=date(2026, 3, 27), end_date=date(2026, 9, 23),
                            announcements=rows if complete else rows[:1])
    if complete:
        prep.check_inventory_window(batch, plan, "600362", {"annual", "interim"})
    else:
        with pytest.raises(ValueError, match="INDUSTRY_UPDATE_INVENTORY_INCOMPLETE"):
            prep.check_inventory_window(batch, plan, "600362", {"annual", "interim"})
