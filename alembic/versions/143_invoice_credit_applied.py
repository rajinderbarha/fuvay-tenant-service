"""MODULE-L5-28 — let customers apply service credits to an invoice at checkout.

Customers earn service credits (dispute settlements / refunds) but had no way to
use them: the old apply_credit_to_booking targeted the legacy `booking` table
(empty, unused), while real bookings live in service_bookings / are billed via
service_invoices, which had no field to record applied credit. This adds
credit_applied_amount to service_invoices so a customer can reduce what they owe
with their credit balance.

Revision ID: 143
Revises: 142
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "143"
down_revision = "142"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_invoices",
        sa.Column("credit_applied_amount", sa.Numeric(14, 2),
                  server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("service_invoices", "credit_applied_amount")
