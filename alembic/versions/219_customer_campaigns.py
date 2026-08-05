"""LEVEL-5 REMEDIATION (2026-08-01, Phase 11) -- Customer Campaign/Banner
backend foundation. Prior audit confirmed no backend-controlled,
ZIP-targetable customer Home-screen banner model existed anywhere in the
codebase (marketing/marketing_command_center are admin-side content-
generation tools with no customer read surface or ZIP targeting). This
migration creates the foundational table only -- no admin/customer frontend
is built in this remediation.

Revision ID: 219
Revises: 218
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "219"
down_revision = "218"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("internal_name", sa.String(200), nullable=False),
        sa.Column("eyebrow", sa.String(100), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("artwork_url_light", sa.String(1000), nullable=True),
        sa.Column("artwork_url_dark", sa.String(1000), nullable=True),
        sa.Column("cta_label", sa.String(60), nullable=True),
        sa.Column("cta_deeplink", sa.String(300), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("eligible_vertical_keys", postgresql.JSONB(), nullable=True),
        sa.Column("eligible_category_ids", postgresql.JSONB(), nullable=True),
        sa.Column("target_zipcodes", postgresql.JSONB(), nullable=True),
        sa.Column("target_zones", postgresql.JSONB(), nullable=True),
        sa.Column("target_cities", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cc_active_window", "customer_campaigns",
                     ["is_enabled", "starts_at", "ends_at"])
    op.create_index("ix_cc_priority", "customer_campaigns", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_cc_priority", table_name="customer_campaigns")
    op.drop_index("ix_cc_active_window", table_name="customer_campaigns")
    op.drop_table("customer_campaigns")
