"""Scale indexes for the platform Home Services operations workspace.

Revision ID: 314
Revises: 313

The admin command center filters the canonical request/job pipeline by
postcode and immutable state/district address snapshots.  Expression indexes
keep those exact, case-normalized filters indexable without duplicating address
fields or introducing another operational record model.
"""
from alembic import op


revision = "314"
down_revision = "313"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_zip_created ON service_jobs (zipcode, created_at DESC, id DESC) WHERE zipcode IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_zip_created ON home_service_booking_drafts (zipcode, created_at DESC, id DESC) WHERE zipcode IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_state_created ON service_jobs (lower(address_snapshot->>'state'), created_at DESC, id DESC) WHERE address_snapshot->>'state' IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_state_created ON home_service_booking_drafts (lower(address_snapshot->>'state'), created_at DESC, id DESC) WHERE address_snapshot->>'state' IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_district_created ON service_jobs (lower(address_snapshot->>'district'), created_at DESC, id DESC) WHERE address_snapshot->>'district' IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_district_created ON home_service_booking_drafts (lower(address_snapshot->>'district'), created_at DESC, id DESC) WHERE address_snapshot->>'district' IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sj_ops_updated ON service_jobs (updated_at DESC, id DESC)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_hsbd_ops_updated ON home_service_booking_drafts (updated_at DESC, id DESC)",
    )
    with op.get_context().autocommit_block():
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_hsbd_ops_updated", "ix_sj_ops_updated",
        "ix_hsbd_ops_district_created", "ix_sj_ops_district_created",
        "ix_hsbd_ops_state_created", "ix_sj_ops_state_created",
        "ix_hsbd_ops_zip_created", "ix_sj_ops_zip_created",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
