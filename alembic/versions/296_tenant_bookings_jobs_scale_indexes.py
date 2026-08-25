"""Scale indexes for the provider Bookings & Jobs command center.

Revision ID: 296
Revises: 295

The workspace filters inside a tenant by assignment, schedule, offering,
job type, technician and open complaint. It also supports contains-search
over booking customer and technician names. These indexes keep those paths
bounded as the platform grows while CONCURRENTLY avoids blocking hot writes.
"""
from alembic import op


revision = "296"
down_revision = "295"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_bj_tenant_assignment_created ON service_jobs (tenant_id, assignment_status, created_at DESC, id DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_bj_tenant_schedule ON service_jobs (tenant_id, scheduled_date, id) WHERE scheduled_date IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_bj_tenant_offering_created ON service_jobs (tenant_id, offering_id, created_at DESC, id DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_bj_tenant_staff_created ON service_jobs (tenant_id, assigned_staff_id, created_at DESC, id DESC) WHERE assigned_staff_id IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_bj_tenant_job_type_created ON service_jobs (tenant_id, job_type_id, created_at DESC, id DESC) WHERE job_type_id IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cc_bj_tenant_job_status ON customer_complaints (tenant_id, job_id, status) WHERE job_id IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sb_customer_name_trgm ON service_bookings USING gin (lower(customer_name) gin_trgm_ops)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sb_customer_phone_trgm ON service_bookings USING gin (lower(customer_phone) gin_trgm_ops)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ptm_full_name_trgm ON provider_team_members USING gin (lower(full_name) gin_trgm_ops)",
    )
    with op.get_context().autocommit_block():
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_ptm_full_name_trgm", "ix_sb_customer_phone_trgm", "ix_sb_customer_name_trgm",
        "ix_cc_bj_tenant_job_status", "ix_sj_bj_tenant_job_type_created",
        "ix_sj_bj_tenant_staff_created", "ix_sj_bj_tenant_offering_created",
        "ix_sj_bj_tenant_schedule", "ix_sj_bj_tenant_assignment_created",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
