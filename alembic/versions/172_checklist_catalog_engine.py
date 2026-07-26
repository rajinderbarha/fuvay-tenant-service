"""Checklist Catalog Engine — canonical, job-type-mapped checklist tables.

Consolidates the three previously disconnected checklist systems
(sj_checklist_templates/quote_checklist, service_checklist_templates/
field_ops, master_checklist_items/admin_catalog) onto one reusable-
template + published-version + exact-Job-Type-mapping model. None of the
legacy tables are dropped here -- they remain readable until all callers
are migrated and proven (see reconciliation report emitted below).

New tables:
  checklist_templates, checklist_template_versions, checklist_sections,
  checklist_items, job_type_checklist_mappings, job_checklist_instances,
  job_checklist_responses.

Reconciliation: legacy "global"-scoped templates cannot be safely mapped to
an exact job type by inference (the task explicitly forbids guessing), so
this migration does NOT attempt to auto-create job_type_checklist_mappings
rows from legacy data. It reports counts of legacy templates per system so
an admin can review and remap them explicitly via the new Checklist Library
UI. Existing completed legacy checklist responses (service_job_checklists /
service_job_checklist_items / job_checklist_items) are left entirely
untouched for historical-record preservation.

Revision ID: 172
Revises: 171
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "172"
down_revision = "171"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("owner_scope", sa.String(20), nullable=False, server_default="PLATFORM"),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_ct_code"),
    )
    op.create_index("ix_ct_status", "checklist_templates", ["status"])
    op.create_index("ix_ct_owner_scope", "checklist_templates", ["owner_scope"])

    op.create_table(
        "checklist_template_versions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_template_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("published_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("checklist_template_id", "version_number", name="uq_ctv_template_version"),
        sa.ForeignKeyConstraint(["checklist_template_id"], ["checklist_templates.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ctv_template", "checklist_template_versions", ["checklist_template_id"])
    op.create_index("ix_ctv_status", "checklist_template_versions", ["status"])

    op.create_table(
        "checklist_sections",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_template_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checklist_template_version_id"], ["checklist_template_versions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_csec_version", "checklist_sections", ["checklist_template_version_id"])

    op.create_table(
        "checklist_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_section_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(20), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evidence_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_evidence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allowed_file_types", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("measurement_unit", sa.String(30), nullable=True),
        sa.Column("select_options", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("validation_rules", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("condition_rules", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("failure_behavior", sa.String(30), nullable=True),
        sa.Column("customer_visible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["checklist_section_id"], ["checklist_sections.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ci_section", "checklist_items", ["checklist_section_id"])

    op.create_table(
        "job_type_checklist_mappings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_job_workflow_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist_template_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("usage", sa.String(20), nullable=False, server_default="OPTIONAL"),
        sa.Column("actor", sa.String(20), nullable=False, server_default="TECHNICIAN"),
        sa.Column("completion_gate", sa.String(50), nullable=False, server_default="NONE"),
        sa.Column("condition_rules", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["master_service_job_type_id"], ["master_service_job_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_job_workflow_id"], ["service_job_workflow.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["checklist_template_version_id"], ["checklist_template_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "master_service_job_type_id", "checklist_template_version_id", "phase",
            name="uq_jtcm_job_type_version_phase",
        ),
    )
    op.create_index("ix_jtcm_job_type", "job_type_checklist_mappings", ["master_service_job_type_id"])
    op.create_index("ix_jtcm_version", "job_type_checklist_mappings", ["checklist_template_version_id"])
    op.create_index("ix_jtcm_status", "job_type_checklist_mappings", ["status"])

    op.create_table(
        "job_checklist_instances",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_template_version_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phase", sa.String(30), nullable=False),
        sa.Column("assigned_actor", sa.String(20), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="NOT_STARTED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waived_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("snapshot_metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["mapping_id"], ["job_type_checklist_mappings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["checklist_template_version_id"], ["checklist_template_versions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("job_id", "mapping_id", name="uq_jci_job_mapping"),
    )
    op.create_index("ix_jci_job", "job_checklist_instances", ["job_id"])
    op.create_index("ix_jci_mapping", "job_checklist_instances", ["mapping_id"])
    op.create_index("ix_jci_tenant", "job_checklist_instances", ["tenant_id"])

    op.create_table(
        "job_checklist_responses",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_checklist_instance_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_item_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_value", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("actor_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("validation_result", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_checklist_instance_id"], ["job_checklist_instances.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_checklist_instance_id", "checklist_item_id", name="uq_jcr_instance_item"),
    )
    op.create_index("ix_jcr_instance", "job_checklist_responses", ["job_checklist_instance_id"])
    op.create_index("ix_jcr_item", "job_checklist_responses", ["checklist_item_id"])

    # ── Reconciliation report only (no guessed mappings created) ───────────
    # Defensive: some deployments may not have every legacy checklist
    # engine's migration applied (e.g. field_ops' service_checklist_templates
    # is a separate, independently-versioned migration lineage) -- a missing
    # legacy table must not abort this migration.
    conn = op.get_bind()

    def _count_if_exists(table_name: str) -> int | str:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ), {"t": table_name}).scalar()
        if not exists:
            return "table not present"
        return conn.execute(sa.text(f"SELECT count(*) FROM {table_name}")).scalar() or 0

    legacy_a = _count_if_exists("sj_checklist_templates")
    legacy_b = _count_if_exists("service_checklist_templates")
    legacy_c = _count_if_exists("master_checklist_items")
    print(
        f"[172 reconciliation] legacy templates found -- "
        f"quote_checklist(sj_checklist_templates)={legacy_a}, "
        f"field_ops(service_checklist_templates)={legacy_b}, "
        f"admin_catalog(master_checklist_items)={legacy_c}. "
        f"None auto-mapped to a Job Type (would require guessing); "
        f"review and remap explicitly via the Checklist Library UI."
    )


def downgrade() -> None:
    op.drop_index("ix_jcr_item", table_name="job_checklist_responses")
    op.drop_index("ix_jcr_instance", table_name="job_checklist_responses")
    op.drop_table("job_checklist_responses")

    op.drop_index("ix_jci_tenant", table_name="job_checklist_instances")
    op.drop_index("ix_jci_mapping", table_name="job_checklist_instances")
    op.drop_index("ix_jci_job", table_name="job_checklist_instances")
    op.drop_table("job_checklist_instances")

    op.drop_index("ix_jtcm_status", table_name="job_type_checklist_mappings")
    op.drop_index("ix_jtcm_version", table_name="job_type_checklist_mappings")
    op.drop_index("ix_jtcm_job_type", table_name="job_type_checklist_mappings")
    op.drop_table("job_type_checklist_mappings")

    op.drop_index("ix_ci_section", table_name="checklist_items")
    op.drop_table("checklist_items")

    op.drop_index("ix_csec_version", table_name="checklist_sections")
    op.drop_table("checklist_sections")

    op.drop_index("ix_ctv_status", table_name="checklist_template_versions")
    op.drop_index("ix_ctv_template", table_name="checklist_template_versions")
    op.drop_table("checklist_template_versions")

    op.drop_index("ix_ct_owner_scope", table_name="checklist_templates")
    op.drop_index("ix_ct_status", table_name="checklist_templates")
    op.drop_table("checklist_templates")
