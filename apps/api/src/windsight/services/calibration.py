"""Learn the forecast's recent error profile and apply it to today's forecast.

Leakage rule: a decision for delivery day D is taken on D-1, when the outturn of D-1 itself is
still incomplete. Only delivery days D-2 and earlier are therefore used. The same rule applies
in the backtest, so the reported improvement is out of sample.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np


@dataclass(frozen=True, slots=True)
class Calibration:
    window_days: int
    days_used: int
    bias_mw: float
    p10_error_mw: float
    p90_error_mw: float


@dataclass(frozen=True, slots=True)
class Adjusted:
    adjusted_mw: float
    band_low_mw: float
    band_high_mw: float


def calibration_days(delivery_date: date, window_days: int) -> list[date]:
    """The delivery days whose outturn is fully known at D's decision time (D-2 backwards)."""
    return [delivery_date - timedelta(days=k) for k in range(2, window_days + 2)]


def calibrate(
    errors_by_day: Mapping[date, Sequence[float]], delivery_date: date, window_days: int
) -> Calibration | None:
    """Bias and P10/P90 of (forecast - actual) over the trailing window, or None if no history."""
    days = [d for d in calibration_days(delivery_date, window_days) if errors_by_day.get(d)]
    errors = [e for d in days for e in errors_by_day[d]]
    if not errors:
        return None
    p10, p90 = (float(v) for v in np.percentile(errors, [10, 90]))
    return Calibration(
        window_days=window_days,
        days_used=len(days),
        bias_mw=float(np.mean(errors)),
        p10_error_mw=p10,
        p90_error_mw=p90,
    )


def adjust(forecast_mw: float, cal: Calibration) -> Adjusted:
    """Bias-corrected forecast and the P10-P90 range of the outturn (actual = forecast - error)."""
    return Adjusted(
        adjusted_mw=max(0.0, forecast_mw - cal.bias_mw),
        band_low_mw=max(0.0, forecast_mw - cal.p90_error_mw),
        band_high_mw=max(0.0, forecast_mw - cal.p10_error_mw),
    )
