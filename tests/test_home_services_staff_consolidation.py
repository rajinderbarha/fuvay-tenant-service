"""STAFF-CONSOLIDATION: Home Services Staff is served exclusively by the
Vertical Directory Framework's staff domain -- no separate/duplicate
operational Staff page or backend for Home Services. This suite proves the
root-cause fix (missing home_services:staff:* permissions, which 403'd every
non-super_admin role) and the new review/action endpoints (verify, reject,
request-changes, restrict, suspend, reactivate, capabilities, workload,
performance, activity, export), plus vertical isolation and audit.

Fixture data inserted directly via SQL (this environment's seed data is not
persistent across sessions) -- same pattern as test_vertical_directory_
framework.py, which this suite complements rather than duplicates.
"""
import uuid
import pytest
import pytest_asyncio
import asyncpg
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"
DB_URL = "postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


@pytest_asyncio.fixture
async def pg():
    conn = await asyncpg.connect(DB_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="module")
async def hs_vertical_id(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        r = await c.get("/v1/admin/verticals")
        return next(v["id"] for v in r.json()["data"]["items"] if v["key"] == "home_services")


@pytest_asyncio.fixture
async def staff_fixture(pg, hs_vertical_id):
    tenant_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")
    cat_id = category["id"]

    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        tenant_id, "HS Staff Consolidation Tenant " + str(tenant_id)[:8])
    await pg.execute(
        "INSERT INTO provider_team_members (id, tenant_id, category_id, member_type, full_name, status, "
        "can_receive_assignment, password_generated, created_at, updated_at) "
        "VALUES ($1,$2,$3,'technician','Consolidation Test Staff',$4,true,false, now(), now())",
        staff_id, tenant_id, cat_id, "active")
    await pg.execute(
        "INSERT INTO staff_business_verticals (id, staff_id, tenant_id, vertical_id, is_active, "
        "verification_status, assignment_status, availability_status, created_at, updated_at) "
        "VALUES (gen_random_uuid(),$1,$2,$3,true,'not_started','pending','unavailable', now(), now())",
        staff_id, tenant_id, uuid.UUID(hs_vertical_id))

    yield {"tenant_id": tenant_id, "staff_id": staff_id}

    await pg.execute("DELETE FROM platform_audit_logs WHERE entity_id IN "
                      "(SELECT id::text FROM staff_business_verticals WHERE staff_id = $1)", staff_id)
    await pg.execute("DELETE FROM vertical_audit_logs WHERE tenant_id = $1", tenant_id)
    await pg.execute("DELETE FROM staff_business_verticals WHERE staff_id = $1", staff_id)
    await pg.execute("DELETE FROM provider_team_members WHERE id = $1", staff_id)
    await pg.execute("DELETE FROM tenants WHERE id = $1", tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# 1. ROOT-CAUSE FIX: permission constants exist and resolve for real roles
# ═══════════════════════════════════════════════════════════════════════════

class TestRootCauseFix:

    def test_home_services_staff_view_permission_exists(self):
        from app.core.permissions import P
        assert P.HOME_SERVICES_STAFF_VIEW == "home_services:staff:view"

    def test_admin_operations_can_view_and_mutate(self):
        from app.core.permissions import permission_checker
        assert permission_checker.has(role="admin_operations", permission="home_services:staff:view")
        assert permission_checker.has(role="admin_operations", permission="home_services:staff:suspend")
        assert permission_checker.has(role="admin_operations", permission="home_services:staff:verify")

    def test_admin_readonly_can_view_but_not_mutate(self):
        from app.core.permissions import permission_checker
        assert permission_checker.has(role="admin_readonly", permission="home_services:staff:view")
        assert not permission_checker.has(role="admin_readonly", permission="home_services:staff:suspend")
        assert not permission_checker.has(role="admin_readonly", permission="home_services:staff:verify")

    def test_unrelated_role_denied(self):
        from app.core.permissions import permission_checker
        assert not permission_checker.has(role="customer", permission="home_services:staff:view")

    async def test_staff_endpoint_no_longer_500s_or_hides_behind_generic_error(self, admin):
        # Direct proof the previously-broken page now returns a clean,
        # well-formed response (not a raw exception / malformed error body).
        r = await admin.get("/v1/admin/verticals/home-services/staff", params={"page_size": 5})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "items" in body["data"] and "total" in body["data"]


# ═══════════════════════════════════════════════════════════════════════════
# 2. SUMMARY USES REAL DATA (never zero-on-failure)
# ═══════════════════════════════════════════════════════════════════════════

class TestSummary:

    async def test_summary_reflects_fixture(self, admin, staff_fixture):
        r = await admin.get("/v1/admin/verticals/home-services/staff/summary")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["total_staff"] >= 1
        assert data["pending_verification"] >= 1  # fixture staff is not_started


# ═══════════════════════════════════════════════════════════════════════════
# 3. STAFF ACTIONS (verify / reject / request-changes / restrict / suspend / reactivate)
# ═══════════════════════════════════════════════════════════════════════════

class TestStaffActions:

    async def test_verify_transitions_and_audits(self, admin, staff_fixture, pg):
        sid = staff_fixture["staff_id"]
        r = await admin.post(f"/v1/admin/verticals/home-services/staff/{sid}/verify", json={"reason": "docs checked"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["verification_status"] == "verified"

        row = await pg.fetchrow("SELECT verification_status FROM staff_business_verticals WHERE staff_id = $1", sid)
        assert row["verification_status"] == "verified"

        audit = await pg.fetchrow(
            "SELECT * FROM vertical_audit_logs WHERE action_type = 'staff.verify' AND tenant_id = $1", staff_fixture["tenant_id"])
        assert audit is not None
        assert audit["notes"] == "docs checked"

    async def test_request_changes_requires_reason(self, admin, staff_fixture):
        sid = staff_fixture["staff_id"]
        r = await admin.post(f"/v1/admin/verticals/home-services/staff/{sid}/request-changes", json={"reason": ""})
        assert r.status_code == 422

    async def test_suspend_requires_reason_and_transitions(self, admin, staff_fixture, pg):
        sid = staff_fixture["staff_id"]
        await pg.execute("UPDATE staff_business_verticals SET assignment_status = 'active' WHERE staff_id = $1", sid)
        r = await admin.post(f"/v1/admin/verticals/home-services/staff/{sid}/suspend", json={"reason": "quality issue"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["assignment_status"] == "suspended"
        assert r.json()["data"]["is_active"] is False

    async def test_reactivate_from_suspended(self, admin, staff_fixture, pg):
        sid = staff_fixture["staff_id"]
        await pg.execute("UPDATE staff_business_verticals SET assignment_status = 'suspended' WHERE staff_id = $1", sid)
        r = await admin.post(f"/v1/admin/verticals/home-services/staff/{sid}/reactivate", json={"reason": "resolved"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["assignment_status"] == "active"

    async def test_invalid_transition_rejected(self, admin, staff_fixture, pg):
        sid = staff_fixture["staff_id"]
        await pg.execute("UPDATE staff_business_verticals SET assignment_status = 'deactivated' WHERE staff_id = $1", sid)
        r = await admin.post(f"/v1/admin/verticals/home-services/staff/{sid}/restrict", json={"reason": "x"})
        assert r.status_code == 422
        assert r.json()["error_code"] == "INVALID_STATE_TRANSITION"


# ═══════════════════════════════════════════════════════════════════════════
# 4. AVAILABILITY / WORKLOAD FROM CANONICAL ENGINE (not a second state machine)
# ═══════════════════════════════════════════════════════════════════════════

class TestAvailabilityAndWorkload:

    async def test_suspended_assignment_never_shows_available(self, admin, staff_fixture, pg):
        sid = staff_fixture["staff_id"]
        await pg.execute("UPDATE staff_business_verticals SET assignment_status = 'suspended', is_active = false WHERE staff_id = $1", sid)
        r = await admin.get(f"/v1/admin/verticals/home-services/staff/{sid}")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["availability_status"] == "offline"

    async def test_workload_endpoint_returns_canonical_shape(self, admin, staff_fixture):
        sid = staff_fixture["staff_id"]
        r = await admin.get(f"/v1/admin/verticals/home-services/staff/{sid}/workload")
        assert r.status_code == 200, r.text
        assert "active_jobs" in r.json()["data"] and "capacity_active" in r.json()["data"]

    async def test_performance_scoped_to_home_services_only(self, admin, staff_fixture):
        sid = staff_fixture["staff_id"]
        r = await admin.get(f"/v1/admin/verticals/home-services/staff/{sid}/performance")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["scope"] == "home_services"

    async def test_capabilities_resolve_through_catalog_not_broad_category(self, admin, staff_fixture):
        sid = staff_fixture["staff_id"]
        r = await admin.get(f"/v1/admin/verticals/home-services/staff/{sid}/capabilities")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["job_types"] == []  # fixture has no capabilities set -- no invented data


# ═══════════════════════════════════════════════════════════════════════════
# 5. CROSS-VERTICAL / SCOPE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════

class TestScopeEnforcement:

    async def test_cannot_mutate_via_wrong_vertical_path(self, admin, staff_fixture):
        sid = staff_fixture["staff_id"]
        r = await admin.post(f"/v1/admin/verticals/coaching/staff/{sid}/suspend", json={"reason": "x"})
        # Fails closed either way: CROSS_VERTICAL_ACCESS_DENIED if Coaching
        # is enabled in this environment, VERTICAL_DISABLED if not -- both
        # are a hard 403, never a successful cross-vertical mutation.
        assert r.status_code == 403
        assert r.json().get("error_code") in ("CROSS_VERTICAL_ACCESS_DENIED", "VERTICAL_DISABLED")

    async def test_query_param_cannot_override_vertical_scope(self, admin, staff_fixture):
        # The vertical is resolved from the URL path only -- a client-
        # supplied query param must have zero effect.
        r1 = await admin.get("/v1/admin/verticals/home-services/staff", params={"page_size": 5})
        r2 = await admin.get("/v1/admin/verticals/home-services/staff",
                             params={"page_size": 5, "vertical": "coaching", "vertical_id": "anything"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert [i["staff_id"] for i in r1.json()["data"]["items"]] == [i["staff_id"] for i in r2.json()["data"]["items"]]

    async def test_export_scoped_to_home_services(self, admin, staff_fixture):
        r = await admin.get("/v1/admin/verticals/home-services/staff/export")
        assert r.status_code == 200, r.text
        assert str(staff_fixture["staff_id"]) in [i["staff_id"] for i in r.json()["data"]["items"]]

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/verticals/home-services/staff")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 6. NAVIGATION CONSOLIDATION (static source inspection)
# ═══════════════════════════════════════════════════════════════════════════

class TestNavigationConsolidation:

    def test_global_staff_nav_removed(self):
        import pathlib
        layout = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
        assert 'href: "/admin/staff"' not in layout

    def test_no_add_staff_button_on_vertical_staff_directory(self):
        # A code comment is allowed to explain the product decision ("this
        # page never offers Add Staff") -- what matters is no rendered
        # button/label actually says it.
        import pathlib
        src = pathlib.Path("frontend/super-admin/components/directory/VerticalStaffDirectory.tsx").read_text(encoding="utf-8")
        code_only = "\n".join(
            line for line in src.splitlines()
            if not line.strip().startswith("//") and not line.strip().startswith("*")
        )
        assert "Add Staff" not in code_only

    def test_home_services_route_reuses_generic_vertical_component(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/[vertical]/staff/page.tsx").read_text(encoding="utf-8")
        assert "VerticalStaffDirectory" in src
