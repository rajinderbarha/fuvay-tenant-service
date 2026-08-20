"""P0 Category-Aware Navigation Sprint — Phase 1 increment.

Extends the existing vertical_catalog effective-menu resolver (already built by a
prior Multi-Vertical Catalog sprint — see test_p0_vertical_catalog_menu_fix.py)
with `operation_visibility` + `enabled_vertical_keys`, and wires AdminLayout.tsx
to hide Home-Services-only global nav items (Brands, Jobs/Field Ops, Security
Deposits, Credit Top-ups) when the backing vertical/operation is disabled —
fixing the literal complaint that these showed globally for every vertical.

Runs against the live dev server (same pattern as other P0 live-integration tests).
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
ADMIN_PASS = "Password123!"

SERVICE_FILE = os.path.join(os.path.dirname(__file__), "..", "app", "engines", "vertical_catalog", "service.py")
ADMIN_LAYOUT = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
API_TS = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin", "lib", "api.ts")


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


# ═════════════════════════════════════════════════════════════════════════════
# Static file checks
# ═════════════════════════════════════════════════════════════════════════════
class TestFiles:
    def test_service_defines_operation_rules(self):
        src = _read(SERVICE_FILE)
        assert "_OPERATION_VERTICAL_RULES" in src
        for key in ["jobs_field_ops", "site_visits", "orders", "leads_crm", "appointments",
                    "security_deposit", "usage_credits"]:
            assert f'"{key}"' in src

    def test_admin_layout_has_visibility_filter(self):
        src = _read(ADMIN_LAYOUT)
        assert "isNavItemVisible" in src
        assert '.filter(item => isNavItemVisible(item.id, effectiveMenu))' in src

    def test_admin_layout_gates_home_services_only_items(self):
        # NOTE: "brands"/"brand-requests" cases were removed by the later Sidebar
        # Duplicate Cleanup sprint (test_p0_sidebar_duplicate_cleanup.py) once those
        # items were dropped entirely from NAV_GROUPS in favor of the single
        # canonical Types & Brands entry — see that suite for the current assertions.
        src = _read(ADMIN_LAYOUT)
        assert "FIELD_OPS_SHARED_ITEMS" in src
        assert "FIELD_OPS_VERTICALS" in src
        assert "VerticalCatalogSection" in src

    def test_api_ts_has_operation_visibility_type(self):
        src = _read(API_TS)
        assert "operation_visibility" in src
        assert "enabled_vertical_keys" in src


# ═════════════════════════════════════════════════════════════════════════════
# Live resolver behavior
# ═════════════════════════════════════════════════════════════════════════════
class TestEffectiveMenuResolver:
    async def test_effective_menu_returns_operation_visibility(self, client):
        r = await client.get("/v1/admin/catalog/navigation/effective-menu")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert "operation_visibility" in d
        assert "enabled_vertical_keys" in d
        for key in ["jobs_field_ops", "site_visits", "orders", "leads_crm", "appointments",
                    "security_deposit", "usage_credits"]:
            assert key in d["operation_visibility"]

    async def test_coaching_vertical_has_no_home_services_modules(self, client):
        """Coaching must not show Brands/Issue Types/Service Options — the literal complaint."""
        r = await client.get("/v1/admin/catalog/navigation/effective-menu")
        d = r.json()["data"]
        coaching = next(v for v in d["verticals"] if v["vertical_key"] == "coaching")
        module_keys = {m["key"] for m in coaching["modules"]}
        assert "issue_types" not in module_keys
        assert "service_options" not in module_keys
        assert "courses" not in module_keys
        assert "batches" not in module_keys
        assert "categories" in module_keys

    async def test_disabling_real_estate_hides_site_visits_only(self, client):
        await client.post("/v1/admin/verticals/coaching/enable")
        await client.post("/v1/admin/verticals/professional_services/enable")
        r0 = await client.post("/v1/admin/verticals/real_estate/disable", json={"reason": "Navigation visibility regression test"})
        assert r0.status_code == 200, r0.text
        try:
            r = await client.get("/v1/admin/catalog/navigation/effective-menu")
            d = r.json()["data"]
            assert d["operation_visibility"]["site_visits"] is False
            # coaching + professional_services still enabled -> leads_crm/appointments stay visible
            assert d["operation_visibility"]["leads_crm"] is True
            assert d["operation_visibility"]["appointments"] is True
        finally:
            await client.post("/v1/admin/verticals/real_estate/enable")

    async def test_disabling_home_services_hides_finance_items(self, client):
        r0 = await client.post("/v1/admin/verticals/home_services/disable", json={"reason": "Navigation visibility regression test"})
        assert r0.status_code == 200, r0.text
        try:
            r = await client.get("/v1/admin/catalog/navigation/effective-menu")
            d = r.json()["data"]
            assert d["operation_visibility"]["security_deposit"] is False
            assert d["operation_visibility"]["usage_credits"] is False
            assert "home_services" not in d["enabled_vertical_keys"]
        finally:
            await client.post("/v1/admin/verticals/home_services/enable")

    async def test_restored_state_matches_original(self, client):
        r = await client.get("/v1/admin/catalog/navigation/effective-menu")
        d = r.json()["data"]
        assert d["operation_visibility"]["site_visits"] is True
        assert d["operation_visibility"]["security_deposit"] is True
        assert "home_services" in d["enabled_vertical_keys"]
        assert "real_estate" in d["enabled_vertical_keys"]
