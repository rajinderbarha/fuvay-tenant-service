"""NOTIFICATION-CENTER: seed invoice.issued.in_app, missed in migration 204's
sweep of event_registry.py's distinct template_keys (found by the
migration's own completeness test).

Revision ID: 206
Revises: 205
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "206"
down_revision = "205"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM notif_event_templates WHERE template_key = 'invoice.issued.in_app'")
    ).fetchone()
    if exists:
        return
    now = datetime.now(timezone.utc)
    conn.execute(sa.text("""
        INSERT INTO notif_event_templates
            (id, template_key, template_name, channel, subject_template, body_template,
             action_label_template, action_url_template, is_active, created_at, updated_at)
        VALUES
            (:id, 'invoice.issued.in_app', 'Invoice Issued (In-App)', 'in_app',
             'Your invoice is ready', 'Invoice for {{amount}} is ready for payment.',
             'View invoice', '/invoices', true, :now, :now)
    """), {"id": str(uuid.uuid4()), "now": now})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM notif_event_templates WHERE template_key = 'invoice.issued.in_app'"))
