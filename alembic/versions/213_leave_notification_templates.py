"""Phase Q -- seed notif_event_templates rows for leave.approved/leave.rejected.
fire_event() silently no-ops without a matching template row (confirmed by
audit), so registering the event in event_registry.py alone is not enough --
this closes the real Phase P gap where leave decisions were never notified
to the requesting technician.

Revision ID: 213
Revises: 212
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "213"
down_revision = "212"
branch_labels = None
depends_on = None

_templates_table = sa.table(
    "notif_event_templates",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("template_key", sa.String),
    sa.column("template_name", sa.String),
    sa.column("channel", sa.String),
    sa.column("subject_template", sa.String),
    sa.column("body_template", sa.Text),
    sa.column("action_label_template", sa.String),
    sa.column("action_url_template", sa.String),
    sa.column("is_active", sa.Boolean),
)


def upgrade() -> None:
    op.bulk_insert(_templates_table, [
        {
            "id": uuid.uuid4(),
            "template_key": "leave.approved.in_app",
            "template_name": "Leave Request Approved (In-App)",
            "channel": "in_app",
            "subject_template": "Your leave request was approved",
            "body_template": "Your time-off request has been approved. Tap to view your schedule.",
            "action_label_template": "View schedule",
            "action_url_template": "/staff/schedule",
            "is_active": True,
        },
        {
            "id": uuid.uuid4(),
            "template_key": "leave.rejected.in_app",
            "template_name": "Leave Request Rejected (In-App)",
            "channel": "in_app",
            "subject_template": "Your leave request was not approved",
            "body_template": "Your time-off request was not approved. Tap to view details.",
            "action_label_template": "View schedule",
            "action_url_template": "/staff/schedule",
            "is_active": True,
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM notif_event_templates WHERE template_key IN ('leave.approved.in_app', 'leave.rejected.in_app')")
