import pytest

from windsight.services.metrics import error_stats, histogram


def test_error_stats_sign_convention_and_values() -> None:
    stats = error_stats([110, 90, 100, 120], [100, 100, 100, 100])
    assert stats is not None
    assert stats.count == 4
    assert stats.bias_mw == pytest.approx(5)  # forecasts ran high on average
    assert stats.mae_mw == pytest.approx(10)
    assert stats.rmse_mw == pytest.approx((100 + 100 + 0 + 400) ** 0.5 / 2)
    assert stats.nmae_pct == pytest.approx(10)
    assert stats.max_shortfall_mw == pytest.approx(20)


def test_error_stats_empty_and_mismatched() -> None:
    assert error_stats([], []) is None
    with pytest.raises(ValueError):
        error_stats([1.0], [])


def test_histogram_counts_every_error() -> None:
    bins = histogram([-600, -100, 0, 450, 900], bin_width_mw=500)
    assert sum(b.count for b in bins) == 5
    assert bins[0].lower_mw == -1000
    assert bins[-1].upper_mw == 1000


def test_error_stats_percentiles_and_zero_outturn() -> None:
    stats = error_stats([float(e) for e in range(11)], [0.0] * 11)
    assert stats is not None
    assert (stats.p10_error_mw, stats.p50_error_mw, stats.p90_error_mw) == (1, 5, 9)
    assert stats.nmae_pct is None  # no wind at all: a percentage is meaningless


def test_max_shortfall_is_zero_when_wind_always_beats_forecast() -> None:
    stats = error_stats([90.0, 80.0], [100.0, 100.0])
    assert stats is not None
    assert stats.bias_mw == -15
    assert stats.max_shortfall_mw == 0


def test_histogram_of_identical_errors_has_one_bin() -> None:
    assert histogram([]) == []
    bins = histogram([0.0, 0.0, 0.0])
    assert [(b.lower_mw, b.upper_mw, b.count) for b in bins] == [(0, 500, 3)]
