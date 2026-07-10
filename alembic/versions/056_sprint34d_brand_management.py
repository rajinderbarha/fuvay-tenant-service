"""Sprint 34D — Enterprise Brand Management

Revision: 056
Down revision: 055

Changes:
  - brands: add code, status, display_name, normalized_name, alias_names_json,
            replacement_brand_id, website_url, country_of_origin, is_global,
            display_order, metadata_json, created_by_user_id, updated_by_user_id
  - master_service_brands: add status, display_order, created_by_user_id

New tables:
  - brand_category_mappings      (M2M brand ↔ category)
  - brand_service_option_mappings (optional brand ↔ service option compatibility)
  - tenant_supported_brands      (provider-scoped brand support with approval)
  - brand_requests               (provider/admin brand-add requests)
  - brand_templates              (reusable brand starter packs)
  - brand_template_items         (items inside a brand template)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()
    # ── 1. Enhance brands table ───────────────────────────────────────────────
    if not _col_exists(conn, "brands", "code"):
        op.add_column("brands", sa.Column("code", sa.String(80), nullable=True))
    if not _col_exists(conn, "brands", "display_name"):
        op.add_column("brands", sa.Column("display_name", sa.String(200), nullable=True))
    if not _col_exists(conn, "brands", "status"):
        op.add_column("brands", sa.Column("status", sa.String(30), nullable=False, server_default="active"))
    if not _col_exists(conn, "brands", "normalized_name"):
        op.add_column("brands", sa.Column("normalized_name", sa.String(200), nullable=True))
    if not _col_exists(conn, "brands", "alias_names_json"):
        op.add_column("brands", sa.Column("alias_names_json", postgresql.JSONB, nullable=True))
    if not _col_exists(conn, "brands", "replacement_brand_id"):
        op.add_column("brands", sa.Column("replacement_brand_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "brands", "website_url"):
        op.add_column("brands", sa.Column("website_url", sa.String(500), nullable=True))
    if not _col_exists(conn, "brands", "country_of_origin"):
        op.add_column("brands", sa.Column("country_of_origin", sa.String(100), nullable=True))
    if not _col_exists(conn, "brands", "is_global"):
        op.add_column("brands", sa.Column("is_global", sa.Boolean, nullable=False, server_default=sa.text("true")))
    if not _col_exists(conn, "brands", "display_order"):
        op.add_column("brands", sa.Column("display_order", sa.Integer, nullable=False, server_default="0"))
    if not _col_exists(conn, "brands", "metadata_json"):
        op.add_column("brands", sa.Column("metadata_json", postgresql.JSONB, nullable=True))
    if not _col_exists(conn, "brands", "created_by_user_id"):
        op.add_column("brands", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _col_exists(conn, "brands", "updated_by_user_id"):
        op.add_column("brands", sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    if not _index_exists(conn, "ix_brands_status"):
        op.create_index("ix_brands_status", "brands", ["status"])
    if not _index_exists(conn, "ix_brands_norm_name"):
        op.create_index("ix_brands_norm_name", "brands", ["normalized_name"])
    if not _index_exists(conn, "ix_brands_is_global"):
        op.create_index("ix_brands_is_global", "brands", ["is_global"])
    try:
        op.create_unique_constraint("uq_brands_code", "brands", ["code"])
    except Exception:
        pass  # code may be null initially; constraint enforced at app layer

    # ── 2. Enhance master_service_brands ──────────────────────────────────────
    if not _col_exists(conn, "master_service_brands", "status"):
        op.add_column("master_service_brands", sa.Column("status", sa.String(30), nullable=False, server_default="active"))
    if not _col_exists(conn, "master_service_brands", "display_order"):
        op.add_column("master_service_brands", sa.Column("display_order", sa.Integer, nullable=False, server_default="0"))
    if not _col_exists(conn, "master_service_brands", "created_by_user_id"):
        op.add_column("master_service_brands", sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))

    # ── 3. brand_category_mappings ────────────────────────────────────────────
    op.create_table(
        "brand_category_mappings",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id",         postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status",              sa.String(30), nullable=False, server_default="active"),
        sa.Column("display_order",       sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("brand_id", "category_id", name="uq_bcm_brand_category"),
    )
    op.create_index("ix_bcm_brand",    "brand_category_mappings", ["brand_id"])
    op.create_index("ix_bcm_category", "brand_category_mappings", ["category_id"])
    op.create_index("ix_bcm_status",   "brand_category_mappings", ["status"])

    # ── 4. brand_service_option_mappings ──────────────────────────────────────
    op.create_table(
        "brand_service_option_mappings",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_id",          postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("master_service_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_option_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status",            sa.String(30), nullable=False, server_default="active"),
        sa.Column("display_order",     sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata_json",     postgresql.JSONB, nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("deleted_at",        sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("brand_id", "service_option_id", name="uq_bsom_brand_option"),
    )
    op.create_index("ix_bsom_brand",          "brand_service_option_mappings", ["brand_id"])
    op.create_index("ix_bsom_service_option", "brand_service_option_mappings", ["service_option_id"])
    op.create_index("ix_bsom_status",         "brand_service_option_mappings", ["status"])

    # ── 5. tenant_supported_brands ────────────────────────────────────────────
    op.create_table(
        "tenant_supported_brands",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("master_service_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_option_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(30), nullable=False, server_default="active"),
        sa.Column("support_level",       sa.String(30), nullable=True),
        sa.Column("notes",               sa.Text, nullable=True),
        sa.Column("created_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("deleted_at",          sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "master_service_id", "brand_id", name="uq_tsb_tenant_service_brand"),
    )
    op.create_index("ix_tsb_tenant",         "tenant_supported_brands", ["tenant_id"])
    op.create_index("ix_tsb_service",        "tenant_supported_brands", ["master_service_id"])
    op.create_index("ix_tsb_brand",          "tenant_supported_brands", ["brand_id"])
    op.create_index("ix_tsb_status",         "tenant_supported_brands", ["status"])

    # ── 6. brand_requests ─────────────────────────────────────────────────────
    op.create_table(
        "brand_requests",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requested_by_user_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",             postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_brand_name",  sa.String(200), nullable=False),
        sa.Column("normalized_name",       sa.String(200), nullable=True),
        sa.Column("suggested_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_service_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason",                sa.Text, nullable=True),
        sa.Column("status",                sa.String(30), nullable=False, server_default="pending"),
        sa.Column("matched_brand_id",      postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_note",            sa.Text, nullable=True),
        sa.Column("reviewed_by_user_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at",           sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",            sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_br_tenant",  "brand_requests", ["tenant_id"])
    op.create_index("ix_br_status",  "brand_requests", ["status"])
    op.create_index("ix_br_matched", "brand_requests", ["matched_brand_id"])

    # ── 7. brand_templates ────────────────────────────────────────────────────
    op.create_table(
        "brand_templates",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",           sa.String(80),  nullable=False),
        sa.Column("name",           sa.String(200), nullable=False),
        sa.Column("description",    sa.Text, nullable=True),
        sa.Column("category_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vertical_type",  sa.String(50), nullable=True),
        sa.Column("status",         sa.String(30), nullable=False, server_default="active"),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_bt_code"),
    )
    op.create_index("ix_bt_status",   "brand_templates", ["status"])
    op.create_index("ix_bt_category", "brand_templates", ["category_id"])

    # ── 8. brand_template_items ───────────────────────────────────────────────
    op.create_table(
        "brand_template_items",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("brand_template_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_id",            postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("master_service_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_order",       sa.Integer, nullable=False, server_default="0"),
        sa.Column("status",              sa.String(30), nullable=False, server_default="active"),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.UniqueConstraint("brand_template_id", "brand_id", name="uq_bti_template_brand"),
    )
    op.create_index("ix_bti_template", "brand_template_items", ["brand_template_id"])
    op.create_index("ix_bti_brand",    "brand_template_items", ["brand_id"])


def downgrade() -> None:
    op.drop_table("brand_template_items")
    op.drop_table("brand_templates")
    op.drop_table("brand_requests")
    op.drop_table("tenant_supported_brands")
    op.drop_table("brand_service_option_mappings")
    op.drop_table("brand_category_mappings")
    for col in ("status", "display_order", "created_by_user_id"):
        op.drop_column("master_service_brands", col)
    for col in ("code", "display_name", "status", "normalized_name", "alias_names_json",
                "replacement_brand_id", "website_url", "country_of_origin",
                "is_global", "display_order", "metadata_json",
                "created_by_user_id", "updated_by_user_id"):
        op.drop_column("brands", col)
