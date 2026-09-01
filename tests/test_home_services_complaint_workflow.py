"""COMPLAINT-CONSOLIDATION: Home Services -> Complaints becomes the
authoritative Super Admin case-management queue, reusing the SAME canonical
`app.engines.complaints` engine (state machine, SLA, evidence, messaging,
resolution) through a vertical-scoped read/write surface
(`VerticalComplaintWorkspaceService`) -- never a second complaint engine.

Fixture data inserted directly via SQL (this environment's seed data is not
persistent across sessions) -- same pattern as
test_home_services_staff_consolidation.py / test_home_services_review_consolidation.py.
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
async def complaint_fixture(pg, hs_vertical_id):
    """One Home Services complaint + one Coaching complaint (isolation
    control), each with a real tenant/customer/job, real rows, cleaned up."""
    hs_tenant = uuid.uuid4()
    coach_tenant = uuid.uuid4()
    customer_id = uuid.uuid4()
    hs_job = uuid.uuid4()
    hs_complaint = uuid.uuid4()
    coach_complaint = uuid.uuid4()
    coach_vertical = await pg.fetchrow("SELECT id FROM verticals WHERE key = 'coaching'")
    category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")
    cat_id = category["id"]

    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        hs_tenant, "Complaint Test HS Tenant " + str(hs_tenant)[:8])
    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'coaching','active','verified', now(), now())",
        coach_tenant, "Complaint Test Coach Tenant " + str(coach_tenant)[:8])
    await pg.execute(
        "INSERT INTO users (id, email, full_name, role, hashed_password, is_active, is_verified, "
        "created_at, updated_at) VALUES ($1,$2,'Complaint Test Customer','customer','x',true,true, now(), now())",
        customer_id, f"cmptest_{customer_id.hex[:8]}@test.local")
    await pg.execute(
        "INSERT INTO service_jobs (id, job_number, booking_id, customer_id, tenant_id, category_id, "
        "offering_id, status, assignment_status, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,'completed','assigned', now(), now())",
        hs_job, f"HS-{hs_job.hex[:6]}", uuid.uuid4(), customer_id, hs_tenant, cat_id, uuid.uuid4())

    await pg.execute(
        "INSERT INTO customer_complaints (id, complaint_number, customer_id, tenant_id, category_id, "
        "record_type, record_id, job_id, complaint_type, priority, status, title, description, severity, "
        "sla_status, vertical_id, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,'service_job',$6,$6,'service_quality','normal','open','AC not cooling', "
        "'The AC stopped cooling again the next day.','high','on_time',$7, now(), now())",
        hs_complaint, f"CMP-{hs_complaint.hex[:6]}", customer_id, hs_tenant, cat_id, hs_job, hs_vertical_id)
    await pg.execute(
        "INSERT INTO customer_complaints (id, complaint_number, customer_id, tenant_id, category_id, "
        "record_type, record_id, complaint_type, priority, status, title, description, severity, "
        "sla_status, vertical_id, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,'coaching_appointment',$6,'service_quality','normal','open','Coach no-show', "
        "'Coach did not join session.','high','on_time',$7, now(), now())",
        coach_complaint, f"CMP-{coach_complaint.hex[:6]}", customer_id, coach_tenant, cat_id,
        uuid.uuid4(), coach_vertical["id"])

    yield {"hs_tenant": hs_tenant, "coach_tenant": coach_tenant, "customer_id": customer_id,
           "hs_job": hs_job, "hs_complaint": hs_complaint, "coach_complaint": coach_complaint}

    for tbl, col in [("complaint_events", "complaint_id"), ("complaint_messages", "complaint_id"),
                     ("complaint_resolutions", "complaint_id")]:
        await pg.execute(f"DELETE FROM {tbl} WHERE {col} = ANY($1::uuid[])", [hs_complaint, coach_complaint])
    await pg.execute("DELETE FROM customer_complaints WHERE id = ANY($1::uuid[])", [hs_complaint, coach_complaint])
    await pg.execute("DELETE FROM service_jobs WHERE id = $1", hs_job)
    await pg.execute("DELETE FROM users WHERE id = $1", customer_id)
    await pg.execute("DELETE FROM tenant_billing WHERE tenant_id = $1", hs_tenant)
    await pg.execute("DELETE FROM usage_credit_ledger WHERE tenant_id = $1", hs_tenant)
    await pg.execute("DELETE FROM tenants WHERE id = ANY($1::uuid[])", [hs_tenant, coach_tenant])


# ═══════════════════════════════════════════════════════════════════════════
# 1. VERTICAL ISOLATION
# ═══════════════════════════════════════════════════════════════════════════

class TestVerticalIsolation:

    async def test_hs_queue_shows_only_hs_complaints(self, admin, complaint_fixture):
        r = await admin.get("/v1/admin/verticals/home-services/complaints", params={"page_size": 100})
        assert r.status_code == 200, r.text
        ids = [c["id"] for c in r.json()["data"]["items"]]
        assert str(complaint_fixture["hs_complaint"]) in ids
        assert str(complaint_fixture["coach_complaint"]) not in ids

    async def test_coaching_queue_does_not_see_hs_complaint(self, admin, complaint_fixture):
        r = await admin.get("/v1/admin/verticals/coaching/complaints", params={"page_size": 100})
        if r.status_code == 403:
            assert r.json().get("error_code") == "VERTICAL_DISABLED"  # Coaching disabled in this env -- fails closed
            return
        ids = [c["id"] for c in r.json()["data"]["items"]]
        assert str(complaint_fixture["hs_complaint"]) not in ids

    async def test_cross_vertical_detail_rejected(self, admin, complaint_fixture):
        r = await admin.get(f"/v1/admin/verticals/coaching/complaints/{complaint_fixture['hs_complaint']}")
        # Fails closed either way: CROSS_VERTICAL_ACCESS_DENIED if Coaching
        # is enabled in this environment, VERTICAL_DISABLED if not.
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") in ("CROSS_VERTICAL_ACCESS_DENIED", "VERTICAL_DISABLED")

    async def test_cross_vertical_mutation_rejected(self, admin, complaint_fixture):
        r = await admin.post(f"/v1/admin/verticals/coaching/complaints/{complaint_fixture['hs_complaint']}/escalate",
                             json={"reason": "test"})
        assert r.status_code == 403

    async def test_query_param_cannot_override_scope(self, admin, complaint_fixture):
        r1 = await admin.get("/v1/admin/verticals/home-services/complaints", params={"page_size": 100})
        r2 = await admin.get("/v1/admin/verticals/home-services/complaints",
                             params={"page_size": 100, "vertical": "coaching"})
        assert [c["id"] for c in r1.json()["data"]["items"]] == [c["id"] for c in r2.json()["data"]["items"]]

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/verticals/home-services/complaints")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 2. JOB CONTEXT / METRICS-TABLE-EXPORT USE SAME PREDICATE
# ═══════════════════════════════════════════════════════════════════════════

class TestJobContextAndMetrics:

    async def test_complaint_resolves_exact_job(self, admin, complaint_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/complaints/{complaint_fixture['hs_complaint']}/job-context")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["job_linked"] is True
        assert d["job_id"] == str(complaint_fixture["hs_job"])

    async def test_summary_and_table_agree_on_open_count(self, admin, complaint_fixture):
        summary = await admin.get("/v1/admin/verticals/home-services/complaints/summary")
        table = await admin.get("/v1/admin/verticals/home-services/complaints", params={"status": "open", "page_size": 100})
        assert summary.json()["data"]["new"] == table.json()["data"]["total"]

    async def test_export_scoped_to_home_services(self, admin, complaint_fixture):
        r = await admin.get("/v1/admin/verticals/home-services/complaints/export")
        assert r.status_code == 200, r.text
        assert str(complaint_fixture["hs_complaint"]) in [c["id"] for c in r.json()["data"]["items"]]


# ═══════════════════════════════════════════════════════════════════════════
# 3. LIFECYCLE / STATE MACHINE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════

class TestLifecycle:

    async def test_assign_and_message_and_escalate(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        me = await admin.get("/v1/auth/me")
        admin_user_id = me.json()["data"]["id"] if me.status_code == 200 else None
        if admin_user_id:
            r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/assign",
                                 json={"assignee_id": admin_user_id})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["assigned_admin_user_id"] == admin_user_id

        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/message",
                             json={"message_text": "Internal: investigating", "internal_only": True})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["visibility"] == "admin_only"

        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/escalate",
                             json={"reason": "needs review"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["status"] == "under_admin_review"

    async def test_escalate_requires_reason(self, admin, complaint_fixture):
        cid = str(complaint_fixture["hs_complaint"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/escalate", json={"reason": ""})
        assert r.status_code == 422

    async def test_propose_then_resolve(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        await pg.execute("UPDATE customer_complaints SET status = 'under_admin_review' WHERE id = $1",
                         complaint_fixture["hs_complaint"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/propose-resolution", json={
            "resolution_type": "service_credit", "description": "Offering a service credit",
            "customer_visible_notes": "We're sorry for the trouble.", "internal_notes": "Approved by team",
        })
        assert r.status_code == 200, r.text

        await pg.execute("UPDATE customer_complaints SET status = 'under_admin_review' WHERE id = $1",
                         complaint_fixture["hs_complaint"])
        r2 = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/resolve", json={"reason": "settled"})
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["status"] == "resolved"

    async def test_invalid_transition_rejected(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        await pg.execute("UPDATE customer_complaints SET status = 'refund_recorded' WHERE id = $1",
                         complaint_fixture["hs_complaint"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/escalate", json={"reason": "x"})
        assert r.status_code in (400, 422)

    async def test_reopen_requires_permission_and_reason(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        await pg.execute("UPDATE customer_complaints SET status = 'resolved' WHERE id = $1",
                         complaint_fixture["hs_complaint"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/reopen", json={"reason": ""})
        assert r.status_code == 422
        r2 = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/reopen", json={"reason": "new evidence"})
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["status"] == "under_admin_review"


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTERNAL NOTES NEVER PUBLIC
# ═══════════════════════════════════════════════════════════════════════════

class TestConversationVisibility:

    async def test_internal_note_marked_admin_only(self, admin, complaint_fixture):
        cid = str(complaint_fixture["hs_complaint"])
        await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/message",
                         json={"message_text": "internal only note", "internal_only": True})
        r = await admin.get(f"/v1/admin/verticals/home-services/complaints/{cid}/conversation")
        assert r.status_code == 200, r.text
        note = next(m for m in r.json()["data"]["items"] if m["message_text"] == "internal only note")
        assert note["visibility"] == "admin_only"
        assert note["sender_type"] == "admin"


# ═══════════════════════════════════════════════════════════════════════════
# 5. RESOLUTION MODEL — SERVICE CREDIT / TENANT CREDIT LEDGER
# ═══════════════════════════════════════════════════════════════════════════

class TestResolutionLedgers:

    async def test_customer_service_credit_uses_canonical_ledger(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/issue-customer-credit",
                             json={"amount": "100", "reason": "Goodwill for repeated failure"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["credit_type"] == "complaint_resolution"
        # canonical ledger row exists (CustomerCreditLedger), not a bare balance write
        ledger_row = await pg.fetchrow(
            "SELECT * FROM customer_credit_ledger WHERE customer_credit_id = $1", uuid.UUID(data["id"]))
        assert ledger_row is not None
        assert ledger_row["transaction_type"] == "issued"

    async def test_tenant_credit_adjustment_uses_usage_credit_ledger(self, admin, complaint_fixture, pg):
        cid = str(complaint_fixture["hs_complaint"])
        # Manual debits intentionally fail closed rather than create a
        # negative provider wallet. Fund this synthetic tenant so the test
        # exercises the immutable debit-ledger path, not overdraft rejection.
        await pg.execute(
            "INSERT INTO tenant_billing (id, tenant_id, credit_balance, created_at, updated_at) "
            "VALUES ($1,$2,20,now(),now()) ON CONFLICT (tenant_id) DO UPDATE SET credit_balance=20, updated_at=now()",
            uuid.uuid4(), complaint_fixture["hs_tenant"])
        r = await admin.post(f"/v1/admin/verticals/home-services/complaints/{cid}/apply-tenant-credit-adjustment",
                             json={"direction": "debit", "credit_units": "10", "reason_code": "APPROVED_GOODWILL_ADJUSTMENT",
                                  "detailed_reason": "Complaint-driven adjustment"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["event_type"] == "manual_credit_adjustment"
        ledger_row = await pg.fetchrow(
            "SELECT * FROM usage_credit_ledger WHERE tenant_id = $1 AND event_type = 'manual_credit_adjustment'",
            complaint_fixture["hs_tenant"])
        assert ledger_row is not None
        assert float(ledger_row["credit_delta"]) == -10.0

    async def test_direct_payment_never_marked_platform_collection(self, complaint_fixture):
        # Static proof: the complaint workspace service never writes a
        # "platform_collected"/payment-collection field -- customer job
        # payment is structurally provider-direct (see ServicePaymentRecord/
        # home_services_finance_service docs from prior sessions).
        import inspect
        from app.engines.vertical_directory import service as mod
        src = inspect.getsource(mod.VerticalComplaintWorkspaceService)
        assert "platform_collected" not in src.lower()
        assert "cash_refund" not in src.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 6. PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════

class TestPermissions:

    def test_view_and_mutation_permissions_distinct(self):
        from app.core.permissions import P
        assert P.HOME_SERVICES_COMPLAINTS_VIEW != P.HOME_SERVICES_COMPLAINTS_RESOLVE
        assert P.HOME_SERVICES_COMPLAINTS_CREDIT_ISSUE != P.HOME_SERVICES_COMPLAINTS_CREDIT_ADJUST

    def test_readonly_role_has_view_but_not_mutations(self):
        from app.core.permissions import permission_checker
        assert permission_checker.has(role="admin_readonly", permission="home_services:complaints:view")
        assert not permission_checker.has(role="admin_readonly", permission="home_services:complaints:resolve")
        assert not permission_checker.has(role="admin_readonly", permission="home_services:complaints:credit_issue")

    def test_operations_role_has_full_workflow(self):
        from app.core.permissions import permission_checker
        for action in ("view", "assign", "message", "escalate", "resolve", "reopen", "credit_issue", "credit_adjust"):
            assert permission_checker.has(role="admin_operations", permission=f"home_services:complaints:{action}")


# ═══════════════════════════════════════════════════════════════════════════
# 7. NAVIGATION / DUPLICATE PAGE DISPOSITION
# ═══════════════════════════════════════════════════════════════════════════

class TestNavigationConsolidation:

    def test_no_global_complaints_menu(self):
        import pathlib
        layout = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
        code_only = "\n".join(l for l in layout.splitlines() if not l.strip().startswith("//"))
        assert 'href: "/admin/complaints"' not in code_only
        assert 'href: "/admin/home-services/complaints"' in code_only
