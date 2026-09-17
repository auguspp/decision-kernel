"""Synthetic contract tests, not provider or Research acceptance."""
from copy import deepcopy

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.radar_stock_candidates import (
    build_stock_discovery_pool, plan_stock_discovery_batch, render_stock_discovery_pool,
)


def source(groups=7, leaders=3):
    authority = {"human_attention_authority": "NONE", "research_authority": "NONE", "investment_authority": "NONE"}
    candidates, breadths, rows = [], [], []
    for i in range(groups):
        c = {"thscode": f"881{100+i:03d}.TI", "name": f"Direction {i}", "family": "BROAD_881", "as_of_session": "2026-09-17"}
        b = {"sector_thscode": c["thscode"], "market_session": "2026-09-17", "leaders": [
            {"thscode": f"60{i}{j:03d}.SH", "ticker": f"60{i}{j:03d}", "name": f"Company {i}-{j}", "daily_return": "0.01", "turnover": "100"}
            for j in range(leaders)], **authority}
        candidates.append(c)
        breadths.append(b)
        rows.append({"group_key": c["thscode"], "primary_candidate": c, "primary_breadth": b,
                     "granular_drivers": [], "granular_driver_breadth": [], "all_candidates": [c], **authority})
    r = {"market_session": "2026-09-17", "produced_at": "2026-09-17T10:00:00Z", "output_market_state_hash": "a"*64,
         "event_ledger_update": {"event_ledger_hash": "b"*64}, "breadth_observations": breadths,
         "broad_entries": {"previous_session": "2026-09-16", "candidates": candidates, **authority},
         "granular_entries": {"previous_session": "2026-09-16", "candidates": [], **authority},
         "composition": {"all_groups": rows, "surfaced_groups": rows[:3], "omitted_groups": rows[3:],
                         "truncated_group_count": max(0, groups-3), "all_candidates": candidates,
                         "as_of_session": "2026-09-17", **authority}, **authority}
    return rehash(r)


def rehash(r):
    r["result_hash"] = canonical_hash({k: v for k, v in r.items() if k != "result_hash"})
    return r


def test_all_groups_retained_independently_of_homepage_without_mutation():
    r = source()
    before = deepcopy(r)
    pool = build_stock_discovery_pool(r)
    assert pool["coverage"]["distinct_stocks"] == 21
    assert pool["coverage"]["stocks_only_outside_homepage"] == 12
    assert [c["thscode"] for c in pool["candidates"][:7]] == [f"60{i}000.SH" for i in range(7)]
    assert r == before
    assert build_stock_discovery_pool(r) == pool
    pool["candidates"][0]["origins"][0]["retained_leader"]["name"] = "changed copy"
    assert r == before


def test_secondary_driver_and_duplicate_security_keep_all_origins():
    r = source(groups=2, leaders=1)
    primary, child = r["composition"]["all_groups"]
    child["primary_candidate"]["family"] = "GRANULAR_884"
    child["primary_breadth"]["leaders"] = deepcopy(primary["primary_breadth"]["leaders"])
    primary["granular_drivers"] = [child["primary_candidate"]]
    primary["granular_driver_breadth"] = [child["primary_breadth"]]
    primary["all_candidates"].append(child["primary_candidate"])
    r["composition"]["all_groups"] = r["composition"]["surfaced_groups"] = [primary]
    pool = build_stock_discovery_pool(rehash(r))
    assert pool["coverage"]["distinct_stocks"] == 1
    assert pool["coverage"]["qualified_directions"] == 2
    assert len(pool["candidates"][0]["origins"]) == 2
    assert [o["is_primary"] for o in pool["candidates"][0]["origins"]] == [True, False]


