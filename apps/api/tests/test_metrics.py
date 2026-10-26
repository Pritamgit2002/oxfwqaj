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
