"""Add customer-backed Instagram arrival confirmation.

Revision ID: 378
Revises: 377
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "378"
down_revision = "377"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_job_arrival_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("staff_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("otp_hash", sa.String(64), nullable=False),
        sa.Column("failed_code_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_source", sa.String(30), nullable=True),
        sa.Column("denial_reason", sa.String(300), nullable=True),
        sa.Column("technician_latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("technician_longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("technician_accuracy_meters", sa.Numeric(8, 2), nullable=True),
        sa.Column("location_recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending','confirmed','denied','expired','superseded')",
            name="ck_sjac_status",
        ),
        sa.CheckConstraint("failed_code_attempts BETWEEN 0 AND 5", name="ck_sjac_code_attempts"),
    )
    op.create_index("ix_sjac_job_status", "service_job_arrival_challenges", ["job_id", "status"])
    op.create_index("ix_sjac_customer", "service_job_arrival_challenges", ["customer_id"])
    op.create_index("ix_sjac_expires", "service_job_arrival_challenges", ["expires_at"])
    op.create_index(
        "uq_sjac_one_pending_per_job", "service_job_arrival_challenges", ["job_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("service_job_arrival_challenges")
