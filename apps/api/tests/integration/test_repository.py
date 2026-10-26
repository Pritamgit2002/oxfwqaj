from datetime import timedelta

from sqlalchemy.orm import Session

from tests.conftest import utc
from windsight.db.models import IngestionRun
from windsight.repositories.generation import GenerationRepository


def _actual(start_hour: int, mw: float) -> dict[str, object]:
    start = utc(2026, 1, 15, start_hour)
    return {
        "start_time": start,
        "settlement_date": start.date(),
        "settlement_period": 2 * start_hour + 1,
        "generation_mw": mw,
        "publish_time": start + timedelta(minutes=30),
    }


def test_upsert_replaces_revised_values(session: Session) -> None:
    repo = GenerationRepository(session)
    repo.upsert_actuals([_actual(0, 9_000.0), _actual(1, 9_500.0)])
    repo.upsert_actuals([_actual(1, 9_750.0)])  # Elexon revised the outturn
    session.commit()
    assert [
        (p.start_time.hour, p.generation_mw)
        for p in repo.actuals_between(utc(2026, 1, 15), utc(2026, 1, 16))
    ] == [(0, 9_000.0), (1, 9_750.0)]


def test_upsert_handles_batches_larger_than_one_statement(session: Session) -> None:
    repo = GenerationRepository(session)
    publish = utc(2026, 1, 1)
    rows = [
        {"publish_time": publish, "start_time": publish + timedelta(hours=h), "generation_mw": h}
        for h in range(2_500)
    ]
    assert repo.upsert_forecasts(rows) == 2_500
    assert repo.upsert_forecasts([]) == 0
    assert repo.upsert_actuals([]) == 0
    session.commit()
    assert repo.dataset_stats()["forecasts"]["rows"] == 2_500


def test_reads_are_half_open_ordered_and_filter_old_runs(session: Session) -> None:
    repo = GenerationRepository(session)
    repo.upsert_actuals([_actual(h, 1.0) for h in range(3)])
    target = utc(2026, 1, 15, 12)
    repo.upsert_forecasts(
        [
            {"publish_time": utc(2026, 1, 14, 9), "start_time": target, "generation_mw": 2.0},
            {"publish_time": utc(2026, 1, 13, 9), "start_time": target, "generation_mw": 1.0},
            {
                "publish_time": utc(2026, 1, 14, 9),
                "start_time": target + timedelta(hours=1),
                "generation_mw": 3.0,
            },
        ]
    )
    session.commit()

    actuals = repo.actuals_between(utc(2026, 1, 15, 0), utc(2026, 1, 15, 2))
    assert [a.start_time.hour for a in actuals] == [0, 1]
    assert all(a.start_time.tzinfo is not None for a in actuals)

    every_run = repo.forecasts_for_targets(target, target + timedelta(hours=2))
    assert [f.generation_mw for f in every_run] == [1.0, 2.0, 3.0]  # by target, then publish
    recent = repo.forecasts_for_targets(target, target + timedelta(hours=2), utc(2026, 1, 14))
    assert [f.generation_mw for f in recent] == [2.0, 3.0]


def test_dataset_stats_track_coverage_and_last_successful_run(session: Session) -> None:
    repo = GenerationRepository(session)
    empty = repo.dataset_stats()
    assert empty["actuals"] == {"rows": 0, "first_start_time": None, "last_start_time": None}
    assert empty["forecasts"]["runs"] == 0

    repo.upsert_actuals([_actual(0, 1.0), _actual(5, 1.0)])
    ok = repo.start_ingestion_run("FUELHH", utc(2026, 1, 15), utc(2026, 1, 16))
    ok.status, ok.finished_at = "success", utc(2026, 1, 20)
    session.add(
        IngestionRun(
            dataset="WINDFOR",
            window_start=utc(2026, 1, 15),
            window_end=utc(2026, 1, 16),
            status="failed",
            finished_at=utc(2026, 1, 21),
        )
    )
    session.commit()

    stats = repo.dataset_stats()
    assert stats["actuals"]["rows"] == 2
    assert stats["actuals"]["first_start_time"] == utc(2026, 1, 15, 0)
    assert stats["actuals"]["last_start_time"] == utc(2026, 1, 15, 5)
    assert stats["last_ingested_at"] == utc(2026, 1, 20)  # the later failed run is ignored
