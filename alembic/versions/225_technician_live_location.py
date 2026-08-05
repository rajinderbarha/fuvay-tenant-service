"""TRACK-TECHNICIAN -- new technician_live_locations table.

No live-location capability existed anywhere in the canonical
ServiceBooking/ServiceJob pipeline before this (audit confirmed: only a
one-shot lat/lng capture existed on the disconnected/dead field_ops.Job
table). One row per job holds the technician's LATEST GPS fix only --
overwritten in place on each submission, never appended -- so no location
history accumulates beyond "right now".

Revision ID: 225
Revises: 224
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "225"
down_revision = "224"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "technician_live_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("accuracy_meters", sa.Numeric(8, 2), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tll_job_id", "technician_live_locations", ["job_id"], unique=True)
    op.create_index("ix_tll_staff_id", "technician_live_locations", ["staff_id"])


def downgrade() -> None:
    op.drop_index("ix_tll_staff_id", table_name="technician_live_locations")
    op.drop_index("ix_tll_job_id", table_name="technician_live_locations")
    op.drop_table("technician_live_locations")
