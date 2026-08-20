"""Enforce one active canonical invoice per service job.

Revision ID: 267
Revises: 266
"""
from __future__ import annotations

from alembic import op

revision = "267"
down_revision = "266"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_si_active_job", "service_invoices", ["job_id"], unique=True,
        postgresql_where="status <> 'cancelled'",
    )


def downgrade() -> None:
    op.drop_index("uq_si_active_job", table_name="service_invoices")
