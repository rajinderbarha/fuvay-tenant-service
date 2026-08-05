"""VERTICAL-MONETIZATION: two independent, vertical-scoped, versioned
monetization policies (provider-side + customer-side) plus the customer
platform-fee charge/snapshot table.

Ownership boundary (audited before this migration -- see engine docstrings):
  - Provider-side "platform earns from tenant" already has a REAL, proven
    runtime: UsageCreditLedger + deduct_for_completed_job() triggered inside
    job completion (execution/home_service_service.py), and Razorpay-verified
    credit top-up purchases (platform_commerce/service.py). This migration
    does NOT touch that pipeline -- vertical_monetization_policies.provider_*
    columns DECLARE which model a vertical uses (so the admin UI/API has one
    source of truth), they do not re-implement deduction.
  - Customer-side platform fee was previously computed/displayed in two
    disconnected places (ServiceCategory.customer_charge_pct for the
    visit-fee/no-bargain preview path; BargainRule.platform_fee_percent for
    the Low/Mid/High bargain path) but NEVER actually collected through the
    real, already-integrated Razorpay payment engine (app/engines/payment).
    This migration adds the policy + charge tables that make collection real
    and auditable, without touching either legacy display-only field.

Revision ID: 178
Revises: 177
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "178"
down_revision = "177"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vertical_monetization_policies",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        # DRAFT -> PUBLISHED -> SUPERSEDED (or ARCHIVED). Only one PUBLISHED
        # (is_current=True) row per vertical at a time.
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.false()),

        # ── Provider-side policy (declarative -- see docstring) ──────────────
        sa.Column("provider_model", sa.String(30), nullable=False, server_default="NONE"),
        sa.Column("provider_percentage", sa.Numeric(6, 3), nullable=True),
        sa.Column("provider_fixed_amount_minor", sa.BigInteger, nullable=True),
        sa.Column("provider_credit_units", sa.Integer, nullable=True),
        sa.Column("provider_subscription_plan_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_chargeable_event", sa.String(40), nullable=True),
        sa.Column("provider_min_charge_minor", sa.BigInteger, nullable=True),
        sa.Column("provider_max_charge_minor", sa.BigInteger, nullable=True),

        # ── Customer-side policy ──────────────────────────────────────────────
        sa.Column("customer_fee_model", sa.String(30), nullable=False, server_default="NONE"),
        sa.Column("customer_fee_percentage", sa.Numeric(6, 3), nullable=True),
        sa.Column("customer_fee_fixed_amount_minor", sa.BigInteger, nullable=True),
        sa.Column("customer_fee_min_minor", sa.BigInteger, nullable=True),
        sa.Column("customer_fee_max_minor", sa.BigInteger, nullable=True),
        sa.Column("customer_fee_basis", sa.String(30), nullable=False, server_default="service_subtotal"),
        # WHEN the fee is collected: before_booking_confirmation |
        # after_estimate_approval | before_work_start | on_completion
        sa.Column("collection_stage", sa.String(40), nullable=False, server_default="after_estimate_approval"),
        sa.Column("customer_fee_refund_policy", sa.String(30), nullable=False, server_default="refundable_if_job_not_started"),

        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("created_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_vmp_vertical", "vertical_monetization_policies", ["vertical_id"])
    op.create_index("ix_vmp_vertical_current", "vertical_monetization_policies",
                    ["vertical_id"], unique=True, postgresql_where=sa.text("is_current = true"))
    op.create_index("ix_vmp_vertical_version", "vertical_monetization_policies",
                    ["vertical_id", "version_number"], unique=True)

    # ── Customer platform-fee charge: the per-booking/quote snapshot + ledger
    # row. Distinct from UsageCreditLedger (provider credit units) -- this is
    # real money, tied 1:1 to a payment_records row once paid. ──────────────
    op.create_table(
        "customer_platform_fee_charges",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("vertical_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("booking_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote_version", sa.Integer, nullable=True),
        sa.Column("policy_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_version", sa.Integer, nullable=True),
        sa.Column("calculation_basis", sa.String(30), nullable=False),  # booking_price_snapshot | approved_quote | visit_fee
        sa.Column("service_subtotal_minor", sa.BigInteger, nullable=False),
        sa.Column("chargeable_subtotal_minor", sa.BigInteger, nullable=False),
        sa.Column("fee_amount_minor", sa.BigInteger, nullable=False),
        sa.Column("tax_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("discount_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("credit_amount_minor", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("total_payable_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("collection_stage", sa.String(40), nullable=False),
        # PENDING | NOT_REQUIRED | PAID | FAILED | REFUNDED | WAIVED
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("payment_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refund_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("calculation_breakdown", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("source_event", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cpfc_idempotency", "customer_platform_fee_charges", ["idempotency_key"], unique=True)
    op.create_index("ix_cpfc_booking", "customer_platform_fee_charges", ["booking_id"])
    op.create_index("ix_cpfc_job", "customer_platform_fee_charges", ["job_id"])
    op.create_index("ix_cpfc_quote", "customer_platform_fee_charges", ["quote_id"])
    op.create_index("ix_cpfc_status", "customer_platform_fee_charges", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cpfc_status", table_name="customer_platform_fee_charges")
    op.drop_index("ix_cpfc_quote", table_name="customer_platform_fee_charges")
    op.drop_index("ix_cpfc_job", table_name="customer_platform_fee_charges")
    op.drop_index("ix_cpfc_booking", table_name="customer_platform_fee_charges")
    op.drop_index("ix_cpfc_idempotency", table_name="customer_platform_fee_charges")
    op.drop_table("customer_platform_fee_charges")

    op.drop_index("ix_vmp_vertical_version", table_name="vertical_monetization_policies")
    op.drop_index("ix_vmp_vertical_current", table_name="vertical_monetization_policies")
    op.drop_index("ix_vmp_vertical", table_name="vertical_monetization_policies")
    op.drop_table("vertical_monetization_policies")
