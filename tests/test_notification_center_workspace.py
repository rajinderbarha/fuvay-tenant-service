"""Tenant Notification Center — backend workspace projection (Phase 1).

Audit found real, already-live infrastructure (event_registry, outbox,
in-app delivery, preferences) built in prior "NOTIFICATION-CENTER-REBUILD"
passes -- this extends it rather than building a second engine:
- category / action-required / critical / trusted-destination are derived
  from the REAL notification_type (= event_key) and severity fields,
  never fabricated for event keys with no live fire_event() caller.
- archive/unarchive reuse the READ_ARCHIVED read_status value that already
  existed in constants.py but had no service method using it.
- A real bug was found and fixed: _dispatch_outbox passed the delivery-
  status constant DELIVERY_PENDING ("pending") as the notification's
  SEVERITY, so every in-app notification ever created had severity=
  'pending' instead of its real info/success/warning/critical value from
  the event registry -- silently breaking any severity-based UI.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
PROJECTION = os.path.join(BASE, "app/engines/platform_notifications/workspace_projection.py")
SERVICE = os.path.join(BASE, "app/engines/platform_notifications/notification_service.py")
ROUTER = os.path.join(BASE, "app/engines/platform_notifications/provider_router.py")
EVENT_REGISTRY = os.path.join(BASE, "app/engines/platform_notifications/event_registry.py")
CONSTANTS = os.path.join(BASE, "app/engines/platform_notifications/constants.py")
COMPLAINT_SERVICE = os.path.join(BASE, "app/engines/complaints/complaint_service.py")
AI_SETTLEMENT_SERVICE = os.path.join(BASE, "app/engines/complaints/ai_settlement_service.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestCategoryAndActionMappingsAreReal:
    def test_every_category_prefix_corresponds_to_a_registered_event(self):
        proj = _read(PROJECTION)
        # Some event keys are registered via imported EVT_* constants (whose
        # literal string value lives in constants.py) rather than an inline
        # string literal in event_registry.py -- check both files.
        registry = _read(EVENT_REGISTRY) + _read(CONSTANTS)
        import re
        prefixes = re.findall(r'\("([a-z_]+\.)", "', proj)
        for prefix in prefixes:
            assert prefix.rstrip(".") in registry, f"category prefix {prefix!r} has no matching registered event"

    def test_every_action_required_key_has_a_real_source(self):
        """Each key must be traceable to an ACTUAL caller -- either the
        event_registry (fire_event path) or the complaints engine's
        hand-rolled notify_provider_complaint() calls (confirmed live: the
        complaints engine never routes provider-facing notifications
        through fire_event()/event_registry at all, using its own literal
        notification_type strings like "complaint.filed" instead of the
        registry's "complaint.created")."""
        proj = _read(PROJECTION)
        registry = _read(EVENT_REGISTRY) + _read(CONSTANTS)
        complaints = _read(COMPLAINT_SERVICE) + _read(AI_SETTLEMENT_SERVICE)
        import re
        start = proj.index("ACTION_REQUIRED_EVENT_KEYS = {")
        end = proj.index("}", start)
        keys = re.findall(r'"([a-z_.]+)"', proj[start:end])
        assert keys, "expected at least one action-required key"
        for key in keys:
            assert f'"{key}"' in registry or f'"{key}"' in complaints, \
                f"action-required key {key!r} not found in event_registry.py, constants.py, or complaints engine"

    def test_complaint_action_keys_match_the_real_hand_rolled_strings_not_the_registry(self):
        """Guards against reintroducing the exact bug this pass fixed: using
        event_registry.py's aspirational "complaint.created" instead of the
        real "complaint.filed" the complaints engine actually fires."""
        proj = _read(PROJECTION)
        start = proj.index("ACTION_REQUIRED_EVENT_KEYS = {")
        end = proj.index("}", start)
        block = proj[start:end]
        assert '"complaint.filed"' in block
        complaints = _read(COMPLAINT_SERVICE)
        assert 'notification_type="complaint.filed"' in complaints

    def test_documents_and_verification_category_uses_real_document_events(self):
        proj = _read(PROJECTION)
        assert '("document.", "Documents & verification")' in proj


class TestArchiveReusesExistingReadStatus:
    def test_archive_sets_read_archived_not_a_new_column(self):
        c = _read(SERVICE)
        start = c.index("async def archive_notification")
        end = c.index("async def unarchive_notification")
        block = c[start:end]
        assert "notif.read_status = READ_ARCHIVED" in block

    def test_default_inbox_excludes_archived(self):
        c = _read(SERVICE)
        assert "InAppNotification.read_status != READ_ARCHIVED" in c


class TestSeverityBugFixed:
    def test_dispatch_outbox_no_longer_hardcodes_delivery_pending_as_severity(self):
        c = _read(SERVICE)
        assert "severity=DELIVERY_PENDING" not in c

    def test_fire_event_path_threads_real_event_severity(self):
        c = _read(SERVICE)
        start = c.index("if pref_enabled:\n                await self._dispatch_outbox")
        block = c[start:start + 260]
        assert "event.severity" in block

    def test_retry_path_also_threads_real_severity(self):
        c = _read(SERVICE)
        assert "return event.vertical_key, event.is_mandatory, event.event_key, event.severity" in c
        assert "severity = await self._resolve_event_flags(db, outbox)" in c


class TestRouterStaticRoutesBeforeDynamic:
    def test_workspace_unread_count_and_preferences_registered_before_dynamic_id_route(self):
        c = _read(ROUTER)
        workspace_pos = c.index('@provider_notif_router.get("/workspace"')
        unread_pos = c.index('@provider_notif_router.get("/unread-count"')
        prefs_pos = c.index('@provider_notif_router.get("/preferences"')
        dynamic_pos = c.index('@provider_notif_router.get("/{notification_id}"')
        assert workspace_pos < dynamic_pos
        assert unread_pos < dynamic_pos
        assert prefs_pos < dynamic_pos

    def test_no_duplicate_route_definitions(self):
        c = _read(ROUTER)
        assert c.count('@provider_notif_router.get("/unread-count"') == 1
        assert c.count('@provider_notif_router.get("/preferences"') == 1

    def test_new_endpoints_present(self):
        c = _read(ROUTER)
        for path in ("/workspace", "/{notification_id}", "/{notification_id}/archive",
                     "/{notification_id}/unarchive", "/mark-read-bulk"):
            assert path in c


class TestTrustedDestinationMapping:
    def test_destination_is_a_frontend_route_not_the_stored_action_url(self):
        c = _read(PROJECTION)
        assert 'def resolve_destination' in c
        assert "TRUSTED_DESTINATIONS.get(notification_type)" in c

    def test_booking_new_maps_to_dispatch_board(self):
        c = _read(PROJECTION)
        assert '"booking.new": "/home-services/dispatch"' in c
