"""Fix missing updated_at column on admin_bulk_setup_runs and service_setup_bulk_runs.

Both AdminBulkSetupRun (app/engines/admin_catalog/models.py, migration 059,
Sprint 34H) and BulkRun (app/engines/service_setup/models.py, migration 098,
the newer enterprise bulk wizard) inherit `updated_at` from ServiceOSBase, but
neither migration actually created that column on its table — every call to
GET /v1/admin/bulk-setup/runs and GET /v1/admin/service-setup/bulk-wizard/runs
500'd with UndefinedColumnError. Same class of schema-drift bug fixed
previously for payment_records (migration 094), catalog_module_definitions/
vertical_catalog_modules (migration 091), and master_data_audit_log
(Sprint 34C bugfix).

Revision ID: 099
Revises: 098
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None

_TABLES = ["admin_bulk_setup_runs", "service_setup_bulk_runs"]


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    for table in _TABLES:
        if not _col_exists(table, "updated_at"):
            op.add_column(table,
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                          server_default=text("now()")))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "updated_at")
