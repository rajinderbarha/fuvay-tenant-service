"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A -- quote version lineage.

Phase 1B found that a "revision" today is a same-row status flip
(mark_revised) with no true version lineage, and that create_quote has no
guard preventing multiple independent quote rows from existing for one job
simultaneously. That second gap is the real risk this migration closes: if
staff/admin call create_quote twice for the same job, nothing marks which
quote is "the current effective one" -- the work-start guard (Phase 2A)
needs a deterministic single answer.

Adds, on service_job_quotes (adapting the existing model rather than
building a second quote system, per the phase's own instruction):
  - version_number      (int, default 1)
  - is_current          (bool, default true)
  - supersedes_quote_id (nullable uuid, FK-less pointer to the prior version)
  - superseded_at       (nullable timestamptz)
  - approved_by         (nullable uuid -- actor who approved, denormalized
                          for quick lookup; the full actor trail already
                          lives in service_job_quote_events)

Backfill policy (dev DB may currently be empty from an earlier wipe --
zero rows is not proof this logic is unneeded): for each job_id, order
existing quotes by created_at. If more than one quote for a job is
CURRENTLY in "customer_approved" status simultaneously, that job is
ambiguous -- do NOT guess which is current; leave ALL of that job's quotes
is_current=false (fail-closed) and report it. Otherwise mark the latest
quote per job as current (version N), all earlier ones as superseded
(versions 1..N-1, chained via supersedes_quote_id).

A partial unique index enforces at most one is_current=true row per job_id
going forward, closing the "concurrent revisions create multiple current
versions" race at the database layer rather than only in application code.

Revision ID: 167
Revises: 166
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "167"
down_revision = "166"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_job_quotes", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("service_job_quotes", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("service_job_quotes", sa.Column("supersedes_quote_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_quotes", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_job_quotes", sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True))

    conn = op.get_bind()

    job_ids = [r[0] for r in conn.execute(sa.text(
        "SELECT DISTINCT job_id FROM service_job_quotes"
    )).fetchall()]

    ambiguous_jobs: list[str] = []
    for job_id in job_ids:
        rows = conn.execute(sa.text(
            "SELECT id, status, created_at FROM service_job_quotes "
            "WHERE job_id = :job_id ORDER BY created_at ASC"
        ), {"job_id": job_id}).fetchall()

        approved_count = sum(1 for r in rows if r[1] == "customer_approved")
        if approved_count > 1:
            # Fail closed -- do not guess which approved quote is authoritative.
            ambiguous_jobs.append(str(job_id))
            conn.execute(sa.text(
                "UPDATE service_job_quotes SET is_current = false WHERE job_id = :job_id"
            ), {"job_id": job_id})
            continue

        prior_id = None
        for idx, row in enumerate(rows, start=1):
            quote_id = row[0]
            is_last = idx == len(rows)
            conn.execute(sa.text(
                "UPDATE service_job_quotes SET version_number = :v, is_current = :cur, "
                "supersedes_quote_id = :prior, superseded_at = CASE WHEN :cur THEN NULL ELSE updated_at END, "
                "approved_by = CASE WHEN status = 'customer_approved' THEN customer_id ELSE NULL END "
                "WHERE id = :id"
            ), {"v": idx, "cur": is_last, "prior": prior_id, "id": quote_id})
            prior_id = quote_id

    if ambiguous_jobs:
        print(f"[167] AMBIGUOUS quote-current jobs (multiple simultaneously-approved quotes, "
              f"left with NO current quote -- requires manual review): {ambiguous_jobs}")
    print(f"[167] backfilled version lineage for {len(job_ids)} job(s) with existing quotes")

    op.create_index(
        "uq_sjq_one_current_per_job",
        "service_job_quotes",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )


def downgrade() -> None:
    op.drop_index("uq_sjq_one_current_per_job", table_name="service_job_quotes")
    op.drop_column("service_job_quotes", "approved_by")
    op.drop_column("service_job_quotes", "superseded_at")
    op.drop_column("service_job_quotes", "supersedes_quote_id")
    op.drop_column("service_job_quotes", "is_current")
    op.drop_column("service_job_quotes", "version_number")
