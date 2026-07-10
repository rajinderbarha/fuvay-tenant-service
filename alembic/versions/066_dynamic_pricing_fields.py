"""Add dynamic pricing fields to master_services.

Adds columns needed for hourly/post-assessment/range pricing models
and extended requirement flags (requires_issue_type, requires_schedule,
requires_address).  All new columns are nullable / have server defaults
so existing rows are unaffected.

Revision ID: 066
Revises: 065
Create Date: 2026-07-04
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    pricing_cols = [
        ("hourly_rate",             sa.Numeric(12, 2), None),
        ("minimum_billable_hours",  sa.Numeric(12, 2), None),
        ("estimated_hours",         sa.Numeric(12, 2), None),
        ("maximum_hours",           sa.Numeric(12, 2), None),
        ("default_estimate",        sa.Numeric(12, 2), None),
        ("assessment_label",        sa.String(200),    None),
        ("customer_note",           sa.Text(),         None),
    ]
    for col, typ, _ in pricing_cols:
        if not _col_exists(conn, "master_services", col):
            op.add_column("master_services", sa.Column(col, typ, nullable=True))

    bool_cols = [
        ("show_estimated_range", "false"),
        ("requires_issue_type",  "false"),
        ("requires_schedule",    "false"),
        ("requires_address",     "false"),
    ]
    for col, default in bool_cols:
        if not _col_exists(conn, "master_services", col):
            op.add_column("master_services", sa.Column(
                col, sa.Boolean(), nullable=False, server_default=default))


def downgrade() -> None:
    conn = op.get_bind()
    for col in [
        "hourly_rate", "minimum_billable_hours", "estimated_hours",
        "maximum_hours", "default_estimate", "assessment_label",
        "customer_note", "show_estimated_range",
        "requires_issue_type", "requires_schedule", "requires_address",
    ]:
        if _col_exists(conn, "master_services", col):
            op.drop_column("master_services", col)
