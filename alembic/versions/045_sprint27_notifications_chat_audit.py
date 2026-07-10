"""Sprint 27 — Notification + Chat + Audit Integration

Revision ID: 045
Revises: 044
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. notification_events ────────────────────────────────────────────────
    op.create_table(
        "notification_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_key", sa.String(120), nullable=False),
        sa.Column("event_name", sa.String(200), nullable=False),
        sa.Column("source_engine", sa.String(80), nullable=False),
        sa.Column("source_record_type", sa.String(80), nullable=True),
        sa.Column("source_record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notif_events_key", "notification_events", ["event_key"])
    op.create_index("ix_notif_events_tenant", "notification_events", ["tenant_id"])
    op.create_index("ix_notif_events_status", "notification_events", ["status"])
    op.create_index("ix_notif_events_created", "notification_events", ["created_at"])

    # ── 2. notification_outbox ────────────────────────────────────────────────
    op.create_table(
        "notification_outbox",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("notification_event_id", UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_type", sa.String(30), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("template_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("action_label", sa.String(100), nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("delivery_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("provider_name", sa.String(80), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("failure_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notif_outbox_status", "notification_outbox", ["delivery_status"])
    op.create_index("ix_notif_outbox_recipient", "notification_outbox", ["recipient_user_id"])
    op.create_index("ix_notif_outbox_event", "notification_outbox", ["notification_event_id"])
    op.create_index("ix_notif_outbox_created", "notification_outbox", ["created_at"])

    # ── 3. in_app_notifications ───────────────────────────────────────────────
    op.create_table(
        "in_app_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("outbox_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("notification_type", sa.String(120), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("action_label", sa.String(100), nullable=True),
        sa.Column("source_record_type", sa.String(80), nullable=True),
        sa.Column("source_record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("read_status", sa.String(20), nullable=False, server_default="unread"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_in_app_notif_user", "in_app_notifications", ["user_id"])
    op.create_index("ix_in_app_notif_read", "in_app_notifications", ["read_status"])
    op.create_index("ix_in_app_notif_created", "in_app_notifications", ["created_at"])

    # ── 4. notif_event_templates ──────────────────────────────────────────────
    op.create_table(
        "notif_event_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_key", sa.String(150), nullable=False, unique=True),
        sa.Column("template_name", sa.String(200), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject_template", sa.String(255), nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("action_label_template", sa.String(100), nullable=True),
        sa.Column("action_url_template", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notif_evt_tmpl_key", "notif_event_templates", ["template_key"])
    op.create_index("ix_notif_evt_tmpl_channel", "notif_event_templates", ["channel"])

    # ── 5. notification_preferences ──────────────────────────────────────────
    op.create_table(
        "notification_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_key", sa.String(120), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "event_key", "channel", name="uq_notif_pref_user_event_channel"),
    )
    op.create_index("ix_notif_pref_user", "notification_preferences", ["user_id"])

    # ── 6. chat_threads ───────────────────────────────────────────────────────
    op.create_table(
        "chat_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_number", sa.String(40), nullable=False, unique=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=True),
        sa.Column("record_type", sa.String(50), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("record_type", "record_id", name="uq_chat_thread_record"),
    )
    op.create_index("ix_chat_thread_tenant", "chat_threads", ["tenant_id"])
    op.create_index("ix_chat_thread_record", "chat_threads", ["record_type", "record_id"])
    op.create_index("ix_chat_thread_customer", "chat_threads", ["customer_id"])

    # ── 7. chat_thread_participants ───────────────────────────────────────────
    op.create_table(
        "chat_thread_participants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("participant_type", sa.String(20), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("can_read", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("can_send", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("thread_id", "user_id", name="uq_chat_participant"),
    )
    op.create_index("ix_chat_participant_thread", "chat_thread_participants", ["thread_id"])
    op.create_index("ix_chat_participant_user", "chat_thread_participants", ["user_id"])

    # ── 8. chat_messages (Sprint 27 record-linked) ────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("message_text", sa.Text, nullable=True),
        sa.Column("media_urls", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="thread"),
        sa.Column("delivery_status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("is_hidden", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("hidden_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_msg_thread", "chat_messages", ["thread_id"])
    op.create_index("ix_chat_msg_sender", "chat_messages", ["sender_user_id"])
    op.create_index("ix_chat_msg_created", "chat_messages", ["created_at"])

    # ── 9. chat_message_reads ─────────────────────────────────────────────────
    op.create_table(
        "chat_message_reads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("message_id", "user_id", name="uq_msg_read"),
    )
    op.create_index("ix_msg_reads_user", "chat_message_reads", ["user_id"])
    op.create_index("ix_msg_reads_thread", "chat_message_reads", ["thread_id"])

    # ── Seed default in-app notification event templates ──────────────────────
    op.execute("""
    INSERT INTO notif_event_templates
        (id, template_key, template_name, channel, subject_template, body_template,
         action_label_template, action_url_template, is_active, created_at, updated_at)
    VALUES
        (gen_random_uuid(), 'booking.confirmed.in_app', 'Booking Confirmed', 'in_app',
         'Booking Confirmed', 'Your booking {{booking_number}} has been confirmed.',
         'View Booking', '/bookings/{{booking_id}}', true, now(), now()),

        (gen_random_uuid(), 'job.created.in_app', 'Job Created', 'in_app',
         'Job Created', 'Job {{job_number}} has been created for your booking.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'job.assigned.in_app', 'Technician Assigned', 'in_app',
         'Technician Assigned', 'A technician has been assigned to your booking {{booking_number}}.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'job.accepted.in_app', 'Job Accepted', 'in_app',
         'Job Accepted', 'Your technician has accepted job {{job_number}}.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'job.scheduled.in_app', 'Job Scheduled', 'in_app',
         'Job Scheduled', 'Your job {{job_number}} is scheduled for {{scheduled_date}}.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'job.completed.in_app', 'Job Completed', 'in_app',
         'Job Completed', 'Job {{job_number}} has been completed.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'quote.sent_to_customer.in_app', 'Quote Received', 'in_app',
         'Quote Received', 'You have received a quote for {{service_name}}.',
         'View Quote', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'quote.customer_approved.in_app', 'Quote Approved', 'in_app',
         'Quote Approved', 'Customer approved the quote for job {{job_number}}.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'quote.customer_rejected.in_app', 'Quote Rejected', 'in_app',
         'Quote Rejected', 'Customer rejected the quote for job {{job_number}}.',
         'View Job', '/jobs/{{job_id}}', true, now(), now()),

        (gen_random_uuid(), 'invoice.issued.in_app', 'Invoice Issued', 'in_app',
         'Invoice Issued', 'Invoice {{invoice_number}} has been issued.',
         'View Invoice', '/invoices/{{invoice_id}}', true, now(), now()),

        (gen_random_uuid(), 'payment.collected.in_app', 'Payment Collected', 'in_app',
         'Payment Collected', 'Payment of {{amount}} has been collected for {{invoice_number}}.',
         'View Invoice', '/invoices/{{invoice_id}}', true, now(), now()),

        (gen_random_uuid(), 'appointment.confirmed.in_app', 'Appointment Confirmed', 'in_app',
         'Appointment Confirmed', 'Your appointment {{appointment_number}} is confirmed.',
         'View Appointment', '/appointments/{{appointment_id}}', true, now(), now()),

        (gen_random_uuid(), 'appointment.completed.in_app', 'Session Completed', 'in_app',
         'Session Completed', 'Your session {{appointment_number}} is complete.',
         'View Appointment', '/appointments/{{appointment_id}}', true, now(), now()),

        (gen_random_uuid(), 'lead.created.in_app', 'Lead Created', 'in_app',
         'New Lead', 'A new real estate lead {{lead_number}} has been created.',
         'View Lead', '/leads/{{lead_id}}', true, now(), now()),

        (gen_random_uuid(), 'lead.accepted.in_app', 'Lead Accepted', 'in_app',
         'Lead Accepted', 'An agent has accepted your lead {{lead_number}}.',
         'View Lead', '/leads/{{lead_id}}', true, now(), now()),

        (gen_random_uuid(), 'review.submitted.in_app', 'Review Received', 'in_app',
         'New Review', 'A customer submitted a review for {{service_name}}.',
         'View Review', '/reviews/{{review_id}}', true, now(), now()),

        (gen_random_uuid(), 'review.approved.in_app', 'Review Approved', 'in_app',
         'Review Approved', 'Your review has been approved.',
         'View Review', '/reviews/{{review_id}}', true, now(), now()),

        (gen_random_uuid(), 'complaint.created.in_app', 'Complaint Filed', 'in_app',
         'Complaint Filed', 'Complaint {{complaint_number}} has been created.',
         'View Complaint', '/complaints/{{complaint_id}}', true, now(), now()),

        (gen_random_uuid(), 'complaint.provider_responded.in_app', 'Complaint Response', 'in_app',
         'Complaint Response', 'The provider has responded to complaint {{complaint_number}}.',
         'View Complaint', '/complaints/{{complaint_id}}', true, now(), now()),

        (gen_random_uuid(), 'complaint.resolved.in_app', 'Complaint Resolved', 'in_app',
         'Complaint Resolved', 'Complaint {{complaint_number}} has been resolved.',
         'View Complaint', '/complaints/{{complaint_id}}', true, now(), now()),

        (gen_random_uuid(), 'complaint.refund_approved.in_app', 'Refund Approved', 'in_app',
         'Refund Approved', 'Your refund request for complaint {{complaint_number}} has been approved.',
         'View Complaint', '/complaints/{{complaint_id}}', true, now(), now()),

        (gen_random_uuid(), 'wallet.low_balance.in_app', 'Low Wallet Balance', 'in_app',
         'Low Balance Warning', 'Your wallet balance is low. Current: {{balance}}.',
         'Top Up', '/wallet', true, now(), now()),

        (gen_random_uuid(), 'chat.new_message.in_app', 'New Chat Message', 'in_app',
         'New Message', 'You have a new message in thread {{thread_number}}.',
         'View Chat', '/chat/{{thread_id}}', true, now(), now()),

        (gen_random_uuid(), 'tenant.verified.in_app', 'Account Verified', 'in_app',
         'Account Verified', 'Your provider account has been verified.',
         'View Dashboard', '/dashboard', true, now(), now()),

        (gen_random_uuid(), 'tenant.suspended.in_app', 'Account Suspended', 'in_app',
         'Account Suspended', 'Your provider account has been suspended. Contact support.',
         'Contact Support', '/support', true, now(), now())
    ON CONFLICT (template_key) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table("chat_message_reads")
    op.drop_table("chat_messages")
    op.drop_table("chat_thread_participants")
    op.drop_table("chat_threads")
    op.drop_table("notification_preferences")
    op.drop_table("notif_event_templates")
    op.drop_table("in_app_notifications")
    op.drop_table("notification_outbox")
    op.drop_table("notification_events")
