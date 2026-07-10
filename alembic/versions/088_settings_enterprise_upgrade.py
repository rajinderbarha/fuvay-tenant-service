"""Platform Settings Enterprise Upgrade — metadata columns + feature_flags table.

- Extend platform_settings with label, category, allowed_values_json, is_secret,
  risk_level, requires_approval, requires_restart, is_runtime_editable, owner_module, status
- Extend tenant_settings with expires_at, requires_approval, status
- Extend setting_audit_logs with request_id, risk_level, action_type
- Create feature_flags (seeded with 0 rows — flags are created via the admin UI/seed script)

Revision ID: 088
Revises: 087
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    def _table_exists(t: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    # ── platform_settings ───────────────────────────────────────────────────
    if not _col_exists("platform_settings", "label"):
        op.add_column("platform_settings", sa.Column("label", sa.String(200), nullable=True))
    if not _col_exists("platform_settings", "category"):
        op.add_column("platform_settings", sa.Column("category", sa.String(60), server_default="general_platform", nullable=False))
    if not _col_exists("platform_settings", "allowed_values_json"):
        op.add_column("platform_settings", sa.Column("allowed_values_json", JSONB, nullable=True))
    if not _col_exists("platform_settings", "is_secret"):
        op.add_column("platform_settings", sa.Column("is_secret", sa.Boolean, server_default="false", nullable=False))
    if not _col_exists("platform_settings", "risk_level"):
        op.add_column("platform_settings", sa.Column("risk_level", sa.String(20), server_default="'low'", nullable=False))
    if not _col_exists("platform_settings", "requires_approval"):
        op.add_column("platform_settings", sa.Column("requires_approval", sa.Boolean, server_default="false", nullable=False))
    if not _col_exists("platform_settings", "requires_restart"):
        op.add_column("platform_settings", sa.Column("requires_restart", sa.Boolean, server_default="false", nullable=False))
    if not _col_exists("platform_settings", "is_runtime_editable"):
        op.add_column("platform_settings", sa.Column("is_runtime_editable", sa.Boolean, server_default="true", nullable=False))
    if not _col_exists("platform_settings", "owner_module"):
        op.add_column("platform_settings", sa.Column("owner_module", sa.String(60), nullable=True))
    if not _col_exists("platform_settings", "status"):
        op.add_column("platform_settings", sa.Column("status", sa.String(20), server_default="'active'", nullable=False))

    # ── tenant_settings ──────────────────────────────────────────────────────
    if not _col_exists("tenant_settings", "expires_at"):
        op.add_column("tenant_settings", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("tenant_settings", "requires_approval"):
        op.add_column("tenant_settings", sa.Column("requires_approval", sa.Boolean, server_default="false", nullable=False))
    if not _col_exists("tenant_settings", "status"):
        op.add_column("tenant_settings", sa.Column("status", sa.String(20), server_default="'active'", nullable=False))

    # ── setting_audit_logs ───────────────────────────────────────────────────
    if not _col_exists("setting_audit_logs", "request_id"):
        op.add_column("setting_audit_logs", sa.Column("request_id", sa.String(100), nullable=True))
    if not _col_exists("setting_audit_logs", "risk_level"):
        op.add_column("setting_audit_logs", sa.Column("risk_level", sa.String(20), server_default="'low'", nullable=False))
    if not _col_exists("setting_audit_logs", "action_type"):
        op.add_column("setting_audit_logs", sa.Column("action_type", sa.String(30), server_default="'updated'", nullable=False))

    # ── feature_flags ────────────────────────────────────────────────────────
    if not _table_exists("feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("flag_key", sa.String(120), nullable=False, unique=True),
            sa.Column("label", sa.String(200), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("status", sa.String(20), server_default="'disabled'", nullable=False),
            sa.Column("rollout_type", sa.String(30), server_default="'global'", nullable=False),
            sa.Column("rollout_percent", sa.Integer, nullable=True),
            sa.Column("category_scope", sa.String(60), nullable=True),
            sa.Column("tenant_scope", UUID(as_uuid=True), nullable=True),
            sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("owner_module", sa.String(60), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_ff_flag_key", "feature_flags", ["flag_key"])
        op.create_index("ix_ff_status", "feature_flags", ["status"])


def downgrade() -> None:
    op.drop_table("feature_flags")
    for col in ("action_type", "risk_level", "request_id"):
        op.drop_column("setting_audit_logs", col)
    for col in ("status", "requires_approval", "expires_at"):
        op.drop_column("tenant_settings", col)
    for col in ("status", "owner_module", "is_runtime_editable", "requires_restart",
                "requires_approval", "risk_level", "is_secret", "allowed_values_json",
                "category", "label"):
        op.drop_column("platform_settings", col)
