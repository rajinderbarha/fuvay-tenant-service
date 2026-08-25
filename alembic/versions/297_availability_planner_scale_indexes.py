"""Scale indexes for the provider availability planner.

Revision ID: 297
Revises: 296

The planner is tenant-scoped, pages field technicians, filters JSONB service
capabilities, and resolves patterns, overrides, leave, and jobs for a bounded
date range. These indexes match those access paths without introducing a
second availability store.
"""
from alembic import op


revision = "297"
down_revision = "296"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ptm_availability_roster ON provider_team_members (tenant_id, member_type, status, lower(full_name), id) WHERE deleted_at IS NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ptm_supported_offerings_gin ON provider_team_members USING gin (supported_offering_ids jsonb_path_ops) WHERE deleted_at IS NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_par_availability_scope_day ON provider_availability_rules (tenant_id, scope_type, scope_id, day_of_week) WHERE is_active=true",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_availability_staff_date ON service_jobs (tenant_id, assigned_staff_id, scheduled_date) WHERE assigned_staff_id IS NOT NULL AND scheduled_date IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sao_availability_staff_date ON staff_availability_overrides (tenant_id, staff_member_id, override_date)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sto_availability_staff_range ON staff_time_off (tenant_id, staff_member_id, start_date, end_date) WHERE status='approved'",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_stor_availability_staff_range ON staff_time_off_requests (tenant_id, staff_member_id, start_date, end_date) WHERE status='approved' AND cancelled_at IS NULL",
    )
    with op.get_context().autocommit_block():
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_stor_availability_staff_range",
        "ix_sto_availability_staff_range",
        "ix_sao_availability_staff_date",
        "ix_sj_availability_staff_date",
        "ix_par_availability_scope_day",
        "ix_ptm_supported_offerings_gin",
        "ix_ptm_availability_roster",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
