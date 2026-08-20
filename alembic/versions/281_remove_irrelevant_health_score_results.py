"""Remove the current calculated Trust & Quality health-score dataset.

The scoring formulas are retained so scores can be regenerated explicitly
after the underlying provider and technician data is production-ready.

Revision ID: 281
Revises: 280
"""

from alembic import op


revision = "281"
down_revision = "280"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM trust_quality_audit_logs
        WHERE target_type = 'health_score'
           OR action_type LIKE 'health_score.%'
        """
    )
    op.execute("DELETE FROM health_scores")


def downgrade() -> None:
    # Calculated values are intentionally not reconstructed. They can be
    # regenerated from retained formulas through an explicit recalculation.
    pass
