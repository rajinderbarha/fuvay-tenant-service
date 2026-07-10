"""Phase 22 — Tenant address fields: zipcode on tenants

Revision ID: 022
Revises: 021
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("zipcode", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "zipcode")
