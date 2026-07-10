"""Fix commerce schema gaps: missing wallet/deposit/commission columns

Revision ID: 063
Revises: 062
Create Date: 2026-07-04
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenant_wallets: Sprint 5 additions ────────────────────────────────────
    op.add_column("tenant_wallets",
        sa.Column("reserved_balance", sa.Numeric(14, 4), nullable=False,
                  server_default="0.00"))
    op.add_column("tenant_wallets",
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"))
    op.add_column("tenant_wallets",
        sa.Column("low_balance_threshold", sa.Numeric(10, 2), nullable=True))
    op.add_column("tenant_wallets",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))

    # ── security_deposits: Sprint 5 additions ─────────────────────────────────
    op.add_column("security_deposits",
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("security_deposits",
        sa.Column("package_purchase_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("security_deposits",
        sa.Column("payment_reference", sa.String(200), nullable=True))

    # ── commission_records: additional columns ────────────────────────────────
    op.add_column("commission_records",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commission_records",
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commission_records",
        sa.Column("calculation_base", sa.String(20), nullable=False,
                  server_default="total_amount"))
    op.add_column("commission_records",
        sa.Column("status", sa.String(20), nullable=False, server_default="deducted"))
    op.add_column("commission_records",
        sa.Column("wallet_ledger_entry_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("commission_records",
        sa.Column("failure_reason", sa.String(500), nullable=True))
    op.add_column("commission_records",
        sa.Column("package_purchase_id", postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("commission_records", "package_purchase_id")
    op.drop_column("commission_records", "failure_reason")
    op.drop_column("commission_records", "wallet_ledger_entry_id")
    op.drop_column("commission_records", "status")
    op.drop_column("commission_records", "calculation_base")
    op.drop_column("commission_records", "payment_id")
    op.drop_column("commission_records", "invoice_id")
    op.drop_column("security_deposits", "payment_reference")
    op.drop_column("security_deposits", "package_purchase_id")
    op.drop_column("security_deposits", "refunded_at")
    op.drop_column("tenant_wallets", "is_active")
    op.drop_column("tenant_wallets", "low_balance_threshold")
    op.drop_column("tenant_wallets", "currency")
    op.drop_column("tenant_wallets", "reserved_balance")
