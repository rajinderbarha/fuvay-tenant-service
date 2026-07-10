"""Phase 4 — Pricing Engine (6 tables)

Revision ID: 004
Revises: 003
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # city_tier_configs
    op.create_table("city_tier_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("city_name", sa.String(100), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("service_category", sa.String(100), nullable=False),
        sa.Column("floor_price", sa.Numeric(10,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("city_name","service_category", name="uq_ctc_city_category"),
    )
    op.create_index("ix_ctc_tier","city_tier_configs",["tier"])

    # service_type_prices (versioned)
    op.create_table("service_type_prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("service_category", sa.String(100), nullable=False),
        sa.Column("city_name", sa.String(100), nullable=False),
        sa.Column("base_price", sa.Numeric(10,2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False, server_default="per_visit"),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column("previous_price", sa.Numeric(10,2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_stp_tenant_type","service_type_prices",["tenant_id","service_type_id"])
    op.create_index("ix_stp_active","service_type_prices",["tenant_id","service_type_id","valid_until"])

    # brand_adjustments (versioned)
    op.create_table("brand_adjustments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("adjustment_pct", sa.Numeric(6,2), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ba_tenant","brand_adjustments",["tenant_id"])

    # zone_surcharges
    op.create_table("zone_surcharges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_name", sa.String(100), nullable=False),
        sa.Column("zone_type", sa.String(30), nullable=False, server_default="pincode"),
        sa.Column("zone_identifiers", JSONB, nullable=False, server_default="[]"),
        sa.Column("surcharge_pct", sa.Numeric(6,2), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_zs_tenant","zone_surcharges",["tenant_id"])
    op.create_index("ix_zs_active","zone_surcharges",["tenant_id","is_active"])

    # dynamic_pricing_rules
    op.create_table("dynamic_pricing_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("rule_name", sa.String(100), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
        sa.Column("adjustment_pct", sa.Numeric(6,2), nullable=False),
        sa.Column("conditions", JSONB, nullable=False, server_default="{}"),
        sa.Column("applies_to", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by", UUID(as_uuid=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_dpr_tenant_active","dynamic_pricing_rules",["tenant_id","is_active"])
    op.create_index("ix_dpr_active_from","dynamic_pricing_rules",["active_from"])
    op.create_index("ix_dpr_active_until","dynamic_pricing_rules",["active_until"])

    # price_snapshots (immutable)
    op.create_table("price_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", sa.String(100), nullable=True),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("service_category", sa.String(100), nullable=False),
        sa.Column("city_name", sa.String(100), nullable=False),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("pipeline_inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("step_city_floor", JSONB, nullable=False, server_default="{}"),
        sa.Column("step_tenant_price", JSONB, nullable=False, server_default="{}"),
        sa.Column("step_brand_adj", JSONB, nullable=False, server_default="{}"),
        sa.Column("step_zone_surge", JSONB, nullable=False, server_default="{}"),
        sa.Column("step_dynamic_rule", JSONB, nullable=False, server_default="{}"),
        sa.Column("final_price", sa.Numeric(10,2), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False, server_default="INR"),
        sa.Column("idempotency_key", sa.String(255), nullable=True, unique=True),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_ps_idem_key"),
    )
    op.create_index("ix_ps_tenant","price_snapshots",["tenant_id"])
    op.create_index("ix_ps_booking","price_snapshots",["booking_id"])
    op.create_index("ix_ps_created","price_snapshots",["created_at"])


def downgrade() -> None:
    for t in ["price_snapshots","dynamic_pricing_rules","zone_surcharges",
              "brand_adjustments","service_type_prices","city_tier_configs"]:
        op.drop_table(t)
