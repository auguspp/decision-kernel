"""Selection regressions; saved_product and original validators remain mandatory."""
from copy import deepcopy
import pytest
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state import run, SHA, AT
from test_current_state_delivery import API

NOOP = "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"

def product(number, *, noop=False, session="2026-09-08", state="b"*64, ledger="c"*64):
    return {"run": run(number), "status": NOOP if noop else "APPENDED_COMPLETED_SESSION_WITH_SHADOW_CANDIDATES",
            "market_session": session, "market_state_hash": state, "event_ledger_hash": ledger,
            "candidate_count": 0 if noop else 21,
            "details": {} if noop else {"result.json": {"read_path": f"details/sector/{number}/result.json"},
                                        "summary.md": {"read_path": f"details/sector/{number}/summary.md"}}}


def setup(monkeypatch, tmp_path, products, latest=None):
    c = delivery.Collector(API(), SHA, tmp_path, now=lambda: AT)
    attempts = latest or [p["run"] for p in products]
    monkeypatch.setattr(c, "runs", lambda lane: (attempts, True))
    by_id = {p["run"]["id"]: p for p in products}
    calls = []
    def saved(lane, r):
        calls.append(r["id"])
        return deepcopy(by_id[r["id"]])
    monkeypatch.setattr(c, "saved_product", saved)
    return c, calls


def test_noop_keeps_exact_result_and_current_attempt(monkeypatch, tmp_path):
    products = [product(12, noop=True), product(11, noop=True), product(10)]
    original = deepcopy(products)
    c, calls = setup(monkeypatch, tmp_path, products)
    result = c.lane("sector")
    assert result["latest_attempt"]["id"] == 12
    assert result["latest_state_validation"]["run"]["id"] == 12
    assert result["last_qualified_result"]["run"]["id"] == 10
    assert result["last_qualified_result"]["candidate_count"] == 21
    assert result["delivery_selection"] == "SAME_SESSION_RESULT_PRESERVED_NOT_NEW_EVENT"
    assert calls == [12, 11, 10] and products == original
    assert c.api.writes == []


@pytest.mark.parametrize("field,value", [("market_state_hash", "d"*64), ("event_ledger_hash", "e"*64)])
def test_state_drift_is_not_silently_skipped(monkeypatch, tmp_path, field, value):
    prior = product(11)
    prior[field] = value
    c, calls = setup(monkeypatch, tmp_path, [product(12, noop=True), prior, product(10)])
    result = c.lane("sector")
    assert result["health"] == "LATEST_SUCCESS_INPUT_REJECTED"
    assert calls == [12, 11]
    assert result["last_qualified_result"]["run"]["id"] == 12


def test_no_cross_day_borrow_and_gap_stays_visible(monkeypatch, tmp_path):
    c, calls = setup(monkeypatch, tmp_path, [product(12, noop=True), product(11, session="2026-09-07")])
    result = c.lane("sector")
    assert result["last_qualified_result"]["run"]["id"] == 12
    assert "SAME_SESSION_RESULT_NOT_FOUND_IN_BOUNDED_QUERY" in result["gaps"]


def test_result_bearing_latest_does_not_scan(monkeypatch, tmp_path):
    c, calls = setup(monkeypatch, tmp_path, [product(12), product(11)])
    assert c.lane("sector")["last_qualified_result"]["run"]["id"] == 12
    assert calls == [12]


def test_corrupt_predecessor_stops_without_older_fallback(monkeypatch, tmp_path):
    c, _ = setup(monkeypatch, tmp_path, [product(12, noop=True), product(11), product(10)])
    calls = []
    def saved(lane, r):
        calls.append(r["id"])
        if r["id"] == 11:
            raise ValueError("archive rejected")
        return product(r["id"], noop=True)
    monkeypatch.setattr(c, "saved_product", saved)
    result = c.lane("sector")
    assert result["health"] == "LATEST_SUCCESS_INPUT_REJECTED"
    assert calls == [12, 11]


def test_later_failure_remains_failure_with_same_day_result(monkeypatch, tmp_path):
    c, calls = setup(monkeypatch, tmp_path, [product(12, noop=True), product(11)],
                     latest=[run(13, conclusion="failure"), run(12), run(11)])
    result = c.lane("sector")
    assert result["health"] == "LATEST_ATTEMPT_FAILED"
    assert result["last_qualified_result"]["run"]["id"] == 11


def test_compatibility_change_is_only_delivery_code():
    from decision_kernel.runtime import concept_detail_compat as c
    assert {k for k in c.POST_DELIVERY_CONTINUITY_IMPLEMENTATION
            if c.POST_DELIVERY_CONTINUITY_IMPLEMENTATION[k] != c.POST_SECTOR_BACKFILL_IMPLEMENTATION[k]} == {
                "runtime/current_state.py", "runtime/current_state_delivery.py"}


@pytest.mark.parametrize("name", ["REPLAY_IMPLEMENTATION", "POST_SECTOR_BACKFILL_IMPLEMENTATION"])
def test_predecessor_detail_receipts_stay_readable(tmp_path, name):
    from decision_kernel.runtime import concept_detail_compat as c, concept_detail_capture as capture
    from test_concept_detail_supplement import execute
    from test_concept_detail_compat import seal, inventory
    root, receipt, *_ = execute(tmp_path)
    receipt = deepcopy(receipt)
    receipt["implementation"] = dict(getattr(c, name))
    seal(root, receipt)
    before = inventory(root)
    assert c.verify(root)[1] == c.PRIOR_DELIVERY
    assert inventory(root) == before
    with pytest.raises(ValueError):
        capture.verify(root)
