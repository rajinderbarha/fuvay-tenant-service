"""HOME-SERVICES-CATALOG: Service Options and Add-ons ownership correction.

Closes the architecture gap found in the "New Service Option" admin form
audit: MasterServiceOption/ServiceOptionMapping were FK'd only to
MasterService (never to a Job Type), and default_price/is_customer_selectable
were treated as global template properties writable straight from the admin
API -- but the same option (e.g. "Wall Stand") legitimately behaves
differently under Installation than under Repair, and this platform's
non-negotiable rule is admin-never-sets-price (already true for
JobTypeDefinition/ServiceBlueprintVersion, violated here).

This mirrors the identical nullable job_type_id pattern already used for
service_issue_mappings (migration 156) and catalog_questions (migration 155):
NULL means "applies to all job types for this service" (backward compatible
with every existing row), a concrete FK scopes the option to one job type.

Purely additive -- no column is dropped, no admin monetary value is copied
into any tenant row, no mapping is auto-created for every job type. Legacy
`default_price`/`min_price`/`max_price` on master_service_options are left in
place (deprecated, no longer written by the admin API) rather than dropped,
per the "do not drop legacy columns blindly" rule; the audit report below
tells the operator how many rows actually carry a non-zero legacy price so
ambiguous cases can be reviewed by hand instead of guessed.

Revision ID: 169
Revises: 168
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "169"
down_revision = "168"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Service Option Mapping: exact Job-Type scoping + mapping-level
    # selectability/usage, replacing the global template's authority ──────────
    op.add_column(
        "service_option_mappings",
        sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_som_job_type", "service_option_mappings", ["job_type_id"])

    # usage: DISABLED | OPTIONAL | REQUIRED -- supersedes the boolean
    # is_required for a proper 3-state, but is_required is kept for backward
    # compatibility with existing readers; usage is the new authoritative
    # field going forward (kept in sync by the service layer).
    op.add_column(
        "service_option_mappings",
        sa.Column("usage", sa.String(20), nullable=False, server_default="OPTIONAL"),
    )
    # Per-actor selectability, scoped to this exact Job-Type mapping -- the
    # same global option template may be customer_selectable under
    # Installation but technician-only under Repair.
    op.add_column(
        "service_option_mappings",
        sa.Column("customer_selectable", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("tenant_selectable", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("technician_selectable", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("available_before_booking", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("available_after_inspection", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("affects_estimate", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("requires_customer_approval", sa.Boolean, nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("quantity_supported", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("minimum_quantity", sa.Integer, nullable=True),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("maximum_quantity", sa.Integer, nullable=True),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("measurement_unit", sa.String(30), nullable=True),
    )
    op.add_column(
        "service_option_mappings",
        sa.Column("blueprint_version", sa.Integer, nullable=True),
    )

    # ── Tenant Service Option: monetary ownership lives here, keyed to the
    # exact job-type mapping (not just master_service_id+service_option_id,
    # which would collapse Installation and Repair pricing together) ────────
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("service_option_mapping_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tsso_mapping", "tenant_supported_service_options", ["service_option_mapping_id"])
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("pricing_model", sa.String(20), nullable=True),  # FIXED | PER_UNIT | RANGE
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("fixed_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("minimum_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("maximum_price", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_supported_service_options",
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Booking option selection snapshot -- preserves what was actually
    # selected/approved at the time, so a later tenant price change never
    # retroactively changes a historical booking/quote total ────────────────
    op.create_table(
        "booking_option_selections",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("booking_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_option_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_option_mapping_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("option_label", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("measurement_unit", sa.String(30), nullable=True),
        sa.Column("tenant_unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("calculated_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("selection_source", sa.String(30), nullable=False),  # CUSTOMER | TENANT | TECHNICIAN | SYSTEM
        sa.Column("selected_by_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("quote_version", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_bos_booking", "booking_option_selections", ["booking_id"])
    op.create_index("ix_bos_tenant", "booking_option_selections", ["tenant_id"])

    # ── Reconciliation / audit report -- read-only, no data mutated ─────────
    conn = op.get_bind()
    total_options = conn.execute(sa.text("SELECT count(*) FROM master_service_options")).scalar()
    priced_options = conn.execute(sa.text(
        "SELECT count(*) FROM master_service_options WHERE default_price <> 0 "
        "OR min_price IS NOT NULL OR max_price IS NOT NULL"
    )).scalar()
    total_mappings = conn.execute(sa.text("SELECT count(*) FROM service_option_mappings WHERE deleted_at IS NULL")).scalar()
    tenant_priced = conn.execute(sa.text(
        "SELECT count(*) FROM tenant_supported_service_options WHERE deleted_at IS NULL"
    )).scalar()
    print(f"[169] master_service_options total={total_options} "
          f"with_legacy_admin_price={priced_options} (deprecated column, not dropped, "
          f"no longer writable via admin API — manual review required if used elsewhere)")
    print(f"[169] service_option_mappings total_active={total_mappings} "
          f"all_master-service-only_pending_job_type_assignment (job_type_id NULL = "
          f"'applies to all job types', not auto-migrated — admin must explicitly scope "
          f"each mapping to a Job Type going forward)")
    print(f"[169] tenant_supported_service_options total={tenant_priced} "
          f"(0 with tenant pricing set — pricing_model/fixed_price/unit_price all NULL "
          f"until a tenant explicitly configures them; no admin default_price was copied)")


def downgrade() -> None:
    op.drop_index("ix_bos_tenant", table_name="booking_option_selections")
    op.drop_index("ix_bos_booking", table_name="booking_option_selections")
    op.drop_table("booking_option_selections")

    for col in ("effective_to", "effective_from", "currency", "maximum_price", "minimum_price",
                "unit_price", "fixed_price", "pricing_model"):
        op.drop_column("tenant_supported_service_options", col)
    op.drop_index("ix_tsso_mapping", table_name="tenant_supported_service_options")
    op.drop_column("tenant_supported_service_options", "service_option_mapping_id")

    for col in ("blueprint_version", "measurement_unit", "maximum_quantity", "minimum_quantity",
                "quantity_supported", "requires_customer_approval", "affects_estimate",
                "available_after_inspection", "available_before_booking", "technician_selectable",
                "tenant_selectable", "customer_selectable", "usage"):
        op.drop_column("service_option_mappings", col)
    op.drop_index("ix_som_job_type", table_name="service_option_mappings")
    op.drop_column("service_option_mappings", "job_type_id")
