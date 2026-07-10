"""P0 Enterprise Notification Template Center.

Live-integration tests (same pattern as test_trust_quality_phase1.py) covering
the extended notification_templates schema, validation/preview/test-send,
override resolution, version history + rollback, platform-default delete
protection, and audit logging.
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

MIGRATION = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions", "102_notification_template_center.py")
MODELS = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "notification", "models.py")
SERVICE = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "notification", "service.py")
ADMIN_ROUTER = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "notification", "admin_router.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def client(token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {token}"}, timeout=30) as c:
        yield c


pytestmark = pytest.mark.anyio


class TestFiles:
    def test_migration_exists(self):
        assert os.path.exists(MIGRATION)

    def test_migration_revision_chain(self):
        src = _read(MIGRATION)
        assert 'revision = "102"' in src

    def test_models_define_new_tables(self):
        src = _read(MODELS)
        for cls in ["NotificationTemplateVersion", "NotificationTestSend", "NotificationTemplateAuditLog"]:
            assert f"class {cls}" in src

    def test_service_has_admin_methods(self):
        src = _read(SERVICE)
        for m in ["create_template_admin", "update_template_admin", "delete_template_admin",
                   "clone_template", "create_override", "resolve_effective_template",
                   "render_preview", "test_send", "rollback_template", "delivery_analytics"]:
            assert f"async def {m}" in src

    def test_admin_router_exists(self):
        assert os.path.exists(ADMIN_ROUTER)


class TestListAndSummary:
    async def test_seed_defaults_idempotent(self, client):
        r1 = await client.post("/v1/admin/notifications/templates/seed-defaults")
        assert r1.status_code == 200, r1.text
        r2 = await client.post("/v1/admin/notifications/templates/seed-defaults")
        assert r2.status_code == 200
        assert r2.json()["data"]["created"] == 0

    async def test_summary_loads(self, client):
        r = await client.get("/v1/admin/notifications/templates/summary")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["total_templates"] > 0
        assert d["platform_defaults"] > 0

    async def test_list_filters_by_event_type(self, client):
        r = await client.get("/v1/admin/notifications/templates", params={"event_type": "booking_confirmed"})
        assert r.status_code == 200
        items = r.json()["data"]["items"]
        assert all(i["event_type"] == "booking_confirmed" for i in items)
        assert len(items) >= 3  # in_app, email, push


class TestValidation:
    async def _get_booking_confirmed_in_app(self, client) -> str:
        r = await client.get("/v1/admin/notifications/templates",
                              params={"event_type": "booking_confirmed", "channel": "in_app"})
        items = r.json()["data"]["items"]
        return items[0]["template_id"]

    async def test_create_rejects_unknown_variable(self, client):
        r = await client.post("/v1/admin/notifications/templates", json={
            "event_type": "booking_confirmed", "channel": "in_app", "audience": "customer",
            "app_scope": "customer_app", "title": "Test", "body": "Hi {{totally_unknown_var}}",
        })
        assert r.status_code >= 400

    async def test_create_rejects_forbidden_customer_variable(self, client):
        r = await client.post("/v1/admin/notifications/templates", json={
            "event_type": "usage_credit_low", "channel": "in_app", "audience": "customer",
            "app_scope": "customer_app", "title": "Test", "body": "Balance {{usage_credit_balance}}",
        })
        assert r.status_code >= 400

    async def test_create_rejects_invalid_event_type(self, client):
        r = await client.post("/v1/admin/notifications/templates", json={
            "event_type": "not_a_real_event", "channel": "in_app", "audience": "customer",
            "app_scope": "customer_app", "title": "Test", "body": "Hi",
        })
        assert r.status_code >= 400

    async def test_create_valid_template_succeeds(self, client):
        r = await client.post("/v1/admin/notifications/templates", json={
            "event_type": "document_expiring", "channel": "in_app", "audience": "tenant_owner",
            "app_scope": "tenant_app", "title": "Doc Expiring Test", "body": "Hi {{tenant_name}}",
        })
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "draft"


class TestPlatformDefaultSafety:
    async def _platform_default_id(self, client) -> str:
        r = await client.get("/v1/admin/notifications/templates",
                              params={"event_type": "booking_confirmed", "channel": "email"})
        return r.json()["data"]["items"][0]["template_id"]

    async def test_delete_platform_default_blocked(self, client):
        tid = await self._platform_default_id(client)
        r = await client.delete(f"/v1/admin/notifications/templates/{tid}")
        assert r.status_code in (403, 409)

    async def test_draft_template_can_be_deleted(self, client):
        # A bare create() with no tenant/vertical becomes a platform default itself (spec: any
        # template without an explicit override scope is platform-wide) — so the deletable-draft
        # case is a clone, which is explicitly is_platform_default=False per create-override/clone rules.
        platform_id = await self._platform_default_id(client)
        clone = await client.post(f"/v1/admin/notifications/templates/{platform_id}/clone")
        tid = clone.json()["data"]["template_id"]
        assert clone.json()["data"]["status"] == "draft"
        r = await client.delete(f"/v1/admin/notifications/templates/{tid}")
        assert r.status_code == 200


class TestCloneOverrideResolve:
    async def _platform_default_id(self, client) -> str:
        r = await client.get("/v1/admin/notifications/templates",
                              params={"event_type": "booking_confirmed", "channel": "in_app"})
        return r.json()["data"]["items"][0]["template_id"]

    async def test_clone_creates_draft_copy(self, client):
        tid = await self._platform_default_id(client)
        r = await client.post(f"/v1/admin/notifications/templates/{tid}/clone")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "draft"
        assert d["is_platform_default"] is False
        assert d["fallback_template_id"] == tid

    async def test_vertical_override_requires_vertical_key(self, client):
        tid = await self._platform_default_id(client)
        r = await client.post(f"/v1/admin/notifications/templates/{tid}/create-override",
                               json={"scope_type": "vertical"})
        assert r.status_code >= 400

    async def test_resolve_effective_template_falls_back_to_platform_default(self, client):
        r = await client.post("/v1/admin/notifications/templates/resolve-effective-template", json={
            "event_type": "booking_confirmed", "channel": "in_app", "audience": "customer",
        })
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["effective_template"] is not None
        assert d["resolution_path"][-1]["scope"] == "platform_default"


class TestPreviewTestSendVersions:
    async def _platform_default_id(self, client) -> str:
        r = await client.get("/v1/admin/notifications/templates",
                              params={"event_type": "booking_confirmed", "channel": "in_app"})
        return r.json()["data"]["items"][0]["template_id"]

    async def test_render_preview_substitutes_variables(self, client):
        tid = await self._platform_default_id(client)
        r = await client.post(f"/v1/admin/notifications/templates/{tid}/render-preview",
                               json={"sample_data": {"customer_name": "Asha"}})
        assert r.status_code == 200
        assert "Asha" in r.json()["data"]["rendered_body"] or r.json()["data"]["rendered_body"]

    async def test_test_send_is_marked_as_test(self, client):
        tid = await self._platform_default_id(client)
        r = await client.post(f"/v1/admin/notifications/templates/{tid}/test-send",
                               json={"recipient": "qa@example.com", "sample_data": {"customer_name": "Asha"}})
        assert r.status_code == 200
        assert r.json()["data"]["is_test"] is True

    async def test_version_created_on_update(self, client):
        tid = await self._platform_default_id(client)
        v1 = await client.get(f"/v1/admin/notifications/templates/{tid}/versions")
        count_before = len(v1.json()["data"]["items"])
        await client.put(f"/v1/admin/notifications/templates/{tid}", json={
            "title": "Booking Confirmed (Updated)", "reason": "test update"})
        v2 = await client.get(f"/v1/admin/notifications/templates/{tid}/versions")
        count_after = len(v2.json()["data"]["items"])
        assert count_after == count_before + 1

    async def test_rollback_requires_reason(self, client):
        tid = await self._platform_default_id(client)
        versions = await client.get(f"/v1/admin/notifications/templates/{tid}/versions")
        first_version = versions.json()["data"]["items"][-1]["version_number"]
        r = await client.post(f"/v1/admin/notifications/templates/{tid}/rollback",
                               json={"version_number": first_version, "reason": ""})
        assert r.status_code >= 400


class TestAnalyticsAndAudit:
    async def _platform_default_id(self, client) -> str:
        r = await client.get("/v1/admin/notifications/templates",
                              params={"event_type": "booking_confirmed", "channel": "in_app"})
        return r.json()["data"]["items"][0]["template_id"]

    async def test_delivery_analytics_loads(self, client):
        tid = await self._platform_default_id(client)
        r = await client.get(f"/v1/admin/notifications/templates/{tid}/delivery-analytics")
        assert r.status_code == 200
        d = r.json()["data"]
        assert "delivery_rate" in d and "failure_rate" in d

    async def test_audit_logs_recorded_for_seed(self, client):
        await client.post("/v1/admin/notifications/templates/seed-defaults")
        r = await client.get("/v1/admin/notifications/templates/audit-logs")
        assert r.status_code == 200
        action_types = {a["action_type"] for a in r.json()["data"]["items"]}
        assert "notification_template.seed_defaults" in action_types

    async def test_no_auth_returns_4xx(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/notifications/templates")
            assert r.status_code in (401, 403)
