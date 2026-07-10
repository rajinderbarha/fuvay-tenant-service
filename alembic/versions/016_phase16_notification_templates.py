"""Phase 16 — Seed platform-default notification templates (in_app channel)

Revision ID: 016
Revises: 015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None

_TEMPLATES = [
    ("job_assigned",       "Job Assigned",         "Your job {{job_number}} has been assigned to {{staff_name}}. They will arrive at {{scheduled_at}}."),
    ("job_status_changed", "Job Status Updated",   "Job {{job_number}} status changed to {{new_status}}."),
    ("booking_confirmed",  "Booking Confirmed",    "Your booking {{booking_number}} on {{scheduled_date}} at {{slot}} is confirmed."),
    ("booking_cancelled",  "Booking Cancelled",    "Your booking {{booking_number}} has been cancelled. Reason: {{reason}}."),
    ("payment_received",   "Payment Received",     "Payment of ₹{{amount}} received for {{reference}}."),
    ("wallet_low",         "Wallet Balance Low",   "Your wallet balance (₹{{balance}}) is below the minimum threshold. Top up to continue operations."),
    ("warranty_claim",     "Warranty Claim",       "A warranty claim has been raised for job {{job_number}}. Issue: {{issue}}."),
    ("staff_invited",      "Staff Invitation",     "You have been invited to join {{tenant_name}} as {{role}}. Accept your invite to get started."),
    ("review_requested",   "Leave a Review",       "How was your experience with job {{job_number}}? Share your feedback to help us improve."),
    ("system_alert",       "System Alert",         "{{message}}"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for notif_type, title, body in _TEMPLATES:
        # Embed static values directly — safe since these are hardcoded migration constants
        safe_type  = notif_type.replace("'", "''")
        safe_title = title.replace("'", "''")
        safe_body  = body.replace("'", "''")
        conn.execute(sa.text(f"""
            INSERT INTO notification_templates
                (id, tenant_id, notif_type, channel, title, body, variables, is_active,
                 created_at, updated_at)
            SELECT gen_random_uuid(), NULL, '{safe_type}', 'in_app',
                   '{safe_title}', '{safe_body}', '[]'::jsonb, true, now(), now()
            WHERE NOT EXISTS (
                SELECT 1 FROM notification_templates
                WHERE tenant_id IS NULL
                  AND notif_type = '{safe_type}'
                  AND channel = 'in_app'
            )
        """))


def downgrade() -> None:
    conn = op.get_bind()
    notif_types = [t[0] for t in _TEMPLATES]
    conn.execute(sa.text("""
        DELETE FROM notification_templates
        WHERE tenant_id IS NULL AND channel = 'in_app'
          AND notif_type = ANY(:types)
    """), {"types": notif_types})
