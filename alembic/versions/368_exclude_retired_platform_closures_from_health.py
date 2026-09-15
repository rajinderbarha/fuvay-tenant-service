"""Rescore provider health without retired platform job closures.

Revision ID: 368
Revises: 367
"""
from alembic import op


revision = "368"
down_revision = "367"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Health metrics no longer count jobs the retired assignment-timeout sweep
    # cancelled itself ("Closed because no alternative provider..."). Stored
    # scores still include them until recalculated, and on staging they hold
    # two providers in the non-bookable band. Queue one normal batched health
    # sweep so the background worker rescores right after deployment instead of
    # at its next six-hourly refresh. Never duplicate a queued/running sweep.
    op.execute("""
        INSERT INTO trust_quality_recalculation_jobs
            (id, job_type, scope_type, status, total_count, processed_count,
             failed_count, triggered_by, created_at, updated_at)
        SELECT gen_random_uuid(), 'health', 'all', 'queued', 0, 0, 0,
               'migration_368', now(), now()
         WHERE NOT EXISTS (
             SELECT 1 FROM trust_quality_recalculation_jobs
              WHERE status IN ('queued', 'running', 'cancelling')
         )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM trust_quality_recalculation_jobs
         WHERE triggered_by = 'migration_368' AND status = 'queued'
    """)
