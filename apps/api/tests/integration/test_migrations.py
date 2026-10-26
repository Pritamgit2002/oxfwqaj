"""Alembic migrations build exactly the schema the ORM models describe."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from tests.conftest import TEST_DATABASE_URL
from windsight.core.config import Settings, get_settings
from windsight.db.models import Base
from windsight.db.session import build_engine

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Config, Engine]]:
    url = Settings(database_url=TEST_DATABASE_URL or f"sqlite:///{tmp_path / 'm.db'}").database_url
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = build_engine(url)
    _reset(engine)
    config = Config()  # no ini file: keeps alembic from reconfiguring the test's logging
    config.set_main_option("script_location", str(MIGRATIONS))
    yield config, engine
    _reset(engine)
    engine.dispose()
    get_settings.cache_clear()


def _reset(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))


def test_upgrade_matches_models_and_downgrade_removes_everything(
    db: tuple[Config, Engine],
) -> None:
    config, engine = db
    command.upgrade(config, "head")

    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == [], f"models and migrations disagree: {diff}"
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0001"

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}


def test_upgrade_is_repeatable(db: tuple[Config, Engine]) -> None:
    config, engine = db
    command.upgrade(config, "head")
    command.upgrade(config, "head")  # release phase runs on every deploy
    assert {"actual_generation", "forecast_generation", "ingestion_run"} <= set(
        inspect(engine).get_table_names()
    )
