"""Thin client for the Elexon BMRS Insights API (no API key required).

Docs:
  https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
  https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream
"""

import logging
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class FuelHHRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    publish_time: datetime = Field(alias="publishTime")
    start_time: datetime = Field(alias="startTime")
    settlement_date: date = Field(alias="settlementDate")
    settlement_period: int = Field(alias="settlementPeriod")
    fuel_type: str = Field(alias="fuelType")
    generation: float


class WindForRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    publish_time: datetime = Field(alias="publishTime")
    start_time: datetime = Field(alias="startTime")
    generation: float


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_chunks(start: datetime, end: datetime, days: int) -> Iterator[tuple[datetime, datetime]]:
    cursor = start
    while cursor < end:
        upper = min(cursor + timedelta(days=days), end)
        yield cursor, upper
        cursor = upper


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={"Accept": "application/json"},
        )
        self._max_retries = max_retries

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._http.get(path, params=params)
                response.raise_for_status()
                payload = response.json()
                # Stream endpoints return a bare list; others wrap it in {"data": [...]}.
                return payload if isinstance(payload, list) else payload.get("data", [])
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                    exc.response.status_code >= 500 or exc.response.status_code == 429
                )
                if not retryable or attempt == self._max_retries:
                    raise
                backoff = 2**attempt
                logger.warning("Elexon %s failed (%s); retrying in %ss", path, exc, backoff)
                time.sleep(backoff)
        raise AssertionError("unreachable")

    def wind_actuals(self, start: datetime, end: datetime) -> list[FuelHHRecord]:
        """Half-hourly WIND outturn for settlement dates covering [start, end)."""
        rows = self._get(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": start.astimezone(UTC).date().isoformat(),
                "settlementDateTo": end.astimezone(UTC).date().isoformat(),
                "fuelType": "WIND",
            },
        )
        records = [FuelHHRecord.model_validate(row) for row in rows]
        return [r for r in records if r.fuel_type == "WIND" and start <= r.start_time < end]

    def wind_forecasts(self, publish_from: datetime, publish_to: datetime) -> list[WindForRecord]:
        """Every WINDFOR forecast run published in [publish_from, publish_to]."""
        rows = self._get(
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": _iso(publish_from), "publishDateTimeTo": _iso(publish_to)},
        )
        return [WindForRecord.model_validate(row) for row in rows]
