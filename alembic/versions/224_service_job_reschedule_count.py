"""CANCEL-RESCHEDULE-FOUNDATION -- additive `reschedule_count` column on
service_jobs. The customer self-service reschedule mutation
(HomeServiceJobAssignmentService.customer_reschedule_booking) previously had
no cap at all; policy decision resolved 2026-08-02: cap customer-initiated
reschedules at MAX_RESCHEDULE_COUNT (3), mirroring the disconnected legacy
`booking` engine's limit but enforced on the real ServiceJob this time.
Nullable-with-server-default so existing rows backfill to 0 without a data
migration.

Revision ID: 224
Revises: 223
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "224"
down_revision = "223"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_jobs",
        sa.Column("reschedule_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("service_jobs", "reschedule_count")
