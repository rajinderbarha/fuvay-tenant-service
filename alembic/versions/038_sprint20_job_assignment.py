"""Sprint 20 — Home Service Job Assignment + Staff Lifecycle.

Adds assignment_status column to service_jobs and service_bookings.
Creates service_job_assignments and service_job_assignment_events tables.

Revision ID: 038
Revises: 037
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add assignment_status to service_jobs
    op.add_column(
        "service_jobs",
        sa.Column("assignment_status", sa.String(30), nullable=False,
                  server_default="unassigned"),
    )
    op.create_index(
        "ix_sj_assignment_status", "service_jobs", ["assignment_status"]
    )

    # 2. Add assignment_status to service_bookings
    op.add_column(
        "service_bookings",
        sa.Column("assignment_status", sa.String(30), nullable=False,
                  server_default="unassigned"),
    )

    # 3. Create service_job_assignments
    op.create_table(
        "service_job_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",                  UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",              UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",               UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_staff_member_id",UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_user_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("assignment_status",       sa.String(30), nullable=False,
                  server_default="assigned"),
        sa.Column("assignment_type",         sa.String(30), nullable=False,
                  server_default="manual"),
        sa.Column("rejection_reason",        sa.Text(),    nullable=True),
        sa.Column("scheduled_date",          sa.Date(),    nullable=True),
        sa.Column("scheduled_time_window",   sa.String(50), nullable=True),
        sa.Column("notes",                   sa.Text(),    nullable=True),
        sa.Column("is_current",              sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("accepted_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sja_job_id",    "service_job_assignments", ["job_id"])
    op.create_index("ix_sja_booking_id","service_job_assignments", ["booking_id"])
    op.create_index("ix_sja_tenant_id", "service_job_assignments", ["tenant_id"])
    op.create_index("ix_sja_staff_id",  "service_job_assignments", ["assigned_staff_member_id"])
    op.create_index("ix_sja_status",    "service_job_assignments", ["assignment_status"])
    op.create_index("ix_sja_is_current","service_job_assignments", ["is_current"])

    # 4. Create service_job_assignment_events
    op.create_table(
        "service_job_assignment_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",    sa.String(50),  nullable=True),
        sa.Column("event_type",    sa.String(60),  nullable=False),
        sa.Column("old_value",     JSONB,          nullable=True),
        sa.Column("new_value",     JSONB,          nullable=True),
        sa.Column("reason",        sa.Text(),      nullable=True),
        sa.Column("request_id",    sa.String(100), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjae_job_id",   "service_job_assignment_events", ["job_id"])
    op.create_index("ix_sjae_tenant_id","service_job_assignment_events", ["tenant_id"])
    op.create_index("ix_sjae_event_type","service_job_assignment_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("service_job_assignment_events")
    op.drop_table("service_job_assignments")
    op.drop_column("service_bookings", "assignment_status")
    op.drop_index("ix_sj_assignment_status", "service_jobs")
    op.drop_column("service_jobs", "assignment_status")
