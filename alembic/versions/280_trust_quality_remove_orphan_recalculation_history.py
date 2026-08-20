"""Remove orphan Trust & Quality recalculation history.

Revision ID: 280
Revises: 279
"""

from alembic import op


revision = "280"
down_revision = "279"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy manual jobs without an actor cannot be attributed or audited and
    # provide no useful operational history. Remove their paired audit rows
    # before deleting the jobs themselves.
    op.execute(
        """
        DELETE FROM trust_quality_audit_logs audit
        USING trust_quality_recalculation_jobs job
        WHERE audit.target_type = 'recalculation_job'
          AND audit.target_id = job.id
          AND job.triggered_by_user_id IS NULL
          AND job.triggered_by = 'manual'
          AND job.status IN ('completed', 'failed', 'cancelled')
        """
    )
    op.execute(
        """
        DELETE FROM trust_quality_recalculation_jobs
        WHERE triggered_by_user_id IS NULL
          AND triggered_by = 'manual'
          AND status IN ('completed', 'failed', 'cancelled')
        """
    )


def downgrade() -> None:
    # Deleted orphan history has no trustworthy actor data to reconstruct.
    pass
