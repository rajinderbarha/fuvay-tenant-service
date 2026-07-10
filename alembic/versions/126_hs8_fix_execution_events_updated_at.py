"""HS8 fix — add missing updated_at column to service_job_execution_events.

Same systemic gap as migrations 122-125: the ORM model declares
updated_at via TimestampMixin but the table's original migration never
added it. This table logs every technician status transition
(on-the-way, reached-site, inspection, service-started, work-done,
parts/quote-required, notes, media) — a real, confirmed 500 on every
single execution-workflow action, found live-verifying HS8.

Revision ID: 126
Revises: 125
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "126"
down_revision = "125"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("service_job_execution_events")]
    if "updated_at" not in columns:
        op.add_column(
            "service_job_execution_events",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("service_job_execution_events")]
    if "updated_at" in columns:
        op.drop_column("service_job_execution_events", "updated_at")
