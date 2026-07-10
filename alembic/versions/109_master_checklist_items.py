"""Phase 2 catalog certification — master_checklist_items table.

Admin/master-catalog-level checklist system, distinct from the tenant-owned
runtime checklist system (app/engines/field_ops/models.py::
ServiceChecklistTemplate). Closes the Phase 2 Module 8 hard gate: "AC Repair
must have at least one technician completion checklist item."

Revision ID: 109
Revises: 108
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "109"
down_revision = "108"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "master_checklist_items" in inspector.get_table_names():
        return

    op.create_table(
        "master_checklist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=text("gen_random_uuid()")),
        sa.Column("category_id", UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_step_key", sa.String(100), nullable=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("owner_role", sa.String(30), nullable=False, server_default="technician"),
        sa.Column("customer_visible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("staff_visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_visible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vertical_type", sa.String(50), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.UniqueConstraint("slug", name="uq_mci_slug"),
    )
    op.create_index("ix_mci_category", "master_checklist_items", ["category_id"])
    op.create_index("ix_mci_master_service", "master_checklist_items", ["master_service_id"])
    op.create_index("ix_mci_active", "master_checklist_items", ["is_active"])
    op.create_index("ix_mci_status", "master_checklist_items", ["status"])


def downgrade() -> None:
    op.drop_table("master_checklist_items")
