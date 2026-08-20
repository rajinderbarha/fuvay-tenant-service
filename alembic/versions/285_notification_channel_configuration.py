"""Secure notification delivery-provider configuration.

Revision ID: 285
Revises: 284
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "285"
down_revision = "284"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend the canonical per-tenant table. Platform-owned providers use the
    # all-zero tenant sentinel; tenant configuration continues to use its real
    # tenant UUID and remains isolated by the existing unique constraint.
    op.add_column("notification_channel_configs", sa.Column("provider_name", sa.String(80), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("encrypted_credentials", sa.Text(), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("credential_fingerprint", sa.String(20), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("configured_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("last_test_status", sa.String(20), nullable=True))
    op.add_column("notification_channel_configs", sa.Column("last_test_message", sa.String(500), nullable=True))
    op.create_table(
        "notification_channel_config_audits",
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_channel_config_audit_channel_created", "notification_channel_config_audits", ["channel", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_notification_channel_config_audit_channel_created", table_name="notification_channel_config_audits")
    op.drop_table("notification_channel_config_audits")
    for column in (
        "last_test_message", "last_test_status", "last_tested_at", "configured_by_user_id",
        "credential_fingerprint", "encrypted_credentials", "provider_name",
    ):
        op.drop_column("notification_channel_configs", column)
