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
