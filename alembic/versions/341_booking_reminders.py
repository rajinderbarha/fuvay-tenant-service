"""Add durable, idempotent Home Services booking reminders.

Revision ID: 341
Revises: 340
"""
from alembic import op
import sqlalchemy as sa


revision = "341"
down_revision = "340"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_jobs", sa.Column("reminder_24h_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("service_jobs", sa.Column("reminder_1h_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("""
        INSERT INTO notif_event_templates
            (id, created_at, updated_at, template_key, template_name, channel,
             subject_template, body_template, action_label_template, action_url_template, is_active)
        VALUES
            (gen_random_uuid(), now(), now(), 'booking.reminder_24h.in_app',
             'Booking reminder — tomorrow', 'in_app', 'Your booking is tomorrow',
             '{{service_name}} is scheduled tomorrow, {{date}}, at {{time}}.',
             'View booking', '/customer/bookings/{{booking_id}}', true),
            (gen_random_uuid(), now(), now(), 'booking.reminder_1h.in_app',
             'Booking reminder — one hour', 'in_app', 'Your booking starts soon',
             '{{service_name}} is scheduled at {{time}}. Please make sure someone is available at the service address.',
             'View booking', '/customer/bookings/{{booking_id}}', true)
        ON CONFLICT (template_key) DO UPDATE
          SET template_name = EXCLUDED.template_name,
              subject_template = EXCLUDED.subject_template,
              body_template = EXCLUDED.body_template,
              action_label_template = EXCLUDED.action_label_template,
              action_url_template = EXCLUDED.action_url_template,
              is_active = true,
              updated_at = now()
    """)


def downgrade() -> None:
    op.execute("DELETE FROM notif_event_templates WHERE template_key IN ('booking.reminder_24h.in_app', 'booking.reminder_1h.in_app')")
    op.drop_column("service_jobs", "reminder_1h_sent_at")
    op.drop_column("service_jobs", "reminder_24h_sent_at")
