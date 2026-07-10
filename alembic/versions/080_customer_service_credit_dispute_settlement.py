"""Customer Service Credit + Dispute Settlement Engine

Revision ID: 080
Revises: 079
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Finance Vertical Configs ──────────────────────────────────────
    op.create_table(
        "finance_vertical_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vertical_type", sa.String(50), nullable=False, unique=True),
        sa.Column("payment_collection_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tenant_payouts_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("customer_service_credits_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tenant_wallet_deduction_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("security_deposit_adjustment_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("manual_customer_refund_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("config_notes", sa.Text),
        sa.Column("updated_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finance_vertical_configs_vertical", "finance_vertical_configs", ["vertical_type"])

    # Seed Home Services config
    op.execute("""
        INSERT INTO finance_vertical_configs (vertical_type, payment_collection_enabled, tenant_payouts_enabled,
            customer_service_credits_enabled, tenant_wallet_deduction_enabled,
            security_deposit_adjustment_enabled, manual_customer_refund_enabled, config_notes)
        VALUES ('home_services', false, false, true, true, true, false,
            'Home Services: customer pays provider directly on-site. Platform issues service credit after disputes.')
        ON CONFLICT (vertical_type) DO NOTHING
    """)

    # ── 2. Customer Service Credits ────────────────────────────────────
    op.create_table(
        "customer_service_credits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("credit_number", sa.String(40), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True)),
        sa.Column("booking_id", UUID(as_uuid=True)),
        sa.Column("job_id", UUID(as_uuid=True)),
        sa.Column("dispute_id", UUID(as_uuid=True)),
        sa.Column("settlement_id", UUID(as_uuid=True)),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("credit_type", sa.String(40), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("issued_by_admin_id", UUID(as_uuid=True)),
        sa.Column("issued_reason", sa.Text, nullable=False),
        sa.Column("customer_message", sa.Text),
        sa.Column("internal_note", sa.Text),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by_admin_id", UUID(as_uuid=True)),
        sa.Column("cancel_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_csc_customer", "customer_service_credits", ["customer_id"])
    op.create_index("ix_csc_tenant", "customer_service_credits", ["tenant_id"])
    op.create_index("ix_csc_dispute", "customer_service_credits", ["dispute_id"])
    op.create_index("ix_csc_status", "customer_service_credits", ["status"])
    op.create_index("ix_csc_settlement", "customer_service_credits", ["settlement_id"])

    # ── 3. Customer Credit Ledger ──────────────────────────────────────
    op.create_table(
        "customer_credit_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_credit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True)),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ccl_credit", "customer_credit_ledger", ["customer_credit_id"])
    op.create_index("ix_ccl_customer", "customer_credit_ledger", ["customer_id"])

    # ── 4. Dispute Settlements ─────────────────────────────────────────
    op.create_table(
        "dispute_settlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("settlement_number", sa.String(40), nullable=False, unique=True),
        sa.Column("dispute_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True)),
        sa.Column("job_id", UUID(as_uuid=True)),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("settlement_type", sa.String(50), nullable=False),
        sa.Column("settlement_status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("settlement_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("deduction_source", sa.String(50), nullable=False, server_default="tenant_wallet"),
        sa.Column("tenant_wallet_deduction_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("security_deposit_deduction_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("platform_goodwill_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("customer_credit_id", UUID(as_uuid=True)),
        sa.Column("tenant_penalty_id", UUID(as_uuid=True)),
        sa.Column("admin_decision_reason", sa.Text, nullable=False),
        sa.Column("customer_message", sa.Text),
        sa.Column("tenant_message", sa.Text),
        sa.Column("internal_note", sa.Text),
        sa.Column("created_by_admin_id", UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by_admin_id", UUID(as_uuid=True)),
        sa.Column("executed_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ds_dispute", "dispute_settlements", ["dispute_id"])
    op.create_index("ix_ds_customer", "dispute_settlements", ["customer_id"])
    op.create_index("ix_ds_tenant", "dispute_settlements", ["tenant_id"])
    op.create_index("ix_ds_status", "dispute_settlements", ["settlement_status"])

    # ── 5. Tenant Penalties ────────────────────────────────────────────
    op.create_table(
        "tenant_penalties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("penalty_number", sa.String(40), nullable=False, unique=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True)),
        sa.Column("job_id", UUID(as_uuid=True)),
        sa.Column("dispute_id", UUID(as_uuid=True)),
        sa.Column("settlement_id", UUID(as_uuid=True)),
        sa.Column("penalty_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_by_admin_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_tp_tenant", "tenant_penalties", ["tenant_id"])
    op.create_index("ix_tp_status", "tenant_penalties", ["status"])
    op.create_index("ix_tp_settlement", "tenant_penalties", ["settlement_id"])

    # ── 6. Security Deposit Adjustments ───────────────────────────────
    op.create_table(
        "security_deposit_adjustments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("settlement_id", UUID(as_uuid=True)),
        sa.Column("dispute_id", UUID(as_uuid=True)),
        sa.Column("adjustment_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_approval"),
        sa.Column("approved_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sda_tenant", "security_deposit_adjustments", ["tenant_id"])
    op.create_index("ix_sda_settlement", "security_deposit_adjustments", ["settlement_id"])

    # ── 7. Finance Audit Logs ──────────────────────────────────────────
    op.create_table(
        "finance_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(40)),
        sa.Column("tenant_id", UUID(as_uuid=True)),
        sa.Column("customer_id", UUID(as_uuid=True)),
        sa.Column("booking_id", UUID(as_uuid=True)),
        sa.Column("dispute_id", UUID(as_uuid=True)),
        sa.Column("settlement_id", UUID(as_uuid=True)),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("reason", sa.Text),
        sa.Column("request_id", sa.String(100)),
        sa.Column("ip_hash", sa.String(100)),
        sa.Column("metadata_json", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fal_event", "finance_audit_logs", ["event_type"])
    op.create_index("ix_fal_tenant", "finance_audit_logs", ["tenant_id"])
    op.create_index("ix_fal_customer", "finance_audit_logs", ["customer_id"])
    op.create_index("ix_fal_settlement", "finance_audit_logs", ["settlement_id"])
    op.create_index("ix_fal_created", "finance_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("finance_audit_logs")
    op.drop_table("security_deposit_adjustments")
    op.drop_table("tenant_penalties")
    op.drop_table("dispute_settlements")
    op.drop_table("customer_credit_ledger")
    op.drop_table("customer_service_credits")
    op.drop_table("finance_vertical_configs")
