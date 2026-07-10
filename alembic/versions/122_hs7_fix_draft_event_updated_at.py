"""HS7 fix — add missing updated_at column to home_service_booking_draft_events.

The ORM model inherits TimestampMixin (created_at + updated_at) via
ServiceOSBase, but migration 034 only created created_at for this table.
Every insert into this event log (draft creation, field updates, provider
matching, price choice, confirmation) has been failing with
UndefinedColumnError since the table was created — a real, confirmed bug
found while live-verifying the HS7 customer booking flow start_booking_draft
step, which emits an event on every draft creation.

Revision ID: 122
Revises: 121
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "122"
down_revision = "121"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("home_service_booking_draft_events")]
    if "updated_at" not in columns:
        op.add_column(
            "home_service_booking_draft_events",
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
    columns = [c["name"] for c in inspector.get_columns("home_service_booking_draft_events")]
    if "updated_at" in columns:
        op.drop_column("home_service_booking_draft_events", "updated_at")
