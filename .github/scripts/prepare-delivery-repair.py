"""Temporary patch preparation only; no production ref, provider or dispatch writes."""
from pathlib import Path
import hashlib


def replace(path, old, new):
    p = Path(path)
    text = p.read_text()
    assert text.count(old) == 1, (path, text.count(old), old[:100])
    p.write_text(text.replace(old, new))

p = 'src/decision_kernel/runtime/current_state_delivery.py'
method = '''    def sector_result_after_validation(self, runs: list[dict], checked: dict) -> tuple[dict, dict | None]:
        """A verified same-session no-op must not erase its result-bearing predecessor.

        This is reading selection, never restore or a new event. Every inspected
        archive still passes saved_product; corruption stops, not older fallback.
        """
        noop = "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"
        if checked.get("status") != noop:
            return checked, None
        identity = ("market_session", "market_state_hash", "event_ledger_hash")
        expected = tuple(checked[key] for key in identity)
        boundary = (model.clock(checked["run"]["created_at"]), checked["run"]["id"])
        eligible = [r for r in runs if model.select_runs([r], "sector")[1] is not None]
        model.check(len(eligible) <= MAX_RUNS, "Sector delivery scan bound")
        for run in sorted(eligible, key=lambda r: (model.clock(r["created_at"]), r["id"]), reverse=True):
            if (model.clock(run["created_at"]), run["id"]) >= boundary:
                continue
            prior = self.saved_product("sector", run)
            if prior["market_session"] != checked["market_session"]:
                break  # Never carry another market day as this day's changes.
            model.check(tuple(prior[key] for key in identity) == expected,
                        "same-session Sector result/state continuity differs")
            if prior["status"] == noop:
                continue
            model.check("result.json" in prior["details"] and "summary.md" in prior["details"],
                        "result-bearing Sector delivery is incomplete")
            return prior, checked
        return checked, checked

'''
replace(p, '    def lane(self, lane: str) -> dict:\n', method + '    def lane(self, lane: str) -> dict:\n')
replace(p, '        latest, qualified, failure, query_complete = None, None, None, False\n', '        latest, qualified, failure, query_complete = None, None, None, False\n        state_validation = None\n')
replace(p, '                qualified = self.saved_product(lane, successful)\n', '                qualified = self.saved_product(lane, successful)\n                if lane == "sector":\n                    qualified, state_validation = self.sector_result_after_validation(runs, qualified)\n')
replace(p, '        result["query_scope"] = f"newest {MAX_RUNS} runs of exact workflow on main; not an all-history audit"\n', '        if state_validation is not None:\n            result["latest_state_validation"] = state_validation\n            result["delivery_selection"] = "SAME_SESSION_RESULT_PRESERVED_NOT_NEW_EVENT"\n            if qualified["run"]["id"] == state_validation["run"]["id"]:\n                result["gaps"].append("SAME_SESSION_RESULT_NOT_FOUND_IN_BOUNDED_QUERY")\n        result["query_scope"] = f"newest {MAX_RUNS} runs of exact workflow on main; not an all-history audit"\n')
replace(p, '            for name in ("summary.md", "context/index.html", "result.json"):\n', '            for name in ("summary.md", "context/index.html", "result.json", "stock-reference.json"):\n')

p = 'src/decision_kernel/runtime/current_state.py'
replace(p, '        details = sector.get("details", {})\n', '''        details = sector.get("details", {})
        validation = payload["lanes"].get("sector", {}).get("latest_state_validation")
        if validation:
            lines += ["", "最新成功运行只做同交易日状态校验；下方保留原结果及来源，不重发事件。"]
''')

p = 'src/decision_kernel/runtime/concept_detail_compat.py'
new_map = "POST_DELIVERY_CONTINUITY_IMPLEMENTATION = MappingProxyType({\n    **POST_SECTOR_BACKFILL_IMPLEMENTATION,\n"
for name in ('current_state.py', 'current_state_delivery.py'):
    digest = hashlib.sha256(Path('src/decision_kernel/runtime', name).read_bytes()).hexdigest()
    new_map += f"    'runtime/{name}': '{digest}',\n"
new_map += "})\nPRIOR_DELIVERY = 'REVIEWED_PRIOR_DELIVERY_IMPLEMENTATION'\n"
replace(p, "CURRENT = 'CURRENT_IMPLEMENTATION'\n", new_map + "CURRENT = 'CURRENT_IMPLEMENTATION'\n")
replace(p, '        historical in (HISTORICAL_IMPLEMENTATION, PRE_SINGLE_QUICK_IMPLEMENTATION)\n        and installed in (REPLAY_IMPLEMENTATION, POST_SECTOR_BACKFILL_IMPLEMENTATION),\n', '        historical in (HISTORICAL_IMPLEMENTATION, PRE_SINGLE_QUICK_IMPLEMENTATION,\n                       REPLAY_IMPLEMENTATION, POST_SECTOR_BACKFILL_IMPLEMENTATION)\n        and installed in (REPLAY_IMPLEMENTATION, POST_SECTOR_BACKFILL_IMPLEMENTATION,\n                          POST_DELIVERY_CONTINUITY_IMPLEMENTATION),\n')
replace(p, '    return verifier(output), (HISTORICAL if historical == HISTORICAL_IMPLEMENTATION else PRE_SINGLE_QUICK)\n', '''    label = (HISTORICAL if historical == HISTORICAL_IMPLEMENTATION else
             PRE_SINGLE_QUICK if historical == PRE_SINGLE_QUICK_IMPLEMENTATION else PRIOR_DELIVERY)
    return verifier(output), label
''')
for name in ('tests/test_concept_detail_compat.py', 'tests/test_single_quick_integration_regressions.py'):
    replace(name, '    assert capture._implementation() == compat.POST_SECTOR_BACKFILL_IMPLEMENTATION\n', '    assert capture._implementation() == compat.POST_DELIVERY_CONTINUITY_IMPLEMENTATION\n')

Path('tests/test_sector_delivery_continuity.py').write_text('''"""Selection regressions; saved_product and original validators remain mandatory."""
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
''')
with Path('docs/concept-detail-replay-compatibility-v1.md').open('a') as f:
    f.write('\n\n## 2026-09-25 — Same-session delivery continuity\n\nThe new installed map changes only current_state.py navigation text and current_state_delivery.py Sector result selection. Concept-detail replay does not call Collector.lane or this navigation. All historical maps remain immutable; exact prior REPLAY and POST_SECTOR_BACKFILL maps are also readable under the unchanged verifier. Unknown hashes still fail. This is saved-result reading, not new source qualification or production replay.\n')
with Path('docs/sector-radar-scheduled-production.md').open('a') as f:
    f.write('\n\n## 2026-09-25 — Reading continuity repair\n\nLatest attempt, verified same-session state check and result-bearing delivery are separate. After a verified no-op, the collector inspects only its existing bounded run page and retains the first validated predecessor with the same market session, market-state hash and event-ledger hash. Corruption stops the search; another day is never borrowed. The original result and summary are retained in the same new read-model commit, with the later validation recorded separately. This does not dispatch, replay source calls, create events or repair missing source inputs.\n')
