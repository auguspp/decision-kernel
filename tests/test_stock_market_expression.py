from __future__ import annotations

import copy
from decimal import Decimal

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_market_expression as market
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime.sector_radar_context import build_sector_radar_context
from test_economic_company_context import ROOT
from test_economic_market_context import NOW
from test_sector_radar_audit import prohibit_network
from test_stock_radar_reading import prepared, synthetic_references


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def _authority():
    return {"human_attention_authority": "NONE", "research_authority": "NONE",
            "investment_authority": "NONE"}


def _sector_result(state, ledger, *, groups):
    candidates = [row["candidate"] for row in groups]
    breadths = [row["breadth"] for row in groups]
    grouped = [{
        "group_key": row["group_key"],
        "primary_candidate": row["candidate"],
        "primary_breadth": row["breadth"],
        "granular_drivers": [],
        "granular_driver_breadth": [],
        "all_candidates": [row["candidate"]],
        **_authority(),
    } for row in groups]
    entries = {"previous_session": state.sessions[-2].isoformat(), "candidates": candidates, **_authority()}
    empty = {"previous_session": state.sessions[-2].isoformat(), "candidates": [], **_authority()}
    composition = {
        "all_candidates": candidates,
        "all_groups": grouped,
        "surfaced_groups": grouped,
        "omitted_groups": [],
        "truncated_group_count": 0,
        "as_of_session": state.sessions[-1].isoformat(),
        **_authority(),
    }
    value = {
        "market_session": state.sessions[-1].isoformat(),
        "produced_at": NOW.isoformat(),
        "output_market_state_hash": state.state_hash,
        "event_ledger_update": {"event_ledger_hash": ledger.ledger_hash},
        "broad_entries": entries,
        "granular_entries": empty,
        "breadth_observations": breadths,
        "composition": composition,
        **_authority(),
    }
    value["result_hash"] = canonical_hash(value)
    return value


def _active_rows(state, ledger):
    context = build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=NOW)
    rows = []
    for universe in context["universes"]:
        for row in universe["rows"]:
            if row["currently_gate_active"]:
                rows.append((universe["family"], row))
    return rows


def _group(state, family, direction, *, leaders, suffix=""):
    observation = direction["observation"]
    candidate = {
        "thscode": observation["thscode"],
        "name": observation["name"],
        "family": family,
        "as_of_session": state.sessions[-1].isoformat(),
    }
    breadth = {
        "market_session": state.sessions[-1].isoformat(),
        "sector_thscode": observation["thscode"],
        "leaders": leaders,
        **_authority(),
    }
    return {"group_key": observation["thscode"] + suffix, "candidate": candidate, "breadth": breadth}


def _leader(code: str, name: str):
    return {"thscode": code, "ticker": code[:6], "name": name,
            "daily_return": "0.10", "turnover": "1000000"}


def _one_unknown_plan():
    state, ledger, association, legacy, response, calls = prepared()
    family_by_code = {row["observation"]["thscode"]: family for family, row in _active_rows(state, ledger)}
    sector = next(iter(legacy["directions"]))
    result = _sector_result(state, ledger, groups=[_group(
        state, family_by_code[sector], legacy["directions"][sector],
        leaders=[_leader("600999.SH", "Unreviewed member")],
    )])
    plan = market.prepare_market_expression_reading(
        ROOT, state, ledger, association, result, observed_at=NOW)
    return state, ledger, association, plan, response, calls, result


def test_unreviewed_business_link_can_be_market_expression_candidate_and_observed():
    state, _, _, plan, response, calls, _ = _one_unknown_plan()
    assert [row["thscode"] for row in plan["issuers"]] == ["600999.SH"]
    issuer = plan["issuers"][0]
    assert issuer["business_linkage_status"] == "UNKNOWN"
    assert issuer["business_benefit_status"] == "NOT_ESTABLISHED"
    assert plan["candidate_routing"]["business_evidence_is_candidate_gate"] is False
    assert plan["maximum_request_count"] <= stock.MAX_REQUESTS

    refs = synthetic_references(state, ["600999.SH"])
    report = stock.observe_stock_reading(
        plan, state, request_json=response, observed_at=NOW, reference_inputs=refs)
    projection = report["projection"]
    surfaced = {row["thscode"]: row for row in projection["surfaced_stocks"]}
    assert "600999.SH" in surfaced
    row = surfaced["600999.SH"]
    assert row["market_expression_status"] == "OBSERVED"
    assert row["business_linkage_status"] == "UNKNOWN"
    assert row["business_benefit_status"] == "NOT_ESTABLISHED"
    assert projection["business_benefit_established"] is False
    assert projection["recommendation"] is None
    assert projection["automatic_research_routing"] is False
    html = market.render_market_expression_reading(report)
    assert "Market Expression = OBSERVED" in html
    assert "Business Link = UNKNOWN" in html
    assert len(calls) <= plan["maximum_request_count"] <= 26


