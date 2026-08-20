"""Harden and scale the platform media library.

Revision ID: 290
Revises: 289
"""
from alembic import op
import sqlalchemy as sa


revision = "290"
down_revision = "289"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE media_assets SET visibility = CASE WHEN is_public THEN 'public' ELSE 'private' END")
    op.execute("UPDATE media_assets SET moderation_status = 'quarantined', is_flagged = true WHERE status = 'quarantined'")
    # Previously issued links stored bearer tokens in plaintext. Expire them
    # before switching to SHA-256 token fingerprints.
    op.execute("UPDATE media_signed_links SET status = 'expired' WHERE status = 'active'")
    op.drop_index("ix_msl_token", table_name="media_signed_links")
    op.create_index("uq_msl_token_hash", "media_signed_links", ["token"], unique=True)

    # Keyset list paths: stable ordering by the selected key plus UUID.
    op.create_index(
        "ix_ma_live_created_id",
        "media_assets",
        ["created_at", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_ma_live_size_id",
        "media_assets",
        ["file_size_bytes", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_ma_live_context_created",
        "media_assets",
        ["media_context", "created_at", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_ma_live_status_created",
        "media_assets",
        ["status", "created_at", "id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_ma_live_status_created", table_name="media_assets")
    op.drop_index("ix_ma_live_context_created", table_name="media_assets")
    op.drop_index("ix_ma_live_size_id", table_name="media_assets")
    op.drop_index("ix_ma_live_created_id", table_name="media_assets")
    op.drop_index("uq_msl_token_hash", table_name="media_signed_links")
    op.create_index("ix_msl_token", "media_signed_links", ["token"])
