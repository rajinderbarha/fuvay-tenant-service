"""Remove the last refund-era security-deposit column.

Revision ID: 334
Revises: 333
"""
from alembic import op
import sqlalchemy as sa


revision = "334"
down_revision = "333"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE refund_requests DROP COLUMN IF EXISTS security_deposit_deducted")


def downgrade() -> None:
    op.add_column(
        "refund_requests",
        sa.Column("security_deposit_deducted", sa.Numeric(12, 2), nullable=True),
    )
