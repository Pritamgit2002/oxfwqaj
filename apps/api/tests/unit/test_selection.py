from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import utc
from windsight.domain import ForecastPoint
from windsight.services.selection import (
    decision_time,
    delivery_bounds,
    latest_per_target,
    select_run_at,
)

LONDON = ZoneInfo("Europe/London")


def test_decision_time_is_previous_day_local_cutoff() -> None:
    assert decision_time(date(2026, 1, 15), time(9, 0), LONDON) == utc(2026, 1, 14, 9, 0)
    # BST: 09:00 local is 08:00 UTC
    assert decision_time(date(2026, 7, 2), time(9, 0), LONDON) == utc(2026, 7, 1, 8, 0)


def test_delivery_bounds_handle_clock_change() -> None:
    start, end = delivery_bounds(date(2026, 3, 29), LONDON)  # spring forward: 23h day
    assert end - start == timedelta(hours=23)


def test_select_run_at_ignores_runs_published_after_cutoff() -> None:
    target = utc(2026, 1, 15, 12)
    points = [
        ForecastPoint(utc(2026, 1, 14, 4, 30), target, 1.0),
        ForecastPoint(utc(2026, 1, 14, 7, 30), target, 2.0),
        ForecastPoint(utc(2026, 1, 14, 9, 30), target, 3.0),
    ]
    run = select_run_at(points, utc(2026, 1, 14, 9, 0))
    assert [p.generation_mw for p in run] == [2.0]
    assert select_run_at(points, utc(2026, 1, 13)) == []


def test_latest_per_target_respects_minimum_horizon() -> None:
    target = utc(2026, 1, 15, 12)
    points = [
        ForecastPoint(target - timedelta(hours=30), target, 1.0),
        ForecastPoint(target - timedelta(hours=10), target, 2.0),
        ForecastPoint(target - timedelta(hours=2), target, 3.0),
    ]
    assert latest_per_target(points, timedelta(hours=4))[target].generation_mw == 2.0
    assert latest_per_target(points, timedelta(hours=24))[target].generation_mw == 1.0
    assert target not in latest_per_target(points, timedelta(hours=48))


def test_delivery_bounds_autumn_clock_change_and_summer_offset() -> None:
    start, end = delivery_bounds(date(2026, 10, 25), LONDON)  # fall back: 25h day
    assert end - start == timedelta(hours=25)
    start, _ = delivery_bounds(date(2026, 7, 1), LONDON)
    assert start == utc(2026, 6, 30, 23)


def test_decision_time_crosses_month_boundary() -> None:
    assert decision_time(date(2026, 2, 1), time(9, 0), LONDON) == utc(2026, 1, 31, 9, 0)


def test_select_run_at_includes_run_published_exactly_at_cutoff_and_sorts() -> None:
    cutoff = utc(2026, 1, 14, 9)
    points = [
        ForecastPoint(cutoff, utc(2026, 1, 15, 1), 2.0),
        ForecastPoint(cutoff, utc(2026, 1, 15, 0), 1.0),
    ]
    run = select_run_at(points, cutoff)
    assert [p.start_time for p in run] == [utc(2026, 1, 15, 0), utc(2026, 1, 15, 1)]


def test_latest_per_target_boundary_is_inclusive() -> None:
    target = utc(2026, 1, 15, 12)
    point = ForecastPoint(target - timedelta(hours=24), target, 1.0)
    assert target in latest_per_target([point], timedelta(hours=24))
