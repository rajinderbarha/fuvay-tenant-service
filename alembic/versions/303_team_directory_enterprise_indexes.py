"""Enterprise indexes for the tenant team directory.

Revision ID: 303
Revises: 302
"""
from alembic import op

revision = "303"
down_revision = "302"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ptm_email_trgm
        ON provider_team_members USING gin (lower(email) gin_trgm_ops)
        WHERE deleted_at IS NULL AND email IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ptm_phone_trgm
        ON provider_team_members USING gin (lower(phone) gin_trgm_ops)
        WHERE deleted_at IS NULL AND phone IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ptm_designation_trgm
        ON provider_team_members USING gin (lower(designation) gin_trgm_ops)
        WHERE deleted_at IS NULL AND designation IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ptm_tenant_presence_roster
        ON provider_team_members (tenant_id, status, availability_state, lower(full_name), id)
        WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_pal_tenant_entity_created
        ON platform_audit_logs (tenant_id, entity_id, created_at DESC, id DESC)
        WHERE entity_id IS NOT NULL
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_tenant_docs_staff_current_created
        ON tenant_documents (tenant_id, staff_member_id, created_at DESC, id DESC)
        WHERE staff_member_id IS NOT NULL AND is_current = true
    """)


def downgrade() -> None:
    for name in (
        "ix_tenant_docs_staff_current_created",
        "ix_pal_tenant_entity_created",
        "ix_ptm_tenant_presence_roster",
        "ix_ptm_designation_trgm",
        "ix_ptm_phone_trgm",
        "ix_ptm_email_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
