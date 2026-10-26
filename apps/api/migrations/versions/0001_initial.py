"""Initial schema: actuals, forecasts and ingestion audit.

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "actual_generation",
        sa.Column("start_time", TS, primary_key=True),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("settlement_period", sa.Integer(), nullable=False),
        sa.Column("generation_mw", sa.Float(), nullable=False),
        sa.Column("publish_time", TS, nullable=False),
        sa.Column("ingested_at", TS, nullable=False),
    )
    op.create_table(
        "forecast_generation",
        sa.Column("publish_time", TS, primary_key=True),
        sa.Column("start_time", TS, primary_key=True),
        sa.Column("generation_mw", sa.Float(), nullable=False),
        sa.Column("ingested_at", TS, nullable=False),
    )
    op.create_index("ix_forecast_generation_start_time", "forecast_generation", ["start_time"])
    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset", sa.String(32), nullable=False),
        sa.Column("window_start", TS, nullable=False),
        sa.Column("window_end", TS, nullable=False),
        sa.Column("started_at", TS, nullable=False),
        sa.Column("finished_at", TS, nullable=True),
        sa.Column("rows_upserted", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ingestion_run")
    op.drop_index("ix_forecast_generation_start_time", table_name="forecast_generation")
    op.drop_table("forecast_generation")
    op.drop_table("actual_generation")
