"""Phase 3 — Platform Commerce Engine (12 tables)

Revision ID: 003
Revises: 002
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── credit_packages ───────────────────────────────────────────────────────
    op.create_table("credit_packages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("credits_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("price_inr", sa.Numeric(10, 2), nullable=False),
        sa.Column("bonus_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("validity_days", sa.Integer, nullable=True),
        sa.Column("plan_restriction", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("purchase_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_revenue", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cpkg_active", "credit_packages", ["is_active"])

    # ── tenant_wallets ────────────────────────────────────────────────────────
    op.create_table("tenant_wallets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("credit_balance", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("lifetime_purchased", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("lifetime_consumed", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("last_transaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("credit_balance >= 0", name="ck_wallet_non_negative"),
        sa.UniqueConstraint("tenant_id", name="uq_wallet_tenant"),
    )

    # ── wallet_transactions (append-only ledger) ──────────────────────────────
    op.create_table("wallet_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("txn_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("balance_before", sa.Numeric(14, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 4), nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wtxn_tenant_id", "wallet_transactions", ["tenant_id"])
    op.create_index("ix_wtxn_reference", "wallet_transactions", ["reference_id"])
    op.create_index("ix_wtxn_idem_key", "wallet_transactions", ["idempotency_key"])

    # ── security_deposits ─────────────────────────────────────────────────────
    op.create_table("security_deposits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("required_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_paid", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("warranty_drawn", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("replenishment_total", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unpaid"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("razorpay_order_id", sa.String(100), nullable=True),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_deposit_tenant"),
    )

    # ── security_deposit_transactions ─────────────────────────────────────────
    op.create_table("security_deposit_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deposit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("txn_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(10, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sdtxn_deposit_id", "security_deposit_transactions", ["deposit_id"])

    # ── commission_records ────────────────────────────────────────────────────
    op.create_table("commission_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.String(100), nullable=False, unique=True),
        sa.Column("base_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("health_adjustment", sa.Numeric(5, 2), nullable=False),
        sa.Column("effective_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("job_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(10, 4), nullable=False),
        sa.Column("wallet_balance_before", sa.Numeric(14, 4), nullable=False),
        sa.Column("wallet_balance_after", sa.Numeric(14, 4), nullable=False),
        sa.Column("health_band_at_time", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("deducted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_commission_job"),
    )
    op.create_index("ix_crec_tenant_id", "commission_records", ["tenant_id"])

    # ── customer_health_scores ────────────────────────────────────────────────
    op.create_table("customer_health_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False, server_default="80.00"),
        sa.Column("band", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("signals", JSONB, nullable=False, server_default="{}"),
        sa.Column("can_book", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("advance_required_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("override_band", sa.String(20), nullable=True),
        sa.Column("override_reason", sa.String(255), nullable=True),
        sa.Column("override_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("customer_id", "tenant_id", name="uq_chs_customer_tenant"),
    )
    op.create_index("ix_chs_tenant_id", "customer_health_scores", ["tenant_id"])

    # ── customer_credit_balances ──────────────────────────────────────────────
    op.create_table("customer_credit_balances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("credit_balance", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("reserved_amount", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("lifetime_purchased", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("lifetime_consumed", sa.Numeric(14, 4), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("credit_balance >= 0", name="ck_ccb_non_negative"),
        sa.UniqueConstraint("customer_id", "tenant_id", name="uq_ccb_customer_tenant"),
    )

    # ── customer_transactions ─────────────────────────────────────────────────
    op.create_table("customer_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("txn_type", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("balance_before", sa.Numeric(14, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(14, 4), nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ctxn_customer_tenant", "customer_transactions", ["customer_id", "tenant_id"])
    op.create_index("ix_ctxn_reference", "customer_transactions", ["reference_id"])

    # ── credit_reservations ───────────────────────────────────────────────────
    op.create_table("credit_reservations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", sa.String(100), nullable=False, unique=True),
        sa.Column("reserved_amount", sa.Numeric(14, 4), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_type", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("booking_id", name="uq_reservation_booking"),
    )
    op.create_index("ix_creserv_customer_tenant", "credit_reservations", ["customer_id", "tenant_id"])
    op.create_index("ix_creserv_status", "credit_reservations", ["status"])
    op.create_index("ix_creserv_expires_at", "credit_reservations", ["expires_at"])

    # ── warranty_claims ───────────────────────────────────────────────────────
    op.create_table("warranty_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", sa.String(100), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("claim_type", sa.String(50), nullable=False, server_default="service_quality"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("media_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("amount_requested", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount_approved", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("resolver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("deposit_transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("parent_claim_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_warranty_job"),
    )
    op.create_index("ix_wc_tenant_id", "warranty_claims", ["tenant_id"])
    op.create_index("ix_wc_status", "warranty_claims", ["status"])

    # ── tenant_badges ─────────────────────────────────────────────────────────
    op.create_table("tenant_badges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("badge_type", sa.String(50), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("qualification_snapshot", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "badge_type", name="uq_badge_tenant_type"),
    )
    op.create_index("ix_tbadge_tenant_id", "tenant_badges", ["tenant_id"])


def downgrade() -> None:
    for table in ["tenant_badges", "warranty_claims", "credit_reservations",
                  "customer_transactions", "customer_credit_balances", "customer_health_scores",
                  "commission_records", "security_deposit_transactions", "security_deposits",
                  "wallet_transactions", "tenant_wallets", "credit_packages"]:
        op.drop_table(table)
