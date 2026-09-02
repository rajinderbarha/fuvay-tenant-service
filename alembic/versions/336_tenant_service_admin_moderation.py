"""Persist canonical tenant-service admin moderation state.

Revision ID: 336
Revises: 335
"""
from alembic import op
import sqlalchemy as sa


revision = "336"
down_revision = "335"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_services",
        sa.Column("admin_suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_services",
        sa.Column("admin_suspension_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_services", "admin_suspension_reason")
    op.drop_column("tenant_services", "admin_suspended_at")
