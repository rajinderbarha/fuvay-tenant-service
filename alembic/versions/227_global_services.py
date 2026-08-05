"""GLOBAL-SERVICES (2026-08-05) -- platform-owned promotional service
listings shown to every customer nationwide, independent of vertical/
category/tenant serviceability, plus the customer-interest leads they
generate. Two new tables, no changes to existing ones.

Revision ID: 227
Revises: 226
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "227"
down_revision = "226"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_global_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tagline", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_pgs_active", "platform_global_services", ["is_active"])

    op.create_table(
        "global_service_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("global_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("zipcode", sa.String(length=10), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("assigned_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_gsl_service", "global_service_leads", ["global_service_id"])
    op.create_index("ix_gsl_status", "global_service_leads", ["status"])
    op.create_index("ix_gsl_customer", "global_service_leads", ["customer_id"])


def downgrade() -> None:
    op.drop_table("global_service_leads")
    op.drop_table("platform_global_services")
