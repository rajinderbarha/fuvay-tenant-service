from pathlib import Path
import uuid

import pytest

from app.engines.notification.models import NotificationTemplate
from app.engines.notification.runtime_copy import render_runtime_copy
from app.engines.notification.seed_data import OPERATIONAL_TEMPLATE_SPECS


class _Scalars:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


class _Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return _Scalars(self.value)


class _Db:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    async def execute(self, _statement):
        if self.error:
            raise self.error
        return _Result(self.value)


@pytest.mark.asyncio
async def test_runtime_copy_renders_active_admin_template():
    template = NotificationTemplate(
        tenant_id=None,
        notif_type="customer_visit_reminder",
        event_type="customer_visit_reminder",
        channel="instagram",
        audience="customer",
        app_scope="customer_app",
        title="Visit update",
        body="{{technician_name}} will arrive {{visit_label}}.",
        action_label="Track {{technician_name}}",
        variables=["technician_name", "visit_label"],
        is_active=True,
        status="active",
        scope_type="platform_default",
        language="en",
        is_platform_default=True,
    )
    template.id = uuid.uuid4()
    rendered = await render_runtime_copy(
        _Db(template),
        event_type="customer_visit_reminder",
        channel="instagram",
        audience="customer",
        data={"technician_name": "Rajan", "visit_label": "today at 4 PM"},
        fallback_title="Fallback",
        fallback_body="Fallback body",
        vertical_key="home_services",
    )
    assert rendered.body == "Rajan will arrive today at 4 PM."
    assert rendered.title == "Visit update"
    assert rendered.action_label == "Track Rajan"
    assert rendered.used_fallback is False


@pytest.mark.asyncio
async def test_runtime_copy_uses_safe_fallback_for_missing_variable_or_db_failure():
    template = NotificationTemplate(
        tenant_id=None,
        notif_type="customer_visit_reminder",
        event_type="customer_visit_reminder",
        channel="instagram",
        audience="customer",
        app_scope="customer_app",
        title="Visit update",
        body="{{technician_name}} will arrive {{visit_label}}.",
        variables=["technician_name", "visit_label"],
        is_active=True,
        status="active",
    )
    template.id = uuid.uuid4()
    missing = await render_runtime_copy(
        _Db(template), event_type="customer_visit_reminder", channel="instagram",
        audience="customer", data={"technician_name": "Rajan"},
        fallback_title="Safe title", fallback_body="Safe body",
    )
    failed = await render_runtime_copy(
        _Db(error=RuntimeError("database unavailable")),
        event_type="customer_visit_reminder", channel="instagram",
        audience="customer", data={}, fallback_title="Safe title", fallback_body="Safe body",
    )
    assert missing.body == "Safe body" and missing.used_fallback is True
    assert failed.body == "Safe body" and failed.used_fallback is True


def test_operational_catalog_and_admin_ui_cover_live_instagram_messages():
    events = {row["event_type"] for row in OPERATIONAL_TEMPLATE_SPECS}
    assert {
        "customer_technician_assigned",
        "customer_reschedule_approval_requested",
        "customer_handover_reminder",
        "customer_payment_reminder",
        "customer_visit_reminder",
        "customer_assignment_cancelled",
    } <= events
    booking_updates = Path("app/engines/messaging_gateway/booking_updates.py").read_text("utf-8")
    assert 'template_event="customer_visit_reminder"' in booking_updates
    assert 'template_event="customer_provider_cancelled"' in booking_updates
    page = Path("frontend/super-admin/app/admin/notifications/page.tsx").read_text("utf-8")
    panel = Path("frontend/super-admin/app/admin/notifications/ManagedMessagesPanel.tsx").read_text("utf-8")
    assert "<ManagedMessagesPanel/>" in page
    assert "notifTemplateAdminApi.updateTemplate" in panel
    assert "Reason for change" in panel


def test_migration_392_seeds_the_operational_catalog():
    migration = Path("alembic/versions/392_admin_managed_operational_messages.py").read_text("utf-8")
    assert 'revision = "392"' in migration
    assert 'down_revision = "391"' in migration
    assert "OPERATIONAL_TEMPLATE_SPECS" in migration
    assert "notification_templates" in migration
