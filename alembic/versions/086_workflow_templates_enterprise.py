"""Workflow Templates Enterprise Upgrade — runtime settings, versioning, transitions,
service mapping table for master_workflow_templates.

Revision ID: 086
Revises: 085
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "086"
down_revision = "085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── master_workflow_templates: runtime settings + versioning ──────────────
    op.add_column("master_workflow_templates", sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    op.add_column("master_workflow_templates", sa.Column("service_group_id", UUID(as_uuid=True), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("service_type_id", UUID(as_uuid=True), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("transitions", JSONB, nullable=False, server_default="[]"))
    op.add_column("master_workflow_templates", sa.Column("max_sla_hours", sa.Integer(), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("requires_technician_assignment", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("master_workflow_templates", sa.Column("requires_customer_confirmation", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("master_workflow_templates", sa.Column("requires_photo_proof", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("master_workflow_templates", sa.Column("requires_part_approval", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("master_workflow_templates", sa.Column("requires_estimate_approval", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("master_workflow_templates", sa.Column("requires_direct_payment_confirmation", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("master_workflow_templates", sa.Column("allows_reschedule", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("master_workflow_templates", sa.Column("allows_cancellation", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("master_workflow_templates", sa.Column("allows_dispute_after_completion", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("master_workflow_templates", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("master_workflow_templates", sa.Column("parent_template_id", UUID(as_uuid=True), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("master_workflow_templates", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("master_workflow_templates", sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_mwt_status", "master_workflow_templates", ["status"])
    op.create_index("ix_mwt_parent", "master_workflow_templates", ["parent_template_id"])
    op.create_index("ix_mwt_is_latest", "master_workflow_templates", ["is_latest"])

    # Backfill status from legacy is_active flag
    op.execute("""
        UPDATE master_workflow_templates
        SET status = CASE WHEN is_active THEN 'active' ELSE 'inactive' END
    """)

    # ── workflow_service_mappings ──────────────────────────────────────────────
    op.create_table(
        "workflow_service_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
        sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
        sa.Column("service_type_id", UUID(as_uuid=True), nullable=True),
        sa.Column("brand_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wsm_template", "workflow_service_mappings", ["template_id"])
    op.create_index("ix_wsm_category", "workflow_service_mappings", ["category_id"])
    op.create_index("ix_wsm_master_service", "workflow_service_mappings", ["master_service_id"])
    op.create_index("ix_wsm_service_type", "workflow_service_mappings", ["service_type_id"])


def downgrade() -> None:
    op.drop_index("ix_wsm_service_type", table_name="workflow_service_mappings")
    op.drop_index("ix_wsm_master_service", table_name="workflow_service_mappings")
    op.drop_index("ix_wsm_category", table_name="workflow_service_mappings")
    op.drop_index("ix_wsm_template", table_name="workflow_service_mappings")
    op.drop_table("workflow_service_mappings")

    op.drop_index("ix_mwt_is_latest", table_name="master_workflow_templates")
    op.drop_index("ix_mwt_parent", table_name="master_workflow_templates")
    op.drop_index("ix_mwt_status", table_name="master_workflow_templates")

    for col in [
        "created_by_user_id", "deprecated_at", "activated_at", "is_latest", "parent_template_id",
        "version_number", "allows_dispute_after_completion", "allows_cancellation", "allows_reschedule",
        "requires_direct_payment_confirmation", "requires_estimate_approval", "requires_part_approval",
        "requires_photo_proof", "requires_customer_confirmation", "requires_technician_assignment",
        "max_sla_hours", "transitions", "service_type_id", "service_group_id", "status",
    ]:
        op.drop_column("master_workflow_templates", col)
