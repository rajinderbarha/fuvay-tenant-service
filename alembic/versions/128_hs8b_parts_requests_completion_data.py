"""HS8B — Parts Approval + Completion Proof.

Adds:
  service_job_parts_requests table (real parts-request record, replacing
  the note-only "needs parts" flag from HS8)
  service_jobs.completion_data JSONB column (single validated completion
  action's payload — work summary, collected amount, payment mode,
  photo ids, technician note)

Revision ID: 128
Revises: 127
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "128"
down_revision = "127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "service_job_parts_requests" not in inspector.get_table_names():
        op.create_table(
            "service_job_parts_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("technician_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("part_name", sa.String(200), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("photo_ids", postgresql.JSONB(), nullable=True),
            sa.Column("technician_note", sa.Text(), nullable=True),
            sa.Column("customer_approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("business_approval_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(30), nullable=False, server_default="requested"),
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("request_id", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_sjpr_job_id", "service_job_parts_requests", ["job_id"])
        op.create_index("ix_sjpr_tenant_id", "service_job_parts_requests", ["tenant_id"])
        op.create_index("ix_sjpr_status", "service_job_parts_requests", ["status"])

    job_columns = [c["name"] for c in inspector.get_columns("service_jobs")]
    if "completion_data" not in job_columns:
        op.add_column("service_jobs", sa.Column("completion_data", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "service_job_parts_requests" in inspector.get_table_names():
        op.drop_table("service_job_parts_requests")
    job_columns = [c["name"] for c in inspector.get_columns("service_jobs")]
    if "completion_data" in job_columns:
        op.drop_column("service_jobs", "completion_data")
