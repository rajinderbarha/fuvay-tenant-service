"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 -- Blueprint Version snapshot.

Phase 2A.1 resolved workflow via the LIVE (master_service_id, job_type_id)
pair on ServiceJobWorkflow -- correct for "which job type", but that row was
still mutable in place (job_type_blueprint_service.set_workflow did an
UPDATE, never an INSERT), so a job created today and an admin edit made
tomorrow would resolve the SAME row -- an in-progress job's approval
requirement could silently change underneath it.

This migration turns ServiceJobWorkflow into an append-only version chain
(mirrors the ServiceJobQuote versioning done in migration 167 for the exact
same reason): each edit supersedes the previous row instead of mutating it.
The row's own primary key IS the "Blueprint Version" reference -- no
separate blueprint-version table is introduced (spec section 10: "do not
duplicate the entire blueprint JSON unless that is the established
design" -- ServiceBlueprintVersion, migration 153, versions a DIFFERENT,
service-wide legacy field set and is the wrong granularity for a
per-job-type workflow row).

Adds the exact snapshot reference to the three records that carry Job Type
through the pipeline:
  home_service_booking_drafts.service_job_workflow_id
  service_bookings.service_job_workflow_id
  service_jobs.service_job_workflow_id
  (plus master_service_job_type_id alongside job_type_id on all three, for
   direct traversal without re-deriving the link)

Revision ID: 171
Revises: 170
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "171"
down_revision = "170"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ServiceJobWorkflow: append-only versioning ──────────────────────────
    op.add_column("service_job_workflow", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("service_job_workflow", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("service_job_workflow", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))

    # The old constraint assumed exactly one row per (master_service, job_type)
    # forever -- versioning means multiple historical rows now legitimately
    # share that pair. Replace with a partial unique index (one CURRENT row
    # per pair), same pattern as migration 167's one-current-quote-per-job.
    op.drop_constraint("uq_sjw_service_job_type", "service_job_workflow", type_="unique")
    op.create_index(
        "uq_sjw_one_current_per_pair", "service_job_workflow",
        ["master_service_id", "job_type_id"], unique=True,
        postgresql_where=sa.text("is_current"),
    )

    # ── Snapshot reference columns ──────────────────────────────────────────
    for table in ("home_service_booking_drafts", "service_bookings", "service_jobs"):
        op.add_column(table, sa.Column("master_service_job_type_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("service_job_workflow_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.add_column(table, sa.Column("selected_problem_id", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_index(f"ix_{table}_sjw_id", table, ["service_job_workflow_id"])

    conn = op.get_bind()

    # ── Backfill (spec section 19 priority order) ───────────────────────────
    # Priority 1/4: for rows that already have job_type_id (backfilled by
    # migration 168) AND an unambiguous, single ServiceJobWorkflow row for
    # that exact (offering_id, job_type_id) pair, resolve
    # master_service_job_type_id + service_job_workflow_id directly -- at
    # this point every ServiceJobWorkflow row is still version_number=1 /
    # is_current=true (just added above), so "the row for this pair" is
    # unambiguous by construction, not a guess among versions.
    total_report: dict[str, dict[str, int]] = {}
    for table in ("home_service_booking_drafts", "service_bookings", "service_jobs"):
        rows = conn.execute(sa.text(
            f"SELECT id, offering_id, job_type_id FROM {table} WHERE job_type_id IS NOT NULL"
        )).fetchall()
        resolved, unresolved_no_link, unresolved_no_workflow = 0, 0, 0
        for row_id, offering_id, job_type_id in rows:
            link = conn.execute(sa.text(
                "SELECT id FROM master_service_job_types WHERE master_service_id = :ms "
                "AND job_type_id = :jt AND is_active = true"
            ), {"ms": offering_id, "jt": job_type_id}).fetchone()
            if not link:
                unresolved_no_link += 1
                continue
            workflow = conn.execute(sa.text(
                "SELECT id FROM service_job_workflow WHERE master_service_id = :ms "
                "AND job_type_id = :jt AND is_current = true"
            ), {"ms": offering_id, "jt": job_type_id}).fetchone()
            if not workflow:
                unresolved_no_workflow += 1
                continue
            conn.execute(sa.text(
                f"UPDATE {table} SET master_service_job_type_id = :link, service_job_workflow_id = :wf "
                f"WHERE id = :id"
            ), {"link": link[0], "wf": workflow[0], "id": row_id})
            resolved += 1
        total_report[table] = {
            "total_with_job_type": len(rows), "resolved": resolved,
            "unresolved_no_active_link": unresolved_no_link,
            "unresolved_no_workflow": unresolved_no_workflow,
        }
        print(f"[171] {table}: {total_report[table]}")


def downgrade() -> None:
    for table in ("service_jobs", "service_bookings", "home_service_booking_drafts"):
        op.drop_index(f"ix_{table}_sjw_id", table_name=table)
        op.drop_column(table, "selected_problem_id")
        op.drop_column(table, "service_job_workflow_id")
        op.drop_column(table, "master_service_job_type_id")

    op.drop_index("uq_sjw_one_current_per_pair", table_name="service_job_workflow")
    op.create_unique_constraint("uq_sjw_service_job_type", "service_job_workflow", ["master_service_id", "job_type_id"])
    op.drop_column("service_job_workflow", "superseded_at")
    op.drop_column("service_job_workflow", "is_current")
    op.drop_column("service_job_workflow", "version_number")
