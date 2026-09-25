"""Add configurable, customer-verified provider cancellation governance.

Revision ID: 383
Revises: 382
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "383"
down_revision = "382"
branch_labels = None
depends_on = None


DEFAULT_REASONS = [
    {"code": "no_technician", "label": "No technician available", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": False, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "cannot_meet_slot", "label": "Cannot meet the selected slot", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": False, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "service_skill_unavailable", "label": "Service, brand or skill unavailable", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "capacity_issue", "label": "Provider capacity or operational issue", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "customer_requested", "label": "Customer requested cancellation", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": False, "minimum_call_attempts": 1, "health_impact": False},
    {"code": "customer_unreachable", "label": "Customer unavailable or unreachable", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": True, "minimum_call_attempts": 2, "health_impact": False},
    {"code": "address_access_issue", "label": "Incorrect or inaccessible address", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": True, "minimum_call_attempts": 1, "health_impact": False},
    {"code": "safety_concern", "label": "Safety concern at the location", "outcome": "provider_cancel", "responsibility": "neutral", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": False},
    {"code": "other", "label": "Other provider reason", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
]


def upgrade() -> None:
    policy = "vertical_monetization_policies"
    op.add_column(policy, sa.Column(
        "provider_cancellation_confirmation_minutes", sa.Integer(),
        nullable=False, server_default=sa.text("15"),
    ))
    op.add_column(policy, sa.Column(
        "provider_cancellation_min_note_length", sa.Integer(),
        nullable=False, server_default=sa.text("10"),
    ))
    op.add_column(policy, sa.Column(
        "provider_cancellation_reasons", postgresql.JSONB(), nullable=False,
        server_default=sa.text("'" + __import__("json").dumps(DEFAULT_REASONS).replace("'", "''") + "'::jsonb"),
    ))
    op.create_check_constraint(
        "ck_vmp_cancel_confirmation_minutes", policy,
        "provider_cancellation_confirmation_minutes BETWEEN 1 AND 1440",
    )
    op.create_check_constraint(
        "ck_vmp_cancel_note_length", policy,
        "provider_cancellation_min_note_length BETWEEN 0 AND 500",
    )

    op.create_table(
        "service_job_cancellation_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=True),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("reason_label", sa.String(length=100), nullable=False),
        sa.Column("reason_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("provider_notes", sa.Text(), nullable=True),
        sa.Column("call_attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sjcr_job_status", "service_job_cancellation_requests", ["job_id", "status"])
    op.create_index("ix_sjcr_customer_status", "service_job_cancellation_requests", ["customer_id", "status"])
    op.create_index("ix_sjcr_expires", "service_job_cancellation_requests", ["expires_at"])
    op.create_index(
        "uq_sjcr_one_pending_per_job", "service_job_cancellation_requests", ["job_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("service_job_cancellation_requests")
    policy = "vertical_monetization_policies"
    op.drop_constraint("ck_vmp_cancel_note_length", policy, type_="check")
    op.drop_constraint("ck_vmp_cancel_confirmation_minutes", policy, type_="check")
    op.drop_column(policy, "provider_cancellation_reasons")
    op.drop_column(policy, "provider_cancellation_min_note_length")
    op.drop_column(policy, "provider_cancellation_confirmation_minutes")
