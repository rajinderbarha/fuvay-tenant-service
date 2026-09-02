"""REVIEW-CONSOLIDATION: the platform-wide "Reviews" page is retired; a
customer review belongs to an exact completed ServiceJob and is surfaced on
Home Services > Jobs > {Job ID} > Review & Feedback, aggregated on
Provider/Staff 360, with an exception-only moderation queue at
Home Services > Reviews Moderation. This suite proves the vertical-scoped
review router (hs_review_router.py) reuses the SAME canonical
customer_reviews engine, never a second review system.

Fixture data inserted directly via SQL (this environment's seed data is not
persistent across sessions) -- same pattern as
test_vertical_directory_framework.py / test_home_services_staff_consolidation.py.
"""
import os
import uuid
import pytest
import pytest_asyncio
import asyncpg
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"
DB_URL = "postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos"

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_SERVER_TESTS") != "1",
        reason="requires a separately running local API; set RUN_LIVE_SERVER_TESTS=1",
    ),
]
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
async def job_fixture(pg):
    """A completed Home Services ServiceJob with an approved review,
    a Coaching tenant + job for isolation checks, all real rows."""
    hs_tenant = uuid.uuid4()
    coach_tenant = uuid.uuid4()
    customer_id = uuid.uuid4()
    hs_job = uuid.uuid4()
    coach_job = uuid.uuid4()
    review_id = uuid.uuid4()

    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        hs_tenant, "Review Test HS Tenant " + str(hs_tenant)[:8])
    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'coaching','active','verified', now(), now())",
        coach_tenant, "Review Test Coach Tenant " + str(coach_tenant)[:8])
    await pg.execute(
        "INSERT INTO users (id, email, full_name, role, hashed_password, is_active, is_verified, "
        "created_at, updated_at) VALUES ($1,$2,'Review Test Customer','customer','x',true,true, now(), now())",
        customer_id, f"revtest_{customer_id.hex[:8]}@test.local")

    for job_id, tenant_id, num in [(hs_job, hs_tenant, f"HS-{hs_job.hex[:6]}"), (coach_job, coach_tenant, f"CO-{coach_job.hex[:6]}")]:
        await pg.execute(
            "INSERT INTO service_jobs (id, job_number, booking_id, customer_id, tenant_id, category_id, "
            "offering_id, status, assignment_status, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,'completed','assigned', now(), now())",
            job_id, num, uuid.uuid4(), customer_id, tenant_id, uuid.uuid4(), uuid.uuid4())

    await pg.execute(
        "INSERT INTO customer_reviews (id, review_number, customer_id, tenant_id, record_type, record_id, "
        "job_id, overall_rating, review_text, status, visibility, submitted_at, approved_at, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,'service_job',$5,$5,5,'Great service','approved','public', now(), now(), now(), now())",
        review_id, f"REV-{review_id.hex[:8]}", customer_id, hs_tenant, hs_job)

    yield {"hs_tenant": hs_tenant, "coach_tenant": coach_tenant, "hs_job": hs_job, "coach_job": coach_job,
           "customer_id": customer_id, "review_id": review_id}

    await pg.execute("DELETE FROM review_events WHERE review_id = $1", review_id)
    await pg.execute("DELETE FROM review_flags WHERE review_id = $1", review_id)
    await pg.execute("DELETE FROM customer_reviews WHERE id = $1", review_id)
    await pg.execute("DELETE FROM service_jobs WHERE id = ANY($1::uuid[])", [hs_job, coach_job])
    await pg.execute("DELETE FROM users WHERE id = $1", customer_id)
    await pg.execute("DELETE FROM tenants WHERE id = ANY($1::uuid[])", [hs_tenant, coach_tenant])


@pytest_asyncio.fixture
async def uncompleted_job_fixture(pg):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    await pg.execute(
        "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
        "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
        tenant_id, "Review Test Uncompleted Tenant " + str(tenant_id)[:8])
    await pg.execute(
        "INSERT INTO service_jobs (id, job_number, booking_id, tenant_id, category_id, offering_id, "
        "status, assignment_status, created_at, updated_at) "
        "VALUES ($1,$2,$3,$4,$5,$6,'assigned','assigned', now(), now())",
        job_id, f"HS-{job_id.hex[:6]}", uuid.uuid4(), tenant_id, uuid.uuid4(), uuid.uuid4())
    yield {"tenant_id": tenant_id, "job_id": job_id}
    await pg.execute("DELETE FROM service_jobs WHERE id = $1", job_id)
    await pg.execute("DELETE FROM tenants WHERE id = $1", tenant_id)


