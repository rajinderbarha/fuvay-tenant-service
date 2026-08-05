"""BOOKING-DETAILS-CONTRACT-FIXES (2026-08-01) -- versioned, immutable
answer snapshot on ServiceBooking. Supersedes the prior remediation
(migration-free) that copied `draft.catalog_question_answers` onto the
ALREADY-USED `issue_details` column -- audit found
`execution/mobile_inspection_service.py` reads `booking.issue_details`
expecting a DIFFERENT shape (`{"answers": [...], "notes": ...}`,
inspection-report data), so overloading it silently broke that consumer.
A dedicated column avoids the collision entirely.

Revision ID: 222
Revises: 221
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "222"
down_revision = "221"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_bookings",
        sa.Column("answer_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("service_bookings", "answer_snapshot")
