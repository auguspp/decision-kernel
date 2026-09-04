from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from typing import Callable, Mapping, Sequence


SECTOR_RADAR_FORMULA_VERSION = "sector-rs-5-20-60-persistence126-v0"
SECTOR_RADAR_SEMANTICS = "PRICE_PATH_DISCOVERY_OBSERVATION_ONLY"
SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY = "NONE"
SECTOR_RADAR_INVESTMENT_AUTHORITY = "NONE"
SECTOR_RADAR_HORIZONS = (5, 20, 60)
SECTOR_RADAR_MAX_WINDOW_SESSIONS = 126
SECTOR_RADAR_TOP_QUARTILE_MIN_RATING = 75


@dataclass(frozen=True)
class SectorPricePoint:
    """One completed-session sector or benchmark market observation."""

    session: date
    close: Decimal
    turnover: Decimal


@dataclass(frozen=True)
class SectorPriceSeries:
    """One explicit index identity and its ordered completed-session observations."""

    thscode: str
    name: str
    points: tuple[SectorPricePoint, ...]


@dataclass(frozen=True)
class SectorHorizonObservation:
    """One visible horizon without collapsing it into an opportunity score."""

    sessions: int
    sector_return: Decimal
    benchmark_return: Decimal
    excess_return: Decimal
    cross_sectional_rank: Decimal
    cross_sectional_rating: int


@dataclass(frozen=True)
class SectorRadarObservation:
    """Auditable sector path observations at one frozen market session."""

    thscode: str
    name: str
    as_of_session: date
    history_session_count: int
    horizon_5: SectorHorizonObservation
    horizon_20: SectorHorizonObservation
    horizon_60: SectorHorizonObservation
    rank_change_5_sessions_20d: Decimal
    excess_acceleration_5_sessions_20d: Decimal
    positive_20d_excess_persistence_sessions: int
    positive_20d_excess_run_started: date | None
    positive_20d_excess_persistence_left_censored: bool
    top_quartile_20d_persistence_sessions: int
    top_quartile_20d_run_started: date | None
    top_quartile_20d_persistence_left_censored: bool
    turnover_pulse_5_vs_prior_20: Decimal | None


@dataclass(frozen=True)
class SectorRadarExclusion:
    """Visible coverage failure for one requested sector identity."""

    thscode: str
    name: str
    reason: str


@dataclass(frozen=True)
class SectorRadarSnapshot:
    """One pure-calculation Sector Discovery Radar snapshot.

    This is a Harness observation contract. It does not classify a Research route,
    create a Human wake, change Fundamental Belief, recommend, or act.
    """

    formula_version: str
    as_of_session: date
    benchmark_thscode: str
    benchmark_name: str
    history_window_start: date
    history_window_end: date
    observations: tuple[SectorRadarObservation, ...]
    exclusions: tuple[SectorRadarExclusion, ...]
    radar_semantics: str = SECTOR_RADAR_SEMANTICS
    human_attention_authority: str = SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY
    investment_authority: str = SECTOR_RADAR_INVESTMENT_AUTHORITY


@dataclass(frozen=True)
class _CrossSection:
    rank_by_thscode: Mapping[str, Decimal]
    rating_by_thscode: Mapping[str, int]


def _validate_series(series: SectorPriceSeries) -> None:
    if not series.thscode.strip():
        raise ValueError("sector series thscode must not be empty")
    if not series.name.strip():
        raise ValueError("sector series name must not be empty")
    if not series.points:
        raise ValueError("sector series must contain completed-session points")

    sessions = tuple(point.session for point in series.points)
    if sessions != tuple(sorted(set(sessions))):
        raise ValueError("sector series sessions must be unique and strictly ascending")

    for point in series.points:
        if not point.close.is_finite() or point.close <= 0:
            raise ValueError("sector series close must be finite and positive")
        if not point.turnover.is_finite() or point.turnover < 0:
            raise ValueError("sector series turnover must be finite and non-negative")


def _slice_at_or_before(
    series: SectorPriceSeries,
    *,
    as_of_session: date,
) -> tuple[SectorPricePoint, ...]:
    return tuple(point for point in series.points if point.session <= as_of_session)


def _return_over(
    closes: Sequence[Decimal],
    *,
    end_index: int,
    sessions: int,
) -> Decimal:
    start_index = end_index - sessions
    if start_index < 0:
        raise ValueError(f"insufficient history for {sessions}-session return")
    return closes[end_index] / closes[start_index] - Decimal(1)


