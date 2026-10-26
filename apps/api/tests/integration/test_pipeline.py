"""End-to-end flow: Elexon -> ingestion -> database -> analytics -> HTTP API.

The pilot window is ingested once from the fake Elexon (see fake_elexon.py), then every
endpoint is checked against answers that follow from the synthetic data:

- At the 09:00 cutoff the forecast in hand for day D is the 07:30 D-1 run, whose lead
  times over D are 16.5 h ... 39.5 h, so the raw error is 1165 ... 1395 MW (mean 1280).
- Every day has the same error profile, so the trailing bias is exactly 1280 MW and the
  bias-corrected error is 10 x |lead - 28| MW: MAE 60 MW.
"""

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import make_client, make_engine
from tests.integration.fake_elexon import ACTUAL_MW, BIAS_MW, GROWTH_MW, FakeElexon
from windsight.core.config import Settings
from windsight.db.models import ActualGeneration, ForecastGeneration, IngestionRun
from windsight.elexon.client import ElexonClient
from windsight.services.ingestion import IngestionService

PILOT_DAYS = 31
INGESTED_DAYS = 62  # 2025-12-03 .. 2026-02-02: calibration history through last delivery day
RUNS = 65 * 8  # forecast runs from 72 h before the window, 8 a day
RAW_BIAS = BIAS_MW + GROWTH_MW * 28


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(environment="test", database_url="sqlite://")


@pytest.fixture(scope="module")
def factory() -> Iterator[sessionmaker[Session]]:
    for engine in make_engine():
        yield sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(scope="module")
def fake() -> FakeElexon:
    return FakeElexon()


@pytest.fixture(scope="module")
def ingested(factory: sessionmaker[Session], settings: Settings, fake: FakeElexon) -> list[int]:
    with ElexonClient("https://elexon.test", transport=fake.transport()) as elexon:
        results = IngestionService(factory, elexon, settings).ingest_pilot_window()
    return [r.rows for r in results]


@pytest.fixture(scope="module")
def api(
    settings: Settings, factory: sessionmaker[Session], ingested: list[int]
) -> Iterator[TestClient]:
    yield from make_client(settings, factory)


def test_ingestion_loads_wind_only_for_the_whole_pilot_window(
    ingested: list[int], factory: sessionmaker[Session], fake: FakeElexon
) -> None:
    assert ingested == [INGESTED_DAYS * 48, RUNS * 48]
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(ActualGeneration)) == INGESTED_DAYS * 48
        assert s.scalar(select(func.count(func.distinct(ForecastGeneration.publish_time)))) == RUNS
        assert s.scalars(select(IngestionRun.status)).all() == ["success", "success"]
    # 7-day chunks: requests stay small and each can be retried on its own
    assert len(fake.requests) == 9 + 10  # 62 days of actuals, 65 days of runs


def test_meta_reports_coverage_and_freshness(api: TestClient) -> None:
    meta = api.get("/api/v1/meta").json()
    assert meta["data"]["actuals"]["rows"] == INGESTED_DAYS * 48
    assert meta["data"]["forecasts"]["runs"] == RUNS
    assert meta["data"]["last_ingested_at"] is not None
    assert meta["decision_window"] == {"start": "2026-01-01", "end": "2026-01-31"}


def test_day_ahead_flow_for_a_pilot_day(api: TestClient) -> None:
    body = api.get("/api/v1/day-ahead", params={"delivery_date": "2026-01-15"}).json()
    assert body["decision_time"] == "2026-01-14T09:00:00Z"
    assert body["forecast_publish_time"] == "2026-01-14T07:30:00Z"
    assert body["forecast_age_hours"] == 1.5
    assert len(body["points"]) == 48  # half-hourly outturn; forecasts on the hour
    assert body["actual_mwh"] == 24 * ACTUAL_MW

    assert body["stats"]["count"] == 24
    assert body["stats"]["bias_mw"] == pytest.approx(RAW_BIAS)
    assert body["calibration"]["days_used"] == 28
    assert body["calibration"]["bias_mw"] == pytest.approx(RAW_BIAS)

    summary = body["summary"]
    assert summary["adjusted_mwh"] == pytest.approx(24 * ACTUAL_MW)
    assert summary["firm_mwh"] < summary["adjusted_mwh"] < summary["forecast_mwh"]
    # forecast error grows with lead time, so the earliest hours have the least wind
    assert summary["trough_start"] == "2026-01-15T00:00:00Z"


