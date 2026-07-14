"""MODULE-L5-10 — capture the customer charge as platform revenue on the invoice.

The per-category customer charge (migration 140) was applied at the booking price
snapshot (the customer sees the inclusive total), but the invoice did not carry
it — so the fee was displayed and agreed but never actually billed or booked as
revenue. This adds platform_fee_amount to service_invoices so the invoice can:
  - bill the customer the inclusive amount (customer_payable_amount = service
    value + platform fee), and
  - keep the service value separate as the provider-commission base (the provider
    must NOT be charged commission on the platform's own fee).

Revision ID: 141
Revises: 140
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "141"
down_revision = "140"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_invoices")]
    if "platform_fee_amount" not in cols:
        op.add_column("service_invoices", sa.Column(
            "platform_fee_amount", sa.Numeric(14, 2), nullable=False,
            server_default="0"))


def downgrade() -> None:
    conn = op.get_bind()
    cols = [c["name"] for c in sa.inspect(conn).get_columns("service_invoices")]
    if "platform_fee_amount" in cols:
        op.drop_column("service_invoices", "platform_fee_amount")
