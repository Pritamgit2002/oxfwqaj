"""Use cases behind the API: combine repository reads with the selection and metric rules."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta

from windsight.core.config import Settings
from windsight.domain import ForecastPoint
from windsight.repositories.generation import GenerationRepository
from windsight.schemas import analytics as out
from windsight.services.calibration import Calibration, adjust, calibrate
from windsight.services.metrics import ErrorStats, error_stats, histogram
from windsight.services.selection import (
    decision_time,
    delivery_bounds,
    latest_per_target,
    select_run_at,
)

# Actuals are half-hourly MW averages, WINDFOR is hourly: energy = MW x period length.
_ACTUAL_PERIOD_H = 0.5
_FORECAST_PERIOD_H = 1.0
# Length of the "lowest wind" window highlighted to the buyer.
_TROUGH_WINDOW_H = 2


def _stats_out(stats: ErrorStats | None) -> out.ErrorStatsOut | None:
    return out.ErrorStatsOut(**asdict(stats)) if stats else None


def _calibration_out(cal: Calibration | None) -> out.CalibrationOut | None:
    return out.CalibrationOut(**asdict(cal)) if cal else None


def _pairs(
    forecasts: list[ForecastPoint], actual_by_time: dict[datetime, float]
) -> tuple[list[float], list[float]]:
    """Align hourly forecasts with the actual for the half-hour starting at the same time."""
    f, a = [], []
    for point in forecasts:
        actual = actual_by_time.get(point.start_time)
        if actual is not None:
            f.append(point.generation_mw)
            a.append(actual)
    return f, a


def _days(first: date, last: date) -> Iterator[date]:
    day = first
    while day <= last:
        yield day
        day += timedelta(days=1)


@dataclass(frozen=True, slots=True)
class _DayRun:
    """The forecast in hand at the D-1 cutoff for one delivery day, and that day's outturn."""

    decision_time: datetime
    run: list[ForecastPoint]
    actual_by_time: dict[datetime, float]

    @property
    def errors(self) -> list[float]:
        f, a = _pairs(self.run, self.actual_by_time)
        return [fc - ac for fc, ac in zip(f, a, strict=True)]


def _summary(run: list[ForecastPoint], cal: Calibration | None) -> out.DayAheadSummary | None:
    if not run:
        return None
    mw = [f.generation_mw for f in run]
    width = min(_TROUGH_WINDOW_H, len(mw))
    lo = min(range(len(mw) - width + 1), key=lambda i: sum(mw[i : i + width]))
    adjusted = [adjust(m, cal) for m in mw] if cal else None
    return out.DayAheadSummary(
        forecast_mwh=sum(mw) * _FORECAST_PERIOD_H,
        adjusted_mwh=sum(a.adjusted_mw for a in adjusted) * _FORECAST_PERIOD_H
        if adjusted
        else None,
        firm_mwh=sum(a.band_low_mw for a in adjusted) * _FORECAST_PERIOD_H if adjusted else None,
        avg_mw=sum(mw) / len(mw),
        peak_mw=max(mw),
        trough_mw=sum(mw[lo : lo + width]) / width,
        trough_start=run[lo].start_time,
        trough_end=run[lo + width - 1].start_time + timedelta(hours=_FORECAST_PERIOD_H),
    )


