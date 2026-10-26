from datetime import date

import pytest

from windsight.services.calibration import Calibration, adjust, calibrate, calibration_days

D = date(2026, 1, 15)


def test_calibration_days_skip_the_unsettled_day_before_delivery() -> None:
    days = calibration_days(D, window_days=3)
    assert days == [date(2026, 1, 13), date(2026, 1, 12), date(2026, 1, 11)]
    assert date(2026, 1, 14) not in days


def test_calibrate_ignores_d_minus_1_and_older_than_window() -> None:
    errors = {
        date(2026, 1, 14): [9_000.0],  # D-1: would leak
        date(2026, 1, 13): [100.0, 300.0],
        date(2026, 1, 12): [200.0],
        date(2026, 1, 1): [-50_000.0],  # outside the 3-day window
    }
    cal = calibrate(errors, D, window_days=3)
    assert cal is not None
    assert cal.days_used == 2
    assert cal.bias_mw == pytest.approx(200)


def test_calibrate_without_history_returns_none() -> None:
    assert calibrate({}, D, window_days=28) is None
    assert calibrate({date(2026, 1, 14): [1.0]}, D, window_days=28) is None


def test_adjust_applies_bias_and_clamps_band_at_zero() -> None:
    cal = Calibration(
        window_days=28, days_used=28, bias_mw=500, p10_error_mw=-1_000, p90_error_mw=2_000
    )
    assert adjust(10_000, cal).adjusted_mw == 9_500
    assert (adjust(10_000, cal).band_low_mw, adjust(10_000, cal).band_high_mw) == (8_000, 11_000)
    low_wind = adjust(300, cal)
    assert low_wind.adjusted_mw == 0
    assert low_wind.band_low_mw == 0


def test_calibrate_pools_errors_across_days_for_percentiles() -> None:
    errors = {
        date(2026, 1, 13): [float(e) for e in range(6)],
        date(2026, 1, 12): [6.0, 7.0, 8.0, 9.0, 10.0],
    }
    cal = calibrate(errors, D, window_days=28)
    assert cal is not None
    assert cal.days_used == 2
    assert (cal.p10_error_mw, cal.p90_error_mw) == pytest.approx((1, 9))
    assert cal.window_days == 28


def test_negative_bias_raises_the_adjusted_forecast() -> None:
    cal = Calibration(
        window_days=28, days_used=5, bias_mw=-800, p10_error_mw=-1_500, p90_error_mw=0
    )
    adjusted = adjust(5_000, cal)
    assert adjusted.adjusted_mw == 5_800
    assert (adjusted.band_low_mw, adjusted.band_high_mw) == (5_000, 6_500)
