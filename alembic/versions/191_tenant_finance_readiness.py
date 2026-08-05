"""TENANT-FINANCE-READINESS: direct payment method + invoice preferences for
the Home Services onboarding Finance Readiness step (step 7 of 8).

Home Services does not collect, hold or settle the customer's job payment —
the tenant's business is paid directly. This table only records HOW the
tenant accepts that direct payment (cash/UPI/card/bank transfer) and its
invoice/receipt preferences, not any payment/settlement/payout mechanism.

Revision ID: 191
Revises: 190
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "191"
down_revision = "190"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_finance_readiness",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("accepts_cash", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("accepts_upi", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("accepts_card_at_service_location", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("accepts_bank_transfer", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("payment_confirmation_required", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("invoice_business_name", sa.String(255), nullable=True),
        sa.Column("invoice_prefix", sa.String(20), nullable=True),
        sa.Column("issue_customer_receipt", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tfr_tenant_id", "tenant_finance_readiness", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tfr_tenant_id", table_name="tenant_finance_readiness")
    op.drop_table("tenant_finance_readiness")
