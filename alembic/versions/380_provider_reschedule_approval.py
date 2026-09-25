"""Add customer approval workflow for provider slot changes.

Revision ID: 380
Revises: 379
"""
from alembic import op
import sqlalchemy as sa


revision = "380"
down_revision = "379"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = "booking_reschedule_requests"
    op.add_column(table, sa.Column("job_id", sa.UUID(), nullable=True))
    op.add_column(table, sa.Column(
        "request_source", sa.String(length=20), nullable=False,
        server_default=sa.text("'customer'"),
    ))
    op.add_column(table, sa.Column("original_date", sa.String(length=10), nullable=True))
    op.add_column(table, sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(table, sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(table, sa.Column("resolved_by", sa.UUID(), nullable=True))
    op.create_index("ix_brr_job_status", table, ["job_id", "status"])
    op.create_index(
        "uq_brr_provider_pending_job", table, ["job_id"], unique=True,
        postgresql_where=sa.text("status = 'pending' AND request_source = 'provider'"),
    )

    policy = "vertical_monetization_policies"
    op.add_column(policy, sa.Column(
        "provider_reschedule_approval_hours", sa.Integer(), nullable=False,
        server_default=sa.text("24"),
    ))
    op.create_check_constraint(
        "ck_vmp_provider_reschedule_approval_hours", policy,
        "provider_reschedule_approval_hours BETWEEN 1 AND 168",
    )


def downgrade() -> None:
    policy = "vertical_monetization_policies"
    op.drop_constraint(
        "ck_vmp_provider_reschedule_approval_hours", policy, type_="check",
    )
    op.drop_column(policy, "provider_reschedule_approval_hours")

    table = "booking_reschedule_requests"
    op.drop_index("uq_brr_provider_pending_job", table_name=table)
    op.drop_index("ix_brr_job_status", table_name=table)
    for column in (
        "resolved_by", "notification_sent_at", "expires_at", "original_date",
        "request_source", "job_id",
    ):
        op.drop_column(table, column)