def test_first_delivery_day_already_has_full_calibration_history(api: TestClient) -> None:
    body = api.get("/api/v1/day-ahead", params={"delivery_date": "2026-01-02"}).json()
    assert body["calibration"]["days_used"] == 28


def test_earlier_cutoff_uses_the_older_run(api: TestClient) -> None:
    body = api.get(
        "/api/v1/day-ahead", params={"delivery_date": "2026-01-15", "cutoff": "06:00"}
    ).json()
    assert body["forecast_publish_time"] == "2026-01-14T04:30:00Z"
    assert body["stats"]["bias_mw"] == pytest.approx(RAW_BIAS + 3 * GROWTH_MW)


def test_accuracy_backtest_over_the_pilot(api: TestClient) -> None:
    acc = api.get("/api/v1/accuracy/day-ahead").json()
    assert acc["stats"]["count"] == PILOT_DAYS * 24
    assert acc["stats"]["mae_mw"] == pytest.approx(RAW_BIAS)
    assert acc["adjusted_stats"]["mae_mw"] == pytest.approx(60)
    assert 70 <= acc["band_coverage_pct"] <= 90
    assert len(acc["daily"]) == PILOT_DAYS
    assert all(d["forecast_publish_time"].endswith("07:30:00Z") for d in acc["daily"])
    by_hour = {h["hour"]: h["bias_mw"] for h in acc["by_hour"]}
    assert by_hour[0] == pytest.approx(BIAS_MW + GROWTH_MW * 16.5)
    assert by_hour[23] == pytest.approx(BIAS_MW + GROWTH_MW * 39.5)
    assert sum(b["count"] for b in acc["error_histogram"]) == PILOT_DAYS * 24


def test_horizon_error_grows_with_lead_time(api: TestClient) -> None:
    buckets = api.get("/api/v1/accuracy/horizon").json()["buckets"]
    assert [b["horizon_hours"] for b in buckets] == list(range(48))
    maes = [b["stats"]["mae_mw"] for b in buckets]
    assert maes == sorted(maes)
    assert maes[0] == pytest.approx(BIAS_MW + GROWTH_MW * 0.5)


def test_series_never_uses_a_forecast_newer_than_the_horizon(api: TestClient) -> None:
    series = api.get(
        "/api/v1/series",
        params={
            "start": "2026-01-15T00:00:00Z",
            "end": "2026-01-16T00:00:00Z",
            "horizon_hours": 24,
        },
    ).json()
    hourly = [p for p in series["points"] if p["forecast_mw"] is not None]
    assert len(hourly) == 24
    for p in hourly:
        lead = (_ts(p["start_time"]) - _ts(p["forecast_publish_time"])) / 3600
        assert 24 <= lead < 27  # runs are 3 h apart: the latest one at least 24 h ahead
    assert series["stats"]["count"] == 24


def test_reingesting_is_idempotent(
    api: TestClient, factory: sessionmaker[Session], settings: Settings
) -> None:
    with ElexonClient("https://elexon.test", transport=FakeElexon().transport()) as elexon:
        IngestionService(factory, elexon, settings).ingest_pilot_window()
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(ActualGeneration)) == INGESTED_DAYS * 48
        assert s.scalar(select(func.count()).select_from(ForecastGeneration)) == RUNS * 48
    assert api.get("/api/v1/meta").json()["data"]["forecasts"]["runs"] == RUNS


def _ts(iso: str) -> float:
    return datetime.fromisoformat(iso).timestamp()
