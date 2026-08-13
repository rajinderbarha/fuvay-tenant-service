"""Catalog enterprise directory indexes.

Revision ID: 252
Revises: 251
"""
from alembic import op

revision = "252"
down_revision = "251"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These are read-heavy control-plane directories, but writes still occur
    # during releases. Build without blocking those writes in production.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_categories_directory ON service_categories (vertical_type, is_active, display_order, id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_categories_finance_flow ON service_categories (finance_model, customer_flow_type, id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_categories_name_trgm ON service_categories USING gin (lower(name) gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_categories_slug_trgm ON service_categories USING gin (lower(slug) gin_trgm_ops)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verticals_directory ON verticals (is_enabled, lifecycle_status, release_stage, sort_order, id)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_verticals_label_trgm ON verticals USING gin (lower(label) gin_trgm_ops)")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_verticals_label_trgm")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_verticals_directory")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_service_categories_slug_trgm")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_service_categories_name_trgm")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_service_categories_finance_flow")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_service_categories_directory")
