"""HOME-SERVICES-ACTIVATION-PAYMENT-01: real online Razorpay collection for
the security-deposit and starter-credit-package activation gates.

Revision ID: 199
Revises: 198
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "199"
down_revision = "198"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activation_payment_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vertical_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_kind", sa.String(30), nullable=False),
        sa.Column("gateway", sa.String(20), nullable=False, server_default="razorpay"),
        sa.Column("gateway_order_id", sa.String(100), nullable=False),
        sa.Column("gateway_payment_id", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("credited_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("policy_version", sa.Integer(), nullable=True),
        sa.Column("raw_order_payload", postgresql.JSONB(), nullable=True),
        sa.Column("raw_webhook_payload", postgresql.JSONB(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_apo_gateway_order_id", "activation_payment_orders", ["gateway_order_id"])
    op.create_unique_constraint("uq_apo_gateway_payment_id", "activation_payment_orders", ["gateway_payment_id"])
    op.create_index("ix_apo_tenant_id", "activation_payment_orders", ["tenant_id"])
    op.create_index("ix_apo_status", "activation_payment_orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_apo_status", table_name="activation_payment_orders")
    op.drop_index("ix_apo_tenant_id", table_name="activation_payment_orders")
    op.drop_constraint("uq_apo_gateway_payment_id", "activation_payment_orders", type_="unique")
    op.drop_constraint("uq_apo_gateway_order_id", "activation_payment_orders", type_="unique")
    op.drop_table("activation_payment_orders")
