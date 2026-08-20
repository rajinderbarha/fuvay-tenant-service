"""Notification-center composite indexes for high-volume inbox/outbox access.

Revision ID: 284
Revises: 283
"""
from alembic import op

revision = "284"
down_revision = "283"
branch_labels = None
depends_on = None


_INDEXES = {
    "ix_in_app_notif_user_created": "in_app_notifications (user_id, created_at DESC)",
    "ix_in_app_notif_user_read_created": "in_app_notifications (user_id, read_status, created_at DESC)",
    "ix_notif_outbox_status_created": "notification_outbox (delivery_status, created_at DESC)",
    "ix_notif_outbox_channel_created": "notification_outbox (channel, created_at DESC)",
    "ix_notif_outbox_recipient_type_created": "notification_outbox (recipient_type, created_at DESC)",
    "ix_notif_outbox_tenant_created": "notification_outbox (tenant_id, created_at DESC)",
    "ix_notif_outbox_vertical_created": "notification_outbox (vertical_key, created_at DESC)",
    "ix_notif_events_key_created": "notification_events (event_key, created_at DESC)",
}


def upgrade() -> None:
    # Concurrent builds avoid long write locks when this migration is applied
    # to a production outbox with millions of rows.
    with op.get_context().autocommit_block():
        for name, definition in _INDEXES.items():
            op.execute(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON {definition}')


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name in reversed(_INDEXES):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')
