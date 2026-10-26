import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_health(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "abc123"
    assert response.headers["Server-Timing"].startswith("app;dur=")
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_day_ahead_uses_latest_run_before_cutoff(client: TestClient, seeded: Session) -> None:
    body = client.get("/api/v1/day-ahead", params={"delivery_date": "2026-01-15"}).json()
    assert body["decision_time"] == "2026-01-14T09:00:00Z"
    assert body["forecast_publish_time"] == "2026-01-14T07:30:00Z"
    assert body["forecast_age_hours"] == 1.5
    assert body["actual_mwh"] == 24 * 10_000
    assert body["stats"]["count"] == 24
    assert body["stats"]["bias_mw"] == 1_000
    assert len(body["points"]) == 48


def test_day_ahead_is_calibrated_on_settled_days_only(client: TestClient, seeded: Session) -> None:
    body = client.get("/api/v1/day-ahead", params={"delivery_date": "2026-01-15"}).json()
    # Jan 11-13 are used; Jan 14's +9 GW error is not yet known at the decision time.
    assert body["calibration"]["days_used"] == 3
    assert body["calibration"]["bias_mw"] == 1_000
    hour = next(p for p in body["points"] if p["forecast_mw"] is not None)
    assert hour["adjusted_mw"] == 10_000
    assert (hour["band_low_mw"], hour["band_high_mw"]) == (9_000, 11_000)

    summary = body["summary"]
    assert summary["forecast_mwh"] == 24 * 11_000
    assert summary["adjusted_mwh"] == 24 * 10_000
    assert summary["firm_mwh"] == 24 * 9_000
    assert summary["trough_end"] > summary["trough_start"]


def test_later_cutoff_picks_newer_run(client: TestClient, seeded: Session) -> None:
    body = client.get(
        "/api/v1/day-ahead", params={"delivery_date": "2026-01-15", "cutoff": "10:00"}
    ).json()
    assert body["forecast_publish_time"] == "2026-01-14T09:30:00Z"
    assert body["stats"]["mae_mw"] == 0


def test_day_ahead_rejects_dates_outside_pilot(client: TestClient) -> None:
    response = client.get("/api/v1/day-ahead", params={"delivery_date": "2026-03-01"})
    assert response.status_code == 422


def test_accuracy_endpoints(client: TestClient, seeded: Session) -> None:
    acc = client.get("/api/v1/accuracy/day-ahead").json()
    assert acc["stats"]["count"] == 5 * 24
    assert acc["adjusted_stats"]["count"] == 5 * 24
    assert acc["adjusted_stats"]["mae_mw"] < acc["stats"]["mae_mw"]
    # band exists for Jan 13-15; Jan 14's +9 GW miss falls outside it
    assert acc["band_coverage_pct"] == pytest.approx(200 / 3)
    assert len(acc["daily"]) == 31
    assert {h["hour"] for h in acc["by_hour"]} == set(range(24))

    horizon = client.get("/api/v1/accuracy/horizon").json()
    assert horizon["buckets"], "expected at least one lead-time bucket"
    assert all(0 <= b["horizon_hours"] < 48 for b in horizon["buckets"])


def test_series_and_meta(client: TestClient, seeded: Session) -> None:
    series = client.get(
        "/api/v1/series",
        params={
            "start": "2026-01-15T00:00:00Z",
            "end": "2026-01-16T00:00:00Z",
            "horizon_hours": 4,
        },
    ).json()
    hourly = [p for p in series["points"] if p["forecast_mw"] is not None]
    assert len(hourly) == 24
    # both D-1 runs are >= 4h ahead of every target on D; the newer 09:30 one wins
    assert hourly[0]["forecast_publish_time"] == "2026-01-14T09:30:00Z"

    meta = client.get("/api/v1/meta").json()
    assert meta["delivery_window"] == {"start": "2026-01-02", "end": "2026-02-01"}
    assert meta["data"]["forecasts"]["runs"] == 6
    assert meta["calibration_window_days"] == 28


def test_series_rejects_naive_datetimes(client: TestClient) -> None:
    response = client.get(
        "/api/v1/series", params={"start": "2026-01-15T00:00:00", "end": "2026-01-16T00:00:00"}
    )
    assert response.status_code == 422


def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    first = client.get("/health").headers["X-Request-ID"]
    second = client.get("/health").headers["X-Request-ID"]
    assert len(first) == 16
    assert first != second


def test_cors_allows_the_web_origin_read_only(client: TestClient) -> None:
    origin = "http://localhost:3000"
    response = client.get("/health", headers={"Origin": origin})
    assert response.headers["access-control-allow-origin"] == origin
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
    preflight = client.options(
        "/api/v1/meta", headers={"Origin": origin, "Access-Control-Request-Method": "POST"}
    )
    assert preflight.status_code == 400  # only GET is allowed
    other = client.get("/health", headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in other.headers


def test_openapi_and_docs_are_served(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert {"/api/v1/day-ahead", "/api/v1/accuracy/day-ahead", "/api/v1/series"} <= set(
        schema["paths"]
    )
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/v1/day-ahead", {}),  # delivery_date is required
        ("/api/v1/day-ahead", {"delivery_date": "2026-01-01"}),  # day before the window
        ("/api/v1/day-ahead", {"delivery_date": "2026-01-15", "cutoff": "25:00"}),
        ("/api/v1/day-ahead", {"delivery_date": "not-a-date"}),
        ("/api/v1/accuracy/day-ahead", {"cutoff": "noon"}),
        ("/api/v1/series", {"horizon_hours": 73}),
        ("/api/v1/series", {"horizon_hours": -1}),
        ("/api/v1/series", {"start": "2026-01-16T00:00:00Z", "end": "2026-01-15T00:00:00Z"}),
        ("/api/v1/series", {"start": "2026-01-01T00:00:00Z", "end": "2026-03-15T00:00:00Z"}),
        (
            "/api/v1/accuracy/horizon",
            {"start": "2026-01-15T00:00:00", "end": "2026-01-16T00:00:00"},
        ),
    ],
)
def test_invalid_requests_are_rejected(
    client: TestClient, path: str, params: dict[str, object]
) -> None:
    response = client.get(path, params=params)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_window_edges_are_accepted(client: TestClient) -> None:
    for day in ("2026-01-02", "2026-02-01"):
        assert client.get("/api/v1/day-ahead", params={"delivery_date": day}).status_code == 200


def test_empty_database_degrades_gracefully(client: TestClient) -> None:
    """Before the first ingestion every view still answers, with no numbers."""
    day = client.get("/api/v1/day-ahead", params={"delivery_date": "2026-01-15"}).json()
    assert day["forecast_publish_time"] is None
    assert (day["summary"], day["calibration"], day["stats"], day["actual_mwh"]) == (None,) * 4
    assert day["points"] == []

    acc = client.get("/api/v1/accuracy/day-ahead").json()
    assert (acc["stats"], acc["adjusted_stats"], acc["band_coverage_pct"]) == (None, None, None)
    assert len(acc["daily"]) == 31
    assert acc["by_hour"] == acc["error_histogram"] == []

    assert client.get("/api/v1/accuracy/horizon").json()["buckets"] == []
    assert client.get("/api/v1/series").json()["points"] == []

    meta = client.get("/api/v1/meta").json()
    assert meta["data"]["actuals"]["rows"] == 0
    assert meta["data"]["last_ingested_at"] is None


def test_no_run_before_cutoff_means_no_forecast(client: TestClient, seeded: Session) -> None:
    # The earliest run for Jan 15 was published 07:30 on Jan 14: a 06:00 cutoff predates it.
    body = client.get(
        "/api/v1/day-ahead", params={"delivery_date": "2026-01-15", "cutoff": "06:00"}
    ).json()
    assert body["forecast_publish_time"] is None
    assert body["summary"] is None
    assert body["actual_mwh"] == 24 * 10_000  # the outturn is still shown
