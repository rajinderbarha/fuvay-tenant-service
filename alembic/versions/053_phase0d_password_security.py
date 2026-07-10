"""Phase 0D — Force Password Change + Admin Reset.

Adds:
- 5 missing security fields to `users` table
- `password_reset_tokens` table for admin-issued reset tokens

Revision ID: 053
Revises: 052
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── New security columns on users ────────────────────────────────────────
    op.add_column("users", sa.Column("password_reset_required", sa.Boolean(),
                                     nullable=False, server_default="false"))
    op.add_column("users", sa.Column("temporary_password_active", sa.Boolean(),
                                     nullable=False, server_default="false"))
    op.add_column("users", sa.Column("password_expires_at",
                                     sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_password_reset_at",
                                     sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_password_reset_by_admin_id",
                                     postgresql.UUID(as_uuid=True), nullable=True))

    # ── password_reset_tokens table ──────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("purpose", sa.String(50), nullable=False),   # force_change|forgot_password|admin_reset
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_ip", sa.String(50), nullable=True),
        sa.Column("used_ip", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prt_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_prt_token_hash", "password_reset_tokens", ["token_hash"])
    op.create_index("ix_prt_status", "password_reset_tokens", ["status"])


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "last_password_reset_by_admin_id")
    op.drop_column("users", "last_password_reset_at")
    op.drop_column("users", "password_expires_at")
    op.drop_column("users", "temporary_password_active")
    op.drop_column("users", "password_reset_required")
