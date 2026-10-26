"""ORM models. Timestamps are stored and returned as timezone-aware UTC."""

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Index, Integer, String, Text, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UTCDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as UTC and always hands back aware UTC values.

    Postgres keeps the offset natively; SQLite (used for tests and Docker-less dev)
    does not, so normalise on the way in and out.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetimes are not allowed")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ActualGeneration(Base):
    """Half-hourly outturn wind generation (Elexon FUELHH, fuelType=WIND)."""

    __tablename__ = "actual_generation"

    start_time: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    settlement_date: Mapped[date] = mapped_column(Date)
    settlement_period: Mapped[int] = mapped_column(Integer)
    generation_mw: Mapped[float] = mapped_column(Float)
    publish_time: Mapped[datetime] = mapped_column(UTCDateTime)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ForecastGeneration(Base):
    """Hourly national wind forecast (Elexon WINDFOR), one row per (run, target time)."""

    __tablename__ = "forecast_generation"

    publish_time: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    generation_mw: Mapped[float] = mapped_column(Float)
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    __table_args__ = (Index("ix_forecast_generation_start_time", "start_time"),)


class IngestionRun(Base):
    """Audit trail of ingestion jobs, surfaced to users as data freshness."""

    __tablename__ = "ingestion_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset: Mapped[str] = mapped_column(String(32))
    window_start: Mapped[datetime] = mapped_column(UTCDateTime)
    window_end: Mapped[datetime] = mapped_column(UTCDateTime)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    rows_upserted: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="running")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
