"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 -- exact Job-Type workflow
resolution.

Phase 2A's blueprint resolver treated "Master Service -> exactly one active
MasterServiceJobType" as the identity key. That is architecturally wrong:
one Master Service (e.g. "Air Conditioner") legitimately owns several Job
Types (Repair, Installation, Uninstallation, General Service), each with its
own ServiceJobWorkflow.quote_approval_required. The old resolver would treat
any Master Service with 2+ linked job types as "ambiguous" and fail closed
for EVERY job under it, including ones whose workflow does not require
approval at all.

This migration adds the exact Job Type reference alongside the existing
offering_id (= MasterService.id) on the three records that carry it through
the canonical pipeline: the booking draft (where it is first selected), and
ServiceBooking/ServiceJob (where it must be copied verbatim, never
re-derived, never overridden by a confirmation payload).

Backfill policy (spec-mandated, no guessing):
  - A pre-existing service_booking/service_job has NO job-type field or
    structured metadata anywhere in this codebase to backfill FROM (traced:
    HomeServiceBookingDraft, ServiceBooking, ServiceJob never carried one
    before this migration). So the ONLY legitimate backfill evidence is:
    "this Master Service has EXACTLY ONE active MasterServiceJobType" --
    in that case there is only one possible answer, not a guess among many.
  - If a Master Service has 0 or 2+ active linked Job Types, every
    booking/job under it is left NULL (unresolved) and counted as requiring
    manual reconciliation. Never the first, never the one with
    quote_approval_required=true, never inferred from display_order.
  - Invalid states (job type inactive, mapping missing, master_service_id
    with no catalog row at all) are counted separately, not silently
    treated as "ambiguous".

The development database may have zero rows -- the counting/reporting logic
below still executes and is exercised by tests with populated fixtures
(see tests/test_module_l5_53_exact_job_type_resolution.py).

Revision ID: 168
Revises: 167
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "168"
down_revision = "167"
branch_labels = None
depends_on = None


def _add_job_type_column(table: str) -> None:
    op.add_column(table, sa.Column("job_type_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(f"ix_{table}_job_type_id", table, ["job_type_id"])


def _backfill_unambiguous(conn, table: str, id_col: str = "id") -> dict:
    """Backfill job_type_id for `table` rows whose offering_id has EXACTLY
    ONE active MasterServiceJobType -- the only case where a single answer
    exists rather than a choice among several. Returns per-table totals."""
    offering_ids = [r[0] for r in conn.execute(sa.text(
        f"SELECT DISTINCT offering_id FROM {table} WHERE job_type_id IS NULL"
    )).fetchall()]

    totals = {"total": 0, "backfilled": 0, "ambiguous": 0, "invalid": 0}
    for offering_id in offering_ids:
        row_count = conn.execute(sa.text(
            f"SELECT count(*) FROM {table} WHERE offering_id = :oid AND job_type_id IS NULL"
        ), {"oid": offering_id}).scalar()
        totals["total"] += row_count

        links = conn.execute(sa.text(
            "SELECT job_type_id FROM master_service_job_types "
            "WHERE master_service_id = :oid AND is_active = true"
        ), {"oid": offering_id}).fetchall()

        if not conn.execute(sa.text(
            "SELECT 1 FROM master_services WHERE id = :oid AND deleted_at IS NULL"
        ), {"oid": offering_id}).fetchone():
            totals["invalid"] += row_count
            continue

        if len(links) == 1:
            conn.execute(sa.text(
                f"UPDATE {table} SET job_type_id = :jt WHERE offering_id = :oid AND job_type_id IS NULL"
            ), {"jt": links[0][0], "oid": offering_id})
            totals["backfilled"] += row_count
        elif len(links) == 0:
            totals["invalid"] += row_count  # no published job type at all for this service
        else:
            totals["ambiguous"] += row_count  # 2+ job types -- genuinely a choice, not inferred

    return totals


def upgrade() -> None:
    _add_job_type_column("home_service_booking_drafts")
    _add_job_type_column("service_bookings")
    _add_job_type_column("service_jobs")

    conn = op.get_bind()
    for table in ("home_service_booking_drafts", "service_bookings", "service_jobs"):
        totals = _backfill_unambiguous(conn, table)
        print(f"[168] {table}: total_null={totals['total']} "
              f"backfilled_unambiguous={totals['backfilled']} "
              f"ambiguous_left_unresolved={totals['ambiguous']} "
              f"invalid_left_unresolved={totals['invalid']}")


def downgrade() -> None:
    for table in ("service_jobs", "service_bookings", "home_service_booking_drafts"):
        op.drop_index(f"ix_{table}_job_type_id", table_name=table)
        op.drop_column(table, "job_type_id")
