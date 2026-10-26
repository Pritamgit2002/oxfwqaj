"""`windsight` command line, run in-process against a scratch database."""

import json
import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select

from tests.integration.fake_elexon import FakeElexon
from windsight import cli
from windsight.core.config import get_settings
from windsight.db import session as db_session
from windsight.db.models import ActualGeneration, Base, ForecastGeneration
from windsight.elexon import client as client_module

COMMITTED_SCHEMA = Path(__file__).resolve().parents[4] / "packages/api-client/openapi.json"


@pytest.fixture
def fresh_settings() -> Iterator[None]:
    for cached in (get_settings, db_session.get_engine, db_session.get_sessionmaker):
        cached.cache_clear()
    yield
    for cached in (get_settings, db_session.get_engine, db_session.get_sessionmaker):
        cached.cache_clear()


def _run(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["windsight", *args])
    cli.main()


def test_export_openapi_matches_the_committed_client_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_settings: None
) -> None:
    out = tmp_path / "nested" / "openapi.json"
    _run(monkeypatch, "export-openapi", "--out", str(out))
    exported = json.loads(out.read_text())
    assert exported == json.loads(COMMITTED_SCHEMA.read_text()), (
        "API schema changed: run `pnpm codegen` and commit packages/api-client"
    )


def test_ingest_command_loads_an_explicit_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_settings: None
) -> None:
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    Base.metadata.create_all(create_engine(url))
    monkeypatch.setenv("DATABASE_URL", url)
    real_client = client_module.ElexonClient
    fake = FakeElexon()

    def fake_client(base_url: str, timeout: float = 60.0) -> client_module.ElexonClient:
        return real_client(base_url, timeout, transport=httpx.MockTransport(fake))

    monkeypatch.setattr(client_module, "ElexonClient", fake_client)

    _run(
        monkeypatch,
        "ingest",
        "--start",
        "2026-01-15T00:00:00+00:00",
        "--end",
        "2026-01-16T00:00:00+00:00",
    )

    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(ActualGeneration)) == 48
        assert conn.scalar(select(func.count(func.distinct(ForecastGeneration.publish_time)))) == 8
    engine.dispose()


def test_unknown_command_exits_with_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "explode")
    assert exc.value.code == 2
