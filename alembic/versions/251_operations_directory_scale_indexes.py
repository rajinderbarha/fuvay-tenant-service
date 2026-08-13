"""Scale indexes for admin operations directories.

Revision ID: 251
Revises: 250
"""
from alembic import op


revision = "251"
down_revision = "250"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These indexes are intentionally concurrent: the affected tables are
    # customer-facing hot paths and must remain writable during deployment.
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        statements = (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_name_trgm ON users USING gin (lower(full_name) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_trgm ON users USING gin (lower(email) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_phone_trgm ON users USING gin (phone gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_role_created_id ON users (role, created_at DESC, id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_tenant_role_created ON users (tenant_id, role, created_at DESC, id) WHERE deleted_at IS NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_customer_addresses_latest ON customer_addresses (customer_id, created_at DESC) INCLUDE (city, district, state, zipcode)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_service_bookings_customer_activity ON service_bookings (customer_id, created_at DESC) INCLUDE (status, tenant_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_customer_complaints_customer_status ON customer_complaints (customer_id, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_customer_reviews_customer_rating ON customer_reviews (customer_id) INCLUDE (overall_rating)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_complaints_tenant_status_created ON customer_complaints (tenant_id, status, created_at DESC, id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_complaints_priority_sla_created ON customer_complaints (priority, sla_status, created_at DESC, id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_complaints_number_trgm ON customer_complaints USING gin (lower(complaint_number) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_complaints_title_trgm ON customer_complaints USING gin (lower(title) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_complaint_messages_complaint ON complaint_messages (complaint_id)",
        )
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in (
            "ix_complaint_messages_complaint", "ix_complaints_title_trgm",
            "ix_complaints_number_trgm", "ix_complaints_priority_sla_created",
            "ix_complaints_tenant_status_created", "ix_customer_reviews_customer_rating",
            "ix_customer_complaints_customer_status", "ix_service_bookings_customer_activity",
            "ix_customer_addresses_latest", "ix_users_tenant_role_created",
            "ix_users_role_created_id", "ix_users_phone_trgm", "ix_users_email_trgm",
            "ix_users_name_trgm",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
