"""ADMIN-TENANT-E2E-06 fix — add missing updated_at column to
analytics_report_runs.

Same systemic gap found repeatedly this session (migrations 122-129):
the ORM model declares updated_at via TimestampMixin but the table's
original migration never added it. This blocked GET /v1/admin/reports
entirely (500 UndefinedColumnError) — the whole Admin Reports page
could never load past its first render.

Revision ID: 131
Revises: 130
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "131"
down_revision = "130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("analytics_report_runs")]
    if "updated_at" not in columns:
        op.add_column(
            "analytics_report_runs",
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
    columns = [c["name"] for c in inspector.get_columns("analytics_report_runs")]
    if "updated_at" in columns:
        op.drop_column("analytics_report_runs", "updated_at")
