from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest


SCRIPT = Path("experiments/sector_radar_current_breadth_2026_09_04.py")


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sector_radar_current_breadth_experiment",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def membership_envelope(items: list[dict]) -> dict:
    return {
        "code": 0,
        "data": {
            "timestamp": 1788518347000,
            "item": items,
        },
    }


def test_membership_is_sorted_hashed_and_duplicate_safe() -> None:
    module = load_module()
    envelope = membership_envelope(
        [
            {"thscode": "000002.SZ", "ticker": "000002", "name": "乙"},
            {"thscode": "600001.SH", "ticker": "600001", "name": "甲"},
        ]
    )
    normalized = module.normalize_membership(
        envelope,
        sector_thscode="881101.TI",
    )

    assert [item["thscode"] for item in normalized["members"]] == [
        "000002.SZ",
        "600001.SH",
    ]
    assert normalized["member_count"] == 2
    assert len(normalized["constituent_set_hash"]) == 64
    assert (
        normalized["membership_semantics"]
        == "CURRENT_CONSTITUENTS_AT_CAPTURE_ONLY"
    )

    duplicate = membership_envelope(
        [
            {"thscode": "600001.SH", "ticker": "600001", "name": "甲"},
            {"thscode": "600001.SH", "ticker": "600001", "name": "甲"},
        ]
    )
    with pytest.raises(ValueError, match="duplicate identity"):
        module.normalize_membership(duplicate, sector_thscode="881101.TI")


def test_stock_snapshot_preserves_unpriced_rows_without_inventing_returns() -> None:
    module = load_module()
    valid = module.normalize_stock_snapshot_item(
        {
            "thscode": "600001.SH",
            "ticker": "600001",
            "last_price": "11",
            "prev_price": "10",
            "price_change_ratio_pct": "10",
            "volume": "100",
            "turnover": "1000",
        }
    )
    assert valid["price_status"] == "PRICED"
    assert valid["daily_return"] == Decimal("0.1")

    unpriced = module.normalize_stock_snapshot_item(
        {
            "thscode": "600002.SH",
            "ticker": "600002",
            "last_price": None,
            "prev_price": "10",
            "price_change_ratio_pct": None,
            "volume": None,
            "turnover": None,
        }
    )
    assert unpriced["price_status"] == "UNPRICED_OR_INVALID"
    assert unpriced["daily_return"] is None


def test_breadth_calculation_is_equal_weight_and_exposes_concentration() -> None:
    module = load_module()
    members = tuple(
        {"thscode": code, "ticker": code[:6], "name": name}
        for code, name in (
            ("600001.SH", "甲"),
            ("600002.SH", "乙"),
            ("600003.SH", "丙"),
            ("600004.SH", "丁"),
        )
    )
    membership = {
        "members": members,
        "member_count": 4,
        "constituent_set_hash": "x" * 64,
        "provider_timestamp": "2026-09-04T16:00:00+08:00",
    }
    snapshot = {
        "600001.SH": {
            "thscode": "600001.SH",
            "ticker": "600001",
            "daily_return": Decimal("0.10"),
            "turnover": Decimal("100"),
            "price_status": "PRICED",
        },
        "600002.SH": {
            "thscode": "600002.SH",
            "ticker": "600002",
            "daily_return": Decimal("0.05"),
            "turnover": Decimal("300"),
            "price_status": "PRICED",
        },
        "600003.SH": {
            "thscode": "600003.SH",
            "ticker": "600003",
            "daily_return": Decimal("-0.05"),
            "turnover": Decimal("200"),
            "price_status": "PRICED",
        },
        "600004.SH": {
            "thscode": "600004.SH",
            "ticker": "600004",
            "daily_return": Decimal("0"),
            "turnover": Decimal("400"),
            "price_status": "PRICED",
        },
    }

    result = module.breadth_observation(
        sector_thscode="881101.TI",
        sector_name="测试行业",
        rationale="TEST",
        membership=membership,
        stock_snapshot_by_code=snapshot,
        index_daily_return=Decimal("0.03"),
    )

    assert result["coverage_ratio"] == Decimal("1")
    assert (result["advancers"], result["decliners"], result["unchanged"]) == (
        2,
        1,
        1,
    )
    assert result["advancer_share"] == Decimal("0.5")
    assert result["equal_weight_mean_daily_return"] == Decimal("0.025")
    assert result["equal_weight_median_daily_return"] == Decimal("0.025")
    assert result["top3_turnover_share"] == Decimal("0.9")
    assert result["top3_positive_return_mass_share"] == Decimal("1")
    assert result["historical_breadth_authority"] == "NONE"
    assert result["index_contribution_authority"] == "NONE"
    assert result["investment_authority"] == "NONE"


def test_pairwise_overlap_exposes_parent_child_containment() -> None:
    module = load_module()
    memberships = {
        "881100.TI": {
            "members": (
                {"thscode": "600001.SH"},
                {"thscode": "600002.SH"},
                {"thscode": "600003.SH"},
            )
        },
        "884100.TI": {
            "members": (
                {"thscode": "600001.SH"},
                {"thscode": "600002.SH"},
            )
        },
        "884200.TI": {"members": ({"thscode": "600004.SH"},)},
    }
    names = {
        "881100.TI": "父行业",
        "884100.TI": "子行业",
        "884200.TI": "无关行业",
    }

    overlaps = module.pairwise_overlaps(memberships, names)
    strongest = overlaps[0]
    assert {strongest["left_thscode"], strongest["right_thscode"]} == {
        "881100.TI",
        "884100.TI",
    }
    assert strongest["intersection_count"] == 2
    assert strongest["jaccard"] == Decimal("2") / Decimal("3")
    assert strongest["smaller_set_containment"] == Decimal("1")
    assert strongest["overlap_semantics"] == "CURRENT_CONSTITUENT_SET_OVERLAP_ONLY"


def test_experiment_contract_contains_no_recommendation_or_action_authority() -> None:
    module = load_module()
    serialized = json.dumps(
        {
            "finalists": module.FINALISTS,
            "breadth_semantics": "CURRENT_CONSTITUENT_EQUAL_WEIGHT_PROXY_ONLY",
            "human_attention_authority": "NONE",
            "investment_authority": "NONE",
        },
        ensure_ascii=False,
    ).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "action" not in serialized
