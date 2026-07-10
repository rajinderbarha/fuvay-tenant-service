"""Add customer_visible + severity_override to service_issue_mappings;
   customer_visible to master_issue_types.

Revision ID: 074
Revises: 073
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # service_issue_mappings additions
    op.add_column(
        "service_issue_mappings",
        sa.Column("customer_visible", sa.Boolean, nullable=False, server_default="true"),
    )
    op.add_column(
        "service_issue_mappings",
        sa.Column("severity_override", sa.String(30), nullable=True),
    )

    # master_issue_types additions
    op.add_column(
        "master_issue_types",
        sa.Column("customer_visible", sa.Boolean, nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("service_issue_mappings", "severity_override")
    op.drop_column("service_issue_mappings", "customer_visible")
    op.drop_column("master_issue_types", "customer_visible")
