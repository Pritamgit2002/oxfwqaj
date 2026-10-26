"""Application settings, loaded from environment variables (and `.env` when present)."""

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Windsight API"
    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://windsight:windsight@localhost:5432/windsight"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 60.0
    # Elexon stream endpoints accept long ranges, but chunking keeps responses small and
    # lets a failed chunk be retried without refetching the whole window.
    elexon_chunk_days: int = 7

    # GB day-ahead market: decisions are taken on D-1 for delivery day D (local time).
    market_timezone: str = "Europe/London"
    default_decision_cutoff: time = time(9, 0)

    # Scope of the pilot: purchase decisions made during January 2026.
    decision_window_start: date = date(2026, 1, 1)
    decision_window_end: date = date(2026, 1, 31)

    # Longest forecast lead time considered by the horizon analysis.
    max_horizon_hours: int = 48

    # Bias correction and uncertainty band are learned from this many trailing delivery days
    # (only days whose outturn is fully known at the decision time).
    calibration_window_days: int = 28

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """PaaS hosts (Heroku, Render) hand out `postgres://` URLs; SQLAlchemy needs a driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.market_timezone)

    @property
    def delivery_window_start(self) -> date:
        return self.decision_window_start + timedelta(days=1)

    @property
    def delivery_window_end(self) -> date:
        return self.decision_window_end + timedelta(days=1)

    @property
    def calibration_start(self) -> date:
        """First delivery day any pilot decision can learn from."""
        return self.delivery_window_start - timedelta(days=self.calibration_window_days + 1)

    def ingestion_window(self) -> tuple[datetime, datetime]:
        """UTC range of target times the pilot needs: calibration history through delivery."""
        start = datetime.combine(self.calibration_start - timedelta(days=1), time(), self.tz)
        end = datetime.combine(self.delivery_window_end + timedelta(days=2), time(), self.tz)
        return start, end


@lru_cache
def get_settings() -> Settings:
    return Settings()
