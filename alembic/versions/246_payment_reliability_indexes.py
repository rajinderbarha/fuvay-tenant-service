"""Add bounded lookup indexes for customer payment reliability.

Revision ID: 246
Revises: 245
"""
from alembic import op


revision = "246"
down_revision = "245"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_spr_customer_reconciliation",
        "service_payment_records",
        ["customer_id", "reconciliation_status"],
        unique=False,
    )
    op.create_index(
        "ix_spr_tenant_customer_reconciliation",
        "service_payment_records",
        ["tenant_id", "customer_id", "reconciliation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_spr_tenant_customer_reconciliation",
        table_name="service_payment_records",
    )
    op.drop_index(
        "ix_spr_customer_reconciliation",
        table_name="service_payment_records",
    )
