"""Phase U -- Technician Notification Preferences: per-user quiet hours (no
per-user quiet-hours concept existed anywhere -- confirmed by audit, the
only "quiet_hours" fields found are per-event/vertical admin policy, not a
personal setting) + a real Expo push-device registration table (confirmed
genuinely absent -- push existed only as an unconfigured provider stub) +
an optimistic-concurrency version counter for the preferences PATCH flow
(no version/ETag mechanism existed anywhere in this codebase).

Revision ID: 217
Revises: 216
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "217"
down_revision = "216"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("quiet_hours_start_local", sa.String(5), nullable=True))
    op.add_column("users", sa.Column("quiet_hours_end_local", sa.String(5), nullable=True))
    op.add_column("users", sa.Column("notif_prefs_version", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "staff_push_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.String(200), nullable=False),
        sa.Column("expo_push_token", sa.String(300), nullable=False),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column("app_version", sa.String(30), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "device_id", name="uq_push_device_user_device"),
    )
    op.create_index("ix_push_device_user", "staff_push_devices", ["user_id"])
    op.create_index("ix_push_device_token", "staff_push_devices", ["expo_push_token"])


def downgrade() -> None:
    op.drop_index("ix_push_device_token", table_name="staff_push_devices")
    op.drop_index("ix_push_device_user", table_name="staff_push_devices")
    op.drop_table("staff_push_devices")
    op.drop_column("users", "notif_prefs_version")
    op.drop_column("users", "quiet_hours_end_local")
    op.drop_column("users", "quiet_hours_start_local")
    op.drop_column("users", "quiet_hours_enabled")
