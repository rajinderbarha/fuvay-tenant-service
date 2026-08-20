"""Make active job refund submissions retry-safe.

Revision ID: 269
Revises: 268
"""
from alembic import op

revision = "269"
down_revision = "268"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX uq_refund_active_customer_job "
        "ON refund_requests (customer_id, job_id) "
        "WHERE job_id IS NOT NULL AND status <> 'cancelled'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_refund_active_customer_job")
