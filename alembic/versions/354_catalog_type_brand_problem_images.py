"""Separate app icons from Instagram artwork for catalog choices.

Revision ID: 354
Revises: 353
"""
from alembic import op
import sqlalchemy as sa


revision = "354"
down_revision = "353"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_types", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("brands", sa.Column("image_url", sa.String(500), nullable=True))
    op.add_column("master_issue_types", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("master_issue_types", "image_url")
    op.drop_column("brands", "image_url")
    op.drop_column("service_types", "image_url")
