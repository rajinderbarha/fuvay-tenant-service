"""Fix missing updated_at column on master_data_audit_log.

The ORM model (MasterDataAuditLog extends ServiceOSBase + TimestampMixin) has
required both created_at and updated_at since migration 055, but 055 only ever
created the created_at column — every INSERT via AdminCatalogService._audit()
has been failing with UndefinedColumnError.

Revision ID: 087
Revises: 086
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("master_data_audit_log")}
    if "updated_at" not in existing_columns:
        op.add_column(
            "master_data_audit_log",
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    op.drop_column("master_data_audit_log", "updated_at")
