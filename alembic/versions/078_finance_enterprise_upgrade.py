"""Finance Hub Enterprise Upgrade
- Create credit_topup_orders (tracks the full top-up lifecycle: initiated -> credited/failed)
- Extend security_deposits with hold_state, rejection_reason, clarification_notes, approved_by, approved_at
- Extend warranty_claims with assigned_reviewer_id, settled_at, settled_amount, documents_requested_at/notes
- Extend payout_records with payout_number, payout_type, approved_amount, approved_by, approved_at, rejection_reason

Revision ID: 078
Revises: 077
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    def _table_exists(t: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    # ── credit_topup_orders ──────────────────────────────────────────────────────
    if not _table_exists("credit_topup_orders"):
        op.create_table(
            "credit_topup_orders",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("credit_package_id", UUID(as_uuid=True), nullable=True),
            sa.Column("order_ref", sa.String(60), nullable=True),
            sa.Column("credits_purchased", sa.Numeric(14, 4), server_default="0", nullable=False),
            sa.Column("bonus_credits", sa.Numeric(14, 4), server_default="0", nullable=False),
            sa.Column("amount_paid", sa.Numeric(12, 2), server_default="0", nullable=False),
            sa.Column("currency", sa.String(10), server_default="'INR'", nullable=False),
            sa.Column("payment_method", sa.String(30), nullable=True),
            sa.Column("payment_status", sa.String(30), server_default="'initiated'", nullable=False),
            sa.Column("wallet_credit_status", sa.String(20), server_default="'pending'", nullable=False),
            sa.Column("wallet_transaction_id", UUID(as_uuid=True), nullable=True),
            sa.Column("gateway_order_id", sa.String(100), nullable=True),
            sa.Column("gateway_payment_id", sa.String(100), nullable=True),
            sa.Column("failure_reason", sa.String(500), nullable=True),
            sa.Column("refunded_amount", sa.Numeric(12, 2), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                      nullable=False),
        )
        op.create_index("ix_cto_tenant_id", "credit_topup_orders", ["tenant_id"])
        op.create_index("ix_cto_payment_status", "credit_topup_orders", ["payment_status"])
        op.create_index("ix_cto_order_ref", "credit_topup_orders", ["order_ref"])

    # ── security_deposits ─────────────────────────────────────────────────────────
    if not _col_exists("security_deposits", "hold_state"):
        op.add_column("security_deposits", sa.Column("hold_state", sa.String(20), nullable=True))
    if not _col_exists("security_deposits", "rejection_reason"):
        op.add_column("security_deposits", sa.Column("rejection_reason", sa.String(500), nullable=True))
    if not _col_exists("security_deposits", "clarification_notes"):
        op.add_column("security_deposits", sa.Column("clarification_notes", sa.Text(), nullable=True))
    if not _col_exists("security_deposits", "approved_by"):
        op.add_column("security_deposits", sa.Column("approved_by", UUID(as_uuid=True), nullable=True))
    if not _col_exists("security_deposits", "approved_at"):
        op.add_column("security_deposits", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))

    # ── warranty_claims ───────────────────────────────────────────────────────────
    if not _col_exists("warranty_claims", "assigned_reviewer_id"):
        op.add_column("warranty_claims", sa.Column("assigned_reviewer_id", UUID(as_uuid=True), nullable=True))
    if not _col_exists("warranty_claims", "settled_at"):
        op.add_column("warranty_claims", sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("warranty_claims", "settled_amount"):
        op.add_column("warranty_claims", sa.Column("settled_amount", sa.Numeric(10, 2), nullable=True))
    if not _col_exists("warranty_claims", "documents_requested_at"):
        op.add_column("warranty_claims", sa.Column("documents_requested_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("warranty_claims", "documents_requested_notes"):
        op.add_column("warranty_claims", sa.Column("documents_requested_notes", sa.Text(), nullable=True))

    # ── payout_records ────────────────────────────────────────────────────────────
    if not _col_exists("payout_records", "payout_number"):
        op.add_column("payout_records", sa.Column("payout_number", sa.String(60), nullable=True))
        conn.execute(sa.text(
            "UPDATE payout_records SET payout_number = 'PO-' || substr(id::text, 1, 8) "
            "WHERE payout_number IS NULL"))
    if not _col_exists("payout_records", "payout_type"):
        op.add_column("payout_records", sa.Column("payout_type", sa.String(30),
                                                    server_default="'tenant_settlement'", nullable=False))
    if not _col_exists("payout_records", "approved_amount"):
        op.add_column("payout_records", sa.Column("approved_amount", sa.Numeric(12, 2), nullable=True))
    if not _col_exists("payout_records", "approved_by"):
        op.add_column("payout_records", sa.Column("approved_by", UUID(as_uuid=True), nullable=True))
    if not _col_exists("payout_records", "approved_at"):
        op.add_column("payout_records", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("payout_records", "rejection_reason"):
        op.add_column("payout_records", sa.Column("rejection_reason", sa.String(500), nullable=True))


def downgrade() -> None:
    for col in ("rejection_reason", "approved_at", "approved_by", "approved_amount", "payout_type", "payout_number"):
        op.drop_column("payout_records", col)
    for col in ("documents_requested_notes", "documents_requested_at", "settled_amount", "settled_at", "assigned_reviewer_id"):
        op.drop_column("warranty_claims", col)
    for col in ("approved_at", "approved_by", "clarification_notes", "rejection_reason", "hold_state"):
        op.drop_column("security_deposits", col)
    op.drop_table("credit_topup_orders")
