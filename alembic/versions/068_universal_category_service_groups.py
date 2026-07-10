"""Universal Category Foundation — service_groups table + category universal fields.

Revision ID: 068
Revises: 067
Create Date: 2026-07-04

Additive changes only — all new columns are nullable or have server defaults.
Existing rows and queries are unaffected.

Changes:
  1. Create service_groups table (intermediate grouping layer between categories and services)
  2. Add universal fields to service_categories (vertical_type, finance_model, etc.)
  3. Add service_group_id FK to master_services
  4. Add service_option_id FK to service_pricing_rules (per-option pricing)
  5. Add catalog_category_id UUID FK to city_tier_configs (parallel with legacy string field)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name=:t"
    ), {"t": table})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create service_groups table (idempotent)
    if not _table_exists(conn, "service_groups"):
        op.create_table(
            "service_groups",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("service_categories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code", sa.String(100), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
            sa.Column("icon_url", sa.String(500), nullable=True),
            sa.Column("metadata_json", JSONB, nullable=True),
            sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_unique_constraint("uq_sg_code", "service_groups", ["code"])
        op.create_unique_constraint("uq_sg_slug", "service_groups", ["slug"])
        op.create_index("ix_sg_category",    "service_groups", ["category_id"])
        op.create_index("ix_sg_status",      "service_groups", ["status"])
        op.create_index("ix_sg_deleted_at",  "service_groups", ["deleted_at"])

    # 2. Add universal fields to service_categories (idempotent)
    if not _col_exists(conn, "service_categories", "vertical_type"):
        op.add_column("service_categories",
            sa.Column("vertical_type", sa.String(50), nullable=True))
    if not _col_exists(conn, "service_categories", "finance_model"):
        op.add_column("service_categories",
            sa.Column("finance_model", sa.String(50), nullable=True))
    if not _col_exists(conn, "service_categories", "provider_business_model"):
        op.add_column("service_categories",
            sa.Column("provider_business_model", sa.String(50), nullable=True))
    if not _col_exists(conn, "service_categories", "requires_location"):
        op.add_column("service_categories",
            sa.Column("requires_location", sa.Boolean, nullable=False, server_default="true"))
    if not _col_exists(conn, "service_categories", "requires_schedule"):
        op.add_column("service_categories",
            sa.Column("requires_schedule", sa.Boolean, nullable=False, server_default="false"))
    if not _col_exists(conn, "service_categories", "requires_brand"):
        op.add_column("service_categories",
            sa.Column("requires_brand", sa.Boolean, nullable=False, server_default="false"))
    if not _col_exists(conn, "service_categories", "requires_service_option"):
        op.add_column("service_categories",
            sa.Column("requires_service_option", sa.Boolean, nullable=False, server_default="false"))
    if not _col_exists(conn, "service_categories", "requires_issue_type"):
        op.add_column("service_categories",
            sa.Column("requires_issue_type", sa.Boolean, nullable=False, server_default="false"))
    if not _col_exists(conn, "service_categories", "tenant_selectable"):
        op.add_column("service_categories",
            sa.Column("tenant_selectable", sa.Boolean, nullable=False, server_default="true"))
    if not _col_exists(conn, "service_categories", "pricing_supported"):
        op.add_column("service_categories",
            sa.Column("pricing_supported", sa.Boolean, nullable=False, server_default="true"))

    if not _index_exists(conn, "ix_sc_vertical_type"):
        op.create_index("ix_sc_vertical_type", "service_categories", ["vertical_type"])
    if not _index_exists(conn, "ix_sc_finance_model"):
        op.create_index("ix_sc_finance_model", "service_categories", ["finance_model"])

    # 3. Add service_group_id FK to master_services (idempotent)
    if not _col_exists(conn, "master_services", "service_group_id"):
        op.add_column("master_services",
            sa.Column("service_group_id", UUID(as_uuid=True),
                      sa.ForeignKey("service_groups.id", ondelete="SET NULL"),
                      nullable=True))
    if not _index_exists(conn, "ix_ms_service_group"):
        op.create_index("ix_ms_service_group", "master_services", ["service_group_id"])

    # 4. Add service_option_id FK to service_pricing_rules (idempotent)
    if not _col_exists(conn, "service_pricing_rules", "service_option_id"):
        op.add_column("service_pricing_rules",
            sa.Column("service_option_id", UUID(as_uuid=True),
                      sa.ForeignKey("master_service_options.id", ondelete="SET NULL"),
                      nullable=True))
    if not _index_exists(conn, "ix_spr_service_option"):
        op.create_index("ix_spr_service_option", "service_pricing_rules", ["service_option_id"])

    # 5. Add catalog_category_id UUID FK to city_tier_configs (idempotent)
    if not _col_exists(conn, "city_tier_configs", "catalog_category_id"):
        op.add_column("city_tier_configs",
            sa.Column("catalog_category_id", UUID(as_uuid=True),
                      sa.ForeignKey("service_categories.id", ondelete="SET NULL"),
                      nullable=True))
    if not _index_exists(conn, "ix_ctc_catalog_category"):
        op.create_index("ix_ctc_catalog_category", "city_tier_configs", ["catalog_category_id"])


def downgrade() -> None:
    op.drop_index("ix_ctc_catalog_category", "city_tier_configs")
    op.drop_column("city_tier_configs", "catalog_category_id")

    op.drop_index("ix_spr_service_option", "service_pricing_rules")
    op.drop_column("service_pricing_rules", "service_option_id")

    op.drop_index("ix_ms_service_group", "master_services")
    op.drop_column("master_services", "service_group_id")

    op.drop_index("ix_sc_finance_model", "service_categories")
    op.drop_index("ix_sc_vertical_type", "service_categories")
    op.drop_column("service_categories", "pricing_supported")
    op.drop_column("service_categories", "tenant_selectable")
    op.drop_column("service_categories", "requires_issue_type")
    op.drop_column("service_categories", "requires_service_option")
    op.drop_column("service_categories", "requires_brand")
    op.drop_column("service_categories", "requires_schedule")
    op.drop_column("service_categories", "requires_location")
    op.drop_column("service_categories", "provider_business_model")
    op.drop_column("service_categories", "finance_model")
    op.drop_column("service_categories", "vertical_type")

    op.drop_index("ix_sg_deleted_at", "service_groups")
    op.drop_index("ix_sg_status", "service_groups")
    op.drop_index("ix_sg_category", "service_groups")
    op.drop_constraint("uq_sg_slug", "service_groups", type_="unique")
    op.drop_constraint("uq_sg_code", "service_groups", type_="unique")
    op.drop_table("service_groups")
