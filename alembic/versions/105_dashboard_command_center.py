"""Platform Command Center Dashboard — migration 104.

Adds only the persistence the dashboard genuinely needs beyond existing
tables: action-queue override state (resolve/snooze/assign for computed
action-queue items sourced live from tenants/complaints/disputes/etc, keyed
by a deterministic action_key rather than a duplicated row per source table)
and exported snapshots. Every other dashboard section reads live from
pre-existing tables (tenants, jobs, commission_records, wallet_transactions,
customer_service_credits, security_deposits, customer_complaints,
dispute_settlements, health_scores, platform_audit_logs) — no duplication.

Revision ID: 104
Revises: 103
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import text

revision = "105"
down_revision = "104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_action_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("action_key", sa.Text, unique=True, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("assigned_to_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    op.create_index("ix_das_status", "dashboard_action_states", ["status"])

    op.create_table(
        "dashboard_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("snapshot_json", JSONB, nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )


def downgrade() -> None:
    op.drop_table("dashboard_snapshots")
    op.drop_table("dashboard_action_states")
