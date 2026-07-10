"""Phase 20 — Checklist System: checklist_template on service_catalog_items

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_catalog_items",
                   sa.Column("checklist_template", JSONB, nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("service_catalog_items", "checklist_template")
