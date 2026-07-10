"""HS9 — Usage Credit Ledger + Completed Job Deduction.

Adds usage_credit_ledger table. Reuses the existing real
tenant_billing.credit_balance column as the canonical usage-credit
balance (already used by the pre-existing admin add_usage_credits
flow) rather than creating a parallel balance field.

Revision ID: 129
Revises: 128
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "129"
down_revision = "128"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "usage_credit_ledger" not in inspector.get_table_names():
        op.create_table(
            "usage_credit_ledger",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("credit_delta", sa.Numeric(12, 2), nullable=False),
            sa.Column("balance_before", sa.Numeric(12, 2), nullable=False),
            sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
            sa.Column("deduction_source", sa.String(50), nullable=True),
            sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("service_type_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("brand_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("request_id", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_ucl_tenant_id", "usage_credit_ledger", ["tenant_id"])
        # Idempotency guard: exactly one completed_job_deduction row per job.
        op.create_index(
            "uq_ucl_job_event_once",
            "usage_credit_ledger",
            ["job_id", "event_type"],
            unique=True,
            postgresql_where=sa.text("job_id IS NOT NULL AND event_type = 'completed_job_deduction'"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "usage_credit_ledger" in inspector.get_table_names():
        op.drop_table("usage_credit_ledger")
