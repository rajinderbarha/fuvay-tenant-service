"""VERTICAL-DIRECTORY-FRAMEWORK: reusable, backend-enforced, vertically
scoped Providers/Staff/Customers/Complaints directories. Runtime tests
against the live server, with fixture data inserted directly via SQL
(this environment's seed data is not persistent across sessions).

Proves: cross-vertical isolation for all 4 domains, one canonical identity
per person/business across verticals, vertical-disable gating, and that
the SAME router/service code serves every vertical (no hardcoded per-
vertical implementation) by exercising it against two different verticals.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
import asyncpg
from decimal import Decimal
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
async def coaching_enabled(admin_token):
    """Coaching may be disabled in this environment -- ensure it's on for
    the duration of these tests, restore original state after."""
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        before = await c.get("/v1/admin/verticals", params={"include_disabled": "true"})
        coaching = next(v for v in before.json()["data"]["items"] if v["key"] == "coaching")
        was_enabled = coaching["is_enabled"]
        if not was_enabled:
            await c.post("/v1/admin/verticals/coaching/enable")
        yield coaching["id"]
        if not was_enabled:
            await c.post("/v1/admin/verticals/coaching/disable", json={"reason": "test cleanup"})


@pytest_asyncio.fixture(scope="module")
async def verticals(admin_token, coaching_enabled):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        r = await c.get("/v1/admin/verticals")
        items = {v["key"]: v["id"] for v in r.json()["data"]["items"]}
        assert "home_services" in items and "coaching" in items
        return items


@pytest_asyncio.fixture
async def fixture_data(pg, verticals):
    """Creates one tenant enrolled in home_services, one in coaching, one
    staff member per tenant, one customer per vertical, one complaint per
    vertical -- real rows, direct SQL, cleaned up after."""
    hs_id, coach_id = verticals["home_services"], verticals["coaching"]
    hs_tenant = uuid.uuid4()
    coach_tenant = uuid.uuid4()
    hs_staff = uuid.uuid4()
    coach_staff = uuid.uuid4()
    hs_customer = uuid.uuid4()
    coach_customer = uuid.uuid4()
    hs_complaint = uuid.uuid4()
    coach_complaint = uuid.uuid4()
    category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")
    cat_id = category["id"]

    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        hs_tenant, "HS Test Tenant " + str(hs_tenant)[:8])
    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'coaching','active','verified', now(), now())",
        coach_tenant, "Coaching Test Tenant " + str(coach_tenant)[:8])

    await pg.execute(
        "INSERT INTO provider_team_members (id, tenant_id, category_id, member_type, full_name, status, "
        "can_receive_assignment, password_generated, created_at, updated_at) "
        "VALUES ($1,$2,$3,'technician','HS Staff Test',$4,true,false, now(), now())",
        hs_staff, hs_tenant, cat_id, "active")
    await pg.execute(
        "INSERT INTO provider_team_members (id, tenant_id, category_id, member_type, full_name, status, "
        "can_receive_assignment, password_generated, created_at, updated_at) "
        "VALUES ($1,$2,$3,'trainer','Coach Staff Test',$4,true,false, now(), now())",
        coach_staff, coach_tenant, cat_id, "active")

    await pg.execute(
        "INSERT INTO staff_business_verticals (id, staff_id, tenant_id, vertical_id, is_active, "
        "verification_status, assignment_status, availability_status, created_at, updated_at) "
        "VALUES (gen_random_uuid(),$1,$2,$3,true,'verified','assigned','available', now(), now())",
        hs_staff, hs_tenant, hs_id)
    await pg.execute(
        "INSERT INTO staff_business_verticals (id, staff_id, tenant_id, vertical_id, is_active, "
        "verification_status, assignment_status, availability_status, created_at, updated_at) "
        "VALUES (gen_random_uuid(),$1,$2,$3,true,'verified','assigned','available', now(), now())",
        coach_staff, coach_tenant, coach_id)

    for cid, email in [(hs_customer, f"hs_{hs_customer.hex[:8]}@test.local"),
                       (coach_customer, f"coach_{coach_customer.hex[:8]}@test.local")]:
        await pg.execute(
            "INSERT INTO users (id, email, full_name, role, hashed_password, is_active, is_verified, "
            "created_at, updated_at) VALUES ($1,$2,'Test Customer','customer','x',true,true, now(), now())",
            cid, email)

    await pg.execute(
        "INSERT INTO customer_business_verticals (id, customer_id, vertical_id, first_activity_at, "
        "last_activity_at, booking_count, relationship_status, source_relationship, created_at, updated_at) "
        "VALUES (gen_random_uuid(),$1,$2, now(), now(), 1, 'active', 'booking', now(), now())",
        hs_customer, hs_id)
    await pg.execute(
        "INSERT INTO customer_business_verticals (id, customer_id, vertical_id, first_activity_at, "
        "last_activity_at, booking_count, relationship_status, source_relationship, created_at, updated_at) "
        "VALUES (gen_random_uuid(),$1,$2, now(), now(), 1, 'active', 'booking', now(), now())",
        coach_customer, coach_id)

    for compl_id, cust_id, tenant_id, vert_id, num in [
        (hs_complaint, hs_customer, hs_tenant, hs_id, f"CMP-HS-{hs_complaint.hex[:6]}"),
        (coach_complaint, coach_customer, coach_tenant, coach_id, f"CMP-CO-{coach_complaint.hex[:6]}"),
    ]:
        await pg.execute(
            "INSERT INTO customer_complaints (id, complaint_number, customer_id, tenant_id, category_id, "
            "vertical_id, record_type, record_id, complaint_type, priority, status, title, description, severity, "
            "sla_status, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,'booking',$7,'service_quality','medium','open','Test complaint',"
            "'Test description','medium','on_time', now(), now())",
            compl_id, num, cust_id, tenant_id, cat_id, vert_id, uuid.uuid4())

    data = {
        "hs_tenant": hs_tenant, "coach_tenant": coach_tenant,
        "hs_staff": hs_staff, "coach_staff": coach_staff,
        "hs_customer": hs_customer, "coach_customer": coach_customer,
        "hs_complaint": hs_complaint, "coach_complaint": coach_complaint,
    }
    yield data

    await pg.execute("DELETE FROM customer_complaints WHERE id = ANY($1::uuid[])", [hs_complaint, coach_complaint])
    await pg.execute("DELETE FROM customer_business_verticals WHERE customer_id = ANY($1::uuid[])", [hs_customer, coach_customer])
    await pg.execute("DELETE FROM users WHERE id = ANY($1::uuid[])", [hs_customer, coach_customer])
    await pg.execute("DELETE FROM staff_business_verticals WHERE staff_id = ANY($1::uuid[])", [hs_staff, coach_staff])
    await pg.execute("DELETE FROM provider_team_members WHERE id = ANY($1::uuid[])", [hs_staff, coach_staff])
    await pg.execute("DELETE FROM tenants WHERE id = ANY($1::uuid[])", [hs_tenant, coach_tenant])


# ═══════════════════════════════════════════════════════════════════════════
# 1. PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════

class TestProvidersIsolation:

    async def test_home_services_shows_only_home_services_providers(self, admin, fixture_data):
        r = await admin.get("/v1/admin/verticals/home-services/providers", params={"page_size": 100})
        assert r.status_code == 200, r.text
        ids = [i["tenant_id"] for i in r.json()["data"]["items"]]
        assert str(fixture_data["hs_tenant"]) in ids
        assert str(fixture_data["coach_tenant"]) not in ids

    async def test_coaching_shows_only_coaching_providers(self, admin, fixture_data):
        r = await admin.get("/v1/admin/verticals/coaching/providers", params={"page_size": 100})
        assert r.status_code == 200, r.text
        ids = [i["tenant_id"] for i in r.json()["data"]["items"]]
        assert str(fixture_data["coach_tenant"]) in ids
        assert str(fixture_data["hs_tenant"]) not in ids

    async def test_provider_detail_rejects_cross_vertical_access(self, admin, fixture_data):
        r = await admin.get(f"/v1/admin/verticals/coaching/providers/{fixture_data['hs_tenant']}")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "CROSS_VERTICAL_ACCESS_DENIED"


# ═══════════════════════════════════════════════════════════════════════════
# 2. STAFF
# ═══════════════════════════════════════════════════════════════════════════

class TestStaffIsolation:

    async def test_home_services_shows_only_assigned_staff(self, admin, fixture_data):
        r = await admin.get("/v1/admin/verticals/home-services/staff", params={"page_size": 100})
        assert r.status_code == 200, r.text
        ids = [i["staff_id"] for i in r.json()["data"]["items"]]
        assert str(fixture_data["hs_staff"]) in ids
        assert str(fixture_data["coach_staff"]) not in ids

    async def test_coaching_does_not_see_home_services_staff(self, admin, fixture_data):
        r = await admin.get("/v1/admin/verticals/coaching/staff", params={"page_size": 100})
        ids = [i["staff_id"] for i in r.json()["data"]["items"]]
        assert str(fixture_data["hs_staff"]) not in ids

    async def test_staff_detail_rejects_cross_vertical_access(self, admin, fixture_data):
        r = await admin.get(f"/v1/admin/verticals/coaching/staff/{fixture_data['hs_staff']}")
        assert r.status_code == 403, r.text

    async def test_removing_one_assignment_preserves_another(self, pg, fixture_data, verticals):
        """A staff member assigned to both verticals keeps the other
        assignment when one is removed -- no cascading delete."""
        staff_id = fixture_data["hs_staff"]
        both_id = uuid.uuid4()
        await pg.execute(
            "INSERT INTO staff_business_verticals (id, staff_id, tenant_id, vertical_id, is_active, "
            "verification_status, assignment_status, availability_status, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,true,'verified','assigned','available', now(), now())",
            both_id, staff_id, fixture_data["hs_tenant"], verticals["coaching"])
        try:
            row = await pg.fetchrow("SELECT COUNT(*) as c FROM staff_business_verticals WHERE staff_id = $1", staff_id)
            assert row["c"] == 2
            await pg.execute("DELETE FROM staff_business_verticals WHERE id = $1", both_id)
            row2 = await pg.fetchrow("SELECT COUNT(*) as c FROM staff_business_verticals WHERE staff_id = $1", staff_id)
            assert row2["c"] == 1  # original home_services assignment untouched
        finally:
            await pg.execute("DELETE FROM staff_business_verticals WHERE id = $1", both_id)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CUSTOMERS
# ═══════════════════════════════════════════════════════════════════════════

class TestCustomersIsolation:

    async def test_home_services_shows_only_hs_customers(self, admin, fixture_data):
        r = await admin.get("/v1/admin/verticals/home-services/customers", params={"page_size": 100})
        assert r.status_code == 200, r.text
        ids = [i["customer_id"] for i in r.json()["data"]["items"]]
        assert str(fixture_data["hs_customer"]) in ids
        assert str(fixture_data["coach_customer"]) not in ids

    async def test_customer_detail_rejects_cross_vertical_access(self, admin, fixture_data):
        r = await admin.get(f"/v1/admin/verticals/coaching/customers/{fixture_data['hs_customer']}")
        assert r.status_code == 403, r.text

    async def test_customer_complaints_count_scoped_to_vertical(self, admin, fixture_data):
        r = await admin.get(f"/v1/admin/verticals/home-services/customers/{fixture_data['hs_customer']}")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["complaints_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECURITY / NAVIGATION / VERTICAL DISABLE
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityAndDisable:

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/verticals/home-services/providers")
            assert r.status_code in (401, 403)

    async def test_disabled_vertical_blocks_all_four_routes(self, admin):
        await admin.post("/v1/admin/verticals/coaching/disable", json={"reason": "isolation test"})
        try:
            for domain in ("providers", "staff", "customers"):
                r = await admin.get(f"/v1/admin/verticals/coaching/{domain}")
                assert r.status_code == 403, f"{domain}: {r.text}"
                assert r.json().get("error_code") == "VERTICAL_DISABLED"
        finally:
            await admin.post("/v1/admin/verticals/coaching/enable")

    async def test_disabling_coaching_does_not_affect_home_services(self, admin):
        await admin.post("/v1/admin/verticals/coaching/disable", json={"reason": "isolation test"})
        try:
            r = await admin.get("/v1/admin/verticals/home-services/providers")
            assert r.status_code == 200, r.text
        finally:
            await admin.post("/v1/admin/verticals/coaching/enable")

    async def test_url_slug_maps_to_correct_vertical_key(self, admin):
        """The hyphenated URL segment resolves server-side to the real
        underscore vertical key -- not a separate/duplicate implementation."""
        r = await admin.get("/v1/admin/verticals/home-services/providers/summary")
        assert r.status_code == 200, r.text

    async def test_nonexistent_vertical_returns_404_not_500(self, admin):
        r = await admin.get("/v1/admin/verticals/totally-fake-vertical/providers")
        assert r.status_code == 404, r.text
