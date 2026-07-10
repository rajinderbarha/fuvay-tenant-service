"""Job Completion + Usage Credit Deduction Verification Sprint.

Propagates the customer-service-credit fields fixed in migration 092
(bookings.credit_applied / bookings.payable_amount) onto the Job created from
that booking — previously convert_to_job copied quoted_price but silently
dropped credit_applied/payable_amount, so the technician-facing job detail had
no way to know the correct amount to collect from the customer.

Revision ID: 093
Revises: 092
"""
from alembic import op
import sqlalchemy as sa

revision = "093"
down_revision = "092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    if not _col_exists("jobs", "credit_applied"):
        op.add_column("jobs", sa.Column(
            "credit_applied", sa.Numeric(10, 2), server_default="0", nullable=False))
    if not _col_exists("jobs", "payable_amount"):
        op.add_column("jobs", sa.Column("payable_amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "payable_amount")
    op.drop_column("jobs", "credit_applied")
