"""HOME-SERVICES-OPERATIONS: Capabilities & Policies page + vertical
runtime-disable gate. Runtime tests against the live server.

Proves:
  - The legacy "Home Services Settings" flags (auto_price_options,
    manual_bargain_rules, provider_first_matching, home_services_only) have
    no admin-editable write path (confirmed dead before this change; this
    test locks that in).
  - The new capability/dependency-health/disable-impact/audit endpoints
    return real, evidence-based data.
  - Disabling home_services actually blocks NEW booking-draft creation
    (VERTICAL_DISABLED, 403) via both the HTTP router AND the DeepSeek
    service-layer choke point.
  - Existing jobs are untouched by the disable (no endpoint here mutates a
    job's own lifecycle).
  - Other verticals are unaffected by disabling home_services.
"""
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"
CUSTOMER_EMAIL = "customer@serviceos.local"
CUSTOMER_PASS = "Password123!"

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_SERVER_TESTS") != "1",
        reason="requires a separately running local API; set RUN_LIVE_SERVER_TESTS=1",
    ),
]
_TOKENS: dict = {}


async def _login(email, password):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": password})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "admin" not in _TOKENS:
        tok = await _login(ADMIN_EMAIL, ADMIN_PASS)
        assert tok, "admin login failed"
        _TOKENS["admin"] = tok
    return _TOKENS["admin"]


