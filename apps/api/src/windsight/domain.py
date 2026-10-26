"""Plain value objects shared by repositories and services (no ORM, no I/O)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ActualPoint:
    start_time: datetime
    generation_mw: float


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    publish_time: datetime
    start_time: datetime
    generation_mw: float

    @property
    def horizon_hours(self) -> float:
        """Lead time: how far ahead of the target time this forecast was published."""
        return (self.start_time - self.publish_time).total_seconds() / 3600
