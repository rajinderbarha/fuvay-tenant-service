"""Enterprise indexes for the Master Services directory.

Revision ID: 256
Revises: 255
"""
from alembic import op


revision = "256"
down_revision = "255"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Build without blocking catalog writes in production. pg_trgm is already
    # enabled by revision 255, but IF NOT EXISTS keeps fresh installs robust.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_name_trgm "
            "ON master_services USING gin (lower(service_name) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_slug_trgm "
            "ON master_services USING gin (lower(slug) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_live_directory "
            "ON master_services (category_id, service_group_id, is_active, display_order, service_name, id) "
            "WHERE deleted_at IS NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_retired_directory "
            "ON master_services (deleted_at DESC, id) WHERE deleted_at IS NOT NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ms_job_model_live "
            "ON master_services (job_type, pricing_model, id) WHERE deleted_at IS NULL"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_msjt_active_lookup "
            "ON master_service_job_types (master_service_id, job_type_id) WHERE is_active = true"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sjw_current_published_lookup "
            "ON service_job_workflow (master_service_id, job_type_id) "
            "WHERE is_current = true AND status = 'published'"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in (
            "ix_sjw_current_published_lookup",
            "ix_msjt_active_lookup",
            "ix_ms_job_model_live",
            "ix_ms_retired_directory",
            "ix_ms_live_directory",
            "ix_ms_slug_trgm",
            "ix_ms_name_trgm",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
