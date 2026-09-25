"""Add admin-governed customer cancellation policy.

Revision ID: 384
Revises: 383
"""
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "384"
down_revision = "383"
branch_labels = None
depends_on = None


DEFAULT_REASONS = [
    {"code": "changed_mind", "label": "Changed my mind", "active": True, "requires_detail": False},
    {"code": "found_another_provider", "label": "Found another provider", "active": True, "requires_detail": False},
    {"code": "price_concern", "label": "Price concern", "active": True, "requires_detail": False},
    {"code": "schedule_conflict", "label": "Schedule conflict", "active": True, "requires_detail": False},
    {"code": "no_longer_needed", "label": "Service no longer needed", "active": True, "requires_detail": False},
    {"code": "provider_asked_to_cancel_or_pay_direct", "label": "Provider asked me to cancel or pay directly", "active": True, "requires_detail": True},
    {"code": "other", "label": "Another reason", "active": True, "requires_detail": True},
]


def upgrade() -> None:
    policy = "vertical_monetization_policies"
    op.add_column(policy, sa.Column(
        "customer_cancellation_enabled", sa.Boolean(), nullable=False,
        server_default=sa.text("true"),
    ))
    op.add_column(policy, sa.Column(
        "customer_cancellation_cutoff_minutes", sa.Integer(), nullable=False,
        server_default=sa.text("120"),
    ))
    escaped = json.dumps(DEFAULT_REASONS).replace("'", "''")
    op.add_column(policy, sa.Column(
        "customer_cancellation_reasons", postgresql.JSONB(), nullable=False,
        server_default=sa.text(f"'{escaped}'::jsonb"),
    ))
    op.create_check_constraint(
        "ck_vmp_customer_cancel_cutoff_minutes", policy,
        "customer_cancellation_cutoff_minutes BETWEEN 0 AND 10080",
    )


def downgrade() -> None:
    policy = "vertical_monetization_policies"
    op.drop_constraint("ck_vmp_customer_cancel_cutoff_minutes", policy, type_="check")
    op.drop_column(policy, "customer_cancellation_reasons")
    op.drop_column(policy, "customer_cancellation_cutoff_minutes")
    op.drop_column(policy, "customer_cancellation_enabled")
