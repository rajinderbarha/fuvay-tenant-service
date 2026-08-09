"""Cached weather readings.

Cached in the database, not in process memory: several workers serve the same PIN
codes, and an in-memory cache would multiply the API calls by the worker count --
exactly what a free provider tier cannot absorb.

One row per (place, kind, target_hour), overwritten in place, so the table stays
proportional to the PIN codes served rather than growing with traffic.

Revision ID: 241
Revises: 240
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "241"
down_revision = "240"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weather_readings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("place", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="current"),
        sa.Column("target_hour", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("condition", sa.String(120), nullable=True),
        sa.Column("rain_mm", sa.Float(), nullable=False, server_default="0"),
        sa.Column("wind_kmh", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    # NULLS NOT DISTINCT so a current reading (target_hour IS NULL) is genuinely
    # unique per place: with the default, every refresh would insert another row.
    op.execute(sa.text(
        "CREATE UNIQUE INDEX uq_weather_place_kind_hour ON weather_readings "
        "(place, kind, target_hour) NULLS NOT DISTINCT"
    ))
    op.create_index("ix_weather_fetched_at", "weather_readings", ["fetched_at"])


def downgrade() -> None:
    op.drop_index("ix_weather_fetched_at", table_name="weather_readings")
    op.execute(sa.text("DROP INDEX IF EXISTS uq_weather_place_kind_hour"))
    op.drop_table("weather_readings")
