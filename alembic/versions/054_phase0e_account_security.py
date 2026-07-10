"""Phase 0E — Account Security + Admin User Controls

Revision: 054
Down revision: 053

Adds:
  - users: account_status, lock_reason, locked_by_user_id,
           deactivated_at, deactivated_by_user_id, deactivation_reason,
           last_failed_login_at
  - user_sessions: revoked_by_user_id, revocation_reason
  - login_events table (login history tracking)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. users — new account security columns ───────────────────────────────
    op.add_column("users", sa.Column(
        "account_status", sa.String(20), nullable=False,
        server_default="active",
    ))
    op.add_column("users", sa.Column("lock_reason", sa.Text, nullable=True))
    op.add_column("users", sa.Column(
        "locked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True,
    ))
    op.add_column("users", sa.Column(
        "deactivated_at", sa.DateTime(timezone=True), nullable=True,
    ))
    op.add_column("users", sa.Column(
        "deactivated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True,
    ))
    op.add_column("users", sa.Column("deactivation_reason", sa.Text, nullable=True))
    op.add_column("users", sa.Column(
        "last_failed_login_at", sa.DateTime(timezone=True), nullable=True,
    ))
    op.create_index("ix_users_account_status", "users", ["account_status"])

    # ── 2. user_sessions — revocation metadata ────────────────────────────────
    op.add_column("user_sessions", sa.Column(
        "revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True,
    ))
    op.add_column("user_sessions", sa.Column(
        "revocation_reason", sa.String(255), nullable=True,
    ))

    # ── 3. login_events table ─────────────────────────────────────────────────
    op.create_table(
        "login_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email_attempted", sa.String(255), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("failure_reason", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_login_events_user_id", "login_events", ["user_id"])
    op.create_index("ix_login_events_email_attempted", "login_events", ["email_attempted"])
    op.create_index("ix_login_events_created_at", "login_events", ["created_at"])
    op.create_index("ix_login_events_event_type", "login_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("login_events")

    op.drop_column("user_sessions", "revocation_reason")
    op.drop_column("user_sessions", "revoked_by_user_id")

    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_column("users", "last_failed_login_at")
    op.drop_column("users", "deactivation_reason")
    op.drop_column("users", "deactivated_by_user_id")
    op.drop_column("users", "deactivated_at")
    op.drop_column("users", "locked_by_user_id")
    op.drop_column("users", "lock_reason")
    op.drop_column("users", "account_status")
