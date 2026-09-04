from __future__ import annotations

import hashlib
import json
import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence


SECTOR_BREADTH_FORMULA_VERSION = "sector-current-breadth-v0"
SECTOR_BREADTH_SEMANTICS = "CURRENT_CONSTITUENT_EQUAL_WEIGHT_PROXY_ONLY"
SECTOR_BREADTH_HISTORICAL_AUTHORITY = "NONE"
SECTOR_BREADTH_INDEX_CONTRIBUTION_AUTHORITY = "NONE"
SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_BREADTH_INVESTMENT_AUTHORITY = "NONE"

_SECTOR_THSCODE = re.compile(r"^\d{6}\.TI$")
_A_SHARE_THSCODE = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")


@dataclass(frozen=True)
class SectorConstituentIdentity:
    """One current A-share constituent identity."""

    thscode: str
    ticker: str
    name: str


@dataclass(frozen=True)
class SectorMembershipSnapshot:
    """One exact current constituent set captured at a timezone-aware instant."""

    sector_thscode: str
    sector_name: str
    captured_at: datetime
    members: tuple[SectorConstituentIdentity, ...]
    constituent_set_hash: str


@dataclass(frozen=True)
class ConstituentMarketPoint:
    """One same-session constituent snapshot row.

    Missing values remain explicitly unpriced. Present numeric values must still be
    finite and mechanically valid; the calculation never invents a return.
    """

    thscode: str
    market_session: date
    last_price: Decimal | None
    prev_price: Decimal | None
    turnover: Decimal | None


@dataclass(frozen=True)
class SectorBreadthMemberMove:
    thscode: str
    ticker: str
    name: str
    daily_return: Decimal
    turnover: Decimal


