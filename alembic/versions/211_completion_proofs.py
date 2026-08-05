"""Phase N -- add service_job_completion_proofs for the pre-final-completion
proof/handover stage. Confirmed genuinely missing: the only existing
completion-shaped fields (work_summary, before/after photo ids) live inside
ServiceJob.completion_data, written atomically WITH the final `completed`
transition + commission trigger inside complete_job -- there is no separate
pre-completion capture point today.

Revision ID: 211
Revises: 210
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "211"
down_revision = "210"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_job_completion_proofs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("final_service_notes", sa.Text(), nullable=True),
        sa.Column("before_photo_ids", postgresql.JSONB(), nullable=True),
        sa.Column("after_photo_ids", postgresql.JSONB(), nullable=True),
        sa.Column("handover_status", sa.String(30), nullable=False, server_default="not_requested"),
        sa.Column("handover_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handover_last_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sjcp_job_id", "service_job_completion_proofs", ["job_id"])
    op.create_index("ix_sjcp_tenant_id", "service_job_completion_proofs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_sjcp_tenant_id", table_name="service_job_completion_proofs")
    op.drop_index("ix_sjcp_job_id", table_name="service_job_completion_proofs")
    op.drop_table("service_job_completion_proofs")
