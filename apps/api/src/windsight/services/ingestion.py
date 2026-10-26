"""Pulls Elexon data into the database. Idempotent: re-running upserts the same rows."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from windsight.core.config import Settings
from windsight.db.models import utcnow
from windsight.elexon.client import ElexonClient, date_chunks
from windsight.repositories.generation import GenerationRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    dataset: str
    rows: int


class IngestionService:
    def __init__(
        self, session_factory: Callable[[], Session], client: ElexonClient, settings: Settings
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._settings = settings

    def _run(
        self, dataset: str, start: datetime, end: datetime, load_chunk: Callable[..., int]
    ) -> IngestionResult:
        with self._session_factory() as session:
            repo = GenerationRepository(session)
            run = repo.start_ingestion_run(dataset, start, end)
            session.commit()
            try:
                for lo, hi in date_chunks(start, end, self._settings.elexon_chunk_days):
                    rows = load_chunk(repo, lo, hi)
                    run.rows_upserted += rows
                    session.commit()
                    logger.info("%s %s -> %s: %d rows", dataset, lo, hi, rows)
                run.status = "success"
            except Exception as exc:
                session.rollback()
                run.status, run.error = "failed", repr(exc)
                raise
            finally:
                run.finished_at = utcnow()
                session.add(run)
                session.commit()
        return IngestionResult(dataset, run.rows_upserted)

    def ingest_actuals(self, start: datetime, end: datetime) -> IngestionResult:
        def load(repo: GenerationRepository, lo: datetime, hi: datetime) -> int:
            records = self._client.wind_actuals(lo, hi)
            return repo.upsert_actuals(
                [
                    {
                        "start_time": r.start_time,
                        "settlement_date": r.settlement_date,
                        "settlement_period": r.settlement_period,
                        "generation_mw": r.generation,
                        "publish_time": r.publish_time,
                    }
                    for r in records
                ]
            )

        return self._run("FUELHH", start, end, load)

    def ingest_forecasts(self, publish_from: datetime, publish_to: datetime) -> IngestionResult:
        def load(repo: GenerationRepository, lo: datetime, hi: datetime) -> int:
            # The API's publish range is inclusive on both ends; drop the upper bound so
            # adjacent chunks don't fetch the same run twice.
            records = [r for r in self._client.wind_forecasts(lo, hi) if r.publish_time < hi]
            return repo.upsert_forecasts(
                [
                    {
                        "publish_time": r.publish_time,
                        "start_time": r.start_time,
                        "generation_mw": r.generation,
                    }
                    for r in records
                ]
            )

        return self._run("WINDFOR", publish_from, publish_to, load)

    def ingest_pilot_window(self) -> list[IngestionResult]:
        """Everything the January 2026 pilot needs, derived from settings."""
        start, end = self._settings.ingestion_window()
        lookback = timedelta(hours=self._settings.max_horizon_hours + 24)
        return [
            self.ingest_actuals(start, end),
            self.ingest_forecasts(start - lookback, end),
        ]
