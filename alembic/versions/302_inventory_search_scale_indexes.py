"""Tenant-scoped trigram indexes for inventory catalogue search.

Revision ID: 302
Revises: 301
"""
from alembic import op


revision = "302"
down_revision = "301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_items_name_trgm ON inventory_items USING gin (name gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_items_sku_trgm ON inventory_items USING gin (sku gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inventory_items_category_trgm ON inventory_items USING gin (category gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sjpr_tenant_inventory_status ON service_job_parts_requests (tenant_id, inventory_item_id, status) WHERE inventory_item_id IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sjpr_tenant_inventory_status")
    op.execute("DROP INDEX IF EXISTS ix_inventory_items_category_trgm")
    op.execute("DROP INDEX IF EXISTS ix_inventory_items_sku_trgm")
    op.execute("DROP INDEX IF EXISTS ix_inventory_items_name_trgm")

