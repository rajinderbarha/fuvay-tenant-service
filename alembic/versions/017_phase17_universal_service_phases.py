"""Phase 17 — Universal Service Phase Logic (repair / service / consultation job types)

Adds job_type + assessment/checklist fields to jobs, and a new job_quotes
table for assessment-driven price quotes with customer approve/reject.

Revision ID: 017
Revises: 016
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("job_type", sa.String(20), nullable=False, server_default="repair"))
    op.add_column("jobs", sa.Column("parent_job_id", UUID(as_uuid=True), nullable=True))
    op.add_column("jobs", sa.Column("findings", sa.Text, nullable=True))
    op.add_column("jobs", sa.Column("recommendation", sa.Text, nullable=True))
    op.add_column("jobs", sa.Column("checklist", JSONB, nullable=False, server_default="[]"))
    op.add_column("jobs", sa.Column("duration_estimate_minutes", sa.Integer, nullable=True))
    op.create_index("ix_job_parent", "jobs", ["parent_job_id"])

    op.create_table("job_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("line_items", JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_jq_job_id", "job_quotes", ["job_id"])
    op.create_index("ix_jq_tenant", "job_quotes", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_jq_tenant", table_name="job_quotes")
    op.drop_index("ix_jq_job_id", table_name="job_quotes")
    op.drop_table("job_quotes")

    op.drop_index("ix_job_parent", table_name="jobs")
    op.drop_column("jobs", "duration_estimate_minutes")
    op.drop_column("jobs", "checklist")
    op.drop_column("jobs", "recommendation")
    op.drop_column("jobs", "findings")
    op.drop_column("jobs", "parent_job_id")
    op.drop_column("jobs", "job_type")