class AnalyticsService:
    def __init__(self, repo: GenerationRepository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    # --- meta -----------------------------------------------------------------------------

    def meta(self) -> out.MetaOut:
        s = self.settings
        return out.MetaOut(
            timezone=s.market_timezone,
            default_decision_cutoff=s.default_decision_cutoff,
            max_horizon_hours=s.max_horizon_hours,
            calibration_window_days=s.calibration_window_days,
            decision_window=out.DateWindow(
                start=s.decision_window_start, end=s.decision_window_end
            ),
            delivery_window=out.DateWindow(
                start=s.delivery_window_start, end=s.delivery_window_end
            ),
            data=out.DataCoverage.model_validate(self.repo.dataset_stats()),
        )

    # --- day-ahead view -------------------------------------------------------------------

    def _day_ahead_runs(self, first_day: date, last_day: date, cutoff: time) -> dict[date, _DayRun]:
        """Forecast in hand and outturn for each delivery day, loaded in two queries."""
        tz = self.settings.tz
        start, _ = delivery_bounds(first_day, tz)
        _, end = delivery_bounds(last_day, tz)
        # Runs older than a few days can never be the latest one at a cutoff.
        published_after = decision_time(first_day, cutoff, tz) - timedelta(days=3)

        forecasts: dict[date, list[ForecastPoint]] = defaultdict(list)
        for f in self.repo.forecasts_for_targets(start, end, published_after):
            forecasts[f.start_time.astimezone(tz).date()].append(f)
        actuals: dict[date, dict[datetime, float]] = defaultdict(dict)
        for a in self.repo.actuals_between(start, end):
            actuals[a.start_time.astimezone(tz).date()][a.start_time] = a.generation_mw

        runs = {}
        for day in _days(first_day, last_day):
            as_of = decision_time(day, cutoff, tz)
            runs[day] = _DayRun(as_of, select_run_at(forecasts[day], as_of), actuals[day])
        return runs

    def _calibrated_runs(
        self, first_day: date, last_day: date, cutoff: time
    ) -> tuple[dict[date, _DayRun], dict[date, Calibration | None]]:
        """Day runs for [first_day, last_day] plus each day's trailing error calibration."""
        window = self.settings.calibration_window_days
        runs = self._day_ahead_runs(first_day - timedelta(days=window + 1), last_day, cutoff)
        errors_by_day = {day: r.errors for day, r in runs.items()}
        calibrations = {
            day: calibrate(errors_by_day, day, window) for day in _days(first_day, last_day)
        }
        return runs, calibrations

    def day_ahead(self, delivery_date: date, cutoff: time) -> out.DayAheadOut:
        runs, calibrations = self._calibrated_runs(delivery_date, delivery_date, cutoff)
        day, cal = runs[delivery_date], calibrations[delivery_date]
        actual_by_time = day.actual_by_time
        forecast_by_time = {f.start_time: f.generation_mw for f in day.run}
        publish_time = day.run[0].publish_time if day.run else None

        points = []
        for t in sorted(actual_by_time.keys() | forecast_by_time.keys()):
            fc, ac = forecast_by_time.get(t), actual_by_time.get(t)
            adj = adjust(fc, cal) if fc is not None and cal else None
            points.append(
                out.DayAheadPoint(
                    start_time=t,
                    actual_mw=ac,
                    forecast_mw=fc,
                    error_mw=fc - ac if fc is not None and ac is not None else None,
                    adjusted_mw=adj.adjusted_mw if adj else None,
                    band_low_mw=adj.band_low_mw if adj else None,
                    band_high_mw=adj.band_high_mw if adj else None,
                )
            )

        return out.DayAheadOut(
            delivery_date=delivery_date,
            decision_time=day.decision_time,
            forecast_publish_time=publish_time,
            forecast_age_hours=(day.decision_time - publish_time).total_seconds() / 3600
            if publish_time
            else None,
            summary=_summary(day.run, cal),
            calibration=_calibration_out(cal),
            actual_mwh=sum(actual_by_time.values()) * _ACTUAL_PERIOD_H if actual_by_time else None,
            stats=_stats_out(error_stats(*_pairs(day.run, actual_by_time))),
            points=points,
        )

    def day_ahead_accuracy(self, cutoff: time) -> out.DayAheadAccuracyOut:
        s = self.settings
        tz = s.tz
        runs, calibrations = self._calibrated_runs(
            s.delivery_window_start, s.delivery_window_end, cutoff
        )
        forecast: list[float] = []
        adjusted: list[float] = []
        actual: list[float] = []
        in_band: list[bool] = []
        by_hour: dict[int, list[float]] = defaultdict(list)
        daily: list[out.DailyAccuracy] = []

        for day, cal in calibrations.items():
            r = runs[day]
            for point in r.run:
                a = r.actual_by_time.get(point.start_time)
                if a is None:
                    continue
                forecast.append(point.generation_mw)
                actual.append(a)
                by_hour[point.start_time.astimezone(tz).hour].append(point.generation_mw - a)
                if cal is None:  # no history yet: the best estimate is the raw forecast
                    adjusted.append(point.generation_mw)
                    continue
                adj = adjust(point.generation_mw, cal)
                adjusted.append(adj.adjusted_mw)
                in_band.append(adj.band_low_mw <= a <= adj.band_high_mw)

            stats = error_stats(*_pairs(r.run, r.actual_by_time))
            daily.append(
                out.DailyAccuracy(
                    delivery_date=day,
                    forecast_publish_time=r.run[0].publish_time if r.run else None,
                    forecast_mwh=sum(p.generation_mw for p in r.run) * _FORECAST_PERIOD_H
                    if r.run
                    else None,
                    actual_mwh=sum(r.actual_by_time.values()) * _ACTUAL_PERIOD_H
                    if r.actual_by_time
                    else None,
                    mae_mw=stats.mae_mw if stats else None,
                    bias_mw=stats.bias_mw if stats else None,
                )
            )

        errors = [f - a for f, a in zip(forecast, actual, strict=True)]
        return out.DayAheadAccuracyOut(
            cutoff=cutoff,
            delivery_window=out.DateWindow(
                start=s.delivery_window_start, end=s.delivery_window_end
            ),
            calibration_window_days=s.calibration_window_days,
            stats=_stats_out(error_stats(forecast, actual)),
            adjusted_stats=_stats_out(error_stats(adjusted, actual)),
            band_coverage_pct=100 * sum(in_band) / len(in_band) if in_band else None,
            daily=daily,
            by_hour=[
                out.HourlyAccuracy(
                    hour=h,
                    count=len(errs),
                    mae_mw=sum(abs(e) for e in errs) / len(errs),
                    bias_mw=sum(errs) / len(errs),
                )
                for h, errs in sorted(by_hour.items())
            ],
            error_histogram=[
                out.HistogramBinOut(lower_mw=b.lower_mw, upper_mw=b.upper_mw, count=b.count)
                for b in histogram(errors)
            ],
        )

    # --- horizon views --------------------------------------------------------------------

    def horizon_accuracy(self, start: datetime, end: datetime) -> out.HorizonAccuracyOut:
        max_h = self.settings.max_horizon_hours
        forecasts = self.repo.forecasts_for_targets(start, end, start - timedelta(hours=max_h))
        actual_by_time = {
            a.start_time: a.generation_mw for a in self.repo.actuals_between(start, end)
        }

        buckets: dict[int, tuple[list[float], list[float]]] = defaultdict(lambda: ([], []))
        for f in forecasts:
            actual = actual_by_time.get(f.start_time)
            if actual is None or not 0 <= f.horizon_hours < max_h:
                continue
            fs, as_ = buckets[int(f.horizon_hours)]
            fs.append(f.generation_mw)
            as_.append(actual)

        result = []
        for h in sorted(buckets):
            stats = _stats_out(error_stats(*buckets[h]))
            if stats:
                result.append(out.HorizonBucket(horizon_hours=h, stats=stats))
        return out.HorizonAccuracyOut(start=start, end=end, buckets=result)

    def series(self, start: datetime, end: datetime, horizon_hours: float) -> out.SeriesOut:
        """Actuals vs the latest forecast published at least `horizon_hours` before each target."""
        lead = timedelta(hours=horizon_hours)
        lookback = timedelta(hours=self.settings.max_horizon_hours) + lead
        forecasts = self.repo.forecasts_for_targets(start, end, start - lookback)
        chosen = latest_per_target(forecasts, lead)
        actual_by_time = {
            a.start_time: a.generation_mw for a in self.repo.actuals_between(start, end)
        }

        points = [
            out.SeriesPoint(
                start_time=t,
                actual_mw=actual_by_time.get(t),
                forecast_mw=chosen[t].generation_mw if t in chosen else None,
                forecast_publish_time=chosen[t].publish_time if t in chosen else None,
            )
            for t in sorted(actual_by_time.keys() | chosen.keys())
        ]
        stats = error_stats(
            *_pairs(sorted(chosen.values(), key=lambda f: f.start_time), actual_by_time)
        )
        return out.SeriesOut(
            start=start.astimezone(UTC),
            end=end.astimezone(UTC),
            horizon_hours=horizon_hours,
            stats=_stats_out(stats),
            points=points,
        )
