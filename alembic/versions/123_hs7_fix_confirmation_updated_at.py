"""HS7 fix — add missing updated_at column to customer_booking_confirmations.

Same root cause as migration 122: the ORM model inherits TimestampMixin
(created_at + updated_at) but the original migration only created
created_at. This is the idempotency-lock table checked by every
HomeService/Coaching/RealEstate `.../confirm` endpoint (via
ConfirmationLockService.get_existing) — a real, confirmed bug found while
live-verifying the HS7 customer booking confirmation step, which failed
with UndefinedColumnError on every single confirm attempt.

Revision ID: 123
Revises: 122
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "123"
down_revision = "122"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("customer_booking_confirmations")]
    if "updated_at" not in columns:
        op.add_column(
            "customer_booking_confirmations",
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
    columns = [c["name"] for c in inspector.get_columns("customer_booking_confirmations")]
    if "updated_at" in columns:
        op.drop_column("customer_booking_confirmations", "updated_at")
