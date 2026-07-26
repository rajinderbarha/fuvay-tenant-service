"""Job-Type Blueprint ownership correction.

USER REQ: the "New Service Category" and "New Master Service" admin forms
expose Brand/Type/Issue/Schedule/Address/Pricing at the wrong catalog level.
Audit confirmed:
  - ServiceCategory (docstring: "Home Services, Coaching Center, Real
    Estate") is the Business Vertical, but wrongly owns requires_location/
    requires_schedule/requires_brand/requires_service_option/
    requires_issue_type/pricing_supported.
  - MasterService wrongly owns job_type (a SCALAR field -- meaning "AC
    Repair" and "AC Installation" are today two separate MasterService
    rows, not one "Air Conditioner" MasterService with two Job-Type
    children), pricing_model, base_price, min_price, max_price, visit_fee,
    is_brand_required, is_type_required, requires_issue_type,
    requires_checklist, requires_schedule, requires_address.

This migration adds the two tables that make Job Type a genuine CHILD
RECORD of a Master Service (matching the canonical hierarchy: Business
Vertical -> Service Group -> Master Service -> Job Type -> Job-Type
Blueprint) instead of a field that forks one service into many rows:

  - master_service_job_types: explicit (master_service, job_type) child
    records, replacing the scalar MasterService.job_type going forward.
  - service_job_workflow: per-(master_service, job_type) ownership of
    inspection/quote-approval/checklist/schedule/address/technician/
    service-area/availability requirements + permitted pricing BEHAVIOR
    (fixed/range/inspection_required/custom_quote -- never an amount).
    Brand/Type dimension usage is NOT duplicated here -- it already has a
    correct home in the existing generic dimension engine
    (service_job_dimensions, migration 154), reused as-is per the
    instruction not to build a second Brand/Type system.

Reconciliation (unambiguous only -- every legacy MasterService row has
exactly ONE job_type value today, so backfilling one child record per row
is a direct, non-guessing 1:1 mapping, not an inference):
  1. One master_service_job_types row per existing, non-deleted
     MasterService whose job_type string resolves to a real job_types.key
     (migration 151). Rows whose job_type does not resolve are reported,
     not guessed.
  2. One service_job_workflow row per that same pairing, copying
     requires_checklist/requires_schedule/requires_address directly (this
     is data preservation, not re-interpretation -- the legacy row only
     ever meant one job type, so its flags unambiguously describe that one
     job type). pricing_behavior derived from the fixed pricing_model enum
     mapping. inspection_required = (pricing_model == 'post_assessment').
     technician_required/service_area_required/quote_approval_required/
     availability_required have NO legacy equivalent -- defaulted False,
     not guessed, and left for admin review.
  3. Brand/Type dimension usage backfilled into service_job_dimensions
     (the EXISTING generic dimension engine) from is_type_required/
     is_brand_required, ON CONFLICT DO NOTHING so it never overwrites
     dimension config an admin has already set via the Catalog Workspace.

Purely additive. No legacy column is dropped or renamed. Legacy fields
remain readable (existing rows, existing reports) but stop being
authoritative -- create/update paths for MasterService and ServiceCategory
are corrected in the same change (service.py) to stop accepting them, and
the customer-facing flow-config resolver now prefers this canonical data
when present, falling back to legacy only when no blueprint exists yet.

Revision ID: 160
Revises: 159
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "160"
down_revision = "159"
branch_labels = None
depends_on = None

_PRICING_BEHAVIOR_MAP = {
    "fixed": "fixed",
    "range": "range",
    "post_assessment": "inspection_required",
    "hourly": "fixed",
}


def upgrade() -> None:
    op.create_table(
        "master_service_job_types",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("master_service_id", "job_type_id", name="uq_msjt_service_job_type"),
    )
    op.create_index("ix_msjt_master_service", "master_service_job_types", ["master_service_id"])
    op.create_index("ix_msjt_job_type", "master_service_job_types", ["job_type_id"])

    op.create_table(
        "service_job_workflow",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("master_service_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inspection_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quote_approval_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("checklist_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("schedule_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("address_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("technician_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("service_area_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("availability_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # fixed / range / inspection_required / custom_quote -- BEHAVIOR only,
        # never an amount. Structural allowlist enforced in the service layer.
        sa.Column("pricing_behavior", sa.String(30), nullable=False, server_default="fixed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("master_service_id", "job_type_id", name="uq_sjw_service_job_type"),
    )
    op.create_index("ix_sjw_master_service", "service_job_workflow", ["master_service_id"])
    op.create_index("ix_sjw_job_type", "service_job_workflow", ["job_type_id"])

    # Relax MasterService.job_type / pricing_model to nullable -- new,
    # job-type-agnostic Master Services no longer carry a single job_type or
    # pricing_model at creation time (job types + their pricing behavior are
    # now child records). Existing rows keep their historical values.
    op.alter_column("master_services", "job_type", existing_type=sa.String(20), nullable=True)
    op.alter_column("master_services", "pricing_model", existing_type=sa.String(30), nullable=True)

    # ── Reconciliation (unambiguous 1:1 backfill only) ──────────────────────
    conn = op.get_bind()

    migrated = conn.execute(sa.text("""
        INSERT INTO master_service_job_types (master_service_id, job_type_id)
        SELECT ms.id, jt.id
        FROM master_services ms
        JOIN job_types jt ON jt.key = ms.job_type
        WHERE ms.deleted_at IS NULL
        ON CONFLICT (master_service_id, job_type_id) DO NOTHING
        RETURNING id
    """)).rowcount

    unresolved = conn.execute(sa.text("""
        SELECT count(*) FROM master_services ms
        WHERE ms.deleted_at IS NULL
          AND ms.job_type IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM job_types jt WHERE jt.key = ms.job_type)
    """)).scalar() or 0

    workflow_migrated = conn.execute(sa.text(f"""
        INSERT INTO service_job_workflow
            (master_service_id, job_type_id, checklist_required, schedule_required,
             address_required, inspection_required, pricing_behavior)
        SELECT
            ms.id, jt.id, ms.requires_checklist, ms.requires_schedule, ms.requires_address,
            (ms.pricing_model = 'post_assessment'),
            CASE ms.pricing_model
                WHEN 'fixed' THEN 'fixed'
                WHEN 'range' THEN 'range'
                WHEN 'post_assessment' THEN 'inspection_required'
                WHEN 'hourly' THEN 'fixed'
                ELSE 'fixed'
            END
        FROM master_services ms
        JOIN job_types jt ON jt.key = ms.job_type
        WHERE ms.deleted_at IS NULL
        ON CONFLICT (master_service_id, job_type_id) DO NOTHING
        RETURNING id
    """)).rowcount

    # Brand/Type dimension usage -- reuse the EXISTING generic dimension
    # engine (service_job_dimensions, migration 154) rather than duplicating
    # a Brand/Type system. Only inserted where no config already exists for
    # that (service, job_type, dimension) so an admin's Catalog Workspace
    # edits are never silently overwritten.
    dims_migrated = conn.execute(sa.text("""
        INSERT INTO service_job_dimensions
            (master_service_id, job_type_id, dimension_id, enabled, required,
             ask_customer, show_during_tenant_setup, use_for_matching, affects_price,
             allow_tenant_override, allow_all_coverage, allow_selected_coverage,
             allow_exclusion_coverage)
        SELECT ms.id, jt.id, cd.id, ms.is_type_required, ms.is_type_required,
               true, true, true, false, true, true, true, true
        FROM master_services ms
        JOIN job_types jt ON jt.key = ms.job_type
        JOIN catalog_dimensions cd ON cd.key = 'type'
        WHERE ms.deleted_at IS NULL
        ON CONFLICT (master_service_id, job_type_id, dimension_id) DO NOTHING
        RETURNING id
    """)).rowcount + conn.execute(sa.text("""
        INSERT INTO service_job_dimensions
            (master_service_id, job_type_id, dimension_id, enabled, required,
             ask_customer, show_during_tenant_setup, use_for_matching, affects_price,
             allow_tenant_override, allow_all_coverage, allow_selected_coverage,
             allow_exclusion_coverage)
        SELECT ms.id, jt.id, cd.id, ms.is_brand_required, ms.is_brand_required,
               true, true, false, false, true, true, true, true
        FROM master_services ms
        JOIN job_types jt ON jt.key = ms.job_type
        JOIN catalog_dimensions cd ON cd.key = 'brand'
        WHERE ms.deleted_at IS NULL
        ON CONFLICT (master_service_id, job_type_id, dimension_id) DO NOTHING
        RETURNING id
    """)).rowcount

    print(f"[160 reconciliation] master_service_job_types migrated={migrated}, "
          f"unresolved_job_type={unresolved} (requires manual review), "
          f"service_job_workflow migrated={workflow_migrated}, "
          f"service_job_dimensions (brand+type) migrated={dims_migrated}")


def downgrade() -> None:
    op.alter_column("master_services", "pricing_model", existing_type=sa.String(30), nullable=False)
    op.alter_column("master_services", "job_type", existing_type=sa.String(20), nullable=False)

    op.drop_index("ix_sjw_job_type", table_name="service_job_workflow")
    op.drop_index("ix_sjw_master_service", table_name="service_job_workflow")
    op.drop_table("service_job_workflow")

    op.drop_index("ix_msjt_job_type", table_name="master_service_job_types")
    op.drop_index("ix_msjt_master_service", table_name="master_service_job_types")
    op.drop_table("master_service_job_types")
