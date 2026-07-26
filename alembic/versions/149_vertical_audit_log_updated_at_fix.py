"""Fix: vertical_audit_logs was missing `updated_at` (ServiceOSBase requires
both created_at and updated_at on every model — a real bug caught live via
direct API testing of migration 148's new enrollment-transition endpoint,
which crashed with asyncpg.UndefinedColumnError on insert).

Revision ID: 149
Revises: 148
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "149"
down_revision = "148"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vertical_audit_logs",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("vertical_audit_logs", "updated_at")
