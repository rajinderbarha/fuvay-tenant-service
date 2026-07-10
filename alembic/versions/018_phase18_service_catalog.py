"""Phase 18 — Service Catalog Engine (tenant-defined services)

Revision ID: 018
Revises: 017
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("service_catalog_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_type_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("service_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("pricing_model", sa.String(20), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("visit_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("pre_approval_limit", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer, nullable=True),
        sa.Column("checklist_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "service_type_id", name="uq_sci_tenant_service_type"),
    )
    op.create_index("ix_sci_tenant_active", "service_catalog_items", ["tenant_id", "is_active"])
    op.create_index("ix_sci_category", "service_catalog_items", ["tenant_id", "category"])


def downgrade() -> None:
    op.drop_index("ix_sci_category", table_name="service_catalog_items")
    op.drop_index("ix_sci_tenant_active", table_name="service_catalog_items")
    op.drop_table("service_catalog_items")
