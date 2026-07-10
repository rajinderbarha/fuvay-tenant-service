"""Sprint 22 — Quote Approval + Checklist Engine for service_jobs.

Creates 7 new tables scoped to the Sprint 19-21 service_jobs ecosystem.
Does NOT touch the legacy field_ops job_quotes / service_checklist_* tables.

Revision ID: 040
Revises: 039
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. service_job_quotes ─────────────────────────────────────────────────
    op.create_table(
        "service_job_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("quote_number",       sa.String(40),  nullable=False),
        sa.Column("booking_id",         UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",          UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_staff_member_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id",         UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("quote_type", sa.String(40), nullable=False, server_default="repair_quote"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("labour_amount",         sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("parts_amount",          sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("service_amount",        sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount",       sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount",            sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_amount",          sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("customer_payable_amount",sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("provider_internal_notes", sa.Text(), nullable=True),
        sa.Column("customer_visible_notes",  sa.Text(), nullable=True),
        sa.Column("rejection_reason",        sa.Text(), nullable=True),
        sa.Column("revision_reason",         sa.Text(), nullable=True),
        sa.Column("idempotency_key",         sa.String(255), nullable=True),
        sa.Column("expires_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_to_customer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("quote_number", name="uq_sjq_quote_number"),
    )
    op.create_index("ix_sjq_job_id",    "service_job_quotes", ["job_id"])
    op.create_index("ix_sjq_booking_id","service_job_quotes", ["booking_id"])
    op.create_index("ix_sjq_tenant_id", "service_job_quotes", ["tenant_id"])
    op.create_index("ix_sjq_customer_id","service_job_quotes",["customer_id"])
    op.create_index("ix_sjq_status",    "service_job_quotes", ["status"])

    # ── 2. service_job_quote_items ────────────────────────────────────────────
    op.create_table(
        "service_job_quote_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("item_type",  sa.String(30), nullable=False),
        sa.Column("item_name",  sa.String(255), nullable=False),
        sa.Column("item_description", sa.Text(), nullable=True),
        sa.Column("quantity",   sa.Numeric(10, 3), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("is_required",         sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_customer_visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("item_metadata",       JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjqi_quote_id",  "service_job_quote_items", ["quote_id"])
    op.create_index("ix_sjqi_job_id",    "service_job_quote_items", ["job_id"])
    op.create_index("ix_sjqi_tenant_id", "service_job_quote_items", ["tenant_id"])

    # ── 3. service_job_quote_events ───────────────────────────────────────────
    op.create_table(
        "service_job_quote_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("quote_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",     UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("old_status", sa.String(40), nullable=True),
        sa.Column("new_status", sa.String(40), nullable=True),
        sa.Column("old_value",  JSONB, nullable=True),
        sa.Column("new_value",  JSONB, nullable=True),
        sa.Column("reason",     sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjqe_quote_id",  "service_job_quote_events", ["quote_id"])
    op.create_index("ix_sjqe_job_id",    "service_job_quote_events", ["job_id"])
    op.create_index("ix_sjqe_tenant_id", "service_job_quote_events", ["tenant_id"])

    # ── 4. sj_checklist_templates ─────────────────────────────────────────────
    # Using sj_ prefix to avoid collision with legacy service_checklist_templates
    op.create_table(
        "sj_checklist_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("offering_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("template_name",  sa.String(255), nullable=False),
        sa.Column("template_type",  sa.String(30),  nullable=False),
        sa.Column("applies_to",     sa.String(20),  nullable=False, server_default="offering"),
        sa.Column("is_required",    sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("is_active",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjct_category_id", "sj_checklist_templates", ["category_id"])
    op.create_index("ix_sjct_tenant_id",   "sj_checklist_templates", ["tenant_id"])
    op.create_index("ix_sjct_active",      "sj_checklist_templates", ["is_active"])

    # ── 5. sj_checklist_template_items ───────────────────────────────────────
    op.create_table(
        "sj_checklist_template_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("item_label",        sa.String(255), nullable=False),
        sa.Column("item_description",  sa.Text(), nullable=True),
        sa.Column("input_type",        sa.String(20), nullable=False, server_default="checkbox"),
        sa.Column("is_required",       sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order",        sa.Integer(), nullable=False, server_default="0"),
        sa.Column("options",           JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjcti_template_id", "sj_checklist_template_items", ["template_id"])

    # ── 6. service_job_checklists ─────────────────────────────────────────────
    op.create_table(
        "service_job_checklists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status",          sa.String(20), nullable=False, server_default="pending"),
        sa.Column("checklist_type",  sa.String(30), nullable=False),
        sa.Column("created_by_user_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("completed_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjcl_job_id",    "service_job_checklists", ["job_id"])
    op.create_index("ix_sjcl_tenant_id", "service_job_checklists", ["tenant_id"])

    # ── 7. service_job_checklist_items ────────────────────────────────────────
    op.create_table(
        "service_job_checklist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id",   UUID(as_uuid=True), nullable=False),
        sa.Column("job_id",       UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=False),
        sa.Column("item_label",   sa.String(255), nullable=False),
        sa.Column("input_type",   sa.String(20),  nullable=False, server_default="checkbox"),
        sa.Column("is_required",  sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("status",       sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("value_text",   sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(14, 4), nullable=True),
        sa.Column("value_json",   JSONB, nullable=True),
        sa.Column("media_url",    sa.String(1000), nullable=True),
        sa.Column("completed_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order",   sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_sjcli_checklist_id", "service_job_checklist_items", ["checklist_id"])
    op.create_index("ix_sjcli_job_id",       "service_job_checklist_items", ["job_id"])


def downgrade() -> None:
    op.drop_table("service_job_checklist_items")
    op.drop_table("service_job_checklists")
    op.drop_table("sj_checklist_template_items")
    op.drop_table("sj_checklist_templates")
    op.drop_table("service_job_quote_events")
    op.drop_table("service_job_quote_items")
    op.drop_table("service_job_quotes")
