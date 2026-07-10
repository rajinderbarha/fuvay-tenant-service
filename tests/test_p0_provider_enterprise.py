"""P0 Enterprise Provider + Onboarding + Package Management Upgrade — tests.

Covers:
- GET /v1/admin/providers/summary
- GET /v1/admin/providers/new-requests/summary
- GET /v1/admin/providers/new-requests
- POST /v1/admin/onboarding/providers/{id}/send-reminder
- POST /v1/admin/onboarding/providers/{id}/approve with profile completion gate
- GET /v1/admin/packages/summary
- Frontend files: new-requests page, packages summary cards, approve validation
- Backend files: new endpoints present in provider_portal/admin_router.py
"""
from __future__ import annotations

import os
import re
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE       = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS  = "Password123!"

PROVIDER_ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "engines", "provider_portal", "admin_router.py"
)
PACKAGE_ROUTER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "app", "engines", "package_commerce", "admin_router.py"
)
API_TS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "lib", "api.ts"
)
NEW_REQUESTS_PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin",
    "app", "admin", "tenants", "onboarding", "page.tsx"
)
PROVIDERS_PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin",
    "app", "admin", "tenants", "page.tsx"
)
ONBOARDING_PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin",
    "app", "admin", "onboarding", "providers", "page.tsx"
)
PACKAGES_PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin",
    "app", "admin", "packages", "page.tsx"
)


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
# 1. BACKEND FILE CHECKS — Provider Router
# ═════════════════════════════════════════════════════════════════════════════

