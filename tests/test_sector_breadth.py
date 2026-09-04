from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.runtime.sector_breadth import (
    ConstituentMarketPoint,
    SectorConstituentIdentity,
    calculate_current_membership_overlap,
    calculate_current_sector_breadth,
    normalize_sector_membership,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
SESSION = date(2026, 9, 4)
CAPTURED = datetime(2026, 9, 4, 15, 30, tzinfo=SHANGHAI)
OBSERVED = datetime(2026, 9, 4, 16, 0, tzinfo=SHANGHAI)


def member(code: str, name: str) -> SectorConstituentIdentity:
    return SectorConstituentIdentity(code, code[:6], name)


def point(
    code: str,
    last: str | None,
    previous: str | None,
    turnover: str | None,
    *,
    session: date = SESSION,
) -> ConstituentMarketPoint:
    return ConstituentMarketPoint(
        thscode=code,
        market_session=session,
        last_price=None if last is None else Decimal(last),
        prev_price=None if previous is None else Decimal(previous),
        turnover=None if turnover is None else Decimal(turnover),
    )


def test_membership_is_canonical_and_content_hashed() -> None:
    normalized = normalize_sector_membership(
        sector_thscode="881102.ti",
        sector_name=" 养殖业 ",
        captured_at=CAPTURED,
        members=(member("600002.SH", "乙"), member("000001.SZ", "甲")),
    )

    assert normalized.sector_thscode == "881102.TI"
    assert normalized.sector_name == "养殖业"
    assert [item.thscode for item in normalized.members] == [
        "000001.SZ",
        "600002.SH",
    ]
    assert len(normalized.constituent_set_hash) == 64

    reordered = normalize_sector_membership(
        sector_thscode="881102.TI",
        sector_name="养殖业",
        captured_at=CAPTURED,
        members=tuple(reversed(normalized.members)),
    )
    assert reordered.constituent_set_hash == normalized.constituent_set_hash


def test_breadth_exposes_coverage_direction_and_concentration() -> None:
    membership = normalize_sector_membership(
        sector_thscode="881102.TI",
        sector_name="养殖业",
        captured_at=CAPTURED,
        members=(
            member("600001.SH", "甲"),
            member("600002.SH", "乙"),
            member("600003.SH", "丙"),
            member("600004.SH", "丁"),
            member("600005.SH", "戊"),
        ),
    )
    observation = calculate_current_sector_breadth(
        membership=membership,
        market_session=SESSION,
        observed_at=OBSERVED,
        sector_last_price=Decimal("105"),
        sector_prev_price=Decimal("100"),
        constituent_points=(
            point("600001.SH", "11", "10", "500"),
            point("600002.SH", "10.5", "10", "300"),
            point("600003.SH", "9.5", "10", "100"),
            point("600004.SH", "10", "10", "100"),
            point("600005.SH", None, None, None),
            point("000001.SZ", "12", "10", "999"),
        ),
    )

    assert observation.member_count == 5
    assert observation.priced_member_count == 4
    assert observation.missing_or_unpriced_member_count == 1
    assert observation.coverage_ratio == Decimal("0.8")
    assert (observation.advancers, observation.decliners, observation.unchanged) == (
        2,
        1,
        1,
    )
    assert observation.advancer_share == Decimal("0.5")
    assert observation.equal_weight_mean_daily_return == Decimal("0.025")
    assert observation.equal_weight_median_daily_return == Decimal("0.025")
    assert observation.index_daily_return == Decimal("0.05")
    assert observation.index_minus_equal_weight_mean == Decimal("0.025")
    assert observation.top_three_turnover_share == Decimal("0.9")
    assert observation.top_three_positive_return_mass_share == Decimal("1")
    assert [item.thscode for item in observation.leaders[:2]] == [
        "600001.SH",
        "600002.SH",
    ]
    assert [item.thscode for item in observation.missing_or_unpriced_members] == [
        "600005.SH"
    ]
    assert observation.historical_breadth_authority == "NONE"
    assert observation.index_contribution_authority == "NONE"
    assert observation.human_attention_authority == "NONE"
    assert observation.investment_authority == "NONE"


def test_breadth_fails_closed_on_temporal_or_numeric_mismatch() -> None:
    membership = normalize_sector_membership(
        sector_thscode="881101.TI",
        sector_name="种植业与林业",
        captured_at=OBSERVED + timedelta(seconds=1),
        members=(member("600001.SH", "甲"),),
    )
    with pytest.raises(ValueError, match="captured after"):
        calculate_current_sector_breadth(
            membership=membership,
            market_session=SESSION,
            observed_at=OBSERVED,
            sector_last_price=Decimal("10"),
            sector_prev_price=Decimal("9"),
            constituent_points=(point("600001.SH", "10", "9", "100"),),
        )

    valid_membership = normalize_sector_membership(
        sector_thscode="881101.TI",
        sector_name="种植业与林业",
        captured_at=CAPTURED,
        members=(member("600001.SH", "甲"),),
    )
    with pytest.raises(ValueError, match="session mismatch"):
        calculate_current_sector_breadth(
            membership=valid_membership,
            market_session=SESSION,
            observed_at=OBSERVED,
            sector_last_price=Decimal("10"),
            sector_prev_price=Decimal("9"),
            constituent_points=(
                point(
                    "600001.SH",
                    "10",
                    "9",
                    "100",
                    session=date(2026, 9, 3),
                ),
            ),
        )

    with pytest.raises(ValueError, match="must be finite"):
        calculate_current_sector_breadth(
            membership=valid_membership,
            market_session=SESSION,
            observed_at=OBSERVED,
            sector_last_price=Decimal("10"),
            sector_prev_price=Decimal("9"),
            constituent_points=(
                point("600001.SH", "NaN", "9", "100"),
            ),
        )


def test_missing_rows_are_visible_and_zero_priced_fails() -> None:
    membership = normalize_sector_membership(
        sector_thscode="884006.TI",
        sector_name="水产养殖",
        captured_at=CAPTURED,
        members=(member("600001.SH", "甲"), member("600002.SH", "乙")),
    )
    with pytest.raises(ValueError, match="at least one priced constituent"):
        calculate_current_sector_breadth(
            membership=membership,
            market_session=SESSION,
            observed_at=OBSERVED,
            sector_last_price=Decimal("10"),
            sector_prev_price=Decimal("9"),
            constituent_points=(point("600001.SH", None, None, None),),
        )


def test_current_overlap_exposes_full_parent_child_containment() -> None:
    parent = normalize_sector_membership(
        sector_thscode="881166.TI",
        sector_name="军工装备",
        captured_at=CAPTURED,
        members=(
            member("600001.SH", "甲"),
            member("600002.SH", "乙"),
            member("600003.SH", "丙"),
        ),
    )
    child = normalize_sector_membership(
        sector_thscode="884183.TI",
        sector_name="航海装备",
        captured_at=CAPTURED,
        members=(member("600001.SH", "甲"), member("600002.SH", "乙")),
    )
    overlap = calculate_current_membership_overlap(left=parent, right=child)

    assert overlap.intersection_count == 2
    assert overlap.union_count == 3
    assert overlap.jaccard == Decimal("2") / Decimal("3")
    assert overlap.smaller_set_containment == Decimal("1")
    assert overlap.left_contains_right is True
    assert overlap.right_contains_left is False
    assert overlap.historical_breadth_authority == "NONE"


def test_serialized_contract_has_no_recommendation_or_trade_authority() -> None:
    membership = normalize_sector_membership(
        sector_thscode="881102.TI",
        sector_name="养殖业",
        captured_at=CAPTURED,
        members=(member("600001.SH", "甲"),),
    )
    observation = calculate_current_sector_breadth(
        membership=membership,
        market_session=SESSION,
        observed_at=OBSERVED,
        sector_last_price=Decimal("10"),
        sector_prev_price=Decimal("9"),
        constituent_points=(point("600001.SH", "10", "9", "100"),),
    )
    serialized = repr(asdict(observation)).lower()
    assert "recommendation" not in serialized
    assert "buy" not in serialized
    assert "sell" not in serialized
    assert "portfolio" not in serialized
    assert observation.human_attention_authority == "NONE"
    assert observation.investment_authority == "NONE"
