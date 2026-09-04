"""NOTIFICATION-CENTER-REBUILD Phase 3 (scoped slice): vertical scope +
mandatory-event protection on the live platform_notifications engine.

Audit finding (Phase 1/2): platform_notifications is the engine that
actually backs /admin/notifications today (NotificationEvent/Outbox/
InAppNotification/NotificationPreference), but none of those tables carry
a vertical scope, and no event is protected from being disabled -- every
event x channel combination in NotificationPreference is equally
toggleable, including what should be mandatory platform-critical events
(compliance SLA breaches today; security/DPDP/complaint-SLA-breach/
work-start-block events once producers exist for them).

`vertical_key` is a plain string (mirrors Vertical.key, the same
string-bridge pattern already used by ServiceCategory.vertical_type --
not a new FK convention) so a NULL value means "global", matching the
architectural rule that auth/security/compliance events are never
vertical-scoped. Denormalized onto both notification_events (the
event-of-record) and in_app_notifications (so the Inbox can filter/hide
NEW notifications for a disabled vertical without a join, while historical
rows keep whatever vertical_key applied when they were created -- exactly
the "snapshotted at creation time" pattern used elsewhere in this codebase
for monetization policy versions).

`is_mandatory` is snapshotted onto notification_events at fire_event() time
from the code-defined event registry (NotificationEventRegistry), so a
later change to the registry's mandatory flag never rewrites history --
same versioning principle as VerticalMonetizationPolicy.

Revision ID: 184
Revises: 183
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "184"
down_revision = "183"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_events", sa.Column("vertical_key", sa.String(length=80), nullable=True))
    op.add_column("notification_events", sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("ix_notif_events_vertical", "notification_events", ["vertical_key"])

    op.add_column("notification_outbox", sa.Column("vertical_key", sa.String(length=80), nullable=True))
    op.create_index("ix_notif_outbox_vertical", "notification_outbox", ["vertical_key"])

    op.add_column("in_app_notifications", sa.Column("vertical_key", sa.String(length=80), nullable=True))
    op.add_column("in_app_notifications", sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="false"))
    op.create_index("ix_in_app_notif_vertical", "in_app_notifications", ["vertical_key"])

    # Seed the 2 templates the scoped Phase-3 proof flows render against --
    # zero NotifEventTemplate rows existed before this migration (confirmed
    # live via GET /v1/admin/notification-templates -> {"items": [], "total": 0}),
    # so without these rows fire_event() would skip outbox creation entirely
    # ("template_missing") for both booking.confirmed and job.assigned.
    op.execute("""
        INSERT INTO notif_event_templates
            (id, created_at, updated_at, template_key, template_name, channel,
             subject_template, body_template, action_label_template, action_url_template, is_active)
        VALUES
            (gen_random_uuid(), now(), now(), 'booking.confirmed.in_app', 'Booking Confirmed (In-App)', 'in_app',
             NULL, 'Booking {{booking_number}} is confirmed.', 'View booking', '/customer/bookings/{{booking_id}}', true),
            (gen_random_uuid(), now(), now(), 'job.assigned.in_app', 'Job Assigned (In-App)', 'in_app',
             'New job assigned to you', 'A job has been assigned to you. Tap to view the details and accept it.', 'View job', '/staff/jobs/{{job_id}}', true),
            (gen_random_uuid(), now(), now(), 'booking.new.in_app', 'New Booking Received (In-App)', 'in_app',
             'New booking received', 'Booking {{booking_number}} came in. Assign a technician to get started.', 'View jobs', '/service-jobs', true)
        ON CONFLICT (template_key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM notif_event_templates WHERE template_key IN "
               "('booking.confirmed.in_app', 'job.assigned.in_app', 'booking.new.in_app')")
    op.drop_index("ix_in_app_notif_vertical", table_name="in_app_notifications")
    op.drop_column("in_app_notifications", "is_mandatory")
    op.drop_column("in_app_notifications", "vertical_key")

    op.drop_index("ix_notif_outbox_vertical", table_name="notification_outbox")
    op.drop_column("notification_outbox", "vertical_key")

    op.drop_index("ix_notif_events_vertical", table_name="notification_events")
    op.drop_column("notification_events", "is_mandatory")
    op.drop_column("notification_events", "vertical_key")
