"""API response contracts. The frontend's TypeScript types are generated from these."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ErrorStatsOut(BaseModel):
    """Error = forecast - actual. Positive means wind under-delivered (a shortfall)."""

    count: int = Field(description="Number of hourly forecast/actual pairs")
    mae_mw: float = Field(description="Mean absolute error")
    rmse_mw: float = Field(description="Root mean squared error")
    bias_mw: float = Field(description="Mean error; > 0 means forecasts run high")
    nmae_pct: float | None = Field(description="MAE as % of mean actual generation")
    p10_error_mw: float
    p50_error_mw: float
    p90_error_mw: float = Field(
        description="Shortfall not exceeded in 90% of hours: the cover needed at P90 confidence"
    )
    p90_abs_error_mw: float
    max_shortfall_mw: float


# --- meta -------------------------------------------------------------------------------


class DateWindow(BaseModel):
    start: date
    end: date


class ActualsCoverage(BaseModel):
    rows: int
    first_start_time: datetime | None
    last_start_time: datetime | None


class ForecastsCoverage(BaseModel):
    rows: int
    runs: int
    first_publish_time: datetime | None
    last_publish_time: datetime | None


class DataCoverage(BaseModel):
    actuals: ActualsCoverage
    forecasts: ForecastsCoverage
    last_ingested_at: datetime | None


class MetaOut(BaseModel):
    timezone: str
    default_decision_cutoff: time
    max_horizon_hours: int
    calibration_window_days: int
    decision_window: DateWindow
    delivery_window: DateWindow
    data: DataCoverage


# --- day-ahead --------------------------------------------------------------------------


class DayAheadPoint(BaseModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    error_mw: float | None
    adjusted_mw: float | None = Field(description="Forecast minus the trailing bias")
    band_low_mw: float | None = Field(description="P10 of the outturn implied by recent errors")
    band_high_mw: float | None = Field(description="P90 of the outturn implied by recent errors")


class CalibrationOut(BaseModel):
    """Error profile learned from delivery days fully settled before the decision (D-2 back)."""

    window_days: int
    days_used: int
    bias_mw: float
    p10_error_mw: float
    p90_error_mw: float


class DayAheadSummary(BaseModel):
    """Headline numbers for the decision, computed from the forecast in hand."""

    forecast_mwh: float
    adjusted_mwh: float | None = Field(description="Bias-corrected expected wind energy")
    firm_mwh: float | None = Field(
        description="Wind energy exceeded with 90% confidence (sum of the band's low edge)"
    )
    avg_mw: float
    peak_mw: float
    trough_mw: float = Field(description="Mean forecast over the lowest-wind window")
    trough_start: datetime
    trough_end: datetime


class DayAheadOut(BaseModel):
    delivery_date: date
    decision_time: datetime = Field(description="When the purchase decision is committed (UTC)")
    forecast_publish_time: datetime | None = Field(
        description="Publish time of the latest forecast run available at the decision time"
    )
    forecast_age_hours: float | None = Field(
        description="How old that forecast run was at the decision time"
    )
    summary: DayAheadSummary | None
    calibration: CalibrationOut | None
    actual_mwh: float | None
    stats: ErrorStatsOut | None
    points: list[DayAheadPoint]


class DailyAccuracy(BaseModel):
    delivery_date: date
    forecast_publish_time: datetime | None
    forecast_mwh: float | None
    actual_mwh: float | None
    mae_mw: float | None
    bias_mw: float | None


class HourlyAccuracy(BaseModel):
    hour: int = Field(ge=0, le=23, description="Local hour of the delivery day")
    count: int
    mae_mw: float
    bias_mw: float


class HistogramBinOut(BaseModel):
    lower_mw: float
    upper_mw: float
    count: int


class DayAheadAccuracyOut(BaseModel):
    cutoff: time
    delivery_window: DateWindow
    calibration_window_days: int
    stats: ErrorStatsOut | None
    adjusted_stats: ErrorStatsOut | None = Field(
        description="Error of the bias-corrected forecast (out of sample, same hours as stats)"
    )
    band_coverage_pct: float | None = Field(
        description="Share of hours whose outturn fell inside the P10-P90 band (target: 80%)"
    )
    daily: list[DailyAccuracy]
    by_hour: list[HourlyAccuracy]
    error_histogram: list[HistogramBinOut]


# --- horizon ----------------------------------------------------------------------------


class HorizonBucket(BaseModel):
    horizon_hours: int = Field(description="Lead time bucket [h, h+1)")
    stats: ErrorStatsOut


class HorizonAccuracyOut(BaseModel):
    start: datetime
    end: datetime
    buckets: list[HorizonBucket]


class SeriesPoint(BaseModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    forecast_publish_time: datetime | None


class SeriesOut(BaseModel):
    start: datetime
    end: datetime
    horizon_hours: float
    stats: ErrorStatsOut | None
    points: list[SeriesPoint]
