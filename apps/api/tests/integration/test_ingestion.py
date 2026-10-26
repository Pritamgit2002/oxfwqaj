import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import utc
from windsight.core.config import Settings
from windsight.db.models import ActualGeneration, ForecastGeneration, IngestionRun
from windsight.elexon.client import ElexonClient
from windsight.repositories.generation import GenerationRepository
from windsight.services.ingestion import IngestionService


def _fake_elexon(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/FUELHH/stream"):
        rows = [
            {
                "publishTime": "2026-01-15T00:30:00Z",
                "startTime": "2026-01-15T00:00:00Z",
                "settlementDate": "2026-01-15",
                "settlementPeriod": 1,
                "fuelType": fuel,
                "generation": 9000,
            }
            for fuel in ("WIND", "CCGT")
        ]
    else:
        rows = [
            {
                "publishTime": "2026-01-14T07:30:00Z",
                "startTime": f"2026-01-15T0{h}:00:00Z",
                "generation": 9500,
            }
            for h in range(3)
        ]
    return httpx.Response(200, content=json.dumps(rows))


def test_ingestion_is_idempotent_and_filters_wind(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    client = ElexonClient("https://elexon.test", transport=httpx.MockTransport(_fake_elexon))
    service = IngestionService(session_factory, client, settings)
    start = utc(2026, 1, 14)
    end = start + timedelta(days=2)

    for _ in range(2):
        assert service.ingest_actuals(start, end).rows == 1
        assert service.ingest_forecasts(start, end).rows == 3

    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(ActualGeneration)) == 1
        assert s.scalar(select(func.count()).select_from(ForecastGeneration)) == 3
        statuses = s.scalars(select(IngestionRun.status)).all()
        assert statuses == ["success"] * 4


def test_failed_ingestion_is_recorded_and_keeps_completed_chunks(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("windsight.elexon.client.time.sleep", lambda _: None)
    calls = 0

    def flaky(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls > 1:  # the first chunk succeeds, then Elexon goes down
            return httpx.Response(503)
        return _fake_elexon(request)

    settings = Settings(environment="test", database_url="sqlite://", elexon_chunk_days=1)
    client = ElexonClient("https://elexon.test", transport=httpx.MockTransport(flaky))
    service = IngestionService(session_factory, client, settings)

    with pytest.raises(httpx.HTTPStatusError):
        service.ingest_actuals(utc(2026, 1, 15), utc(2026, 1, 18))

    with session_factory() as s:
        run = s.scalars(select(IngestionRun)).one()
        assert run.status == "failed"
        assert "503" in (run.error or "")
        assert run.finished_at is not None
        assert run.rows_upserted == 1
        assert s.scalar(select(func.count()).select_from(ActualGeneration)) == 1
        # a failed run must not count as a refresh
        assert GenerationRepository(s).dataset_stats()["last_ingested_at"] is None


def test_forecast_chunks_do_not_double_count_runs_on_the_boundary(
    session_factory: sessionmaker[Session],
) -> None:
    """The API's publish range is inclusive; a run exactly on a chunk edge is loaded once."""
    boundary = utc(2026, 1, 15)

    def runs(request: httpx.Request) -> httpx.Response:
        rows = [
            {"publishTime": t, "startTime": "2026-01-16T00:00:00Z", "generation": 1}
            for t in ("2026-01-14T12:00:00Z", "2026-01-15T00:00:00Z", "2026-01-15T12:00:00Z")
            if request.url.params["publishDateTimeFrom"]
            <= t
            <= request.url.params["publishDateTimeTo"]
        ]
        return httpx.Response(200, json=rows)

    settings = Settings(environment="test", database_url="sqlite://", elexon_chunk_days=1)
    client = ElexonClient("https://elexon.test", transport=httpx.MockTransport(runs))
    result = IngestionService(session_factory, client, settings).ingest_forecasts(
        boundary - timedelta(days=1), boundary + timedelta(days=1)
    )
    assert result.rows == 3
