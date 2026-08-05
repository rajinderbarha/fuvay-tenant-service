"""NOTIFICATION-CENTER: seed the one remaining untemplated in_app template
key (chat.new_message.in_app) found after migration 204 -- brings the
registry's 35 distinct in_app template_keys to fully seeded (34/34 existing
+ this one).

Revision ID: 205
Revises: 204
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "205"
down_revision = "204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM notif_event_templates WHERE template_key = 'chat.new_message.in_app'")
    ).fetchone()
    if exists:
        return
    now = datetime.now(timezone.utc)
    conn.execute(sa.text("""
        INSERT INTO notif_event_templates
            (id, template_key, template_name, channel, subject_template, body_template,
             action_label_template, action_url_template, is_active, created_at, updated_at)
        VALUES
            (:id, 'chat.new_message.in_app', 'New Chat Message (In-App)', 'in_app',
             'New message', 'You have a new message.', 'View message', '/chat', true, :now, :now)
    """), {"id": str(uuid.uuid4()), "now": now})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM notif_event_templates WHERE template_key = 'chat.new_message.in_app'"))
