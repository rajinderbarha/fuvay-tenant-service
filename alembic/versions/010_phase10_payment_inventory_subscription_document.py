"""Phase 10 — Payment + Inventory + Subscription + Document (15 tables)
Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Payment (4 tables) ────────────────────────────────────────────────────
    op.create_table("payment_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", sa.String(100), nullable=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payment_type", sa.String(30), nullable=False),
        sa.Column("gateway", sa.String(20), nullable=False),
        sa.Column("gateway_payment_id", sa.String(100), nullable=False, unique=True),
        sa.Column("gateway_order_id", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(12,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("platform_fee", sa.Numeric(10,2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(10,2), nullable=False, server_default="0"),
        sa.Column("net_to_tenant", sa.Numeric(12,2), nullable=False, server_default="0"),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("invoice_id", UUID(as_uuid=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("gateway_payment_id", name="uq_pr_gateway_id"),
    )
    op.create_index("ix_pr_tenant","payment_records",["tenant_id"])
    op.create_index("ix_pr_booking","payment_records",["booking_id"])

    op.create_table("refund_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("gateway", sa.String(20), nullable=False),
        sa.Column("gateway_refund_id", sa.String(100), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12,2), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("initiated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("gateway_refund_id", name="uq_rr_gateway_id"),
    )
    op.create_index("ix_rr_payment","refund_records",["payment_id"])

    op.create_table("invoice_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("booking_id", sa.String(100), nullable=True),
        sa.Column("invoice_number", sa.String(50), nullable=False, unique=True),
        sa.Column("invoice_type", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12,2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10,2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="issued"),
        sa.Column("media_file_id", UUID(as_uuid=True), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("line_items", JSONB, nullable=False, server_default="[]"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("invoice_number", name="uq_ir_number"),
    )
    op.create_index("ix_ir_tenant","invoice_records",["tenant_id"])
    op.create_index("ix_ir_payment","invoice_records",["payment_id"])

    op.create_table("payout_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("gateway", sa.String(20), nullable=False),
        sa.Column("gateway_transfer_id", sa.String(100), nullable=True),
        sa.Column("bank_account", JSONB, nullable=False, server_default="{}"),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_por_tenant","payout_records",["tenant_id"])

    # ── Inventory (5 tables) ──────────────────────────────────────────────────
    op.create_table("inventory_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="unit"),
        sa.Column("unit_cost", sa.Numeric(10,2), nullable=False),
        sa.Column("min_quantity", sa.Integer, nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","sku", name="uq_ii_tenant_sku"),
    )
    op.create_index("ix_ii_tenant","inventory_items",["tenant_id"])

    op.create_table("stock_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_name", sa.String(100), nullable=False),
        sa.Column("location_type", sa.String(20), nullable=False),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","location_name","location_type", name="uq_sl2_tenant_loc"),
    )
    op.create_index("ix_sl2_tenant","stock_locations",["tenant_id"])

    op.create_table("stock_balances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reserved_qty", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_txn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("item_id","location_id", name="uq_sb_item_loc"),
    )
    op.create_index("ix_sb_location","stock_balances",["location_id"])

    op.create_table("stock_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("txn_type", sa.String(30), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("balance_before", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(10,2), nullable=True),
        sa.Column("job_id", sa.String(100), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_stxn_idem"),
    )
    op.create_index("ix_stxn_item_loc","stock_transactions",["item_id","location_id"])
    op.create_index("ix_stxn_job","stock_transactions",["job_id"])

    op.create_table("stock_reservations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.String(100), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("job_id","item_id","location_id", name="uq_sr_job_item_loc"),
    )
    op.create_index("ix_sr_job","stock_reservations",["job_id"])
    op.create_index("ix_sr_status","stock_reservations",["status"])
    op.create_index("ix_sr_expires","stock_reservations",["expires_at"])

    # ── Subscription (3 tables) ───────────────────────────────────────────────
    op.create_table("subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("plan_type", sa.String(30), nullable=False),
        sa.Column("billing_cycle", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(10,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dunning_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_method", JSONB, nullable=False, server_default="{}"),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_sub_tenant"),
    )

    op.create_table("subscription_periods",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("plan_type", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(10,2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("jobs_included", sa.Integer, nullable=False, server_default="0"),
        sa.Column("jobs_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("overage_amount", sa.Numeric(10,2), nullable=False, server_default="0"),
        sa.Column("payment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("invoice_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sp_subscription","subscription_periods",["subscription_id"])

    op.create_table("subscription_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_plan", sa.String(30), nullable=True),
        sa.Column("to_plan", sa.String(30), nullable=True),
        sa.Column("proration_amount", sa.Numeric(10,2), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_se_subscription","subscription_events",["subscription_id"])

    # ── Document (3 tables) ───────────────────────────────────────────────────
    op.create_table("document_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("template_html", sa.Text, nullable=False),
        sa.Column("required_vars", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","doc_type", name="uq_dt_tenant_type"),
    )
    op.create_index("ix_dt_tenant","document_templates",["tenant_id"])

    op.create_table("documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("document_number", sa.String(50), nullable=False, unique=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("is_frozen", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("content_html", sa.Text, nullable=True),
        sa.Column("variables_used", JSONB, nullable=False, server_default="{}"),
        sa.Column("storage_key", sa.String(500), nullable=True),
        sa.Column("media_file_id", UUID(as_uuid=True), nullable=True),
        sa.Column("signing_token", sa.String(128), nullable=True),
        sa.Column("signing_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("signer_ip", sa.String(50), nullable=True),
        sa.Column("signature_data", sa.Text, nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_number", name="uq_doc_number"),
    )
    op.create_index("ix_doc_tenant_type","documents",["tenant_id","doc_type"])
    op.create_index("ix_doc_entity","documents",["entity_type","entity_id"])

    op.create_table("document_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(30), nullable=True),
        sa.Column("actor_ip", sa.String(50), nullable=True),
        sa.Column("meta", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_de_document","document_events",["document_id"])


def downgrade() -> None:
    for t in ["document_events","documents","document_templates",
              "subscription_events","subscription_periods","subscriptions",
              "stock_reservations","stock_transactions","stock_balances",
              "stock_locations","inventory_items",
              "payout_records","invoice_records","refund_records","payment_records"]:
        op.drop_table(t)
