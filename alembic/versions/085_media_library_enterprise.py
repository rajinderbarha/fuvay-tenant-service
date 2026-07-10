"""Phase 0E Media Library Enterprise Upgrade.

Adds:
  - Additional columns on media_assets: flagged, flag_reason, moderation_status,
    scan_status (rename/enhance), thumbnail_key, visibility, media_number (display ID)
  - media_links: associate media to modules/records
  - media_signed_links: track generated signed URLs
  - media_audit_logs: full audit trail per file
  - media_storage_usage: aggregate storage tracking

Revision ID: 085
Revises: 084
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "085"
down_revision = "084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enhance media_assets ─────────────────────────────────────────────────
    op.add_column("media_assets", sa.Column("media_number",       sa.String(30),  nullable=True))
    op.add_column("media_assets", sa.Column("thumbnail_key",      sa.String(1000),nullable=True))
    op.add_column("media_assets", sa.Column("visibility",         sa.String(30),  nullable=False, server_default="private"))
    op.add_column("media_assets", sa.Column("processing_status",  sa.String(30),  nullable=False, server_default="ready"))
    op.add_column("media_assets", sa.Column("scan_status",        sa.String(30),  nullable=False, server_default="not_scanned"))
    op.add_column("media_assets", sa.Column("moderation_status",  sa.String(30),  nullable=False, server_default="clean"))
    op.add_column("media_assets", sa.Column("is_flagged",         sa.Boolean(),   nullable=False, server_default="false"))
    op.add_column("media_assets", sa.Column("flag_reason",        sa.String(80),  nullable=True))
    op.add_column("media_assets", sa.Column("flagged_at",         sa.DateTime(timezone=True), nullable=True))
    op.add_column("media_assets", sa.Column("uploaded_from_app",  sa.String(60),  nullable=True))
    op.add_column("media_assets", sa.Column("tags_json",          postgresql.JSONB(), nullable=True, server_default="[]"))
    op.add_column("media_assets", sa.Column("description",        sa.String(500), nullable=True))
    op.add_column("media_assets", sa.Column("linked_module",      sa.String(60),  nullable=True))
    op.add_column("media_assets", sa.Column("linked_record_id",   sa.String(100), nullable=True))
    op.add_column("media_assets", sa.Column("archived_at",        sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ma_flagged",     "media_assets", ["is_flagged"])
    op.create_index("ix_ma_visibility",  "media_assets", ["visibility"])
    op.create_index("ix_ma_created_at",  "media_assets", ["created_at"])

    # ── media_links ──────────────────────────────────────────────────────────
    op.create_table(
        "media_links",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("media_id",    postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_name", sa.String(80),  nullable=False),
        sa.Column("record_type", sa.String(80),  nullable=False),
        sa.Column("record_id",   sa.String(100), nullable=False),
        sa.Column("display_name",sa.String(255), nullable=True),
        sa.Column("status",      sa.String(30),  nullable=False, server_default="active"),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ml_media",  "media_links", ["media_id"])
    op.create_index("ix_ml_record", "media_links", ["module_name", "record_type", "record_id"])

    # ── media_signed_links ───────────────────────────────────────────────────
    op.create_table(
        "media_signed_links",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("media_id",          postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id",postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose",           sa.String(30), nullable=False, server_default="preview"),
        sa.Column("token",             sa.String(128), nullable=False, unique=True),
        sa.Column("expires_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("status",            sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_msl_media",  "media_signed_links", ["media_id"])
    op.create_index("ix_msl_token",  "media_signed_links", ["token"])
    op.create_index("ix_msl_status", "media_signed_links", ["status"])

    # ── media_audit_logs ─────────────────────────────────────────────────────
    op.create_table(
        "media_audit_logs",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("media_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",      sa.String(60),  nullable=True),
        sa.Column("action_type",     sa.String(80),  nullable=False),
        sa.Column("tenant_id",       postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_hash",         sa.String(64),  nullable=True),
        sa.Column("request_id",      sa.String(80),  nullable=True),
        sa.Column("metadata_json",   postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_mal_media",   "media_audit_logs", ["media_id"])
    op.create_index("ix_mal_actor",   "media_audit_logs", ["actor_user_id"])
    op.create_index("ix_mal_action",  "media_audit_logs", ["action_type"])
    op.create_index("ix_mal_created", "media_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("media_audit_logs")
    op.drop_table("media_signed_links")
    op.drop_table("media_links")

    op.drop_index("ix_ma_created_at", "media_assets")
    op.drop_index("ix_ma_visibility",  "media_assets")
    op.drop_index("ix_ma_flagged",     "media_assets")
    for col in ("archived_at", "linked_record_id", "linked_module", "description",
                "tags_json", "uploaded_from_app", "flagged_at", "flag_reason", "is_flagged",
                "moderation_status", "scan_status", "processing_status",
                "visibility", "thumbnail_key", "media_number"):
        op.drop_column("media_assets", col)
