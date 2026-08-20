"""Case-folded city indexes for operations filters.

Revision ID: 271
Revises: 270
"""
from alembic import op


revision = "271"
down_revision = "270"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_city_lower_created_id ON service_jobs (lower(city), created_at DESC, id DESC)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_city_lower_status_created_id ON home_service_booking_drafts (lower(city), status, created_at DESC, id DESC)")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_hsbd_ops_city_lower_status_created_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_sj_ops_city_lower_created_id")
