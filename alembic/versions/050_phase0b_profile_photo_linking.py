"""Phase 0B — Profile Photo Linking: business_logo_media_id + shop_photo_media_id on tenants.

Revision ID: 050
Revises: 049
Create Date: 2026-07-03 00:00:00.000000
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("business_logo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("shop_photo_media_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "shop_photo_media_id")
    op.drop_column("tenants", "business_logo_media_id")
