"""Recreate the two Workflow Template tables, which were dropped out-of-band.

`master_workflow_templates` is created by migration 055 and extended by 086;
`workflow_service_mappings` is created by 086. Both migrations ran long ago
(alembic_version is well past them) and their sibling tables from the same
revisions — master_issue_types, master_service_options, master_data_audit_log —
are all still present. Only these two are gone, so they were dropped outside
alembic rather than lost to a failed migration.

The consequence was total: every one of the ~30 /v1/admin/workflow-templates
endpoints returned 500 (UndefinedTableError), so the entire Workflow Templates
admin page — list, summary, create, seed, builder, mapping, runtime preview,
audit — was dead on arrival.

Schema here is the union of 055 + 086 as the ORM model declares it today
(app/engines/admin_catalog/models.py), which is what the code actually reads and
writes. Guarded with checkfirst/IF NOT EXISTS so it is a no-op on any
environment where the tables survived.

Revision ID: 273
Revises: 272
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "273"
down_revision = "272"
branch_labels = None
depends_on = None

_TEMPLATES = "master_workflow_templates"
_MAPPINGS = "workflow_service_mappings"


def _has(table: str) -> bool:
    bind = op.get_bind()
    return bind.execute(
        sa.text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}
    ).scalar() is not None


def upgrade() -> None:
    if not _has(_TEMPLATES):
        op.create_table(
            _TEMPLATES,
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            # Scope
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
            sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
            sa.Column("service_type_id", UUID(as_uuid=True), nullable=True),
            # Identity
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("workflow_type", sa.String(30), nullable=False),
            # Definition — steps and transitions are JSONB on the row itself,
            # not child tables.
            sa.Column("steps", JSONB, nullable=False, server_default="[]"),
            sa.Column("transitions", JSONB, nullable=False, server_default="[]"),
            # Runtime settings
            sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("max_sla_hours", sa.Integer(), nullable=True),
            sa.Column("requires_technician_assignment", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("requires_customer_confirmation", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("requires_photo_proof", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("requires_part_approval", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("requires_estimate_approval", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("requires_direct_payment_confirmation", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("allows_reschedule", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("allows_cancellation", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("allows_dispute_after_completion", sa.Boolean(), nullable=False, server_default="true"),
            # Lifecycle + versioning
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("parent_template_id", UUID(as_uuid=True), nullable=True),
            sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True,
                      server_default=sa.text("now()")),
            sa.UniqueConstraint("slug", name="uq_mwt_slug"),
        )
        op.create_index("ix_mwt_category", _TEMPLATES, ["category_id"])
        op.create_index("ix_mwt_master_service", _TEMPLATES, ["master_service_id"])
        op.create_index("ix_mwt_workflow_type", _TEMPLATES, ["workflow_type"])
        op.create_index("ix_mwt_active", _TEMPLATES, ["is_active"])
        # Every list query filters is_latest and orders by display_order, name —
        # the admin list's only access path, so it gets its own index rather
        # than a sort of the whole table.
        op.create_index("ix_mwt_latest_order", _TEMPLATES,
                        ["is_latest", "display_order", "name"])
        op.create_index("ix_mwt_status", _TEMPLATES, ["status"])

    if not _has(_MAPPINGS):
        op.create_table(
            _MAPPINGS,
            sa.Column("id", UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("template_id", UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", UUID(as_uuid=True), nullable=False),
            sa.Column("service_group_id", UUID(as_uuid=True), nullable=True),
            sa.Column("master_service_id", UUID(as_uuid=True), nullable=True),
            sa.Column("service_type_id", UUID(as_uuid=True), nullable=True),
            sa.Column("brand_id", UUID(as_uuid=True), nullable=True),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True,
                      server_default=sa.text("now()")),
        )
        op.create_index("ix_wsm_template", _MAPPINGS, ["template_id"])
        op.create_index("ix_wsm_category", _MAPPINGS, ["category_id"])
        op.create_index("ix_wsm_master_service", _MAPPINGS, ["master_service_id"])
        op.create_index("ix_wsm_service_type", _MAPPINGS, ["service_type_id"])


def downgrade() -> None:
    # Deliberately not dropping: this migration only ever *restores* tables that
    # earlier migrations already own, so dropping them here would undo 055/086.
    pass