def _average(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("cannot average an empty observation set")
    return sum(values, Decimal(0)) / Decimal(len(values))


def _cross_section(values: Mapping[str, Decimal]) -> _CrossSection:
    """Return strongest-first average ranks plus bounded 1–99 ratings."""

    if len(values) < 2:
        raise ValueError("sector cross-section requires at least two observations")
    if any(not value.is_finite() for value in values.values()):
        raise ValueError("sector cross-section contains a non-finite value")

    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    size = len(ordered)
    rank_by_thscode: dict[str, Decimal] = {}
    rating_by_thscode: dict[str, int] = {}

    start = 0
    while start < size:
        end = start
        value = ordered[start][1]
        while end + 1 < size and ordered[end + 1][1] == value:
            end += 1

        ascending_start_rank = Decimal(start + 1)
        ascending_end_rank = Decimal(end + 1)
        average_ascending_rank = (
            ascending_start_rank + ascending_end_rank
        ) / Decimal(2)
        strongest_first_rank = Decimal(size + 1) - average_ascending_rank

        scaled = (
            Decimal(98)
            * (average_ascending_rank - Decimal(1))
            / Decimal(size - 1)
        )
        rating = 1 + int(
            (scaled + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR)
        )

        for index in range(start, end + 1):
            thscode = ordered[index][0]
            rank_by_thscode[thscode] = strongest_first_rank
            rating_by_thscode[thscode] = rating
        start = end + 1

    return _CrossSection(
        rank_by_thscode=rank_by_thscode,
        rating_by_thscode=rating_by_thscode,
    )


def _persistence(
    *,
    sessions: Sequence[date],
    history: Mapping[int, Mapping[str, Decimal] | Mapping[str, int]],
    thscode: str,
    condition: Callable[[Decimal | int], bool],
    first_computable_index: int,
) -> tuple[int, date | None, bool]:
    count = 0
    run_started: date | None = None
    for end_index in range(len(sessions) - 1, first_computable_index - 1, -1):
        value = history[end_index][thscode]
        if not condition(value):
            break
        count += 1
        run_started = sessions[end_index]

    left_censored = (
        count > 0
        and run_started == sessions[first_computable_index]
    )
    return count, run_started, left_censored


def calculate_sector_radar_snapshot(
    *,
    sectors: Sequence[SectorPriceSeries],
    benchmark: SectorPriceSeries,
    as_of_session: date,
) -> SectorRadarSnapshot:
    """Calculate one frozen-PIT sector observation snapshot.

    All cross-sectional ratings and persistence paths use one fixed eligible sector
    universe and the same exact completed-session calendar. Malformed or incomplete
    sectors are excluded visibly. Future points after ``as_of_session`` are ignored.
    """

    _validate_series(benchmark)
    if not sectors:
        raise ValueError("Sector Radar requires at least one requested sector")

    requested_ids = [series.thscode.strip().upper() for series in sectors]
    if len(requested_ids) != len(set(requested_ids)):
        raise ValueError("Sector Radar received duplicate requested sector identities")

    benchmark_points = _slice_at_or_before(
        benchmark,
        as_of_session=as_of_session,
    )
    if not benchmark_points or benchmark_points[-1].session != as_of_session:
        raise ValueError("benchmark does not reach the requested completed session")
    benchmark_points = benchmark_points[-SECTOR_RADAR_MAX_WINDOW_SESSIONS:]
    if len(benchmark_points) <= max(SECTOR_RADAR_HORIZONS):
        raise ValueError("benchmark has insufficient history for 60-session analysis")

    sessions = tuple(point.session for point in benchmark_points)
    benchmark_close = tuple(point.close for point in benchmark_points)
    required_session_set = set(sessions)

    eligible: dict[str, tuple[SectorPriceSeries, tuple[SectorPricePoint, ...]]] = {}
    exclusions: list[SectorRadarExclusion] = []

    for raw_series in sectors:
        thscode = raw_series.thscode.strip().upper()
        name = raw_series.name.strip()
        try:
            _validate_series(raw_series)
            available = _slice_at_or_before(
                raw_series,
                as_of_session=as_of_session,
            )
            by_session = {point.session: point for point in available}
            missing = tuple(
                session for session in sessions if session not in by_session
            )
            off_calendar = tuple(
                point.session
                for point in available
                if sessions[0] <= point.session <= sessions[-1]
                and point.session not in required_session_set
            )
            if missing:
                raise ValueError(
                    "missing required benchmark sessions: "
                    + ", ".join(session.isoformat() for session in missing[:3])
                    + ("..." if len(missing) > 3 else "")
                )
            if off_calendar:
                raise ValueError(
                    "contains off-benchmark sessions: "
                    + ", ".join(session.isoformat() for session in off_calendar[:3])
                    + ("..." if len(off_calendar) > 3 else "")
                )
            aligned = tuple(by_session[session] for session in sessions)
            eligible[thscode] = (
                SectorPriceSeries(
                    thscode=thscode,
                    name=name,
                    points=raw_series.points,
                ),
                aligned,
            )
        except ValueError as exc:
            exclusions.append(
                SectorRadarExclusion(
                    thscode=thscode,
                    name=name,
                    reason=str(exc),
                )
            )

    if len(eligible) < 2:
        raise ValueError(
            "Sector Radar requires at least two fully aligned eligible sectors"
        )

    sector_close = {
        thscode: tuple(point.close for point in aligned)
        for thscode, (_, aligned) in eligible.items()
    }
    sector_turnover = {
        thscode: tuple(point.turnover for point in aligned)
        for thscode, (_, aligned) in eligible.items()
    }

    current_index = len(sessions) - 1
    prior_index = current_index - 5

    current_excess_by_horizon: dict[int, dict[str, Decimal]] = {}
    current_cross_section_by_horizon: dict[int, _CrossSection] = {}
    benchmark_return_by_horizon: dict[int, Decimal] = {}

    for horizon in SECTOR_RADAR_HORIZONS:
        benchmark_return = _return_over(
            benchmark_close,
            end_index=current_index,
            sessions=horizon,
        )
        benchmark_return_by_horizon[horizon] = benchmark_return
        excess = {
            thscode: _return_over(
                closes,
                end_index=current_index,
                sessions=horizon,
            )
            - benchmark_return
            for thscode, closes in sector_close.items()
        }
        current_excess_by_horizon[horizon] = excess
        current_cross_section_by_horizon[horizon] = _cross_section(excess)

    historical_20d_excess: dict[int, Mapping[str, Decimal]] = {}
    historical_20d_ratings: dict[int, Mapping[str, int]] = {}
    historical_20d_ranks: dict[int, Mapping[str, Decimal]] = {}

    for end_index in range(20, current_index + 1):
        benchmark_return = _return_over(
            benchmark_close,
            end_index=end_index,
            sessions=20,
        )
        excess = {
            thscode: _return_over(
                closes,
                end_index=end_index,
                sessions=20,
            )
            - benchmark_return
            for thscode, closes in sector_close.items()
        }
        cross_section = _cross_section(excess)
        historical_20d_excess[end_index] = excess
        historical_20d_ratings[end_index] = cross_section.rating_by_thscode
        historical_20d_ranks[end_index] = cross_section.rank_by_thscode

    observations: list[SectorRadarObservation] = []
    for thscode, (identity, _) in eligible.items():
        horizons: dict[int, SectorHorizonObservation] = {}
        for horizon in SECTOR_RADAR_HORIZONS:
            sector_return = _return_over(
                sector_close[thscode],
                end_index=current_index,
                sessions=horizon,
            )
            cross_section = current_cross_section_by_horizon[horizon]
            horizons[horizon] = SectorHorizonObservation(
                sessions=horizon,
                sector_return=sector_return,
                benchmark_return=benchmark_return_by_horizon[horizon],
                excess_return=current_excess_by_horizon[horizon][thscode],
                cross_sectional_rank=cross_section.rank_by_thscode[thscode],
                cross_sectional_rating=cross_section.rating_by_thscode[thscode],
            )

        positive_count, positive_started, positive_left_censored = _persistence(
            sessions=sessions,
            history=historical_20d_excess,
            thscode=thscode,
            condition=lambda value: Decimal(value) > 0,
            first_computable_index=20,
        )
        quartile_count, quartile_started, quartile_left_censored = _persistence(
            sessions=sessions,
            history=historical_20d_ratings,
            thscode=thscode,
            condition=lambda value: int(value) >= SECTOR_RADAR_TOP_QUARTILE_MIN_RATING,
            first_computable_index=20,
        )

        recent_turnover = _average(sector_turnover[thscode][-5:])
        prior_turnover = _average(sector_turnover[thscode][-25:-5])
        turnover_pulse = (
            None
            if prior_turnover == 0
            else recent_turnover / prior_turnover
        )

        observations.append(
            SectorRadarObservation(
                thscode=thscode,
                name=identity.name,
                as_of_session=as_of_session,
                history_session_count=len(sessions),
                horizon_5=horizons[5],
                horizon_20=horizons[20],
                horizon_60=horizons[60],
                rank_change_5_sessions_20d=(
                    historical_20d_ranks[prior_index][thscode]
                    - historical_20d_ranks[current_index][thscode]
                ),
                excess_acceleration_5_sessions_20d=(
                    historical_20d_excess[current_index][thscode]
                    - historical_20d_excess[prior_index][thscode]
                ),
                positive_20d_excess_persistence_sessions=positive_count,
                positive_20d_excess_run_started=positive_started,
                positive_20d_excess_persistence_left_censored=(
                    positive_left_censored
                ),
                top_quartile_20d_persistence_sessions=quartile_count,
                top_quartile_20d_run_started=quartile_started,
                top_quartile_20d_persistence_left_censored=(
                    quartile_left_censored
                ),
                turnover_pulse_5_vs_prior_20=turnover_pulse,
            )
        )

    observations.sort(
        key=lambda observation: (
            observation.horizon_20.cross_sectional_rank,
            observation.thscode,
        )
    )
    exclusions.sort(key=lambda exclusion: (exclusion.thscode, exclusion.name))

    return SectorRadarSnapshot(
        formula_version=SECTOR_RADAR_FORMULA_VERSION,
        as_of_session=as_of_session,
        benchmark_thscode=benchmark.thscode.strip().upper(),
        benchmark_name=benchmark.name.strip(),
        history_window_start=sessions[0],
        history_window_end=sessions[-1],
        observations=tuple(observations),
        exclusions=tuple(exclusions),
    )
