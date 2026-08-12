"""Add composite indexes for large tenant/provider directories.

Revision ID: 245
Revises: 244
"""
from alembic import op


revision = "245"
down_revision = "244"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_tenants_vertical_created_id",
        "tenants",
        ["vertical", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_tenants_vertical_status_created",
        "tenants",
        ["vertical", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_tenants_vertical_verification_created",
        "tenants",
        ["vertical", "verification_status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tenants_vertical_verification_created", table_name="tenants")
    op.drop_index("ix_tenants_vertical_status_created", table_name="tenants")
    op.drop_index("ix_tenants_vertical_created_id", table_name="tenants")
