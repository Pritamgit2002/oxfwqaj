"""Data access for generation data. The only module that writes SQL for these tables."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from windsight.db.models import ActualGeneration, ForecastGeneration, IngestionRun
from windsight.domain import ActualPoint, ForecastPoint

_BATCH_SIZE = 1000


def _upsert(
    session: Session,
    model: type[ActualGeneration] | type[ForecastGeneration],
    rows: Sequence[dict[str, Any]],
    keys: list[str],
) -> int:
    dialect = session.get_bind().dialect.name
    if dialect not in ("postgresql", "sqlite"):
        raise NotImplementedError(f"upsert not supported for dialect {dialect!r}")
    for i in range(0, len(rows), _BATCH_SIZE):
        stmt: postgresql.Insert | sqlite.Insert = (
            postgresql.insert(model) if dialect == "postgresql" else sqlite.insert(model)
        )
        stmt = stmt.values(rows[i : i + _BATCH_SIZE])
        updates = {c: stmt.excluded[c] for c in rows[0] if c not in keys}
        session.execute(stmt.on_conflict_do_update(index_elements=keys, set_=updates))
    return len(rows)


class GenerationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- writes -------------------------------------------------------------------------

    def upsert_actuals(self, rows: Sequence[dict[str, Any]]) -> int:
        return _upsert(self.session, ActualGeneration, rows, ["start_time"]) if rows else 0

    def upsert_forecasts(self, rows: Sequence[dict[str, Any]]) -> int:
        if not rows:
            return 0
        return _upsert(self.session, ForecastGeneration, rows, ["publish_time", "start_time"])

    # --- reads --------------------------------------------------------------------------

    def actuals_between(self, start: datetime, end: datetime) -> list[ActualPoint]:
        stmt = (
            select(ActualGeneration.start_time, ActualGeneration.generation_mw)
            .where(ActualGeneration.start_time >= start, ActualGeneration.start_time < end)
            .order_by(ActualGeneration.start_time)
        )
        return [ActualPoint(t, mw) for t, mw in self.session.execute(stmt)]

    def forecasts_for_targets(
        self, start: datetime, end: datetime, published_after: datetime | None = None
    ) -> list[ForecastPoint]:
        """All forecast rows (from every run) whose target time falls in [start, end)."""
        stmt = select(
            ForecastGeneration.publish_time,
            ForecastGeneration.start_time,
            ForecastGeneration.generation_mw,
        ).where(ForecastGeneration.start_time >= start, ForecastGeneration.start_time < end)
        if published_after is not None:
            stmt = stmt.where(ForecastGeneration.publish_time >= published_after)
        stmt = stmt.order_by(ForecastGeneration.start_time, ForecastGeneration.publish_time)
        return [ForecastPoint(p, t, mw) for p, t, mw in self.session.execute(stmt)]

    def dataset_stats(self) -> dict[str, Any]:
        a = self.session.execute(
            select(
                func.count(),
                func.min(ActualGeneration.start_time),
                func.max(ActualGeneration.start_time),
            )
        ).one()
        f = self.session.execute(
            select(
                func.count(),
                func.count(func.distinct(ForecastGeneration.publish_time)),
                func.min(ForecastGeneration.publish_time),
                func.max(ForecastGeneration.publish_time),
            )
        ).one()
        last_run = self.session.execute(
            select(func.max(IngestionRun.finished_at)).where(IngestionRun.status == "success")
        ).scalar_one_or_none()
        return {
            "actuals": {"rows": a[0], "first_start_time": a[1], "last_start_time": a[2]},
            "forecasts": {
                "rows": f[0],
                "runs": f[1],
                "first_publish_time": f[2],
                "last_publish_time": f[3],
            },
            "last_ingested_at": last_run,
        }

    # --- ingestion audit ----------------------------------------------------------------

    def start_ingestion_run(self, dataset: str, start: datetime, end: datetime) -> IngestionRun:
        run = IngestionRun(dataset=dataset, window_start=start, window_end=end)
        self.session.add(run)
        self.session.flush()
        return run
