"""Recover booking destinations for historical quote notifications.

Revision ID: 307
Revises: 306
"""
from alembic import op

revision = "307"
down_revision = "306"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some development/retention cleanup removed old quote revisions while
    # their unread notification and booking correctly remained. The legacy
    # producer embedded the canonical booking UUID in a fixed internal path.
    # Parse only that exact trusted shape, require the booking to exist, and
    # write the same explicit destination fields produced by new code.
    op.execute(r"""
        UPDATE in_app_notifications AS n
           SET source_record_type = 'service_bookings',
               source_record_id = b.id,
               updated_at = now()
          FROM service_bookings AS b
         WHERE n.notification_type = 'quote.sent'
           AND n.source_record_type = 'service_job_quote'
           AND n.action_url ~ '^/customer/bookings/[0-9a-fA-F-]{36}/quotes(?:\?|$)'
           AND b.id = substring(
               n.action_url from '^/customer/bookings/([0-9a-fA-F-]{36})/quotes'
           )::uuid
    """)


def downgrade() -> None:
    pass

