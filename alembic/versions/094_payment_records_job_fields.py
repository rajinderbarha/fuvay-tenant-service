"""Fix missing Step-9 job-payment columns on payment_records.

The PaymentRecord model (app/engines/payment/models.py) was extended with 8
job-level on-site/cash payment fields (job_id, payment_number, payment_method,
payment_status, collected_by_user_id, collected_by_staff_id, paid_at, notes) for
Step 9's job invoice/payment/commission closure flow, but no migration ever
added them to the live table — every real call to BillingService.record_payment()
500'd with UndefinedColumnError. Same class of bug fixed previously for
catalog_module_definitions/vertical_catalog_modules (migration 091).

Revision ID: 094
Revises: 093
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='payment_records' AND column_name=:c"), {"c": col})
        return bool(r.fetchone())

    if not _col_exists("job_id"):
        op.add_column("payment_records", sa.Column("job_id", UUID(as_uuid=True), nullable=True))
        op.create_index("ix_pr_job", "payment_records", ["job_id"])
    if not _col_exists("payment_number"):
        op.add_column("payment_records", sa.Column("payment_number", sa.String(50), nullable=True))
        op.create_unique_constraint("uq_pr_payment_number", "payment_records", ["payment_number"])
    if not _col_exists("payment_method"):
        op.add_column("payment_records", sa.Column("payment_method", sa.String(30), nullable=True))
    if not _col_exists("payment_status"):
        op.add_column("payment_records", sa.Column("payment_status", sa.String(20), nullable=True))
        op.create_index("ix_pr_payment_status", "payment_records", ["payment_status"])
    if not _col_exists("collected_by_user_id"):
        op.add_column("payment_records", sa.Column("collected_by_user_id", UUID(as_uuid=True), nullable=True))
    if not _col_exists("collected_by_staff_id"):
        op.add_column("payment_records", sa.Column("collected_by_staff_id", UUID(as_uuid=True), nullable=True))
    if not _col_exists("paid_at"):
        op.add_column("payment_records", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    if not _col_exists("notes"):
        op.add_column("payment_records", sa.Column("notes", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("payment_records", "notes")
    op.drop_column("payment_records", "paid_at")
    op.drop_column("payment_records", "collected_by_staff_id")
    op.drop_column("payment_records", "collected_by_user_id")
    op.drop_index("ix_pr_payment_status", table_name="payment_records")
    op.drop_column("payment_records", "payment_status")
    op.drop_column("payment_records", "payment_method")
    op.drop_constraint("uq_pr_payment_number", "payment_records", type_="unique")
    op.drop_column("payment_records", "payment_number")
    op.drop_index("ix_pr_job", table_name="payment_records")
    op.drop_column("payment_records", "job_id")