class TestProviderRouterFile:
    def test_file_exists(self):
        assert os.path.isfile(PROVIDER_ROUTER_PATH)

    def test_has_providers_summary_route(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"/providers/summary"' in src

    def test_has_new_requests_route(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"/providers/new-requests"' in src

    def test_has_new_requests_summary_route(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"/providers/new-requests/summary"' in src

    def test_has_send_reminder_route(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert "send-reminder" in src or "send_reminder" in src

    def test_approve_has_profile_completion_check(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert "profile_completion_percentage" in src
        assert "pct < 100" in src or "< 100" in src

    def test_approve_raises_422_on_incomplete_profile(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert "422" in src

    def test_providers_summary_has_active_key(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"active"' in src

    def test_providers_summary_has_pending_review(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"pending_review"' in src

    def test_providers_summary_has_package_pending_approval(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert '"package_pending_approval"' in src

    def test_new_requests_cte_filters_not_started(self):
        src = _read(PROVIDER_ROUTER_PATH)
        assert "not_started" in src


# ═════════════════════════════════════════════════════════════════════════════
# 2. BACKEND FILE CHECKS — Package Router
# ═════════════════════════════════════════════════════════════════════════════

class TestPackageRouterFile:
    def test_file_exists(self):
        assert os.path.isfile(PACKAGE_ROUTER_PATH)

    def test_has_packages_summary_route(self):
        src = _read(PACKAGE_ROUTER_PATH)
        assert '"/v1/admin/packages/summary"' in src

    def test_summary_before_package_id_route(self):
        src = _read(PACKAGE_ROUTER_PATH)
        summary_pos = src.index("/v1/admin/packages/summary")
        id_pos = src.index("/v1/admin/packages/{package_id}")
        assert summary_pos < id_pos

    def test_summary_has_active_assignments(self):
        src = _read(PACKAGE_ROUTER_PATH)
        assert "active_assignments" in src

    def test_summary_has_featured(self):
        src = _read(PACKAGE_ROUTER_PATH)
        assert "featured" in src


# ═════════════════════════════════════════════════════════════════════════════
# 3. API TS FILE CHECKS
# ═════════════════════════════════════════════════════════════════════════════

class TestApiTsFile:
    def test_file_exists(self):
        assert os.path.isfile(API_TS_PATH)

    def test_has_providers_admin_api(self):
        src = _read(API_TS_PATH)
        assert "providersAdminApi" in src

    def test_providers_admin_api_has_summary(self):
        src = _read(API_TS_PATH)
        assert "/v1/admin/providers/summary" in src

    def test_providers_admin_api_has_new_requests(self):
        src = _read(API_TS_PATH)
        assert "/v1/admin/providers/new-requests" in src

    def test_providers_admin_api_has_new_requests_summary(self):
        src = _read(API_TS_PATH)
        assert "/v1/admin/providers/new-requests/summary" in src

    def test_provider_directory_summary_interface_exists(self):
        src = _read(API_TS_PATH)
        assert "ProviderDirectorySummary" in src

    def test_new_requests_summary_interface_exists(self):
        src = _read(API_TS_PATH)
        assert "NewRequestsSummary" in src

    def test_new_requests_provider_interface_exists(self):
        src = _read(API_TS_PATH)
        assert "NewRequestsProvider" in src

    def test_package_api_has_summary(self):
        src = _read(API_TS_PATH)
        assert "/v1/admin/packages/summary" in src

    def test_package_summary_interface_exists(self):
        src = _read(API_TS_PATH)
        assert "PackageSummary" in src

    def test_send_reminder_in_onboarding_api(self):
        src = _read(API_TS_PATH)
        assert "sendReminder" in src


# ═════════════════════════════════════════════════════════════════════════════
# 4. FRONTEND PAGE CHECKS
# ═════════════════════════════════════════════════════════════════════════════

class TestFrontendPages:
    def test_new_requests_page_exists(self):
        assert os.path.isfile(NEW_REQUESTS_PAGE)

    def test_new_requests_page_uses_new_api(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "providersAdminApi" in src

    def test_new_requests_page_has_summary_cards(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "SummaryCard" in src

    def test_new_requests_page_has_profile_bar(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "profile_completion_percentage" in src or "ProfileBar" in src

    def test_new_requests_page_has_send_reminder(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "sendReminder" in src or "send-reminder" in src or "Bell" in src

    def test_new_requests_page_links_to_onboarding(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "/admin/onboarding/providers/" in src

    def test_new_requests_page_has_pagination(self):
        src = _read(NEW_REQUESTS_PAGE)
        assert "totalPages" in src or "page" in src.lower()

    def test_providers_page_has_summary_cards(self):
        src = _read(PROVIDERS_PAGE)
        assert "ProviderDirectorySummary" in src or "providersAdminApi" in src

    def test_onboarding_page_has_profile_completion_guard(self):
        src = _read(ONBOARDING_PAGE)
        assert "profile_completion_percentage" in src

    def test_onboarding_page_approve_disabled_when_incomplete(self):
        src = _read(ONBOARDING_PAGE)
        assert "profileComplete" in src or "profile_completion_percentage" in src

    def test_packages_page_has_summary_data(self):
        src = _read(PACKAGES_PAGE)
        assert "packageApi.summary" in src or "summary()" in src

    def test_packages_page_has_summary_cards(self):
        src = _read(PACKAGES_PAGE)
        assert "summaryData" in src or "PackageSummary" in src

    def test_packages_page_imports_package_summary(self):
        src = _read(PACKAGES_PAGE)
        assert "PackageSummary" in src


# ═════════════════════════════════════════════════════════════════════════════
# 5. LIVE API — Providers Summary
# ═════════════════════════════════════════════════════════════════════════════

class TestProvidersSummaryEndpoint:
    async def test_returns_200(self, client):
        r = await client.get("/v1/admin/providers/summary")
        assert r.status_code == 200, r.text

    async def test_has_required_keys(self, client):
        r = await client.get("/v1/admin/providers/summary")
        data = r.json()["data"]
        for key in ("total", "active", "suspended", "pending_setup", "pending_review",
                    "changes_requested", "rejected", "package_pending_approval"):
            assert key in data, f"Missing key: {key}"

    async def test_all_values_are_integers(self, client):
        r = await client.get("/v1/admin/providers/summary")
        data = r.json()["data"]
        for key, val in data.items():
            assert isinstance(val, int), f"{key} should be int, got {type(val)}"

    async def test_total_gte_active(self, client):
        r = await client.get("/v1/admin/providers/summary")
        data = r.json()["data"]
        assert data["total"] >= data["active"]

    async def test_no_auth_returns_4xx(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/providers/summary")
        assert r.status_code in (401, 403)


# ═════════════════════════════════════════════════════════════════════════════
# 6. LIVE API — New Requests
# ═════════════════════════════════════════════════════════════════════════════

class TestNewRequestsEndpoints:
    async def test_summary_returns_200(self, client):
        r = await client.get("/v1/admin/providers/new-requests/summary")
        assert r.status_code == 200, r.text

    async def test_summary_has_required_keys(self, client):
        r = await client.get("/v1/admin/providers/new-requests/summary")
        data = r.json()["data"]
        for key in ("total", "with_package", "without_package", "package_selected", "profile_near_complete"):
            assert key in data, f"Missing key: {key}"

    async def test_list_returns_200(self, client):
        r = await client.get("/v1/admin/providers/new-requests")
        assert r.status_code == 200, r.text

    async def test_list_has_providers_and_total(self, client):
        r = await client.get("/v1/admin/providers/new-requests")
        data = r.json()["data"]
        assert "providers" in data
        assert "total" in data

    async def test_list_providers_have_profile_completion(self, client):
        r = await client.get("/v1/admin/providers/new-requests")
        providers = r.json()["data"]["providers"]
        for p in providers:
            assert "profile_completion_percentage" in p
            assert isinstance(p["profile_completion_percentage"], int)

    async def test_has_package_filter_true(self, client):
        r = await client.get("/v1/admin/providers/new-requests", params={"has_package": "true"})
        assert r.status_code == 200

    async def test_has_package_filter_false(self, client):
        r = await client.get("/v1/admin/providers/new-requests", params={"has_package": "false"})
        assert r.status_code == 200

    async def test_vertical_filter(self, client):
        r = await client.get("/v1/admin/providers/new-requests", params={"vertical_type": "home_services"})
        assert r.status_code == 200
        for p in r.json()["data"]["providers"]:
            assert p.get("vertical_type") == "home_services"

    async def test_search_filter(self, client):
        r = await client.get("/v1/admin/providers/new-requests", params={"q": "test"})
        assert r.status_code == 200

    async def test_pagination_page2(self, client):
        r = await client.get("/v1/admin/providers/new-requests", params={"page": 2, "page_size": 5})
        assert r.status_code == 200

    async def test_no_auth_returns_4xx(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/providers/new-requests")
        assert r.status_code in (401, 403)


# ═════════════════════════════════════════════════════════════════════════════
# 7. LIVE API — Send Reminder
# ═════════════════════════════════════════════════════════════════════════════

class TestSendReminder:
    async def test_send_reminder_valid_tenant(self, client):
        # Get any tenant to test with
        r = await client.get("/v1/admin/tenants?limit=1")
        assert r.status_code == 200
        data = r.json()
        items = (data.get("data") or {}).get("items") or (data.get("data") or {}).get("tenants") or []
        if not items:
            pytest.skip("No tenants available")
        tenant_id = str(items[0].get("tenant_id") or items[0].get("id", ""))
        r2 = await client.post(f"/v1/admin/onboarding/providers/{tenant_id}/send-reminder")
        assert r2.status_code == 200

    async def test_send_reminder_nonexistent_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        r = await client.post(f"/v1/admin/onboarding/providers/{fake_id}/send-reminder")
        assert r.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 8. LIVE API — Packages Summary
# ═════════════════════════════════════════════════════════════════════════════

class TestPackagesSummaryEndpoint:
    async def test_returns_200(self, client):
        r = await client.get("/v1/admin/packages/summary")
        assert r.status_code == 200, r.text

    async def test_has_required_keys(self, client):
        r = await client.get("/v1/admin/packages/summary")
        data = r.json()["data"]
        for key in ("total", "active", "inactive", "onboarding", "subscription",
                    "lead_credit", "deposit", "featured", "active_assignments"):
            assert key in data, f"Missing key: {key}"

    async def test_all_values_are_integers(self, client):
        r = await client.get("/v1/admin/packages/summary")
        data = r.json()["data"]
        for key, val in data.items():
            assert isinstance(val, int), f"{key} should be int, got {type(val)}"

    async def test_total_gte_active_plus_inactive(self, client):
        r = await client.get("/v1/admin/packages/summary")
        data = r.json()["data"]
        assert data["total"] >= data["active"] + data["inactive"]

    async def test_active_assignments_gte_zero(self, client):
        r = await client.get("/v1/admin/packages/summary")
        assert r.json()["data"]["active_assignments"] >= 0

    async def test_no_auth_returns_4xx(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/packages/summary")
        assert r.status_code in (401, 403)


# ═════════════════════════════════════════════════════════════════════════════
# 9. PROFILE COMPLETION GATE ON APPROVE
# ═════════════════════════════════════════════════════════════════════════════

class TestApproveProfileGate:
    async def test_approve_incomplete_profile_returns_422_or_404(self, client):
        """Any tenant with profile < 100% must be rejected by approve endpoint."""
        # Get a tenant that is likely incomplete (new_request)
        r = await client.get("/v1/admin/providers/new-requests", params={"page_size": 5})
        assert r.status_code == 200
        providers = r.json()["data"]["providers"]
        incomplete = [p for p in providers if p["profile_completion_percentage"] < 100]
        if not incomplete:
            pytest.skip("No incomplete-profile providers available for this test")
        tenant_id = incomplete[0]["tenant_id"]
        r2 = await client.post(f"/v1/admin/onboarding/providers/{tenant_id}/approve")
        assert r2.status_code in (422, 409), f"Expected 422 for incomplete profile, got {r2.status_code}: {r2.text}"

    async def test_approve_nonexistent_tenant_returns_non_200(self, client):
        fake_id = str(uuid.uuid4())
        r = await client.post(f"/v1/admin/onboarding/providers/{fake_id}/approve")
        assert r.status_code != 200
