"""Seed the registered job-delayed in-app notification template.

Revision ID: 333
Revises: 332
"""
from alembic import op


revision = "333"
down_revision = "332"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO notif_event_templates
            (id, template_key, template_name, channel, subject_template,
             body_template, action_label_template, action_url_template,
             is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'job.delayed.in_app', 'Job Delayed (In-App)',
             'in_app', 'Job delayed',
             'Job {{job_number}} is delayed. Open the job for the latest schedule and status.',
             'View job', '/home-services/bookings-jobs', true, now(), now())
        ON CONFLICT (template_key) DO UPDATE SET
            is_active = true, updated_at = now()
    """)


def downgrade() -> None:
    op.execute("DELETE FROM notif_event_templates WHERE template_key = 'job.delayed.in_app'")
