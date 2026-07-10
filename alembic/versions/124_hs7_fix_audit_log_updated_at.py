"""HS7 fix — add missing updated_at column to final_creation_audit_log.

Same root cause as migrations 122/123: caught proactively while auditing
sibling tables in the confirm-booking write path (HomeServiceFinalCreation
Service._audit inserts into this table on every successful booking).

Revision ID: 124
Revises: 123
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "124"
down_revision = "123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("final_creation_audit_logs")]
    if "updated_at" not in columns:
        op.add_column(
            "final_creation_audit_logs",
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
    columns = [c["name"] for c in inspector.get_columns("final_creation_audit_logs")]
    if "updated_at" in columns:
        op.drop_column("final_creation_audit_logs", "updated_at")
