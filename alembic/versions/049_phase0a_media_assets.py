"""Phase 0A — Media Engine Hardening: media_assets table + profile_photo_media_id on users.

Revision ID: 049
Revises: 048
Create Date: 2026-07-03 00:00:00.000000
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_type",           sa.String(60),   nullable=False),
        sa.Column("owner_id",             postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",            postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id",          postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_user_id",  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_context",        sa.String(80),   nullable=False),
        sa.Column("file_name_original",   sa.String(255),  nullable=False),
        sa.Column("file_name_stored",     sa.String(500),  nullable=False),
        sa.Column("mime_type",            sa.String(100),  nullable=False),
        sa.Column("file_extension",       sa.String(20),   nullable=False),
        sa.Column("file_size_bytes",      sa.Integer(),    nullable=False),
        sa.Column("storage_driver",       sa.String(30),   nullable=False, server_default="local"),
        sa.Column("storage_bucket",       sa.String(255),  nullable=True),
        sa.Column("storage_key",          sa.String(1000), nullable=False),
        sa.Column("public_url",           sa.String(2000), nullable=True),
        sa.Column("is_public",            sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("access_level",         sa.String(30),   nullable=False, server_default="tenant"),
        sa.Column("status",               sa.String(30),   nullable=False, server_default="active"),
        sa.Column("checksum",             sa.String(64),   nullable=True),
        sa.Column("width",                sa.Integer(),    nullable=True),
        sa.Column("height",               sa.Integer(),    nullable=True),
        sa.Column("metadata_json",        postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",           sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at",           sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ma_owner",          "media_assets", ["owner_type", "owner_id"])
    op.create_index("ix_ma_tenant",         "media_assets", ["tenant_id"])
    op.create_index("ix_ma_customer",       "media_assets", ["customer_id"])
    op.create_index("ix_ma_context",        "media_assets", ["media_context"])
    op.create_index("ix_ma_status",         "media_assets", ["status"])
    op.create_index("ix_ma_tenant_context", "media_assets", ["tenant_id", "media_context"])
    op.create_index("ix_ma_uploader",       "media_assets", ["uploaded_by_user_id"])

    # Add profile_photo_media_id to users table
    op.add_column("users", sa.Column("profile_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_photo_media_id")
    op.drop_index("ix_ma_uploader",       "media_assets")
    op.drop_index("ix_ma_tenant_context", "media_assets")
    op.drop_index("ix_ma_status",         "media_assets")
    op.drop_index("ix_ma_context",        "media_assets")
    op.drop_index("ix_ma_customer",       "media_assets")
    op.drop_index("ix_ma_tenant",         "media_assets")
    op.drop_index("ix_ma_owner",          "media_assets")
    op.drop_table("media_assets")
