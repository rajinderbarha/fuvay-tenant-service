"""MODULE-L5-02 bug #16 fix — add missing updated_at column to financial_events.

Same systemic model/migration drift fixed before (see migration 131 and
122-129): the ORM model FinancialEvent(ServiceOSBase) declares updated_at via
the shared timestamp mixin, but migration 041 created financial_events with only
created_at. Every financial-event audit write (invoice creation, payment
recording, commission) INSERTs an updated_at value, so against a real migrated
DB the whole post-completion financial flow died with
`UndefinedColumnError: column "updated_at" of relation "financial_events"`
(500). Unit tests missed it because they build the schema from model metadata
(which includes updated_at), not from the migration history.

Revision ID: 137
Revises: 136
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "137"
down_revision = "136"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("financial_events")]
    if "updated_at" not in columns:
        op.add_column(
            "financial_events",
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
    columns = [c["name"] for c in inspector.get_columns("financial_events")]
    if "updated_at" in columns:
        op.drop_column("financial_events", "updated_at")
