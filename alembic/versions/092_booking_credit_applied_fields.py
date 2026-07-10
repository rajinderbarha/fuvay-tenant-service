"""Fix broken customer-credit-to-booking integration.

apply_credit_to_booking() trusted a client-supplied `booking_amount` with no
server-side verification against the real Booking.quoted_price, and never wrote
the result back onto the Booking row — so the reduced payable-to-provider amount
was computed but silently discarded. This adds the two fields needed to persist
it, so the real amount displayed to customer/provider/technician can be correct.

Revision ID: 092
Revises: 091
"""
from alembic import op
import sqlalchemy as sa

revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    def _col_exists(table: str, col: str) -> bool:
        r = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"), {"t": table, "c": col})
        return bool(r.fetchone())

    if not _col_exists("bookings", "credit_applied"):
        op.add_column("bookings", sa.Column(
            "credit_applied", sa.Numeric(10, 2), server_default="0", nullable=False))
    if not _col_exists("bookings", "payable_amount"):
        op.add_column("bookings", sa.Column(
            "payable_amount", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("bookings", "payable_amount")
    op.drop_column("bookings", "credit_applied")
