"""Scale indexes for the unified Home Services operations workspace.

Revision ID: 270
Revises: 269
"""
from alembic import op


revision = "270"
down_revision = "269"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All indexes are built concurrently because service_jobs and booking
    # drafts are customer-facing hot tables in production.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        statements = (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_status_created_id ON service_jobs (status, created_at DESC, id DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_assignment_created_id ON service_jobs (assignment_status, created_at DESC, id DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_tenant_status_created_id ON service_jobs (tenant_id, status, created_at DESC, id DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_city_created_id ON service_jobs (city, created_at DESC, id DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_city_status_created_id ON home_service_booking_drafts (city, status, created_at DESC, id DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sjq_current_job_status ON service_job_quotes (job_id, version_number DESC) INCLUDE (status) WHERE is_current",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_job_number_trgm ON service_jobs USING gin (lower(job_number) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sb_booking_number_trgm ON service_bookings USING gin (lower(booking_number) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_customer_name_trgm ON home_service_booking_drafts USING gin (lower(customer_name) gin_trgm_ops)",
        )
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_hsbd_customer_name_trgm", "ix_sb_booking_number_trgm",
        "ix_sj_job_number_trgm", "ix_sjq_current_job_status",
        "ix_hsbd_ops_city_status_created_id", "ix_sj_ops_city_created_id",
        "ix_sj_ops_tenant_status_created_id", "ix_sj_ops_assignment_created_id",
        "ix_sj_ops_status_created_id",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
