"""Expose operational customer messages to the admin template center.

Revision ID: 392
Revises: 391
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "392"
down_revision = "391"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Importing the application-owned catalog avoids a second, drifting copy of
    # multilingual production wording.  The migration is still idempotent and
    # only consumes plain dictionaries.
    from app.engines.notification.seed_data import OPERATIONAL_TEMPLATE_SPECS

    conn = op.get_bind()
    now = datetime.now(timezone.utc)
    for spec in OPERATIONAL_TEMPLATE_SPECS:
        exists = conn.execute(sa.text("""
            SELECT 1 FROM notification_templates
             WHERE tenant_id IS NULL
               AND notif_type = :event_type
               AND channel = 'instagram'
             LIMIT 1
        """), {"event_type": spec["event_type"]}).first()
        if exists:
            continue
        conn.execute(sa.text("""
            INSERT INTO notification_templates (
                id, tenant_id, notif_type, channel, title, body, variables,
                is_active, vertical, event_type, audience, app_scope,
                scope_type, language, status, action_label, priority,
                is_platform_default, is_system, created_at, updated_at
            ) VALUES (
                :id, NULL, :event_type, 'instagram', :title, :body,
                CAST(:variables AS jsonb), true, 'home_services', :event_type,
                'customer', 'customer_app', 'platform_default', 'en', 'active',
                :action_label, 'normal', true, true, :created_at, :updated_at
            )
        """), {
            "id": str(uuid.uuid4()),
            "event_type": spec["event_type"],
            "title": spec["title"],
            "body": spec["body"],
            "variables": json.dumps(spec.get("variables", [])),
            "action_label": spec.get("action_label"),
            "created_at": now,
            "updated_at": now,
        })


def downgrade() -> None:
    from app.engines.notification.seed_data import OPERATIONAL_TEMPLATE_SPECS

    events = [spec["event_type"] for spec in OPERATIONAL_TEMPLATE_SPECS]
    op.get_bind().execute(sa.text("""
        DELETE FROM notification_templates
         WHERE tenant_id IS NULL
           AND channel = 'instagram'
           AND is_system = true
           AND event_type = ANY(:events)
    """), {"events": events})
