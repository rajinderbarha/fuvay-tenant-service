"""FINAL-L5-05K — Finance Hub Credit Top-up Migration.

Adds usage_credit_ledger_event_id to credit_topup_orders so the top-up
grant (moved off ledger.credit_wallet/TenantWallet onto the canonical
UsageCreditService in this sprint) can reference its usage_credit_ledger
row the same way it previously referenced a wallet_transaction_id. The
legacy wallet_transaction_id column is left in place (historical data,
never deleted) but is no longer written by new code.

Revision ID: 134
Revises: 133
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "134"
down_revision = "133"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("credit_topup_orders")}
    if "usage_credit_ledger_event_id" not in cols:
        op.add_column(
            "credit_topup_orders",
            sa.Column("usage_credit_ledger_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("credit_topup_orders")}
    if "usage_credit_ledger_event_id" in cols:
        op.drop_column("credit_topup_orders", "usage_credit_ledger_event_id")