@dataclass(frozen=True)
class SectorCurrentBreadthObservation:
    """Current equal-weight breadth proxy with no historical or investment authority."""

    formula_version: str
    sector_thscode: str
    sector_name: str
    market_session: date
    observed_at: datetime
    membership_captured_at: datetime
    constituent_set_hash: str
    index_daily_return: Decimal
    member_count: int
    priced_member_count: int
    missing_or_unpriced_member_count: int
    coverage_ratio: Decimal
    advancers: int
    decliners: int
    unchanged: int
    advancer_share: Decimal
    decliner_share: Decimal
    equal_weight_mean_daily_return: Decimal
    equal_weight_median_daily_return: Decimal
    index_minus_equal_weight_mean: Decimal
    total_constituent_turnover: Decimal
    top_three_turnover_share: Decimal | None
    top_three_positive_return_mass_share: Decimal | None
    leaders: tuple[SectorBreadthMemberMove, ...]
    laggards: tuple[SectorBreadthMemberMove, ...]
    missing_or_unpriced_members: tuple[SectorConstituentIdentity, ...]
    breadth_semantics: str = SECTOR_BREADTH_SEMANTICS
    historical_breadth_authority: str = SECTOR_BREADTH_HISTORICAL_AUTHORITY
    index_contribution_authority: str = (
        SECTOR_BREADTH_INDEX_CONTRIBUTION_AUTHORITY
    )
    human_attention_authority: str = (
        SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_BREADTH_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class SectorCurrentMembershipOverlap:
    """Current set overlap only; never historical membership or index contribution."""

    left_sector_thscode: str
    left_sector_name: str
    left_member_count: int
    right_sector_thscode: str
    right_sector_name: str
    right_member_count: int
    intersection_count: int
    union_count: int
    jaccard: Decimal
    smaller_set_containment: Decimal
    left_contains_right: bool
    right_contains_left: bool
    intersection_members: tuple[str, ...]
    overlap_semantics: str = "CURRENT_CONSTITUENT_SET_OVERLAP_ONLY"
    historical_breadth_authority: str = SECTOR_BREADTH_HISTORICAL_AUTHORITY
    human_attention_authority: str = (
        SECTOR_BREADTH_HUMAN_ATTENTION_AUTHORITY
    )
    investment_authority: str = SECTOR_BREADTH_INVESTMENT_AUTHORITY


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _require_finite(
    value: Decimal,
    *,
    field: str,
    positive: bool = False,
    non_negative: bool = False,
) -> None:
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{field} must be positive")
    if non_negative and value < 0:
        raise ValueError(f"{field} must be non-negative")


def _normalize_member(
    member: SectorConstituentIdentity,
) -> SectorConstituentIdentity:
    thscode = member.thscode.strip().upper()
    ticker = member.ticker.strip()
    name = member.name.strip()
    if not _A_SHARE_THSCODE.fullmatch(thscode):
        raise ValueError("sector constituent must be a qualified A-share thscode")
    if ticker != thscode[:6]:
        raise ValueError(f"sector constituent ticker disagrees with {thscode}")
    if not name:
        raise ValueError(f"sector constituent name is empty for {thscode}")
    return SectorConstituentIdentity(
        thscode=thscode,
        ticker=ticker,
        name=name,
    )


def _membership_hash(
    *,
    sector_thscode: str,
    members: Sequence[SectorConstituentIdentity],
) -> str:
    payload = {
        "sector_thscode": sector_thscode,
        "members": [
            {
                "name": member.name,
                "thscode": member.thscode,
                "ticker": member.ticker,
            }
            for member in members
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_sector_membership(
    *,
    sector_thscode: str,
    sector_name: str,
    captured_at: datetime,
    members: Sequence[SectorConstituentIdentity],
) -> SectorMembershipSnapshot:
    """Validate, sort and hash one exact current constituent set."""

    normalized_sector = sector_thscode.strip().upper()
    normalized_name = sector_name.strip()
    if not _SECTOR_THSCODE.fullmatch(normalized_sector):
        raise ValueError("sector membership requires a six-digit .TI identity")
    if not normalized_name:
        raise ValueError("sector membership requires a non-empty name")
    _require_aware(captured_at, field="sector membership captured_at")
    if not members:
        raise ValueError("sector membership must contain at least one constituent")

    normalized_members = tuple(_normalize_member(member) for member in members)
    by_code = {member.thscode: member for member in normalized_members}
    if len(by_code) != len(normalized_members):
        raise ValueError("sector membership contains duplicate constituent identities")
    ordered = tuple(by_code[key] for key in sorted(by_code))
    return SectorMembershipSnapshot(
        sector_thscode=normalized_sector,
        sector_name=normalized_name,
        captured_at=captured_at,
        members=ordered,
        constituent_set_hash=_membership_hash(
            sector_thscode=normalized_sector,
            members=ordered,
        ),
    )


def _normalize_market_point(
    point: ConstituentMarketPoint,
) -> ConstituentMarketPoint:
    thscode = point.thscode.strip().upper()
    if not _A_SHARE_THSCODE.fullmatch(thscode):
        raise ValueError("constituent market point has an invalid A-share identity")

    for field, value in (
        ("last_price", point.last_price),
        ("prev_price", point.prev_price),
        ("turnover", point.turnover),
    ):
        if value is None:
            continue
        _require_finite(
            value,
            field=f"constituent {thscode} {field}",
            positive=field in {"last_price", "prev_price"},
            non_negative=field == "turnover",
        )

    return ConstituentMarketPoint(
        thscode=thscode,
        market_session=point.market_session,
        last_price=point.last_price,
        prev_price=point.prev_price,
        turnover=point.turnover,
    )


def _priced_return(point: ConstituentMarketPoint) -> tuple[Decimal, Decimal] | None:
    if (
        point.last_price is None
        or point.prev_price is None
        or point.turnover is None
    ):
        return None
    return point.last_price / point.prev_price - Decimal(1), point.turnover


def _average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("cannot average an empty sequence")
    return sum(values, Decimal(0)) / Decimal(len(values))


def calculate_current_sector_breadth(
    *,
    membership: SectorMembershipSnapshot,
    market_session: date,
    observed_at: datetime,
    sector_last_price: Decimal,
    sector_prev_price: Decimal,
    constituent_points: Sequence[ConstituentMarketPoint],
) -> SectorCurrentBreadthObservation:
    """Calculate one current constituent breadth observation.

    Extra market rows are allowed because callers may pass a complete same-session
    market snapshot. Missing membership rows remain visible through coverage.
    """

    _require_aware(observed_at, field="sector breadth observed_at")
    _require_aware(
        membership.captured_at,
        field="sector membership captured_at",
    )
    if membership.captured_at > observed_at:
        raise ValueError("sector membership cannot be captured after breadth observation")
    _require_finite(
        sector_last_price,
        field="sector last price",
        positive=True,
    )
    _require_finite(
        sector_prev_price,
        field="sector previous price",
        positive=True,
    )

    normalized_points = tuple(
        _normalize_market_point(point) for point in constituent_points
    )
    by_code = {point.thscode: point for point in normalized_points}
    if len(by_code) != len(normalized_points):
        raise ValueError("constituent market snapshot contains duplicate identities")
    if any(point.market_session != market_session for point in normalized_points):
        raise ValueError("constituent market snapshot contains a session mismatch")

    priced_moves: list[SectorBreadthMemberMove] = []
    missing: list[SectorConstituentIdentity] = []
    for member in membership.members:
        point = by_code.get(member.thscode)
        priced = None if point is None else _priced_return(point)
        if priced is None:
            missing.append(member)
            continue
        daily_return, turnover = priced
        priced_moves.append(
            SectorBreadthMemberMove(
                thscode=member.thscode,
                ticker=member.ticker,
                name=member.name,
                daily_return=daily_return,
                turnover=turnover,
            )
        )

    if not priced_moves:
        raise ValueError("sector breadth requires at least one priced constituent")

    returns = tuple(move.daily_return for move in priced_moves)
    turnovers = tuple(move.turnover for move in priced_moves)
    member_count = len(membership.members)
    priced_count = len(priced_moves)
    advancers = sum(value > 0 for value in returns)
    decliners = sum(value < 0 for value in returns)
    unchanged = priced_count - advancers - decliners
    equal_weight_mean = _average(returns)
    total_turnover = sum(turnovers, Decimal(0))
    positive_returns = tuple(
        sorted((value for value in returns if value > 0), reverse=True)
    )
    positive_return_mass = sum(positive_returns, Decimal(0))

    leaders = tuple(
        sorted(
            priced_moves,
            key=lambda move: (move.daily_return, move.thscode),
            reverse=True,
        )[:5]
    )
    laggards = tuple(
        sorted(
            priced_moves,
            key=lambda move: (move.daily_return, move.thscode),
        )[:5]
    )
    index_daily_return = sector_last_price / sector_prev_price - Decimal(1)

    return SectorCurrentBreadthObservation(
        formula_version=SECTOR_BREADTH_FORMULA_VERSION,
        sector_thscode=membership.sector_thscode,
        sector_name=membership.sector_name,
        market_session=market_session,
        observed_at=observed_at,
        membership_captured_at=membership.captured_at,
        constituent_set_hash=membership.constituent_set_hash,
        index_daily_return=index_daily_return,
        member_count=member_count,
        priced_member_count=priced_count,
        missing_or_unpriced_member_count=len(missing),
        coverage_ratio=Decimal(priced_count) / Decimal(member_count),
        advancers=advancers,
        decliners=decliners,
        unchanged=unchanged,
        advancer_share=Decimal(advancers) / Decimal(priced_count),
        decliner_share=Decimal(decliners) / Decimal(priced_count),
        equal_weight_mean_daily_return=equal_weight_mean,
        equal_weight_median_daily_return=statistics.median(returns),
        index_minus_equal_weight_mean=index_daily_return - equal_weight_mean,
        total_constituent_turnover=total_turnover,
        top_three_turnover_share=(
            None
            if total_turnover == 0
            else sum(sorted(turnovers, reverse=True)[:3], Decimal(0))
            / total_turnover
        ),
        top_three_positive_return_mass_share=(
            None
            if positive_return_mass == 0
            else sum(positive_returns[:3], Decimal(0)) / positive_return_mass
        ),
        leaders=leaders,
        laggards=laggards,
        missing_or_unpriced_members=tuple(missing),
    )


def calculate_current_membership_overlap(
    *,
    left: SectorMembershipSnapshot,
    right: SectorMembershipSnapshot,
) -> SectorCurrentMembershipOverlap:
    """Compare two exact current constituent sets without historical claims."""

    if left.sector_thscode == right.sector_thscode:
        raise ValueError("membership overlap requires two distinct sectors")
    left_members = {member.thscode for member in left.members}
    right_members = {member.thscode for member in right.members}
    intersection = tuple(sorted(left_members & right_members))
    union = left_members | right_members
    smaller = min(len(left_members), len(right_members))
    return SectorCurrentMembershipOverlap(
        left_sector_thscode=left.sector_thscode,
        left_sector_name=left.sector_name,
        left_member_count=len(left_members),
        right_sector_thscode=right.sector_thscode,
        right_sector_name=right.sector_name,
        right_member_count=len(right_members),
        intersection_count=len(intersection),
        union_count=len(union),
        jaccard=Decimal(len(intersection)) / Decimal(len(union)),
        smaller_set_containment=Decimal(len(intersection)) / Decimal(smaller),
        left_contains_right=right_members <= left_members,
        right_contains_left=left_members <= right_members,
        intersection_members=intersection,
    )
