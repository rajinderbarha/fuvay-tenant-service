"""Job Types — reconcile a real 3-vs-9 value divergence found live between
admin_catalog.VALID_JOB_TYPES (9 values: repair/installation/uninstallation/
inspection/maintenance/cleaning/consultation/service/custom) and
field_ops.JobType/TYPE_TRANSITION_OVERRIDES (only 3: repair/service/
consultation). Every job_type outside the 3 silently inherited the full
repair transition graph (mandatory assessment) with no way to configure
otherwise -- confirmed via get_allowed_transitions()'s fallback behavior.

This migration is purely additive:
  - New `job_types` table: admin-configurable, workflow-only (no monetary
    columns, per the platform's admin-never-sets-price rule), seeded with
    the 9 existing values and behavior flags matching field_ops's current
    real behavior for repair/service/consultation, and sensible new defaults
    for the previously-undifferentiated 6 (installation/uninstallation/
    inspection/maintenance/cleaning/custom).
  - Nullable `job_type_id` FK-by-convention column added to master_services,
    service_pricing_rules, tenant_services, jobs, bookings -- alongside the
    existing string `job_type` column (kept for compatibility, not dropped).
  - Backfill: job_type_id resolved by joining each table's existing
    `job_type` string to job_types.key.

Revision ID: 151
Revises: 150
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "151"
down_revision = "150"
branch_labels = None
depends_on = None

# key, label, requires_assessment, allows_quote, requires_checklist, display_order
SEED_JOB_TYPES = [
    ("repair",         "Repair",         True,  True,  False, 1),
    ("service",        "Service",        False, False, True,  2),
    ("consultation",   "Consultation",   True,  True,  False, 3),
    ("installation",   "Installation",   False, False, True,  4),
    ("uninstallation", "Uninstallation", False, False, False, 5),
    ("inspection",      "Inspection",     True,  True,  False, 6),
    ("maintenance",     "Maintenance",    False, False, True,  7),
    ("cleaning",        "Cleaning",       False, False, True,  8),
    ("custom",          "Custom",         True,  True,  True,  9),
]


def upgrade() -> None:
    op.create_table(
        "job_types",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(30), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requires_assessment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allows_quote", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_checklist", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("key", name="uq_job_types_key"),
    )
    op.create_index("ix_job_types_is_active", "job_types", ["is_active"])

    conn = op.get_bind()
    for key, label, req_assess, allows_quote, req_checklist, order in SEED_JOB_TYPES:
        conn.execute(sa.text("""
            INSERT INTO job_types (key, label, requires_assessment, allows_quote, requires_checklist, display_order)
            VALUES (:key, :label, :req_assess, :allows_quote, :req_checklist, :order)
        """), {"key": key, "label": label, "req_assess": req_assess,
               "allows_quote": allows_quote, "req_checklist": req_checklist, "order": order})

    for table in ("master_services", "service_pricing_rules", "tenant_services", "jobs", "bookings"):
        op.add_column(table, sa.Column("job_type_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
        op.execute(f"""
            UPDATE {table} t SET job_type_id = jt.id
            FROM job_types jt WHERE jt.key = t.job_type
        """)
        op.create_index(f"ix_{table}_job_type_id", table, ["job_type_id"])


def downgrade() -> None:
    for table in ("master_services", "service_pricing_rules", "tenant_services", "jobs", "bookings"):
        op.drop_index(f"ix_{table}_job_type_id", table_name=table)
        op.drop_column(table, "job_type_id")
    op.drop_index("ix_job_types_is_active", table_name="job_types")
    op.drop_table("job_types")