def test_batch_pages_cover_entire_pool_with_original_cost_ceiling_and_no_execution():
    r = source()
    pool = build_stock_discovery_pool(r)
    offset, all_codes = 0, []
    while offset is not None:
        batch = plan_stock_discovery_batch(r, pool_hash=pool["pool_hash"], offset=offset)
        assert batch["maximum_request_count"] <= 26
        assert batch["maximum_request_count"] == 4 + len(batch["direction_codes"]) + 3 * len(batch["selected_codes"])
        assert len(batch["direction_codes"]) <= 6
        assert batch["execution"] == "NOT_EXECUTED"
        assert batch["prior_pages_execution"] == "NOT_ASSERTED"
        assert batch["market_requests"] == 0
        assert batch["automatic_research_routing"] is False
        assert batch["prior_page_codes"] + batch["selected_codes"] + batch["deferred_codes"] == [c["thscode"] for c in pool["candidates"]]
        all_codes.extend(batch["selected_codes"])
        offset = batch["next_offset"]
    assert len(all_codes) == len(set(all_codes)) == 21
    assert "603000.SH" in all_codes[:5]


def test_stale_pool_hash_cannot_be_reused_on_new_source():
    r = source()
    pool = build_stock_discovery_pool(r)
    r["produced_at"] = "2026-09-17T11:00:00Z"
    with pytest.raises(ValueError, match="another pool"):
        plan_stock_discovery_batch(rehash(r), pool_hash=pool["pool_hash"])


@pytest.mark.parametrize("offset", [-1, True, "0", 100])
def test_invalid_offset_is_rejected(offset):
    r = source()
    with pytest.raises(ValueError, match="offset"):
        plan_stock_discovery_batch(r, pool_hash=build_stock_discovery_pool(r)["pool_hash"], offset=offset)


@pytest.mark.parametrize("field,value", [("thscode", "600000.XX"), ("ticker", "123"), ("name", ""),
                                         ("daily_return", "NaN"), ("turnover", "-1"), ("turnover", True)])
def test_invalid_retained_leader_is_not_promoted(field, value):
    r = source()
    r["breadth_observations"][0]["leaders"][0][field] = value
    with pytest.raises(ValueError):
        build_stock_discovery_pool(rehash(r))


def test_rehashed_authority_and_wrong_session_are_rejected():
    for field, value in [("investment_authority", "BUY"), ("market_session", "2026-09-16")]:
        r = source()
        r["breadth_observations"][0][field] = value
        with pytest.raises(ValueError):
            build_stock_discovery_pool(rehash(r))


def test_hash_tamper_is_rejected():
    r = source()
    r["produced_at"] = "changed"
    with pytest.raises(ValueError, match="hash"):
        build_stock_discovery_pool(r)


def test_empty_pool_is_explicit_scope_not_market_quiet():
    r = source(groups=0)
    pool = build_stock_discovery_pool(r)
    batch = plan_stock_discovery_batch(r, pool_hash=pool["pool_hash"])
    assert batch["selected_codes"] == [] and batch["next_offset"] is None
    assert batch["maximum_request_count"] == 0
    assert "不是全市场没有" in "\n".join(render_stock_discovery_pool(r))


def test_names_are_escaped_and_unknowns_do_not_claim_research():
    r = source(groups=1, leaders=1)
    r["breadth_observations"][0]["leaders"][0]["name"] = "<script>x</script>|[fake](url)"
    text = "\n".join(render_stock_discovery_pool(rehash(r)))
    assert "<script>" not in text and "&#124;" in text
    assert "个股多日价格条件、业务受益、Research 均未由本池检查" in text
    assert "不会自动发起行情" in text


def test_same_security_conflicting_names_and_duplicate_direction_rows_fail():
    r = source(groups=2, leaders=1)
    r["breadth_observations"][1]["leaders"][0].update(thscode="600000.SH", ticker="600000")
    with pytest.raises(ValueError, match="conflicting"):
        build_stock_discovery_pool(rehash(r))
    r = source(groups=1, leaders=1)
    r["breadth_observations"][0]["leaders"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        build_stock_discovery_pool(rehash(r))
