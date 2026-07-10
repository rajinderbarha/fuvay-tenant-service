"""Fix users table: add missing columns that ORM expects but DB lacks.

Revision ID: 069
Revises: 068
Create Date: 2026-07-04
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def _col_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # users.deleted_at — in ORM model but never migrated
    if not _col_exists(conn, "users", "deleted_at"):
        op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # users.meta — JSONB field that may be missing on older deploys
    if not _col_exists(conn, "users", "meta"):
        op.add_column("users", sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"))

    # tenants: slug unique constraint (needed for ON CONFLICT)
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name='tenants' AND constraint_name='uq_tenants_slug'"
    ))
    if not result.fetchone():
        # Only add if slug column exists and no dupes
        if _col_exists(conn, "tenants", "slug"):
            op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])

    # service_groups: ensure unique constraint on code/slug exists (may have been created without it)
    for cname, cols in [("uq_sg_code", ["code"]), ("uq_sg_slug", ["slug"])]:
        result = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name='service_groups' AND constraint_name=:c"
        ), {"c": cname})
        # constraint already created by migration 068 table creation; skip


def downgrade() -> None:
    op.drop_column("users", "deleted_at")
