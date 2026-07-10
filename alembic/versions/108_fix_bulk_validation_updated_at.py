"""Phase 2 catalog cert fix — add missing updated_at to service_setup_bulk_validation_results.

BulkValidationResult (app/engines/service_setup/models.py) extends
ServiceOSBase, whose TimestampMixin unconditionally adds both created_at AND
updated_at to every ORM model — migration 098 only created created_at,
so any UPDATE/refresh touching this table raised
asyncpg.exceptions.UndefinedColumnError: column "updated_at" ... does not
exist. Found live while certifying the Bulk Setup Wizard's /validate
endpoint (POST /v1/admin/service-setup/bulk-wizard/drafts/{id}/validate).

Revision ID: 108
Revises: 107
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "108"
down_revision = "107"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("service_setup_bulk_validation_results")}
    if "updated_at" not in cols:
        op.add_column(
            "service_setup_bulk_validation_results",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=text("now()")),
        )


def downgrade() -> None:
    op.drop_column("service_setup_bulk_validation_results", "updated_at")
