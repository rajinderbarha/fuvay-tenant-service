"""NOTIFICATION-CENTER: seed the remaining registered-but-untemplated
in_app notification templates.

Audit found: NotificationService._create_outbox_for_recipient silently
skips delivery when no NotifEventTemplate row exists for an event's
template_key (logs "notification.template_missing" and continues) -- a
missing template means fire_event() succeeds (the NotificationEvent row is
created) but NO InAppNotification is ever produced. Of the 35 distinct
in_app template_keys referenced across event_registry.py, only 11 had a
seeded row (confirmed live query against this environment).

Several of the still-untemplated events (complaint.*, quote.*, wallet.*,
review.*, tenant.verified/suspended) also have ZERO real fire_event()
caller today -- their tenant-facing notifications are instead hand-rolled
directly by complaint_service.py / quote_checklist/notifications.py /
customer_reviews/notifications.py under DIFFERENT literal notification_type
strings (e.g. "complaint.filed", not "complaint.created" -- see
workspace_projection.py's ACTION_REQUIRED_EVENT_KEYS comment for the full
finding). Seeding these registry-path templates does not change today's
live behavior, but closes a real reliability gap: if/when one of these
registry event keys is ever wired to fire_event() (the natural next step
for, say, a real usage-credit low-balance alert), delivery will not
silently fail for want of a template row.

Revision ID: 204
Revises: 203
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import table, column

revision = "204"
down_revision = "203"
branch_labels = None
depends_on = None

_notif_templates = table(
    "notif_event_templates",
    column("id", UUID(as_uuid=True)),
    column("template_key", sa.String),
    column("template_name", sa.String),
    column("channel", sa.String),
    column("subject_template", sa.String),
    column("body_template", sa.Text),
    column("action_label_template", sa.String),
    column("action_url_template", sa.String),
    column("is_active", sa.Boolean),
    column("created_at", sa.DateTime(timezone=True)),
    column("updated_at", sa.DateTime(timezone=True)),
)

# (template_key, name, subject, body, action_label, action_url)
_TEMPLATES = [
    ("appointment.confirmed.in_app", "Appointment Confirmed (In-App)",
     "Appointment confirmed", "Your appointment on {{appointment_date}} is confirmed.",
     "View appointment", "/appointments"),
    ("appointment.completed.in_app", "Appointment Completed (In-App)",
     "Session completed", "Your session on {{appointment_date}} is complete.",
     "View appointment", "/appointments"),
    ("complaint.created.in_app", "Complaint Filed (In-App)",
     "New complaint — {{complaint_number}}", "A customer filed a complaint. Please respond.",
     "View complaint", "/home-services/complaints"),
    ("complaint.provider_responded.in_app", "Complaint Response (In-App)",
     "Response to your complaint", "The provider responded to complaint {{complaint_number}}.",
     "View complaint", "/home-services/complaints"),
    ("complaint.refund_approved.in_app", "Refund Approved (In-App)",
     "Refund approved", "A refund was approved for complaint {{complaint_number}}.",
     "View complaint", "/home-services/complaints"),
    ("complaint.resolved.in_app", "Complaint Resolved (In-App)",
     "Complaint resolved", "Complaint {{complaint_number}} has been resolved.",
     "View complaint", "/home-services/complaints"),
    ("compliance.sla.warning.in_app", "Compliance SLA Warning (In-App)",
     "SLA deadline approaching", "A compliance item is approaching its deadline ({{deadline}}).",
     "Review", "/compliance"),
    ("compliance.sla.critical.in_app", "Compliance SLA Critical (In-App)",
     "SLA deadline breached", "A compliance item has breached its deadline ({{deadline}}).",
     "Review", "/compliance"),
    ("job.accepted.in_app", "Job Accepted (In-App)",
     "Job accepted", "Technician accepted job {{job_number}}.",
     "View job", "/home-services/bookings-jobs"),
    ("job.completed.in_app", "Job Completed (In-App)",
     "Job completed", "Job {{job_number}} has been completed.",
     "View job", "/home-services/bookings-jobs"),
    ("job.created.in_app", "Job Created (In-App)",
     "New job created", "Job {{job_number}} was created and needs assignment.",
     "View job", "/home-services/bookings-jobs"),
    ("job.scheduled.in_app", "Job Scheduled (In-App)",
     "Job scheduled", "Job {{job_number}} has been scheduled.",
     "View job", "/home-services/bookings-jobs"),
    ("lead.created.in_app", "New Lead (In-App)",
     "New lead received", "A new lead from {{lead_name}} was received.",
     "View lead", "/leads"),
    ("lead.accepted.in_app", "Lead Accepted (In-App)",
     "Lead accepted", "Lead from {{lead_name}} was accepted.",
     "View lead", "/leads"),
    ("payment.collected.in_app", "Payment Collected (In-App)",
     "Payment collected", "A payment of {{amount}} was collected.",
     "View payment", "/finance"),
    ("quote.sent_to_customer.in_app", "Quote Sent (In-App)",
     "Quote sent to customer", "Quote {{quote_number}} for {{amount}} was sent to the customer.",
     "View quote", "/service-jobs"),
    ("quote.customer_approved.in_app", "Quote Approved (In-App)",
     "Customer approved a quote", "Quote {{quote_number}} for {{amount}} was approved by the customer.",
     "View quote", "/service-jobs"),
    ("quote.customer_rejected.in_app", "Quote Rejected (In-App)",
     "Customer rejected a quote", "Quote {{quote_number}} for {{amount}} was rejected by the customer.",
     "View quote", "/service-jobs"),
    ("review.submitted.in_app", "Review Submitted (In-App)",
     "New review received", "A customer left a {{rating}}-star review.",
     "View review", "/reviews"),
    ("review.approved.in_app", "Review Approved (In-App)",
     "Review published", "Your review response was approved.",
     "View review", "/reviews"),
    ("tenant.verified.in_app", "Provider Verified (In-App)",
     "Your business is verified", "{{tenant_name}} has been verified.",
     "View profile", "/profile"),
    ("tenant.suspended.in_app", "Provider Suspended (In-App)",
     "Account suspended", "{{tenant_name}} has been suspended. Contact support.",
     "Contact support", "/settings"),
    ("wallet.low_balance.in_app", "Wallet Low Balance (In-App)",
     "Usage credit balance is low", "Your usage credit balance is {{balance}}. Top up to avoid service interruption.",
     "Top up credits", "/finance/usage-credit-ledger"),
]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0] for row in conn.execute(sa.text("SELECT template_key FROM notif_event_templates")).fetchall()
    }
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": uuid.uuid4(), "template_key": key, "template_name": name,
            "channel": "in_app", "subject_template": subject, "body_template": body,
            "action_label_template": action_label, "action_url_template": action_url,
            "is_active": True, "created_at": now, "updated_at": now,
        }
        for key, name, subject, body, action_label, action_url in _TEMPLATES
        if key not in existing
    ]
    if rows:
        op.bulk_insert(_notif_templates, rows)


def downgrade() -> None:
    conn = op.get_bind()
    keys = [t[0] for t in _TEMPLATES]
    conn.execute(
        sa.text("DELETE FROM notif_event_templates WHERE template_key = ANY(:keys)"),
        {"keys": keys},
    )
