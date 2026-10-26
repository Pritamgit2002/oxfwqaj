import pytest

from windsight.core.config import Settings


@pytest.mark.parametrize(
    "url",
    ["postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"],
)
def test_paas_database_urls_get_the_psycopg_driver(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:p@host:5432/db"


def test_other_database_urls_are_untouched() -> None:
    assert Settings(database_url="sqlite://").database_url == "sqlite://"


def test_ingestion_window_includes_calibration_history() -> None:
    s = Settings(calibration_window_days=28)
    start, _ = s.ingestion_window()
    assert start.date() < s.calibration_start <= s.delivery_window_start


def test_pilot_windows_are_derived_from_decision_window() -> None:
    s = Settings()
    assert (str(s.delivery_window_start), str(s.delivery_window_end)) == (
        "2026-01-02",
        "2026-02-01",
    )
    assert str(s.calibration_start) == "2025-12-04"  # 28 settled days + the unsettled D-1
    assert str(s.tz) == "Europe/London"


def test_ingestion_window_spans_history_through_last_delivery_day() -> None:
    start, end = Settings().ingestion_window()
    assert start.isoformat() == "2025-12-03T00:00:00+00:00"
    assert end.isoformat() == "2026-02-03T00:00:00+00:00"


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALIBRATION_WINDOW_DAYS", "14")
    monkeypatch.setenv("CORS_ORIGINS", '["https://example.test"]')
    monkeypatch.setenv("DEFAULT_DECISION_CUTOFF", "10:30")
    s = Settings()
    assert s.calibration_window_days == 14
    assert s.cors_origins == ["https://example.test"]
    assert str(s.default_decision_cutoff) == "10:30:00"
