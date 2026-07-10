"""073 — package_audit_logs: missing table that blocks registration completion.

The PackageAuditLog model was defined in package_commerce/models.py but never
migrated. The _pkg_audit() call inside create_package_assignment() adds a row to
this table; when db.commit() flushes it, PostgreSQL raises
'relation "package_audit_logs" does not exist' — caught as the generic
'Failed to create your account' error on the registration /complete endpoint.

Revision ID: 073
Revises: 072
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    return conn.dialect.has_table(conn, name)


def _index_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"), {"n": name}
    ).scalar()
    return result is not None


def upgrade() -> None:
    if not _table_exists("package_audit_logs"):
        op.create_table(
            "package_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                       server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id",          postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("package_id",         postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("package_purchase_id",postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("actor_user_id",       postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("actor_role",          sa.String(30),  nullable=True),
            sa.Column("action",              sa.String(60),  nullable=False),
            sa.Column("old_value",           postgresql.JSONB, nullable=True),
            sa.Column("new_value",           postgresql.JSONB, nullable=True),
            sa.Column("reason",              sa.Text,        nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=False),
        )

    for idx_name, col in [
        ("ix_pal_tenant_id",  "tenant_id"),
        ("ix_pal_package_id", "package_id"),
        ("ix_pal_action",     "action"),
    ]:
        if not _index_exists(idx_name):
            op.create_index(idx_name, "package_audit_logs", [col])


def downgrade() -> None:
    pass  # additive — no destructive downgrade
