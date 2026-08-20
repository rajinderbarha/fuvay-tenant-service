"""Enterprise directory indexes for service types and brands.

Revision ID: 257
Revises: 256
"""
from alembic import op

revision = "257"
down_revision = "256"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        statements = (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_types_name_trgm ON service_types USING gin (lower(name) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_types_code_trgm ON service_types USING gin (lower(code) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_types_live_directory ON service_types (status, type_family, customer_visible, display_order, name, id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_types_retired_directory ON service_types (deleted_at DESC, id) WHERE deleted_at IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brands_name_trgm ON brands USING gin (lower(name) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brands_code_trgm ON brands USING gin (lower(code) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brands_live_directory ON brands (status, is_global, display_order, name, id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_brands_retired_directory ON brands (deleted_at DESC, id) WHERE deleted_at IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_stm_scope_active ON service_type_mappings (category_id, service_group_id, service_id, type_id) WHERE status <> 'archived'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_bm_scope_active ON brand_mappings (category_id, service_group_id, service_id, brand_id) WHERE status <> 'archived'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tst_type_enabled ON tenant_service_types (service_type_id, tenant_id) WHERE is_enabled = true",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tsb_brand_enabled ON tenant_service_brands (brand_id, tenant_id) WHERE is_enabled = true",
        )
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = ("ix_tsb_brand_enabled", "ix_tst_type_enabled", "ix_bm_scope_active", "ix_stm_scope_active",
             "ix_brands_retired_directory", "ix_brands_live_directory", "ix_brands_code_trgm", "ix_brands_name_trgm",
             "ix_service_types_retired_directory", "ix_service_types_live_directory", "ix_service_types_code_trgm", "ix_service_types_name_trgm")
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
