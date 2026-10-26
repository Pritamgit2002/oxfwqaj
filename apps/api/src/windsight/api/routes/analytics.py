from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from windsight.api.deps import AnalyticsDep, SettingsDep
from windsight.core.config import Settings
from windsight.schemas import analytics as out
from windsight.services.selection import delivery_bounds

router = APIRouter(prefix="/api/v1")

CutoffQuery = Annotated[
    time | None,
    Query(description="Local decision cutoff on D-1 (HH:MM). Defaults to the server setting."),
]


def _check_delivery_date(day: date, settings: Settings) -> None:
    if not settings.delivery_window_start <= day <= settings.delivery_window_end:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"delivery_date must be between {settings.delivery_window_start} "
            f"and {settings.delivery_window_end}",
        )


def _range(
    start: datetime | None, end: datetime | None, settings: Settings
) -> tuple[datetime, datetime]:
    """Validate an explicit target-time range, defaulting to the whole delivery window."""
    if start is None:
        start, _ = delivery_bounds(settings.delivery_window_start, settings.tz)
    if end is None:
        _, end = delivery_bounds(settings.delivery_window_end, settings.tz)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start/end need a UTC offset")
    if end <= start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "end must be after start")
    if end - start > timedelta(days=62):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "range is limited to 62 days")
    return start.astimezone(UTC), end.astimezone(UTC)


@router.get("/meta", response_model=out.MetaOut, tags=["meta"])
def meta(analytics: AnalyticsDep) -> out.MetaOut:
    """Pilot scope, defaults and data freshness."""
    return analytics.meta()


@router.get("/day-ahead", response_model=out.DayAheadOut, tags=["day-ahead"])
def day_ahead(
    analytics: AnalyticsDep,
    settings: SettingsDep,
    delivery_date: date,
    cutoff: CutoffQuery = None,
) -> out.DayAheadOut:
    """The forecast a buyer had at the D-1 cutoff for `delivery_date`, against what happened."""
    _check_delivery_date(delivery_date, settings)
    return analytics.day_ahead(delivery_date, cutoff or settings.default_decision_cutoff)


@router.get("/accuracy/day-ahead", response_model=out.DayAheadAccuracyOut, tags=["accuracy"])
def day_ahead_accuracy(
    analytics: AnalyticsDep, settings: SettingsDep, cutoff: CutoffQuery = None
) -> out.DayAheadAccuracyOut:
    """Error statistics of decision-time forecasts across the whole pilot window."""
    return analytics.day_ahead_accuracy(cutoff or settings.default_decision_cutoff)


@router.get("/accuracy/horizon", response_model=out.HorizonAccuracyOut, tags=["accuracy"])
def horizon_accuracy(
    analytics: AnalyticsDep,
    settings: SettingsDep,
    start: datetime | None = None,
    end: datetime | None = None,
) -> out.HorizonAccuracyOut:
    """How forecast error grows with lead time (0 to max_horizon_hours)."""
    return analytics.horizon_accuracy(*_range(start, end, settings))


@router.get("/series", response_model=out.SeriesOut, tags=["explorer"])
def series(
    analytics: AnalyticsDep,
    settings: SettingsDep,
    start: datetime | None = None,
    end: datetime | None = None,
    horizon_hours: Annotated[float, Query(ge=0, le=72)] = 24,
) -> out.SeriesOut:
    """Actuals vs the latest forecast published at least `horizon_hours` before each target."""
    return analytics.series(*_range(start, end, settings), horizon_hours)
