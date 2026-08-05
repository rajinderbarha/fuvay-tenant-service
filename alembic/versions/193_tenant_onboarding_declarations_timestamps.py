"""TENANT-ONBOARDING-DECLARATIONS-TIMESTAMPS: add created_at/updated_at to
tenant_onboarding_declarations. Migration 192 created the table without them,
but the ORM model inherits ServiceOSBase (TimestampMixin), which declares
both columns on every query -- causing UndefinedColumnError on any read.

Revision ID: 193
Revises: 192
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "193"
down_revision = "192"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_onboarding_declarations",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column(
        "tenant_onboarding_declarations",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_column("tenant_onboarding_declarations", "updated_at")
    op.drop_column("tenant_onboarding_declarations", "created_at")
