"""A deterministic stand-in for the Elexon BMRS stream endpoints.

The synthetic world has known answers, so integration tests can assert exact behaviour:
- outturn is a flat ACTUAL_MW in every half hour (plus CCGT rows the client must drop);
- a WINDFOR run is published every 3 h at hh:30 UTC, covering the next RUN_HOURS hours;
- each forecast runs high by BIAS_MW plus GROWTH_MW per hour of lead time, so error
  grows with horizon and the trailing bias correction has something to learn.
"""

import math
from datetime import UTC, date, datetime, time, timedelta

import httpx

ACTUAL_MW = 10_000.0
BIAS_MW = 1_000.0
GROWTH_MW = 10.0
RUN_HOURS = 48
RUN_EVERY = timedelta(hours=3)
FIRST_RUN = datetime(2025, 1, 1, 1, 30, tzinfo=UTC)


def forecast_mw(publish: datetime, target: datetime) -> float:
    lead_hours = (target - publish).total_seconds() / 3600
    return ACTUAL_MW + BIAS_MW + GROWTH_MW * lead_hours


def run_times(start: datetime, end: datetime) -> list[datetime]:
    """Publish times in [start, end], inclusive like the real API."""
    n = math.ceil((start - FIRST_RUN) / RUN_EVERY)
    t, out = FIRST_RUN + n * RUN_EVERY, []
    while t <= end:
        out.append(t)
        t += RUN_EVERY
    return out


def _z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeElexon:
    def __init__(self, fail_dataset: str | None = None) -> None:
        self.fail_dataset = fail_dataset
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        if request.url.path.endswith("/FUELHH/stream"):
            if self.fail_dataset == "FUELHH":
                return httpx.Response(503)
            return httpx.Response(
                200, json=self._actuals(params["settlementDateFrom"], params["settlementDateTo"])
            )
        if request.url.path.endswith("/WINDFOR/stream"):
            if self.fail_dataset == "WINDFOR":
                return httpx.Response(503)
            return httpx.Response(
                200,
                json=self._forecasts(params["publishDateTimeFrom"], params["publishDateTimeTo"]),
            )
        return httpx.Response(404)

    @staticmethod
    def _actuals(first: str, last: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        day = date.fromisoformat(first)
        while day <= date.fromisoformat(last):
            midnight = datetime.combine(day, time(), UTC)
            for i in range(48):
                start = midnight + timedelta(minutes=30 * i)
                for fuel, mw in (("WIND", ACTUAL_MW), ("CCGT", 5_000.0)):
                    rows.append(
                        {
                            "publishTime": _z(start + timedelta(minutes=30)),
                            "startTime": _z(start),
                            "settlementDate": day.isoformat(),
                            "settlementPeriod": i + 1,
                            "fuelType": fuel,
                            "generation": mw,
                        }
                    )
            day += timedelta(days=1)
        return rows

    @staticmethod
    def _forecasts(start: str, end: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for publish in run_times(datetime.fromisoformat(start), datetime.fromisoformat(end)):
            first_target = publish.replace(minute=0) + timedelta(hours=1)
            for h in range(RUN_HOURS):
                target = first_target + timedelta(hours=h)
                rows.append(
                    {
                        "publishTime": _z(publish),
                        "startTime": _z(target),
                        "generation": forecast_mw(publish, target),
                    }
                )
        return rows
