import json
from collections.abc import Callable
from datetime import timedelta, timezone

import httpx
import pytest

from tests.conftest import utc
from windsight.elexon import client as client_module
from windsight.elexon.client import ElexonClient, _iso, date_chunks


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_module.time, "sleep", lambda _: None)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> ElexonClient:
    return ElexonClient("https://elexon.test", transport=httpx.MockTransport(handler))


def _actual(start: str, fuel: str = "WIND") -> dict[str, object]:
    return {
        "publishTime": start,
        "startTime": start,
        "settlementDate": start[:10],
        "settlementPeriod": 1,
        "fuelType": fuel,
        "generation": 1234.5,
    }


def test_date_chunks_cover_range_without_gaps_or_overlap() -> None:
    start, end = utc(2026, 1, 1), utc(2026, 1, 16)
    chunks = list(date_chunks(start, end, days=7))
    assert chunks == [
        (utc(2026, 1, 1), utc(2026, 1, 8)),
        (utc(2026, 1, 8), utc(2026, 1, 15)),
        (utc(2026, 1, 15), utc(2026, 1, 16)),
    ]
    assert list(date_chunks(end, start, days=7)) == []


def test_iso_normalises_to_utc_zulu() -> None:
    plus_one = timezone(timedelta(hours=1))
    assert _iso(utc(2026, 1, 15, 9).astimezone(plus_one)) == "2026-01-15T09:00:00Z"


def test_wind_actuals_sends_settlement_dates_and_filters_window_and_fuel() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        rows = [
            _actual("2026-01-14T23:30:00Z"),  # before the window
            _actual("2026-01-15T00:00:00Z"),
            _actual("2026-01-15T00:00:00Z", fuel="CCGT"),
            _actual("2026-01-16T00:00:00Z"),  # end is exclusive
        ]
        return httpx.Response(200, json=rows)

    with _client(handler) as client:
        records = client.wind_actuals(utc(2026, 1, 15), utc(2026, 1, 16))

    assert [r.start_time for r in records] == [utc(2026, 1, 15)]
    assert records[0].generation == 1234.5
    params = seen[0].url.params
    assert seen[0].url.path == "/datasets/FUELHH/stream"
    assert (params["settlementDateFrom"], params["settlementDateTo"]) == (
        "2026-01-15",
        "2026-01-16",
    )
    assert params["fuelType"] == "WIND"


def test_wind_forecasts_accepts_wrapped_payload() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        row = {"publishTime": "2026-01-14T07:30:00Z", "startTime": "2026-01-15T00:00:00Z"}
        return httpx.Response(200, json={"data": [{**row, "generation": 9000}]})

    with _client(handler) as client:
        records = client.wind_forecasts(utc(2026, 1, 14), utc(2026, 1, 15))

    assert len(records) == 1
    assert records[0].publish_time == utc(2026, 1, 14, 7, 30)
    assert seen[0].url.params["publishDateTimeFrom"] == "2026-01-14T00:00:00Z"
    assert seen[0].url.params["publishDateTimeTo"] == "2026-01-15T00:00:00Z"


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transient_http_errors_are_retried(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status) if calls < 3 else httpx.Response(200, json=[])

    with _client(handler) as client:
        assert client.wind_forecasts(utc(2026, 1, 14), utc(2026, 1, 15)) == []
    assert calls == 3


def test_network_errors_are_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("connection reset", request=request)
        return httpx.Response(200, content=json.dumps([]))

    with _client(handler) as client:
        assert client.wind_forecasts(utc(2026, 1, 14), utc(2026, 1, 15)) == []
    assert calls == 2


def test_client_errors_fail_fast() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad range"})

    with _client(handler) as client, pytest.raises(httpx.HTTPStatusError):
        client.wind_forecasts(utc(2026, 1, 14), utc(2026, 1, 15))
    assert calls == 1


def test_gives_up_after_max_retries() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(502)

    with _client(handler) as client, pytest.raises(httpx.HTTPStatusError):
        client.wind_actuals(utc(2026, 1, 14), utc(2026, 1, 15))
    assert calls == 3
