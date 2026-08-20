"""Provider directory search and detail aggregate indexes.

Revision ID: 262
Revises: 261
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "262"
down_revision = "261"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trigram indexes keep contains-search responsive without changing its
    # business semantics to prefix-only matching. CONCURRENTLY cannot run in
    # Alembic's transaction, so these remain normal DDL for deterministic
    # deploys; production deploy tooling should schedule this migration in a
    # low-write window.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index("ix_tenants_business_name_trgm", "tenants", [sa.text("lower(business_name) gin_trgm_ops")], postgresql_using="gin")
    op.create_index("ix_tenants_tenant_name_trgm", "tenants", [sa.text("lower(tenant_name) gin_trgm_ops")], postgresql_using="gin")
    op.create_index("ix_tenants_email_trgm", "tenants", [sa.text("lower(email) gin_trgm_ops")], postgresql_using="gin")
    op.create_index("ix_tenants_phone_trgm", "tenants", [sa.text("lower(phone) gin_trgm_ops")], postgresql_using="gin")
    op.create_index("ix_tenants_tenant_code_trgm", "tenants", [sa.text("lower(tenant_code) gin_trgm_ops")], postgresql_using="gin")
    op.create_index("ix_pal_tenant_created", "platform_audit_logs", ["tenant_id", sa.text("created_at DESC")])
    op.create_index("ix_sj_tenant_status", "service_jobs", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_sj_tenant_status", table_name="service_jobs")
    op.drop_index("ix_pal_tenant_created", table_name="platform_audit_logs")
    for name in ("ix_tenants_tenant_code_trgm", "ix_tenants_phone_trgm", "ix_tenants_email_trgm", "ix_tenants_tenant_name_trgm", "ix_tenants_business_name_trgm"):
        op.drop_index(name, table_name="tenants")
