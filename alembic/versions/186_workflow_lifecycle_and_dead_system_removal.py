"""WORKFLOW-CANONICALIZATION Phase 2-5: extend service_job_workflow with
publishing lifecycle + real capability columns, and drop the dead-workflow
tables confirmed unread outside their own self-contained CRUD surface.

ServiceJobWorkflow (service_job_workflow, migration 160/171) is the ONE
real, resolved-at-booking-time workflow authority. This migration:

  1. Adds a publishing lifecycle on top of the existing version chain
     (version_number/is_current/superseded_at from migration 171):
     status, supersedes_workflow_id (self-FK), effective_from/to,
     created_by/approved_by/published_by, change_reason, published_at.
  2. Adds three new capability columns, each backed by a real enforcement
     point wired in this same change:
       - allows_cancellation / allows_reschedule: enforced in
         home_service_assignment/service.py customer_cancel_booking /
         customer_reschedule_booking, and in
         execution/home_service_service.py cancel_job.
       - requires_direct_payment_record: added for schema completeness only
         -- NOT enforced yet (see code comment at the enforcement site in
         home_service_service.py). Renamed from the dead system's old
         wording "Requires direct payment confirmation".
  3. Drops workflow_templates / workflow_template_versions (system #3,
     raw-SQL, app/engines/workflows/) -- confirmed unread by any runtime
     execution path; the router/service files are deleted in this same
     change and the app.main mount removed.

     CORRECTION TO THE PHASE 1 AUDIT: MasterWorkflowTemplate and
     WorkflowServiceMapping (system #2, app/engines/admin_catalog/) were
     NOT dropped here. Implementation-time inspection found live,
     non-CRUD callers the audit missed --
     app/engines/admin_catalog/bulk_setup_service.py,
     recommendation_engine_service.py, and service_option_admin_router.py
     all query MasterWorkflowTemplate directly. Removing that table/model
     (or WorkflowServiceMapping, which the same CRUD surface owns) risked
     breaking those live features without a full audit of every call site
     under this session's time budget, so both tables and the
     /admin/workflow-templates CRUD routes/service methods that own them
     are LEFT IN PLACE. This is a real open follow-up, not a completed
     removal -- see the final report.

Revision ID: 186
Revises: 185
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "186"
down_revision = "185"
branch_labels = None
depends_on = None

WORKFLOW_STATUSES = (
    "draft", "validated", "impact_reviewed", "approved", "published", "superseded",
)


def upgrade() -> None:
    # ── 1. Publishing lifecycle columns on service_job_workflow ────────────
    op.add_column("service_job_workflow", sa.Column(
        "status", sa.String(length=20), nullable=False, server_default="published"))
    op.add_column("service_job_workflow", sa.Column(
        "supersedes_workflow_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "effective_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "effective_to", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "created_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "approved_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "published_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "change_reason", sa.Text(), nullable=True))
    op.add_column("service_job_workflow", sa.Column(
        "published_at", sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key(
        "fk_sjw_supersedes_workflow", "service_job_workflow",
        "service_job_workflow", ["supersedes_workflow_id"], ["id"],
    )
    op.create_index(
        "ix_sjw_status", "service_job_workflow", ["status"],
    )

    # Existing rows (all created prior to this migration) are already the
    # live, in-force version of their (master_service_id, job_type_id) pair
    # -- default them to 'published' with published_at = created_at so the
    # "new jobs snapshot only status='published', is_current=true" rule
    # holds immediately without orphaning any existing row.
    op.execute("UPDATE service_job_workflow SET published_at = created_at WHERE published_at IS NULL")

    # ── 2. New capability columns ───────────────────────────────────────────
    op.add_column("service_job_workflow", sa.Column(
        "allows_cancellation", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("service_job_workflow", sa.Column(
        "allows_reschedule", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("service_job_workflow", sa.Column(
        "requires_direct_payment_record", sa.Boolean(), nullable=False, server_default=sa.false()))

    # ── 3. Drop dead tables (system #3 only -- see module docstring) ───────
    op.execute("DROP TABLE IF EXISTS workflow_template_versions CASCADE")
    op.execute("DROP TABLE IF EXISTS workflow_templates CASCADE")


def downgrade() -> None:
    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("definition", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "workflow_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.drop_index("ix_sjw_status", table_name="service_job_workflow")
    op.drop_constraint("fk_sjw_supersedes_workflow", "service_job_workflow", type_="foreignkey")
    op.drop_column("service_job_workflow", "requires_direct_payment_record")
    op.drop_column("service_job_workflow", "allows_reschedule")
    op.drop_column("service_job_workflow", "allows_cancellation")
    op.drop_column("service_job_workflow", "published_at")
    op.drop_column("service_job_workflow", "change_reason")
    op.drop_column("service_job_workflow", "published_by")
    op.drop_column("service_job_workflow", "approved_by")
    op.drop_column("service_job_workflow", "created_by")
    op.drop_column("service_job_workflow", "effective_to")
    op.drop_column("service_job_workflow", "effective_from")
    op.drop_column("service_job_workflow", "supersedes_workflow_id")
    op.drop_column("service_job_workflow", "status")
