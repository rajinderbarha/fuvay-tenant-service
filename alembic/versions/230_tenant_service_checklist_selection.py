"""Tenant selection of checklist points per service.

Product rule: the ADMIN authors the checklist library
(checklist_catalog: template -> version -> section -> item, already complete
and super-admin guarded), and each TENANT then chooses which of those points
their technicians must actually complete for a given service -- at least 5.

Nothing existed for that second half. `job_type_checklist_mappings` links a
published template version to a job type PLATFORM-wide; there was no way for
one provider to run a different subset of points than another, so
`_instance_items` handed every technician the full authored list.

This table is that selection. Deliberately keyed on
(tenant_id, master_service_id, checklist_item_id):
  - master_service_id, not job_type, because the rule is stated per SERVICE;
  - checklist_item_id, so a selection survives sections being reordered;
  - a UNIQUE constraint, so double-submitting a selection cannot duplicate a
    point and inflate the count past the minimum check.

`is_active` rather than row deletion keeps a tenant's history auditable -- a
point they deselected is still visible to support when a customer asks why a
step was not performed on an older job.

Revision ID: 230
Revises: 229
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "230"
down_revision = "229"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant_service_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("master_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Which authored version the point was chosen from. A tenant's
        # selection must not silently follow a newly published version whose
        # items they never reviewed.
        sa.Column("checklist_template_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("selected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "master_service_id", "checklist_item_id",
                            name="uq_tsci_tenant_service_item"),
    )
    # The hot read is "this tenant's active points for this service", done on
    # every job checklist instantiation.
    op.create_index("ix_tsci_tenant_service", "tenant_service_checklist_items",
                    ["tenant_id", "master_service_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_tsci_tenant_service", table_name="tenant_service_checklist_items")
    op.drop_table("tenant_service_checklist_items")
