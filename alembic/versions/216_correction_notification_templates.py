"""Phase S -- seed notif_event_templates rows for employment_correction.*
events. fire_event() silently no-ops without a matching template row
(confirmed pattern from Phase Q's migration 213) -- registering the event
in event_registry.py alone is not enough.

Revision ID: 216
Revises: 215
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "216"
down_revision = "215"
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
            "template_key": "employment_correction.approved.in_app",
            "template_name": "Employment Correction Approved (In-App)",
            "channel": "in_app",
            "subject_template": "Your correction request was approved",
            "body_template": "Your employment details correction request has been approved.",
            "action_label_template": "View employment details",
            "action_url_template": "/staff/profile/employment",
            "is_active": True,
        },
        {
            "id": uuid.uuid4(),
            "template_key": "employment_correction.changes_requested.in_app",
            "template_name": "Employment Correction Needs Changes (In-App)",
            "channel": "in_app",
            "subject_template": "Your correction request needs changes",
            "body_template": "Your business asked for changes to your correction request. Tap to view details.",
            "action_label_template": "View employment details",
            "action_url_template": "/staff/profile/employment",
            "is_active": True,
        },
        {
            "id": uuid.uuid4(),
            "template_key": "employment_correction.rejected.in_app",
            "template_name": "Employment Correction Rejected (In-App)",
            "channel": "in_app",
            "subject_template": "Your correction request was not approved",
            "body_template": "Your employment details correction request was not approved.",
            "action_label_template": "View employment details",
            "action_url_template": "/staff/profile/employment",
            "is_active": True,
        },
    ])


def downgrade() -> None:
    op.execute(
        "DELETE FROM notif_event_templates WHERE template_key IN "
        "('employment_correction.approved.in_app', 'employment_correction.changes_requested.in_app', "
        "'employment_correction.rejected.in_app')"
    )
