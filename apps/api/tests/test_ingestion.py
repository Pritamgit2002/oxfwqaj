import json
from datetime import timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import utc
from windsight.core.config import Settings
from windsight.db.models import ActualGeneration, ForecastGeneration, IngestionRun
from windsight.elexon.client import ElexonClient
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
