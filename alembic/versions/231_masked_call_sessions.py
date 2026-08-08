"""Masked calling — job-scoped call sessions so neither party ever learns the
other's real phone number.

Off-platform leakage prevention. The flow requires the technician to phone the
customer as their first task, and a real phone number handed over once is a
permanent private channel: the next job goes direct and the platform never
sees it. So the platform bridges the call instead -- it dials both legs, both
sides see only the platform's caller id, and the binding is scoped to ONE job.

Design points that matter:
  - Real numbers are NOT stored on this row. They are read from the booking/
    staff record at dial time and handed straight to the telephony provider.
    Copying them here would create a second place a leak could come from, for
    no benefit.
  - `provider_call_id` is what a status webhook is matched on, and is UNIQUE:
    a replayed callback cannot create a second session or double-count a call.
  - `expires_at` makes the binding time-bound as well as job-bound.
  - Recording url is stored, not audio, and only if the provider returns one.

Revision ID: 231
Revises: 230
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "231"
down_revision = "230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "masked_call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Who asked for the call, and in which direction.
        sa.Column("initiated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initiator_role", sa.String(length=20), nullable=False),
        sa.Column("direction", sa.String(length=30), nullable=False),
        # Telephony provider linkage. provider_call_id is UNIQUE so a replayed
        # status webhook cannot be processed twice.
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_call_id", sa.String(length=120), nullable=True),
        # The platform number BOTH sides see. Safe to store -- it is ours.
        sa.Column("caller_id_used", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="requested"),
        sa.Column("failure_reason", sa.String(length=200), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("recording_url", sa.String(length=1000), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_call_id", name="uq_mcs_provider_call_id"),
    )
    op.create_index("ix_mcs_job", "masked_call_sessions", ["job_id"])
    op.create_index("ix_mcs_tenant_status", "masked_call_sessions", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_mcs_tenant_status", table_name="masked_call_sessions")
    op.drop_index("ix_mcs_job", table_name="masked_call_sessions")
    op.drop_table("masked_call_sessions")
