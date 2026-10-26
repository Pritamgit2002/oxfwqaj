"""Forecast error statistics.

Sign convention: error = forecast - actual.
  error > 0  -> wind came in *below* forecast (shortfall the buyer must cover)
  error < 0  -> wind came in above forecast (surplus)
"""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ErrorStats:
    count: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    nmae_pct: float | None
    p10_error_mw: float
    p50_error_mw: float
    p90_error_mw: float
    p90_abs_error_mw: float
    max_shortfall_mw: float


def error_stats(forecast: Sequence[float], actual: Sequence[float]) -> ErrorStats | None:
    if len(forecast) != len(actual):
        raise ValueError("forecast and actual must be the same length")
    if not forecast:
        return None
    f = np.asarray(forecast, dtype=float)
    a = np.asarray(actual, dtype=float)
    err = f - a
    abs_err = np.abs(err)
    mean_actual = float(a.mean())
    mae = float(abs_err.mean())
    p10, p50, p90 = (float(v) for v in np.percentile(err, [10, 50, 90]))
    return ErrorStats(
        count=len(err),
        mae_mw=mae,
        rmse_mw=float(np.sqrt((err**2).mean())),
        bias_mw=float(err.mean()),
        nmae_pct=(mae / mean_actual * 100) if mean_actual > 0 else None,
        p10_error_mw=p10,
        p50_error_mw=p50,
        p90_error_mw=p90,
        p90_abs_error_mw=float(np.percentile(abs_err, 90)),
        max_shortfall_mw=float(max(err.max(), 0.0)),
    )


@dataclass(frozen=True, slots=True)
class HistogramBin:
    lower_mw: float
    upper_mw: float
    count: int


def histogram(errors: Sequence[float], bin_width_mw: float = 500.0) -> list[HistogramBin]:
    if not errors:
        return []
    e = np.asarray(errors, dtype=float)
    lo = np.floor(e.min() / bin_width_mw) * bin_width_mw
    hi = np.ceil(e.max() / bin_width_mw) * bin_width_mw
    if hi == lo:
        hi = lo + bin_width_mw
    counts, edges = np.histogram(e, bins=np.arange(lo, hi + bin_width_mw, bin_width_mw))
    return [
        HistogramBin(float(edges[i]), float(edges[i + 1]), int(c)) for i, c in enumerate(counts)
    ]
