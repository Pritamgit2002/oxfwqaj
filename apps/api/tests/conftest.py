from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from windsight.core.config import Settings, get_settings
from windsight.db.models import Base
from windsight.db.session import get_session
from windsight.main import create_app
from windsight.repositories.generation import GenerationRepository


@pytest.fixture
def settings() -> Settings:
    return Settings(environment="test", database_url="sqlite://")


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s


@pytest.fixture
def client(settings: Settings, session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()

    def override_session() -> Iterator[Session]:
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def _seed_day(
    repo: GenerationRepository,
    day_start: datetime,
    runs: dict[datetime, Callable[[int], float]],
    actual_mw: float = 10_000.0,
) -> None:
    """Flat half-hourly actuals for one day plus hourly forecast runs (publish -> MW by hour)."""
    repo.upsert_actuals(
        [
            {
                "start_time": day_start + timedelta(minutes=30 * i),
                "settlement_date": day_start.date(),
                "settlement_period": i + 1,
                "generation_mw": actual_mw,
                "publish_time": day_start + timedelta(minutes=30 * (i + 1)),
            }
            for i in range(48)
        ]
    )
    repo.upsert_forecasts(
        [
            {
                "publish_time": publish,
                "start_time": day_start + timedelta(hours=h),
                "generation_mw": mw(h),
            }
            for publish, mw in runs.items()
            for h in range(24)
        ]
    )


@pytest.fixture
def seeded(session: Session) -> Session:
    """Delivery day 2026-01-15 (flat 10 GW outturn) with calibration history.

    Day under test, two runs on D-1:
    - run A published 2026-01-14 07:30 UTC forecasts 11 GW (before the 09:00 cutoff)
    - run B published 2026-01-14 09:30 UTC forecasts 10 GW (after the cutoff)

    History (each day's run published 07:30 on the previous day):
    - Jan 11-13: errors alternate +2 GW / 0 by hour -> bias 1 GW, P10 0, P90 2 GW
    - Jan 14 (D-1): +9 GW error; not yet settled at D's decision, so it must be ignored
    """
    repo = GenerationRepository(session)
    for day in (11, 12, 13):
        _seed_day(
            repo,
            utc(2026, 1, day),
            {utc(2026, 1, day - 1, 7, 30): lambda h: 12_000.0 if h % 2 == 0 else 10_000.0},
        )
    _seed_day(repo, utc(2026, 1, 14), {utc(2026, 1, 13, 7, 30): lambda h: 19_000.0})
    _seed_day(
        repo,
        utc(2026, 1, 15),
        {utc(2026, 1, 14, 7, 30): lambda h: 11_000.0, utc(2026, 1, 14, 9, 30): lambda h: 10_000.0},
    )
    session.commit()
    return session
