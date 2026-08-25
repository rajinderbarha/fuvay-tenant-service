"""Make customer quote notifications open their booking detail.

Revision ID: 306
Revises: 305
"""
from alembic import op

revision = "306"
down_revision = "305"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical quote.sent rows stored a quote id. The native customer app
    # deliberately accepts only allowlisted record destinations and has no
    # standalone quote route; it presents quote approval within Booking
    # Details. Backfill the canonical booking identity so existing unread
    # notifications become actionable too.
    op.execute("""
        UPDATE in_app_notifications AS n
           SET source_record_type = 'service_bookings',
               source_record_id = q.booking_id,
               updated_at = now()
          FROM service_job_quotes AS q
         WHERE n.notification_type = 'quote.sent'
           AND n.source_record_type = 'service_job_quote'
           AND n.source_record_id = q.id
           AND q.booking_id IS NOT NULL
    """)


def downgrade() -> None:
    # The quote id cannot be reconstructed from a booking alone when a booking
    # has multiple quote versions. Leaving the safe booking destination in
    # place is less destructive than guessing during downgrade.
    pass

