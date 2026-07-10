"""Bargain Module — Customer Range + Platform Fee Floor Fix.

Adds customer_min_price / customer_max_price / platform_fee_fixed_amount to
bargain_rules. Previously evaluate_bargain() compared a customer's counter-offer
against a flat, admin-set floor_amount with no concept of a customer-facing
display/negotiation range or platform fee — see BARGAIN_MODULE_TEST_RESULTS.md
and app/engines/admin_catalog/bargain_engine.py for the corrected formula:

    bargain_floor = customer_min_price * (1 + platform_fee_percent / 100)
                                        + platform_fee_fixed_amount

platform_fee_percent already exists on the linked ServicePricingRule and is
reused where available; platform_fee_fixed_amount is new (fixed-fee mode is
an alternative to percent-fee mode, per the ticket). floor_amount/floor_type
are kept for backward compatibility with any existing rule rows and as a
fallback when no customer_min_price is configured.

Revision ID: 116
Revises: 115
"""
from alembic import op
import sqlalchemy as sa

revision = "116"
down_revision = "115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("bargain_rules")}

    if "customer_min_price" not in existing_columns:
        op.add_column("bargain_rules", sa.Column("customer_min_price", sa.Numeric(12, 2), nullable=True))
    if "customer_max_price" not in existing_columns:
        op.add_column("bargain_rules", sa.Column("customer_max_price", sa.Numeric(12, 2), nullable=True))
    if "platform_fee_percent" not in existing_columns:
        op.add_column("bargain_rules", sa.Column("platform_fee_percent", sa.Numeric(6, 2), nullable=True))
    if "platform_fee_fixed_amount" not in existing_columns:
        op.add_column("bargain_rules", sa.Column("platform_fee_fixed_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("bargain_rules", "platform_fee_fixed_amount")
    op.drop_column("bargain_rules", "platform_fee_percent")
    op.drop_column("bargain_rules", "customer_max_price")
    op.drop_column("bargain_rules", "customer_min_price")
