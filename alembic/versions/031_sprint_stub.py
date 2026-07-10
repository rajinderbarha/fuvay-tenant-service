"""Sprint 9-13 bridge — creates all catalog tables missing from migrations 024-030.

These sprints introduced the service catalog, pricing, brands, service types,
tenant service enablement, and master offerings tables that later migrations
build upon.  This migration creates those tables with their original schemas;
subsequent migrations (032, 056, 062, 065, 066, 067, 068) add columns and
indexes incrementally.

Revision ID: 031
Revises: 023
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "031"
down_revision = "023"
branch_labels = None
depends_on = None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=:t"
    ), {"t": table})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. pricing_tiers ──────────────────────────────────────────────────────
    if not _table_exists(conn, "pricing_tiers"):
        op.create_table(
            "pricing_tiers",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("name",                       sa.String(120), nullable=False),
            sa.Column("code",                       sa.String(60),  nullable=False),
            sa.Column("tier_type",                  sa.String(30),  nullable=False),
            sa.Column("description",                sa.Text,        nullable=True),
            sa.Column("base_multiplier",            sa.Numeric(6, 3), nullable=False,
                      server_default="1"),
            sa.Column("platform_fee_percent",       sa.Numeric(6, 2), nullable=False,
                      server_default="0"),
            sa.Column("default_commission_percent", sa.Numeric(6, 2), nullable=False,
                      server_default="0"),
            sa.Column("default_sla_minutes",        sa.Integer, nullable=False,
                      server_default="60"),
            sa.Column("is_active",                  sa.Boolean, nullable=False,
                      server_default="true"),
            sa.Column("deleted_at",                 sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at",                 sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",                 sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("code", name="uq_pt_code"),
        )
        op.create_index("ix_pt_active", "pricing_tiers", ["is_active"])

    # ── 2. tier_locations ─────────────────────────────────────────────────────
    if not _table_exists(conn, "tier_locations"):
        op.create_table(
            "tier_locations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tier_id",    UUID(as_uuid=True), nullable=False),
            sa.Column("country",    sa.String(60),  nullable=False, server_default="India"),
            sa.Column("state",      sa.String(100), nullable=True),
            sa.Column("district",   sa.String(100), nullable=True),
            sa.Column("city",       sa.String(100), nullable=True),
            sa.Column("zipcode",    sa.String(20),  nullable=True),
            sa.Column("zone_name",  sa.String(100), nullable=True),
            sa.Column("priority",   sa.Integer, nullable=False, server_default="100"),
            sa.Column("is_active",  sa.Boolean, nullable=False, server_default="true"),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )
        op.create_index("ix_tl_tier",    "tier_locations", ["tier_id"])
        op.create_index("ix_tl_zipcode", "tier_locations", ["zipcode"])
        op.create_index("ix_tl_city",    "tier_locations", ["city"])
        op.create_index("ix_tl_active",  "tier_locations", ["is_active"])

    # ── 3. service_categories ─────────────────────────────────────────────────
    # Note: is_customer_visible, primary_engine_key, frontend_component_key,
    #       banner_url are added by migration 032.
    #       vertical_type, finance_model, etc. are added by migration 068.
    if not _table_exists(conn, "service_categories"):
        op.create_table(
            "service_categories",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("name",                    sa.String(200), nullable=False),
            sa.Column("slug",                    sa.String(200), nullable=False),
            sa.Column("description",             sa.Text,        nullable=True),
            sa.Column("icon_url",                sa.String(500), nullable=True),
            sa.Column("image_url",               sa.String(500), nullable=True),
            sa.Column("display_order",           sa.Integer, nullable=False, server_default="0"),
            sa.Column("is_active",               sa.Boolean, nullable=False, server_default="true"),
            sa.Column("category_type",           sa.String(50),  nullable=True),
            sa.Column("primary_engine_id",       UUID(as_uuid=True), nullable=True),
            sa.Column("customer_flow_type",      sa.String(50),  nullable=True),
            sa.Column("provider_dashboard_type", sa.String(100), nullable=True),
            sa.Column("is_provider_registerable",sa.Boolean, nullable=False, server_default="true"),
            sa.Column("monetization_model",      sa.String(50),  nullable=True),
            sa.Column("created_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_sc_slug"),
        )
        op.create_index("ix_sc_active", "service_categories", ["is_active"])

    # ── 4. service_types ──────────────────────────────────────────────────────
    if not _table_exists(conn, "service_types"):
        op.create_table(
            "service_types",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("category_id",  UUID(as_uuid=True), nullable=True),
            sa.Column("name",         sa.String(200), nullable=False),
            sa.Column("slug",         sa.String(200), nullable=False),
            sa.Column("description",  sa.Text,        nullable=True),
            sa.Column("icon_url",     sa.String(500), nullable=True),
            sa.Column("is_active",    sa.Boolean, nullable=False, server_default="true"),
            sa.Column("deleted_at",   sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_st_slug"),
        )
        op.create_index("ix_st_category", "service_types", ["category_id"])
        op.create_index("ix_st_active",   "service_types", ["is_active"])

    # ── 5. brands ─────────────────────────────────────────────────────────────
    # Note: code, display_name, status, normalized_name, etc. added by 056.
    #       description, deleted_at added by 062.
    if not _table_exists(conn, "brands"):
        op.create_table(
            "brands",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("category_id",  UUID(as_uuid=True), nullable=True),
            sa.Column("name",         sa.String(200), nullable=False),
            sa.Column("slug",         sa.String(200), nullable=False),
            sa.Column("logo_url",     sa.String(500), nullable=True),
            sa.Column("is_active",    sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_b_slug"),
        )
        op.create_index("ix_b_category", "brands", ["category_id"])
        op.create_index("ix_b_active",   "brands", ["is_active"])

    # ── 6. master_services ────────────────────────────────────────────────────
    # Note: icon_url, tenant_override_allowed, etc. added by 065 (conditional).
    #       hourly fields added by 066 (conditional).
    #       service_group_id added by 068 (unconditional — needs migration fix).
    if not _table_exists(conn, "master_services"):
        op.create_table(
            "master_services",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("category_id",               UUID(as_uuid=True), nullable=False),
            sa.Column("service_name",              sa.String(200), nullable=False),
            sa.Column("slug",                      sa.String(200), nullable=False),
            sa.Column("description",               sa.Text,        nullable=True),
            sa.Column("image_url",                 sa.String(500), nullable=True),
            sa.Column("job_type",                  sa.String(20),  nullable=False),
            sa.Column("pricing_model",             sa.String(30),  nullable=False),
            sa.Column("base_price",                sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("min_price",                 sa.Numeric(12, 2), nullable=True),
            sa.Column("max_price",                 sa.Numeric(12, 2), nullable=True),
            sa.Column("visit_fee",                 sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("pre_approval_limit",        sa.Numeric(12, 2), nullable=True),
            sa.Column("estimated_duration_minutes",sa.Integer, nullable=True),
            sa.Column("requires_checklist",        sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_brand_required",         sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_type_required",          sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_active",                 sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at",                sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",                sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_ms_slug"),
        )
        op.create_index("ix_ms_category", "master_services", ["category_id"])
        op.create_index("ix_ms_job_type", "master_services", ["job_type"])
        op.create_index("ix_ms_active",   "master_services", ["is_active"])

    # ── 7. master_service_types ───────────────────────────────────────────────
    if not _table_exists(conn, "master_service_types"):
        op.create_table(
            "master_service_types",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=False),
            sa.Column("service_type_id",   UUID(as_uuid=True), nullable=False),
            sa.Column("is_required",       sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_default",        sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_active",         sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("master_service_id", "service_type_id", name="uq_mst_service_type"),
        )
        op.create_index("ix_mst_service", "master_service_types", ["master_service_id"])

    # ── 8. master_service_brands ──────────────────────────────────────────────
    # Note: status, display_order, created_by_user_id added by 056 (unconditional).
    #       is_default added by 062 (unconditional).
    if not _table_exists(conn, "master_service_brands"):
        op.create_table(
            "master_service_brands",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=False),
            sa.Column("brand_id",          UUID(as_uuid=True), nullable=False),
            sa.Column("is_required",       sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_active",         sa.Boolean, nullable=False, server_default="true"),
            sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("master_service_id", "brand_id", name="uq_msb_service_brand"),
        )
        op.create_index("ix_msb_service", "master_service_brands", ["master_service_id"])

    # ── 9. service_pricing_rules ──────────────────────────────────────────────
    # Note: deleted_at added by 065 (conditional — safe to include).
    #       service_option_id added by 068 (unconditional — needs migration fix).
    if not _table_exists(conn, "service_pricing_rules"):
        op.create_table(
            "service_pricing_rules",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("master_service_id",    UUID(as_uuid=True), nullable=False),
            sa.Column("category_id",          UUID(as_uuid=True), nullable=True),
            sa.Column("job_type",             sa.String(20), nullable=False),
            sa.Column("tier_id",              UUID(as_uuid=True), nullable=True),
            sa.Column("service_type_id",      UUID(as_uuid=True), nullable=True),
            sa.Column("brand_id",             UUID(as_uuid=True), nullable=True),
            sa.Column("city",                 sa.String(100), nullable=True),
            sa.Column("zipcode",              sa.String(20),  nullable=True),
            sa.Column("pricing_model",        sa.String(30),  nullable=False),
            sa.Column("base_price",           sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("min_price",            sa.Numeric(12, 2), nullable=True),
            sa.Column("max_price",            sa.Numeric(12, 2), nullable=True),
            sa.Column("visit_fee",            sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("platform_fee_percent", sa.Numeric(6, 2),  nullable=False, server_default="0"),
            sa.Column("commission_percent",   sa.Numeric(6, 2),  nullable=False, server_default="0"),
            sa.Column("tax_percent",          sa.Numeric(6, 2),  nullable=False, server_default="0"),
            sa.Column("effective_from",       sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_to",         sa.DateTime(timezone=True), nullable=True),
            sa.Column("priority",             sa.Integer, nullable=False, server_default="100"),
            sa.Column("is_active",            sa.Boolean, nullable=False, server_default="true"),
            sa.Column("deleted_at",           sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at",           sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",           sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )
        op.create_index("ix_spr_service", "service_pricing_rules", ["master_service_id"])
        op.create_index("ix_spr_tier",    "service_pricing_rules", ["tier_id"])
        op.create_index("ix_spr_zipcode", "service_pricing_rules", ["zipcode"])
        op.create_index("ix_spr_city",    "service_pricing_rules", ["city"])
        op.create_index("ix_spr_active",  "service_pricing_rules", ["is_active"])

    # ── 10. tenant_services ───────────────────────────────────────────────────
    if not _table_exists(conn, "tenant_services"):
        op.create_table(
            "tenant_services",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id",           UUID(as_uuid=True), nullable=False),
            sa.Column("master_service_id",   UUID(as_uuid=True), nullable=False),
            sa.Column("category_id",         UUID(as_uuid=True), nullable=False),
            sa.Column("job_type",            sa.String(20),  nullable=False),
            sa.Column("is_enabled",          sa.Boolean, nullable=False, server_default="true"),
            sa.Column("tenant_display_name", sa.String(200), nullable=True),
            sa.Column("tenant_description",  sa.Text,        nullable=True),
            sa.Column("tenant_base_price",   sa.Numeric(12, 2), nullable=True),
            sa.Column("tenant_min_price",    sa.Numeric(12, 2), nullable=True),
            sa.Column("tenant_max_price",    sa.Numeric(12, 2), nullable=True),
            sa.Column("tenant_visit_fee",    sa.Numeric(12, 2), nullable=True),
            sa.Column("override_allowed",    sa.Boolean, nullable=False, server_default="false"),
            sa.Column("requires_brand",      sa.Boolean, nullable=False, server_default="false"),
            sa.Column("requires_type",       sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_active",           sa.Boolean, nullable=False, server_default="true"),
            sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_id", "master_service_id", name="uq_ts_tenant_service"),
        )
        op.create_index("ix_ts_tenant",  "tenant_services", ["tenant_id"])
        op.create_index("ix_ts_service", "tenant_services", ["master_service_id"])
        op.create_index("ix_ts_active",  "tenant_services", ["tenant_id", "is_enabled"])

    # ── 11. tenant_service_types ──────────────────────────────────────────────
    if not _table_exists(conn, "tenant_service_types"):
        op.create_table(
            "tenant_service_types",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id",               UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_service_id",        UUID(as_uuid=True), nullable=False),
            sa.Column("service_type_id",          UUID(as_uuid=True), nullable=False),
            sa.Column("is_enabled",              sa.Boolean, nullable=False, server_default="true"),
            sa.Column("tenant_price_adjustment",  sa.Numeric(12, 2), nullable=True),
            sa.Column("created_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_service_id", "service_type_id", name="uq_tst_service_type"),
        )
        op.create_index("ix_tst_tenant_service", "tenant_service_types", ["tenant_service_id"])

    # ── 12. tenant_service_brands ─────────────────────────────────────────────
    if not _table_exists(conn, "tenant_service_brands"):
        op.create_table(
            "tenant_service_brands",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id",               UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_service_id",        UUID(as_uuid=True), nullable=False),
            sa.Column("brand_id",                UUID(as_uuid=True), nullable=False),
            sa.Column("is_enabled",              sa.Boolean, nullable=False, server_default="true"),
            sa.Column("tenant_price_adjustment",  sa.Numeric(12, 2), nullable=True),
            sa.Column("created_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",              sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("tenant_service_id", "brand_id", name="uq_tsb_service_brand"),
        )
        op.create_index("ix_tsb_tenant_service", "tenant_service_brands", ["tenant_service_id"])

    # ── 13. master_offerings ──────────────────────────────────────────────────
    # Note: customer_flow_type, primary_engine_key, requires_address, requires_slot,
    #       requires_photo_upload, requires_customer_notes added by 032 (unconditional).
    if not _table_exists(conn, "master_offerings"):
        op.create_table(
            "master_offerings",
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("category_id",               UUID(as_uuid=True), nullable=False),
            sa.Column("name",                      sa.String(200), nullable=False),
            sa.Column("slug",                      sa.String(200), nullable=False),
            sa.Column("description",               sa.Text,        nullable=True),
            sa.Column("offering_class",            sa.String(50),  nullable=False),
            sa.Column("image_url",                 sa.String(500), nullable=True),
            sa.Column("icon_url",                  sa.String(500), nullable=True),
            sa.Column("default_pricing_model",     sa.String(30),  nullable=False),
            sa.Column("default_base_price",        sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("default_visit_fee",         sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("default_appointment_fee",   sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("default_lead_fee",          sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("default_min_price",         sa.Numeric(12, 2), nullable=True),
            sa.Column("default_max_price",         sa.Numeric(12, 2), nullable=True),
            sa.Column("currency",                  sa.String(10), nullable=False, server_default="INR"),
            sa.Column("is_brand_required",         sa.Boolean, nullable=False, server_default="false"),
            sa.Column("is_type_required",          sa.Boolean, nullable=False, server_default="false"),
            sa.Column("requires_checklist",        sa.Boolean, nullable=False, server_default="false"),
            sa.Column("allow_provider_override",   sa.Boolean, nullable=False, server_default="false"),
            sa.Column("estimated_duration_minutes",sa.Integer, nullable=True),
            sa.Column("tags",                      JSONB, nullable=True),
            sa.Column("metadata",                  JSONB, nullable=True),
            sa.Column("display_order",             sa.Integer, nullable=False, server_default="0"),
            sa.Column("status",                    sa.String(20), nullable=False, server_default="active"),
            sa.Column("is_active",                 sa.Boolean, nullable=False, server_default="true"),
            sa.Column("deleted_at",                sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at",                sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at",                sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_mo_slug"),
        )
        op.create_index("ix_mo_category", "master_offerings", ["category_id"])
        op.create_index("ix_mo_active",   "master_offerings", ["is_active"])


def downgrade() -> None:
    for t in [
        "master_offerings", "tenant_service_brands", "tenant_service_types",
        "tenant_services", "service_pricing_rules", "master_service_brands",
        "master_service_types", "master_services", "brands", "service_types",
        "service_categories", "tier_locations", "pricing_tiers",
    ]:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {t} CASCADE"))
