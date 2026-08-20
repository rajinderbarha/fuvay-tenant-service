"""Enterprise lifecycle and directory indexes for checklist catalog.

Revision ID: 258
Revises: 257
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "258"
down_revision = "257"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("checklist_templates", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("checklist_templates", sa.Column("archived_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("checklist_templates", sa.Column("archive_reason", sa.Text(), nullable=True))
    op.add_column("job_type_checklist_mappings", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_type_checklist_mappings", sa.Column("disable_reason", sa.Text(), nullable=True))
    with op.get_context().autocommit_block():
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        statements = (
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ct_name_trgm ON checklist_templates USING gin (lower(name) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ct_code_trgm ON checklist_templates USING gin (lower(code) gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ct_live_directory ON checklist_templates (purpose, owner_scope, updated_at DESC, id) WHERE status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ct_retired_directory ON checklist_templates (archived_at DESC, id) WHERE status = 'archived'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ctv_latest ON checklist_template_versions (checklist_template_id, version_number DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jtcm_active_job_phase ON job_type_checklist_mappings (master_service_job_type_id, phase, display_order, id) WHERE status = 'active' AND usage <> 'DISABLED'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jtcm_active_version ON job_type_checklist_mappings (checklist_template_version_id, id) WHERE status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jci_tenant_state_created ON job_checklist_instances (tenant_id, state, created_at DESC, id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jci_version_state ON job_checklist_instances (checklist_template_version_id, state)",
        )
        for statement in statements:
            op.execute(statement)


def downgrade() -> None:
    names = (
        "ix_jci_version_state", "ix_jci_tenant_state_created", "ix_jtcm_active_version",
        "ix_jtcm_active_job_phase", "ix_ctv_latest", "ix_ct_retired_directory",
        "ix_ct_live_directory", "ix_ct_code_trgm", "ix_ct_name_trgm",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
    op.drop_column("job_type_checklist_mappings", "disable_reason")
    op.drop_column("job_type_checklist_mappings", "disabled_at")
    op.drop_column("checklist_templates", "archive_reason")
    op.drop_column("checklist_templates", "archived_by")
    op.drop_column("checklist_templates", "archived_at")
