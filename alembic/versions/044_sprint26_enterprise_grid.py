"""Sprint 26 — Enterprise Filters + Data Grid System."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade():
    # ── enterprise_saved_views ────────────────────────────────────────────────
    op.create_table(
        "enterprise_saved_views",
        sa.Column("id",            UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",     UUID(as_uuid=True), nullable=True),
        sa.Column("scope",         sa.String(32),   nullable=False),  # admin|provider|staff
        sa.Column("resource_key",  sa.String(64),   nullable=False),
        sa.Column("view_name",     sa.String(128),  nullable=False),
        sa.Column("is_default",    sa.Boolean,      nullable=False, server_default=sa.false()),
        sa.Column("filters",       JSONB,           nullable=False, server_default=sa.text("'{}'")),
        sa.Column("sort",          JSONB,           nullable=False, server_default=sa.text("'{}'")),
        sa.Column("columns",       JSONB,           nullable=False, server_default=sa.text("'[]'")),
        sa.Column("page_size",     sa.Integer,      nullable=False, server_default=sa.text("25")),
        sa.Column("visibility",    sa.String(32),   nullable=False, server_default=sa.text("'private'")),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index("ix_esv_owner_resource", "enterprise_saved_views", ["owner_user_id", "resource_key"])
    op.create_index("ix_esv_tenant_resource", "enterprise_saved_views", ["tenant_id", "resource_key"])

    # ── enterprise_column_preferences ────────────────────────────────────────
    op.create_table(
        "enterprise_column_preferences",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",      UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("resource_key", sa.String(64),  nullable=False),
        sa.Column("columns",      JSONB,          nullable=False, server_default=sa.text("'[]'")),
        sa.Column("density",      sa.String(16),  nullable=False, server_default=sa.text("'comfortable'")),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()")),
        sa.UniqueConstraint("user_id", "resource_key", name="uq_colpref_user_resource"),
    )
    op.create_index("ix_ecp_user_resource", "enterprise_column_preferences", ["user_id", "resource_key"])

    # ── enterprise_export_jobs ───────────────────────────────────────────────
    op.create_table(
        "enterprise_export_jobs",
        sa.Column("id",                    UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requested_by_user_id",  UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",             UUID(as_uuid=True), nullable=True),
        sa.Column("resource_key",          sa.String(64),  nullable=False),
        sa.Column("status",                sa.String(32),  nullable=False, server_default=sa.text("'pending'")),
        sa.Column("export_format",         sa.String(16),  nullable=False, server_default=sa.text("'csv'")),
        sa.Column("filters",               JSONB,          nullable=False, server_default=sa.text("'{}'")),
        sa.Column("columns",               JSONB,          nullable=False, server_default=sa.text("'[]'")),
        sa.Column("row_count",             sa.Integer,     nullable=True),
        sa.Column("file_url",              sa.Text,        nullable=True),
        sa.Column("failure_reason",        sa.Text,        nullable=True),
        sa.Column("expires_at",            sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",            sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",            sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index("ix_eej_user",    "enterprise_export_jobs", ["requested_by_user_id"])
    op.create_index("ix_eej_tenant",  "enterprise_export_jobs", ["tenant_id"])
    op.create_index("ix_eej_resource","enterprise_export_jobs", ["resource_key"])


def downgrade():
    op.drop_table("enterprise_export_jobs")
    op.drop_table("enterprise_column_preferences")
    op.drop_table("enterprise_saved_views")
