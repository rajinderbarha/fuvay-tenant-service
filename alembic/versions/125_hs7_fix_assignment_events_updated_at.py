"""HS7 fix — add missing updated_at column to service_job_assignment_events.

Same systemic gap as migrations 122-124 (TimestampMixin declares
updated_at but the table's original migration never added it). Found
live-verifying GET /v1/customer/bookings/{id}/tracking, which reads this
table to build the customer-safe timeline — a real, confirmed 500 on
every booking tracking request.

Revision ID: 125
Revises: 124
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "125"
down_revision = "124"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("service_job_assignment_events")]
    if "updated_at" not in columns:
        op.add_column(
            "service_job_assignment_events",
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
    columns = [c["name"] for c in inspector.get_columns("service_job_assignment_events")]
    if "updated_at" in columns:
        op.drop_column("service_job_assignment_events", "updated_at")
