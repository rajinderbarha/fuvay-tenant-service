"""Enterprise indexes for the Service Groups directory.

Revision ID: 255
Revises: 254
"""
from alembic import op


revision = "255"
down_revision = "254"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration intentionally uses PostgreSQL CONCURRENTLY so production
    # catalog traffic is not blocked while large indexes are built.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sg_name_trgm "
            "ON service_groups USING gin (lower(name) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sg_code_trgm "
            "ON service_groups USING gin (lower(code) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sg_slug_trgm "
            "ON service_groups USING gin (lower(slug) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sg_live_directory "
            "ON service_groups (category_id, status, display_order, name, id) "
            "WHERE deleted_at IS NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sg_retired_directory "
            "ON service_groups (deleted_at DESC, id) WHERE deleted_at IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_group_live_active "
            "ON master_services (service_group_id, is_active, id) "
            "WHERE deleted_at IS NULL AND service_group_id IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tenant_services_enabled_lookup "
            "ON tenant_services (master_service_id, tenant_id) "
            "WHERE deleted_at IS NULL AND is_enabled = true"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in (
            "ix_tenant_services_enabled_lookup",
            "ix_ms_group_live_active",
            "ix_sg_retired_directory",
            "ix_sg_live_directory",
            "ix_sg_slug_trgm",
            "ix_sg_code_trgm",
            "ix_sg_name_trgm",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
