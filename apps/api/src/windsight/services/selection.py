"""Rules for *which* forecast a trader would have had in hand at a point in time.

These are pure functions so the business rules can be unit tested without a database.
"""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from windsight.domain import ForecastPoint


def delivery_bounds(delivery_date: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC [start, end) of a local delivery day (23/25h on clock-change days)."""
    start = datetime.combine(delivery_date, time(), tz)
    end = datetime.combine(delivery_date + timedelta(days=1), time(), tz)
    return start.astimezone(UTC), end.astimezone(UTC)


def decision_time(delivery_date: date, cutoff: time, tz: ZoneInfo) -> datetime:
    """Day-ahead purchases for day D are committed on D-1 at the local cutoff."""
    return datetime.combine(delivery_date - timedelta(days=1), cutoff, tz).astimezone(UTC)


def select_run_at(forecasts: Iterable[ForecastPoint], as_of: datetime) -> list[ForecastPoint]:
    """Points of the most recent forecast run published at or before `as_of`.

    `forecasts` should already be restricted to the target window of interest; only runs
    that actually cover that window are therefore considered.
    """
    available = [f for f in forecasts if f.publish_time <= as_of]
    if not available:
        return []
    latest = max(f.publish_time for f in available)
    return sorted((f for f in available if f.publish_time == latest), key=lambda f: f.start_time)


def latest_per_target(
    forecasts: Iterable[ForecastPoint], min_horizon: timedelta
) -> dict[datetime, ForecastPoint]:
    """For each target time T, the latest forecast published no later than T - min_horizon."""
    best: dict[datetime, ForecastPoint] = {}
    for f in forecasts:
        if f.publish_time > f.start_time - min_horizon:
            continue
        current = best.get(f.start_time)
        if current is None or f.publish_time > current.publish_time:
            best[f.start_time] = f
    return best
