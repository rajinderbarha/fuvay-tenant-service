"""Canonical top-up invoices and non-bookable health finance guard.

Revision ID: 387
Revises: 386
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "387"
down_revision = "386"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("activation_payment_orders", sa.Column("invoice_number", sa.String(50), nullable=True))
    op.add_column("activation_payment_orders", sa.Column("invoice_issued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("activation_payment_orders", sa.Column("plan_snapshot_json", postgresql.JSONB(), nullable=True))
    op.add_column("activation_payment_orders", sa.Column("invoice_issuer_snapshot_json", postgresql.JSONB(), nullable=True))
    op.add_column("activation_payment_orders", sa.Column("invoice_buyer_snapshot_json", postgresql.JSONB(), nullable=True))
    op.create_unique_constraint("uq_apo_invoice_number", "activation_payment_orders", ["invoice_number"])
    op.execute("CREATE SEQUENCE IF NOT EXISTS hs_topup_invoice_number_seq START WITH 1")

    # Existing captured top-up purchases become downloadable too.  Their
    # plan/legal snapshots are completed lazily on first invoice read because
    # old rows predate immutable snapshots.
    op.execute("""
        UPDATE activation_payment_orders
           SET invoice_number = 'FV' || to_char(COALESCE(captured_at, created_at), 'YYYY') || 'HS' ||
                                lpad(nextval('hs_topup_invoice_number_seq')::text, 8, '0'),
               invoice_issued_at = COALESCE(captured_at, created_at)
         WHERE status = 'captured'
           AND payment_kind = 'activation_funding'
           AND invoice_number IS NULL
    """)

    op.add_column(
        "vertical_monetization_policies",
        sa.Column(
            "provider_non_bookable_health_charge_mode", sa.String(30),
            nullable=False, server_default="BASE_RATE_ONLY",
        ),
    )


def downgrade() -> None:
    op.drop_column("vertical_monetization_policies", "provider_non_bookable_health_charge_mode")
    op.drop_constraint("uq_apo_invoice_number", "activation_payment_orders", type_="unique")
    op.drop_column("activation_payment_orders", "invoice_buyer_snapshot_json")
    op.drop_column("activation_payment_orders", "invoice_issuer_snapshot_json")
    op.drop_column("activation_payment_orders", "plan_snapshot_json")
    op.drop_column("activation_payment_orders", "invoice_issued_at")
    op.drop_column("activation_payment_orders", "invoice_number")
    op.execute("DROP SEQUENCE IF EXISTS hs_topup_invoice_number_seq")
