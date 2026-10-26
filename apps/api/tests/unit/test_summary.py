"""The decision brief: headline numbers derived from the forecast run in hand."""

from datetime import timedelta

import pytest

from tests.conftest import utc
from windsight.domain import ForecastPoint
from windsight.services.analytics import _pairs, _summary
from windsight.services.calibration import Calibration

PUBLISHED = utc(2026, 1, 14, 7, 30)
DAY = utc(2026, 1, 15)


def _run(mw: list[float]) -> list[ForecastPoint]:
    return [ForecastPoint(PUBLISHED, DAY + timedelta(hours=h), v) for h, v in enumerate(mw)]


def test_summary_without_history_reports_raw_forecast_only() -> None:
    summary = _summary(_run([10_000.0] * 24), cal=None)
    assert summary is not None
    assert summary.forecast_mwh == 240_000
    assert summary.avg_mw == summary.peak_mw == 10_000
    assert summary.adjusted_mwh is None
    assert summary.firm_mwh is None


def test_summary_finds_lowest_two_hour_window() -> None:
    mw = [8_000.0] * 24
    mw[5], mw[6] = 2_000.0, 3_000.0  # lowest pair: 05:00-07:00
    mw[10] = 1_000.0  # a lower single hour, but its pair is higher
    summary = _summary(_run(mw), cal=None)
    assert summary is not None
    assert summary.trough_mw == 2_500
    assert (summary.trough_start, summary.trough_end) == (
        DAY + timedelta(hours=5),
        DAY + timedelta(hours=7),
    )


def test_summary_with_calibration_gives_expected_and_firm_energy() -> None:
    cal = Calibration(
        window_days=28, days_used=28, bias_mw=1_000, p10_error_mw=-500, p90_error_mw=2_500
    )
    summary = _summary(_run([10_000.0] * 24), cal)
    assert summary is not None
    assert summary.adjusted_mwh == pytest.approx(24 * 9_000)
    assert summary.firm_mwh == pytest.approx(24 * 7_500)
    assert summary.firm_mwh < summary.adjusted_mwh < summary.forecast_mwh


def test_summary_of_missing_run_is_none_and_single_hour_is_handled() -> None:
    assert _summary([], cal=None) is None
    single = _summary(_run([4_000.0]), cal=None)
    assert single is not None
    assert single.trough_end - single.trough_start == timedelta(hours=1)


def test_pairs_only_keep_hours_with_an_outturn() -> None:
    run = _run([1.0, 2.0, 3.0])
    actuals = {DAY: 10.0, DAY + timedelta(hours=2): 30.0}
    assert _pairs(run, actuals) == ([1.0, 3.0], [10.0, 30.0])
