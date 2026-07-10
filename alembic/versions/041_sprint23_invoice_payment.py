"""Sprint 23 — Invoice / Payment / Commission / Subscription Status.

Creates 5 new tables for the service_jobs financial lifecycle.
Reuses tenant_wallets + wallet_transactions from platform_commerce for wallet/ledger.
Does NOT touch legacy field_ops invoice/commission tables.

Revision ID: 041
Revises: 040
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. service_invoices ───────────────────────────────────────────────────
    op.create_table(
        "service_invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_number",   sa.String(40),  nullable=False),
        sa.Column("booking_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",           UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("category_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("offering_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("status",           sa.String(30), nullable=False, server_default="draft"),
        sa.Column("currency",         sa.String(10), nullable=False, server_default="INR"),
        sa.Column("subtotal_amount",  sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("labour_amount",    sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("parts_amount",     sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("service_amount",   sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("discount_amount",  sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("tax_amount",       sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("total_amount",     sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("customer_payable_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("payment_mode",     sa.String(30), nullable=False, server_default="onsite"),
        sa.Column("payment_status",   sa.String(30), nullable=False, server_default="pending"),
        sa.Column("commission_status",sa.String(30), nullable=False, server_default="pending"),
        sa.Column("invoice_source",   sa.String(30), nullable=False, server_default="manual_final"),
        sa.Column("issued_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes",            sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("invoice_number", name="uq_si_invoice_number"),
    )
    op.create_index("ix_si_job_id",     "service_invoices", ["job_id"])
    op.create_index("ix_si_booking_id", "service_invoices", ["booking_id"])
    op.create_index("ix_si_tenant_id",  "service_invoices", ["tenant_id"])
    op.create_index("ix_si_customer_id","service_invoices", ["customer_id"])
    op.create_index("ix_si_status",     "service_invoices", ["status"])
    op.create_index("ix_si_payment_status", "service_invoices", ["payment_status"])

    # ── 2. service_invoice_items ──────────────────────────────────────────────
    op.create_table(
        "service_invoice_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("item_type",    sa.String(30),  nullable=False),
        sa.Column("item_name",    sa.String(255), nullable=False),
        sa.Column("item_description", sa.Text(), nullable=True),
        sa.Column("quantity",     sa.Numeric(10,3), nullable=False, server_default="1"),
        sa.Column("unit_price",   sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("line_total",   sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("source_quote_item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_customer_visible",  sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sii_invoice_id", "service_invoice_items", ["invoice_id"])
    op.create_index("ix_sii_job_id",     "service_invoice_items", ["job_id"])
    op.create_index("ix_sii_tenant_id",  "service_invoice_items", ["tenant_id"])

    # ── 3. service_payment_records ────────────────────────────────────────────
    op.create_table(
        "service_payment_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("payment_mode", sa.String(30), nullable=False),
        sa.Column("payment_status",  sa.String(30), nullable=False, server_default="pending"),
        sa.Column("collected_amount",sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("currency",     sa.String(10), nullable=False, server_default="INR"),
        sa.Column("collected_by_user_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("collected_by_staff_member_id", UUID(as_uuid=True), nullable=True),
        sa.Column("proof_media_url",              sa.String(1000), nullable=True),
        sa.Column("customer_confirmation_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("customer_confirmed",            sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("customer_confirmed_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_confirmed_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_verified_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason",         sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_spr_invoice_id", "service_payment_records", ["invoice_id"])
    op.create_index("ix_spr_job_id",     "service_payment_records", ["job_id"])
    op.create_index("ix_spr_tenant_id",  "service_payment_records", ["tenant_id"])

    # ── 4. svc_commission_records ─────────────────────────────────────────────
    # Using svc_ prefix to avoid collision with platform_commerce commission_records
    op.create_table(
        "svc_commission_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("invoice_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("status",      sa.String(30), nullable=False, server_default="pending"),
        sa.Column("commission_base_amount",  sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("commission_rate",         sa.Numeric(5,2),  nullable=True),
        sa.Column("commission_fixed_amount", sa.Numeric(14,2), nullable=True),
        sa.Column("commission_amount",       sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("currency",    sa.String(10), nullable=False, server_default="INR"),
        sa.Column("wallet_ledger_entry_id", UUID(as_uuid=True), nullable=True),
        sa.Column("failure_code",    sa.String(60), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("calculated_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("deducted_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("invoice_id", name="uq_svccom_invoice"),
    )
    op.create_index("ix_svccom_tenant_id",  "svc_commission_records", ["tenant_id"])
    op.create_index("ix_svccom_status",     "svc_commission_records", ["status"])
    op.create_index("ix_svccom_idem_key",   "svc_commission_records", ["idempotency_key"])

    # ── 5. financial_events ───────────────────────────────────────────────────
    op.create_table(
        "financial_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("record_type",  sa.String(30), nullable=False),
        sa.Column("record_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type",   sa.String(20), nullable=False),
        sa.Column("actor_user_id",UUID(as_uuid=True), nullable=True),
        sa.Column("event_type",   sa.String(60), nullable=False),
        sa.Column("old_value",    JSONB, nullable=True),
        sa.Column("new_value",    JSONB, nullable=True),
        sa.Column("reason",       sa.Text(), nullable=True),
        sa.Column("request_id",   sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_fev_record_type", "financial_events", ["record_type"])
    op.create_index("ix_fev_record_id",   "financial_events", ["record_id"])
    op.create_index("ix_fev_tenant_id",   "financial_events", ["tenant_id"])
    op.create_index("ix_fev_event_type",  "financial_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("financial_events")
    op.drop_table("svc_commission_records")
    op.drop_table("service_payment_records")
    op.drop_table("service_invoice_items")
    op.drop_table("service_invoices")
