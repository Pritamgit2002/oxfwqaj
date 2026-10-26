from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import sqlite

from tests.conftest import utc
from windsight.db.models import UTCDateTime
from windsight.domain import ForecastPoint


def test_horizon_hours_is_lead_time_from_publish_to_target() -> None:
    point = ForecastPoint(utc(2026, 1, 14, 7, 30), utc(2026, 1, 15, 12), 9_000.0)
    assert point.horizon_hours == pytest.approx(28.5)
    assert ForecastPoint(utc(2026, 1, 15), utc(2026, 1, 15), 1.0).horizon_hours == 0


def test_utc_column_rejects_naive_and_normalises_offsets() -> None:
    col, dialect = UTCDateTime(), sqlite.dialect()
    with pytest.raises(ValueError, match="naive"):
        col.process_bind_param(datetime(2026, 1, 15), dialect)  # noqa: DTZ001
    bst = datetime(2026, 7, 1, 9, tzinfo=timezone(timedelta(hours=1)))
    assert col.process_bind_param(bst, dialect) == utc(2026, 7, 1, 8)
    assert col.process_bind_param(None, dialect) is None


def test_utc_column_hands_back_aware_utc() -> None:
    col, dialect = UTCDateTime(), sqlite.dialect()
    # SQLite returns naive values; they were stored as UTC.
    assert col.process_result_value(datetime(2026, 1, 15, 9), dialect) == utc(2026, 1, 15, 9)  # noqa: DTZ001
    assert col.process_result_value(None, dialect) is None