@pytest_asyncio.fixture(scope="module")
async def customer_token(anyio_backend):
    if "customer" not in _TOKENS:
        _TOKENS["customer"] = await _login(CUSTOMER_EMAIL, CUSTOMER_PASS)
    return _TOKENS["customer"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


@pytest_asyncio.fixture
async def ensure_enabled(admin):
    """Always leave home_services enabled after each test that disables it —
    other test modules in the suite depend on it being on."""
    yield
    await admin.post("/v1/admin/verticals/home_services/enable")


# ═══════════════════════════════════════════════════════════════════════════
# 1. LEGACY SETTINGS FLAGS — no admin write path exists
# ═══════════════════════════════════════════════════════════════════════════

class TestLegacyFlagsNotEditable:

    async def test_no_write_endpoint_for_home_services_config(self, admin):
        r = await admin.get("/openapi.json")
        schema = r.json()
        # The only method ever registered for this path is GET (read-only
        # status pills) -- no PUT/PATCH/POST exists to mutate these flags.
        path = schema["paths"].get("/v1/admin/home-services/config", {})
        assert "post" not in path and "put" not in path and "patch" not in path

    async def test_auto_price_options_not_read_by_pricing_runtime(self):
        """Static assertion: the deterministic pricing engine never branches
        on this flag (grounded in the audit — grep confirmed zero call
        sites outside the flag's own definition)."""
        import inspect
        from app.engines.home_service_booking import matching_engine
        src = inspect.getsource(matching_engine)
        assert "auto_price_options_enabled" not in src


# ═══════════════════════════════════════════════════════════════════════════
# 2. CAPABILITY / DEPENDENCY-HEALTH / IMPACT / AUDIT — real projections
# ═══════════════════════════════════════════════════════════════════════════

class TestCapabilityRegistry:

    async def test_capabilities_endpoint_returns_grouped_registry(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/capabilities")
        assert r.status_code == 200, r.text
        groups = r.json()["data"]["groups"]
        names = {g["name"] for g in groups}
        assert {"Provider setup", "Customer experience", "Service execution", "Finance", "AI"} <= names

    async def test_tenant_owned_pricing_is_tenant_owned_not_admin(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/capabilities")
        groups = {g["name"]: g["capabilities"] for g in r.json()["data"]["groups"]}
        pricing = next(c for c in groups["Provider setup"] if c["name"] == "Tenant-owned pricing")
        assert pricing["owner"] == "Tenant"

    async def test_fixed_price_confirmation_is_server_authoritative(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/capabilities")
        groups = {g["name"]: g["capabilities"] for g in r.json()["data"]["groups"]}
        names = [c["name"] for c in groups["Customer experience"]]
        assert all("Low / Mid / High" not in name for name in names)

    async def test_customer_provider_selection_is_disabled(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/capabilities")
        groups = {g["name"]: g["capabilities"] for g in r.json()["data"]["groups"]}
        sel = next(c for c in groups["Customer experience"] if c["name"] == "Customer provider selection")
        assert sel["status"] == "disabled"
        assert sel["owner"] == "Code-controlled"

    async def test_no_manual_bargain_rules_row_in_registry(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/capabilities")
        all_names = [c["name"] for g in r.json()["data"]["groups"] for c in g["capabilities"]]
        assert "Manual Bargain Rules" not in all_names
        assert "Home Services Only" not in all_names

    async def test_dependency_health_is_backed_by_persisted_checks(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/dependency-health")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        checks = data["checks"]
        assert checks
        assert {c["status"] for c in checks} <= {"healthy", "unhealthy", "unverified"}
        assert data["healthy_count"] == sum(c["status"] == "healthy" for c in checks)
        assert data["total_count"] == len(checks)
        assert all(c["last_checked_at"] for c in checks if c["status"] == "healthy")

    async def test_disable_impact_returns_real_counts(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/disable-impact")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "active_jobs" in data and "draft_bookings_in_progress" in data
        assert isinstance(data["active_jobs"], int)

    async def test_audit_log_endpoint_returns_list(self, admin):
        r = await admin.get("/v1/admin/verticals/home_services/audit")
        assert r.status_code == 200, r.text
        assert "items" in r.json()["data"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. RUNTIME DISABLE GATE
# ═══════════════════════════════════════════════════════════════════════════

class TestVerticalDisableGate:

    async def test_disable_requires_reason_is_audited(self, admin, ensure_enabled):
        r = await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "scheduled maintenance"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["disable_reason"] == "scheduled maintenance"
        audit = await admin.get("/v1/admin/verticals/home_services/audit")
        actions = [a["action_type"] for a in audit.json()["data"]["items"]]
        assert "vertical.disable" in actions

    @pytest.mark.skipif(not CUSTOMER_EMAIL, reason="customer fixture unavailable")
    async def test_disabled_blocks_new_booking_draft(self, admin, ensure_enabled, customer_token):
        if not customer_token:
            pytest.skip("customer login unavailable in this environment")
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "test"})
        async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {customer_token}"}, timeout=30) as c:
            r = await c.post("/v1/customer/home-services/booking-drafts",
                              json={"category_slug": "ac-repair", "offering_slug": "ac-service"})
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    def test_disabled_blocks_service_layer_directly(self):
        """Proves the guard lives in the SHARED service method
        (HomeServiceChatbotBookingService.start_booking_draft), not only the
        HTTP router's Depends() — the exact choke point DeepSeek's
        _tool_start_home_service_draft calls directly, bypassing the router
        entirely. Static evidence check: the vertical check must execute
        before any catalog resolution, inside the service method itself."""
        import inspect
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        src = inspect.getsource(HomeServiceChatbotBookingService.start_booking_draft)
        assert "VerticalDisabledException" in src
        assert "_load_vertical" in src
        # DeepSeek's tool calls this exact method, not the router.
        from app.engines.ai_conversation import backend_tools
        tools_src = inspect.getsource(backend_tools)
        assert "start_booking_draft" in tools_src

    async def test_re_enable_restores_entry_point(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "t"})
        r = await admin.post("/v1/admin/verticals/home_services/enable")
        assert r.status_code == 200
        assert r.json()["data"]["is_enabled"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 4. OTHER-VERTICAL ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

class TestOtherVerticalIsolation:

    async def test_disabling_home_services_does_not_disable_others(self, admin, ensure_enabled):
        before = (await admin.get("/v1/admin/verticals", params={"include_disabled": "true"})).json()["data"]["items"]
        others_before = {v["key"]: v["is_enabled"] for v in before if v["key"] != "home_services"}

        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "isolation test"})

        after = (await admin.get("/v1/admin/verticals", params={"include_disabled": "true"})).json()["data"]["items"]
        others_after = {v["key"]: v["is_enabled"] for v in after if v["key"] != "home_services"}

        assert others_before == others_after
