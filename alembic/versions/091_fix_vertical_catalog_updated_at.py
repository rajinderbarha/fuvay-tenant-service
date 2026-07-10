"""Fix missing updated_at columns on catalog_module_definitions / vertical_catalog_modules.

Migration 089 created these tables without `updated_at`, but their ORM models
inherit ServiceOSBase which declares both created_at AND updated_at as mapped
columns — every SELECT via the ORM 500'd with UndefinedColumnError. Same class
of bug fixed previously for master_data_audit_log (migration 087).

Revision ID: 091
Revises: 090
"""
from alembic import op
import sqlalchemy as sa

revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    for table in ("catalog_module_definitions", "vertical_catalog_modules"):
        if not _col_exists(table, "updated_at"):
            op.add_column(table, sa.Column(
                "updated_at", sa.DateTime(timezone=True),
                server_default=sa.text("now()"), nullable=False))


def downgrade() -> None:
    for table in ("catalog_module_definitions", "vertical_catalog_modules"):
        op.drop_column(table, "updated_at")
