"""Phase M -- add service_job_work_sessions for technician work-execution
elapsed-time tracking (start/pause/resume). Confirmed genuinely missing:
only the ServiceJob.status JS_SERVICE_STARTED->JS_WORK_DONE flip existed,
no pause/resume timer anywhere. Supplementary evidence only, never a
workflow-status authority.

Revision ID: 210
Revises: 209
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "210"
down_revision = "209"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_job_work_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segment_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_reason", sa.String(60), nullable=True),
        sa.Column("accumulated_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sjws_job_id", "service_job_work_sessions", ["job_id"])
    op.create_index("ix_sjws_tenant_id", "service_job_work_sessions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_sjws_tenant_id", table_name="service_job_work_sessions")
    op.drop_index("ix_sjws_job_id", table_name="service_job_work_sessions")
    op.drop_table("service_job_work_sessions")
