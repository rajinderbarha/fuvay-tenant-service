"""DPDP-COMMAND-CENTER-UPGRADE: proves the three concrete, highest-value
fixes made to the platform-wide Privacy & DPDP Command Center
(app/engines/compliance/):

1. Compliance health never defaults to 100/COMPLIANT because no requests
   exist -- it is an evidence-based evaluation of a fixed control checklist.
2. A versioned DPDP policy configuration (name/version/effective date/
   enforcement phase/SLA policy/evidence requirements) is stored data, not
   hardcoded frontend text.
3. The DPDP SLA evaluator scheduler is backend-authoritative (DPDPSchedulerRun
   log), not inferred from whether an admin clicked a button.
4. Cross-system data discovery (scan-data) reports REAL per-subject counts
   for wired modules, never a fake placeholder 0 that looks identical to a
   genuinely empty result.

Fixture data inserted directly via SQL -- same pattern as the other
Home-Services-consolidation test suites this session.
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


@pytest_asyncio.fixture
async def customer_with_cross_system_data(pg):
    """One customer with real rows in >=2 distinct systems (reviews +
    complaints + consent), proving discovery is genuinely cross-system,
    not a static per-category checklist."""
    customer_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    review_id = uuid.uuid4()
    complaint_id = uuid.uuid4()
    category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")

    await pg.execute(
        "INSERT INTO users (id, email, full_name, role, hashed_password, is_active, is_verified, "
        "created_at, updated_at) VALUES ($1,$2,'DPDP Test Customer','customer','x',true,true, now(), now())",
        customer_id, f"dpdptest_{customer_id.hex[:8]}@test.local")
    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        tenant_id, "DPDP Test Tenant " + str(tenant_id)[:8])
    await pg.execute(
        "INSERT INTO customer_reviews (id, review_number, customer_id, tenant_id, record_type, record_id, "
        "overall_rating, review_text, status, visibility, submitted_at, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,'service_job',$5,4,'Good','approved','public', now(), now(), now())",
        review_id, f"REV-{review_id.hex[:8]}", customer_id, tenant_id, uuid.uuid4())
    await pg.execute(
        "INSERT INTO customer_complaints (id, complaint_number, customer_id, tenant_id, category_id, "
        "record_type, record_id, complaint_type, priority, status, title, description, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,'service_job',$6,'service_quality','normal','open','Test','Test complaint', now(), now())",
        complaint_id, f"CMP-{complaint_id.hex[:6]}", customer_id, tenant_id, category["id"], uuid.uuid4())
    await pg.execute(
        "INSERT INTO consent_records (id, user_id, tenant_id, consent_type, action, policy_version, "
        "granted_at, created_at, updated_at) VALUES (gen_random_uuid(),$1,$2,'marketing','granted','DPDP-2025-v1', now(), now(), now())",
        customer_id, tenant_id)

    yield {"customer_id": customer_id, "tenant_id": tenant_id, "review_id": review_id, "complaint_id": complaint_id}

    await pg.execute("DELETE FROM compliance_audit_logs WHERE reference_id IN "
                      "(SELECT id::text FROM compliance_requests WHERE subject_id = $1)", customer_id)
    await pg.execute("DELETE FROM compliance_request_items WHERE request_id IN "
                      "(SELECT id FROM compliance_requests WHERE subject_id = $1)", customer_id)
    await pg.execute("DELETE FROM compliance_requests WHERE subject_id = $1", customer_id)
    await pg.execute("DELETE FROM consent_records WHERE user_id = $1", customer_id)
    await pg.execute("DELETE FROM customer_complaints WHERE id = $1", complaint_id)
    await pg.execute("DELETE FROM customer_reviews WHERE id = $1", review_id)
    await pg.execute("DELETE FROM tenants WHERE id = $1", tenant_id)
    await pg.execute("DELETE FROM users WHERE id = $1", customer_id)


# ═══════════════════════════════════════════════════════════════════════════
# 1. COMPLIANCE HEALTH — NEVER DEFAULT 100/COMPLIANT
# ═══════════════════════════════════════════════════════════════════════════

class TestComplianceHealth:

    async def test_health_reports_evidence_based_state(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/health")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert "state" in d and "controls_evaluated" in d and "controls_total" in d
        assert d["controls_evaluated"] <= d["controls_total"]
        # The exact scenario the spec forbids: a perfect score must never
        # appear without full control evaluation backing it.
        if d["score"] == 100:
            assert d["controls_evaluated"] == d["controls_total"]
            assert d["controls_failed"] == 0

    async def test_compliant_requires_full_evaluation(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/health")
        d = r.json()["data"]
        if d["is_compliant"]:
            assert d["controls_evaluated"] == d["controls_total"]
            assert d["controls_failed"] == 0
            assert d["controls_without_evidence"] == 0
        else:
            # band/state must not claim COMPLIANT when incomplete
            assert d["band"] != "compliant"

    async def test_health_calculation_method_disclosed(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/health")
        d = r.json()["data"]
        assert d["calculation_method"] == "fixed_control_checklist_v1"
        assert d["policy_version"] is not None


# ═══════════════════════════════════════════════════════════════════════════
# 2. POLICY VERSION / EFFECTIVE DATE
# ═══════════════════════════════════════════════════════════════════════════

class TestPolicyVersion:

    async def test_policy_version_and_effective_date_stored(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/policies")
        assert r.status_code == 200, r.text
        items = r.json()["data"]["items"]
        assert len(items) >= 1
        active = next(p for p in items if p["is_active"])
        assert active["policy_version"] == "DPDP-2025-v1"
        assert active["effective_date"] is not None
        assert active["publication_date"] is not None
        assert active["enforcement_phase"]
        assert isinstance(active["applicable_request_types"], list) and len(active["applicable_request_types"]) > 0
        assert isinstance(active["sla_policy"], dict) and active["sla_policy"]

    async def test_only_one_active_policy_version(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/policies")
        items = r.json()["data"]["items"]
        active = [p for p in items if p["is_active"]]
        assert len(active) == 1


# ═══════════════════════════════════════════════════════════════════════════
# 3. SCHEDULER (BACKEND-AUTHORITATIVE, AUDITED MANUAL RUN)
# ═══════════════════════════════════════════════════════════════════════════

class TestScheduler:

    async def test_scheduler_status_backend_authoritative(self, admin):
        r = await admin.get("/v1/admin/compliance/dpdp/scheduler-status")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] in ("healthy", "failed", "never_run")

    async def test_manual_run_updates_scheduler_status(self, admin, pg):
        before = await pg.fetchval("SELECT count(*) FROM dpdp_scheduler_runs")
        r = await admin.post("/v1/admin/compliance/jobs/run")
        assert r.status_code == 200, r.text
        assert "scheduler_run_id" in r.json()["data"]
        after = await pg.fetchval("SELECT count(*) FROM dpdp_scheduler_runs")
        assert after == before + 1

        status_r = await admin.get("/v1/admin/compliance/dpdp/scheduler-status")
        d = status_r.json()["data"]
        assert d["status"] == "healthy"
        assert d["last_run_trigger"] == "manual"

    async def test_manual_run_requires_authentication(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/admin/compliance/jobs/run")
            assert r.status_code in (401, 403)

    async def test_scheduler_run_records_actor(self, admin, pg):
        await admin.post("/v1/admin/compliance/jobs/run")
        row = await pg.fetchrow(
            "SELECT trigger, triggered_by_user_id FROM dpdp_scheduler_runs "
            "WHERE trigger = 'manual' ORDER BY started_at DESC LIMIT 1")
        assert row is not None
        assert row["triggered_by_user_id"] is not None


# ═══════════════════════════════════════════════════════════════════════════
# 4. CROSS-SYSTEM DATA DISCOVERY (real counts, not fake zeros)
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossSystemDiscovery:

    async def test_discovery_finds_data_across_multiple_systems(self, admin, customer_with_cross_system_data):
        cid = customer_with_cross_system_data["customer_id"]
        req_r = await admin.post("/v1/admin/compliance/requests", json={
            "subject_type": "customer", "subject_id": str(cid),
            "request_type": "data_export", "subject_email": "x@test.local",
            "request_source": "admin_created",
        })
        assert req_r.status_code in (200, 201), req_r.text
        request_id = req_r.json()["data"]["id"]

        scan_r = await admin.post(f"/v1/admin/compliance/requests/{request_id}/scan-data")
        assert scan_r.status_code == 200, scan_r.text
        scan = scan_r.json()["data"]

        # Real, wired modules must reflect this subject's actual data across
        # at least two distinct systems (reviews + complaints), not a
        # static per-category list with placeholder zeros.
        with_data = set(scan["categories_with_data"])
        assert "Reviews" in with_data
        assert "Complaints" in with_data
        assert len(with_data) >= 2

    async def test_unwired_modules_reported_not_faked_as_zero(self, admin, customer_with_cross_system_data):
        cid = customer_with_cross_system_data["customer_id"]
        req_r = await admin.post("/v1/admin/compliance/requests", json={
            "subject_type": "customer", "subject_id": str(cid),
            "request_type": "data_export", "subject_email": "x@test.local",
            "request_source": "admin_created",
        })
        request_id = req_r.json()["data"]["id"]
        scan_r = await admin.post(f"/v1/admin/compliance/requests/{request_id}/scan-data")
        scan = scan_r.json()["data"]
        # Modules genuinely not wired to a real per-subject query must be
        # explicitly disclosed, not silently presented as "0 records found".
        assert "Documents" in scan["modules_not_wired_for_automated_discovery"]

    async def test_category_filter_does_not_limit_discovery(self, admin, customer_with_cross_system_data):
        # The discovery scan itself is not parameterized by a client-
        # supplied category filter -- it always scans every wired module
        # for the resolved subject, regardless of any UI filter state.
        cid = customer_with_cross_system_data["customer_id"]
        req_r = await admin.post("/v1/admin/compliance/requests", json={
            "subject_type": "customer", "subject_id": str(cid),
            "request_type": "data_export", "subject_email": "x@test.local",
            "request_source": "admin_created",
        })
        request_id = req_r.json()["data"]["id"]
        scan_r = await admin.post(f"/v1/admin/compliance/requests/{request_id}/scan-data")
        scan = scan_r.json()["data"]
        assert scan["modules_scanned"] >= 15  # every configured module, not a filtered subset


# ═══════════════════════════════════════════════════════════════════════════
# 5. API FAILURE HANDLING
# ═══════════════════════════════════════════════════════════════════════════

class TestErrorHandling:

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/compliance/dpdp/health")
            assert r.status_code in (401, 403)
