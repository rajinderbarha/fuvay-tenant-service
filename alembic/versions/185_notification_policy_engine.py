"""NOTIFICATION-CENTER-REBUILD Phase 3/4: NotificationPolicy engine --
the Event Policies tab's backing entity (see policy_models.py docstring
for how this differs from the event registry and the template model).

Revision ID: 185
Revises: 184
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "185"
down_revision = "184"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_key", sa.String(120), nullable=False),
        sa.Column("vertical_key", sa.String(80), nullable=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("delivery_mode", sa.String(20), nullable=False, server_default="immediate"),
        sa.Column("required_channels", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("primary_channels", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("fallback_channels", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("escalation_delay_minutes", sa.Integer, nullable=True),
        sa.Column("consent_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("retry_interval_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("dedup_window_seconds", sa.Integer, nullable=False, server_default="600"),
        sa.Column("rate_limit_per_hour", sa.Integer, nullable=True),
        sa.Column("quiet_hours_start", sa.String(5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(5), nullable=True),
        sa.Column("severity_override_bypasses_quiet_hours", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("expiry_minutes", sa.Integer, nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("event_key", "vertical_key", "version_number", name="uq_notif_policy_version"),
    )
    op.create_index("ix_notif_policy_event", "notification_policies", ["event_key"])
    op.create_index("ix_notif_policy_vertical", "notification_policies", ["vertical_key"])
    op.create_index("ix_notif_policy_current", "notification_policies", ["event_key", "vertical_key"],
                     unique=True, postgresql_where=sa.text("is_current = true"))

    op.create_table(
        "notification_policy_recipient_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_role", sa.String(30), nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.UniqueConstraint("policy_id", "recipient_role", name="uq_npr_policy_role"),
    )
    op.create_index("ix_npr_policy", "notification_policy_recipient_rules", ["policy_id"])

    op.create_table(
        "notification_policy_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_key", sa.String(120), nullable=False),
        sa.Column("vertical_key", sa.String(80), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(60), nullable=False),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
    )
    op.create_index("ix_npal_policy", "notification_policy_audit_logs", ["policy_id"])
    op.create_index("ix_npal_event", "notification_policy_audit_logs", ["event_key"])


def downgrade() -> None:
    op.drop_table("notification_policy_audit_logs")
    op.drop_table("notification_policy_recipient_rules")
    op.drop_index("ix_notif_policy_current", table_name="notification_policies")
    op.drop_index("ix_notif_policy_vertical", table_name="notification_policies")
    op.drop_index("ix_notif_policy_event", table_name="notification_policies")
    op.drop_table("notification_policies")