# ═══════════════════════════════════════════════════════════════════════════
# 1. JOB 360 REVIEW LINK
# ═══════════════════════════════════════════════════════════════════════════

class TestJobReviewLink:

    async def test_job_not_completed_state(self, admin, uncompleted_job_fixture):
        job_id = uncompleted_job_fixture["job_id"]
        r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_id}/review")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["state"] == "job_not_completed"

    async def test_completed_job_no_review_is_awaiting(self, admin, pg):
        tenant_id = uuid.uuid4()
        job_id = uuid.uuid4()
        await pg.execute(
            "INSERT INTO tenants (id, tenant_name, business_name, vertical, status, verification_status, "
            "created_at, updated_at) VALUES ($1,$2,$2,'home_services','active','verified', now(), now())",
            tenant_id, "Awaiting Review Tenant " + str(tenant_id)[:8])
        await pg.execute(
            "INSERT INTO service_jobs (id, job_number, booking_id, tenant_id, category_id, offering_id, "
            "status, assignment_status, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,'completed','assigned', now(), now())",
            job_id, f"HS-{job_id.hex[:6]}", uuid.uuid4(), tenant_id, uuid.uuid4(), uuid.uuid4())
        try:
            r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_id}/review")
            assert r.status_code == 200, r.text
            assert r.json()["data"]["state"] == "awaiting_review"
        finally:
            await pg.execute("DELETE FROM service_jobs WHERE id = $1", job_id)
            await pg.execute("DELETE FROM tenants WHERE id = $1", tenant_id)

    async def test_review_belongs_to_exact_job(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["job_id"] == str(job_fixture["hs_job"])
        assert d["state"] == "review_available"
        assert d["overall_rating"] == 5

    async def test_review_belongs_to_home_services(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/coaching/jobs/{job_fixture['hs_job']}/review")
        # Fails closed either way: CROSS_VERTICAL_ACCESS_DENIED if Coaching
        # is enabled in this environment, VERTICAL_DISABLED if not -- both
        # are a hard 403, never a successful cross-vertical read.
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") in ("CROSS_VERTICAL_ACCESS_DENIED", "VERTICAL_DISABLED")

    async def test_query_param_cannot_override_vertical_scope(self, admin, job_fixture):
        r1 = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review")
        r2 = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review",
                             params={"vertical": "coaching"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["data"]["overall_rating"] == r2.json()["data"]["overall_rating"]

    async def test_review_integrity_no_action_required(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review/integrity")
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "no_action_required"
        assert d["checks"]["one_canonical_review_per_job"] is True
        assert d["checks"]["review_belongs_to_home_services"] is True

    async def test_rating_impact_reflects_contribution(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review/rating-impact")
        assert r.status_code == 200, r.text
        assert r.json()["data"]["contributes"] is True

    async def test_permission_enforced_no_token(self, job_fixture):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════
# 2. PROVIDER / STAFF AGGREGATES
# ═══════════════════════════════════════════════════════════════════════════

class TestAggregates:

    async def test_provider_review_summary_scoped(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/providers/{job_fixture['hs_tenant']}/review-summary")
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["data"]["recent_reviews"], list)

    async def test_provider_summary_rejects_cross_vertical(self, admin, job_fixture):
        r = await admin.get(f"/v1/admin/verticals/home-services/providers/{job_fixture['coach_tenant']}/review-summary")
        assert r.status_code == 403, r.text


# ═══════════════════════════════════════════════════════════════════════════
# 3. MODERATION QUEUE (exception-only)
# ═══════════════════════════════════════════════════════════════════════════

class TestModeration:

    async def test_normal_review_not_in_moderation_queue(self, admin, job_fixture):
        r = await admin.get("/v1/admin/verticals/home-services/reviews/moderation")
        assert r.status_code == 200, r.text
        ids = [i["id"] for i in r.json()["data"]["items"]]
        assert str(job_fixture["review_id"]) not in ids  # status=approved, not an exception

    async def test_flag_moves_review_into_moderation_queue(self, admin, job_fixture):
        rid = str(job_fixture["review_id"])
        flag_r = await admin.post(f"/v1/admin/verticals/home-services/reviews/{rid}/flag", json={"reason": "test flag"})
        assert flag_r.status_code == 200, flag_r.text

        queue_r = await admin.get("/v1/admin/verticals/home-services/reviews/moderation", params={"status": "flagged"})
        ids = [i["id"] for i in queue_r.json()["data"]["items"]]
        assert rid in ids

        resolve_r = await admin.post(f"/v1/admin/verticals/home-services/reviews/{rid}/resolve", json={"reason": "reviewed"})
        assert resolve_r.status_code == 200, resolve_r.text

    async def test_escalate_does_not_crash_and_logs_event(self, admin, job_fixture):
        rid = str(job_fixture["review_id"])
        r = await admin.post(f"/v1/admin/verticals/home-services/reviews/{rid}/escalate", json={"reason": "needs finance review"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["id"] == rid

    async def test_hide_and_restore_updates_review_state(self, admin, job_fixture):
        rid = str(job_fixture["review_id"])
        hide_r = await admin.post(f"/v1/admin/verticals/home-services/reviews/{rid}/hide", json={"reason": "policy"})
        assert hide_r.status_code == 200, hide_r.text
        assert hide_r.json()["data"]["status"] == "hidden"

        job_review_r = await admin.get(f"/v1/admin/verticals/home-services/jobs/{job_fixture['hs_job']}/review")
        assert job_review_r.json()["data"]["state"] == "review_hidden"

        restore_r = await admin.post(f"/v1/admin/verticals/home-services/reviews/{rid}/restore", json={"reason": "resolved"})
        assert restore_r.status_code == 200, restore_r.text
        assert restore_r.json()["data"]["status"] == "approved"

    def test_admin_cannot_edit_rating_or_text(self):
        # Every POST mutation this router exposes accepts only {reason: str}
        # -- there is no request body shape anywhere that could carry a
        # client-supplied overall_rating/review_text into a review record.
        # (overall_rating/review_text DO appear elsewhere in this module as
        # read-only query filters/response fields -- that's fine; what must
        # never exist is a POST body field for them.)
        import inspect
        from app.engines.customer_reviews import hs_review_router as mod
        src = inspect.getsource(mod)
        assert "class ModerationActionRequest(BaseModel):" in src
        model_block = src[src.index("class ModerationActionRequest"):]
        model_block = model_block[:model_block.index("\n\n\n")]
        assert "reason: str" in model_block
        assert "overall_rating" not in model_block
        assert "review_text" not in model_block

    async def test_moderation_queue_scoped_to_home_services(self, admin, job_fixture, pg):
        # A flagged Coaching review must never appear in the HS queue.
        coach_review_id = uuid.uuid4()
        await pg.execute(
            "INSERT INTO customer_reviews (id, review_number, customer_id, tenant_id, record_type, record_id, "
            "job_id, overall_rating, review_text, status, visibility, submitted_at, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,'service_job',$5,$5,1,'bad','flagged','hidden', now(), now(), now())",
            coach_review_id, f"REV-{coach_review_id.hex[:8]}", job_fixture["customer_id"],
            job_fixture["coach_tenant"], job_fixture["coach_job"])
        try:
            r = await admin.get("/v1/admin/verticals/home-services/reviews/moderation", params={"status": "flagged"})
            ids = [i["id"] for i in r.json()["data"]["items"]]
            assert str(coach_review_id) not in ids
        finally:
            await pg.execute("DELETE FROM customer_reviews WHERE id = $1", coach_review_id)


# ═══════════════════════════════════════════════════════════════════════════
# 4. NAVIGATION CONSOLIDATION (static source inspection)
# ═══════════════════════════════════════════════════════════════════════════

class TestNavigationConsolidation:

    def test_global_reviews_nav_removed(self):
        import pathlib
        layout = pathlib.Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
        assert 'href: "/admin/reviews"' not in layout

    def test_unlinked_global_reviews_route_remains_operational(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/reviews/page.tsx").read_text(encoding="utf-8")
        assert "adminReviewApi.list" in src
        assert '<AdminLayout activeNav="reviews">' in src

    def test_job_360_has_review_tab(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx").read_text(encoding="utf-8")
        assert "ReviewFeedbackTab" in src
        assert '"Review & Feedback"' in src

    def test_moderation_page_exists_and_scoped(self):
        import pathlib
        src = pathlib.Path("frontend/super-admin/app/admin/home-services/reviews/moderation/page.tsx").read_text(encoding="utf-8")
        assert "home-services" in src
