"""Add durable 30-minute provider and technician visit reminders.

Revision ID: 361
Revises: 360
"""
from alembic import op
import sqlalchemy as sa


revision = "361"
down_revision = "360"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_jobs",
        sa.Column("provider_reminder_30m_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "service_jobs",
        sa.Column("staff_reminder_30m_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("""
        INSERT INTO notif_event_templates
            (id, created_at, updated_at, template_key, template_name, channel,
             subject_template, body_template, action_label_template,
             action_url_template, is_active)
        VALUES
            (gen_random_uuid(), now(), now(), 'job.visit_reminder_30m.in_app',
             'Upcoming service visit - 30 minutes', 'in_app',
             'Visit starts in 30 minutes',
             '{{service_name}} - {{booking_number}} starts at {{time}}. {{visit_instruction}}',
             'Open job', '{{action_url}}', true)
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
    op.execute(
        "DELETE FROM notif_event_templates "
        "WHERE template_key = 'job.visit_reminder_30m.in_app'"
    )
    op.drop_column("service_jobs", "staff_reminder_30m_sent_at")
    op.drop_column("service_jobs", "provider_reminder_30m_sent_at")
