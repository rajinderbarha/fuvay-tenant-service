"""Align the current provider-risk table with its ORM timestamp contract.

Revision ID: 287
Revises: 286
"""
from alembic import op
import sqlalchemy as sa

revision = "287"
down_revision = "286"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "intel_risk_scores",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("intel_risk_scores", "updated_at")