def test_membership_alone_does_not_create_observed_market_expression():
    state, _, _, plan, response, _, _ = _one_unknown_plan()

    def falling(path, params):
        result = response(path, params)
        if path == stock.STOCK_HISTORY:
            for i, row in enumerate(result["data"]["item"]):
                row["close_price"] = str(Decimal(100) - i)
        return result

    refs = synthetic_references(state, ["600999.SH"], kind="falling")
    report = stock.observe_stock_reading(
        plan, state, request_json=falling, observed_at=NOW, reference_inputs=refs)
    p = report["projection"]
    assert p["surfaced_stocks"] == []
    row = p["all_stock_observations"][0]
    assert row["market_expression_status"] == "NOT_ESTABLISHED"
    assert row["business_linkage_status"] == "UNKNOWN"
    assert row["excluded_reasons"]
    assert p["status"] == "NO_MATCH_WITHIN_BOUNDED_MARKET_EXPRESSION_SCOPE"


def test_reviewed_business_link_is_annotation_not_benefit_claim():
    state, ledger, association, legacy, response, _, = prepared()
    reviewed = legacy["issuers"][0]
    origin = reviewed["origins"][0]
    sector = origin["sector_codes"][0]
    family_by_code = {row["observation"]["thscode"]: family for family, row in _active_rows(state, ledger)}
    result = _sector_result(state, ledger, groups=[_group(
        state, family_by_code[sector], legacy["directions"][sector],
        leaders=[_leader(reviewed["thscode"], reviewed["company_name"])],
    )])
    plan = market.prepare_market_expression_reading(
        ROOT, state, ledger, association, result, observed_at=NOW)
    issuer = plan["issuers"][0]
    assert issuer["business_linkage_status"] == "REVIEWED_BUSINESS_LINK_PRESENT"
    assert issuer["business_benefit_status"] == "NOT_ESTABLISHED"
    assert issuer["origins"][0]["company"] is not None


def test_three_surfaced_groups_are_bounded_without_raising_request_ceiling():
    state, ledger, association, _, _, _ = prepared()
    active = _active_rows(state, ledger)[:3]
    assert len(active) == 3
    groups = []
    for group_index, (family, direction) in enumerate(active):
        leaders = [_leader(f"60{group_index}{rank:03d}.SH", f"candidate-{group_index}-{rank}")
                   for rank in range(5)]
        groups.append(_group(state, family, direction, leaders=leaders))
    result = _sector_result(state, ledger, groups=groups)
    plan = market.prepare_market_expression_reading(
        ROOT, state, ledger, association, result, observed_at=NOW)
    assert len(plan["issuers"]) == 6
    assert len(plan["directions"]) == 3
    assert plan["maximum_request_count"] == 25
    assert plan["maximum_request_count"] <= stock.MAX_REQUESTS == 26
    # Round-robin over the three surfaced groups, not ticker sorting.
    assert plan["candidate_routing"]["candidate_codes"] == [
        "600000.SH", "601000.SH", "602000.SH", "600001.SH", "601001.SH", "602001.SH"]


def test_sector_result_tamper_fails_closed_before_stock_requests():
    state, _, association, plan, _, _, result = _one_unknown_plan()
    bad = copy.deepcopy(result)
    bad["composition"]["surfaced_groups"][0]["primary_candidate"]["name"] = "tampered"
    with pytest.raises(ValueError, match="hash"):
        market.prepare_market_expression_reading(
            ROOT, state, _one_unknown_plan()[1], association, bad, observed_at=NOW)
